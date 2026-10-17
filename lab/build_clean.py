"""Drop testfol.io ticker-modifier series (anything containing '?') -> clean_etf.json / clean_A.json."""
import json
for src,dst in [("hist_native.json","clean_etf.json"),("hist_extA.json","clean_A.json"),("hist_extX.json","clean_X.json")]:
    H=json.load(open(src)); keep=[i for i,n in enumerate(H["names"]) if "?" not in n]
    H["names"]=[H["names"][i] for i in keep]; H["v"]=[H["v"][i] for i in keep]
    json.dump(H,open(dst,"w")); print(dst,len(H["names"]),"assets")
