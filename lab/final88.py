import json,urllib.request,time
P={"Current":{'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':22,'TBF':10,'DBMF':23},
   "Current+":{'VTISIM':25,'BNDSIM':10,'UUPSIM':5,'GLDSIM':22,'TBF':10,'DBMF':23,'ZROZSIM':5},
   "Mid tune":{'VTISIM':25,'BNDSIM':13,'BIL':10,'GLDSIM':18,'TBF':6,'DBMF':28},
   "Robust tune":{'VTISIM':20,'BNDSIM':16,'BIL':14,'GLDSIM':15,'TBF':3,'DBMF':32},
   "FULL#1":{'SHYSIM':25,'SPMOSIM':20,'GLDSIM':15,'DBMF':10,'KMLMSIM':10,'UUPSIM':10,'XLVSIM':5,'ZROZSIM':5},
   "REV#5":{'DBMF':25,'VTVSIM':25,'UUPSIM':25,'GLDSIM':20,'QQQSIM':5}}
SUB={"BIL":"TBILL?E=0.14","TBF":"TLTSIM?L=-1&E=0.9","DBMF":"KMLMSIM"}
def conv(a):
    o={}
    for k,v in a.items(): t=SUB.get(k,k); o[t]=o.get(t,0)+v
    return o
res={}; names=list(P)
for chunk in (names[:3],names[3:]):
    body={"start_date":"1987-12-31","end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":conv(P[n])} for n in chunk]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180)); time.sleep(1)
    print(chunk,d["start_date"],"->",d["end_date"],"limiting:",d["limiting_ticker"],"errors:",d["errors"])
    ann={r[0]:r[1::2] for r in d["annual_returns"]}
    for i,(n,s) in enumerate(zip(chunk,d["stats"])):
        res[n]=dict(alloc=conv(P[n]),cagr=s["cagr"],std=s["std"],mdd=s["max_drawdown"],sharpe=s["sharpe"],sortino=s["sortino"],calmar=s["calmar"],ulcer=s["ulcer_index"],upi=s["upi"],end_val=s["end_val"],
            **{f"y{y}":ann[y][i] for y in (1994,2002,2008,2022)},worst=min(v[i] for v in ann.values()))
json.dump(res,open("final88.json","w"),indent=1)
for n,s in res.items(): print(f"{n:12} CAGR {s['cagr']:5.2f} vol {s['std']:5.2f} MDD {s['mdd']:6.2f} Sh {s['sharpe']:.2f} So {s['sortino']:.2f} Cal {s['calmar']:.2f} Ulc {s['ulcer']:.2f} UPI {s['upi']:.2f} end {s['end_val']:.0f} | 94 {s['y1994']} 02 {s['y2002']} 08 {s['y2008']} 22 {s['y2022']} worstyr {s['worst']}")
