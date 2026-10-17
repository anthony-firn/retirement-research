import numpy as np
from sim import *
from opt import ev
V={
"CURRENT":{'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':22,'TBF':10,'DBMFSIM':23},
"Robust tune":{'VTISIM':20,'BNDSIM':16,'BIL':14,'GLDSIM':15,'TBF':3,'DBMFSIM':32},
"Cur 75%+BIL":{'VTISIM':22.5,'BNDSIM':7.5,'BIL':28.75,'GLDSIM':16.5,'TBF':7.5,'DBMFSIM':17.25},
"TBF5->BND":{'VTISIM':30,'BNDSIM':15,'BIL':5,'GLDSIM':22,'TBF':5,'DBMFSIM':23},
"TBF0->BND":{'VTISIM':30,'BNDSIM':20,'BIL':5,'GLDSIM':22,'DBMFSIM':23},
"MF up,GLD dn":{'VTISIM':30,'BNDSIM':10,'BIL':5,'GLDSIM':17,'TBF':10,'DBMFSIM':28},
"Mid tune":{'VTISIM':25,'BNDSIM':13,'BIL':10,'GLDSIM':18,'TBF':6,'DBMFSIM':28},
}
W=np.c_[*[w_of(v)[:,0]*100 for v in V.values()]]
P_={"1988-2026":years>=0,"1988-2006":years<=2006,"2007-2026":years>=2007,"1994":years==1994,"2000-02":(years>=2000)&(years<=2002),"2008":years==2008,"2022":years==2022}
for pn,mask in P_.items():
    idx=np.flatnonzero(mask); M=ev(W,idx)
    print(f"\n{pn:13}  CAGR   Vol    MDD Sharpe Calmar Ulcer")
    for i,n in enumerate(V): print(f"{n:13} {M['cagr'][i]:5.2f} {M['std'][i]:5.2f} {M['mdd'][i]:6.2f} {M['sharpe'][i]:5.2f} {M['calmar'][i]:6.2f} {M['ulcer'][i]:5.2f}")
