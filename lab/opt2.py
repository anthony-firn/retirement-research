import numpy as np,json,sys
import opt
from opt import *
def objectives(m0):
    pen=lambda m:np.where(m['cagr']>=m0['cagr']-1e-9,0,-1e3)
    return {
     "Max Sharpe":lambda m:m['sharpe']+pen(m),
     "Max Calmar":lambda m:m['calmar']+pen(m),
     "Min Ulcer":lambda m:-m['ulcer']+pen(m),
     "Min MaxDD":lambda m:m['mdd']+pen(m),
     "Max UPI":lambda m:m['upi']+pen(m),
     "Balanced":lambda m:(m['sharpe']/m0['sharpe']+m['calmar']/m0['calmar']+m0['ulcer']/m['ulcer']+m0['mdd']/m['mdd'])/4+pen(m),
    }
opt.objectives=objectives
def table(title,W,idx=None):
    M=ev(W,idx); print(f"\n== {title}")
    print(f"{'':12}"+" ".join(f"{n[:6]:>6}" for n in NAMES)+" |  CAGR   Vol    MDD Sharpe Sortino Calmar Ulcer  UPI")
    for i,name in enumerate(LBL):
        print(f"{name:12}"+" ".join(f"{x:6.0f}" for x in W[:,i])+f" | {M['cagr'][i]:5.2f} {M['std'][i]:5.2f} {M['mdd'][i]:6.2f} {M['sharpe'][i]:5.2f} {M['sortino'][i]:6.2f} {M['calmar'][i]:6.2f} {M['ulcer'][i]:5.2f} {M['upi'][i]:5.2f}")
full=opt.optimize(); LBL=["CURRENT"]+list(full)
Wf=np.c_[cur,*full.values()]; table("FULL PERIOD 1988-2026 (in-sample)",Wf)
json.dump({k:v.tolist() for k,v in full.items()},open(f"full_cap{CAP}.json","w"))
IS=np.flatnonzero(years<=2006); OOS=np.flatnonzero(years>=2007)
wf=opt.optimize(IS); Ww=np.c_[cur,*wf.values()]
table("WALK-FORWARD: optimized on 1988-2006 only (in-sample)",Ww,IS)
table("WALK-FORWARD: same weights, tested 2007-2026 (out-of-sample)",Ww,OOS)
