"""Verify top search results on testfol.io (continuous 1987-12-31 -> today, plus each decade) vs FULL#1.
Usage: python3 verify_top.py gpu_clean_etf.json [gpu_clean_A.json ...]   (env TOP=4 per file)"""
import json, sys, os, time, urllib.request
TOP = int(os.environ.get("TOP", "4"))
F1 = {"SHYSIM": 25, "SPMOSIM": 20, "GLDSIM": 15, "KMLMSIM": 20, "UUPSIM": 10, "XLVSIM": 5, "ZROZSIM": 5}
P = {"FULL#1": F1}
for f in sys.argv[1:]:
    tag = os.path.splitext(os.path.basename(f))[0].replace("gpu_", "")
    for i, r in enumerate(json.load(open(f))["results"][:TOP]):
        assert not any("?" in k for k in r["alloc"]), "modifier ticker found"
        P[f"{tag}#{i+1}"] = r["alloc"]

def call(start, end, names):
    body = {"start_date": start, "end_date": end, "start_val": 10000, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": P[n]} for n in names]}
    req = urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=180)); time.sleep(1)
    assert not d["errors"], d["errors"]
    return d

WIN = [("full", "1987-12-31", "2026-10-16"), ("1988-1997", "1987-12-31", "1997-12-31"), ("1998-2007", "1998-01-01", "2007-12-31"),
       ("2008-2017", "2008-01-01", "2017-12-31"), ("2018-2026", "2018-01-01", "2026-10-16")]
names = [n for n in P if n != "FULL#1"]
out = {n: {} for n in P}
for w, a, b in WIN:
    for i in range(0, len(names), 4):                     # FULL#1 + 4 challengers per request (API max 5)
        grp = ["FULL#1"] + names[i:i + 4]
        d = call(a, b, grp)
        if w == "full": print(f"testfol {d['start_date']} -> {d['end_date']}  limiting={d['limiting_ticker']}")
        for n, s in zip(grp, d["stats"]):
            out[n][w] = dict(cagr=s["cagr"], std=s["std"], mdd=s["max_drawdown"], sharpe=s["sharpe"], sortino=s["sortino"], calmar=s["calmar"], ulcer=s["ulcer_index"], end=s["end_val"])

def wins(n):
    f, b = out[n]["full"], out["FULL#1"]["full"]
    ok = f["sharpe"] > b["sharpe"] and f["calmar"] > b["calmar"] and f["ulcer"] < b["ulcer"] and f["mdd"] > b["mdd"] and f["cagr"] >= b["cagr"]
    dec = sum(out[n][w]["sharpe"] > out["FULL#1"][w]["sharpe"] and out[n][w]["calmar"] > out["FULL#1"][w]["calmar"] and out[n][w]["ulcer"] < out["FULL#1"][w]["ulcer"] for w, *_ in WIN[1:])
    return ok, dec

print(f"\n{'':14} {'allocation':66}  CAGR   MDD  Sharpe Calmar Ulcer | full-win decades-won")
for n in P:
    f = out[n]["full"]; a = " ".join(f"{k.replace('SIM','')}{v}" for k, v in P[n].items())
    ok, dec = wins(n) if n != "FULL#1" else ("-", "-")
    print(f"{n:14} {a:66} {f['cagr']:5.2f} {f['mdd']:6.2f} {f['sharpe']:.3f} {f['calmar']:.3f} {f['ulcer']:.3f} | {ok!s:5} {dec}/4")
json.dump(dict(portfolios=P, testfol=out), open("verify_top.json", "w"), indent=1)
