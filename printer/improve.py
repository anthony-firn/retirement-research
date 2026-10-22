"""Improvement harness: test PASSIVE changes (cost, tax, fund choice, settings, credit; no market signals) to the current best
money printers for the retiree case (the retiree's taxes, taxable account). Queue and verdicts: results/IMPROVE.md.

Two tracks, kept in results/improve_best.json:
  simple  the printer the retiree can run at M1 with no credit
  credit  the best printer with a box-spread loan (IBKR/Schwab)
Each IDEA maps a track's current best to candidate variants. SEARCH: all candidates + the reference on the same 1,000 histories in
5 cases (base, trend -2%/yr, trend -4%/yr, 2000-2026 era only, 3-month blocks). The 3 best candidates that keep break risk no worse than
the reference are re-run with it on 2,000 FRESH histories. ACCEPTED if, on the fresh histories: break risk is no worse in every case
(ends below start <= +1 pt, dips < 70% <= +2 pts, runs dry <= +0.2 pt, base never cut >= -2 pts, margin calls <= max(1%, reference)),
robust CE (risk aversion 3, mean of the 5 cases) is >= 0.5% higher (any gain for FREE ideas: same holdings, lower cost/tax), and the first-decade bad-history print is not lower.
Usage: IDEA=<name> THROTTLE=1 python3 printer/improve.py [--accept]   (writes results/improve/<name>.json and .log)"""
import os, sys, json, time, subprocess, datetime as dt, numpy as np
from dataclasses import asdict, replace
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); ACCEPT = "--accept" in sys.argv; sys.argv = [sys.argv[0]]
import money_printer as mp, search as se
P = mp.Printer; OUT = os.environ.get("RESEARCH_OUT", os.path.join(ROOT, "..", "results")); BEST_F = os.environ.get("RESEARCH_BEST_FILE", os.path.join(OUT, "improve_best.json"))
SEARCH_SEED = int(os.environ.get("SEARCH_SEED", "601")); VALIDATION_SEED = int(os.environ.get("VALIDATION_SEED", "701"))
PATHS = int(os.environ.get("PATHS", "1000")); FRESH = int(os.environ.get("FRESH", "2000")); THROTTLE = max(0.75, float(os.environ.get("THROTTLE", "1")))
S2 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65)
START = {"simple": asdict(P("MP-2", mp.load_alloc("MP-2 engine"), **S2)),
         "credit": asdict(P("MP-2 + $10k box loan (1.2x), base 5.25%", mp.load_alloc("MP-2 engine"), lev=1.2, rate_spread=0.6, interest_tax="capital", **{**S2, "base": 5.25}))}
def load_best(): return json.load(open(BEST_F)) if os.path.exists(BEST_F) else START

def cool(limit=80, resume=74):                                     # laptop heat guard (it shut down twice)
    try:
        t = int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.split()[0])
        while t >= limit:
            print(f"  GPU {t}C, cooling...", flush=True); time.sleep(60)
            t = int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.split()[0])
            if t < resume: break
    except Exception: pass

I00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
def cases(seed, n):
    return {"base": (mp.make_idx(n, 40, seed=seed), {}), "trend -2%/yr": (mp.make_idx(n, 40, seed=seed + 1), dict(trend_haircut=0.02)),
            "trend -4%/yr": (mp.make_idx(n, 40, seed=seed + 2), dict(trend_haircut=0.04)), "recent era": (mp.make_idx(n, 40, seed=seed + 3, era=(I00, mp.T)), {}),
            "3-month blocks": (mp.make_idx(n, 40, block=63, seed=seed + 4), {})}
def evaluate(pr, C):
    res = {p.name: {} for p in pr}
    for lab, (IDX, kw) in C.items():
        for i in range(0, len(pr), 8):
            cool(); tb = time.time(); r = mp.simulate(pr[i:i + 8], IDX, **kw)
            for c, p in enumerate(pr[i:i + 8]): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name][lab] = s
            time.sleep(THROTTLE * (time.time() - tb))
        print(f"    {lab} done", flush=True)
    for v in res.values(): v["robust_ce"] = float(np.mean([v[k]["ce"] for k in C])); v["worst_margin_call"] = max(v[k].get("margin_call", 0) for k in C)
    return res
