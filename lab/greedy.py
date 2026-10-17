import sys; sys.argv=["x"]
import numpy as np
from search2 import ev,cur,NAMES,years,show,CAP,K
N=len(NAMES)
def quarters(idx):
    yr=years[idx]; c=np.quantile(yr,[.25,.5,.75])
    return [idx[yr<=c[0]],idx[(yr>c[0])&(yr<=c[1])],idx[(yr>c[1])&(yr<=c[2])],idx[yr>c[2]]]
def ratio_score(m,b): return (m['sharpe']/b['sharpe']+m['calmar']/b['calmar']+b['ulcer']/m['ulcer'])/3
def greedy(periods,step=5,maxit=12,log=True):
    base=[{k:v[0] for k,v in ev(cur[:,None],p).items()} for p in periods]   # fixed reference = current
    w=cur.copy(); hist=[]
    def scores(W): 
        out=[]
        for p,b in zip(periods,base):
            m=ev(W,p); out.append((ratio_score(m,b),m['cagr']-b['cagr']))
        return out
    cs=[s[0][0] for s in scores(w[:,None])]
    for it in range(maxit):
        nb=[];mv=[]
        for i in np.flatnonzero(w>=step):
            for j in range(N):
                if i!=j and w[j]+step<=CAP:
                    x=w.copy();x[i]-=step;x[j]+=step
                    if (x>0).sum()<=K: nb.append(x);mv.append((NAMES[i],NAMES[j]))
        Wn=np.array(nb).T; S=scores(Wn)
        sc=np.array([s[0] for s in S]); dc=np.array([s[1] for s in S])
        ok=(sc>=np.array(cs)[:,None]+1e-4).all(0)&(dc>=-1.0).all(0)   # better in EVERY period, CAGR within 1pt everywhere
        if not ok.any(): break
        gain=(sc-np.array(cs)[:,None]).min(0); gain[~ok]=-np.inf; k=gain.argmax()
        w=Wn[:,k]; cs=list(sc[:,k])
        if log: print(f"  step {it+1}: {mv[k][0]} -> {mv[k][1]} ({step}%)   per-period score vs current: "+" ".join(f"{x:.3f}" for x in cs))
    return w
ALL=np.arange(len(years)); Q=quarters(ALL)
print("Quarters:",[f"{years[q][0]}-{years[q][-1]}" for q in Q])
print("\n### Honest test: greedy uses ONLY first two quarters (1988-2006)")
w_h=greedy(Q[:2])
W=np.c_[cur,w_h]; L=["CURRENT","Greedy-H"]
for q in Q: show(f"{years[q][0]}-{years[q][-1]}{'  (OUT-OF-SAMPLE)' if q is Q[2] or q is Q[3] else ''}",W,L,q)
show("2007-2026 combined OUT-OF-SAMPLE",W,L,np.r_[Q[2],Q[3]])
print("\n### Greedy using all four quarters")
w_a=greedy(Q)
W=np.c_[cur,w_a]; L=["CURRENT","Greedy-All"]
show("FULL 1988-2026",W,L)
for q in Q: show(f"{years[q][0]}-{years[q][-1]}",W,L,q)
import json; json.dump({"honest":w_h.tolist(),"all":w_a.tolist()},open("greedy_res.json","w"))
