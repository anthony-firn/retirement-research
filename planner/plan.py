"""Retirement planner: Social Security, pensions, account types, taxes - on top of the investment policy.

Annual steps in REAL (today's) dollars, vectorised over historical paths (every quarter 1972-2016 with enough
data) and bootstrapped 1-year-block paths. Brackets, standard deduction and SS COLA are inflation-indexed
(constant in real terms); non-indexed items (SS-taxation thresholds, pensions without COLA) erode with CPI.
Portfolio each year: the policy's tier for that year's budget (strategy/policy.py), same in every account.

Usage:  python3 plan.py profile.json        (see examples/*.json)
Research tool - simplified tax model (federal 2026 + flat state), not tax or legal advice.
"""
import json, os, sys, math, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, "..", "strategy"))
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import policy as pl

# ------------------------------------------------------------------ tax tables (2026, approx. = 2025 indexed)
BRACKETS = {"single": [(11925, .10), (48475, .12), (103350, .22), (197300, .24), (250525, .32), (626350, .35), (1e18, .37)],
            "mfj": [(23850, .10), (96950, .12), (206700, .22), (394600, .24), (501050, .32), (751600, .35), (1e18, .37)]}
LTCG = {"single": [(48350, 0.0), (533400, .15), (1e18, .20)], "mfj": [(96700, 0.0), (600050, .15), (1e18, .20)]}
STD = {"single": 15750, "mfj": 31500}; SENIOR_EXTRA = {"single": 2000, "mfj": 1600}      # per 65+ person
SS_THRESH = {"single": (25000, 34000), "mfj": (32000, 44000)}                          # NOT inflation-indexed
RMD_AGE = 75; RMD_DIV = {75: 24.6, 80: 20.2, 85: 16.0, 90: 12.2, 95: 8.9, 100: 6.4}

def tax_ordinary(x, filing):
    tax = np.zeros_like(x); lo = 0.0
    for hi, r in BRACKETS[filing]: tax += np.clip(x - lo, 0, hi - lo) * r; lo = hi
    return tax
def tax_ltcg(gains, ordinary_taxable, filing):
    tax = np.zeros_like(gains); lo = 0.0; base = ordinary_taxable
    for hi, r in LTCG[filing]:
        room = np.clip(hi - np.maximum(base, lo), 0, None); take = np.minimum(gains, room); tax += take * r; gains = gains - take; base = base + take; lo = hi
    return tax
def ss_taxable(ss, other_income, filing, erosion):
    """IRS provisional-income rule: 0 / up to 50% / up to 85% of benefits taxable. Thresholds are not indexed."""
    a, b = SS_THRESH[filing]; a = a / erosion; b = b / erosion
    prov = other_income + 0.5 * ss
    mid = np.minimum(0.5 * ss, 0.5 * np.clip(prov - a, 0, None))
    high = np.minimum(0.85 * ss, 0.85 * np.clip(prov - b, 0, None) + np.minimum(0.5 * ss, 0.5 * (b - a)))
    return np.where(prov <= a, 0.0, np.where(prov <= b, mid, high))
def rmd_factor(age):
    if age < RMD_AGE: return 0.0
    ks = sorted(RMD_DIV); age = min(age, ks[-1])
    for a0, a1 in zip(ks, ks[1:]):
        if a0 <= age <= a1: d = RMD_DIV[a0] + (RMD_DIV[a1] - RMD_DIV[a0]) * (age - a0) / (a1 - a0); return 1 / d
    return 1 / RMD_DIV[ks[-1]]

# ------------------------------------------------------------------ Social Security
def own_benefit(pia_month, fra, claim_age):
    m = (fra - claim_age) * 12
    if m > 0: f = 1 - (min(m, 36) * 5 / 9 + max(m - 36, 0) * 5 / 12) / 100
    else: f = 1 + min(-m, (70 - fra) * 12) * (2 / 3) / 100
    return pia_month * 12 * f
def survivor_benefit(deceased_month, survivor_fra, claim_age):
    if claim_age < 60: return 0.0
    f = 1.0 if claim_age >= survivor_fra else 0.715 + 0.285 * (claim_age - 60) / (survivor_fra - 60)
    return deceased_month * 12 * f
def ss_income(person, age):
    """Annual real SS for one person at `age` (COLA keeps it constant in real terms)."""
    ss = person.get("ss") or {}; out = 0.0
    if ss.get("pia_month") and age >= ss.get("claim_age", 67): out = max(out, own_benefit(ss["pia_month"], ss.get("fra", 67), ss.get("claim_age", 67)))
    sv = ss.get("survivor")
    if sv and age >= sv.get("claim_age", 67): out = max(out, survivor_benefit(sv["deceased_benefit_month"], sv.get("fra", 67), sv.get("claim_age", 67)))
    return out
def pension_income(person, age, erosion):
    p = person.get("pension")
    if not p or age < p.get("start_age", 65): return 0.0
    amt = p["annual"]; cola = p.get("cola", 0.0); yrs = age - p.get("start_age", 65)
    return amt * ((1 + cola) ** yrs) / erosion * (1.0)               # nominal pension in today's $: grows by COLA, erodes by CPI

