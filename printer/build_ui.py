"""Build the Money Printer Forge page (printer/ui/forge.html): the slider UI with the whole Printer Atlas inlined.
Reads results/printer_atlas.json (python3 printer/atlas.py validate) and printer/ui/template.html.
Usage: python3 printer/build_ui.py [bare_output.html]"""
import os, sys, json, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
A = json.load(open(os.environ.get("ATLAS_OUT", os.path.join(ROOT, "..", "results", "printer_atlas.json"))))
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
r4 = lambda x: None if x is None else round(float(x), 4)

# Pareto frontier per account: printers no other printer beats on every objective at once. Stats are rounded to what a person
# would notice first (0.1% of start a year ~ $8/month per $100k; one percentage point), so near-copies don't all survive.
OBJ = [("typical", 1, .001), ("bad", 1, .001), ("early", 1, .001), ("stress_typical", 1, .001), ("never_cut", 1, .01), ("steady", 1, .01),
       ("left", 1, .05), ("lose", -1, .01), ("dd90", -1, .01), ("dry", -1, .002)]
DRY_MAX = 0.02                                                                    # only printers that run dry in <= 2% of histories
def pareto(M):
    keep = np.ones(len(M), bool)
    for i in range(len(M)):
        if keep[i] and np.any(np.all(M >= M[i], 1) & np.any(M > M[i], 1)): keep[i] = False
    return np.flatnonzero(keep)
nfunds = np.array([len(p["alloc"]) for p in A["printers"]])
front = {}
for k, a in A["accounts"].items():
    M = np.array([[sg * round(st[o] / q) for o, sg, q in OBJ] for st in a["stats"]] , float)
    ok = np.flatnonzero([st["dry"] <= DRY_MAX for st in a["stats"]])
    front[k] = ok[pareto(np.c_[M, -nfunds][ok])].tolist()                        # simplicity (fewer funds) is the 11th objective
    print(f"  {k}: {len(front[k])} of {len(M)} printers on the frontier")
cell_ids = {k: sorted({x for x in np.array(a["cells"]).ravel().tolist()}) for k, a in A["accounts"].items()}
used = sorted(set().union(*cell_ids.values(), *front.values())); remap = {i: n for n, i in enumerate(used)}
printers = []
for i in used:
    p = A["printers"][i]
    printers.append(dict(alloc=[[t.replace("SIM", ""), w] for t, w in sorted(p["alloc"].items(), key=lambda x: -x[1])], base=r4(p["base"]),
                         skim=r4(p["skim"]), bucket=p["bucket_months"], cut_below=r4(p["cut_below"]), cut_to=r4(p["cut_to"]), tier=p["tier"]))
missing = {t for p in printers for t, _ in p["alloc"] if t not in FUNDS}
assert not missing, missing
data = dict(levels=A["levels"], tiers=[dict(name=t["name"], n=t["n"], lev=t["lev"], k1=t["k1"]) for t in A["tiers"]], paths=A["paths"],
            funds={t: list(v) for t, v in FUNDS.items()}, printers=printers, accounts={})
for k, a in A["accounts"].items():
    flat = [remap[x] for x in np.array(a["cells"]).ravel().tolist()]
    keep = sorted(set(cell_ids[k]) | set(front[k]))
    data["accounts"][k] = dict(label=ACCOUNTS[k], cells=flat, frontier=[remap[i] for i in front[k]],
                               stats={str(remap[i]): {s: r4(v) for s, v in a["stats"][i].items()} for i in keep})
tpl = open(os.path.join(ROOT, "ui", "template.html")).read()
out = tpl.replace("__ATLAS_DATA__", json.dumps(data, separators=(",", ":")))
open(os.path.join(ROOT, "ui", "forge.html"), "w").write('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n' + out + "\n</body></html>\n")
if len(sys.argv) > 1: open(sys.argv[1], "w").write(out)                      # bare page for the Artifact publisher (it adds the skeleton)
print(f"printer/ui/forge.html: {len(printers)} printers, {len(out)/1024:.0f} KB")
