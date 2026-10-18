"""Validation gates for the engine.
1. Engine (fed testfol's cached series) vs testfol.io's own stats for lineup portfolios  -> engine correctness
2. Our own SIM recipes vs testfol's SIM series                                           -> data correctness"""
import json, os, sys, numpy as np, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from engine.backtest import backtest
from engine import sims, store
ROOT = os.path.dirname(os.path.abspath(__file__))

def gate1():
    V = json.load(open(os.path.join(ROOT, "..", "lab", "verify_frontier_etf.json")))
    print("Gate 1: engine vs testfol.io (1987-12-31 -> 2026-10-16, yearly rebalance)")
    print(f"  {'portfolio':9} | {'CAGR eng/tf':>14} | {'MDD eng/tf':>14} | {'Sharpe eng/tf':>14} | {'Ulcer eng/tf':>13}")
    worst = 0
    for n, alloc in V["portfolios"].items():
        if any(k not in store._testfol() for k in alloc): continue
        r = backtest({"start_date": "1987-12-31", "end_date": "2026-10-16", "start_val": 10000, "backtests": [{"allocation": alloc, "rebalance_freq": "Yearly"}]})
        e = r["stats"][0]; t = V["testfol"][n]["full"]; worst = max(worst, abs(e["cagr"] - t["cagr"]))
        print(f"  {n:9} | {e['cagr']:6.2f}/{t['cagr']:6.2f} | {e['max_drawdown']:6.2f}/{t['mdd']:6.2f} | {e['sharpe']:6.3f}/{t['sharpe']:6.3f} | {e['ulcer_index']:5.2f}/{t['ulcer']:5.2f}")
    print(f"  worst CAGR gap: {worst:.3f} pts/yr")

def gate2():
    tf = store._testfol()
    print("\nGate 2: our own SIM recipes vs testfol SIM series (annualised return by period)")
    for name, fn in sims.RECIPES.items():
        t, v = fn(); T, Vt = np.array(tf[name]["t"]), np.array(tf[name]["v"])
        common = np.intersect1d(t, T); a = np.array(v)[np.searchsorted(t, common)]; b = Vt[np.searchsorted(T, common)]
        yrs = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in common])
        print(f"  {name}: {dt.datetime.fromtimestamp(common[0], dt.UTC).date()} -> {dt.datetime.fromtimestamp(common[-1], dt.UTC).date()}")
        for lo, hi in ((1927, 1949), (1950, 1969), (1970, 1991), (1992, 2000), (2001, 2026)):
            m = (yrs >= lo) & (yrs <= hi)
            if m.sum() < 200: continue
            i, j = np.flatnonzero(m)[[0, -1]]; ya = (j - i) / 252
            ca = ((a[j] / a[i]) ** (1 / ya) - 1) * 100; cb = ((b[j] / b[i]) ** (1 / ya) - 1) * 100
            ra = np.diff(np.log(a[i:j + 1])); rb = np.diff(np.log(b[i:j + 1]))
            print(f"    {lo}-{hi}: ours {ca:6.2f}%  testfol {cb:6.2f}%  gap {ca-cb:+5.2f}  daily corr {np.corrcoef(ra, rb)[0,1]:.4f}")

if __name__ == "__main__":
    gate1(); gate2()
