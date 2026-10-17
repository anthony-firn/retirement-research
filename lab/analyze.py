import numpy as np,datetime as dt
from simn import *
R1={"IEFSIM":33,"KMLMSIM":20,"GLDSIM":12,"SPMOSIM":10,"UUPSIM":8,"TLTSIM?L=-1&E=0.9":7,"VOESIM":6,"QLDSIM":4}
F1={"SHYSIM":25,"KMLMSIM":20,"SPMOSIM":20,"GLDSIM":15,"UUPSIM":10,"XLVSIM":5,"ZROZSIM":5}
lbl=lambda n:{"TLTSIM?L=-1&E=0.9":"TBF","TBILL?E=0.14":"BIL"}.get(n,n.replace("SIM",""))
idx={n:NAMES.index(n) for n in R1}
w=w_of(R1); f=lambda W:{k:float(v[0]) for k,v in metrics(values(W)).items()}
base=f(w)
print("R1:",{k:round(v,3) for k,v in base.items()})
# 1) asset stats
print("\n1) ASSETS ALONE (1988-2026)")
for n in R1:
    m=f(w_of({n:100})); print(f"  {lbl(n):5} w={R1[n]:2}%  CAGR {m['cagr']:6.2f} vol {m['std']:5.1f} MDD {m['mdd']:6.1f} Sharpe {m['sharpe']:.2f}")
# daily returns
D=P[1:]/P[:-1]-1; cols=[idx[n] for n in R1]
# monthly
ym=np.array([dt.datetime.fromtimestamp(x,dt.UTC).strftime("%Y%m") for x in t])
ends=np.r_[np.flatnonzero(ym[1:]!=ym[:-1]),len(t)-1]
Mr=P[ends][1:]/P[ends][:-1]-1
C=np.corrcoef(Mr[:,cols].T)
print("\n2) MONTHLY CORRELATIONS")
print("       "+" ".join(f"{lbl(n):>5}" for n in R1))
for i,n in enumerate(R1): print(f"  {lbl(n):5}"+" ".join(f"{C[i,j]:5.2f}" for j in range(len(R1))))
# risk contribution (daily cov)
S=np.cov(D[:,cols].T)*252; wv=np.array(list(R1.values()))/100
rc=wv*(S@wv); rc/=rc.sum()
mu=(np.log(P[-1,cols]/P[0,cols]))/ (len(t)/252)
print("\n3) RISK vs RETURN CONTRIBUTION")
for i,n in enumerate(R1): print(f"  {lbl(n):5} weight {wv[i]*100:4.0f}%  risk share {rc[i]*100:6.1f}%  return share {wv[i]*mu[i]/np.dot(wv,mu)*100:6.1f}%")
# 4) ablation
print("\n4) REMOVE ONE (others scaled up)   ΔCAGR  ΔMDD  ΔSharpe ΔCalmar ΔUlcer")
for n in R1:
    a={k:v for k,v in R1.items() if k!=n}; s=sum(a.values()); a={k:v*100/s for k,v in a.items()}
    m=f(w_of(a)); print(f"  -{lbl(n):5}  {m['cagr']-base['cagr']:+6.2f} {m['mdd']-base['mdd']:+6.2f} {m['sharpe']-base['sharpe']:+7.3f} {m['calmar']-base['calmar']:+7.3f} {m['ulcer']-base['ulcer']:+6.3f}")
# 5) crisis episodes
E=[("1990 Gulf War","1990-07-16","1990-10-11"),("1994 bond crash","1994-01-31","1994-11-22"),("1998 LTCM","1998-07-17","1998-10-08"),
   ("2000-02 dotcom","2000-03-24","2002-10-09"),("2008 GFC","2007-10-09","2009-03-09"),("2011 Euro","2011-04-29","2011-10-03"),
   ("2015-16","2015-05-21","2016-02-11"),("2018 Q4","2018-09-20","2018-12-24"),("2020 Covid","2020-02-19","2020-03-23"),("2022 rates","2022-01-03","2022-10-14")]
td=np.array([dt.datetime.fromtimestamp(x,dt.UTC).date().isoformat() for x in t])
VR=values(w)[:,0]; VF=values(w_of(F1))[:,0]; VT=P[:,NAMES.index("VTISIM")]
print("\n5) CRISES (% return over episode)")
print(f"  {'episode':16} {'VTI':>6} {'R1':>6} {'FULL1':>6} | "+" ".join(f"{lbl(n):>5}" for n in R1))
for name,a,b in E:
    i=np.searchsorted(td,a); j=np.searchsorted(td,b)
    r=lambda x:(x[j]/x[i]-1)*100
    print(f"  {name:16} {r(VT):6.1f} {r(VR):6.1f} {r(VF):6.1f} | "+" ".join(f"{r(P[:,idx[n]]):5.1f}" for n in R1))
