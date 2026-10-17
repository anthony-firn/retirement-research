import json,numpy as np
H=json.load(open("hist_long.json"))
s=lambda k:dict(zip(H[k]["t"],H[k]["v"]))
dbmf,kmlm,tb=s("DBMFSIM"),s("KMLMSIM"),s("TBILL")
# vol-match KMLM to DBMF over overlap (daily)
ov=sorted(set(dbmf)&set(kmlm)&set(tb))
rd=np.diff(np.log([dbmf[t] for t in ov])); rk=np.diff(np.log([kmlm[t] for t in ov]))
a=rd.std()/rk.std(); print("scale a =",round(a,3))
src={"VTISIM":"VTISIM","VEASIM":"VEASIM","BNDSIM":"BNDSIM","BIL":"TBILL?E=0.14","GLDSIM":"GLDSIM","TBF":"TLTSIM?L=-1&E=0.9","RF":"TBILL"}
S={k:s(v) for k,v in src.items()}
dates=sorted(set.intersection(*[set(x) for x in S.values()],set(kmlm)))
dates=[t for t in dates if t>=min(kmlm)]
cols={k:np.array([S[k][t] for t in dates]) for k in S}
# managed futures splice
mf=[1.0]; d0=min(dbmf)
for i in range(1,len(dates)):
    t,p=dates[i],dates[i-1]
    if p>=d0 and t in dbmf and p in dbmf: r=dbmf[t]/dbmf[p]-1
    else: r=a*(kmlm[t]/kmlm[p]-1)+(1-a)*(tb[t]/tb[p]-1)
    mf.append(mf[-1]*(1+r))
cols["DBMFSIM"]=np.array(mf)
names=["VTISIM","VEASIM","BNDSIM","BIL","GLDSIM","TBF","DBMFSIM"]
json.dump({"names":names,"t":dates,"v":[(cols[n]/cols[n][0]).tolist() for n in names],"rf":(cols["RF"]/cols["RF"][0]).tolist()},open("hist_spliced.json","w"))
import datetime as dt; print(len(dates),dt.datetime.fromtimestamp(dates[0],dt.UTC).date(),dt.datetime.fromtimestamp(dates[-1],dt.UTC).date())
