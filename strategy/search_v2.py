"""Robust GPU strategy search (v2).
- Folds: 4 calendar decades + full period. Hard constraint: MDD <= budget in EVERY fold.
- Score: min over decade folds of CAGR (worst-decade CAGR).
- GUARANTEE=1: drawdown governor uses the all-time high (DECAY=0), governor budget L <= budget-2, M >= 1,
  so total loss is bounded by construction (~ L + worst day of the safest tier).
- Stage 2: neighbourhood check - every parameter +/-1 notch; pick the strategy with the best neighbourhood-MEDIAN score.
- WALKFWD=1: select using only folds before 2007, then report 2007-2026 out-of-sample.
Env: N, CHUNK, SEED, GUARANTEE, WALKFWD, OUT."""
import os, json, time, numpy as np, torch
import gpu_strategy as gs

N = int(os.environ.get("N", "300000")); CH = int(os.environ.get("CHUNK", "50000")); SEED = int(os.environ.get("SEED", "2"))
GUAR = os.environ.get("GUARANTEE", "1") == "1"; WF = os.environ.get("WALKFWD", "0") == "1"
OUT = os.environ.get("OUT", os.path.join(gs.ROOT, f"v2_{'guar' if GUAR else 'free'}{'_wf' if WF else ''}.json"))
BUDGETS = [int(x) for x in os.environ.get("BUDGETS", "6,8,10,12,15,20,25,30,40").split(",")]
yr = gs.YEARS
def rng(a, b): return int(np.searchsorted(yr, a)), int(np.searchsorted(yr, b + 1))
FOLDS = {"1988-1997": rng(1987, 1997), "1998-2007": rng(1998, 2007), "2008-2017": rng(2008, 2017), "2018-2026": rng(2018, 2026), "full": (0, gs.T)}
SEL = ["1988-1997", "1998-2007"] if WF else ["1988-1997", "1998-2007", "2008-2017", "2018-2026"]
SEL_FULL = rng(1987, 2006) if WF else (0, gs.T)
OOS = rng(2007, 2026)

def evaluate(P):
    out = {f: gs.run(P, a, b) for f, (a, b) in FOLDS.items()}
    out["selfull"] = gs.run(P, *SEL_FULL); out["oos"] = gs.run(P, *OOS)
    return out

def score(M, bgt):
    feas = (M["selfull"]["mdd"] <= bgt)
    for f in SEL: feas &= M[f]["mdd"] <= bgt
    s = torch.stack([M[f]["cagr"] for f in SEL]).min(0).values
    return torch.where(feas, s, torch.full_like(s, -1e9))

def restrict(P, bgt):
    """Guarantee mode: DECAY=0, L <= bgt-2, M >= 1."""
    if not GUAR: return P
    P["DECAY"] = torch.zeros_like(P["DECAY"])
    Ls = torch.tensor(gs.SPACE["L"], device=gs.DEV); allowed = torch.nonzero(Ls <= bgt - 2).squeeze(1)
    if len(allowed) == 0: allowed = torch.tensor([0], device=gs.DEV)
    P["L"] = torch.where(Ls[P["L"]] <= bgt - 2, P["L"], allowed[torch.randint(len(allowed), P["L"].shape, device=gs.DEV)])
    Ms = torch.tensor(gs.SPACE["M"], device=gs.DEV); P["M"] = torch.where(Ms[P["M"]] >= 1.0, P["M"], torch.full_like(P["M"], gs.SPACE["M"].index(1.0)))
    return P

def neighbours(P, i):
    base = {k: int(P[k][i]) for k in gs.KEYS}; nb = [base]
    for k in gs.KEYS:
        for d in (-1, 1):
            j = base[k] + d
            if 0 <= j < len(gs.SPACE[k]): x = dict(base); x[k] = j; nb.append(x)
    return {k: torch.tensor([x[k] for x in nb], device=gs.DEV) for k in gs.KEYS}

def to_params(P, i): return {k: gs.SPACE[k][int(P[k][i])] for k in gs.KEYS}
def summary(M, i): return {f: {m: float(M[f][m][i]) for m in ("cagr", "mdd", "ulcer", "sharpe", "switches", "worst_day")} for f in M}

if __name__ == "__main__":
    t0 = time.time(); g = np.random.default_rng(SEED); res = {"guarantee": GUAR, "walkforward": WF, "budgets": {}}
    print(f"v2 search  N={N}  guarantee={GUAR}  walk-forward={WF}  select on {SEL}", flush=True)
    for bgt in BUDGETS:
        best = []                                                     # (score, P-chunk, idx)
        for c in range(0, N, CH):
            P = restrict(gs.sample(min(CH, N - c), g), bgt); M = evaluate(P); s = score(M, bgt)
            top = torch.topk(s, min(100, len(s))).indices
            for i in top.tolist():
                if s[i] > -1e8: best.append((float(s[i]), {k: int(P[k][i]) for k in gs.KEYS}))
        best.sort(key=lambda x: -x[0]); best = best[:150]
        if not best: print(f"{bgt:>3}%: no feasible strategy"); continue
        # stage 2: neighbourhood robustness
        cand = []
        for sc, p in best:
            P1 = {k: torch.tensor([p[k]], device=gs.DEV) for k in gs.KEYS}; NB = restrict(neighbours(P1, 0), bgt)
            sN = score(evaluate(NB), bgt); med = float(torch.median(torch.where(sN > -1e8, sN, torch.full_like(sN, float("nan"))).nan_to_num(nan=-50.0)))
            feas_frac = float((sN > -1e8).float().mean())
            cand.append((med, feas_frac, sc, p))
        cand.sort(key=lambda x: (-x[0], -x[2])); med, ff, sc, p = cand[0]
        P1 = {k: torch.tensor([p[k]], device=gs.DEV) for k in gs.KEYS}; M = evaluate(P1); S = summary(M, 0)
        res["budgets"][bgt] = dict(params=to_params(P1, 0), score=sc, neighbourhood_median=med, neighbourhood_feasible=ff, metrics=S)
        st = [n for n in gs.LADDER if all(gs.static(n, a, b)["mdd"] <= bgt for a, b in [FOLDS[f] for f in SEL] + [SEL_FULL])]
        bs = max(st, key=lambda n: min(gs.static(n, *FOLDS[f])["cagr"] for f in SEL)) if st else None
        bs_txt = f"{bs:7} worst-dec {min(gs.static(bs, *FOLDS[f])['cagr'] for f in SEL):5.2f} full {gs.static(bs)['cagr']:5.2f}/{gs.static(bs)['mdd']:4.1f} OOS {gs.static(bs, *OOS)['cagr']:5.2f}/{gs.static(bs, *OOS)['mdd']:4.1f}" if bs else "none"
        print(f"{bgt:>3}% | static {bs_txt} || strategy worst-dec {sc:5.2f} (nbhd med {med:5.2f}, {ff*100:3.0f}% feas) full {S['full']['cagr']:5.2f}/{S['full']['mdd']:4.1f} "
              f"OOS {S['oos']['cagr']:5.2f}/{S['oos']['mdd']:4.1f} sw/yr {S['full']['switches']:4.1f}  ({time.time()-t0:.0f}s)", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {OUT}")
