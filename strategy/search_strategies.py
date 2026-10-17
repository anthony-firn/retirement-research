"""GPU random search over tier-switching strategies, per drawdown budget, with walk-forward validation.
Env: N (total strategies, default 300000), CHUNK (50000), SEED, OUT."""
import os, json, time, numpy as np, torch
import gpu_strategy as gs

N = int(os.environ.get("N", "300000")); CH = int(os.environ.get("CHUNK", "50000")); SEED = int(os.environ.get("SEED", "1"))
OUT = os.environ.get("OUT", os.path.join(gs.ROOT, "search_results.json"))
BUDGETS = [5, 8, 10, 12, 15, 20, 25, 30, 40]
split = int(np.searchsorted(gs.YEARS, 2007))          # first trading day of 2007
PERIODS = {"full": (0, gs.T), "is": (0, split), "oos": (split, gs.T)}

g = np.random.default_rng(SEED); t0 = time.time(); rows = []
for c in range(0, N, CH):
    P = gs.sample(min(CH, N - c), g)
    M = {p: gs.run(P, a, b) for p, (a, b) in PERIODS.items()}
    keep = {k: v.cpu().numpy() for k, v in P.items()}
    for i in range(len(P["B"])):
        pass
    arr = {f"{p}_{m}": M[p][m].cpu().numpy() for p in M for m in ("cagr", "mdd", "ulcer", "sharpe", "switches")}
    rows.append((keep, arr))
    print(f"  {c + len(P['B'])}/{N} strategies  ({time.time() - t0:.0f}s)", flush=True)

params = {k: np.concatenate([r[0][k] for r in rows]) for k in gs.KEYS}
met = {k: np.concatenate([r[1][k] for r in rows]) for k in rows[0][1]}
dec = lambda i: {k: gs.SPACE[k][int(params[k][i])] for k in gs.KEYS}
def mets(i): return {k: float(v[i]) for k, v in met.items()}

# static benchmarks (buy-and-hold one lineup tier)
stat = {n: {p: gs.static(n, a, b) for p, (a, b) in PERIODS.items()} for n in gs.LADDER}
res = {"budgets": {}, "n": N, "split": gs.DATES[split]}
print(f"\n{'budget':>6} | {'best static (MDD<=b all periods)':38} | {'robust strategy: min(IS,OOS) CAGR':44} | walk-forward (pick on IS -> OOS)")
for bgt in BUDGETS:
    feas = (met["full_mdd"] <= bgt) & (met["is_mdd"] <= bgt) & (met["oos_mdd"] <= bgt)
    robust = np.where(feas, np.minimum(met["is_cagr"], met["oos_cagr"]), -1e9)
    i = int(np.argmax(robust))
    st = [(n, s) for n, s in stat.items() if all(s[p]["mdd"] <= bgt for p in s)]
    bs = max(st, key=lambda x: min(x[1]["is"]["cagr"], x[1]["oos"]["cagr"])) if st else None
    feas_is = met["is_mdd"] <= bgt; j = int(np.argmax(np.where(feas_is, met["is_cagr"], -1e9)))
    res["budgets"][bgt] = dict(robust=dict(params=dec(i), **mets(i)), walkforward=dict(params=dec(j), **mets(j)),
                               static=(dict(name=bs[0], **{f"{p}_{k}": v for p, s in bs[1].items() for k, v in s.items()}) if bs else None))
    s_txt = f"{bs[0]:8} full {bs[1]['full']['cagr']:5.2f}/{bs[1]['full']['mdd']:5.1f} IS {bs[1]['is']['cagr']:5.2f} OOS {bs[1]['oos']['cagr']:5.2f}" if bs else "none"
    print(f"{bgt:>5}% | {s_txt:38} | full {met['full_cagr'][i]:5.2f}/{met['full_mdd'][i]:5.1f} IS {met['is_cagr'][i]:5.2f} OOS {met['oos_cagr'][i]:5.2f} sw/yr {met['full_switches'][i]:4.1f} | "
          f"IS {met['is_cagr'][j]:5.2f}/{met['is_mdd'][j]:5.1f} -> OOS {met['oos_cagr'][j]:5.2f}/{met['oos_mdd'][j]:5.1f}")
json.dump(res, open(OUT, "w"), indent=1)
print(f"\ndone {time.time() - t0:.0f}s -> {OUT}")
