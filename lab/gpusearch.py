"""GPU-batched portfolio search (PyTorch; falls back to multithreaded CPU).

Same rules/objective as beat_r1.py, much faster:
  * within-year growth matrix G is precomputed once  -> a portfolio path is one matmul + per-year scaling
  * decade metrics are slices of the full path (no re-simulation)
  * hundreds of hill-climbers advance in lockstep; all their neighbours are scored in one GPU batch

Objective (maximize): min over { full-period Sharpe, Calmar, 1/Ulcer, 1/MaxDD ratios vs BASE,
                                 each decade's Sharpe, Calmar, 1/Ulcer ratios vs BASE }
  subject to: CAGR >= BASE CAGR, <= K holdings, <= CAP % each, integer percents.
Score > 1  <=>  beats BASE on every one of those numbers.

Env: HIST (dataset json), BASE (json alloc), CLIMBERS, ROUNDS, SEED, OUT, CAP, K, DEVICE
"""
import os, json, time, math
import numpy as np, torch, datetime as dt

HIST = os.environ.get("HIST", "clean_etf.json")
BASE = json.loads(os.environ.get("BASE", '{"SHYSIM":25,"SPMOSIM":20,"GLDSIM":15,"KMLMSIM":20,"UUPSIM":10,"XLVSIM":5,"ZROZSIM":5}'))
CLIMBERS = int(os.environ.get("CLIMBERS", "512"))
ROUNDS = int(os.environ.get("ROUNDS", "8"))          # perturb + re-climb rounds (iterated local search)
SEED = int(os.environ.get("SEED", "0"))
CAP = int(os.environ.get("CAP", "35")); K = int(os.environ.get("K", "8"))
OUT = os.environ.get("OUT", "gpu_res.json")
DEV = torch.device(os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu"))
CHUNK = int(os.environ.get("CHUNK", "6000"))          # portfolios per GPU batch (memory bound)

# ---------------------------------------------------------------- data
H = json.load(open(HIST)); NAMES = H["names"]; A = len(NAMES)
P = np.array(H["v"], dtype=np.float64).T; RF = np.array(H["rf"], dtype=np.float64)
years = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in H["t"]])
T = len(years)
bounds = np.flatnonzero(np.diff(years)) + 1
starts = np.r_[0, bounds]; ends = np.r_[bounds, T]
Gnp = np.empty_like(P); seg = np.empty(T, dtype=np.int64)
for k, (a, b) in enumerate(zip(starts, ends)):
    ref = P[a - 1] if a > 0 else P[0]                 # rebalance at prior year's last close
    Gnp[a:b] = P[a:b] / ref; seg[a:b] = k
end_rows = ends - 1
rfx = RF[1:] / RF[:-1] - 1
qc = np.quantile(years, [.25, .5, .75])
qmask = [years <= qc[0], (years > qc[0]) & (years <= qc[1]), (years > qc[1]) & (years <= qc[2]), years > qc[2]]
PERIODS = [(0, T - 1)] + [(max(np.flatnonzero(m)[0] - 1, 0), np.flatnonzero(m)[-1]) for m in qmask]   # inclusive row ranges
PLABEL = ["full"] + [f"{years[max(a,1)]}-{years[b]}" for a, b in PERIODS[1:]]

def tensors(dtype):
    return (torch.tensor(Gnp, dtype=dtype, device=DEV), torch.tensor(seg, device=DEV),
            torch.tensor(end_rows, device=DEV), torch.tensor(rfx, dtype=dtype, device=DEV))
G32 = tensors(torch.float32)