def safe(v, ref, C):
    return all(v[k]["lose_value"] <= ref[k]["lose_value"] + .01 and v[k]["deep_dip"] <= ref[k]["deep_dip"] + .02 and v[k]["run_dry"] <= ref[k]["run_dry"] + .002
               and v[k]["base_never_cut"] >= ref[k]["base_never_cut"] - .02 for k in C) and v["worst_margin_call"] <= max(.01, ref["worst_margin_call"])
def better(v, ref, gain=0.005): return v["robust_ce"] > ref["robust_ce"] * (1 + gain) and v["base"]["print_y1_10_bad"] >= ref["base"]["print_y1_10_bad"] - 1e-6

# ------------------------------------------------------------------ ideas: track best -> candidate variants (names must be unique)
def swap(p, old, new, label):
    a = dict(p.alloc)
    if old not in a: return []
    a[new] = a.get(new, 0) + a.pop(old); return [replace(p, name=f"{p.name} | {label}", alloc=a)]
def settings(p):                                                   # one or two settings at a time around the current best
    v = lambda lab, **kw: replace(p, name=f"{p.name} | {lab}", **kw); out = []
    out += [v(f"skim>{int(100 + 100 * k)}%", skim=k) for k in (0.25, 0.60, 0.80, 1.0, 1.5) if k != p.skim]
    out += [v(f"bucket {m}m", bucket_months=m) for m in (36, 60, 72, 96) if m != p.bucket_months]
    out += [v(f"skim>{int(100 + 100 * k)}% bucket {m}m", skim=k, bucket_months=m) for k, m in ((0.6, 60), (0.8, 72), (1.0, 96))]
    out += [v(f"base {p.base + d:.2f}%", base=p.base + d) for d in (-0.25, 0.25)]
    out += [v(f"guardrail at {int(c * 100)}%", cut_below=c) for c in (0.65, 0.75)] + [v(f"cut to {int(c * 100)}%", cut_to=c) for c in (0.5, 0.8) if c != p.cut_to]
    out += [v(f"restore at {int(r * 100)}%", restore_above=r) for r in (0.8, 1.0)]
    out += [v(f"band {b}pt", band=b) for b in (4.0, 10.0)] + [v(f"valve {x}x", valve=x) for x in (1.5, 3.0)]
    if p.lev > 1: out += [v(f"leverage {l}x", lev=l) for l in (round(p.lev - 0.1, 2), round(p.lev + 0.1, 2))]
    return out
def combo(p):                                                      # box-spread boost + a run line (separate loan, same box rate)
    if p.lev <= 1: return []
    return [replace(p, name=f"{p.name} | + {int(c * 100)}% run line" + (" below 90%" if db < 1 else ""), credit=c, draw_below=db) for c in (0.10, 0.15, 0.25) for db in (1.0, 0.9)]
def stacked(p):                                                    # return-stacked funds: 2 exposures per dollar (NTSX 90/60 US stocks/Treasuries, RSSB 100/100 global)
    out = []
    for old in ("VBRSIM", "GDESIM"):
        for new, xs in (("NTSXSIM", (5, 10, 15)), ("RSSBSIM", (5, 10, 15))):
            for x in xs:
                a = dict(p.alloc)
                if a.get(old, 0) < x: continue
                a[old] -= x; a[new] = a.get(new, 0) + x; a = {k: w for k, w in a.items() if w > 0}
                out.append(replace(p, name=f"{p.name} | {x} {old[:-3]} -> {new[:-3]}", alloc=a))
    return out
def glidepath(p):                                                  # calendar-based shift between stocks (VBR, GDE) and defenders, by age
    out = []
    for x in (5, 10):
        for dlab, dst in (("trend", {"DBMFSIM": .5, "KMLMSIM": .5}), ("gold", {"IAUMSIM": 1.0} if "IAUMSIM" in p.alloc else {"GLDSIM": 1.0})):
            d = dict(p.alloc); d["VBRSIM"] -= x / 2; d["GDESIM"] -= x / 2
            for k, f in dst.items(): d[k] = d.get(k, 0) + x * f
            if min(d.values()) < 0 or any(k not in p.alloc for k in d): continue
            for yrs in (10, 20):
                out.append(replace(p, name=f"{p.name} | rising stocks: {x} pts {dlab}->stocks over {yrs}y", alloc=d, glide=dict(p.alloc), glide_years=yrs))
                out.append(replace(p, name=f"{p.name} | falling stocks: {x} pts stocks->{dlab} over {yrs}y", glide=d, glide_years=yrs))
    return out
