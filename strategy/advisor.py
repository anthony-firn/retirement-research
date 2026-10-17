"""Daily portfolio advisor.

Given your situation and today's testfol.io data, recommends a lineup-tier blend from the optimised
switching strategy for your loss budget, and prints what to SELL and BUY.

Usage:
  python3 advisor.py --age 35 --value 250000 --peak 260000 --contrib 20000 --retire-age 55 --spending 70000 \
                     --holdings holdings.json [--refresh] [--budget 20]
holdings.json: {"KMLM": 50000, "IEI": 80000, ...}   (real tickers, $ market value; "CASH" allowed)
Not financial advice: research tool built on backtests of simulated history.
"""
import argparse, json, os, sys, math, subprocess, datetime as dt
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
PF = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
REAL = lambda t: t.replace("SIM", "") if t not in ("REITSIM",) else "VNQ"
STRATS = os.path.join(ROOT, "v2_guar.json")

def loss_budget(age, value, contrib, retire_age, spending, other_income=0.0, swr=0.04):
    """Map life stage to a max-drawdown budget (%)."""
    need = max(spending - other_income, 0) / swr                       # nest egg in today's dollars
    funded = value / need if need > 0 else 99
    years = max(retire_age - age, 0)
    if funded >= 1.0 or years == 0:                                    # living off it (or could): protect it
        b = 8 if funded < 1.5 else 10 if funded < 2.5 else 15         # more surplus -> can afford a bit more
        stage = "retired / fully funded"
    else:
        b = min(40, 8 + 1.0 * years)                                   # accumulator: time + contributions absorb losses
        if years <= 5: b = min(b, 12); stage = "pre-retirement (<= 5 years)"
        else: stage = "accumulating"
    return b, dict(nest_egg=need, funded=funded, years=years, stage=stage)

def pick_strategy(budget):
    S = json.load(open(STRATS))["budgets"]
    avail = sorted(int(k) for k in S)
    k = max([b for b in avail if b <= budget] or [avail[0]])
    return k, S[str(k)]

def today_state(params, value_ratio):
    """Recompute today's indicators + governor exactly like the backtest engine (CPU)."""
    os.environ["DEVICE"] = "cpu"
    sys.path.insert(0, ROOT); import gpu_strategy as gs, torch
    d = gs.T - 1; K = gs.K; p = params
    stress = np.maximum(gs.STRESS_DAY[:K], gs.STRESS_WEEK[:K] / p["WEEKF"]) * p["M"]; stress = np.maximum.accumulate(stress)
    dd = max(0.0, 1 - value_ratio) * 100; cushion = max(p["L"] - dd, 0)
    k = int((stress <= cushion).sum()) - 1
    if k < 0: gov = 0.0
    else:
        nxt = stress[k + 1] if k + 1 < K else stress[k] + 1e9
        gov = min(k + max(0.0, min(1.0, (cushion - stress[k]) / max(nxt - stress[k], 1e-6))), K - 1)
    sig = {}
    if p["SMA"] >= 0 and p["S_TREND"] > 0: sig[f"S&P below {gs.SMA_N[p['SMA']]}-day average"] = (bool(gs.SMA_FLAGS[p["SMA"], d]), p["S_TREND"])
    if p["VOL"] > 0 and p["S_VOL"] > 0: sig[f"S&P 20-day volatility > {p['VOL']}% (now {float(gs.RVOL[d]):.1f}%)"] = (float(gs.RVOL[d]) > p["VOL"], p["S_VOL"])
    if p["VIXL"] > 0 and p["S_VIX"] > 0: sig[f"VIX > {p['VIXL']} (now {float(gs.VIXT[d]):.1f})"] = (float(gs.VIXT[d]) > p["VIXL"], p["S_VIX"])
    rate_on = p["RATE"] < 0 and float(gs.IEF63[d]) < p["RATE"]
    if p["RATE"] < 0 and (p["S_RATE"] > 0 or p["HEDGE"]): sig[f"Rate shock: IEF 3-month return < {p['RATE']}% (now {float(gs.IEF63[d]):.1f}%)"] = (rate_on, p["S_RATE"])
    steps = sum(s for on, s in sig.values() if on)
    target = max(0.0, min(min(p["B"], gov) - steps, K - 1))
    return dict(date=gs.DATES[d], dd=dd, cushion=cushion, governor=gov, signals=sig, steps=steps, target=target, rate_on=rate_on,
                ladder=gs.LADDER, hedged=gs.HEDGED)

