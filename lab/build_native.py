import json,numpy as np,datetime as dt
H=json.load(open("hist_long.json"))
start=min(H["KMLMSIM"]["t"])
ETFS=["VTISIM", "VEASIM", "BNDSIM", "IEFSIM", "GLDSIM", "TLTSIM?L=-1&E=0.9", "TBILL?E=0.14", "KMLMSIM", "VTVSIM", "VBRSIM", "XLPSIM", "XLUSIM", "XLVSIM", "SPMOSIM", "QQQSIM", "IWMSIM", "REITSIM", "SHYSIM", "TLTSIM", "ZROZSIM", "SLVSIM", "GSGSIM", "UUPSIM", "NTSXSIM", "GDESIM", "RSSBSIM", "UGLSIM", "XLBSIM", "XLESIM", "XLFSIM", "XLISIM", "XLKSIM", "XLYSIM", "XLCSIM", "VUGSIM", "VVSIM", "VOSIM", "VOESIM", "VOTSIM", "VBSIM", "VBKSIM", "IWCSIM", "VXUSSIM", "EFASIM", "URTHSIM", "VTSIM", "NTSDSIM", "NTSISIM", "IEISIM", "UPROSIM", "SSOSIM", "TMFSIM", "UBTSIM", "TYDSIM", "TQQQSIM", "QLDSIM", "TECLSIM", "UWMSIM"]  # investable ETF sims covering 1987-12-31 (fixed list for reproducibility)
tick=[k for k in ETFS if min(H[k]["t"])<=start]
S={k:dict(zip(H[k]["t"],H[k]["v"])) for k in tick}; rf=dict(zip(H["TBILL"]["t"],H["TBILL"]["v"]))
dates=sorted(t for t in set.intersection(*[set(x) for x in S.values()],set(rf)) if t>=start)
tick=[k for k in tick if S[k][dates[0]]>1e-9]
v=[[S[k][t]/S[k][dates[0]] for t in dates] for k in tick]
json.dump({"names":tick,"t":dates,"v":v,"rf":[rf[t]/rf[dates[0]] for t in dates]},open("hist_native.json","w"))
print(len(tick),"assets",len(dates),"days",dt.datetime.fromtimestamp(dates[0],dt.UTC).date());print(tick)
