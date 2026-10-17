"""Fetch daily testfol.io histories for every lineup portfolio + market-indicator series.
Output: data_portfolios.json, data_indicators.json (cached; rerun to refresh to the latest testfol day)."""
import json, os, time, urllib.request
ROOT = os.path.dirname(os.path.abspath(__file__))
PF = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
LINEUP = ["MinRisk", "E6", "Safe-Now", "C1-Now", "E9", "E10", "E11", "S12+", "S12-F5", "S12.5", "S13", "S13.5",
          "E14", "E15", "M25", "M30", "M35", "E20", "E22", "E24"]
INDICATORS = ["SPYSIM", "QQQSIM", "VIXSIM", "IEFSIM", "TLTSIM", "SHYSIM", "GLDSIM", "UUPSIM", "INFLATION", "TBILL", "KMLMSIM", "XLESIM"]

def call(allocs, start="1987-12-31"):
    body = {"start_date": start, "end_date": "2100-01-01", "start_val": 1, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": a} for a in allocs]}
    req = urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=240)); time.sleep(1)
    assert not d["errors"], d["errors"]; return d

if __name__ == "__main__":
    out = {"names": [], "t": None, "v": []}
    for i in range(0, len(LINEUP), 5):
        grp = LINEUP[i:i + 5]; d = call([PF[n]["alloc"] for n in grp]); h = d["charts"]["history"]
        if out["t"] is None: out["t"] = h[0]
        assert h[0] == out["t"], "date mismatch between batches"
        out["names"] += grp; out["v"] += h[1:]
        print("portfolios", grp, d["start_date"], "->", d["end_date"])
    json.dump(out, open(os.path.join(ROOT, "data_portfolios.json"), "w"))
    ind = {}
    for t in INDICATORS:                                  # one call each: full native history
        d = call([{t: 100}], start="1900-01-01"); h = d["charts"]["history"]
        ind[t] = {"t": h[0], "v": h[1]}; print("indicator", t, d["start_date"], "->", d["end_date"], len(h[0]))
    json.dump(ind, open(os.path.join(ROOT, "data_indicators.json"), "w"))
