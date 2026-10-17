"""Life-plan backtest: how the switching strategies would have treated a real investor, using the
strategy's daily path on testfol.io data (1988-2026) with monthly contributions / withdrawals.

For every historical start month it answers:
  accumulating -> years until the account reaches the nest egg (spending / SWR, inflation-adjusted)
  retired      -> did the money last N years with inflation-adjusted withdrawals? lowest real value reached?
Usage: python3 lifeplan.py --value 250000 --contrib 20000 --spending 70000 [--retired --years 30]
"""
import argparse, json, os, numpy as np
os.environ.setdefault("DEVICE", "cpu")
import gpu_strategy as gs, torch

ROOT = gs.ROOT
CPI = gs.align("INFLATION")

def strategy_paths(source="v2_guar.json"):
    S = json.load(open(os.path.join(ROOT, source)))["budgets"]
    keys = sorted(S, key=int); rows = [{k: gs.SPACE[k].index(S[b]["params"][k]) for k in gs.KEYS} for b in keys]
    P = {k: torch.tensor([r[k] for r in rows], device=gs.DEV) for k in gs.KEYS}
    m = gs.run(P, keep_tiers=True)
    return {int(b): dict(nav=m["nav"][:, i].cpu().numpy(), tier=m["tiers"][:, i].cpu().numpy(), params=S[b]["params"]) for i, b in enumerate(keys)}

def month_starts():
    ym = np.array([d[:7] for d in gs.DATES]); return np.r_[0, np.flatnonzero(ym[1:] != ym[:-1]) + 1]

def accumulate(nav, value, contrib, nest_egg, max_years=40):
    """Years to reach nest egg (real terms) for every start month. Contributions grow with CPI."""
    ms = month_starts(); out = []
    for s in ms:
        v = value; real_target = nest_egg; reached = None
        for j, (a, b) in enumerate(zip(ms[ms >= s][:-1], ms[ms >= s][1:])):
            infl = CPI[a] / CPI[s]
            v = v * nav[b] / nav[a] + contrib / 12 * infl
            if v / infl >= real_target: reached = (j + 1) / 12; break
            if j + 1 >= max_years * 12: break
        out.append((gs.DATES[s], reached, (len(ms[ms >= s]) - 1) / 12))
    return out

def retire(nav, value, spending, years):
    """Inflation-adjusted withdrawals for `years` from each start month that has enough history."""
    ms = month_starts(); res = []
    for k, s in enumerate(ms):
        seq = ms[k:k + years * 12 + 1]
        if len(seq) < years * 12 + 1: break
        v = value; lowest = value; ok = True
        for a, b in zip(seq[:-1], seq[1:]):
            infl = CPI[a] / CPI[s]; v = v * nav[b] / nav[a] - spending / 12 * infl
            lowest = min(lowest, v / (CPI[b] / CPI[s]))
            if v <= 0: ok = False; break
        res.append((gs.DATES[s], ok, lowest, v / (CPI[seq[-1]] / CPI[s]) if ok else 0))
    return res

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--value", type=float, default=250000); ap.add_argument("--contrib", type=float, default=20000)
    ap.add_argument("--spending", type=float, default=70000); ap.add_argument("--swr", type=float, default=0.04)
    ap.add_argument("--retired", action="store_true"); ap.add_argument("--years", type=int, default=30)
    a = ap.parse_args(); paths = strategy_paths()
    if not a.retired:
        egg = a.spending / a.swr
        print(f"Accumulating: ${a.value:,.0f} now, +${a.contrib:,.0f}/yr (inflation-indexed), target ${egg:,.0f} (today's $)")
        print(f"{'budget':>6} {'CAGR':>6} {'MDD':>6} | years to goal: median  worst  (start months that reached it within their history)")
        for b, p in paths.items():
            r = accumulate(p["nav"], a.value, a.contrib, egg)
            yrs = [x[1] for x in r if x[1] is not None]; done = [x for x in r if x[1] is not None or x[2] >= 40]
            nv = p["nav"]; cagr = ((nv[-1] / nv[0]) ** (252 / len(nv)) - 1) * 100; mdd = (1 - nv / np.maximum.accumulate(nv)).max() * 100
            if yrs: print(f"{b:>5}% {cagr:6.2f} {mdd:6.1f} | {np.median(yrs):6.1f} {max(yrs):6.1f}   ({len(yrs)} of {len(r)} start months reached the goal)")
    else:
        print(f"Retired: ${a.value:,.0f}, withdrawing ${a.spending:,.0f}/yr inflation-indexed for {a.years} years")
        for b, p in paths.items():
            r = retire(p["nav"], a.value, a.spending, a.years)
            if not r: print(f"{b:>5}%: not enough history for {a.years}-year windows"); continue
            fails = sum(1 for x in r if not x[1]); lo = min(x[2] for x in r)
            print(f"{b:>5}% | survived {len(r)-fails}/{len(r)} start months | lowest real value {lo:,.0f} | median ending real value {np.median([x[3] for x in r]):,.0f}")
