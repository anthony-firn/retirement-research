import json,numpy as np
H=json.load(open("hist_long.json")); SP=json.load(open("hist_spliced.json"))
src={"VTI":"VTISIM","VEA":"VEASIM","VTV":"VTVSIM","VBR":"VBRSIM","XLP":"XLPSIM","XLU":"XLUSIM","XLV":"XLVSIM","SPMO":"SPMOSIM","QQQ":"QQQSIM","IWM":"IWMSIM","VNQ":"REITSIM",
     "BND":"BNDSIM","SHY":"SHYSIM","IEF":"IEFSIM","TLT":"TLTSIM","ZROZ":"ZROZSIM","BIL":"TBILL?E=0.14","TBF":"TLTSIM?L=-1&E=0.9",
     "GLD":"GLDSIM","SLV":"SLVSIM","GSG":"GSGSIM","UUP":"UUPSIM","KMLM":"KMLMSIM","NTSX":"NTSXSIM","GDE":"GDESIM","RSSB":"RSSBSIM","UGL":"UGLSIM"}
S={k:dict(zip(H[v]["t"],H[v]["v"])) for k,v in src.items()}
rf=dict(zip(H["TBILL"]["t"],H["TBILL"]["v"]))
dbmf=dict(zip(SP["t"],SP["v"][SP["names"].index("DBMFSIM")]))
dates=sorted(set.intersection(*[set(x) for x in S.values()],set(rf),set(dbmf)))
names=list(src)+["DBMF"]; S["DBMF"]=dbmf
v=[[S[n][t] for t in dates] for n in names]; v=[[x/a[0] for x in a] for a in v]
r=[rf[t] for t in dates]; r=[x/r[0] for x in r]
json.dump({"names":names,"t":dates,"v":v,"rf":r},open("hist_univ.json","w"))
import datetime as dt; print(len(names),"assets",len(dates),"days from",dt.datetime.fromtimestamp(dates[0],dt.UTC).date())
