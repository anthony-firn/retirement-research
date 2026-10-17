"""Drop testfol.io ticker-modifier series (anything containing '?') -> clean_etf.json / clean_A.json."""
import json
for src,dst in [("hist_native.json","clean_etf.json"),("hist_extA.json","clean_A.json"),("hist_extX.json","clean_X.json")]:
    H=json.load(open(src))
    # drop modifier tickers and any series that ever hits zero (e.g. SQQQ: -3x Nasdaq wiped out in 2000)
    keep=[i for i,n in enumerate(H["names"]) if "?" not in n and min(H["v"][i])>1e-9]
    gone=[n for i,n in enumerate(H["names"]) if i not in keep and "?" not in n]
    if gone: print("  dropped (hit zero):",gone)
    H["names"]=[H["names"][i] for i in keep]; H["v"]=[H["v"][i] for i in keep]
    json.dump(H,open(dst,"w")); print(dst,len(H["names"]),"assets")