def rules(p):                                                      # income rules that react to the account, not the market
    return [replace(p, name=f"{p.name} | bucket tops up a cut base", bucket_fill=True), replace(p, name=f"{p.name} | no raise after a losing year", no_raise_after_loss=True),
            replace(p, name=f"{p.name} | both rules", bucket_fill=True, no_raise_after_loss=True)]
def settings2(p):                                                  # pairs of the settings that came close in the first pass
    v = lambda lab, **kw: replace(p, name=f"{p.name} | {lab}", **kw)
    return [v("valve 3x + restore 80%", valve=3.0, restore_above=0.8), v("valve 3x + guardrail 75%", valve=3.0, cut_below=0.75), v("restore 80% + guardrail 75%", restore_above=0.8, cut_below=0.75),
            v("valve 3x + restore 80% + guardrail 75%", valve=3.0, restore_above=0.8, cut_below=0.75), v("valve 2.5x", valve=2.5), v("valve 4x", valve=4.0), v("no valve", valve=0),
            v("valve 3x + skim>125%", valve=3.0, skim=0.25), v("valve 3x + base 5.5%", valve=3.0, base=p.base - 0.25)]
def rsst(p):                                                       # RSST (US stocks + trend, 2 exposures per dollar) replaces X of VBR and X of DBMF;
    out = []                                                       # the freed X goes to defenders, to stocks, or pro rata; optimistic and pessimistic proxy
    for fund, tag in (("RSSTSIM", "RSST"), ("RSSTPSIM", "RSST pessimistic")):
        for x in (5, 10, 15):
            for dlab, dst in (("defenders", {"KMLMSIM": .5, ("IAUMSIM" if "IAUMSIM" in p.alloc else "GLDSIM"): .5}), ("stocks", {"VBRSIM": .5, "GDESIM": .5}), ("pro rata", None)):
                a = dict(p.alloc)
                if a.get("VBRSIM", 0) < x or a.get("DBMFSIM", 0) < x: continue
                a["VBRSIM"] -= x; a["DBMFSIM"] -= x
                if dst is None: tot = sum(a.values()); a = {k: w + x * w / tot for k, w in a.items()}
                else:
                    for k, f in dst.items(): a[k] = a.get(k, 0) + x * f
                a[fund] = x; out.append(replace(p, name=f"{p.name} | {x} {tag} for {x} VBR + {x} DBMF, freed to {dlab}", alloc=a))
    return out
def lever_engines(p):                                              # box-spread leverage on calmer engines instead of MP-2 (credit track only)
    if p.lev <= 1: return []
    engines = {"CH-12": "Crisis-Hedged 12 (no UUP)", "CH-11.5": "Crisis-Hedged 11.5", "Gold-Stack 12": "Gold-Stack 12"}
    allocs = {k: mp.load_alloc(v) for k, v in engines.items()}; allocs["3-fund VBR 35 / KMLM 35 / gold 30"] = {"VBRSIM": 35, "KMLMSIM": 35, "GLDSIM": 30}
    out = []
    for lab, a in allocs.items():
        a = {("IAUMSIM" if k == "GLDSIM" else k): w for k, w in a.items()}
        out += [replace(p, name=f"{p.name} | engine {lab}, {l}x, base {b}%", alloc=a, lev=l, base=b) for l in (1.2, 1.35, 1.5) for b in (5.25, 5.75)]
    return out
