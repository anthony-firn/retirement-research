"""Equilibrium (perpetual) withdrawal + rebalancing-rule search on the GPU.
Portfolio: Crisis-Hedged 12 (env PF). Each lane = (rebalancing rule, withdrawal rate, market history).
- Histories: 1-year block bootstrap of joint daily returns of the 8 funds + CPI (1972-2026), or the actual 30-year windows (HIST=1).
- Monthly withdrawal = rate x starting value / 12, grown with inflation (constant real income), taken from the most overweight funds first.
- Rebalance rules: drift band (abs pp) with a minimum spacing, optional safety valve (any fund >= m x target, any time),
  or calendar yearly (every 252 days) with the 2x valve (current rule). Trading cost 0.05% of traded value.
- Taxable account: average-cost basis per fund, flat tax on each year's net realized gains (env TAX, default 0.03 = the retiree's likely case:
  ~0% federal LTCG + CA), paid from the portfolio at year-end; losses carry forward.
Output per rule: equilibrium rate where the 30-year real ending value = start in 50% / 90% of histories, plus dips."""
import os, sys, json, math, time, numpy as np, torch
src = open(os.path.join(os.path.dirname(os.path.abspath(globals().get("__file__", "equilibrium_gpu.py"))), "rebal_test.py")).read(); exec(src[:src.index("S = [(")])
DEV = torch.device("cuda"); f32 = torch.float32
YEARS = int(os.environ.get("YEARS", "30")); L = YEARS * 252; PATHS = int(os.environ.get("PATHS", "1000")); TAXR = float(os.environ.get("TAX", "0.03"))
HAIR = float(os.environ.get("MF_HAIRCUT", "0"))
cpi = np.nan_to_num(np.asarray(h.cpi, float), nan=np.nan); cpi = np.where(np.isnan(cpi), np.nanmin(cpi), cpi); CPIR = np.r_[1.0, cpi[1:] / cpi[:-1]]
Rn = R.copy()
if HAIR:
    for n in ("KMLMSIM", "DBMFSIM"):
        if n in names: Rn[:, names.index(n)] -= HAIR / 252
Rg = torch.tensor(Rn, device=DEV, dtype=f32); Cg = torch.tensor(CPIR, device=DEV, dtype=f32); W0g = torch.tensor(W0, device=DEV, dtype=f32)
def make_idx(seed):
    if os.environ.get("HIST"):
        st = np.arange(1, T - L, 21); return torch.tensor(st[:, None] + np.arange(L)[None, :], device=DEV)
    g = np.random.default_rng(seed); nb = L // 252 + 1; s = g.integers(1, T - 252, size=(PATHS, nb))
    return torch.tensor((s[:, :, None] + np.arange(252)[None, None, :]).reshape(PATHS, -1)[:, :L], device=DEV)
def simulate(rules, rates, IDX, taxr=TAXR, skim=None, full=False):
    C, K, P = len(rules), len(rates), IDX.shape[0]; N = C * K * P
    ci = torch.arange(C, device=DEV).repeat_interleave(K * P); ki = torch.arange(K, device=DEV).repeat_interleave(P).repeat(C); pi = torch.arange(P, device=DEV).repeat(C * K)
    X = torch.tensor([r.get("band", 1e9) for r in rules], device=DEV, dtype=f32)[ci]; G = torch.tensor([r.get("gap", 0) for r in rules], device=DEV)[ci]
    VM = torch.tensor([r.get("valve", 1e9) for r in rules], device=DEV, dtype=f32)[ci]; YR = torch.tensor([bool(r.get("yearly", False)) for r in rules], device=DEV)[ci]
    rate = torch.tensor(rates, device=DEV, dtype=f32)[ki] / 100
    val = W0g.repeat(N, 1).clone(); basis = val.clone(); last = torch.zeros(N, dtype=torch.long, device=DEV); infl = torch.ones(N, device=DEV)
    gains = torch.zeros(N, device=DEV); carry = torch.zeros(N, device=DEV); minreal = torch.ones(N, device=DEV); dead = torch.zeros(N, dtype=torch.bool, device=DEV)
    nreb = torch.zeros(N, device=DEV); taxpaid = torch.zeros(N, device=DEV); lowyear = torch.full((N,), 9.0, device=DEV)
    inc = torch.zeros(N, YEARS, device=DEV); yi = 0
    for d in range(1, L):
        rows = IDX[pi, d]; val = val * (1 + Rg[rows]); infl = infl * Cg[rows]
        V = val.sum(1)
        if d % 21 == 0:                                                       # monthly withdrawal from overweight funds first
            amt = (rate / 12 * infl).clamp(max=V.clamp(min=0)); tgt = W0g * V[:, None]; exc = (val - tgt).clamp(min=0); se = exc.sum(1)
            take_exc = torch.minimum(amt, se); rest = amt - take_exc
            sell = exc * (take_exc / se.clamp(min=1e-12))[:, None] + (val - exc * (take_exc / se.clamp(min=1e-12))[:, None]) * (rest / (V - take_exc).clamp(min=1e-12))[:, None]
            inc[:, min(yi, YEARS - 1)] += sell.sum(1) / infl
            frac = (sell / val.clamp(min=1e-12)).clamp(0, 1); gains += (sell - basis * frac).sum(1); basis = basis * (1 - frac); val = val - sell
            V = val.sum(1); dead |= V <= 1e-6
        w = val / V.clamp(min=1e-12)[:, None]
        since = d - last
        trig = (((w - W0g).abs().max(1).values * 100 > X) & (since > G)) | ((w / W0g).max(1).values >= VM) | (YR & (since >= 252))
        trig &= ~dead
        if trig.any():
            tgt = W0g * V[:, None]; over = (val > tgt) & trig[:, None]; under = (val < tgt) & trig[:, None]
            frac = torch.where(over, (val - tgt) / val.clamp(min=1e-12), torch.zeros_like(val)); gains += (torch.where(over, val - tgt, torch.zeros_like(val)) - basis * frac).sum(1)
            basis = basis * (1 - frac) + torch.where(under, tgt - val, torch.zeros_like(val))
            cost = (COST * (tgt - val).abs().sum(1)) * trig; val = torch.where(trig[:, None], tgt * (1 - (cost / V.clamp(min=1e-12)))[:, None], val)
            last = torch.where(trig, torch.full_like(last, d), last); nreb += trig
        if d % 252 == 251:                                                    # year-end tax
            net = gains + carry; tax = taxr * net.clamp(min=0); carry = net.clamp(max=0); gains.zero_()
            V = val.sum(1); f = (tax / V.clamp(min=1e-12)).clamp(0, 1); val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]; taxpaid += tax / infl
            if skim is not None:                                               # skim real value above (1 + skim) x start as a bonus
                V = val.sum(1); bonus = ((V / infl - (1 + skim)).clamp(min=0) * infl).clamp(max=V)
                f = (bonus / V.clamp(min=1e-12)).clamp(0, 1); gains += ((val - basis) * f[:, None]).sum(1); val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]
                inc[:, min(yi, YEARS - 1)] += bonus / infl
            yi += 1
            real = val.sum(1) / infl; lowyear = torch.minimum(lowyear, real)
        real = val.sum(1) / infl; minreal = torch.minimum(minreal, real)
    real_end = (val.sum(1) / infl).view(C, K, P).cpu().numpy(); mn = minreal.view(C, K, P).cpu().numpy()
    if full: return dict(real_end=real_end, minreal=mn, inc=inc.view(C, K, P, YEARS).cpu().numpy(), reb=(nreb.view(C, K, P).mean(2) / YEARS).cpu().numpy(), dead=dead.view(C, K, P).float().mean(2).cpu().numpy())
    return real_end, mn, (nreb.view(C, K, P).mean(2) / YEARS).cpu().numpy(), dead.view(C, K, P).float().mean(2).cpu().numpy()
