import json,urllib.request,time
P={"Current":{'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':22,'TBF':10,'DBMFSIM':23},
   "Current+":{'VTISIM':25,'BNDSIM':10,'UUPSIM':5,'GLDSIM':22,'TBF':10,'DBMFSIM':23,'ZROZSIM':5},
   "Mid tune":{'VTISIM':25,'BNDSIM':13,'BIL':10,'GLDSIM':18,'TBF':6,'DBMFSIM':28},
   "Robust tune":{'VTISIM':20,'BNDSIM':16,'BIL':14,'GLDSIM':15,'TBF':3,'DBMFSIM':32},
   "FULL#1":{'SHYSIM':25,'SPMOSIM':20,'GLDSIM':15,'DBMFSIM':10,'KMLMSIM':10,'UUPSIM':10,'XLVSIM':5,'ZROZSIM':5},
   "REV#5":{'DBMFSIM':25,'VTVSIM':25,'UUPSIM':25,'GLDSIM':20,'QQQSIM':5}}
def call(start,ps,proxy):
    sub=lambda a:{("TBILL?E=0.14" if k=="BIL" else "TLTSIM?L=-1&E=0.9" if k=="TBF" else k) if proxy else k:v for k,v in a.items()}
    body={"start_date":start,"end_date":"2026-10-16","start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":sub(P[n])} for n in ps]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    return json.load(urllib.request.urlopen(req,timeout=180))
res={}
for w,start,proxy in [("2009","2009-08-20",False),("2000","2000-01-03",True)]:
    names=list(P); out=[]
    for chunk in (names[:3],names[3:]):
        d=call(start,chunk,proxy); time.sleep(1)
        print(w,chunk,d["start_date"],d["end_date"],"limiting:",d["limiting_ticker"],"errors:",d["errors"])
        ann={r[0]:r[1::2] for r in d["annual_returns"]}
        for i,(n,s) in enumerate(zip(chunk,d["stats"])):
            res.setdefault(w,{})[n]=dict(start=d["start_date"],end=d["end_date"],cagr=s["cagr"],std=s["std"],mdd=s["max_drawdown"],sharpe=s["sharpe"],sortino=s["sortino"],calmar=s["calmar"],ulcer=s["ulcer_index"],upi=s["upi"],end_val=s["end_val"],
                y2008=ann.get(2008,[None]*3)[i],y2022=ann.get(2022,[None]*3)[i],y2002=ann.get(2002,[None]*3)[i])
json.dump(res,open("final.json","w"),indent=1)
for w in res:
    print(f"\n== window {w}")
    for n,s in res[w].items(): print(f"{n:12} CAGR {s['cagr']:5.2f} vol {s['std']:5.2f} MDD {s['mdd']:6.2f} Sh {s['sharpe']:.2f} So {s['sortino']:.2f} Cal {s['calmar']:.2f} Ulc {s['ulcer']:.2f} UPI {s['upi']:.2f} end {s['end_val']:.0f} 2002 {s['y2002']} 2008 {s['y2008']} 2022 {s['y2022']}")
