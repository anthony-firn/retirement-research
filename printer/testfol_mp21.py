"""testfol.io check of MP-2 vs MP-2.1 (the part testfol can model: same funds, the 4x valve as Yearly + 300% band vs 2x as Yearly +
100% band, $50k living off the $240/month base, inflation-adjusted). testfol has no guardrail, bonus bucket or taxes, and no IAUM
backfill (real IAUM from 2021). Writes results/testfol_mp21.json and results/link_mp2_vs_mp21.txt.  Usage: python3 printer/testfol_mp21.py"""
import os, json, sys, zlib, base64, urllib.parse, urllib.request
MP2 = {"DBMFSIM": 27, "VBRSIM": 27, "GDESIM": 21, "KMLMSIM": 15, "GLDSIM": 8, "TQQQSIM": 2}
def bt(alloc, rel): return {"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": alloc, "absolute_dev": 0, "relative_dev": rel}
def call(backtests, start="1990-01-01", end="2026-10-20", sv=50000, cf=0, infl=False):
    body = {"start_date": start, "end_date": end, "start_val": sv, "adj_inflation": False, "cashflow": cf, "cashflow_freq": "Monthly", "rolling_window": 60,
            "adjust_cashflows_for_inflation": infl, "backtests": backtests}
    r = urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    return json.load(urllib.request.urlopen(r, timeout=300))
MP2 = {"DBMFSIM": 27, "VBRSIM": 27, "GDESIM": 21, "KMLMSIM": 15, "GLDSIM": 8, "TQQQSIM": 2}
MP21 = {"DBMFSIM": 27, "VBRSIM": 27, "GDESIM": 21, "KMLMSIM": 15, "IAUM": 8, "TQQQSIM": 2}
MP21_sim = dict(MP2)                                     # testfol has no IAUM backfill: full window uses GLDSIM for both
def show(title, d, names):
    print(f"\n{title}  ({d['start_date']} -> {d['end_date']}; limiting ticker {d.get('limiting_ticker')})")
    print(f"  {'':34} {'CAGR':>7} {'max DD':>8} {'Sharpe':>7} {'Ulcer':>6} {'end value':>11}")
    h = d["charts"]["history"]
    for i, (n, s) in enumerate(zip(names, d["stats"])):
        print(f"  {n:34} {s['cagr']:6.2f}% {s['max_drawdown']:7.1f}% {s['sharpe']:7.3f} {s['ulcer_index']:6.2f} {h[i + 1][-1]:>11,.0f}")
    return d
out = {}
names = ["MP-2 (2x valve: Yearly + 100% band)", "MP-2.1 (4x valve: Yearly + 300% band)"]
out["full_nowd"] = show("Full window, $50k, no withdrawals (portfolio only)", call([bt(MP2, 100), bt(MP21_sim, 300)]), names)
out["full_wd"] = show("Full window, $50k, living off $240/month (inflation-adjusted)", call([bt(MP2, 100), bt(MP21_sim, 300)], cf=-240, infl=True), names)
names2 = ["MP-2 (GLD, 2x valve)", "MP-2.1 (IAUM, 4x valve)", "MP-2 with IAUM only (2x valve)"]
out["iaum_wd"] = show("Since IAUM existed, $50k, living off $240/month", call([bt(MP2, 100), bt(MP21, 300), bt(dict(MP21), 100)], cf=-240, infl=True), names2)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "testfol_mp21.json"), "w"), indent=1, default=str)
def pf(name, alloc, rel):
    return {"name": name, "tickers": [{"ticker": t, "percent": w} for t, w in alloc.items()], "investDividends": True, "rebalanceFreq": "Yearly", "rebalanceOffset": 0,
            "drag": 0, "absoluteDev": 0, "relativeDev": rel, "rebalanceBandMode": "SYMMETRIC", "absoluteDevBelow": 0, "absoluteDevAbove": 0, "relativeDevBelow": 0, "relativeDevAbove": 0}
def link(pfs, start_val=50000, wd=240):
    gp = {"start_date": "", "end_date": "", "start_val": start_val, "adj_inflation": False, "adjust_cashflows_for_inflation": bool(wd), "annual_cashflow_growth_rate": 0,
          "target_currency": "USD", "cashflow": -wd, "cashflow_freq": "Monthly", "cashflow_offset": 0, "match_first_portfolio_income_cashflows": False,
          "one_time_cashflows": [], "rolling_window": 60, "withdrawal_surface_include": False, "withdrawal_surface_projection": "NONE",
          "withdrawal_surface_projection_min_years": 10, "withdrawal_surface_start_years": 5, "withdrawal_surface_end_years": 50, "withdrawal_surface_step_years": 1, "cashflow_legs": []}
    d = base64.b64encode(zlib.compress(json.dumps({"globalParams": gp, "portfolios": pfs, "glidePortfolios": []}, separators=(",", ":")).encode(), 9)).decode()
    return "https://testfol.io/?d=" + urllib.parse.quote(d, safe="")
L1 = link([pf("MP-2", MP2, 100), pf("MP-2.1 (testfol part: 4x valve)", MP21_sim, 300)])
L2 = link([pf("MP-2 (GLD)", MP2, 100), pf("MP-2.1 (IAUM, 4x valve)", MP21, 300)])
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "link_mp2_vs_mp21.txt"), "w").write(f"Full window (2000-), $50k, $240/month inflation-adjusted:\n{L1}\n\nSince IAUM (2021-), real IAUM:\n{L2}\n")
print("\nLINK1", L1); print("\nLINK2", L2)