def blend_weights(st, params):
    lo = int(math.floor(st["target"])); f = st["target"] - lo; hi = min(lo + 1, len(st["ladder"]) - 1)
    names = [st["ladder"][lo], st["ladder"][hi]]
    if params["HEDGE"] and st["rate_on"]: names = [st["hedged"].get(n, n) for n in names]
    w = {}
    for name, frac in ((names[0], 1 - f), (names[1], f)):
        for t, x in PF[name]["alloc"].items(): w[REAL(t)] = w.get(REAL(t), 0) + frac * x / 100
    return names, f, {k: v for k, v in sorted(w.items(), key=lambda kv: -kv[1]) if v > 1e-6}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", type=float, required=True); ap.add_argument("--value", type=float, required=True)
    ap.add_argument("--peak", type=float, help="highest value this account has reached (default: --value)")
    ap.add_argument("--contrib", type=float, default=0); ap.add_argument("--retire-age", type=float, default=65)
    ap.add_argument("--spending", type=float, default=0, help="yearly spending need in retirement (today's $)")
    ap.add_argument("--other-income", type=float, default=0); ap.add_argument("--holdings", help="json of current $ per ticker")
    ap.add_argument("--budget", type=float, help="override max-drawdown budget (%)"); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.refresh: subprocess.run([sys.executable, os.path.join(ROOT, "fetch_data.py")], check=True)
    b, info = loss_budget(a.age, a.value, a.contrib, a.retire_age, a.spending, a.other_income)
    if a.budget: b = a.budget
    kb, S = pick_strategy(b); p = S["params"]
    st = today_state(p, a.value / (a.peak or a.value))
    names, f, w = blend_weights(st, p)
    print(f"=== Advisor  (testfol data through {st['date']}) ===")
    print(f"Life stage: {info['stage']} | years to retirement {info['years']:.0f} | nest egg needed ${info['nest_egg']:,.0f} | funded {info['funded']*100:.0f}%")
    print(f"Loss budget: {b:.0f}% -> strategy for {kb}% budget (backtest 1988-2026: CAGR {S['metrics']['full']['cagr']:.2f}%, max DD {S['metrics']['full']['mdd']:.1f}%, "
          f"2007-26 CAGR {S['metrics']['oos']['cagr']:.2f}%)")
    print(f"Drawdown guard: account {st['dd']:.1f}% below peak, cushion {st['cushion']:.1f}% -> can afford up to tier {st['governor']:.2f} ({st['ladder'][int(st['governor'])]})")
    for k, (on, s) in st["signals"].items(): print(f"  signal {'ON ' if on else 'off'}  {k}  (step down {s})")
    print(f"Recommended: tier {st['target']:.2f} = {1-f:.0%} {names[0]} + {f:.0%} {names[1]}")
    print("Target weights: " + ", ".join(f"{t} {x*100:.1f}%" for t, x in w.items()))
    if a.holdings:
        H = json.load(open(a.holdings)); tot = sum(H.values())
        print(f"\nTrades for ${tot:,.0f} account (sell first, then buy):")
        rows = []
        for t in sorted(set(H) | set(w)):
            delta = w.get(t, 0) * tot - H.get(t, 0)
            if abs(delta) >= max(50, 0.002 * tot): rows.append((t, delta))
        for t, dlt in sorted(rows, key=lambda x: x[1]): print(f"  {'SELL' if dlt < 0 else 'BUY ':4} {t:6} ${abs(dlt):>12,.0f}")
        if not rows: print("  none - already within tolerance")
    print("\nResearch tool, not financial advice. Switching realises gains: best used in a tax-advantaged account.")

if __name__ == "__main__":
    main()
