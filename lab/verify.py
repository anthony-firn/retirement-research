import json,urllib.request,sys
def pf(a): return {"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":a}
def mk(d,proxy):
    m={"VTISIM":"VTISIM","BNDSIM":"BNDSIM","GLDSIM":"GLDSIM","DBMFSIM":"DBMFSIM",
       "BIL":"TBILL?E=0.14" if proxy else "BIL","TBF":"TLTSIM?L=-1&E=0.9" if proxy else "TBF"}
    return {m[k]:v for k,v in d.items() if v}
P={"Current":{'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':22,'TBF':10,'DBMFSIM':23},
   "Mid tune":{'VTISIM':25,'BNDSIM':13,'BIL':10,'GLDSIM':18,'TBF':6,'DBMFSIM':28},
   "Robust tune":{'VTISIM':20,'BNDSIM':16,'BIL':14,'GLDSIM':15,'TBF':3,'DBMFSIM':32}}
for label,start,proxy in [("2000-2026 (sim TBF/BIL)","2000-01-01",True),("2009-2026 (real TBF/BIL)","2009-08-20",False)]:
    body={"start_date":start,"end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,"backtests":[pf(mk(v,proxy)) for v in P.values()]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180))
    print(f"\n== testfol.io {label}  [{d['start_date']} → {d['end_date']}] errors={d['errors']}")
    print(f"{'':12}  CAGR   Vol    MDD Sharpe Sortino Calmar Ulcer   UPI  End $")
    for n,s in zip(P,d["stats"]):
        print(f"{n:12} {s['cagr']:5.2f} {s['std']:5.2f} {s['max_drawdown']:6.2f} {s['sharpe']:5.2f} {s['sortino']:6.2f} {s['calmar']:6.2f} {s['ulcer_index']:5.2f} {s['upi']:5.2f} {s['end_val']:7.0f}")
