import json,urllib.request,sys
def pf(a,freq="Yearly"): return {"invest_dividends":True,"rebalance_freq":freq,"rebalance_offset":0,"drag":0,"allocation":a}
user={"VTISIM":30,"BNDSIM":10,"BIL":5,"GLDSIM":22,"TBF":10,"DBMFSIM":23}
if len(sys.argv)>2: user={"VTISIM":30,"BNDSIM":10,"TBILL?E=0.14":5,"GLDSIM":22,"TLTSIM?L=-1&E=0.9":10,"DBMFSIM":23}
body={"start_date":sys.argv[1],"end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
 "backtests":[pf(user),pf({"SPYSIM":100}),pf({"VTISIM":60,"BNDSIM":40})]}
req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
d=json.load(urllib.request.urlopen(req,timeout=120))
json.dump(d,open(f"resp_{sys.argv[1]}.json","w"))
print("errors",d["errors"],"limiting",d["limiting_ticker"],d["start_date"],d["end_date"])
names=["Yours","SPYSIM","60/40"]
keys=["cagr","std","max_drawdown","max_drawdown_peak_date","max_drawdown_recovery_date","sharpe","sortino","calmar","ulcer_index","end_val","beta","benchmark_corr"]
for k in keys: print(f"{k:28}"+"".join(f"{str(round(s[k],2) if isinstance(s[k],float) else s[k]):>14}" for s in d["stats"]))
print("\nYear   Yours  SPYSIM  60/40")
for r in d["annual_returns"]: print(r[0], *[f"{x:7.1f}" for x in r[1::2]])