def gde_stack(p):                                                  # more GDE (90% stocks + 90% gold per dollar) for the same VBR + gold exposure;
    out = []                                                       # the freed capital goes to the trend funds or pro rata
    gold = "IAUMSIM" if "IAUMSIM" in p.alloc else "GLDSIM"
    for g in (4, 6, int(p.alloc.get(gold, 0) / 0.9 * 10) / 10):
        a = dict(p.alloc); x = 0.9 * g
        if a.get(gold, 0) < x - 1e-9 or a.get("VBRSIM", 0) < x: continue
        a["VBRSIM"] -= x; a[gold] -= x; a["GDESIM"] += g; freed = 2 * x - g
        for dlab in ("trend", "pro rata"):
            b = {k: w for k, w in a.items() if w > 1e-9}
            if dlab == "trend": b["DBMFSIM"] += freed / 2; b["KMLMSIM"] += freed / 2
            else: tot = sum(b.values()); b = {k: w + freed * w / tot for k, w in b.items()}
            out.append(replace(p, name=f"{p.name} | +{g} GDE for {x:.1f} VBR + {x:.1f} gold, freed to {dlab}", alloc=b))
    return out
def settings3(p):                                                  # credit track: a second pass around the new best
    v = lambda lab, **kw: replace(p, name=f"{p.name} | {lab}", **kw)
    if p.lev <= 1: return [v("no valve", valve=0), v("valve 4x", valve=4.0)]
    return [v("leverage 1.25x", lev=1.25), v("leverage 1.3x", lev=1.3), v("band 10pt", band=10.0), v("leverage 1.25x + band 10pt", lev=1.25, band=10.0),
            v("base 5.5%", base=5.5), v("leverage 1.25x + base 5.5%", lev=1.25, base=5.5), v("restore 75%", restore_above=0.75), v("valve 4x", valve=4.0),
            v("guardrail 75%", cut_below=0.75), v("skim>125%", skim=0.25)]
def climb(p):                                                      # short GPU hill-climb on the fund weights around the current best (same settings);
    import search as sr                                            # guard rails as printer/search.py; the top distinct engines go to the normal test
    sys.path.insert(0, os.path.join(ROOT, "..", "lab")); import stress_forward as sf
    U = ["DBMFSIM", "KMLMSIM", "VBRSIM", "GDESIM", "IAUMSIM" if "IAUMSIM" in p.alloc else "GLDSIM", "TQQQSIM", "XLVSIM", "XLESIM", "VTVSIM", "SPMOSIM", "IEISIM"]
    mv = lambda t, sc: sf.move("GLDSIM" if t in ("IAUMSIM", "GLDMSIM") else t, sc)
    def valid(a):
        if len(a) > 9 or any(w > 35 or w < 1 for w in a.values()) or sum(a.values()) != 100: return False
        if a.get("KMLMSIM", 0) + a.get("DBMFSIM", 0) > 42 or a.get("TQQQSIM", 0) > 25 or sum(sr.AI.get(t, 0) * w for t, w in a.items()) > 25: return False
        return min(sum(w / 100 * mv(t, sf.SC[k]) for t, w in a.items()) for k in sr.BAD) >= -8.5
    rng = np.random.default_rng(int(p.lev * 100)); IDX = mp.make_idx(int(os.environ.get("CLIMB_PATHS", "256")), 40, step=5, seed=int(os.environ.get("CLIMB_SEED", "901")))
    def mutate(q):
        for _ in range(50):
            a = {k: int(round(w)) for k, w in q.alloc.items()}; a[max(a, key=a.get)] += 100 - sum(a.values())
            x = rng.choice(list(a)); y = rng.choice(U); d = int(rng.choice([1, 2, 3]))
            if x == y or a[x] < d: continue
            a[x] -= d; a[y] = a.get(y, 0) + d; a = {k: w for k, w in a.items() if w > 0}
            if valid(a): return replace(q, alloc=a)
        return q
    def fit(pop):
        r = [mp.simulate(pop, IDX, step=5, **kw) for kw in ({}, dict(trend_haircut=0.02), dict(trend_haircut=0.04))]
        out = []
        for c in range(len(pop)):
            ces = [se.ce(x["spend"][c], gamma=3.0) for x in r]; b0 = r[0]
            pen = 0.3 * max(0, (b0["real_end"][c] < 1).mean() - R0["lose"]) + 0.3 * max(0, (b0["minreal"][c] < .7).mean() - R0["dip"]) + 2 * max(0, r[2]["dead"][c].mean() - R0["dry4"]) \
                  + 2 * max(0, max(x["margin_call"][c].mean() for x in r) - 0.01)
            out.append(float(np.mean(ces)) - pen)
        return out
    r0 = [mp.simulate([p], IDX, step=5, **kw) for kw in ({}, dict(trend_haircut=0.04))]
    R0 = dict(lose=(r0[0]["real_end"][0] < 1).mean(), dip=(r0[0]["minreal"][0] < .7).mean(), dry4=r0[1]["dead"][0].mean())
    pop = [p] + [mutate(mutate(p)) for _ in range(31)]; f = fit(pop); seen = {}
    for it in range(int(os.environ.get("CLIMB_ITERS", "30"))):
        cool(); tb = time.time(); kids = [mutate(q) for q in pop]; kf = fit(kids)
        for i in range(len(pop)):
            if kf[i] > f[i]: pop[i], f[i] = kids[i], kf[i]
        for q, v in zip(pop, f): seen[tuple(sorted(q.alloc.items()))] = (v, q)
        time.sleep(THROTTLE * (time.time() - tb))
    top = [q for v, q in sorted(seen.values(), key=lambda t: -t[0]) if q.alloc != p.alloc][:12]
    return [replace(q, name=f"{p.name} | climb: " + " ".join(f"{k[:-3]} {w}" for k, w in sorted(q.alloc.items(), key=lambda t: -t[1]))) for q in top]
