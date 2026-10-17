import json,urllib.request
T=["VTISIM","VEASIM","VWOSIM","BNDSIM","TBILL?E=0.14","GLDSIM","TLTSIM?L=-1&E=0.9","DBMFSIM","TBILL"]
pf=lambda t:{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":{t:100}}
def call(ts):
    body={"start_date":"2000-01-01","end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,"backtests":[pf(t) for t in ts]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180)); print(d["errors"],d["start_date"],d["end_date"],[len(x) for x in d["charts"]["history"]])
    return d["charts"]["history"]
a=call(T[:5]); b=call(T[5:])
assert a[0]==b[0]
json.dump({"tickers":T,"t":a[0],"v":a[1:]+b[1:]},open("hist.json","w"))
