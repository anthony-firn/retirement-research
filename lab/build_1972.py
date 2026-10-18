"""Component dataset 1972-2026 for the GPU optimiser (clean_1972.json), same format as clean_etf.json.
Every ETF is its testfol SIM series where it exists; earlier history uses the documented proxies from
strategy/history70s.py (KMLM -> haircut trend proxy, DBMF -> 0.709 x MF leg + 0.291 x T-bills, QQQ -> XLK,
TQQQ -> TECL (3x tech), QLD -> 2x XLK, BND -> IEI, GSG -> XLE before 1979). Series that go to zero are dropped."""
import json, os, sys, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, "..", "strategy"))
import history70s as h
import b40_risk as br                                   # provides the DBMF construction on history70s.CAL
NAMES = ["VTISIM", "VEASIM", "VTVSIM", "VBRSIM", "XLPSIM", "XLUSIM", "XLVSIM", "SPMOSIM", "REITSIM", "BNDSIM", "SHYSIM", "IEISIM", "IEFSIM",
         "TLTSIM", "ZROZSIM", "GLDSIM", "SLVSIM", "GSGSIM", "UUPSIM", "KMLMSIM", "DBMFSIM", "TYDSIM", "TMFSIM", "UBTSIM", "TQQQSIM", "QQQSIM",
         "QLDSIM", "XLESIM", "XLBSIM", "XLFSIM", "XLISIM", "XLKSIM", "XLYSIM", "XLCSIM", "VUGSIM", "VVSIM", "VOSIM", "VOESIM", "VOTSIM", "VBSIM",
         "VBKSIM", "IWCSIM", "UPROSIM", "SSOSIM", "SPXLSIM", "UGLSIM", "NTSXSIM", "GDESIM", "RSSBSIM", "NTSISIM", "EFASIM", "VXUSSIM", "URTHSIM", "VTSIM"]
SUB = dict(br.SUB)
def comp(n):
    if n == "KMLMSIM": r = br.kmlm_leg
    elif n == "DBMFSIM": r = br.dbmf
    elif n in SUB: r = SUB[n]
    else: s = h.series(n); r = h.rets(np.nan_to_num(s, nan=np.nan)); r[np.isnan(np.r_[np.nan, s[:-1]])] = np.nan
    return np.asarray(r, float)
if __name__ == "__main__":
    out_n, out_v = [], []
    for n in NAMES:
        r = comp(n)
        if np.isnan(r[1:]).any(): print(f"  skip {n}: no data back to 1972"); continue
        v = np.cumprod(1 + np.nan_to_num(r))
        if v.min() <= 1e-9: print(f"  skip {n}: goes to zero"); continue
        out_n.append(n); out_v.append((v / v[0]).tolist())
    rf = np.cumprod(1 + h.rf); t = h.CAL.tolist()
    json.dump({"names": out_n, "t": t, "v": out_v, "rf": (rf / rf[0]).tolist()}, open(os.path.join(ROOT, "clean_1972.json"), "w"))
    print(f"clean_1972.json: {len(out_n)} assets, {len(t)} days from 1971-12-31")