def settings_local(p):                                             # one step in each direction on every setting, around the current best (both tracks)
    v = lambda lab, **kw: replace(p, name=f"{p.name} | {lab}", **kw); out = []
    if p.lev > 1 and not p.lev_daily: out += [v(f"leverage {round(p.lev + d, 2)}x", lev=round(p.lev + d, 2)) for d in (-0.05, 0.05)]
    out += [v(f"base {p.base + d:.2f}%", base=p.base + d) for d in (-0.25, 0.25)]
    out += [v(f"skim>{int(round(100 + 100 * (p.skim + d)))}%", skim=round(p.skim + d, 2)) for d in (-0.10, 0.10)]
    out += [v(f"bucket {p.bucket_months + d}m", bucket_months=p.bucket_months + d) for d in (-12, 12)]
    out += [v(f"guardrail {int(round((p.cut_below + d) * 100))}%", cut_below=round(p.cut_below + d, 2)) for d in (-0.05, 0.05)]
    out += [v(f"cut to {int(round((p.cut_to + d) * 100))}%", cut_to=round(p.cut_to + d, 2)) for d in (-0.05, 0.05)]
    out += [v(f"restore {int(round((p.restore_above + d) * 100))}%", restore_above=round(p.restore_above + d, 2)) for d in (-0.05, 0.05)]
    out += [v(f"band {p.band + d:g}pt", band=p.band + d) for d in (-2.0, 2.0)]
    out += [v(f"valve {x:g}x", valve=x) for x in (2.0, 3.0, 4.0, 0) if x != p.valve]
    return out
def front_load(p):                                                 # higher base early, lower later (the retiree's early years matter most)
    return [replace(p, name=f"{p.name} | base {p.base + up:.2f}% for {yrs}y then {p.base - dn:.2f}%", base=p.base + up, base_years=yrs, base_after=p.base - dn)
            for up in (0.25, 0.5) for yrs in (10, 15) for dn in (0.25, 0.5, 0.75)]
def trend_more(p):                                                 # more trend (DBMF/KMLM, kept 27:15) from VBR + GDE pro rata; beyond the 42% guard rail
    out = []
    t0 = p.alloc.get("DBMFSIM", 0) + p.alloc.get("KMLMSIM", 0); s0 = p.alloc.get("VBRSIM", 0) + p.alloc.get("GDESIM", 0)
    for tot in (45, 48, 50):
        x = tot - t0; a = dict(p.alloc)
        for k in ("VBRSIM", "GDESIM"): a[k] -= x * p.alloc[k] / s0
        a["DBMFSIM"] += x * 27 / 42; a["KMLMSIM"] += x * 15 / 42
        out.append(replace(p, name=f"{p.name} | trend {tot}% (from VBR + GDE)", alloc=a))
    return out
