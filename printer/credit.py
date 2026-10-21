"""Credit for the MP-2 printer: which borrowing helps it RUN (borrow the paycheck in down markets instead of selling) or
BOOST (hold more than the account is worth), and what each costs at October 2026 rates.

Rates on 2026-10-20 (3-month T-bill 4.09%, SOFR 3.87%, fed funds 3.88%, prime 7.00%) as spreads over the T-bill, which is the
loan's base rate in the simulator (1972-2026 T-bills, so the 1980s rate spikes are included):
  in-fund leverage (futures/swaps inside GDE, TQQQ, return-stacked ETFs) ~ +0.5   box-spread loan (SPX, 1-yr)  ~ +0.4
  IBKR Pro margin (<$100k: BM + 1.5%)                                    ~ +1.5   M1 margin (5.90%)            ~ +2.0
  HELOC (~7.3%) / HECM reverse-mortgage line (~7.5%)                      ~ +3.4   Schwab PAL ($100k line)      ~ +4.4
Tax treatment of the interest depends on the credit and its use (see BOX/IBKR/... below). Every case: MP-2 settings, the retiree's taxes unless noted, 2,000 fresh 40-year histories (daily), plus stress cases.
Usage: THROTTLE=0.75 python3 printer/credit.py   (writes results/printer_credit.json and .log)
       MODE=sweep SIZE=50000 THROTTLE=0.75 python3 printer/credit.py   (how much credit makes sense for the retiree: leverage up to the 2x Reg T
       limit and run lines up to 35% x base print, at box-spread and M1 rates; the most credit whose break risk is no worse than plain
       MP-2 in every stress case; finalists re-run on fresh histories; writes results/printer_credit_sweep.json and .log)"""
import os, sys, json, time, datetime as dt, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.argv = [sys.argv[0]]
import money_printer as mp, search as se
from dataclasses import replace
PATHS = int(os.environ.get("PATHS", "2000")); THROTTLE = float(os.environ.get("THROTTLE", "0")); OUT = os.path.join(ROOT, "..", "results")
AL = mp.load_alloc("MP-2 engine"); S2 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65); P = mp.Printer
# tax treatment of the interest follows the credit AND what the money is used for:
#   box spread: 60/40 capital loss either way; margin or HELOC used to invest: investment interest (itemized, up to ordinary
#   investment income); HELOC/HECM used to spend: California home-equity interest (state only); margin/PAL used to spend: none
BOX = dict(rate_spread=0.4, interest_tax="capital"); IBKR = dict(rate_spread=1.5, interest_tax="investment"); M1 = dict(rate_spread=2.0, interest_tax="investment")
HOME = dict(rate_spread=3.4, interest_tax="investment"); M1_SPEND = dict(rate_spread=2.0); HOME_SPEND = dict(rate_spread=3.4, interest_tax="home"); PAL = dict(rate_spread=4.4)

def printers():
    pr = [P("MP-2 (no credit)", AL, **S2)]
    for lev in (1.1, 1.2, 1.33):                                   # BOOST
        pr.append(P(f"boost {lev}x in-fund leverage (T-bill +0.5)", AL, lev=lev, lev_daily=True, rate_spread=0.5, **S2))
        for lab, kw in (("box spread +0.4", BOX), ("IBKR margin +1.5", IBKR), ("M1 margin +2.0", M1), ("HELOC +3.4", HOME)):
            pr.append(P(f"boost {lev}x {lab}", AL, lev=lev, **kw, **S2))
    for cap in (0.15, 0.25):                                       # RUN: borrow the paycheck while below the start
        for lab, kw in (("box spread +0.4", BOX), ("M1 margin +2.0", M1_SPEND), ("HELOC/HECM +3.4", HOME_SPEND), ("Schwab PAL +4.4", PAL)):
            pr.append(P(f"run: {int(cap*100)}% line below start, {lab}", AL, credit=cap, **kw, **S2))
        pr.append(P(f"run: {int(cap*100)}% line below 90%, box spread +0.4", AL, credit=cap, draw_below=0.9, **BOX, **S2))
    for b in (6.25, 6.75):                                         # spend the boost: higher base print
        pr.append(P(f"boost 1.2x box spread, base {b}%", AL, lev=1.2, **BOX, **{**S2, "base": b}))
        pr.append(P(f"run 25% box line, base {b}%", AL, credit=0.25, **BOX, **{**S2, "base": b}))
    return pr

BOX_NOW = dict(rate_spread=0.6, interest_tax="capital")          # today's 3-month SPX box 4.69% vs T-bill 4.09%

