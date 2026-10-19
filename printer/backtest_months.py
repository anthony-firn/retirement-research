"""Month-by-month history of a printer run through the operator rules on actual daily prices.
python3 printer/backtest_months.py [--printer MP-2] [--start 2025-10-17] [--value 50000]
Prices = each fund's total-return index (dividends reinvested), inflation = CPI-U; IRA-style (taxes estimated, not deducted)."""
import os, sys, json, argparse, datetime as dt, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--printer", default="MP-2"); ap.add_argument("--start", default="2025-10-17"); ap.add_argument("--value", type=float, default=50000)
ap.add_argument("--tax", default="retiree, not working"); a = ap.parse_args(); sys.argv = [sys.argv[0]]
import money_printer as mp, operate as op
cfg = op.PRINTERS[a.printer]; S = cfg["settings"]; tick = list(cfg["targets"])
dates = [dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in mp.h.CAL]; i0 = int(np.searchsorted(np.array(dates), a.start))
lvl = {t: np.cumprod(1 + mp.fund_returns(t + "SIM")) for t in tick}; cpi = np.asarray(mp.h.cpi, float); rf = np.asarray(mp.RF)
d0 = dates[i0]; V0 = a.value
st = dict(printer=a.printer, targets=cfg["targets"], settings=S, baseline=dict(start_value=V0, start_cpi=cpi[i0], start_date=d0),
          holdings={t: {"shares": V0 * w / 100 / lvl[t][i0], "lots": [dict(shares=V0 * w / 100 / lvl[t][i0], cost=lvl[t][i0], date=d0)]} for t, w in cfg["targets"].items()},
          cash_bucket=0.0, guardrail_mult=1.0, last_rebalance=d0, last_month_paid=d0[:7], last_year_end=int(d0[:4]), log=[])
rows = []; total = 0.0
print(f"{a.printer} printer, ${V0:,.0f} invested {d0}, following the operator rules through {dates[-1]} (actual prices, dividends reinvested)\n")
print(f"{'month':8} {'paid on':11} {'base print':>11} {'bonus':>8} {'SPENT':>9} | {'account after':>14} {'real vs start':>13} | events")
for d in range(i0 + 1, len(dates)):
    st["cash_bucket"] *= 1 + rf[d]
    prices = {t: float(lvl[t][d]) for t in tick}; p = op.plan(st, dates[d], prices, float(cpi[d]))
    if not p["steps"]: continue
    ev = [s["step"] for s in p["steps"] if s["step"] != "MONTHLY PRINT"]
    mp_ = [s for s in p["steps"] if s["step"] == "MONTHLY PRINT"]
    gains_before = st.get("realized_gains_by_year", {}).get(dates[d][:4], 0.0)
    st = op.apply(st, p, dates[d], a.tax); st["log"] = []
    V = op.value(st, prices)
    if mp_:
        s = mp_[0]; total += s["spend"]
        sold = ", ".join(f"{t} ${-x:,.0f}" for t, x in s["trades"].items())
        rows.append(dict(month=s["month"], date=dates[d], base=s["base"], bonus=s["bucket_draw"], spend=s["spend"], account=V, real=V / V0 / (cpi[d] / cpi[i0]), events=ev, sold=sold))
        print(f"{s['month']:8} {dates[d]:11} ${s['base']:>10,.0f} ${s['bucket_draw']:>7,.0f} ${s['spend']:>8,.0f} | ${V:>13,.0f} {V / V0 / (cpi[d] / cpi[i0]) * 100:12.0f}% | sold {sold}" + (f" | {', '.join(ev)}" if ev else ""))
    elif ev:
        print(f"{'':8} {dates[d]:11} {'':>11} {'':>8} {'':>9} | ${V:>13,.0f} {'':>13} | {', '.join(ev)}: " + "; ".join(s["why"][:90] for s in p["steps"]))
Vend = op.value(st, {t: float(lvl[t][-1]) for t in tick}) + st["cash_bucket"]
g = sum(st.get("realized_gains_by_year", {}).values())
print(f"\nTotal spent: ${total:,.0f} over {len(rows)} months (avg ${total / max(len(rows), 1):,.0f}/month) | account now ${Vend:,.0f} (started ${V0:,.0f}; "
      f"{Vend / V0 / (cpi[-1] / cpi[i0]) * 100:.0f}% of the start after inflation) | inflation over the period {(cpi[-1] / cpi[i0] - 1) * 100:.1f}% | realized gains ${g:,.0f}")
json.dump(dict(rows=rows, total=total, account_end=Vend), open(os.path.join(ROOT, "..", "results", f"backtest_months_{a.printer}_{a.start}.json"), "w"), indent=1, default=float)
