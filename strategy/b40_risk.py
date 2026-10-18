"""Honest risk profile of Plan-b40 vs Plan-b40-split (KMLM 18 + DBMF 17), with the daily breaker (38% below peak, 1-day lag).
- Daily return series 1972-2026: components from testfol SIM data + documented proxies (history70s.py).
  DBMF before 2000 = 0.709 x managed-futures leg + 0.291 x T-bills (vol-matched to DBMF, as in lab/build_long.py).
- Breaker: when the cushion (38% - drawdown) gets small, the position steps down the lineup ladder (worst-day curve).
- 2000 bootstrapped 40-year histories (1-year and 3-month blocks): early-horizon drawdown and real-loss probabilities.
- Plan level: annual real returns of each strategy (with breaker) feed the no-Social-Security plan -> run-out odds by age."""
import os, json, math, numpy as np
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import policy as pl, history70s as h
ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------- daily series on the policy calendar
T_ts = np.array(pl.D["t"]); T = len(T_ts)
def on_cal(r_cal):                                             # history70s.CAL returns -> policy calendar (compound across gaps)
    lv = np.cumprod(1 + r_cal); idx = np.clip(np.searchsorted(h.CAL, T_ts, side="right") - 1, 0, None); v = lv[idx]
    return np.r_[0, v[1:] / v[:-1] - 1]
kmlm_leg = h.MF.copy(); kml = h.rets(h.series("KMLMSIM")); has_k = ~np.isnan(h.series("KMLMSIM")); kmlm_leg[has_k] = kml[has_k]
dbmf = 0.709 * kmlm_leg + 0.291 * h.rf; d_raw = h.series("DBMFSIM"); has_d = ~np.isnan(d_raw); dbmf[has_d] = h.rets(np.nan_to_num(d_raw, nan=1.0))[has_d]
first_d = np.flatnonzero(has_d)[0]; dbmf[first_d] = 0.709 * kmlm_leg[first_d] + 0.291 * h.rf[first_d]
SUB = dict(h.SUB); SUB["DBMFSIM"] = dbmf
P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
B40 = P["Plan-b40"]["alloc"]; SPLIT = dict(B40); SPLIT.pop("KMLMSIM"); SPLIT = {"KMLMSIM": 18, "DBMFSIM": 17, **SPLIT}
SER = {"Plan-b40": on_cal(h.blend_series(B40, SUB)), "Plan-b40-split": on_cal(h.blend_series(SPLIT, SUB))}
CPI = np.array(json.load(open(os.path.join(ROOT, "data_indicators.json")))["INFLATION"]["v"]); ci = np.array(json.load(open(os.path.join(ROOT, "data_indicators.json")))["INFLATION"]["t"])
cpi = CPI[np.clip(np.searchsorted(ci, T_ts, side="right") - 1, 0, None)]; CPIR = np.r_[1, cpi[1:] / cpi[:-1]]
X_CAP = pl.tier_for_budget(40); L_BRK = 40 - pl.MARGIN_GAP

def ladder_ret(x, d):
    lo = np.floor(x).astype(int).clip(0, len(pl.LADDER) - 1); hi = np.minimum(lo + 1, len(pl.LADDER) - 1); f = x - lo
    return (1 - f) * pl.RET[d, lo] + f * pl.RET[d, hi]

def interp_wd(c):
    curve = pl.WORST_DAY; k = np.clip(np.searchsorted(curve, c, side="right") - 1, 0, len(curve) - 2)
    x = k + np.clip((c - curve[k]) / np.maximum(curve[k + 1] - curve[k], 1e-9), 0, 1)
    return np.where(c <= curve[0], 0.0, np.where(c >= curve[-1], len(curve) - 1.0, x))

