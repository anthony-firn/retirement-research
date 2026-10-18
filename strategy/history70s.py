"""Extend every lineup tier back to 1972 so the policy can be tested through the 1970s stagflation.

Components come from testfol.io SIM series (lab/hist_long.json). Missing before 1988 are replaced by documented proxies:
  KMLMSIM -> MF proxy: 12-month time-series momentum on SPY, TLT, GLD, UUP, commodities (GSG; XLE before 1979),
             each leg vol-targeted (60-day), portfolio scaled to KMLM's volatility, plus T-bill collateral.
             Validated against real KMLMSIM 1988-2026 below.
  QQQSIM -> XLKSIM, TQQQSIM -> TECLSIM (3x XLK), QLDSIM -> 2x XLK daily minus borrow, BNDSIM -> IEISIM, GSGSIM -> XLESIM (<1979).
Tiers are rebuilt with yearly rebalancing over 1972-1987 and spliced onto the testfol.io tier series from 1988.
Output: data_portfolios_1972.json (same format as data_portfolios.json) + data_cpi_1972.json"""
import json, os, math, numpy as np, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(ROOT, "..", "lab", "hist_long.json")))
PF = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
P88 = json.load(open(os.path.join(ROOT, "data_portfolios.json"))); IND = json.load(open(os.path.join(ROOT, "data_indicators.json")))
START = int(dt.datetime(1971, 12, 31, tzinfo=dt.UTC).timestamp())

# master calendar: SPYSIM trading days from 1971-12-31
spy_t = np.array(H["SPYSIM"]["t"]); CAL = spy_t[spy_t >= START]
def series(name, src=None):
    s = src or H[name]; t = np.array(s["t"]); v = np.array(s["v"]); idx = np.searchsorted(t, CAL, side="right") - 1
    out = np.where(idx >= 0, v[np.clip(idx, 0, None)], np.nan); out[CAL < t[0]] = np.nan; return out
def rets(v): r = np.r_[0, v[1:] / v[:-1] - 1]; return np.nan_to_num(r)
tb = series(None, IND["TBILL"]); rf = rets(tb); cpi = series(None, IND["INFLATION"])

# ---- managed-futures proxy
legs = {"SPYSIM": rets(series("SPYSIM")), "TLTSIM": rets(series("TLTSIM")), "GLDSIM": rets(series("GLDSIM")), "UUPSIM": rets(series("UUPSIM"))}
gsg = series("GSGSIM"); xle = series("XLESIM"); legs["CMDTY"] = np.where(np.isnan(gsg), rets(xle), rets(np.nan_to_num(gsg, nan=1.0)))
legs["CMDTY"][np.isnan(gsg) & ~np.isnan(np.r_[np.nan, gsg[:-1]])] = 0
def mf_proxy(target_vol=14.2):
    n = len(CAL); R = np.stack(list(legs.values()), 1) - rf[:, None] * 0      # excess not needed: legs are total returns of futures-like assets
    lr = np.log1p(R); cum = np.cumsum(lr, 0)
    mom = np.r_[np.zeros((252, R.shape[1])), cum[252:] - cum[:-252]]           # 12-month return
    sig = np.sign(mom)
    vol = np.sqrt(np.maximum(np.r_[np.zeros((60, R.shape[1])), np.array([R[i - 60:i].var(0) for i in range(60, n)])], 1e-10)) * math.sqrt(252)
    w = sig / vol / R.shape[1]; w = np.r_[np.zeros((1, R.shape[1])), w[:-1]]    # trade next day
    raw = (w * (R - rf[:, None])).sum(1)                                        # futures: earn excess return on positions
    k = target_vol / 100 / (raw[300:].std() * math.sqrt(252)); return rf + k * raw
MF = mf_proxy()
# conservative haircut: remove the proxy's excess return over real KMLMSIM measured 1988-2026 (applied to every day)
_i88 = int(np.searchsorted(CAL, json.load(open(os.path.join(ROOT, "data_portfolios.json")))["t"][0]))
_k = rets(series("KMLMSIM"))[_i88 + 1:]; _p = MF[_i88 + 1:]
HAIRCUT = (np.prod(1 + _p) ** (252 / len(_p)) - np.prod(1 + _k) ** (252 / len(_k))) / 252
MF = MF - HAIRCUT

