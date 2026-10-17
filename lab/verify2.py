import json,urllib.request,time
MAP={"VTI":"VTISIM","BND":"BNDSIM","GLD":"GLDSIM","BIL":"TBILL?E=0.14","TBF":"TLTSIM?L=-1&E=0.9","ZROZ":"ZROZSIM","UUP":"UUPSIM","SHY":"SHYSIM","SPMO":"SPMOSIM","XLV":"XLVSIM","KMLM":"KMLMSIM","QQQ":"QQQSIM","VTV":"VTVSIM","IEF":"IEFSIM"}
P={"Current":{'VTI':30,'BND':10,'BIL':5,'GLD':22,'TBF':10,'DBMF':23},
   "Current+ (ZROZ,UUP)":{'VTI':25,'BND':10,'UUP':5,'GLD':22,'TBF':10,'DBMF':23,'ZROZ':5},
   "FULL#1 search":{'SHY':25,'SPMO':20,'GLD':15,'DBMF':10,'KMLM':10,'UUP':10,'XLV':5,'ZROZ':5},
   "REV#5 search":{'DBMF':25,'VTV':25,'UUP':25,'GLD':20,'QQQ':5}}
def run(label,start,mf):
    def conv(a):
        out={}
        for k,v in a.items():
            t=mf if k=="DBMF" else MAP[k]; out[t]=out.get(t,0)+v
        return out
    body={"start_date":start,"end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":conv(a)} for a in P.values()]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180))
    print(f"\n== testfol.io {label}  [{d['start_date']} → {d['end_date']}] limiting={d['limiting_ticker']} errors={d['errors']}")
    print(f"{'':22}  CAGR   Vol    MDD Sharpe Sortino Calmar Ulcer")
    for n,s in zip(P,d["stats"]):
        print(f"{n:22} {s['cagr']:5.2f} {s['std']:5.2f} {s['max_drawdown']:6.2f} {s['sharpe']:5.2f} {s['sortino']:6.2f} {s['calmar']:6.2f} {s['ulcer_index']:5.2f}")
run("1988-2026, KMLMSIM in place of DBMF","1988-01-01","KMLMSIM"); time.sleep(1)
run("2000-2026, DBMFSIM","2000-01-01","DBMFSIM")