def sweep_printers():
    pr = [P(f"no credit, base {b}%", AL, **{**S2, "base": b}) for b in (5.25, 5.75, 6.25, 6.75)]
    for lab, kw in (("box", BOX_NOW), ("M1", M1)):
        pr += [P(f"boost {lev}x {lab}, base {b}%", AL, lev=lev, **kw, **{**S2, "base": b}) for lev in (1.2, 1.33, 1.5, 1.75, 2.0) for b in (5.25, 5.75, 6.25, 6.75)]
    for lab, kw in (("box", dict(rate_spread=0.6, interest_tax="capital")), ("M1", M1_SPEND)):
        pr += [P(f"run {int(c*100)}% {lab} line, base {b}%", AL, credit=c, **kw, **{**S2, "base": b}) for c in (0.15, 0.25, 0.35) for b in (5.75, 6.25, 6.75)]
    return pr

def sweep():
    SIZE = float(os.environ.get("SIZE", "50000")); i00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
    def runs(seed, n):
        return {"base": (mp.make_idx(n, 40, seed=seed), {}), "trend -2%/yr": (mp.make_idx(n, 40, seed=seed + 1), dict(trend_haircut=0.02)),
                "trend -4%/yr": (mp.make_idx(n, 40, seed=seed + 2), dict(trend_haircut=0.04)), "recent era 2000-2026 only": (mp.make_idx(n, 40, seed=seed + 3, era=(i00, mp.T)), {}),
                "3-month blocks": (mp.make_idx(n, 40, block=63, seed=seed + 4), {})}
    def evaluate(pr, R):
        res = {p.name: {} for p in pr}
        for lab, (IDX, kw) in R.items():
            for i in range(0, len(pr), 8):
                tb = time.time(); r = mp.simulate(pr[i:i + 8], IDX, **kw)
                for c, p in enumerate(pr[i:i + 8]): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name][lab] = s
                if THROTTLE: time.sleep(THROTTLE * (time.time() - tb))
            print(f"  {lab} done", flush=True)
        for v in res.values(): v["robust_ce"] = float(np.mean([v[k]["ce"] for k in R])); v["worst_margin_call"] = max(v[k].get("margin_call", 0) for k in R)
        return res
    def ok(v, ref):                                                # break risk no worse than plain MP-2 in every case
        return all(v[k]["lose_value"] <= ref[k]["lose_value"] + .01 and v[k]["deep_dip"] <= ref[k]["deep_dip"] + .02 and v[k]["run_dry"] <= ref[k]["run_dry"] + .002
                   and v[k]["base_never_cut"] >= ref[k]["base_never_cut"] - .02 for k in ref if k in v and isinstance(v[k], dict)) and v["worst_margin_call"] <= .01
    pr = sweep_printers(); REF = "no credit, base 5.75%"
    print(f"Search: {len(pr)} printers, the retiree's taxes, {PATHS} histories x 5 cases", flush=True); res = evaluate(pr, runs(401, PATHS))
    passed = sorted([n for n, v in res.items() if ok(v, res[REF])], key=lambda n: -res[n]["robust_ce"])
    fin = [REF] + [n for n in passed if n != REF][:7] + sorted(res, key=lambda n: -res[n]["robust_ce"])[:3]
    fin = list(dict.fromkeys(fin)); print(f"Validate {len(fin)} finalists on 2,000 fresh histories x 5 cases", flush=True)
    val = evaluate([p for p in pr if p.name in fin], runs(501, 2000))
    for n, v in val.items(): v["passes"] = ok(v, val[REF])
    json.dump(dict(search=res, validate=val), open(os.path.join(OUT, "printer_credit_sweep.json"), "w"), indent=1)
    mo = lambda x: f"${x * SIZE / 12:,.0f}"; pc = lambda x: f"{x * 100:.0f}%"
    for title, R in (("SEARCH", res), ("VALIDATION (fresh histories)", val)):
        print(f"\n{title}: the retiree's taxes, ${SIZE:,.0f} taxable account, $/month after tax (today's $), 40 years. ok = break risk no worse than plain MP-2 in all 5 cases")
        print(f"{'printer':30} ok | robust CE | base pay | typical  bad  | yrs 1-10 typ/bad | never cut  lose  dip<70%  dry  | worst margin call | trend -4%: CE  typical  dry  lose")
        for n, v in sorted(R.items(), key=lambda kv: -kv[1]["robust_ce"]):
            b = v["base"]; t = v["trend -4%/yr"]; pb = float(n.split("base ")[1].rstrip("%")) / 100
            print(f"{n:30} {'ok' if ok(v, R[REF]) else '--'} | {mo(v['robust_ce']):>8}  | {mo(pb):>7}  | {mo(b['print_typical']):>6} {mo(b['print_bad']):>5} | {mo(b['print_y1_10_typ']):>6} / {mo(b['print_y1_10_bad']):<5} | "
                  f"{pc(b['base_never_cut']):>5}   {pc(b['lose_value']):>4}  {pc(b['deep_dip']):>5}  {b['run_dry']*100:4.1f}% | {v['worst_margin_call']*100:5.1f}%            | {mo(t['ce']):>6}  {mo(t['print_typical']):>6}  {t['run_dry']*100:4.1f}%  {pc(t['lose_value'])}", flush=True)

