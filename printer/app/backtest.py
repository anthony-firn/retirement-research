"""Backtests for the local app, on the same 1972-2026 daily data the printer search used (strategy/history70s.py).

portfolio()  testfol-style: growth of $10,000 with no withdrawals, rebalanced Yearly / Quarterly / Monthly / None, or by the
             printer rule (> 6 points off target, at most once a year, plus the 2x valve). Stats are engine/backtest.py's
             (validated against testfol.io): CAGR, std, max drawdown, Sharpe, Sortino, Calmar, Ulcer, UPI; plus drawdown,
             annual-return and rolling-return series.
history()    the printer running on one real historical path from a chosen start date: monthly paycheck, bonus, cash
             bucket, safety-brake cuts, taxes, balance (money_printer.simulate with trace=True, so the rules are identical).
fan()        simulated futures: percentiles of the real balance and the yearly paycheck over 40 reshuffled histories."""
import os, sys, math, datetime as dt, threading, numpy as np, torch
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", ".."))
_argv = sys.argv; sys.argv = sys.argv[:1]
import money_printer as mp
sys.argv = _argv
from engine.backtest import stats as tf_stats

CAL = np.asarray(mp.h.CAL, np.int64); T = len(CAL)
DATES = np.array([dt.datetime.fromtimestamp(int(t), dt.UTC).date() for t in CAL])
YEAR = np.array([d.year for d in DATES]); MONTH = np.array([d.month for d in DATES]); QUARTER = YEAR * 4 + (MONTH - 1) // 3
RFI = np.cumprod(1 + np.asarray(mp.RF, float)); CPI = np.cumprod(mp.CPIR)
GPU = threading.Lock()                                                            # one simulation at a time on the laptop GPU
_RET = {}
def rets(t):
    if t not in _RET: _RET[t] = mp.fund_returns(t + "SIM")
    return _RET[t]

def span(start, end):
    i0 = int(np.searchsorted(CAL, int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.UTC).timestamp()))) if start else 0
    i1 = int(np.searchsorted(CAL, int(dt.datetime.fromisoformat(end).replace(tzinfo=dt.UTC).timestamp()), side="right")) - 1 if end else T - 1
    i0 = max(0, min(i0, T - 260)); i1 = max(i0 + 252, min(i1, T - 1)); return i0, i1

