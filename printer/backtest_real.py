"""Month-by-month printer run with REAL ETF prices and REAL distributions (Yahoo close + dividends derived from adjusted close).
Shows per month: gross pulled out, tax set aside (the retiree's rates on realized gains + that month's fund distributions), net spendable,
and exact holdings (shares, value, weight) after the month's trades. Distributions are reinvested on the ex-date.
python3 printer/backtest_real.py [--printer MP-2] [--start 2025-10-17] [--value 50000] [--tax "retiree, not working"]"""
import os, sys, json, argparse, datetime as dt, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--printer", default="MP-2"); ap.add_argument("--start", default="2025-10-17"); ap.add_argument("--value", type=float, default=50000)
ap.add_argument("--tax", default="retiree, not working"); a = ap.parse_args(); sys.argv = [sys.argv[0]]
import operate as op, money_printer as mp
from engine.data import sources as src
cfg = op.PRINTERS[a.printer]; S = cfg["settings"]; tick = list(cfg["targets"]); R = op.TAXP[a.tax]
QUAL = {"VBR", "XLV", "VTI", "SPMO", "XLE", "XLP"}
day = lambda ts: dt.datetime.fromtimestamp(ts, dt.UTC).date().isoformat()
close, adj = {}, {}
for t in tick:
    ts, c = src.yahoo(t, field="close"); _, ac = src.yahoo(t, field="adjclose")
    close[t] = {day(x): float(v) for x, v in zip(ts, c) if v}; adj[t] = {day(x): float(v) for x, v in zip(ts, ac) if v}
dates = sorted(set.intersection(*[set(close[t]) for t in tick])); dates = [d for d in dates if d >= a.start]
DIVS = {t: {day(x): v for x, v in zip(*src.yahoo_dividends(t))} for t in tick}
def dividend(t, i): return DIVS[t].get(dates[i], 0.0)             # cash distribution per share going ex on dates[i]
cal = [day(x) for x in mp.h.CAL]; cpi_by = dict(zip(cal, np.asarray(mp.h.cpi, float))); rf_by = dict(zip(cal, np.asarray(mp.RF)))
def cpi_at(d): k = max(x for x in cpi_by if x <= d); return cpi_by[k]
d0 = dates[0]; V0 = a.value; px0 = {t: close[t][d0] for t in tick}
st = dict(printer=a.printer, targets=cfg["targets"], settings=S, baseline=dict(start_value=V0, start_cpi=cpi_at(d0), start_date=d0),
          holdings={t: {"shares": V0 * w / 100 / px0[t], "lots": [dict(shares=V0 * w / 100 / px0[t], cost=px0[t], date=d0)]} for t, w in cfg["targets"].items()},
          cash_bucket=0.0, guardrail_mult=1.0, last_rebalance=d0, last_month_paid=d0[:7], last_year_end=int(d0[:4]), log=[])
months = {}; m_dist = {}; lines = []
def M(d): return months.setdefault(d[:7], dict(gross=0.0, bonus=0.0, gain_tax=0.0, dist=0.0, dist_tax=0.0, gains=0.0, events=[], sold={}, divs={}))
for i in range(1, len(dates)):
    d = dates[i]; prices = {t: close[t][d] for t in tick}
    st["cash_bucket"] *= 1 + rf_by.get(d, 0.0)
    for t in tick:                                               # distributions: cash -> taxed -> reinvested
        D = dividend(t, i)
        if D > 0:
            h = st["holdings"][t]; cash = h["shares"] * D; h["shares"] += cash / prices[t]; h["lots"].append(dict(shares=cash / prices[t], cost=prices[t], date=d))
            rate = (R["lt"] if t in QUAL else R["ord"]) + R["ca"]; m = M(d); m["dist"] += cash; m["dist_tax"] += cash * rate; m["divs"][t] = m["divs"].get(t, 0) + cash
    p = op.plan(st, d, prices, cpi_at(d))
    if not p["steps"]: continue
    m = M(d)
    for s in p["steps"]:
        for t, dollars in s["trades"].items():
            if dollars < 0:
                picks, lt, stg, tax = op.tax_lots(st, t, -dollars, prices[t], d, a.tax); m["gain_tax"] += tax; m["gains"] += lt + stg
                if s["step"] == "MONTHLY PRINT": m["sold"][t] = m["sold"].get(t, 0) + (-dollars)
        if s["step"] == "MONTHLY PRINT": m["gross"] += s["spend"]; m["bonus"] += s["bucket_draw"]; m["paid_on"] = d
        else: m["events"].append(s["step"])
    st = op.apply(st, p, d, a.tax); st["log"] = []
    m["holdings"] = {t: dict(shares=st["holdings"][t]["shares"], price=prices[t], value=st["holdings"][t]["shares"] * prices[t]) for t in tick}
    m["account"] = op.value(st, prices); m["bucket"] = st["cash_bucket"]