if __name__ == "__main__" and os.environ.get("MODE") == "sweep": sweep()
elif __name__ == "__main__":
    pr = printers(); i00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
    runs = {"base": (mp.make_idx(PATHS, 40, seed=301), {}, None), "trend -2%/yr": (mp.make_idx(PATHS, 40, seed=302), dict(trend_haircut=0.02), None),
            "recent era 2000-2026 only": (mp.make_idx(PATHS, 40, seed=303, era=(i00, mp.T)), {}, None),
            "3-month blocks": (mp.make_idx(PATHS, 40, block=63, seed=304), {}, None), "middle tax": (mp.make_idx(PATHS, 40, seed=301), {}, "middle bracket"),
            "actual 40-yr windows (1972-86 starts)": (mp.make_idx(0, 40, hist=True), {}, None),
            "Roth": (mp.make_idx(PATHS, 40, seed=301), {}, "none (IRA/Roth)")}           # IRAs can't borrow: in-fund leverage only
    res = {p.name: {} for p in pr}
    for lab, (IDX, kw, tax) in runs.items():
        sub = [p for p in pr if lab != "Roth" or (p.lev == 1 and p.credit == 0) or p.lev_daily]
        for i in range(0, len(sub), 8):
            tb = time.time(); chunk = [replace(p, tax=tax) if tax else p for p in sub[i:i + 8]]; r = mp.simulate(chunk, IDX, **kw)
            for c, p in enumerate(sub[i:i + 8]): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name][lab] = s
            if THROTTLE: time.sleep(THROTTLE * (time.time() - tb))
        print(f"  {lab} done", flush=True)
    STRESS = [k for k in runs if k not in ("base", "actual 40-yr windows (1972-86 starts)", "Roth")]
    for v in res.values(): v["robust_ce"] = float(np.mean([v["base"]["ce"]] + [v[k]["ce"] for k in STRESS])); v["worst_ce"] = float(min(v[k]["ce"] for k in ["base"] + STRESS))
    json.dump(res, open(os.path.join(OUT, "printer_credit.json"), "w"), indent=1)
    mo = lambda x: f"${x * 100000 / 12:,.0f}"; pc = lambda x: f"{x * 100:.0f}%"
    print(f"\nMP-2 printer with credit, the retiree's taxes, per $100k, $/month after tax (today's $). {PATHS} fresh 40-year histories.")
    print(f"{'printer':52} | robust CE  worst CE | typical  bad   60-70 typ/bad | never cut  lose value  dip<70%  dry  margin call | loan p90 | CE: trend-2 / recent / 3-mo / middle tax | actual windows typ / never cut")
    b0 = res["MP-2 (no credit)"]["robust_ce"]
    for n, v in res.items():
        b = v["base"]; a = v["actual 40-yr windows (1972-86 starts)"]
        print(f"{n:52} | {mo(v['robust_ce']):>7} {(v['robust_ce']/b0-1)*100:+5.1f}% {mo(v['worst_ce']):>6} | {mo(b['print_typical']):>6} {mo(b['print_bad']):>5} {mo(b['print_y1_10_typ']):>5}/{mo(b['print_y1_10_bad']):<5} | "
              f"{pc(b['base_never_cut']):>6}   {pc(b['lose_value']):>6}   {pc(b['deep_dip']):>6} {b['run_dry']*100:4.1f}%  {pc(b.get('margin_call', 0)):>5}   | {b.get('loan_max_bad', 0)*100:4.0f}%   | "
              + " / ".join(mo(v[k]["ce"]) for k in STRESS) + f" | {mo(a['print_typical'])} / {pc(a['base_never_cut'])}"
              + (f" | Roth CE {mo(v['Roth']['ce'])} typ {mo(v['Roth']['print_typical'])} dip {pc(v['Roth']['deep_dip'])}" if "Roth" in v else ""), flush=True)
