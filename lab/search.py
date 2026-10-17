import numpy as np,json,sys
from simu import *
CAP=35; K=8; N=len(NAMES)
rng=np.random.default_rng(int(sys.argv[1]) if len(sys.argv)>1 else 0)
CUR={'VTI':30,'BND':10,'BIL':5,'GLD':22,'TBF':10,'DBMF':23}
cur=w_of(CUR)[:,0]*100
def ev(W,idx=None):
    out={}
    for i in range(0,W.shape[1],1500):
        m=metrics(values(W[:,i:i+1500]/100,idx),idx)
        for k,v in m.items(): out.setdefault(k,[]).append(v)
    return {k:np.concatenate(v) for k,v in out.items()}
def thirds(idx):
    yr=years[idx]; c=np.quantile(yr,[1/3,2/3])
    return [idx[yr<=c[0]],idx[(yr>c[0])&(yr<=c[1])],idx[yr>c[1]]]
def make_score(idx):
    ps=thirds(idx); base=[{k:v[0] for k,v in ev(cur[:,None],p).items()} for p in ps]
    floor=ev(cur[:,None],idx)['cagr'][0]
    def f(W):
        tot=ev(W,idx); s=[]
        for p,b in zip(ps,base):
            m=ev(W,p)
            s.append((m['sharpe']/b['sharpe']+m['calmar']/b['calmar']+b['ulcer']/m['ulcer'])/3)
        pen=np.where(tot['cagr']>=floor,0,-1e3)+np.where((W>0).sum(0)<=K,0,-1e3)
        return np.min(s,0)+pen
    return f
def climb(w,f,steps=(5,2,1)):
    best=f(w[:,None])[0]
    for s in steps:
        while True:
            nb=[]
            for i in np.flatnonzero(w>=s):
                for j in range(N):
                    if i!=j and w[j]+s<=CAP:
                        x=w.copy();x[i]-=s;x[j]+=s;nb.append(x)
            M=np.array(nb).T; sc=f(M); k=sc.argmax()
            if sc[k]>best+1e-9: best,w=sc[k],M[:,k]
            else: break
    return w,best
def search(idx,nstart=8):
    f=make_score(idx)
    S=[]
    for _ in range(3000):
        k=rng.integers(3,K+1); pick=rng.choice(N,k,replace=False)
        x=np.zeros(N); x[pick]=rng.dirichlet(np.ones(k))*100; x=np.minimum(np.round(x/5)*5,CAP)
        x[pick[0]]+=100-x.sum()
        if 0<=x.min() and x.max()<=CAP: S.append(x)
    S=np.array(S).T; sc=f(S); starts=[cur]+[S[:,i] for i in np.argsort(-sc)[:nstart]]
    res=sorted((climb(s.copy(),f) for s in starts),key=lambda r:-r[1])
    return res
def show(title,W,lbl,idx=None):
    M=ev(W,idx); print(f"\n== {title}")
    print(f"{'':10}{'allocation':58}  CAGR   Vol    MDD Sharpe Calmar Ulcer")
    for i,n in enumerate(lbl):
        a=" ".join(f"{NAMES[j]}{W[j,i]:.0f}" for j in np.argsort(-W[:,i]) if W[j,i]>0)
        print(f"{n:10}{a:58} {M['cagr'][i]:5.2f} {M['std'][i]:5.2f} {M['mdd'][i]:6.2f} {M['sharpe'][i]:5.2f} {M['calmar'][i]:6.2f} {M['ulcer'][i]:5.2f}")
if __name__=="__main__":
    ALL=np.arange(len(years)); IS=np.flatnonzero(years<=2006); OOS=np.flatnonzero(years>=2007)
    wf=search(IS)[:3]
    W=np.c_[cur,*[r[0] for r in wf]]; L=["CURRENT","WF#1","WF#2","WF#3"]
    show("WALK-FORWARD picked on 1988-2006 — IN-sample",W,L,IS)
    show("WALK-FORWARD same weights — OUT-of-sample 2007-2026",W,L,OOS)
    full=search(ALL)[:5]
    W=np.c_[cur,*[r[0] for r in full]]; L=["CURRENT"]+[f"FULL#{i+1}" for i in range(len(full))]
    show("FULL 1988-2026 search",W,L)
    for p in thirds(ALL): show(f"  sub-period {years[p][0]}-{years[p][-1]}",W,L,p)
    json.dump({"names":NAMES,"wf":[r[0].tolist() for r in wf],"full":[r[0].tolist() for r in full]},open("search_res.json","w"))
