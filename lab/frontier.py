"""Return/safety efficient frontier on the GPU.

For each target CAGR T: maximise SAFETY subject to CAGR >= T (full period) and every decade CAGR >= DEC_FRAC*T.
SAFETY (default "absolute": every period's Ulcer & MDD vs C1 full-period values; "drawdown": vs C1 same-decade) = min over { Ulcer and MaxDD ratios vs C1, full period and each decade } + 0.01*Sharpe
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
SAFETY = os.environ.get("SAFETY", "absolute")   # "nowsafe": absolute + EP_FLOOR/EP22_FLOOR/AIX guard rails | "maxret": TARGETS are max-drawdown caps, maximise CAGR (decade-balanced) | "absolute": every period's Ulcer & MDD vs C1 FULL-period values | "drawdown": vs C1 same-decade values | "ratios": old
B = g.B; T_CUR = [TARGETS[0]]
# --- current-regime ("nowsafe") constraints --------------------------------------------------------------
EP_FLOOR = float(os.environ.get("EP_FLOOR", "-100"))      # every analog episode return >= EP_FLOOR (%)
EP22_FLOOR = float(os.environ.get("EP22_FLOOR", "-100"))  # 2022 inflation/war/rates episode >= this (%)
AIX = float(os.environ.get("AIX", "1e9"))                 # cap on AI/mega-tech notional exposure (% of portfolio)
AI_COEF = {"TQQQSIM": 3, "QLDSIM": 2, "TECLSIM": 3, "QQQSIM": 1, "XLKSIM": 1, "SPMOSIM": 0.6, "VUGSIM": 0.6,
           "UPROSIM": 1.2, "SPXLSIM": 1.2, "SSOSIM": 0.8, "VTISIM": 0.35, "VVSIM": 0.4, "SPYSIM": 0.4, "NTSXSIM": 0.36,
           "NTSDSIM": 0.3, "VTSIM": 0.25, "URTHSIM": 0.3, "XLCSIM": 0.5, "XLYSIM": 0.3, "GDESIM": 0.36}
AIV = torch.tensor([AI_COEF.get(n, 0.0) for n in g.NAMES], device=g.DEV)
I22 = [e[0] for e in rg.EPISODES].index("2022 inflation/war/rates")
def ai_exposure(W): return (AIV.to(W.dtype)[:, None] * W).sum(0)

def score(W, TT=None):
    T = T_CUR[0]; res = []
    if SAFETY == "maxret":                                               # T = max-drawdown cap in % (e.g. 40)
        for i in range(0, W.shape[1], g.CHUNK):
            M = g.metrics(W[:, i:i + g.CHUNK], TT); f = M[0]
            dec = torch.stack([m["cagr"] for m in M[1:]]).min(0).values
            s = torch.minimum(f["cagr"], dec / DEC_FRAC)
            worst_dd = torch.stack([m["mdd"] for m in M]).min(0).values
            s = s + torch.where(worst_dd >= -T, 0.0, -100.0 + (worst_dd + T))
            res.append(torch.nan_to_num(s + 0.01 * f["sharpe"], nan=-1e9))
        return torch.cat(res)
    for i in range(0, W.shape[1], g.CHUNK):
        w = W[:, i:i + g.CHUNK]; M = g.metrics(w, TT); f, b = M[0], B[0]
        pen = torch.where(f["cagr"] >= T, 0.0, -10.0 + (f["cagr"] - T))
        if SAFETY == "ratios":
            parts = [f["sharpe"] / b["sharpe"], f["calmar"] / b["calmar"], b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]
        else:
            parts = [b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]
        for m, bq in zip(M[1:], B[1:]):
            ref = b if SAFETY == "absolute" else bq                    # absolute: fixed yardstick = C1 full period
            parts += ([m["sharpe"] / bq["sharpe"], m["calmar"] / bq["calmar"], bq["ulcer"] / m["ulcer"]] if SAFETY == "ratios"
                      else [ref["ulcer"] / m["ulcer"], ref["mdd"] / m["mdd"]])
            pen = pen + torch.where(m["cagr"] >= DEC_FRAC * T, 0.0, -5.0 + 0.5 * (m["cagr"] - DEC_FRAC * T))
        s = torch.stack(parts).min(0).values + pen
        if SAFETY != "ratios": s = s + 0.01 * f["sharpe"]                      # tie-break
        if SAFETY == "nowsafe":                                                # current-economy guard rails
            ep = rg.episodes(w, TT); worst = ep.min(0).values; e22 = ep[I22]; aix = ai_exposure(w)
            s = s + torch.where(worst >= EP_FLOOR, 0.0, -20.0 + (worst - EP_FLOOR))
            s = s + torch.where(e22 >= EP22_FLOOR, 0.0, -20.0 + (e22 - EP22_FLOOR))
            s = s + torch.where(aix <= AIX, 0.0, -20.0 - 0.1 * (aix - AIX))
            s = s + 0.005 * rg.scen(ep)                                        # tie-break: better in today's analogs
        res.append(torch.nan_to_num(s, nan=-1e9))
    return torch.cat(res)
g.score = score

_PF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "portfolios.json")))
SEED_PF = {}
for nm in os.environ.get("SEEDS", "Safe-Now,C1-Now,C1,C2,FULL#1").split(","):
    if nm not in _PF: continue
    a = _PF[nm]["alloc"]
    if all(k in g.NAMES for k in a):
        v = torch.zeros(g.A, dtype=torch.long, device=g.DEV)
        for k, x in a.items(): v[g.NAMES.index(k)] = x
        SEED_PF[nm] = v

if __name__ == "__main__":
    t0 = time.time(); rng = np.random.default_rng(g.SEED); out = []; prev = None
    if SAFETY == "nowsafe": print(f"nowsafe: every episode >= {EP_FLOOR}%, 2022 >= {EP22_FLOOR}%, AI exposure <= {AIX}%", flush=True)
    print(f"frontier SAFETY={SAFETY} | {g.DEV} | {g.A} assets | targets {TARGETS} | decade floor {DEC_FRAC}xT | climbers {g.CLIMBERS} rounds {g.ROUNDS}", flush=True)
    for T in TARGETS:
        T_CUR[0] = T
        W = g.random_start(g.CLIMBERS, rng); W[0] = g.base_vec()[:, 0].long().to(g.DEV)
        for k, nm in enumerate(SEED_PF, 1):                                 # seed known good portfolios
            W[k] = SEED_PF[nm]
        if prev is not None: W[1 + len(SEED_PF):1 + len(SEED_PF) + len(prev)] = prev[:g.CLIMBERS - 1 - len(SEED_PF)]   # warm start
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
                            scenario=float(rg.scen(torch.tensor(e[:, None], device=g.DEV, dtype=torch.float64))[0]), worst=float(e.min()),
                            ai_exposure=float(ai_exposure(Wt[:, k:k+1])[0])))
        b = out[-len(top)]; a = " ".join(f"{n.replace('SIM','')}{v}" for n, v in b["alloc"].items()); f = b["full"]
        print(f"T={T:4.1f} safety {b['safety']:.3f} | {a:68} CAGR {f['cagr']:5.2f} MDD {f['mdd']:6.2f} Sh {f['sharpe']:.3f} Cal {f['calmar']:.3f} Ulc {f['ulcer']:.3f} | worst analog {b['worst']:+.1f} 2022 {b['episodes']['2022 inflation/war/rates']:+.1f} AI {b['ai_exposure']:.0f}% ({time.time()-t0:.0f}s)", flush=True)
        json.dump(dict(targets=TARGETS, dec_frac=DEC_FRAC, base=g.BASE, base_metrics=B, episodes=rg.EPISODES, results=out), open(g.OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {g.OUT}")
