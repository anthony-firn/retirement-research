import json,urllib.request,time
T=["VTISIM","VEASIM","VWOSIM","BNDSIM","IEFSIM","GLDSIM","TLTSIM?L=-1&E=0.9","TBILL?E=0.14","TBILL","DBMFSIM","KMLMSIM","MCISIM"]
out={}
for t in T:
    body={"start_date":"1900-01-01","end_date":"2026-10-16","start_val":1,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":{t:100}}]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180)); h=d["charts"]["history"]
    out[t]={"t":h[0],"v":h[1]}; print(f"{t:22} {d['start_date']} {len(h[0])} days  CAGR {d['stats'][0]['cagr']:.2f}")
    time.sleep(1)
json.dump(out,open("hist_long.json","w"))