# fill holdings for months that only had distributions after the last trade (end-of-month snapshot)
last = dates[-1]; prices = {t: close[t][last] for t in tick}
out = [f"# {a.printer} printer — ${V0:,.0f} invested {d0}, operator rules, real ETF prices and distributions, taxes at '{a.tax}' rates\n",
       "| Month | Paid on | GROSS pulled out | Tax set aside (gains + distributions) | NET spendable | Realized gains | Distributions received (reinvested) | Sold | Account after |", "|---|---|---|---|---|---|---|---|---|"]
tot = dict(gross=0, tax=0, net=0, dist=0)
for k in sorted(months):
    m = months[k]; tax = m["gain_tax"] + m["dist_tax"]; dv = ", ".join(f"{t} ${x:,.0f}" for t, x in m["divs"].items()) or "—"
    if "paid_on" not in m:
        if m["dist"] > 0: tot["tax"] += tax; tot["net"] -= tax; tot["dist"] += m["dist"]; out.append(f"| {k} | no print this month | — | ${tax:,.2f} (distributions) | −${tax:,.2f} | — | {dv} | — | — |")
        continue
    net = m["gross"] - tax; tot["gross"] += m["gross"]; tot["tax"] += tax; tot["net"] += net; tot["dist"] += m["dist"]
    out.append(f"| {k} | {m['paid_on']} | ${m['gross']:,.2f} | ${tax:,.2f} (${m['gain_tax']:,.2f} + ${m['dist_tax']:,.2f}) | **${net:,.2f}** | ${m['gains']:,.2f} | {dv} | "
               + ", ".join(f"{t} ${x:,.0f}" for t, x in m["sold"].items()) + f" | ${m['account']:,.0f}" + (f" ({', '.join(m['events'])})" if m["events"] else "") + " |")
out.append(f"| **Total** | | **${tot['gross']:,.2f}** | **${tot['tax']:,.2f}** | **${tot['net']:,.2f}** | | ${tot['dist']:,.0f} | | ${op.value(st, prices):,.0f} on {last} |")
out += ["\n## Exact holdings after each month's trades (shares / value / weight)", "| Month | " + " | ".join(tick) + " | Total |", "|---|" + "---|" * (len(tick) + 1)]
out.append(f"| start {d0} | " + " | ".join(f"{V0*cfg['targets'][t]/100/px0[t]:.3f} sh / ${V0*cfg['targets'][t]/100:,.0f} / {cfg['targets'][t]:.1f}%" for t in tick) + f" | ${V0:,.0f} |")
for k in sorted(months):
    m = months[k]
    if "holdings" not in m: continue
    Vt = sum(x["value"] for x in m["holdings"].values())
    out.append(f"| {k} | " + " | ".join(f"{m['holdings'][t]['shares']:.3f} sh / ${m['holdings'][t]['value']:,.0f} / {m['holdings'][t]['value']/Vt*100:.1f}%" for t in tick) + f" | ${Vt:,.0f} |")
out.append(f"| now {last} | " + " | ".join(f"{st['holdings'][t]['shares']:.3f} sh / ${st['holdings'][t]['shares']*prices[t]:,.0f}" for t in tick) + f" | ${op.value(st, prices):,.0f} |")
txt = "\n".join(out); print(txt); open(os.path.join(ROOT, "..", "results", f"backtest_real_{a.printer}_{a.start}.md"), "w").write(txt + "\n")
