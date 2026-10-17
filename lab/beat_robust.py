import os; os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"
import numpy as np,json,sys,multiprocessing as mp
import beat
from beat import *
ALL=np.arange(len(years)); yr=years; c=np.quantile(yr,[.25,.5,.75])
Q=[ALL[yr<=c[0]],ALL[(yr>c[0])&(yr<=c[1])],ALL[(yr>c[1])&(yr<=c[2])],ALL[yr>c[2]]]
def evp(W,idx):
    out={}
    for i in range(0,W.shape[1],600):
        m=metrics(values(W[:,i:i+600]/100,idx),idx)
        for k,v in m.items(): out.setdefault(k,[]).append(v)
    return {k:np.concatenate(v) for k,v in out.items()}
BQ=[{k:float(v[0]) for k,v in evp(f1[:,None],q).items()} for q in Q]
def score(W):
    m=ev(W)
    full=np.min([m['sharpe']/B['sharpe'],m['calmar']/B['calmar'],B['ulcer']/m['ulcer'],B['mdd']/m['mdd']],0)
    qs=[]
    for q,b in zip(Q,BQ):
        mq=evp(W,q); qs.append(np.min([mq['sharpe']/b['sharpe'],mq['calmar']/b['calmar'],b['ulcer']/mq['ulcer']],0))
    s=np.minimum(full,np.min(qs,0))
    return s+np.where(m['cagr']>=B['cagr']+0.01,0,-10+(m['cagr']-B['cagr']))+np.where((W>0).sum(0)<=K,0,-100)
beat.score=score
if __name__=="__main__":
    with mp.Pool(16) as p: R=p.map(beat.ils,range(48))
    R.sort(key=lambda r:-r[1]); json.dump({"names":NAMES,"res":R},open("beat_robust_res.json","w"))
    W=np.c_[f1,np.array([r[0] for r in R[:8]]).T]; M=ev(W)
    print(f"Quarters: {[f'{yr[q][0]}-{yr[q][-1]}' for q in Q]}")
    for i in range(W.shape[1]):
        w=W[:,i]; a=" ".join(f"{NAMES[j].replace('SIM','')}{w[j]:.0f}" for j in np.argsort(-w) if w[j]>0)
        qsh=" ".join(f"{evp(w[:,None],q)['sharpe'][0]:.2f}" for q in Q)
        print(f"{'FULL#1' if i==0 else f'R{i}':6} {a:70} CAGR {M['cagr'][i]:5.2f} MDD {M['mdd'][i]:6.2f} Sh {M['sharpe'][i]:.3f} Cal {M['calmar'][i]:.3f} Ulc {M['ulcer'][i]:.3f} | qSharpe {qsh} | score {R[i-1][1] if i else 1:.3f}")
