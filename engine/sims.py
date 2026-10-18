"""Our own SIM recipes (mirroring testfol's documented sources in lab/sim_catalog.csv). Each splices an older
proxy onto the real fund, scaling at the join so the index is continuous."""
import numpy as np
from .data import sources

def splice(*parts):
    """parts: (t, v) series ordered oldest -> newest; each later part takes over from its first date."""
    t0, v0 = map(np.asarray, parts[0]); T, V = list(t0), list(v0)
    for t, v in parts[1:]:
        t, v = np.asarray(t), np.asarray(v); start = t[0]
        keep = [i for i, x in enumerate(T) if x < start]; T = [T[i] for i in keep]; V = [V[i] for i in keep]
        if T:
            prev = np.searchsorted(t0 := np.array(T), start) - 1; scale = V[-1] / v[0]      # join at the new fund's first close
        else: scale = 1.0
        T += list(t); V += list(v * scale)
    return np.array(T), np.array(V)

def VTISIM():
    """US total market: Fama-French Rm-Rf + Rf -> VTSMX (1992-04-27) -> VTI (2001-06-15)."""
    return splice(sources.french_market_daily(), sources.yahoo("VTSMX"), sources.yahoo("VTI"))

RECIPES = {"VTISIM": VTISIM}
