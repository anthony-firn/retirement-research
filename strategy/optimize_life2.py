"""One glide-path rule for everyone: wider grid, joint objective across profiles, split-sample validation.
Score = sum over accumulator profiles of p75 years-to-goal; hard constraints in every profile: never run out,
lowest real value after retiring >= LOWFLOOR x nest egg; retiree (already retired, 4%) worst lowest real >= RETFLOOR.
Selection on starts 1988-2002, validated on starts 2003-2016 (and reported on all)."""
import os, json, itertools, time, numpy as np, torch
import life_gpu as lg, policy as pl

LOWFLOOR = float(os.environ.get("LOWFLOOR", "0.6")); RETFLOOR = float(os.environ.get("RETFLOOR", "0.7"))
allst = [i for i in range(len(pl.DATES)) if (i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])) and pl.DATES[i] < "2017"]
SPLIT_DATE = os.environ.get("SPLIT_DATE", "2003"); split = sum(1 for i in allst if pl.DATES[i] < SPLIT_DATE)
keys = ("BASE", "SLOPE", "CAP", "RET", "F0")
G = list(itertools.product([8, 10, 12, 14, 16, 20, 25], [1.0, 1.5, 2.0, 2.5, 3.0], [20, 25, 30, 35, 40, 50], [12, 15, 18, 20, 25], [0.6, 0.8, 1.0]))
G.append((20, 2.5, 50, 15, 1.0))                                                            # current rule for reference
params = {k: torch.tensor([g[i] for g in G], device=lg.DEV, dtype=torch.float32) for i, k in enumerate(keys)}
profiles = dict(lg.PROFILES); retp = dict(age=60, value=300000, contrib=0, retire_age=60, spending=12000, already_retired=True)
t0 = time.time(); M = {}
for name, prof in profiles.items(): M[name] = lg.run(prof, params, allst, years=40); print(f"  {name} simulated ({time.time()-t0:.0f}s)", flush=True)
M["retiree"] = lg.run(retp, params, allst, years=25); print(f"  retiree simulated ({time.time()-t0:.0f}s)", flush=True)

def stats(sel):
    tot = np.zeros(len(G)); ok = np.ones(len(G), bool); per = {}
    for name in profiles:
        m = M[name]; y = m["ytg"].cpu().numpy()[sel]; sp = m["span"].cpu().numpy()[sel]; c = np.where(np.isnan(y), sp + 1, y)
        p75 = np.percentile(c, 75, axis=0); tot += p75; per[name] = (p75, np.median(c, axis=0))
        ok &= ~m["dead"].cpu().numpy()[sel].any(0); ok &= m["low_after"].cpu().numpy()[sel].min(0) >= LOWFLOOR
    r = M["retiree"]; ok &= ~r["dead"].cpu().numpy()[sel].any(0); rlow = r["low_after"].cpu().numpy()[sel].min(0); ok &= rlow >= RETFLOOR
    return tot, ok, per, rlow

A, B, ALL = slice(0, split), slice(split, None), slice(None)
tA, okA, _, _ = stats(A); j = int(np.argmin(np.where(okA, tA, 1e9)))           # chosen on early starts only
tB, okB, perB, rB = stats(B); tF, okF, perF, rF = stats(ALL); jc = len(G) - 1
jf = int(np.argmin(np.where(okF, tF, 1e9)))                                     # best on all starts (for reference)
def show(lab, k):
    print(f"\n{lab}: BASE {G[k][0]} SLOPE {G[k][1]} CAP {G[k][2]} RET {G[k][3]} F0 {G[k][4]}  | feasible early/late/all: {okA[k]}/{okB[k]}/{okF[k]}")
    for name in profiles:
        print(f"   {name:30} p75 years: late-starts {perB[name][0][k]:5.1f}  all {perF[name][0][k]:5.1f} | median all {perF[name][1][k]:5.1f}")
    print(f"   retiree worst lowest real value: late {rB[k]*100:5.1f}%  all {rF[k]*100:5.1f}%")
show("CURRENT rule", jc); show(f"CHOSEN on starts before {SPLIT_DATE} (validated on later starts)", j); show("Best using all starts (in-sample)", jf)
json.dump(dict(chosen=dict(zip(keys, G[j])), best_all=dict(zip(keys, G[jf])), current=dict(zip(keys, G[jc])), lowfloor=LOWFLOOR, retfloor=RETFLOOR,
               port_file=os.environ.get("PORT_FILE", "data_portfolios.json"), split=SPLIT_DATE),
          open(os.path.join(pl.ROOT, os.environ.get("OUT", "life_rule.json")), "w"), indent=1)
print(f"\ndone {time.time()-t0:.0f}s")
