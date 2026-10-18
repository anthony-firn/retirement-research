"""Portfolio backtester with testfol-compatible request/response fields.
request = {start_date, end_date, start_val, backtests:[{allocation:{TICKER:pct}, rebalance_freq:'Yearly'|'Quarterly'|'Monthly'|'None', drag}]}
Stats definitions match testfol.io (validated in engine/validate.py)."""
import math, datetime as dt, numpy as np
from . import store

def _day(s): return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.UTC).timestamp())
def _date(t): return dt.datetime.fromtimestamp(int(t), dt.UTC).date().isoformat()

def _align(tickers, start, end):
    S = {k: store.get(k) for k in tickers}; rf = store.get("TBILL")
    first = max(s[0][0] for s in S.values()); limiting = max(S, key=lambda k: S[k][0][0])
    cal = S[limiting][0]; cal = cal[(cal >= max(first, start)) & (cal <= end)]
    for k, (t, v) in S.items(): cal = cal[np.isin(cal, t)] if len(t) < 40000 else cal
    def at(series):
        t, v = series; i = np.searchsorted(t, cal, side="right") - 1; return v[np.clip(i, 0, None)]
    return cal, {k: at(s) for k, s in S.items()}, at(rf), limiting

def _period_key(t, freq):
    d = dt.datetime.fromtimestamp(int(t), dt.UTC)
    return {"Yearly": d.year, "Quarterly": (d.year, (d.month - 1) // 3), "Monthly": (d.year, d.month)}.get(freq)

def run_one(bt, cal, P, start_val):
    alloc = {k: v / 100 for k, v in bt["allocation"].items()}; names = list(alloc); w = np.array([alloc[n] for n in names])
    w = w / w.sum(); X = np.stack([P[n] for n in names], 1); R = X[1:] / X[:-1] - 1; freq = bt.get("rebalance_freq", "Yearly")
    drag = bt.get("drag", 0) / 100 / 252
    val = np.empty(len(cal)); val[0] = start_val; hold = w * start_val
    for d in range(1, len(cal)):
        if freq != "None" and _period_key(cal[d], freq) != _period_key(cal[d - 1], freq): hold = w * hold.sum()   # rebalance at prior close
        hold = hold * (1 + R[d - 1]) * (1 - drag); val[d] = hold.sum()
    return val

def stats(val, rf):
    r = val[1:] / val[:-1] - 1; rfd = rf[1:] / rf[:-1] - 1; ex = r - rfd; n = len(val); yrs = n / 252
    cagr = (val[-1] / val[0]) ** (1 / yrs) - 1; dd = val / np.maximum.accumulate(val) - 1; mdd = dd.min()
    ulcer = math.sqrt(((dd * 100) ** 2).mean()); rf_c = (rf[-1] / rf[0]) ** (1 / yrs) - 1
    down = np.minimum(ex, 0)
    return dict(cagr=cagr * 100, std=r.std() * math.sqrt(252) * 100, max_drawdown=mdd * 100,
                sharpe=ex.mean() * 252 / (ex.std() * math.sqrt(252)), sortino=ex.mean() * 252 / (math.sqrt((down ** 2).mean()) * math.sqrt(252)),
                calmar=cagr / -mdd if mdd < 0 else float("inf"), ulcer_index=ulcer, upi=(cagr - rf_c) * 100 / ulcer if ulcer else float("inf"),
                end_val=float(val[-1]), cum_return=(val[-1] / val[0] - 1) * 100)

def backtest(req):
    tickers = sorted({k for bt in req["backtests"] for k in bt["allocation"]})
    start = _day(req.get("start_date") or "1800-01-01"); end = _day(req.get("end_date") or "2100-01-01")
    cal, P, rf, limiting = _align(tickers, start, end); out = {"errors": [], "limiting_ticker": limiting, "start_date": _date(cal[0]), "end_date": _date(cal[-1]),
                                                              "stats": [], "charts": {"history": [cal.tolist()]}, "sources": {k: store.source_of(k) for k in tickers}}
    for bt in req["backtests"]:
        if abs(sum(bt["allocation"].values()) - 100) > 1e-6: out["errors"].append("Allocation percentages must sum to 100"); continue
        v = run_one(bt, cal, P, req.get("start_val", 10000)); out["stats"].append(stats(v, rf)); out["charts"]["history"].append(v.tolist())
    return out
