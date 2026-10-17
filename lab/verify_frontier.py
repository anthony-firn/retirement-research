"""Verify the efficient frontier on testfol.io: rank-1 portfolio per target, plus C1 / C1-Now / Safe-Now.
Full continuous 1987-12-31 -> today, each decade as its own run, scenario episodes + 2026 YTD from testfol history.
Usage: python3 verify_frontier.py frontier.json frontier_lo.json frontier_etf.json   (env TMIN/TMAX, OUT)"""
import json, sys, os, time, urllib.request, datetime as dt, numpy as np
PF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "portfolios.json")))
P = {n: PF[n]["alloc"] for n in os.environ.get("REFS", "Safe-Now,C1,C1-Now").split(",") if n}
LO, HI = float(os.environ.get("TMIN", "6")), float(os.environ.get("TMAX", "15"))
picked = {}
for path in (sys.argv[1:] or ["frontier.json"]):            # files containing "etf" -> E<target>, else F<target>
    F = json.load(open(path)); EP = F["episodes"]; bn = os.path.basename(path)
    import re
    mv = re.search(r"sweet_(v\d+)", bn)
    if "sweet_final" in bn: mv = None
    pre = (mv.group(1).upper() + "-") if mv else ("S" if "sweet_final" in bn else ("M" if "maxret" in bn else ("E" if "etf" in bn else "F")))   # M<cap> = max CAGR with |MDD| <= cap
    for r in F["results"]:
        if r["rank"] == 1 and (pre == "M" or LO <= r["target"] <= HI): picked[(pre, r["target"])] = r["alloc"]
for (pre, tgt) in sorted(picked): P[f"{pre}{tgt:g}"] = picked[(pre, tgt)]

def call(start, end, names):
    body = {"start_date": start, "end_date": end, "start_val": 10000, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": P[n]} for n in names]}
    req = urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=180)); time.sleep(1); assert not d["errors"], d["errors"]; return d

WIN = [("full", "1987-12-31", "2026-10-16"), ("1988-1997", "1987-12-31", "1997-12-31"), ("1998-2007", "1998-01-01", "2007-12-31"),
       ("2008-2017", "2008-01-01", "2017-12-31"), ("2018-2026", "2018-01-01", "2026-10-16")]
names = list(P); out = {n: {} for n in names}
for w, a, b in WIN:
    for i in range(0, len(names), 5):
        grp = names[i:i + 5]; d = call(a, b, grp)
        if w == "full":
            h = d["charts"]["history"]; td = np.array([dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in h[0]])
        for k, (n, s) in enumerate(zip(grp, d["stats"])):
            out[n][w] = dict(cagr=s["cagr"], std=s["std"], mdd=s["max_drawdown"], sharpe=s["sharpe"], sortino=s["sortino"], calmar=s["calmar"], ulcer=s["ulcer_index"], end=s["end_val"])
            if w == "full":
                v = np.array(h[k + 1]); e = np.array([(v[np.searchsorted(td, y)] / v[np.searchsorted(td, x)] - 1) * 100 for _, x, y, _ in EP])
                wt = np.array([x[3] for x in EP]); wt = wt / wt.sum()
                iy = np.searchsorted(td, "2025-12-31", side="right") - 1; seg = v[iy:]
                out[n]["episodes"] = dict(zip([x[0] for x in EP], e.tolist())); out[n]["worst"] = float(e.min())
                out[n]["scenario"] = float((wt * e).sum() + 0.5 * e.min()); out[n]["ytd"] = (v[-1] / v[iy] - 1) * 100
                out[n]["ytd_dd"] = (seg / np.maximum.accumulate(seg) - 1).min() * 100
        if w == "full":
            for k, n in enumerate(grp):
                yrs = {r[0]: r[1 + 2 * k] for r in d["annual_returns"]}
                out[n]["worst_year"] = min((v, y) for y, v in yrs.items() if y >= 1988)
                out[n]["neg_years"] = sum(1 for y, v in yrs.items() if y >= 1988 and v < 0)

lab = lambda a: " ".join(f"{k.replace('SIM','')}{v}" for k, v in a.items())
print(f"{'':9} {'allocation':66} CAGR  Vol   MDD   Sharpe Calmar Ulcer | worst yr  neg | analog worst | dec-CAGR min | 2026YTD")
for n in names:
    f = out[n]["full"]; dmin = min(out[n][w]["cagr"] for w, *_ in WIN[1:])
    wy, yy = out[n]["worst_year"]
    print(f"{n:9} {lab(P[n]):66} {f['cagr']:5.2f} {f['std']:5.2f} {f['mdd']:6.2f} {f['sharpe']:.3f} {f['calmar']:.3f} {f['ulcer']:5.2f} | {wy:6.1f} {yy} {out[n]['neg_years']:2d} | {out[n]['worst']:+6.1f} | {dmin:6.2f} | {out[n]['ytd']:+6.1f}")
print("\nDecade CAGR / Sharpe (testfol, each decade its own run)")
for n in names: print(f"{n:9} " + "  ".join(f"{w}: {out[n][w]['cagr']:5.2f}/{out[n][w]['sharpe']:.2f}" for w, *_ in WIN[1:]))
print("\nScenario episodes (%)")
print(f"{'episode':28}" + "".join(f"{n:>9}" for n in names))
for e, *_ in EP: print(f"{e:28}" + "".join(f"{out[n]['episodes'][e]:9.1f}" for n in names))
json.dump(dict(portfolios=P, testfol=out), open(os.environ.get("OUT", "verify_frontier.json"), "w"), indent=1)
