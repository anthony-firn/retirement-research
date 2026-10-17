"""Forward-looking stress test: hypothetical one-shot asset moves for plausible 2026-27 scenarios.
Assumptions are rough judgement calls (see results/MARKET_2026-10.md), not forecasts. Leveraged ETFs are
approximated as leverage x underlying move (capped at -95%), ignoring path effects.
Usage: python3 stress_forward.py S12 <other portfolio names from results/portfolios.json>"""
import json, os, sys
PF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "portfolios.json")))
# underlying moves (%) per scenario
SC = {
 "AI bust (Nasdaq -45%, yields -100bp)":      dict(NDX=-45, SPX=-30, SV=-25, MID=-25, IEI=5, IEF=8, LT=15, SHY=2, GLD=8, KMLM=10, UUP=5, HC=-10, STP=-5, NRG=-20, CMD=-15, REIT=-25, SLV=0),
 "Oil stagflation (Brent $150, 10y +100bp)":   dict(NDX=-25, SPX=-20, SV=-20, MID=-20, IEI=-3, IEF=-7, LT=-15, SHY=0, GLD=15, KMLM=20, UUP=5, HC=-8, STP=-5, NRG=35, CMD=30, REIT=-20, SLV=10),
 "Bond revolt (10y -> 6.5%, stocks -15%)":     dict(NDX=-20, SPX=-15, SV=-15, MID=-15, IEI=-5, IEF=-10, LT=-20, SHY=0, GLD=-5, KMLM=12, UUP=4, HC=-8, STP=-6, NRG=0, CMD=0, REIT=-20, SLV=-5),
 "Deflationary recession (Fed -200bp)":        dict(NDX=-30, SPX=-25, SV=-30, MID=-28, IEI=8, IEF=12, LT=20, SHY=3, GLD=10, KMLM=5, UUP=3, HC=-10, STP=-5, NRG=-30, CMD=-30, REIT=-30, SLV=-5),
 "Dollar crisis / debasement":                 dict(NDX=-5, SPX=-5, SV=-3, MID=-4, IEI=-3, IEF=-5, LT=-10, SHY=0, GLD=30, KMLM=8, UUP=-12, HC=-3, STP=-2, NRG=10, CMD=15, REIT=-5, SLV=35),
 "Soft landing, AI keeps going":               dict(NDX=25, SPX=15, SV=12, MID=12, IEI=3, IEF=4, LT=6, SHY=1, GLD=5, KMLM=-5, UUP=-3, HC=8, STP=6, NRG=-5, CMD=-5, REIT=10, SLV=5),
}
MAP = {  # ticker -> (underlying, leverage)
 "TQQQSIM": ("NDX", 3), "QLDSIM": ("NDX", 2), "QQQSIM": ("NDX", 1), "TECLSIM": ("NDX", 3.3), "XLKSIM": ("NDX", 1.1), "SPMOSIM": ("NDX", 0.9),
 "VTISIM": ("SPX", 1), "SPYSIM": ("SPX", 1), "VVSIM": ("SPX", 1), "UPROSIM": ("SPX", 3), "SPXLSIM": ("SPX", 3), "SSOSIM": ("SPX", 2), "VTVSIM": ("SV", 0.8),
 "VBRSIM": ("SV", 1), "VOESIM": ("MID", 1), "IWMSIM": ("SV", 1.1), "XLVSIM": ("HC", 1), "XLPSIM": ("STP", 1), "XLESIM": ("NRG", 1), "XLYSIM": ("SPX", 1.2),
 "IEISIM": ("IEI", 1), "IEFSIM": ("IEF", 1), "TYDSIM": ("IEF", 3), "TLTSIM": ("LT", 1), "ZROZSIM": ("LT", 1.6), "TMFSIM": ("LT", 3), "UBTSIM": ("LT", 2),
 "SHYSIM": ("SHY", 1), "BNDSIM": ("IEI", 1), "GLDSIM": ("GLD", 1), "UGLSIM": ("GLD", 2), "SLVSIM": ("SLV", 1), "KMLMSIM": ("KMLM", 1), "DBMFSIM": ("KMLM", 0.8),
 "UUPSIM": ("UUP", 1), "GSGSIM": ("CMD", 1), "REITSIM": ("REIT", 1), "GDESIM": ("GLD", 0.9),
}
names = sys.argv[1:] or ["S12"]
print(f"{'scenario':42}" + "".join(f"{n:>10}" for n in names))
for sc, mv in SC.items():
    row = []
    for n in names:
        tot = 0.0
        for t, w in PF[n]["alloc"].items():
            u, lev = MAP[t]; r = max(-95.0, lev * mv[u])
            if t == "GDESIM": r = 0.9 * mv["GLD"] + 0.9 * mv["SPX"]
            tot += w / 100 * r
        row.append(tot)
    print(f"{sc:42}" + "".join(f"{x:+10.1f}" for x in row))
