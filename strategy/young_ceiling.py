"""Age 30, $8k, +$15k/yr (two IRAs) to 65: does holding the ceiling tiers early, then gliding, beat the life-stage policy?
Every quarterly start 1972-1991 (35 years must fit in 1972-2026 data). Values in today's dollars."""
import os, sys, json, numpy as np
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import policy as pl
I = json.load(open(os.path.join(pl.ROOT, "data_indicators.json"))); ci = np.array(I["INFLATION"]["t"]); cv = np.array(I["INFLATION"]["v"])
T_ts = np.array(pl.D["t"]); CPI = cv[np.clip(np.searchsorted(ci, T_ts, side="right") - 1, 0, None)]
AGE, V0, C, RET_AGE = 30, 8000, 15000, 65
def static_then(start, tier, until_age):
    """hold `tier` statically (rebalanced daily, no breaker) until `until_age`, then hand over to the policy."""
    k = pl.LADDER.index(tier); v = V0; end = start + int((until_age - AGE) * 252); month = pl.DATES[start][:7]; low = 1.0; peak = v; worst = 0
    for d in range(start + 1, end):
        v *= 1 + pl.RET[d, k]
        if pl.DATES[d][:7] != month: month = pl.DATES[d][:7]; v += C / 12 * CPI[d] / CPI[start]
        peak = max(peak, v); worst = max(worst, 1 - v / peak)
    rv = v / (CPI[end] / CPI[start])
    if until_age >= RET_AGE: return rv, worst
    p = pl.simulate(end, RET_AGE - until_age, until_age, rv, C, RET_AGE, 70000)
    vv = np.array([x[1] for x in p]); w2 = (1 - vv / np.maximum.accumulate(vv)).max()
    return vv[-1], max(worst, w2)
yrs = np.array([int(d[:4]) for d in pl.DATES]); starts = [i for i in range(1, len(pl.DATES)) if pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i-1][:7] and yrs[i] <= 1991]
VAR = {"Policy (glide rule, budget 50 -> 25)": None, "S13.5 static all the way": ("S13.5", 65), "E20 to 45, then policy": ("E20", 45),
       "E24 to 45, then policy": ("E24", 45), "E24 to 40, then policy": ("E24", 40), "E24 all the way": ("E24", 65)}
print(f"Age {AGE}, ${V0:,} now, +${C:,}/yr real to {RET_AGE}. {len(starts)} quarterly starts {pl.DATES[starts[0]][:4]}-{pl.DATES[starts[-1]][:4]}. Real $ at 65:")
print(f"{'':38} {'worst':>10} {'p10':>10} {'median':>10} {'best':>10} | worst drawdown lived (median / max)")
for n, spec in VAR.items():
    res = []
    for s in starts:
        if spec is None:
            p = pl.simulate(s, RET_AGE - AGE, AGE, V0, C, RET_AGE, 70000); vv = np.array([x[1] for x in p]); res.append((vv[-1], (1 - vv / np.maximum.accumulate(vv)).max()))
        else: res.append(static_then(s, *spec))
    f = np.array([r[0] for r in res]); w = np.array([r[1] for r in res]) * 100
    print(f"{n:38} {f.min():10,.0f} {np.percentile(f,10):10,.0f} {np.median(f):10,.0f} {f.max():10,.0f} | {np.median(w):5.1f}% / {w.max():5.1f}%", flush=True)
