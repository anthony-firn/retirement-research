"""The Printer Atlas as the app serves it: every validated candidate printer, its fresh-history stats per account type and horizon,
plain fund names, tax brackets and benchmark printers. Sources: results/printer_atlas.json (atlas.py validate) and
results/printer_horizons.json (atlas.py horizons)."""
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
              dict(name="100% US stocks (VTI)", alloc=[["VTI", 100]], base=4.0, skim=0.25, bucket=36, cut_below=0.7, cut_to=0.8)]
# tax brackets the atlas has a taxable profile for; income_tax = the profile's ordinary rate + state, used on tax-deferred withdrawals
BRACKETS = {"low": dict(label="10–12% federal", taxable="taxable_low", income_tax=0.12),
            "mid": dict(label="22–24% federal", taxable="taxable_mid", income_tax=0.313)}
LEVERED = {"TQQQ", "QLD", "TYD", "TMF", "UGL", "UBT", "GDE", "NTSX", "RSSB"}        # leveraged or stacked (more than 100% exposure)
r4 = lambda x: None if x is None else round(float(x), 4)

def build(atlas_path=None, horizons_path=None):
    """Every validated candidate printer with its stats per account type and horizon (results/printer_horizons.json). The app mixes
    account types by the user's dollars and computes the Pareto frontier for that mix in the browser."""
    A = json.load(open(atlas_path or os.path.join(RESULTS, "printer_atlas.json")))
    Hz = json.load(open(horizons_path or os.environ.get("HORIZONS_OUT", os.path.join(RESULTS, "printer_horizons.json"))))
    printers = []
    for p in A["printers"]:
        al = [[t.replace("SIM", ""), w] for t, w in sorted(p["alloc"].items(), key=lambda x: -x[1])]
        printers.append(dict(alloc=al, base=r4(p["base"]), skim=r4(p["skim"]), bucket=p["bucket_months"], cut_below=r4(p["cut_below"]), cut_to=r4(p["cut_to"]),
                             levered=sum(w for t, w in al if t in LEVERED), k1=any(t in ("UUP", "UGL") for t, _ in al)))
    missing = {t for p in printers + BENCHMARKS for t, _ in p["alloc"] if t not in FUNDS}
    assert not missing, missing
    return dict(horizons=Hz["horizons"], fields=Hz["fields"], paths=Hz["paths"], funds={t: list(v) for t, v in FUNDS.items()}, printers=printers,
                benchmarks=BENCHMARKS, brackets=BRACKETS, accounts={k: dict(label=ACCOUNTS[k], tax=a["tax"], stats=Hz["accounts"][k]) for k, a in A["accounts"].items()})
