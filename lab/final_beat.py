import json,urllib.request,time
A=json.load(open("beat_res.json")); Rb=json.load(open("beat_robust_res.json")); names=A["names"]
toalloc=lambda w:{names[j]:int(round(x)) for j,x in enumerate(w) if x>0}
F1={'SHYSIM':25,'SPMOSIM':20,'GLDSIM':15,'KMLMSIM':20,'UUPSIM':10,'XLVSIM':5,'ZROZSIM':5}
P={"FULL#1":F1,"R1":toalloc(Rb["res"][0][0]),"R2":toalloc(Rb["res"][1][0]),"R3":toalloc(Rb["res"][2][0]),"R6":toalloc(Rb["res"][5][0]),
   "#1":toalloc(A["res"][0][0]),"#2":toalloc(A["res"][1][0]),"#5":toalloc(A["res"][4][0]),"#10":toalloc(A["res"][9][0])}
for k,v in P.items(): assert sum(v.values())==100,(k,sum(v.values()))
def call(start,end,ps):
    body={"start_date":start,"end_date":end,"start_val":10000,"adj_inflation":False,"cashflow":0,"cashflow_freq":"Yearly","rolling_window":60,
          "backtests":[{"invest_dividends":True,"rebalance_freq":"Yearly","rebalance_offset":0,"drag":0,"allocation":P[n]} for n in ps]}
    req=urllib.request.Request("https://testfol.io/api/backtest",json.dumps(body).encode(),{"Content-Type":"application/json","User-Agent":"curl/8.5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=180)); time.sleep(1); return d
out={"alloc":P,"full":{},"decades":{}}
for grp in (["FULL#1","R1","R2","R3","R6"],["FULL#1","#1","#2","#5","#10"]):
    d=call("1987-12-31","2026-10-16",grp)
    print(grp,d["start_date"],"->",d["end_date"],"limiting",d["limiting_ticker"],d["errors"])
    ann={r[0]:r[1::2] for r in d["annual_returns"]}
    for i,(n,s) in enumerate(zip(grp,d["stats"])):
        out["full"][n]=dict(cagr=s["cagr"],std=s["std"],mdd=s["max_drawdown"],sharpe=s["sharpe"],sortino=s["sortino"],calmar=s["calmar"],ulcer=s["ulcer_index"],upi=s["upi"],end=s["end_val"],
            y1994=ann[1994][i],y2002=ann[2002][i],y2008=ann[2008][i],y2022=ann[2022][i],worst=min(v[i] for v in ann.values()))
for a,b in [("1987-12-31","1997-12-31"),("1998-01-01","2007-12-31"),("2008-01-01","2017-12-31"),("2018-01-01","2026-10-16")]:
    d=call(a,b,["FULL#1","R1","R2","R3","#1"])
    out["decades"][a[:4]+"-"+b[:4]]={n:dict(cagr=s["cagr"],mdd=s["max_drawdown"],sharpe=s["sharpe"],calmar=s["calmar"],ulcer=s["ulcer_index"]) for n,s in zip(["FULL#1","R1","R2","R3","#1"],d["stats"])}
json.dump(out,open("final_beat.json","w"),indent=1)
for n,a in P.items(): print(n,a)
print()
for n,s in out["full"].items(): print(f"{n:7} CAGR {s['cagr']:5.2f} vol {s['std']:5.2f} MDD {s['mdd']:6.2f} Sh {s['sharpe']:.3f} So {s['sortino']:.2f} Cal {s['calmar']:.3f} Ulc {s['ulcer']:.3f} UPI {s['upi']:.2f} end {s['end']:.0f} | 94 {s['y1994']} 02 {s['y2002']} 08 {s['y2008']} 22 {s['y2022']} worst {s['worst']}")
for p,dd in out["decades"].items():
    print("\n",p); [print(f"  {n:7} CAGR {s['cagr']:5.2f} MDD {s['mdd']:6.2f} Sh {s['sharpe']:.2f} Cal {s['calmar']:.2f} Ulc {s['ulcer']:.2f}") for n,s in dd.items()]
