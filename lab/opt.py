import numpy as np,sys,json
from sim import *
CAP=int(sys.argv[1]) if len(sys.argv)>1 else 40   # max % per asset
rng=np.random.default_rng(0)
CUR={'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':22,'TBF':10,'DBMFSIM':23}
cur=w_of(CUR)[:,0]*100
def ev(Wpct,idx=None):
    out={}
    for i in range(0,Wpct.shape[1],4000):
        m=metrics(values(Wpct[:,i:i+4000]/100,idx),idx)
        for k,v in m.items(): out.setdefault(k,[]).append(v)
    return {k:np.concatenate(v) for k,v in out.items()}
m0={k:float(v[0]) for k,v in ev(cur[:,None]).items()}
def objectives(m0):
    pen=lambda m:np.where(m['cagr']>=m0['cagr']-1e-9,0,-1e3)
    return {
     "Max Sharpe":lambda m:m['sharpe'],
     "Max Calmar":lambda m:m['calmar'],
     "Min Ulcer":lambda m:-m['ulcer'],
     "Min MaxDD":lambda m:m['mdd'],
     "Max UPI (Martin)":lambda m:m['upi'],
     "Balanced, CAGR>=current":lambda m:(m['sharpe']/m0['sharpe']+m['calmar']/m0['calmar']+m0['ulcer']/m['ulcer']+m0['mdd']/m['mdd'])/4+pen(m),
    }
def climb(w,f,idx=None,steps=(5,2,1)):
    best=f(ev(w[:,None],idx))[0]
    for s in steps:
        while True:
            nb=[]
            for i in range(len(NAMES)):
                for j in range(len(NAMES)):
                    if i!=j and w[i]-s>=0 and w[j]+s<=CAP:
                        x=w.copy();x[i]-=s;x[j]+=s;nb.append(x)
            N=np.array(nb).T; sc=f(ev(N,idx)); k=sc.argmax()
            if sc[k]>best+1e-9: best,w=sc[k],N[:,k]
            else: break
    return w,best
def sample(n):
    W=rng.dirichlet(np.full(len(NAMES),0.7),n).T*100
    W=W[:,(W<=CAP).all(0)]
    return np.round(W)
def optimize(idx=None,mref=None):
    mref=mref or {k:float(v[0]) for k,v in ev(cur[:,None],idx).items()}
    S=np.c_[cur[:,None],sample(30000)]; M=ev(S,idx); res={}
    for name,f in objectives(mref).items():
        sc=f(M); starts=[cur]+[S[:,k] for k in np.argsort(-sc)[:4]]
        best=max((climb(np.clip(np.round(s),0,CAP)+0,f,idx) for s in starts if abs(s.sum()-100)<0.5 or True),key=lambda r:r[1])
        w=best[0]
        res[name]=w
    return res
if __name__=="__main__":
    res=optimize()
    json.dump({k:v.tolist() for k,v in res.items()},open(f"opt_cap{CAP}.json","w"))
    allw=np.c_[cur,*res.values()]; M=ev(allw)
    print(f"cap {CAP}%  | "+" ".join(f"{n:>7}" for n in NAMES)+" |  CAGR   Vol   MDD  Sharpe Sortino Calmar Ulcer  UPI")
    for i,name in enumerate(["CURRENT"]+list(res)):
        w=allw[:,i]
        print(f"{name[:24]:24}"+" ".join(f"{x:7.0f}" for x in w)+f" | {M['cagr'][i]:5.2f} {M['std'][i]:5.2f} {M['mdd'][i]:6.2f} {M['sharpe'][i]:5.2f} {M['sortino'][i]:6.2f} {M['calmar'][i]:6.2f} {M['ulcer'][i]:5.2f} {M['upi'][i]:5.2f}")