def eq_rate(rates, q_end):                                                    # rate where quantile of real ending value crosses 1.0
    r = np.array(rates, float); y = np.array(q_end) - 1.0
    for i in range(len(r) - 1):
        if y[i] >= 0 > y[i + 1]: return r[i] + (r[i + 1] - r[i]) * y[i] / (y[i] - y[i + 1])
    return r[-1] if y[-1] >= 0 else (r[0] if y[0] < 0 else float("nan"))
def summarize(rules, rates, real_end, mn, nreb, dead):
    out = []
    for c, ru in enumerate(rules):
        p10 = [np.percentile(real_end[c, k], 10) for k in range(len(rates))]; p50 = [np.median(real_end[c, k]) for k in range(len(rates))]
        e90 = eq_rate(rates, p10); e50 = eq_rate(rates, p50)
        k = int(np.argmin(np.abs(np.array(rates) - e90))); dip = np.percentile(mn[c, k], 10)
        out.append(dict(rule=ru["name"], eq90=e90, eq50=e50, dip10=float(dip), reb=float(nreb[c, k]), dead=float(dead[c].max()), **{k2: v for k2, v in ru.items() if k2 != "name"}))
    return out
def grid():
    R_ = [dict(name="yearly + 2x valve (current)", yearly=True, valve=2.0), dict(name="yearly, no valve", yearly=True)]
    for b in (4, 5, 6, 7, 8, 10, 12):
        for gname, gd in (("0", 0), ("6m", 126), ("1y", 252), ("18m", 378)):
            for v in (1.75, 2.0, 2.5, 3.0, None):
                d = dict(name=f"band ±{b}pp, min {gname}, " + (f"valve {v}x" if v else "no valve"), band=b, gap=gd)
                if v: d["valve"] = v
                R_.append(d)
    return R_
if __name__ == "__main__":
    t0 = time.time(); rules = grid(); rates = [3, 4, 5, 6, 7, 8, 9]
    IDX = make_idx(int(os.environ.get("SEED", "7"))); print(f"{len(rules)} rules x {len(rates)} rates x {IDX.shape[0]} {'historical windows' if os.environ.get('HIST') else 'bootstrap histories'}, {YEARS}y, tax {TAXR*100:.0f}%, MF haircut {HAIR*100:.0f}%", flush=True)
    res = []; CH = int(os.environ.get("CHUNK_RULES", "36"))
    for i in range(0, len(rules), CH):
        out = simulate(rules[i:i + CH], rates, IDX); res += summarize(rules[i:i + CH], rates, *out); print(f"  {i + CH}/{len(rules)} ({time.time()-t0:.0f}s)", flush=True)
    res.sort(key=lambda x: -x["eq90"])
    print(f"\n{'rule':34} | equilibrium rate: 90% of histories  50% | real value dip (p10) | rebalances/yr")
    for x in res[:25] + [x for x in res if "current" in x["rule"] or x["rule"] == "yearly, no valve"]:
        print(f"{x['rule']:34} |                 {x['eq90']:5.2f}%      {x['eq50']:5.2f}% |   {x['dip10']*100:5.1f}% of start   | {x['reb']:.2f}")
    json.dump(res, open(os.environ.get("OUT", "equilibrium_grid.json"), "w"), indent=1)