def crash_lev(p):                                                  # credit track: leverage target that reacts to the account's own drawdown
    if p.lev <= 1: return []
    out = [replace(p, name=f"{p.name} | brake: {p.lev}x -> {to}x while >= {int(th * 100)}% below its high", lev_dd=th, lev_dd_to=to) for th in (0.15, 0.25) for to in (1.0, 1.1)]
    out += [replace(p, name=f"{p.name} | lever more: {p.lev}x -> {to}x while >= {int(th * 100)}% below its high", lev_dd=th, lev_dd_to=to) for th in (0.15, 0.20, 0.25) for to in (1.4, 1.5)]
    return out
def phase_in(p):                                                   # simple track: park part in short Treasuries (SHY) for the first year(s)
    if p.lev > 1: return []
    out = []
    for c, yrs in ((33, 1), (50, 1), (50, 2)):
        a = {k: w * (100 - c) / 100 for k, w in p.alloc.items()}; a["SHYSIM"] = c; g = dict(p.alloc); g["SHYSIM"] = 0
        out.append(replace(p, name=f"{p.name} | phase in: {c}% in SHY, invested over {yrs}y", alloc=a, glide=g, glide_years=yrs))
    return out
def real_assets(p):                                                # energy (oil/war/inflation regime) or international stocks (outside the US AI bubble)
    out = []
    for src_, dst, xs in (("VBRSIM", "XLESIM", (3, 5, 8)), ("GDESIM", "XLESIM", (3, 5)), ("VBRSIM", "VXUSSIM", (5, 10)), ("GDESIM", "VXUSSIM", (5,))):
        for x in xs:
            a = dict(p.alloc)
            if a.get(src_, 0) < x: continue
            a[src_] -= x; a[dst] = a.get(dst, 0) + x; out.append(replace(p, name=f"{p.name} | {x} {src_[:-3]} -> {dst[:-3]}", alloc=a))
    return out
def lever_more_mild(p):
    if p.lev <= 1: return []
    return [replace(p, name=f"{p.name} | lever more: {p.lev}x -> {to}x while >= {int(th * 100)}% below its high", lev_dd=th, lev_dd_to=to) for th in (0.20, 0.25, 0.30) for to in (1.3, 1.35)]
def crash_buyer(p):                                                # simple track: no loan normally, a box loan only after a fall (needs IBKR/Schwab)
    if p.lev > 1: return []
    box = dict(rate_spread=0.6, interest_tax="capital")
    return [replace(p, name=f"{p.name} | crash buyer: box loan to {to}x while >= {int(th * 100)}% below its high", lev_dd=th, lev_dd_to=to, **box) for th in (0.15, 0.20, 0.25) for to in (1.15, 1.25)]
FREE = {"cheap_gold", "bucket_tax", "bucket_offset"}               # same holdings, lower cost or tax: any gain counts
OPS = {"tlh"}                                                      # adds recurring manual work (swaps): must gain >= 0.25%                                # same holdings, lower cost or tax: any gain counts (no 0.5% bar)
IDEAS = {
    "cheap_gold": lambda p: swap(p, "GLDSIM", "GLDMSIM", "GLD -> GLDM") + swap(p, "GLDSIM", "IAUMSIM", "GLD -> IAUM"),
    "bucket_tax": lambda p: [replace(p, name=f"{p.name} | bucket in Treasury fund", bucket_tax="treasury"), replace(p, name=f"{p.name} | bucket in BOXX", bucket_tax="boxx")],
    "settings": settings,
    "combo": combo,
    "stacked": stacked,
    "glidepath": glidepath,
    "rules": rules,
    "settings2": settings2,
    "rsst": rsst,
    "lever_engines": lever_engines,
    "gde_stack": gde_stack,
    "bucket_offset": lambda p: [replace(p, name=f"{p.name} | bucket pays the loan down", bucket_offsets_loan=True)] if p.lev > 1 and not p.lev_daily else [],
    "settings3": settings3,
    "climb": climb,
    "settings_local": settings_local,
    "front_load": front_load,
    "trend_more": trend_more,
    "crash_lev": crash_lev,
    "phase_in": phase_in,
    "real_assets": real_assets,
    "lever_more_mild": lever_more_mild,
    "crash_buyer": crash_buyer,
    "tlh": lambda p: [replace(p, name=f"{p.name} | harvest losses >= {int(h * 100)}% into twins", harvest=h) for h in (0.05, 0.10)],
}

