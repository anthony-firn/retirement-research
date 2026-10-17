"""Return/safety efficient frontier on the GPU.

For each target CAGR T: maximise SAFETY subject to CAGR >= T (full period) and every decade CAGR >= DEC_FRAC*T.
SAFETY (default "drawdown") = min over { Ulcer and MaxDD ratios vs C1, full period and each decade } + 0.01*Sharpe
       ("ratios" = old: Sharpe/Calmar/Ulcer/MDD full + decade Sharpe/Calmar/Ulcer)   (1.0 = as safe as C1 everywhere)
Climbers for each target are warm-started from the previous target's best portfolios.
Env: TARGETS="8,9,...", DEC_FRAC (0.7), CLIMBERS, ROUNDS, HIST, EXCLUDE, OUT.  Run from lab/.
"""
import os, json, time, numpy as np, torch
os.environ.setdefault("BASE", '{"IEISIM":34,"KMLMSIM":20,"UUPSIM":13,"GLDSIM":11,"SPMOSIM":11,"XLPSIM":5,"QLDSIM":3,"XLESIM":3}')
import regime as rg                      # episodes + scenario score (also imports gpusearch)
g = rg.g
TARGETS = [float(x) for x in os.environ.get("TARGETS", "8,9,10,11,12,13,14,15,16").split(",")]
DEC_FRAC = float(os.environ.get("DEC_FRAC", "0.7"))
SAFETY = os.environ.get("SAFETY", "drawdown")   # "drawdown": Ulcer+MDD ratios vs C1 (full + each decade) | "ratios": Sharpe/Calmar/Ulcer/MDD (old)
B = g.B; T_CUR = [TARGETS[0]]

def score(W, TT=None):
    T = T_CUR[0]; res = []
    for i in range(0, W.shape[1], g.CHUNK):
        w = W[:, i:i + g.CHUNK]; M = g.metrics(w, TT); f, b = M[0], B[0]
        pen = torch.where(f["cagr"] >= T, 0.0, -10.0 + (f["cagr"] - T))
        if SAFETY == "ratios":
            parts = [f["sharpe"] / b["sharpe"], f["calmar"] / b["calmar"], b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]
        else:
            parts = [b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]
        for m, bq in zip(M[1:], B[1:]):
            parts += ([m["sharpe"] / bq["sharpe"], m["calmar"] / bq["calmar"], bq["ulcer"] / m["ulcer"]] if SAFETY == "ratios"
                      else [bq["ulcer"] / m["ulcer"], bq["mdd"] / m["mdd"]])
            pen = pen + torch.where(m["cagr"] >= DEC_FRAC * T, 0.0, -5.0 + 0.5 * (m["cagr"] - DEC_FRAC * T))
        s = torch.stack(parts).min(0).values + pen
        if SAFETY != "ratios": s = s + 0.01 * f["sharpe"]                      # tie-break
        res.append(torch.nan_to_num(s, nan=-1e9))
    return torch.cat(res)
g.score = score

if __name__ == "__main__":
    t0 = time.time(); rng = np.random.default_rng(g.SEED); out = []; prev = None
    print(f"frontier SAFETY={SAFETY} | {g.DEV} | {g.A} assets | targets {TARGETS} | decade floor {DEC_FRAC}xT | climbers {g.CLIMBERS} rounds {g.ROUNDS}", flush=True)
    for T in TARGETS:
        T_CUR[0] = T
        W = g.random_start(g.CLIMBERS, rng); W[0] = g.base_vec()[:, 0].long().to(g.DEV)
        if prev is not None: W[1:1 + len(prev)] = prev                       # warm start
        sc = score(W.T.to(torch.float32)); W, sc = g.climb(W, sc)
        for r in range(g.ROUNDS):
            Wp = g.perturb(W, rng); sp = score(Wp.T.to(torch.float32)); Wp, sp = g.climb(Wp, sp)
            better = sp > sc; W[better] = Wp[better]; sc[better] = sp[better]
        order = torch.argsort(sc, descending=True); prev = W[order[:min(256, g.CLIMBERS - 1)]].clone()
        Wn = W[order[:40]].cpu().numpy(); seen = set(); top = []
        for x in Wn:
            k = tuple(x)
            if k not in seen: seen.add(k); top.append(x)
            if len(top) == 3: break
        Wt = torch.tensor(np.array(top).T, dtype=torch.float64, device=g.DEV)
        s64 = score(Wt, g.G64).cpu().numpy(); M = g.metrics(Wt, g.G64); ep = rg.episodes(Wt, g.G64)
        for k in range(len(top)):
            alloc = {g.NAMES[j]: int(top[k][j]) for j in np.argsort(-top[k]) if top[k][j] > 0}
            f = {m: float(M[0][m][k]) for m in M[0]}
            e = ep[:, k].cpu().numpy()
            out.append(dict(target=T, rank=k + 1, alloc=alloc, safety=float(s64[k]), full=f,
                            decades={p: {m: float(M[i][m][k]) for m in ("cagr", "sharpe", "calmar", "ulcer", "mdd")} for i, p in enumerate(g.PLABEL[1:], 1)},
                            episodes=dict(zip([x[0] for x in rg.EPISODES], e.tolist())),
                            scenario=float(rg.scen(torch.tensor(e[:, None], device=g.DEV, dtype=torch.float64))[0]), worst=float(e.min())))
        b = out[-len(top)]; a = " ".join(f"{n.replace('SIM','')}{v}" for n, v in b["alloc"].items()); f = b["full"]
        print(f"T={T:4.1f} safety {b['safety']:.3f} | {a:68} CAGR {f['cagr']:5.2f} MDD {f['mdd']:6.2f} Sh {f['sharpe']:.3f} Cal {f['calmar']:.3f} Ulc {f['ulcer']:.3f} | worst analog {b['worst']:+.1f} ({time.time()-t0:.0f}s)", flush=True)
        json.dump(dict(targets=TARGETS, dec_frac=DEC_FRAC, base=g.BASE, base_metrics=B, episodes=rg.EPISODES, results=out), open(g.OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {g.OUT}")