# ------------------------------------------------------------------ return paths (real, annual, per tier)
def annual_paths(n_boot=1000, seed=3):
    V = np.array(pl.D["v"]).T; t = np.array(pl.D["t"])
    I = json.load(open(os.path.join(pl.ROOT, "data_indicators.json"))); ci = np.array(I["INFLATION"]["t"]); cv = np.array(I["INFLATION"]["v"])
    cpi = cv[np.clip(np.searchsorted(ci, t, side="right") - 1, 0, None)]
    yr = np.arange(0, len(t) - 252, 252); R = V[yr + 252] / V[yr] / (cpi[yr + 252] / cpi[yr])[:, None] - 1; INF = cpi[yr + 252] / cpi[yr] - 1   # (Y, K)
    hist = []; starts = [i for i in range(len(t)) if (i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])) and pl.DATES[i] < "2017"]
    for s in starts:
        idx = np.arange(s, len(t) - 252, 252); hist.append((V[idx + 252] / V[idx] / (cpi[idx + 252] / cpi[idx])[:, None] - 1, cpi[idx + 252] / cpi[idx] - 1, pl.DATES[s]))
    g = np.random.default_rng(seed); boot = [(R[g.integers(0, len(R), 60)], INF[g.integers(0, len(R), 60)] * 0 + INF.mean(), "boot") for _ in range(n_boot)]
    # bootstrap draws whole years jointly (returns + that year's inflation)
    boot = []
    for _ in range(n_boot):
        k = g.integers(0, len(R), 60); boot.append((R[k], INF[k], "boot"))
    return hist, boot

# ------------------------------------------------------------------ the simulation
def simulate(profile, paths, horizon_age=95):
    """Returns per-path dict arrays. Paths: list of (real annual tier returns (Y,K), inflation (Y,), label)."""
    P = len(paths); filing = profile.get("filing", "single"); state = profile.get("state_tax", 0.0)
    people = profile["people"]; age0 = people[0]["age"]; ret_age = profile["retire_age"]
    acc = profile["accounts"]; tax_v = np.full(P, float(acc.get("taxable", {}).get("value", 0))); basis = np.full(P, float(acc.get("taxable", {}).get("basis", acc.get("taxable", {}).get("value", 0))))
    trad = np.full(P, float(acc.get("traditional", {}).get("value", 0))); roth = np.full(P, float(acc.get("roth", {}).get("value", 0)))
    contrib = profile.get("contrib", {}); spend = float(profile["spending"]); div_yield = profile.get("taxable_yield", 0.02); turnover = profile.get("taxable_turnover", 0.15)
    max_drop = profile.get("max_drop"); erosion = np.ones(P)
    alive = np.ones(P, bool); taxes = np.zeros(P); spent = np.zeros(P); years = horizon_age - age0
    min_total = np.full(P, np.inf); ok = np.ones(P, bool)
    for y in range(years):
        age = age0 + y; total = tax_v + trad + roth; retired = age >= ret_age
        # portfolio for this year from the policy
        b, _ = pl.life_budget(age, float(np.median(total)), sum(contrib.values()), ret_age, spend, max_drop=max_drop)
        x = pl.tier_for_budget(b); lo = int(math.floor(x)); hi = min(lo + 1, pl.LADDER.__len__() - 1); f = x - lo
        r = np.array([(1 - f) * p[0][min(y, len(p[0]) - 1), lo] + f * p[0][min(y, len(p[0]) - 1), hi] if y < len(p[0]) else np.nan for p in paths])
        infl = np.array([p[1][y] if y < len(p[1]) else np.nan for p in paths]); valid = ~np.isnan(r)
        r = np.nan_to_num(r); infl = np.nan_to_num(infl); erosion = erosion * (1 + infl)
        # growth
        gain_frac = np.where(tax_v > 0, np.clip(1 - basis / np.maximum(tax_v, 1e-9), 0, 1), 0)
        tax_v = tax_v * (1 + r); trad = trad * (1 + r); roth = roth * (1 + r)
        # taxable-account annual tax drag: dividends (half qualified) + realised gains from rebalancing turnover
        divs = tax_v * div_yield; realised = tax_v * turnover * gain_frac
        basis = basis + realised + divs                                                # realised gains + reinvested dividends raise basis
        income = sum(pension_income(p_, age, erosion) for p_ in people) + np.zeros(P)
        ss = sum(ss_income(p_, age_p) for p_, age_p in ((p_, p_["age"] + y) for p_ in people)) + np.zeros(P)
        if not retired:
            tax_v += contrib.get("taxable", 0); basis += contrib.get("taxable", 0); trad += contrib.get("traditional", 0); roth += contrib.get("roth", 0)
            ordinary = divs * 0.5 + income; taxable_ss = ss_taxable(ss, ordinary, filing, erosion)
            ti = np.clip(ordinary + taxable_ss - STD[filing], 0, None)
            t = tax_ordinary(ti, filing) + tax_ltcg(realised + divs * 0.5, ti, filing) + state * (ti + realised + divs * 0.5)
            tax_v -= t                                                                  # assume portfolio taxes paid from the taxable account (wages cover the rest)
        else:
            rmd = trad * rmd_factor(age); need = np.maximum(spend - ss - income, 0)
            # iterate gross-up: withdraw taxable -> traditional (beyond RMD) -> Roth until net covers need + taxes
            w_tax = np.zeros(P); w_trad = rmd.copy(); w_roth = np.zeros(P)
            for _ in range(4):
                ordinary = w_trad + income + divs * 0.5; taxable_ss = ss_taxable(ss, ordinary, filing, erosion)
                n65 = sum(1 for p_ in people if p_["age"] + y >= 65)
                ti = np.clip(ordinary + taxable_ss - STD[filing] - SENIOR_EXTRA[filing] * n65, 0, None)
                gains = w_tax * gain_frac + realised + divs * 0.5
                t = tax_ordinary(ti, filing) + tax_ltcg(gains, ti, filing) + state * (ti + gains)
                short = need + t - (w_tax + w_trad + w_roth)
                add_tax = np.clip(np.minimum(short, tax_v - w_tax), 0, None); w_tax += add_tax; short -= add_tax
                add_trad = np.clip(np.minimum(short, trad - w_trad), 0, None); w_trad += add_trad; short -= add_trad
                add_roth = np.clip(np.minimum(short, roth - w_roth), 0, None); w_roth += add_roth; short -= add_roth
            basis = basis * np.where(tax_v > 0, 1 - w_tax / np.maximum(tax_v, 1e-9), 1)
            tax_v -= w_tax; trad -= w_trad; roth -= w_roth
            excess = np.clip((w_tax + w_trad + w_roth) - need - t, 0, None); tax_v += excess; basis += excess   # RMD surplus reinvested (taxable)
            covered = (w_tax + w_trad + w_roth + ss + income) >= spend + t - 1
            ok &= covered | ~valid; spent += np.where(valid, np.minimum(spend, w_tax + w_trad + w_roth + ss + income - t), 0)
        taxes += np.where(valid, t, 0)
        total = tax_v + trad + roth; min_total = np.where(valid, np.minimum(min_total, total), min_total)
        tax_v, trad, roth = (np.maximum(a, 0) for a in (tax_v, trad, roth))
    return dict(success=ok, end=tax_v + trad + roth, taxes=taxes, low=min_total)

