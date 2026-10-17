import numpy as np
from greedy import greedy,quarters,ratio_score,ev,cur,NAMES,years,show
ALL=np.arange(len(years)); Q=quarters(ALL)
lbl=[f"{years[q][0]}-{years[q][-1]}" for q in Q]
fmt=lambda w:" ".join(f"{NAMES[j]}{w[j]:.0f}" for j in np.argsort(-w) if w[j]>0)
print("\n#### Leave-one-decade-out")
for h in range(4):
    tr=[Q[i] for i in range(4) if i!=h]
    print(f"\nHold out {lbl[h]}  (fit on the other three)")
    w=greedy(tr)
    W=np.c_[cur,w]; M=ev(W,Q[h])
    print(f"  result: {fmt(w)}")
    for i,n in enumerate(["CURRENT","CV-pick"]):
        print(f"  held-out {n:8} CAGR {M['cagr'][i]:5.2f} MDD {M['mdd'][i]:6.2f} Sharpe {M['sharpe'][i]:.2f} Calmar {M['calmar'][i]:.2f} Ulcer {M['ulcer'][i]:.2f}")