def metrics(W, TT=None):
    """W: (A,n) weights in percent (any float dtype). Returns list (full + decades) of dict metric -> (n,) tensor."""
    G, sg, er, rf = TT or G32
    W = W.to(G.dtype) / 100.0
    V = G @ W                                          # (T,n) within-year growth
    lev = torch.cumprod(V[er], 0)                      # value at each year end
    lev = torch.cat([torch.ones_like(lev[:1]), lev[:-1]], 0)
    V = V * lev[sg]
    out = []
    for a, b in PERIODS:
        Vs = V[a:b + 1]; n = Vs.shape[0]; yrs = n / 252.0
        r = Vs[1:] / Vs[:-1] - 1
        ex = r - rf[a:b, None]
        cagr = (Vs[-1] / Vs[0]) ** (1 / yrs) - 1
        sharpe = ex.mean(0) * 252 / (ex.std(0, unbiased=False) * math.sqrt(252))
        dd = Vs / torch.cummax(Vs, 0).values - 1
        mdd = dd.min(0).values
        ulcer = torch.sqrt(((dd * 100) ** 2).mean(0))
        out.append(dict(cagr=cagr * 100, sharpe=sharpe, mdd=mdd * 100, ulcer=ulcer, calmar=cagr / -mdd, std=r.std(0, unbiased=False) * math.sqrt(252) * 100))
    return out

def base_vec():
    w = torch.zeros(A, 1, dtype=torch.float64)
    for k, v in BASE.items(): w[NAMES.index(k), 0] = v
    return w
G64 = tensors(torch.float64)
B = [{k: float(v[0]) for k, v in p.items()} for p in metrics(base_vec().to(DEV), G64)]

def score(W, TT=None):
    """W (A,n) percent -> (n,) score on device; scored in chunks."""
    res = []
    for i in range(0, W.shape[1], CHUNK):
        M = metrics(W[:, i:i + CHUNK], TT)
        f, b = M[0], B[0]
        parts = [f["sharpe"] / b["sharpe"], f["calmar"] / b["calmar"], b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]
        for m, bq in zip(M[1:], B[1:]):
            parts += [m["sharpe"] / bq["sharpe"], m["calmar"] / bq["calmar"], bq["ulcer"] / m["ulcer"]]
        s = torch.stack(parts).min(0).values
        s = s + torch.where(f["cagr"] >= b["cagr"] + 0.01, 0.0, -10.0 + (f["cagr"] - b["cagr"]))
        res.append(torch.nan_to_num(s, nan=-1e9))
    return torch.cat(res)

# ---------------------------------------------------------------- batched hill climbing
def neighbours(Wc, step):
    """Wc: (C,A) int percents. All moves 'step' points from a held asset i to any asset j.
    Returns cand (M,A), owner (M,) climber index."""
    C = Wc.shape[0]
    held = Wc >= step                                                     # (C,A) sources
    ci, ii = torch.nonzero(held, as_tuple=True)                           # source pairs
    jj = torch.arange(A, device=DEV)
    ci = ci.repeat_interleave(A); ii = ii.repeat_interleave(A); jj = jj.repeat(len(held.nonzero()))
    keep = ii != jj
    ci, ii, jj = ci[keep], ii[keep], jj[keep]
    cand = Wc[ci].clone()
    r = torch.arange(len(ci), device=DEV)
    cand[r, ii] -= step; cand[r, jj] += step
    ok = (cand[r, jj] <= CAP) & ((cand > 0).sum(1) <= K)
    return cand[ok], ci[ok]

def climb(Wc, sc, steps=(5, 2, 1)):
    """Advance all climbers until none improves. Wc (C,A) int, sc (C,) scores."""
    for s in steps:
        active = torch.ones(Wc.shape[0], dtype=torch.bool, device=DEV)
        while active.any():
            idx = torch.nonzero(active).squeeze(1)
            cand, own = neighbours(Wc[idx], s)
            if len(cand) == 0: break
            cs = score(cand.T.to(torch.float32))
            best = torch.full((len(idx),), -1e18, device=DEV).scatter_reduce(0, own, cs, reduce="amax")
            # pick one argmax per owner
            is_best = cs == best[own]
            first = torch.full((len(idx),), -1, dtype=torch.long, device=DEV)
            first.scatter_reduce_(0, own[is_best], torch.nonzero(is_best).squeeze(1), reduce="amax", include_self=True)
            improve = best > sc[idx] + 1e-7
            upd = idx[improve]
            Wc[upd] = cand[first[improve]]; sc[upd] = best[improve]
            active[:] = False; active[upd] = True
    return Wc, sc

