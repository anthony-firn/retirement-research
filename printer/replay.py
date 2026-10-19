"""Replay test: run the OPERATOR (printer/operate.py) day by day through real 2000-2026 history and check that it reproduces
the SIMULATOR (printer/money_printer.py) on the same path — i.e. the rules you follow are the rules that were tested.
Both run in an IRA (no tax) so only the printer rules are compared. Prices = each fund's total-return index (dividends reinvested).
Reports total real spending, ending real value, rebalances and guardrail cuts for: simulator, operator (simulator-style
'spread' selling) and operator (practical 'most overweight fund first' selling).  Usage: python3 printer/replay.py [MP-2]"""
import os, sys, json, datetime as dt, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, ".."))
argv = sys.argv[1:]; sys.argv = [sys.argv[0]]
import money_printer as mp, operate as op
NAME = argv[0] if argv else "MP-2"; START = os.environ.get("START", "2000-01-03")
cfg = op.PRINTERS[NAME]; S = cfg["settings"]; tick = list(cfg["targets"])
i0 = int(np.searchsorted(mp.h.CAL, int(dt.datetime.fromisoformat(START).replace(tzinfo=dt.UTC).timestamp()))); Y = (mp.T - 1 - i0) // 252; L = Y * 252
dates = [dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in mp.h.CAL]
lvl = {t: np.cumprod(1 + mp.fund_returns(t + "SIM")) for t in tick}; cpi = np.asarray(mp.h.cpi, float)

# ---- simulator on this exact path
pr = mp.Printer(NAME, {t + "SIM": w for t, w in cfg["targets"].items()}, band=S["band"], gap_days=252, valve=S["valve"], base=S["base"], skim=S["skim"],
                bucket_months=S["bucket_months"], cut_below=S["cut_below"], cut_to=S["cut_to"], restore_above=S["restore_above"], tax="none (IRA/Roth)")
IDX = torch.tensor((i0 + np.arange(L))[None, :], device=mp.DEV); r = mp.simulate([pr], IDX)
sim = dict(spend=float(r["spend"][0, 0].sum()), real_end=float(r["real_end"][0, 0] + r["bucket_end"][0, 0]), reb=float(r["reb"][0, 0] * Y), cut=bool(r["cut"][0, 0]))

# ---- operator, day by day
def run_operator(spread):
    op.SPREAD = spread; V0 = 100000.0; d0 = dates[i0]
    st = dict(printer=NAME, targets=cfg["targets"], settings=S, baseline=dict(start_value=V0, start_cpi=cpi[i0], start_date=d0),
              holdings={t: {"shares": V0 * w / 100 / lvl[t][i0], "lots": [dict(shares=V0 * w / 100 / lvl[t][i0], cost=lvl[t][i0], date=d0)]} for t, w in cfg["targets"].items()},
              cash_bucket=0.0, guardrail_mult=1.0, last_rebalance=d0, last_month_paid=d0[:7], last_year_end=int(d0[:4]), log=[])
    spend_real = 0.0; nreb = 0; cuts = 0; rf = np.asarray(mp.RF)
    for d in range(i0 + 1, i0 + L):
        st["cash_bucket"] *= 1 + rf[d]                                     # bucket earns T-bills
        prices = {t: float(lvl[t][d]) for t in tick}; p = op.plan(st, dates[d], prices, float(cpi[d]))
        for s in p["steps"]:
            if s["step"] == "MONTHLY PRINT": spend_real += s["spend"] / (cpi[d] / cpi[i0]) / V0
            if s["step"] == "REBALANCE": nreb += 1
            if s["step"] == "YEAR-END" and s["guardrail"] < 1: cuts += 1
        if p["steps"]: st = op.apply(st, p, dates[d], "IRA"); st["log"] = []
    V = op.value(st, {t: float(lvl[t][i0 + L - 1]) for t in tick}); real_end = (V + st["cash_bucket"]) / (cpi[i0 + L - 1] / cpi[i0]) / V0
    return dict(spend=spend_real, real_end=real_end, reb=nreb, cut=cuts > 0)
o_spread = run_operator(True); o_simple = run_operator(False)
print(f"Replay {NAME} {dates[i0]} -> {dates[i0 + L - 1]} ({Y} years, IRA, $100k start; amounts as multiples of the starting value, today's dollars)")
print(f"  {'':42} total spent   ending value   rebalances   guardrail cut ever")
for lab, x in (("simulator (money_printer.py)", sim), ("operator, simulator-style selling", o_spread), ("operator, practical selling (default)", o_simple)):
    print(f"  {lab:42} {x['spend']:9.2f}x   {x['real_end']:10.2f}x   {x['reb']:8.0f}      {x['cut']}")
gap = max(abs(o_spread["spend"] / sim["spend"] - 1), abs(o_spread["real_end"] / sim["real_end"] - 1)) * 100
print(f"  operator vs simulator: largest difference {gap:.1f}% (calendar months/years vs 21/252-trading-day periods)")
json.dump(dict(sim=sim, operator_spread=o_spread, operator_practical=o_simple), open(os.path.join(ROOT, "..", "results", f"replay_{NAME}.json"), "w"), indent=1, default=float)