def run(idea):
    best = load_best(); logp = os.path.join(OUT, "improve", f"{idea}.log"); os.makedirs(os.path.dirname(logp), exist_ok=True); log = open(logp, "w")
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    say(f"IDEA {idea} — {dt.datetime.now():%Y-%m-%d %H:%M}"); out = {}; new_best = dict(best)
    only = [t for t in os.environ.get("TRACKS", "").split(",") if t]
    for track, spec in best.items():
        if only and track not in only: continue
        ref = P(**spec); cand = IDEAS[idea](ref)
        if not cand: say(f"  [{track}] no candidates"); continue
        say(f"  [{track}] reference: {ref.name}; {len(cand)} candidates; search {PATHS} histories x 5 cases")
        R = evaluate([ref] + cand, cases(SEARCH_SEED, PATHS)); C = list(cases(0, 1)); gain = 0.0 if idea in FREE else 0.0025 if idea in OPS else 0.005
        def twin_ok(p):                                            # a proxy-based change counts only if its pessimistic twin passes too
            t = p.name.replace("RSST for", "RSST pessimistic for")
            return t == p.name or "pessimistic" in p.name or (t in R and safe(R[t], R[ref.name], C) and better(R[t], R[ref.name], gain))
        ok = sorted([p for p in cand if safe(R[p.name], R[ref.name], C) and twin_ok(p) and "pessimistic" not in p.name], key=lambda p: -R[p.name]["robust_ce"])[:3]
        V = evaluate([ref] + ok, cases(VALIDATION_SEED, FRESH)) if ok else {}
        gain = 0.0 if idea in FREE else 0.0025 if idea in OPS else 0.005
        verdict = [p for p in ok if safe(V[p.name], V[ref.name], C) and better(V[p.name], V[ref.name], gain)]
        win = max(verdict, key=lambda p: V[p.name]["robust_ce"]) if verdict else None
        out[track] = dict(search=R, validate=V, winner=win.name if win else None)
        mo = lambda x, z: f"${x * z / 12:,.0f}"
        for title, T in (("search", R), ("fresh", V)):
            if not T: continue
            say(f"  [{track}] {title}: {'printer':70} | robust CE $50k / $100k | first 10 yrs typ/bad ($50k) | 40-yr typ/bad ($50k) | never cut  lose  dip  dry | trend -4% CE | safe better")
            for n, v in sorted(T.items(), key=lambda kv: -kv[1]["robust_ce"]):
                b = v["base"]; r0 = T[ref.name]
                say(f"  {'':10} {(n if len(n) <= 70 else '…' + n[-69:]):70} | {mo(v['robust_ce'], 5e4):>6} / {mo(v['robust_ce'], 1e5):>6} ({(v['robust_ce'] / r0['robust_ce'] - 1) * 100:+.1f}%) | "
                    f"{mo(b['print_y1_10_typ'], 5e4)} / {mo(b['print_y1_10_bad'], 5e4)} | {mo(b['print_typical'], 5e4)} / {mo(b['print_bad'], 5e4)} | "
                    f"{b['base_never_cut'] * 100:3.0f}%  {b['lose_value'] * 100:3.0f}%  {b['deep_dip'] * 100:3.0f}%  {b['run_dry'] * 100:3.1f}% | {mo(v['trend -4%/yr']['ce'], 5e4)} | "
                    f"{'yes' if safe(v, r0, C) else 'no ':3}  {'yes' if better(v, r0, gain) else 'no'}")
        say(f"  [{track}] VERDICT: " + (f"ACCEPT {win.name} (robust CE {(V[win.name]['robust_ce'] / V[ref.name]['robust_ce'] - 1) * 100:+.1f}% on fresh histories)" if win else "keep the reference"))
        if win: new_best[track] = asdict(win)
    json.dump(out, open(os.path.join(OUT, "improve", f"{idea}.json"), "w"), indent=1, default=str)
    if ACCEPT and new_best != best: json.dump(new_best, open(BEST_F, "w"), indent=1); say("  improve_best.json updated")
    return out

