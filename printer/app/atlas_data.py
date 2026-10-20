"""The Printer Atlas as the app serves it: printers used by any slider cell or on any account's Pareto frontier, their fresh-history
stats per account, the slider cells, plain fund names, and benchmark printers. Source: results/printer_atlas.json (atlas.py validate)."""
import os, json, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); RESULTS = os.path.join(ROOT, "..", "..", "results")
FUNDS = {  # ticker: (plain name, class)  classes: stocks, boost (leveraged / stacked), trend, gold, bonds
    "VBR": ("Vanguard Small-Cap Value: small US value companies", "stocks"), "VTI": ("Vanguard Total Stock Market: the whole US market", "stocks"),
    "VTV": ("Vanguard Value: large US value companies", "stocks"), "XLV": ("Health Care Select Sector SPDR", "stocks"),
    "XLP": ("Consumer Staples Select Sector SPDR", "stocks"), "XLU": ("Utilities Select Sector SPDR", "stocks"), "XLE": ("Energy Select Sector SPDR", "stocks"),
    "SPMO": ("Invesco S&P 500 Momentum", "stocks"), "REIT": ("US real-estate investment trusts", "stocks"),
    "DBMF": ("iMGP DBi Managed Futures: trend-following", "trend"), "KMLM": ("KraneShares Mount Lucas Managed Futures: trend-following", "trend"),
    "GLD": ("SPDR Gold Shares (GLDM / IAUM: same gold, lower fee)", "gold"), "UGL": ("ProShares Ultra Gold: 2x gold, K-1 tax form", "boost"),
    "GDE": ("WisdomTree Efficient Gold Plus Equity: 90% S&P 500 + 90% gold", "boost"), "NTSX": ("WisdomTree US Efficient Core: 90% stocks + 60% Treasuries", "boost"),
    "RSSB": ("Return Stacked Global Stocks & Bonds: 100% + 100%", "boost"), "TQQQ": ("ProShares UltraPro QQQ: 3x Nasdaq-100", "boost"),
    "QLD": ("ProShares Ultra QQQ: 2x Nasdaq-100", "boost"), "TYD": ("Direxion Daily 7-10 Yr Treasury Bull 3x", "boost"),
    "TMF": ("Direxion Daily 20+ Yr Treasury Bull 3x", "boost"), "UBT": ("ProShares Ultra 20+ Year Treasury: 2x", "boost"),
    "IEI": ("iShares 3-7 Year Treasury Bond", "bonds"), "IEF": ("iShares 7-10 Year Treasury Bond", "bonds"), "TLT": ("iShares 20+ Year Treasury Bond", "bonds"),
    "ZROZ": ("PIMCO 25+ Year Zero Coupon US Treasury", "bonds"), "SHY": ("iShares 1-3 Year Treasury Bond", "bonds"), "BND": ("Vanguard Total Bond Market", "bonds"),
    "UUP": ("Invesco DB US Dollar Bullish: K-1 tax form", "bonds"),
}
ACCOUNTS = {"roth": "Roth IRA (tax-free)", "taxable_low": "Taxable, low income", "taxable_mid": "Taxable, middle income"}
# reference printers for comparisons (classic portfolios run with the default printer rules: 4% base, skim above 125%, 36-month bucket)
BENCHMARKS = [dict(name="60/40 (VTI 60 · BND 40)", alloc=[["VTI", 60], ["BND", 40]], base=4.0, skim=0.25, bucket=36, cut_below=0.7, cut_to=0.8),
              dict(name="100% US stocks (VTI)", alloc=[["VTI", 100]], base=4.0, skim=0.25, bucket=36, cut_below=0.7, cut_to=0.8),
              dict(name="CH-12 Printer", alloc=[["DBMF", 25], ["KMLM", 16], ["GLD", 15], ["VBR", 15], ["XLV", 13], ["TYD", 11], ["TQQQ", 5]],
                   base=4.0, skim=0.25, bucket=36, cut_below=0.7, cut_to=0.8),
              dict(name="MP-2", alloc=[["DBMF", 27], ["VBR", 27], ["GDE", 21], ["KMLM", 15], ["GLD", 8], ["TQQQ", 2]],
                   base=5.75, skim=0.40, bucket=48, cut_below=0.7, cut_to=0.65)]
# Pareto frontier per account: printers no other printer beats on every objective at once. Stats are rounded to what a person
# would notice first (0.1% of start a year ~ $8/month per $100k; one percentage point), so near-copies don't all survive.
OBJ = [("typical", 1, .001), ("bad", 1, .001), ("early", 1, .001), ("stress_typical", 1, .001), ("never_cut", 1, .01), ("steady", 1, .01),
       ("left", 1, .05), ("lose", -1, .01), ("dd90", -1, .01), ("dry", -1, .002)]
DRY_MAX = 0.02                                                                    # only printers that run dry in <= 2% of histories
r4 = lambda x: None if x is None else round(float(x), 4)

def pareto(M):
    keep = np.ones(len(M), bool)
    for i in range(len(M)):
        if keep[i] and np.any(np.all(M >= M[i], 1) & np.any(M > M[i], 1)): keep[i] = False
    return np.flatnonzero(keep)

def build(path=None):
    A = json.load(open(path or os.environ.get("ATLAS_OUT", os.path.join(RESULTS, "printer_atlas.json"))))
    nfunds = np.array([len(p["alloc"]) for p in A["printers"]]); front = {}
    for k, a in A["accounts"].items():
        M = np.array([[sg * round(st[o] / q) for o, sg, q in OBJ] for st in a["stats"]], float)
        ok = np.flatnonzero([st["dry"] <= DRY_MAX for st in a["stats"]])
        front[k] = ok[pareto(np.c_[M, -nfunds][ok])].tolist()                    # simplicity (fewer funds) is the 11th objective
    cell_ids = {k: sorted(set(np.array(a["cells"]).ravel().tolist())) for k, a in A["accounts"].items()}
    used = sorted(set().union(*cell_ids.values(), *front.values())); remap = {i: n for n, i in enumerate(used)}
    printers = [dict(alloc=[[t.replace("SIM", ""), w] for t, w in sorted(p["alloc"].items(), key=lambda x: -x[1])], base=r4(p["base"]), skim=r4(p["skim"]),
                     bucket=p["bucket_months"], cut_below=r4(p["cut_below"]), cut_to=r4(p["cut_to"]), tier=p["tier"]) for p in (A["printers"][i] for i in used)]
    missing = {t for p in printers + BENCHMARKS for t, _ in p["alloc"] if t not in FUNDS}
    assert not missing, missing
    data = dict(levels=A["levels"], tiers=[dict(name=t["name"], n=t["n"], lev=t["lev"], k1=t["k1"]) for t in A["tiers"]], paths=A["paths"],
                funds={t: list(v) for t, v in FUNDS.items()}, printers=printers, benchmarks=BENCHMARKS, accounts={})
    for k, a in A["accounts"].items():
        keep = sorted(set(cell_ids[k]) | set(front[k]))
        data["accounts"][k] = dict(label=ACCOUNTS[k], tax=a["tax"], cells=[remap[x] for x in np.array(a["cells"]).ravel().tolist()],
                                   frontier=[remap[i] for i in front[k]], stats={str(remap[i]): {s: r4(v) for s, v in a["stats"][i].items()} for i in keep})
    return data
