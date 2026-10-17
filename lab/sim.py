import json,numpy as np,datetime as dt
H=json.load(open("hist_spliced.json"))
NAMES=H["names"]
t=np.array(H["t"]); P=np.array(H["v"]).T; RF=np.array(H["rf"])
years=np.array([dt.datetime.fromtimestamp(x,dt.UTC).year for x in t])
rf_d=RF[1:]/RF[:-1]-1

def values(W,idx=None):
    """W: (8,N) weights summing to 1. Yearly rebalance at first trading day of each year. Returns (days,N) portfolio values."""
    sl=slice(None) if idx is None else idx
    p=P[sl]; y=years[sl]
    out=np.empty((len(p),W.shape[1])); level=np.ones(W.shape[1]); start=0
    bounds=np.flatnonzero(np.diff(y))+1
    segs=list(zip(np.r_[0,bounds],np.r_[bounds,len(p)]))
    for a,b in segs:
        a0=a-1 if a>0 else 0           # rebalance at prior close
        g=p[a0:b]/p[a0]                # growth since rebalance
        seg=g@W*level
        if a>0: out[a:b]=seg[1:]
        else: out[a:b]=seg
        level=seg[-1]
    return out

def metrics(V,idx=None):
    rfd=rf_d if idx is None else rf_d[idx][1:] if False else None
    r=V[1:]/V[:-1]-1
    n=len(V); yrs=n/252.0
    sl=slice(None) if idx is None else idx
    rfx=(RF[sl][1:]/RF[sl][:-1]-1)[:,None]
    cagr=(V[-1]/V[0])**(1/yrs)-1
    std=r.std(0)*np.sqrt(252)
    ex=r-rfx
    sharpe=ex.mean(0)*252/(ex.std(0)*np.sqrt(252))
    peak=np.maximum.accumulate(V,0); dd=V/peak-1
    mdd=dd.min(0); ulcer=np.sqrt((dd*100)**2).mean(0) if False else np.sqrt(((dd*100)**2).mean(0))
    rf_c=(RF[sl][-1]/RF[sl][0])**(1/yrs)-1
    down=np.minimum(ex,0); sortino=ex.mean(0)*252/(np.sqrt((down**2).mean(0))*np.sqrt(252))
    return dict(cagr=cagr*100,std=std*100,sharpe=sharpe,sortino=sortino,mdd=mdd*100,calmar=cagr/-mdd,ulcer=ulcer,upi=(cagr-rf_c)*100/ulcer)

def w_of(d): return np.array([d.get(n,0) for n in NAMES],float)[:,None]/100
