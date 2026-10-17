import numpy as np,json,sys
from sim import *
from opt import ev,cur
BAND=float(sys.argv[1]) if len(sys.argv)>1 else 10
LO=np.clip(cur-BAND,0,100); HI=np.minimum(cur+BAND,100)
rng=np.random.default_rng(1)
def periods(idx):
    yr=years[idx]; cuts=np.quantile(yr,[1/3,2/3])
    return [idx[yr<=cuts[0]],idx[(yr>cuts[0])&(yr<=cuts[1])],idx[yr>cuts[1]]]
def score_fn(idx):
    ps=periods(idx); b=[{k:v[0] for k,v in ev(cur[:,None],p).items()} for p in ps]
    full0=ev(cur[:,None],idx)['cagr'][0]
    def f(W):
        tot=ev(W,idx); s=[]
        for p,m0 in zip(ps,b):
            m=ev(W,p)
            s.append((m['sharpe']/m0['sharpe']+m['calmar']/m0['calmar']+m0['ulcer']/m['ulcer']+m0['mdd']/m['mdd'])/4)
        worst=np.min(s,0)
        return worst+np.where(tot['cagr']>=full0-0.25,0,-1e3)   # allow CAGR within 0.25pt of current
    return f
def climb(w,f,steps=(5,2,1)):
    best=f(w[:,None])[0]
    for s in steps:
        while True:
            nb=[]
            for i in range(len(NAMES)):
                for j in range(len(NAMES)):
                    if i!=j and w[i]-s>=LO[i] and w[j]+s<=HI[j]:
                        x=w.copy();x[i]-=s;x[j]+=s;nb.append(x)
            if not nb: break
            N=np.array(nb).T; sc=f(N); k=sc.argmax()
            if sc[k]>best+1e-9: best,w=sc[k],N[:,k]
            else: break
    return w,best
def optimize(idx):
    f=score_fn(idx)
    # random starts inside the band
    S=[cur]
    while len(S)<400:
        x=LO+rng.random(len(NAMES))*(HI-LO); x=np.round(x/x.sum()*100)
        x[np.argmax(x)]+=100-x.sum()
        if (x>=LO).all() and (x<=HI).all(): S.append(x)
    S=np.array(S).T; sc=f(S)
    starts=[S[:,k] for k in np.argsort(-sc)[:6]]
    return max((climb(s.copy(),f) for s in starts),key=lambda r:r[1])[0]
def show(title,W,lbl,idx):
    M=ev(W,idx); print(f"\n== {title}")
    print(f"{'':10}"+" ".join(f"{n[:6]:>6}" for n in NAMES)+" |  CAGR   Vol    MDD Sharpe Sortino Calmar Ulcer  UPI")
    for i,name in enumerate(lbl):
        print(f"{name:10}"+" ".join(f"{x:6.0f}" for x in W[:,i])+f" | {M['cagr'][i]:5.2f} {M['std'][i]:5.2f} {M['mdd'][i]:6.2f} {M['sharpe'][i]:5.2f} {M['sortino'][i]:6.2f} {M['calmar'][i]:6.2f} {M['ulcer'][i]:5.2f} {M['upi'][i]:5.2f}")
ALL=np.arange(len(years))
IS=np.flatnonzero(years<=2006); OOS=np.flatnonzero(years>=2007)
w_wf=optimize(IS)
W=np.c_[cur,w_wf]
show(f"band ±{BAND:.0f}: picked on 1988-2006, IN-sample",W,["CURRENT","Tuned"],IS)
show(f"band ±{BAND:.0f}: same weights, OUT-of-sample 2007-2026",W,["CURRENT","Tuned"],OOS)
w_full=optimize(ALL)
W=np.c_[cur,w_full]
show(f"band ±{BAND:.0f}: picked on full 1988-2026",W,["CURRENT","Tuned"],ALL)
for p in periods(ALL): show(f"   sub-period {years[p][0]}-{years[p][-1]}",W,["CURRENT","Tuned"],p)
json.dump({"wf":w_wf.tolist(),"full":w_full.tolist()},open(f"robust_band{BAND:.0f}.json","w"))
