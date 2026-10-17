import json,urllib.request,time,os
H=json.load(open("hist_long.json"))
T=["VTVSIM","VBRSIM","XLPSIM","XLUSIM","XLVSIM","USMVSIM","SPMOSIM","QQQSIM","IWMSIM","REITSIM","SHYSIM","TLTSIM","ZROZSIM","SLVSIM","GSGSIM","UUPSIM","PBPSIM","NTSXSIM","GDESIM","RSSBSIM","UGLSIM","SPYSIM"]
for t in T:
    if t in H: continue
    body={"start_date":"1900-01-01","end_date":"2026-10-16","start_val":1,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":{t:100}}]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    try:
        d=json.load(urllib.request.urlopen(req,timeout=180)); h=d["charts"]["history"]
        H[t]={"t":h[0],"v":h[1]}; s=d['stats'][0]
        print(f"{t:10} {d['start_date']}  CAGR {s['cagr']:6.2f} vol {s['std']:5.1f} MDD {s['max_drawdown']:6.1f} sharpe {s['sharpe']:.2f}",flush=True)
    except Exception as e: print(t,"ERR",e)
    time.sleep(1)
json.dump(H,open("hist_long.json","w"))
