"""Build a testfol.io share link (?d=base64(zlib(json))) for portfolios in results/portfolios.json.
Usage: python3 make_link.py R1 FULL#1 Current   [--open]"""
import json,zlib,base64,urllib.parse,sys,subprocess,os
P=json.load(open(os.path.join(os.path.dirname(__file__),"..","results","portfolios.json")))
def pf(name,alloc):
    return {"name":name,"tickers":[{"ticker":k,"percent":v} for k,v in alloc.items()],"investDividends":True,"rebalanceFreq":"Yearly","rebalanceOffset":0,
            "drag":0,"absoluteDev":0,"relativeDev":0,"rebalanceBandMode":"SYMMETRIC","absoluteDevBelow":0,"absoluteDevAbove":0,"relativeDevBelow":0,"relativeDevAbove":0}
gp={"start_date":"1987-12-31","end_date":"","start_val":10000,"adj_inflation":False,"adjust_cashflows_for_inflation":False,"annual_cashflow_growth_rate":0,
    "target_currency":"USD","cashflow":0,"cashflow_freq":"Yearly","cashflow_offset":0,"match_first_portfolio_income_cashflows":False,"one_time_cashflows":[],
    "rolling_window":60,"withdrawal_surface_include":False,"withdrawal_surface_projection":"NONE","withdrawal_surface_projection_min_years":10,
    "withdrawal_surface_start_years":5,"withdrawal_surface_end_years":50,"withdrawal_surface_step_years":1,"cashflow_legs":[]}
names=[a for a in sys.argv[1:] if not a.startswith("--")]
data={"globalParams":gp,"portfolios":[pf(n,P[n]["alloc"]) for n in names],"glidePortfolios":[]}
d=base64.b64encode(zlib.compress(json.dumps(data,separators=(",",":")).encode(),9)).decode()
url="https://testfol.io/?d="+urllib.parse.quote(d,safe="")
print(url)
if "--open" in sys.argv: subprocess.Popen(["xdg-open",url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
