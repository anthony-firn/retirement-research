"""Verify regime-search results on testfol.io: full continuous run stats + scenario-episode returns
and 2026 YTD computed from testfol's own daily history.
Usage: python3 verify_regime.py regime_now.json regime_safe.json   (env TOP=3)"""
import json, sys, os, time, urllib.request, datetime as dt, numpy as np
TOP = int(os.environ.get("TOP", "3"))
PF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "portfolios.json")))
P = {"C1": PF["C1"]["alloc"], "FULL#1": PF["FULL#1"]["alloc"]}
EP = None
for f in sys.argv[1:]:
    d = json.load(open(f)); EP = d["episodes"]; tag = os.path.splitext(os.path.basename(f))[0].replace("regime_", "")
    for i, r in enumerate(d["results"][:TOP]): P[f"{tag}#{i+1}"] = r["alloc"]

def call(names):
    body = {"start_date": "1987-12-31", "end_date": "2026-10-16", "start_val": 10000, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": P[n]} for n in names]}
    req = urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=180)); time.sleep(1); assert not d["errors"], d["errors"]; return d

out = {}; names = list(P)
for i in range(0, len(names), 5):
    grp = names[i:i + 5]; d = call(grp)
    h = d["charts"]["history"]; td = np.array([dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in h[0]])
    print(f"testfol {d['start_date']} -> {d['end_date']} limiting={d['limiting_ticker']}")
    for k, (n, s) in enumerate(zip(grp, d["stats"])):
        v = np.array(h[k + 1]); ep = {}
        for name, a, b, _ in EP:
            ia = np.searchsorted(td, a); ib = np.searchsorted(td, b); ep[name] = (v[ib] / v[ia] - 1) * 100
        iy = np.searchsorted(td, "2025-12-31", side="right") - 1
        ytd = (v[-1] / v[iy] - 1) * 100; seg = v[iy:]; ytd_dd = (seg / np.maximum.accumulate(seg) - 1).min() * 100
        w = np.array([e[3] for e in EP]); w = w / w.sum(); e = np.array(list(ep.values()))
        out[n] = dict(alloc=P[n], cagr=s["cagr"], std=s["std"], mdd=s["max_drawdown"], sharpe=s["sharpe"], sortino=s["sortino"], calmar=s["calmar"],
                      ulcer=s["ulcer_index"], episodes=ep, scenario=float((w * e).sum() + 0.5 * e.min()), worst=float(e.min()), ytd=ytd, ytd_dd=ytd_dd)

lab = lambda a: " ".join(f"{k.replace('SIM','')}{v}" for k, v in a.items())
print(f"\n{'':8} {'allocation':64} CAGR   MDD   Sharpe Calmar Ulcer | scen  worst | 2026YTD  ytdDD")
for n, r in out.items():
    print(f"{n:8} {lab(r['alloc']):64} {r['cagr']:5.2f} {r['mdd']:6.2f} {r['sharpe']:.3f} {r['calmar']:.3f} {r['ulcer']:.3f} | {r['scenario']:+5.2f} {r['worst']:+5.1f} | {r['ytd']:+6.1f} {r['ytd_dd']:6.1f}")
print("\nScenario episode returns (%), testfol daily data:")
print(f"{'episode':28}" + "".join(f"{n:>9}" for n in out))
for name, *_ in EP: print(f"{name:28}" + "".join(f"{out[n]['episodes'][name]:9.1f}" for n in out))
json.dump(out, open("verify_regime.json", "w"), indent=1)
