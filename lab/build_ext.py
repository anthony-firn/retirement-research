import json,sys,datetime as dt
H=json.load(open("hist_long.json")); base=json.load(open("hist_native.json"))
extra=sys.argv[1].split(","); out=sys.argv[2]
names=base["names"]+extra; dates=base["t"]
S={k:dict(zip(H[k]["t"],H[k]["v"])) for k in extra}
common=[t for t in dates if all(t in S[k] for k in extra)]
print("dates kept",len(common),"of",len(dates))
ix={t:i for i,t in enumerate(dates)}
v=[[base["v"][j][ix[t]]/base["v"][j][ix[common[0]]] for t in common] for j in range(len(base["names"]))]+[[S[k][t]/S[k][common[0]] for t in common] for k in extra]
rf=[base["rf"][ix[t]]/base["rf"][ix[common[0]]] for t in common]
json.dump({"names":names,"t":common,"v":v,"rf":rf},open(out,"w")); print(len(names),"assets from",dt.datetime.fromtimestamp(common[0],dt.UTC).date())