def run_paths(name, IDX):
    """IDX: (N, L) day indices. Returns nav (N, L) nominal, real (N, L), engaged flags."""
    N, L = IDX.shape; s = SER[name]; nav = np.ones(N); peak = np.ones(N); x = np.full(N, X_CAP); infl = np.ones(N)
    NAV = np.empty((N, L)); REAL = np.empty((N, L)); eng = np.zeros(N, bool)
    for d in range(L):
        rows = IDX[:, d]
        if d > 0:
            top = x >= X_CAP - 1e-6
            r = np.where(top, s[rows], ladder_ret(np.minimum(x, X_CAP), rows))
            nav = nav * (1 + r); infl = infl * CPIR[rows]
        peak = np.maximum(peak, nav); dd = (1 - nav / peak) * 100
        cushion = np.maximum(L_BRK - dd, 0); gov = np.where(cushion > pl.WORST_DAY[0], interp_wd(cushion), 0.0)
        new = np.minimum(X_CAP, gov); eng |= new < X_CAP - 0.02
        cost = np.where(np.abs(new - x) > 0.02, pl.COST * np.abs(new - x), 0); nav = nav * (1 - cost); x = np.where(np.abs(new - x) > 0.02, new, x)
        NAV[:, d] = nav; REAL[:, d] = nav / infl
    return NAV, REAL, eng

def make_idx(n, years, block, seed):
    g = np.random.default_rng(seed); L = years * 252; nb = L // block + 1
    st = g.integers(1, T - block, size=(n, nb)); return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :L]

def annual_real_history(name):
    IDX = np.arange(1, T)[None, :]; NAV, REAL, _ = run_paths(name, IDX)
    yrs = np.array([int(d[:4]) for d in pl.DATES[1:]]); ends = np.r_[np.flatnonzero(np.diff(yrs)), len(yrs) - 1]
    rv = REAL[0, ends]; nv = NAV[0, ends]; c = cpi[1:][ends]
    return rv[1:] / rv[:-1] - 1, c[1:] / c[:-1] - 1

if __name__ == "__main__":
    out = {}
    print(f"Breaker: {L_BRK:.0f}% below peak, 1-day lag. Top position = static portfolio; breaker steps down the lineup ladder.\n")
    for name in SER:
        r = SER[name][1:]; v = np.cumprod(1 + r); yrs = len(r) / 252
        print(f"{name}: static 1972-2026 CAGR {((v[-1])**(1/yrs)-1)*100:.2f}%, max drop {(1-v/np.maximum.accumulate(v)).max()*100:.1f}%")
    H = [1, 3, 5, 10, 20, 40]; TH = [10, 15, 20, 25, 30]
    for block, lab in ((252, "1-year blocks"), (63, "3-month blocks (harsher)")):
        IDX = make_idx(2000, 40, block, 41)
        for name in SER:
            NAV, REAL, eng = run_paths(name, IDX); dd_run = 1 - NAV / np.maximum.accumulate(NAV, 1)
            print(f"\n=== {name} | {lab} | 2000 histories ===")
            print("   chance of a drop bigger than X% at some point within the first N years:")
            print("   " + f"{'':10}" + "".join(f"{f'{th}%':>8}" for th in TH))
            res = {}
            for hy in H:
                m = dd_run[:, :hy * 252].max(1) * 100; row = [float((m > th).mean() * 100) for th in TH]; res[f"dd_{hy}y"] = row
                print(f"   {f'{hy} yr':10}" + "".join(f"{x:7.1f}%" for x in row))
            print("   chance of being BELOW the starting amount after inflation at year N:  " +
                  "  ".join(f"{hy}y {float((REAL[:, hy * 252 - 1] < 1).mean() * 100):4.1f}%" for hy in (1, 3, 5, 10, 20)))
            yr1 = NAV[:, 251::252]; y_ret = np.c_[yr1[:, :1] - 1, yr1[:, 1:] / yr1[:, :-1] - 1]
            print(f"   worst single year across all histories: {y_ret.min()*100:.1f}%  | chance any given year loses >10%: {(y_ret < -0.10).mean()*100:.1f}%  >20%: {(y_ret < -0.20).mean()*100:.2f}%")
            print(f"   worst drop ever: {dd_run.max()*100:.1f}%  | breaker engaged in {eng.mean()*100:.1f}% of histories")
            out[f"{name}|{lab}"] = res
    json.dump(out, open(os.path.join(ROOT, "b40_risk.json"), "w"), indent=1)
