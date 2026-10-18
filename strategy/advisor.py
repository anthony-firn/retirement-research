"""Daily portfolio advisor (uses policy.py - the same rules as the backtests).

  python3 advisor.py --age 40 --value 250000 --peak 262000 --contrib 20000 --retire-age 60 --spending 70000 \
                     [--holdings holdings.json] [--refresh]
holdings.json: {"KMLM": 50000, "IEI": 80000, "CASH": 1000, ...}  real tickers, current $ market value.
--peak: the highest value this account has reached (drives the drawdown breaker). Default = --value.
Research tool built on backtests of partly simulated history - not financial advice.
"""
import argparse, json, os, sys, subprocess, math, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))

def market_context():
    I = json.load(open(os.path.join(ROOT, "data_indicators.json")))
    spy = np.array(I["SPYSIM"]["v"]); vix = np.array(I["VIXSIM"]["v"]) * 17.24; ief = np.array(I["IEFSIM"]["v"]); cpi = np.array(I["INFLATION"]["v"])
    lr = np.diff(np.log(spy[-21:])); vol = lr.std() * math.sqrt(252) * 100
    return {"S&P vs 200-day average": f"{(spy[-1] / spy[-200:].mean() - 1) * 100:+.1f}%", "S&P 20-day volatility": f"{vol:.1f}%",
            "VIX": f"{vix[-1]:.1f}", "IEF 3-month return (rate trend)": f"{(ief[-1] / ief[-64] - 1) * 100:+.1f}%",
            "CPI last 12 months": f"{(cpi[-1] / cpi[-253] - 1) * 100:.1f}%"}

def years_to_goal(value, contrib, egg, real_return):
    v, y = value, 0
    while v < egg and y < 60: v = v * (1 + real_return) + contrib; y += 1
    return y if v >= egg else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", type=float, required=True); ap.add_argument("--value", type=float, required=True)
    ap.add_argument("--peak", type=float); ap.add_argument("--contrib", type=float, default=0)
    ap.add_argument("--retire-age", type=float, default=65); ap.add_argument("--spending", type=float, default=0)
    ap.add_argument("--other-income", type=float, default=0); ap.add_argument("--holdings")
    ap.add_argument("--budget", type=float, help="override loss budget (%)")
    ap.add_argument("--max-drop", type=float, help="biggest drop (%%) you would sit through without selling (sets the comfort cap)"); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.refresh: subprocess.run([sys.executable, os.path.join(ROOT, "fetch_data.py")], check=True)
    sys.path.insert(0, ROOT); import policy as pl
    b, info = pl.life_budget(a.age, a.value, a.contrib, a.retire_age, a.spending, a.other_income, max_drop=a.max_drop)
    if a.budget: b = a.budget
    x_cap = pl.tier_for_budget(b); dd = max(0.0, 1 - a.value / (a.peak or a.value)) * 100
    x = pl.breaker(x_cap, dd, b); (lo, hi, f), w = pl.blend(x)
    # what this budget did historically (fixed budget, no cash flows)
    path = pl.simulate(0, 40, 30, 1.0, 0, 200, 0, fixed_budget=b); v = np.array([p[1] for p in path])
    cagr = ((v[-1] / v[0]) ** (252 / len(v)) - 1) * 100; mdd = (1 - v / np.maximum.accumulate(v)).max() * 100
    i07 = int(np.searchsorted(pl.DATES, "2007-01-01")); c07 = ((v[-1] / v[i07]) ** (252 / (len(v) - i07)) - 1) * 100
    print(f"=== Advisor  (testfol.io data through {pl.DATES[-1]}) ===")
    print(f"You: {info['stage']}, {info['years']:.0f} years to planned retirement, nest egg needed ${info['nest_egg']:,.0f}, funded {info['funded']*100:.0f}%")
    print(f"Loss budget: {b:.0f}% (comfort cap {info['cap']:.0f}%)  ->  breaker at {b - pl.MARGIN_GAP:.0f}% below your peak (checked daily)")
    print(f"This budget 1988-2026: CAGR {cagr:.1f}% (since 2007: {c07:.1f}%), max drawdown {mdd:.1f}%, breaker never triggered")
    if info["stage"] == "accumulating" and a.spending:
        real = max(c07 - 3.0, 0.5) / 100                                     # conservative: post-2007 return minus ~3% inflation
        y = years_to_goal(a.value, a.contrib, info["nest_egg"], real)
        if y is not None: print(f"Projection (conservative {real*100:.1f}% real): nest egg in ~{y} years -> age {a.age + y:.0f}")
    print(f"Account drawdown: {dd:.1f}% below peak -> " + ("breaker not engaged" if x >= x_cap - 1e-6 else f"BREAKER ENGAGED: risk cut from tier {x_cap:.2f} to {x:.2f}"))
    print(f"\nRECOMMENDED: {1-f:.0%} {lo}" + (f" + {f:.0%} {hi}" if f > 0.005 else ""))
    print("Target weights: " + ", ".join(f"{t} {x_*100:.1f}%" for t, x_ in w.items()))
    print("\nMarket context (informational - timing signals were tested and did not help out-of-sample):")
    for k, v_ in market_context().items(): print(f"  {k}: {v_}")
    if a.holdings:
        H = json.load(open(a.holdings)); tot = sum(H.values()); rows = []
        for t in sorted(set(H) | set(w)):
            dlt = w.get(t, 0) * tot - H.get(t, 0)
            if abs(dlt) >= max(50, 0.002 * tot): rows.append((t, dlt))
        print(f"\nTrades for your ${tot:,.0f} (do the SELLs first, then the BUYs):")
        for t, dlt in sorted(rows, key=lambda r: r[1]): print(f"  {'SELL' if dlt < 0 else 'BUY '} {t:6} ${abs(dlt):>12,.0f}   ({abs(dlt)/tot*100:4.1f}% of account)")
        if not rows: print("  none - already on target")
    print("\nRe-run daily (or after any big market day). Best in a tax-advantaged account. Not financial advice.")

if __name__ == "__main__":
    main()