def random_start(C, g):
    W = torch.zeros(C, A, dtype=torch.long)
    for c in range(C):
        k = int(g.integers(4, K + 1)); pick = g.choice(A, k, replace=False)
        x = np.round(g.dirichlet(np.ones(k)) * 100); x = np.minimum(x, CAP)
        x[np.argmin(x)] += 100 - x.sum()
        if x.min() < 0 or x.max() > CAP: x = np.full(k, 0.0); x[:] = 100 // k; x[0] += 100 - x.sum()
        W[c, torch.tensor(pick)] = torch.tensor(x, dtype=torch.long)
    return W.to(DEV)

def perturb(Wc, g):
    W = Wc.clone()
    for c in range(W.shape[0]):
        for _ in range(int(g.integers(1, 4))):                     # 1-3 random moves of 5-15 points
            held = torch.nonzero(W[c] > 0).squeeze(1).cpu().numpy()
            i = int(g.choice(held)); j = int(g.integers(A)); amt = int(min(W[c, i], g.integers(5, 16)))
            if i == j or W[c, j] + amt > CAP: continue
            W[c, i] -= amt; W[c, j] += amt
            if (W[c] > 0).sum() > K: W[c, j] -= amt; W[c, i] += amt
    return W

if __name__ == "__main__":
    t0 = time.time(); g = np.random.default_rng(SEED)
    print(f"device {DEV} | {A} assets | {T} days | climbers {CLIMBERS} | rounds {ROUNDS} | periods {PLABEL}", flush=True)
    W = random_start(CLIMBERS, g); W[0] = base_vec()[:, 0].long().to(DEV)
    sc = score(W.T.to(torch.float32)); W, sc = climb(W, sc)
    print(f"  initial climb done  best {sc.max().item():.4f}  ({time.time()-t0:.1f}s)", flush=True)
    for r in range(ROUNDS):
        Wp = perturb(W, g); sp = score(Wp.T.to(torch.float32)); Wp, sp = climb(Wp, sp)
        better = sp > sc; W[better] = Wp[better]; sc[better] = sp[better]
        print(f"  round {r+1}/{ROUNDS}  best {sc.max().item():.4f}  improved {int(better.sum())} climbers  ({time.time()-t0:.1f}s)", flush=True)
    # unique, re-scored in float64
    Wn = W.cpu().numpy(); order = np.argsort(-sc.cpu().numpy()); seen = set(); top = []
    for i in order:
        key = tuple(Wn[i]);
        if key in seen: continue
        seen.add(key); top.append(Wn[i])
        if len(top) == 25: break
    Wt = torch.tensor(np.array(top).T, dtype=torch.float64, device=DEV)
    s64 = score(Wt, G64).cpu().numpy(); M = metrics(Wt, G64)
    lab = lambda n: n.replace("SIM", "")
    print(f"\nBASE   CAGR {B[0]['cagr']:.2f} MDD {B[0]['mdd']:.2f} Sh {B[0]['sharpe']:.3f} Cal {B[0]['calmar']:.3f} Ulc {B[0]['ulcer']:.3f}")
    res = []
    for k in range(len(top)):
        alloc = {NAMES[j]: int(top[k][j]) for j in np.argsort(-top[k]) if top[k][j] > 0}
        f = {m: float(M[0][m][k]) for m in M[0]}
        dec = [{m: float(M[p][m][k]) for m in ("sharpe", "calmar", "ulcer", "cagr")} for p in range(1, 5)]
        res.append(dict(alloc=alloc, score=float(s64[k]), full=f, decades=dict(zip(PLABEL[1:], dec))))
        if k < 12:
            a = " ".join(f"{lab(n)}{v}" for n, v in alloc.items())
            print(f"#{k+1:<3} {a:70} CAGR {f['cagr']:5.2f} MDD {f['mdd']:6.2f} Sh {f['sharpe']:.3f} Cal {f['calmar']:.3f} Ulc {f['ulcer']:.3f} | score {s64[k]:.4f}")
    json.dump(dict(hist=HIST, base=BASE, base_metrics=B, periods=PLABEL, results=res, seconds=time.time() - t0), open(OUT, "w"), indent=1)
    print(f"\ndone in {time.time()-t0:.1f}s -> {OUT}")
