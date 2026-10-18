"""Tune the life-stage glide path on the GPU over every historical start (quarterly 1988-2016).
Accumulators: minimise 75th-percentile years-to-goal (retire on reaching the nest egg), subject to
  never running out after retiring, and real value never < LOWFLOOR x nest egg after retiring.
Retiree: choose the retiree budget maximising the worst-case lowest real value (4% inflation-indexed withdrawals)."""
import os, json, time, numpy as np, torch
import life_gpu as lg, policy as pl

LOWFLOOR = float(os.environ.get("LOWFLOOR", "0.6"))
starts = [i for i in range(len(pl.DATES)) if (i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])) and pl.DATES[i] < "2017"]
params, G = lg.grid(); keys = ("BASE", "SLOPE", "CAP", "RET", "F0"); CUR = (8, 1.0, 40, 8, 1.0)
res = {}; t0 = time.time()

def summarise(m, j):
    y = m["ytg"][:, j].cpu().numpy(); span = m["span"][:, j].cpu().numpy(); cens = np.where(np.isnan(y), span + 1, y)
    return dict(p75=float(np.percentile(cens, 75)), median=float(np.median(cens)), worst=float(cens.max()), reached=int((~np.isnan(y)).sum()),
                dead=int(m["dead"][:, j].sum()), low_after=float(m["low_after"][:, j].min()), mdd=float(m["mdd"][:, j].max()))

for name, prof in lg.PROFILES.items():
    m = lg.run(prof, params, starts)
    y = m["ytg"].cpu().numpy(); span = m["span"].cpu().numpy(); cens = np.where(np.isnan(y), span + 1, y)
    p75 = np.percentile(cens, 75, axis=0); dead = m["dead"].cpu().numpy().any(0); low = m["low_after"].cpu().numpy().min(0)
    ok = (~dead) & (low >= LOWFLOOR); score = np.where(ok, p75, 1e9); j = int(np.argmin(score)); jc = G.index(CUR)
    res[name] = dict(best=dict(zip(keys, G[j]), **summarise(m, j)), current=dict(zip(keys, CUR), **summarise(m, jc)), feasible=int(ok.sum()))
    b, c = res[name]["best"], res[name]["current"]
    print(f"\n{name}  ({ok.sum()} of {len(G)} settings feasible, {time.time()-t0:.0f}s)")
    for lab, r in (("current", c), ("optimised", b)):
        print(f"  {lab:9} BASE {r['BASE']:>4} SLOPE {r['SLOPE']:<4} CAP {r['CAP']:>2} RET {r['RET']:>2} F0 {r['F0']:<3} | years to goal: median {r['median']:4.1f} p75 {r['p75']:4.1f} worst {r['worst']:4.1f} "
              f"| reached {r['reached']}/{len(starts)} | ran out {r['dead']} | lowest real after retiring {r['low_after']*100:4.0f}% of egg | max DD {r['mdd']:4.1f}%")

# retiree: already retired, 4% withdrawals; only RET matters
print("\nRetiree: 60y, $300k, withdrawing 4% ($12k) inflation-indexed, 25 years max")
retp = dict(age=60, value=300000, contrib=0, retire_age=60, spending=12000, already_retired=True)
P = {k: torch.tensor([8.0] * 9, device=lg.DEV) for k in keys}; P["RET"] = torch.tensor([5, 6, 8, 10, 12, 15, 20, 25, 30], device=lg.DEV, dtype=torch.float32); P["F0"] = torch.ones(9, device=lg.DEV)
m = lg.run(retp, P, starts, years=25); out = []
for j in range(9):
    lo = m["low_after"][:, j].cpu().numpy(); dd = m["mdd"][:, j].cpu().numpy()
    out.append(dict(RET=float(P["RET"][j]), dead=int(m["dead"][:, j].sum()), worst_low=float(lo.min()), median_low=float(np.median(lo)), mdd=float(dd.max())))
    print(f"  retiree budget {float(P['RET'][j]):>4.0f}% -> ran out {out[-1]['dead']}/{len(starts)} | worst lowest real value {lo.min()*100:5.1f}% | median lowest {np.median(lo)*100:5.1f}% | max DD {dd.max():4.1f}%")
res["retiree"] = out
json.dump(res, open(os.path.join(pl.ROOT, "life_opt.json"), "w"), indent=1)
print(f"\ndone {time.time()-t0:.0f}s")