def summary(res):
    return dict(success=float(res["success"].mean() * 100), end_p10=float(np.percentile(res["end"], 10)), end_p50=float(np.median(res["end"])),
                taxes_p50=float(np.median(res["taxes"])), low_p10=float(np.percentile(res["low"], 10)))

def sweep_ss(prof, paths):
    """Try every survivor-claim age (60-67) x own-claim age (62-70) for person 0 (if survivor benefit given) or own claim 62-70."""
    p0 = prof["people"][0]; ss = p0.get("ss", {}); res = []
    sv_ages = range(60, 68) if ss.get("survivor") else [None]
    for sa in sv_ages:
        for oa in range(62, 71):
            q = json.loads(json.dumps(prof)); s_ = q["people"][0]["ss"]; s_["claim_age"] = oa
            if sa is not None: s_["survivor"]["claim_age"] = sa
            m = summary(simulate(q, paths)); res.append((sa, oa, m))
    return sorted(res, key=lambda r: (-r[2]["success"], -r[2]["end_p10"]))

def sweep_retire(prof, paths, ages=range(45, 71), target=95.0):
    out = []
    for a in ages:
        if a < prof["people"][0]["age"]: continue
        q = dict(prof); q["retire_age"] = a; m = summary(simulate(q, paths)); out.append((a, m))
        if m["success"] >= target: break
    return out

if __name__ == "__main__":
    prof = json.load(open(sys.argv[1])); flags = sys.argv[2:]; hist, boot = annual_paths()
    print(f"Plan: {prof.get('name', '')}   (today's $; {len(hist)} historical starts 1972-2016 + {len(boot)} bootstrapped paths)")
    for lab, paths in (("history", hist), ("synthetic", boot)):
        s = summary(simulate(prof, paths))
        print(f"  {lab:9}: success to 95 {s['success']:5.1f}% | ending wealth p10 ${s['end_p10']:,.0f}  median ${s['end_p50']:,.0f} | "
              f"lowest balance p10 ${s['low_p10']:,.0f} | lifetime taxes median ${s['taxes_p50']:,.0f}")
    if "--ss" in flags:
        print("\nSocial Security claiming strategies (synthetic paths), best first:")
        for sa, oa, m in sweep_ss(prof, boot)[:8]:
            print(f"  {'survivor at ' + str(sa) + ', ' if sa else ''}own at {oa}: success {m['success']:5.1f}% | ending p10 ${m['end_p10']:,.0f} median ${m['end_p50']:,.0f}")
    if "--retire" in flags:
        print("\nEarliest retirement age with >= 95% success (synthetic paths):")
        for a, m in sweep_retire(prof, boot): print(f"  retire at {a}: success {m['success']:5.1f}% | ending p10 ${m['end_p10']:,.0f}")
