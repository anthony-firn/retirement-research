import os; os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"
import numpy as np,json,sys,multiprocessing as mp
from simn import *
N=len(NAMES); CAP=35; K=8
import os as _o,json as _j
F1=_j.loads(_o.environ.get('BASE','{"SHYSIM":25,"SPMOSIM":20,"GLDSIM":15,"KMLMSIM":20,"UUPSIM":10,"XLVSIM":5,"ZROZSIM":5}'))
f1=w_of(F1)[:,0]*100
def ev(W):
    out={}
    for i in range(0,W.shape[1],600):
        m=metrics(values(W[:,i:i+600]/100))
        for k,v in m.items(): out.setdefault(k,[]).append(v)
    return {k:np.concatenate(v) for k,v in out.items()}
B={k:float(v[0]) for k,v in ev(f1[:,None]).items()}
def score(W):
    m=ev(W)
    s=np.min([m['sharpe']/B['sharpe'],m['calmar']/B['calmar'],B['ulcer']/m['ulcer'],B['mdd']/m['mdd']],0)
    return s+np.where(m['cagr']>=B['cagr']+0.01,0,-10+ (m['cagr']-B['cagr']))+np.where((W>0).sum(0)<=K,0,-100)
def climb(w,steps=(5,2,1)):
    best=score(w[:,None])[0]
    for s in steps:
        while True:
            nb=[]
            for i in np.flatnonzero(w>=s):
                for j in range(N):
                    if i!=j and w[j]+s<=CAP:
                        x=w.copy();x[i]-=s;x[j]+=s
                        if (x>0).sum()<=K: nb.append(x)
            M=np.array(nb).T; sc=score(M); k=sc.argmax()
            if sc[k]>best+1e-7: best,w=sc[k],M[:,k]
            else: break
    return w,best
def ils(seed):
    rng=np.random.default_rng(seed)
    if seed==0: w=f1.copy()
    else:
        k=rng.integers(4,K+1); pick=rng.choice(N,k,replace=False)
        w=np.zeros(N); w[pick]=np.round(rng.dirichlet(np.ones(k))*100)
        w=np.minimum(w,CAP); w[pick[np.argmin(w[pick])]]+=100-w.sum()
        if w.min()<0 or w.max()>CAP: w=f1.copy()
    w,b=climb(w); best=(w,b)
    for _ in range(6):   # perturb & re-climb
        x=best[0].copy(); held=np.flatnonzero(x>0)
        i=rng.choice(held); j=rng.integers(N); amt=min(x[i],rng.integers(5,16))
        if x[j]+amt>CAP: continue
        x[i]-=amt; x[j]+=amt
        if (x>0).sum()>K: continue
        x,b=climb(x)
        if b>best[1]: best=(x,b)
    return best[0].tolist(),float(best[1])
if __name__=="__main__":
    n=int(sys.argv[1]) if len(sys.argv)>1 else 48
    with mp.Pool(min(os.cpu_count(),24)) as p: R=p.map(ils,range(n))
    R.sort(key=lambda r:-r[1])
    json.dump({"names":NAMES,"res":R},open("beat_res.json","w"))
    W=np.array([r[0] for r in R[:12]]).T; M=ev(np.c_[f1,W])
    print(f"cpus {os.cpu_count()}  FULL#1 baseline: CAGR {B['cagr']:.2f} MDD {B['mdd']:.2f} Sh {B['sharpe']:.3f} Cal {B['calmar']:.3f} Ulc {B['ulcer']:.3f}")
    for i in range(W.shape[1]+1):
        w=np.c_[f1,W][:,i]; a=" ".join(f"{NAMES[j].replace('SIM','')}{w[j]:.0f}" for j in np.argsort(-w) if w[j]>0)
        print(f"{'FULL#1' if i==0 else f'#{i}':6} {a:75} CAGR {M['cagr'][i]:5.2f} Vol {M['std'][i]:5.2f} MDD {M['mdd'][i]:6.2f} Sh {M['sharpe'][i]:.3f} Cal {M['calmar'][i]:.3f} Ulc {M['ulcer'][i]:.3f}  score {R[i-1][1] if i else 1:.3f}")
