"""Market-indicator states on the 1972-2026 calendar (history70s.CAL), computed only from data available at the time.
Each is 0/1 per day; the printer reads them once a month (at the withdrawal) and tilts target weights while a signal is on.
  trend_off   S&P 500 total-return index below its 210-day (10-month) average
  vol_high    S&P 500 63-day realized volatility above 20% a year
  curve_inv   10-year Treasury yield below the 3-month T-bill yield (Yahoo ^TNX, ^IRX)
  infl_high   CPI up more than 4% over the past 12 months (lagged 21 trading days for publication delay)
  gold_off    gold below its 210-day average"""
import os, sys, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, "..")); sys.path.insert(0, os.path.join(ROOT, "..", "strategy"))
import history70s as h
NAMES = ["trend_off", "vol_high", "curve_inv", "infl_high", "gold_off"]

def _sma(x, n):
    c = np.cumsum(np.r_[0, x]); out = np.full(len(x), np.nan); out[n - 1:] = (c[n:] - c[:-n]) / n; return out

def _yahoo_on_cal(t):
    from engine.data import sources as src
    ts, v = src.yahoo(t, field="close"); ts = np.array(ts); v = np.array(v, float); i = np.searchsorted(ts, h.CAL, side="right") - 1
    out = np.where(i >= 0, v[np.clip(i, 0, None)], np.nan); return out

def compute():
    spy = h.series("SPYSIM"); gld = h.series("GLDSIM"); r = np.r_[0, spy[1:] / spy[:-1] - 1]
    vol = np.sqrt(_sma(r ** 2, 63) * 252)
    tnx, irx = _yahoo_on_cal("^TNX"), _yahoo_on_cal("^IRX")
    cpi = np.asarray(h.cpi, float); lag = 21; yoy = np.full(len(cpi), np.nan); yoy[252 + lag:] = cpi[252:-lag] / cpi[:-252 - lag] - 1
    S = np.stack([spy < _sma(spy, 210), vol > 0.20, tnx < irx, yoy > 0.04, gld < _sma(gld, 210)], 1).astype(np.float32)
    S[np.isnan(np.stack([_sma(spy, 210), vol, tnx - irx, yoy, _sma(gld, 210)], 1))] = 0
    return S

_cache = os.path.join(ROOT, "signals_cache.npy")
def load():
    if os.path.exists(_cache) and os.path.getmtime(_cache) > os.path.getmtime(__file__): return np.load(_cache)
    S = compute(); np.save(_cache, S); return S

if __name__ == "__main__":
    import datetime as dt
    S = load(); yrs = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in h.CAL])
    print("share of days each signal is ON:")
    for k, n in enumerate(NAMES): print(f"  {n:10} all {S[:, k].mean()*100:4.0f}% | 1972-99 {S[yrs < 2000, k].mean()*100:4.0f}% | 2000-26 {S[yrs >= 2000, k].mean()*100:4.0f}% | today {'ON' if S[-1, k] else 'off'}")
