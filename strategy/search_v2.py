"""Robust GPU strategy search (v2), continuous tier blends.
- Folds: 4 calendar decades + full period. Hard constraint: MDD <= budget in EVERY selection fold.
- Score: worst-decade CAGR. Stage 2: every parameter +/-1 notch (one GPU batch); pick best neighbourhood median.
- GUARANTEE=1: governor on all-time high (DECAY=0), M >= 1, and for budget b only strategies with L <= b-2
  -> total loss bounded by construction (~ L + worst day of the safest tier).
- WALKFWD=1: select on 1988-2006 only; report 2007-2026 out-of-sample.
Each sampled strategy is evaluated once and scored against every budget.
Env: N, CHUNK, SEED, GUARANTEE, WALKFWD, BUDGETS, OUT."""
import os, json, time, numpy as np, torch
import gpu_strategy as gs

N = int(os.environ.get("N", "300000")); CH = int(os.environ.get("CHUNK", "40000")); SEED = int(os.environ.get("SEED", "2"))
GUAR = os.environ.get("GUARANTEE", "1") == "1"; WF = os.environ.get("WALKFWD", "0") == "1"
OUT = os.environ.get("OUT", os.path.join(gs.ROOT, f"v2_{'guar' if GUAR else 'free'}{'_wf' if WF else ''}.json"))
BUDGETS = [int(x) for x in os.environ.get("BUDGETS", "6,8,10,12,15,20,25,30,40").split(",")]
yr = gs.YEARS
def rng(a, b): return int(np.searchsorted(yr, a)), int(np.searchsorted(yr, b + 1))
FOLDS = {"1988-1997": rng(1987, 1997), "1998-2007": rng(1998, 2007), "2008-2017": rng(2008, 2017), "2018-2026": rng(2018, 2026), "full": (0, gs.T)}
SEL = ["1988-1997", "1998-2007"] if WF else ["1988-1997", "1998-2007", "2008-2017", "2018-2026"]
EXTRA = {"selfull": rng(1987, 2006) if WF else (0, gs.T), "oos": rng(2007, 2026)}
MET = ("cagr", "mdd", "ulcer", "sharpe", "switches", "worst_day")

def evaluate(P):
    out = {}
    for f, (a, b) in list(FOLDS.items()) + list(EXTRA.items()):
        m = gs.run(P, a, b); out[f] = {k: m[k].cpu().numpy() for k in MET}
    return out

def score(M, bgt, Lv=None):
    feas = M["selfull"]["mdd"] <= bgt
    for f in SEL: feas &= M[f]["mdd"] <= bgt
    if GUAR and Lv is not None: feas &= Lv <= bgt - 2
    s = np.min([M[f]["cagr"] for f in SEL], 0)
    return np.where(feas, s, -1e9)

def guarantee_restrict(P):
    if GUAR:
        P["DECAY"] = torch.zeros_like(P["DECAY"])
        Ms = torch.tensor(gs.SPACE["M"], device=gs.DEV)
        P["M"] = torch.where(Ms[P["M"]] >= 1.0, P["M"], torch.full_like(P["M"], gs.SPACE["M"].index(1.0)))
    return P

def neighbours(p):
    nb = [dict(p)]
    for k in gs.KEYS:
        for d in (-1, 1):
            j = p[k] + d
            if 0 <= j < len(gs.SPACE[k]): x = dict(p); x[k] = j; nb.append(x)
    return nb

def stack(rows): return {k: torch.tensor([r[k] for r in rows], device=gs.DEV) for k in gs.KEYS}
def params_of(p): return {k: gs.SPACE[k][p[k]] for k in gs.KEYS}
Lvals = lambda P: np.array(gs.SPACE["L"])[P["L"]]

if __name__ == "__main__":
    t0 = time.time(); g = np.random.default_rng(SEED)
    print(f"v2 search  N={N}  guarantee={GUAR}  walk-forward={WF}  select on {SEL}", flush=True)
    allP = {k: [] for k in gs.KEYS}; allM = None
    for c in range(0, N, CH):
        P = guarantee_restrict(gs.sample(min(CH, N - c), g)); M = evaluate(P)
        for k in gs.KEYS: allP[k].append(P[k].cpu().numpy())
        allM = M if allM is None else {f: {m: np.concatenate([allM[f][m], M[f][m]]) for m in MET} for f in M}
        print(f"  evaluated {c + len(P['B'])}/{N}  ({time.time()-t0:.0f}s)", flush=True)
    allP = {k: np.concatenate(v) for k, v in allP.items()}
    res = {"guarantee": GUAR, "walkforward": WF, "n": N, "budgets": {}}
    for bgt in BUDGETS:
        s = score(allM, bgt, Lvals(allP)); top = np.argsort(-s)[:150]; top = [i for i in top if s[i] > -1e8]
        if not top: print(f"{bgt:>3}%: no feasible strategy"); continue
        cands = [{k: int(allP[k][i]) for k in gs.KEYS} for i in top]
        rows, owner = [], []
        for ci, p in enumerate(cands):
            for x in neighbours(p): rows.append(x); owner.append(ci)
        NB = guarantee_restrict(stack(rows)); MN = evaluate(NB); sN = score(MN, bgt, Lvals({k: NB[k].cpu().numpy() for k in gs.KEYS}))
        owner = np.array(owner); best = None
        for ci in range(len(cands)):
            v = sN[owner == ci]; med = float(np.median(np.where(v > -1e8, v, -50.0))); ff = float((v > -1e8).mean())
            key = (med, s[top[ci]])
            if best is None or key > best[0]: best = (key, ci, med, ff)
        _, ci, med, ff = best; i = top[ci]
        S = {f: {m: float(allM[f][m][i]) for m in MET} for f in allM}
        res["budgets"][bgt] = dict(params=params_of(cands[ci]), score=float(s[i]), neighbourhood_median=med, neighbourhood_feasible=ff, metrics=S)
        st = [n for n in gs.LADDER if all(gs.static(n, *FOLDS[f])["mdd"] <= bgt for f in SEL) and gs.static(n, *EXTRA["selfull"])["mdd"] <= bgt]
        bs = max(st, key=lambda n: min(gs.static(n, *FOLDS[f])["cagr"] for f in SEL)) if st else None
        so = gs.static(bs, *EXTRA["oos"]) if bs else None
        bs_txt = f"{bs:7} worst-dec {min(gs.static(bs, *FOLDS[f])['cagr'] for f in SEL):5.2f} full {gs.static(bs)['cagr']:5.2f}/{gs.static(bs)['mdd']:4.1f} OOS {so['cagr']:5.2f}/{so['mdd']:4.1f}" if bs else "none"
        print(f"{bgt:>3}% | static {bs_txt} || strategy worst-dec {s[i]:5.2f} (nbhd med {med:5.2f}, {ff*100:3.0f}% feas) full {S['full']['cagr']:5.2f}/{S['full']['mdd']:4.1f} "
              f"OOS {S['oos']['cagr']:5.2f}/{S['oos']['mdd']:4.1f} sw/yr {S['full']['switches']:4.1f}  ({time.time()-t0:.0f}s)", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {OUT}")
