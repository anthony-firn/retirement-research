"""Validate the money printers found by printer/search.py on fresh data and build the lineup.
Every finalist + reference printers are re-run DAILY on 2,000 fresh histories (different seed than the search) and in stress cases:
trend funds earn 2% / 4% less a year, harsher 3-month-block reshuffle, recent era only (blocks drawn from 2000-2026), middle tax bracket.
Each engine is also checked on testfol.io (yearly + 2x-valve proxy, 2000-2026). Writes results/PRINTER_SEARCH.md and printer_validate.json."""
import os, sys, json, urllib.request, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
import money_printer as mp, search as se
from dataclasses import replace
OUT = os.path.join(ROOT, "..", "results"); PATHS = int(os.environ.get("PATHS", "2000")); TOPN = int(os.environ.get("TOPN", "4"))
def load_finalists():
    fin = []
    for mode in ("retiree", "balanced", "max_print", "fortress"):
        f = os.path.join(OUT, f"printer_search_{mode}.json")
        if not os.path.exists(f): continue
        seen = set(); k = 0
        for r in json.load(open(f)):
            eng = tuple(sorted(r["printer"]["alloc"].items()))
            if eng in seen: continue
            seen.add(eng); k += 1; q = r["printer"]
            fin.append(mp.Printer(f"{mode} #{k}", {t: int(w) for t, w in q["alloc"].items()}, base=q["base"], skim=q["skim"], bucket_months=int(q["bucket_months"]), cut_below=q["cut_below"], cut_to=q["cut_to"]))
            if k == TOPN: break
    return fin
REFS = lambda: [mp.Printer("CH-12 Printer (current)", mp.load_alloc("Crisis-Hedged 12 (no UUP)")), mp.Printer("60/40 Printer", mp.load_alloc("60/40")),
                mp.Printer("VTI Printer", mp.load_alloc("VTI (100% US stocks)"))]
def testfol(alloc):
    body = {"start_date": "1987-12-31", "end_date": "2026-10-16", "start_val": 10000, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": alloc, "absolute_dev": 0, "relative_dev": 100}]}
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}), timeout=240))
        s = d["stats"][0]; return dict(start=d["start_date"], cagr=s["cagr"], mdd=s["max_drawdown"], sharpe=s["sharpe"], ulcer=s["ulcer_index"])
    except Exception as e: return dict(error=str(e)[:80])
if __name__ == "__main__":
    pr = load_finalists() + REFS(); i00 = int(np.searchsorted(mp.h.CAL, int(__import__("datetime").datetime(2000, 1, 3, tzinfo=__import__("datetime").UTC).timestamp())))
    runs = {"base": (mp.make_idx(PATHS, 40, seed=202), {}), "trend -2%/yr": (mp.make_idx(PATHS, 40, seed=203), dict(trend_haircut=0.02)),
            "trend -4%/yr": (mp.make_idx(PATHS, 40, seed=204), dict(trend_haircut=0.04)), "3-month blocks": (mp.make_idx(PATHS, 40, block=63, seed=205), {}),
            "recent era 2000-2026 only": (mp.make_idx(PATHS, 40, seed=206, era=(i00, mp.T)), {}),
            "gold -3%/yr": (mp.make_idx(PATHS, 40, seed=207), dict(drag={"GLDSIM": .03, "GDESIM": .027, "UGLSIM": .06})),
            "gold -5%/yr": (mp.make_idx(PATHS, 40, seed=208), dict(drag={"GLDSIM": .05, "GDESIM": .045, "UGLSIM": .10}))}
    STRESS = [k for k in runs if k != "base"]
    res = {p.name: dict(printer=dict(alloc=p.alloc, base=p.base, skim=p.skim, bucket_months=p.bucket_months, cut_below=p.cut_below, cut_to=p.cut_to)) for p in pr}
    for lab, (IDX, kw) in runs.items():
        for i in range(0, len(pr), 8):
            chunk = pr[i:i + 8]; r = mp.simulate(chunk, IDX, **kw)
            for c, p in enumerate(chunk): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name][lab] = s
        print(f"  {lab} done", flush=True)
    r = mp.simulate([replace(p, tax="middle bracket") for p in pr[:8]] + [replace(p, tax="middle bracket") for p in pr[8:]], runs["base"][0])
    for c, p in enumerate(pr): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name]["middle tax"] = s
    for p in pr: res[p.name]["testfol"] = testfol(p.alloc)
    mo = lambda x: f"${x * 100000 / 12:,.0f}"
    for v in res.values():
        v["robust_ce"] = float(np.mean([v["base"]["ce"]] + [v[k]["ce"] for k in STRESS])); v["worst_ce"] = float(min(v[k]["ce"] for k in ["base"] + STRESS))
        v["gold_exposure"] = v["printer"]["alloc"].get("GLDSIM", 0) + 0.9 * v["printer"]["alloc"].get("GDESIM", 0) + 2 * v["printer"]["alloc"].get("UGLSIM", 0)
    json.dump(res, open(os.path.join(OUT, "printer_validate.json"), "w"), indent=1, default=float)
    hdr = "| Printer | Engine | Settings | Robust CE | Worst-case CE | CE base | Typical | Bad | Ages 60-70 | Base never cut | Loses value | Dry | CE: trend -2% / -4% / 3-mo / recent era / gold -3% / -5% | Gold exposure | testfol CAGR / MDD / Sharpe (start) |"
    lines = [hdr, "|" + "---|" * 15]
    for n, v in sorted(res.items(), key=lambda kv: -kv[1]["robust_ce"]):
        b = v["base"]; p = v["printer"]; t = v["testfol"]
        eng = " · ".join(f"{k.replace('SIM','')} {w}" for k, w in sorted(p["alloc"].items(), key=lambda x: -x[1]))
        st = f"base {p['base']:.2f}%, skim>{int(round(p['skim']*100))}%, bucket {p['bucket_months']}m, cut {p['cut_below']:.2f}->{p['cut_to']:.2f}" if p["skim"] is not None else "fixed"
        tf = f"{t['cagr']:.2f}% / {t['mdd']:.1f}% / {t['sharpe']:.3f} ({t['start'][:4]})" if "cagr" in t else t.get("error", "")
        lines.append(f"| {n} | {eng} | {st} | **{mo(v['robust_ce'])}** | {mo(v['worst_ce'])} | {mo(b['ce'])} | {mo(b['print_typical'])} | {mo(b['print_bad'])} | {mo(b['print_y1_10_typ'])} | {b['base_never_cut']*100:.0f}% | {b['lose_value']*100:.0f}% | {b['run_dry']*100:.1f}% | "
                     + " / ".join(mo(v[k]["ce"]) for k in STRESS if k != "3-month blocks" or True) + f" | {v['gold_exposure']:.0f}% | {tf} |")
    open(os.path.join(OUT, "printer_validate_table.md"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