def blend_series(alloc, sub):
    """Daily returns of a yearly-rebalanced portfolio over CAL with substitutions."""
    comps = {}
    for t, w in alloc.items():
        if t == "KMLMSIM": comps[t] = MF
        elif t in sub: comps[t] = sub[t]
        else: comps[t] = rets(np.nan_to_num(series(t), nan=np.nan)) if t in H else None
        if comps[t] is None: raise KeyError(t)
    years = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in CAL]); out = np.zeros(len(CAL)); wts = None
    for d in range(len(CAL)):
        if d == 0 or years[d] != years[d - 1]: wts = {t: w / 100 for t, w in alloc.items()}
        r = sum(wts[t] * comps[t][d] for t in alloc); out[d] = r / sum(wts.values())
        tot = sum(wts[t] * (1 + comps[t][d]) for t in alloc); wts = {t: wts[t] * (1 + comps[t][d]) / tot * sum(wts.values()) for t in alloc}
    return out

xlk = rets(series("XLKSIM"))
SUB = {"QQQSIM": xlk, "TQQQSIM": rets(series("TECLSIM")), "QLDSIM": 2 * xlk - rf - 0.0095 / 252, "BNDSIM": rets(series("IEISIM")),
       "GSGSIM": legs["CMDTY"], "SPMOSIM": np.nan_to_num(rets(series("SPMOSIM")))}

if __name__ == "__main__":
    i88 = int(np.searchsorted(CAL, P88["t"][0]))
    km = series("KMLMSIM"); kr = rets(km)[i88 + 1:]; pr = MF[i88 + 1:]
    def ann(r): return ((np.prod(1 + r)) ** (252 / len(r)) - 1) * 100
    ym = np.array([dt.datetime.fromtimestamp(x, dt.UTC).strftime("%Y%m") for x in CAL[i88 + 1:]]); e = np.r_[np.flatnonzero(ym[1:] != ym[:-1]), len(ym) - 1]
    mk = np.add.reduceat(np.log1p(kr), np.r_[0, e[:-1] + 1]); mp = np.add.reduceat(np.log1p(pr), np.r_[0, e[:-1] + 1])
    print(f"MF proxy vs real KMLMSIM 1988-2026: CAGR {ann(pr):.2f}% vs {ann(kr):.2f}% | vol {pr.std()*math.sqrt(252)*100:.1f}% vs {kr.std()*math.sqrt(252)*100:.1f}% | monthly corr {np.corrcoef(mk, mp)[0,1]:.2f}")
    yrs = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in CAL])
    for y in (1973, 1974, 1979, 1980, 1981, 1987, 2008, 2022):
        m = yrs == y; print(f"   {y}: proxy {np.prod(1 + MF[m]) * 100 - 100:+6.1f}%" + (f" | KMLM {np.prod(1 + rets(km)[m]) * 100 - 100:+6.1f}%" if y >= 1988 else ""))
    # build tiers 1972-1987 and splice onto testfol series
    names = P88["names"]; out_v = []
    for n in names:
        r = blend_series(PF[n]["alloc"], SUB); pre = np.cumprod(1 + r[:i88 + 1]); scale = pre[-1]
        v88 = np.array(P88["v"][names.index(n)]); v88 = v88 / v88[0] * scale
        out_v.append(np.r_[pre[:-1], v88].tolist())
    T88 = np.array(P88["t"]); full_t = np.r_[CAL[:i88], T88]
    assert all(len(v) == len(full_t) for v in out_v)
    json.dump({"names": names, "t": full_t.tolist(), "v": out_v}, open(os.path.join(ROOT, "data_portfolios_1972.json"), "w"))
    cp = series(None, IND["INFLATION"]); cp88 = np.array(IND["INFLATION"]["v"]); json.dump({"t": full_t.tolist()}, open(os.path.join(ROOT, "data_cpi_1972.json"), "w"))
    print(f"\ntiers extended: {dt.datetime.fromtimestamp(full_t[0], dt.UTC).date()} -> {dt.datetime.fromtimestamp(full_t[-1], dt.UTC).date()}  ({len(full_t)} days)")
    print(f"{'tier':8} 1972-87 CAGR   MDD | 1973-74 | 1979-81 | Oct-1987")
    for n, v in zip(names, out_v):
        v = np.array(v[:i88 + 1]); c = ((v[-1] / v[0]) ** (252 / len(v)) - 1) * 100; mdd = (1 - v / np.maximum.accumulate(v)).max() * 100
        def per(a, b):
            ia = int(np.searchsorted(CAL, int(dt.datetime(*a, tzinfo=dt.UTC).timestamp()))); ib = int(np.searchsorted(CAL, int(dt.datetime(*b, tzinfo=dt.UTC).timestamp())))
            return (v[ib] / v[ia] - 1) * 100
        print(f"{n:8} {c:9.2f} {mdd:6.1f} | {per((1973,1,2),(1974,12,31)):+6.1f}% | {per((1979,1,2),(1981,12,31)):+6.1f}% | {per((1987,10,1),(1987,10,30)):+6.1f}%")