def confirm(n=4000):
    """Night's start vs current best for each track on brand-new histories (seeds no idea has seen) + actual 40-year windows."""
    best = load_best(); C = cases(1101, n); C["actual 40-yr windows"] = (mp.make_idx(0, 40, hist=True), {}); out = {}
    logp = os.path.join(OUT, "improve", "confirm.log"); log = open(logp, "w")
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    say(f"CONFIRM on new histories ({n} paths per case, seeds 1101-1105) + actual windows — {dt.datetime.now():%Y-%m-%d %H:%M}")
    for track in best:
        pr = [P(**START.get(track, START["simple"])), P(**best[track])]
        if pr[0].name == pr[1].name: continue
        R = evaluate(pr, C); out[track] = R; a, b = (R[q.name] for q in pr); K5 = list(cases(0, 1))
        for v in (a, b): v["robust_ce"] = float(np.mean([v[k]["ce"] for k in K5])); v["worst_margin_call"] = max(v[k].get("margin_call", 0) for k in K5)
        say(f"\n[{track}] start: {pr[0].name}\n[{track}] best:  {pr[1].name}")
        say(f"  robust CE (5 cases): ${a['robust_ce'] * 5e4 / 12:,.0f} -> ${b['robust_ce'] * 5e4 / 12:,.0f} at $50k ({(b['robust_ce'] / a['robust_ce'] - 1) * 100:+.1f}%), "
            f"${a['robust_ce'] * 1e5 / 12:,.0f} -> ${b['robust_ce'] * 1e5 / 12:,.0f} per $100k; break risk no worse in every case: {'yes' if safe(b, a, list(cases(0, 1))) else 'NO'}")
        for k in C:
            x, y = a[k], b[k]; mo = lambda v: f"${v * 5e4 / 12:,.0f}"
            say(f"  {k:22} | first 10 yrs typ {mo(x['print_y1_10_typ'])} -> {mo(y['print_y1_10_typ'])}, bad {mo(x['print_y1_10_bad'])} -> {mo(y['print_y1_10_bad'])} | 40-yr typ {mo(x['print_typical'])} -> {mo(y['print_typical'])}, "
                f"bad {mo(x['print_bad'])} -> {mo(y['print_bad'])} | never cut {x['base_never_cut']*100:.0f}% -> {y['base_never_cut']*100:.0f}% | lose {x['lose_value']*100:.0f}% -> {y['lose_value']*100:.0f}% | "
                f"dip {x['deep_dip']*100:.0f}% -> {y['deep_dip']*100:.0f}% | dry {x['run_dry']*100:.1f}% -> {y['run_dry']*100:.1f}% | margin call {x.get('margin_call', 0)*100:.1f}% -> {y.get('margin_call', 0)*100:.1f}%")
        if pr[1].lev > 1 and not pr[1].lev_daily:                     # box-spread premium 0.6 pts wider than assumed (both printers)
            pw = [replace(q, name=q.name + " [box +0.6]", rate_spread=q.rate_spread + 0.6) for q in pr]; W = evaluate(pw, {"base": C["base"], "trend -4%/yr": C["trend -4%/yr"]})
            x, y = (W[q.name] for q in pw); mo = lambda v: f"${v * 5e4 / 12:,.0f}"
            for k in ("base", "trend -4%/yr"):
                say(f"  box +0.6 pts, {k:12} | CE {mo(x[k]['ce'])} -> {mo(y[k]['ce'])} | 40-yr typ {mo(x[k]['print_typical'])} -> {mo(y[k]['print_typical'])} | lose {x[k]['lose_value']*100:.0f}% -> {y[k]['lose_value']*100:.0f}% | "
                    f"dip {x[k]['deep_dip']*100:.0f}% -> {y[k]['deep_dip']*100:.0f}% | dry {x[k]['run_dry']*100:.1f}% -> {y[k]['run_dry']*100:.1f}% | margin call {x[k].get('margin_call', 0)*100:.1f}% -> {y[k].get('margin_call', 0)*100:.1f}%")
            out[track + " box +0.6"] = W
    json.dump(out, open(os.path.join(OUT, "improve", "confirm.json"), "w"), indent=1, default=str)

if __name__ == "__main__" and os.environ.get("CONFIRM"): confirm(int(os.environ.get("FRESH", "4000")))
elif __name__ == "__main__":
    idea = os.environ.get("IDEA")
    if idea not in IDEAS: print("IDEA must be one of:", ", ".join(IDEAS)); sys.exit(1)
    run(idea)