def thin(n, k=1600):                                                              # indices for charts: about k points, always the last
    st = max(1, n // k); ix = np.arange(0, n, st); return ix if ix[-1] == n - 1 else np.r_[ix, n - 1]

def iso(i): return DATES[i].isoformat()

# ------------------------------------------------------------------ testfol-style portfolio backtest
def _values(allocs, i0, i1, rebalance):
    tick = sorted({t for a in allocs for t, _ in a}); R = np.stack([rets(t)[i0 + 1:i1 + 1] for t in tick], 1); n = i1 - i0 + 1
    W = np.zeros((len(allocs), len(tick)))
    for p, a in enumerate(allocs):
        for t, w in a: W[p, tick.index(t)] += w
    W /= W.sum(1, keepdims=True); hold = W * 10000.0; V = np.empty((len(allocs), n)); V[:, 0] = 10000; last = np.zeros(len(allocs), int)
    key = {"Yearly": YEAR, "Quarterly": QUARTER, "Monthly": YEAR * 12 + MONTH}.get(rebalance)
    for d in range(1, n):
        if key is not None and key[i0 + d] != key[i0 + d - 1]: hold = W * hold.sum(1, keepdims=True)        # at the period's first close
        hold = hold * (1 + R[d - 1]); tot = hold.sum(1, keepdims=True)
        if rebalance == "Printer rule":
            w = hold / tot; rel = np.where(W > 0, w / np.where(W > 0, W, 1), 0).max(1)
            trig = ((np.abs(w - W).max(1) * 100 > 6) & (d - last > 252)) | (rel >= 2)
            if trig.any():
                cost = mp.COST * np.abs(W * tot - hold).sum(1); new = W * (tot[:, 0] - cost)[:, None]
                hold = np.where(trig[:, None], new, hold); last = np.where(trig, d, last); tot = hold.sum(1, keepdims=True)
        V[:, d] = tot[:, 0]
    return V

def portfolio(portfolios, start=None, end=None, rebalance="Yearly", real=False):
    i0, i1 = span(start, end); V = _values([p["alloc"] for p in portfolios], i0, i1, rebalance); n = V.shape[1]
    if real: V = V / (CPI[i0:i1 + 1] / CPI[i0])[None]
    ix = thin(n); out = dict(start=iso(i0), end=iso(i1), dates=[int(CAL[i0 + i]) for i in ix], portfolios=[])
    yrs = YEAR[i0:i1 + 1]; ends = np.r_[np.flatnonzero(np.diff(yrs)), n - 1]; out["years"] = yrs[ends].tolist()
    for p, v in zip(portfolios, V):
        st = tf_stats(v, RFI[i0:i1 + 1]); dd = v / np.maximum.accumulate(v) - 1
        yv = np.r_[v[0], v[ends]]; ann = yv[1:] / yv[:-1] - 1
        roll = {}
        for w in (1, 3, 5, 10):
            L = 252 * w
            if n > L + 10: rr = (v[L:] / v[:-L]) ** (1 / w) - 1; roll[w] = [None] * int(np.searchsorted(ix, L)) + [float(rr[i - L]) for i in ix if i >= L]
        mo_ends = np.r_[np.flatnonzero(np.diff(YEAR[i0:i1 + 1] * 12 + MONTH[i0:i1 + 1])), n - 1]; mv = np.r_[v[0], v[mo_ends]]; mret = mv[1:] / mv[:-1] - 1
        st.update(best_year=float(ann.max() * 100), worst_year=float(ann.min() * 100), positive_months=float((mret > 0).mean() * 100),
                  worst_month=float(mret.min() * 100), max_dd_date=iso(i0 + int(dd.argmin())),
                  longest_dd_years=float(_longest_underwater(v) / 252))
        out["portfolios"].append(dict(name=p.get("name", ""), alloc=p["alloc"], growth=v[ix].round(2).tolist(), drawdown=(dd[ix] * 100).round(2).tolist(),
                                      annual=(ann * 100).round(2).tolist(), rolling={k: [None if x is None else round(x * 100, 2) for x in r] for k, r in roll.items()},
                                      stats={k: (None if not np.isfinite(x) else round(float(x), 4)) if isinstance(x, float) else x for k, x in st.items()}))
    return out

def _longest_underwater(v):
    peak = np.maximum.accumulate(v); under = v < peak * 0.9999; best = cur = 0
    for u in under: cur = cur + 1 if u else 0; best = max(best, cur)
    return best

# ------------------------------------------------------------------ the printer running on real history
def printer(spec, tax):
    return mp.Printer(spec.get("name", "p"), {t + "SIM": int(w) for t, w in spec["alloc"]}, base=float(spec["base"]),
                      skim=None if spec.get("skim") is None else float(spec["skim"]), bucket_months=int(spec.get("bucket", 36)),
                      cut_below=float(spec.get("cut_below", 0.7)), cut_to=float(spec.get("cut_to", 0.8)), tax=tax)

def history(specs, tax, start=None, end=None):
    i0, i1 = span(start, end); L = i1 - i0 + 1; IDX = torch.tensor(i0 + np.arange(L), device=mp.DEV)[None]
    with GPU: r = mp.simulate([printer(s, tax) for s in specs], IDX, trace=True)
    S = 252; mo = (np.arange(L) * 12) // S; first = np.r_[0, np.flatnonzero(np.diff(mo)) + 1]   # first day of each model month
    M = min(r["spend"].shape[2], len(first) - 1)                                   # complete months only
    ix = thin(L); out = dict(start=iso(i0), end=iso(i1), dates=[int(CAL[i0 + i]) for i in ix], months=[int(CAL[i0 + first[m + 1]]) for m in range(M)], printers=[])
    for c, s in enumerate(specs):
        val, bkt, inf, mult = (r[f"trace_{k}"][c, 0] for k in ("value", "bucket", "infl", "mult"))
        real_tot = (val + bkt) / inf; paid = r["spend"][c, 0, :M]                     # paid each month, real fraction of start
        cut = mult[first[1:M + 1]] < 0.999; y = paid[:(M // 12) * 12].reshape(-1, 12).sum(1)
        dd = real_tot / np.maximum.accumulate(real_tot) - 1
        out["printers"].append(dict(name=s.get("name", ""), paid=paid.round(6).tolist(), base_paid=(s["base"] / 100 / 12 * mult[first[1:M + 1]]).round(6).tolist(),
            cut=cut.astype(int).tolist(), real=real_tot[ix].round(5).tolist(), nominal=(val + bkt)[ix].round(5).tolist(), bucket=(bkt / inf)[ix].round(5).tolist(),
            real_dd=(dd[ix] * 100).round(2).tolist(),
            summary=dict(total_paid=float(paid.sum()), avg_year=float(paid.sum() / (M / 12)), worst_year=float(y.min()) if len(y) else None,
                         best_year=float(y.max()) if len(y) else None, months_cut=int(cut.sum()), end_real=float(real_tot[-1]), low_real=float(real_tot.min()),
                         low_date=iso(i0 + int(real_tot.argmin())), max_real_dd=float(dd.min() * 100), ran_dry=bool(r["dead"][c, 0]),
                         taxes=float(r["tax"][c, 0] * (L / S)))))
    return out

# ------------------------------------------------------------------ simulated futures
def fan(spec, tax, paths=500, years=40):
    IDX = mp.make_idx(paths, years, step=5, seed=4242)
    with GPU: r = mp.simulate([printer(spec, tax)], IDX, step=5)
    bal = np.c_[np.ones(paths), r["yreal"][0]]; sp = r["spend"][0]; inc = sp[:, :years * 12].reshape(paths, years, 12).sum(2)
    q = [5, 10, 25, 50, 75, 90, 95]
    return dict(years=list(range(years + 1)), q=q, balance=np.percentile(bal, q, axis=0).round(4).tolist(), income=np.percentile(inc, q, axis=0).round(5).tolist(),
                below_start=(bal < 1).mean(0).round(4).tolist(), dry=float(r["dead"][0].mean()), paths=paths)

# ------------------------------------------------------------------ evaluate any printer (e.g. a blend between atlas cells)
_at = None; _EVAL_IDX = None
def evaluate(spec, tax):
    """The atlas's own fresh-history stats for one printer: same 600 histories (seed 909), base case + trend stress, so numbers
    are directly comparable with the cached cells."""
    global _at, _EVAL_IDX
    if _at is None:
        _argv = sys.argv; sys.argv = sys.argv[:1]; import atlas as _a; sys.argv = _argv; _at = _a
    p = printer(spec, tax)
    with GPU:
        if _EVAL_IDX is None: _EVAL_IDX = mp.make_idx(_at.FRESH, _at.YEARS, step=_at.STEP, seed=909)
        rb = mp.simulate([p], _EVAL_IDX, step=_at.STEP); rs = mp.simulate([p], _EVAL_IDX, step=_at.STEP, trend_haircut=0.02)
    return {k: round(float(v), 4) for k, v in _at.display_stats(rb, rs, 0, p).items()}
