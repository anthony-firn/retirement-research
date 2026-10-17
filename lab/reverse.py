import sys; sys.argv=["x","0","1.0","5"]
import numpy as np
from search2 import *
IS=np.flatnonzero(years>=2007); OOS=np.flatnonzero(years<=2006)
r=search(IS)[:5]
W=np.c_[cur,*[x[0] for x in r]]; L=["CURRENT"]+[f"REV#{i+1}" for i in range(len(r))]
show("REVERSE: picked on 2007-2026 — IN-sample",W,L,IS)
show("REVERSE: same weights — OUT-of-sample 1988-2006",W,L,OOS)
import json; json.dump([x[0].tolist() for x in r],open("rev_res.json","w"))
