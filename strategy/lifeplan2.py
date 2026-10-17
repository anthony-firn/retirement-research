"""Life-plan backtests of the policy vs fixed portfolios, over every historical start (quarterly) 1988-2026.
Accumulators: years until the nest egg (spending/4%, real $) is reached. Retirees: survival + lowest real value.
All returns: testfol.io daily data of the lineup portfolios. Inflation: testfol CPI."""
import json, os, numpy as np
import policy as pl

I = json.load(open(os.path.join(pl.ROOT, "data_indicators.json")))
t = np.array(pl.D["t"]); ci = np.array(I["INFLATION"]["t"]); cv = np.array(I["INFLATION"]["v"])
CPI = cv[np.clip(np.searchsorted(ci, t, side="right") - 1, 0, None)]
starts = [i for i in range(len(pl.DATES)) if i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])]

PROFILES = {
    "Age 25, $20k, +$12k/yr, wants $60k/yr": dict(age=25, value=20000, contrib=12000, retire_age=60, spending=60000),
    "Age 40, $250k, +$20k/yr, wants $70k/yr": dict(age=40, value=250000, contrib=20000, retire_age=60, spending=70000),
    "Age 55, $800k, +$25k/yr, wants $70k/yr": dict(age=55, value=800000, contrib=25000, retire_age=65, spending=70000),
}
FIXED = {"Policy (glide path + breaker)": None, "Always S12+ (b=25)": 25, "Always E10 (b=20)": 20, "Always E14/E15 (b=40)": 40}

def years_to_goal(path, egg):
    for d, real_v, x, b in path:
        if real_v >= egg: return (np.searchsorted(pl.DATES, d) - np.searchsorted(pl.DATES, path[0][0])) / 252
    return None

if __name__ == "__main__":
    out = {}
    for pname, p in PROFILES.items():
        egg = p["spending"] / 0.04; print(f"\n{pname}  -> nest egg ${egg:,.0f} (today's $)")
        print(f"  {'approach':32} | reached goal | median yrs | worst yrs | max real drawdown seen")
        for fname, fb in FIXED.items():
            yrs = []; worst_dd = 0; n = 0
            for s in starts:
                path = pl.simulate(s, 45, p["age"], p["value"], p["contrib"], 200, p["spending"], cpi=CPI, fixed_budget=fb) if fb else \
                       pl.simulate(s, 45, p["age"], p["value"], p["contrib"], p["retire_age"], p["spending"], cpi=CPI)
                y = years_to_goal(path, egg); n += 1
                v = np.array([q[1] for q in path]); worst_dd = max(worst_dd, (1 - v / np.maximum.accumulate(v)).max() * 100)
                if y is not None: yrs.append(y)
                elif (len(pl.DATES) - s) / 252 < 15: n -= 1                     # too little history to judge
            if yrs: print(f"  {fname:32} | {len(yrs):>3}/{n:<3}      | {np.median(yrs):9.1f} | {max(yrs):8.1f} | {worst_dd:6.1f}%")
            out.setdefault(pname, {})[fname] = dict(reached=len(yrs), n=n, median=float(np.median(yrs)) if yrs else None, worst=float(max(yrs)) if yrs else None, max_real_dd=worst_dd)
    # retiree
    print("\nRetired at 65 with $1.5M, spending $60k/yr inflation-adjusted (4%), 25-year windows")
    print(f"  {'approach':32} | survived | lowest real value | median real value after 25y")
    for fname, fb in {"Policy (retiree budget)": None, "Always C1-Now (b=10)": 10, "Always S12+ (b=25)": 25, "Always MinRisk (b=6)": 6}.items():
        res = []
        for s in starts:
            if (len(pl.DATES) - s) / 252 < 25: break
            path = pl.simulate(s, 25, 65, 1500000, 0, 65, 60000, cpi=CPI, fixed_budget=fb)
            v = np.array([q[1] for q in path]); res.append((v.min(), v[-1] if len(path) >= 25 * 252 - 5 else 0))
        surv = sum(1 for lo, end in res if end > 0)
        print(f"  {fname:32} | {surv:>3}/{len(res):<3}  | ${min(r[0] for r in res):>12,.0f}   | ${np.median([r[1] for r in res]):>12,.0f}")
        out.setdefault("retiree", {})[fname] = dict(survived=surv, n=len(res), lowest=float(min(r[0] for r in res)), median_end=float(np.median([r[1] for r in res])))
    json.dump(out, open(os.path.join(pl.ROOT, "lifeplan_results.json"), "w"), indent=1)
