"""Regime-aware GPU search: tune C1-style portfolios for the Oct-2026 environment.

Scenario set = historical episodes (1988-2026) that resemble today's risks
(AI/tech bubble, oil/war shock, Fed hiking into inflation, 10y > 5%, credit stress, policy shock).
MODE=now  : keep C1's full-history quality (>=95% of C1 Sharpe/Calmar/Ulcer, MDD within 0.5pt,
            CAGR >= C1-0.3, each decade Sharpe >= 90% of C1) and MAXIMISE scenario score.
MODE=safe : CAGR >= 6.5%, every scenario >= -3%, scenario score >= C1's, then MAXIMISE
            min(Sharpe, Calmar, 1/Ulcer, 1/MDD vs C1).
scenario score = weighted mean episode return + 0.5 * worst episode return   (percent)
Env: same as gpusearch.py plus MODE.  Run from lab/.
"""
import os, json, time, numpy as np, torch, datetime as dt
os.environ.setdefault("BASE", '{"IEISIM":34,"KMLMSIM":20,"UUPSIM":13,"GLDSIM":11,"SPMOSIM":11,"XLPSIM":5,"QLDSIM":3,"XLESIM":3}')
import gpusearch as g

MODE = os.environ.get("MODE", "now")
EPISODES = [  # name, start, end, weight
    ("1990 Gulf War oil shock",   "1990-07-16", "1990-10-11", 1.5),
    ("1994 Fed hikes / bond crash","1994-01-31", "1994-11-22", 1.0),
    ("2000-02 tech bubble burst", "2000-03-24", "2002-10-09", 2.0),
    ("2007-09 credit crisis",     "2007-10-09", "2009-03-09", 1.0),
    ("2013 taper tantrum",        "2013-05-02", "2013-09-05", 1.0),
    ("2018 Q4 Fed + tech",        "2018-09-20", "2018-12-24", 1.0),
    ("2020 Covid crash",          "2020-02-19", "2020-03-23", 1.0),
    ("2022 inflation/war/rates",  "2022-01-03", "2022-10-14", 2.0),
    ("2023 10y to 5%",            "2023-07-31", "2023-10-27", 1.5),
    ("2025 tariff shock",         "2025-02-19", "2025-04-08", 1.0),
]
td = np.array([dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in g.H["t"]])
EI = torch.tensor([np.searchsorted(td, a) for _, a, _, _ in EPISODES], device=g.DEV)
EJ = torch.tensor([np.searchsorted(td, b) for _, _, b, _ in EPISODES], device=g.DEV)
EW = torch.tensor([w for *_, w in EPISODES], device=g.DEV); EW = EW / EW.sum()

def paths(W, TT=None):
    G, sg, er, rf = TT or g.G32
    W = W.to(G.dtype) / 100.0
    V = G @ W; lev = torch.cumprod(V[er], 0); lev = torch.cat([torch.ones_like(lev[:1]), lev[:-1]], 0)
    return V * lev[sg]

def episodes(W, TT=None):
    V = paths(W, TT); return (V[EJ] / V[EI] - 1) * 100            # (E,n)

def scen(ep): return (EW.to(ep.dtype)[:, None] * ep).sum(0) + 0.5 * ep.min(0).values

Bep = episodes(g.base_vec().to(g.DEV), g.G64)[:, 0]; Bsc = float(scen(Bep[:, None])[0])
B = g.B

def score(W, TT=None):
    res = []
    for i in range(0, W.shape[1], g.CHUNK):
        w = W[:, i:i + g.CHUNK]; M = g.metrics(w, TT); f, b = M[0], B[0]; ep = episodes(w, TT); sc = scen(ep)
        pen = torch.zeros_like(sc)
        if MODE == "now":
            pen -= 100 * ((f["sharpe"] < 0.95 * b["sharpe"]) | (f["calmar"] < 0.95 * b["calmar"]) | (f["ulcer"] > 1.05 * b["ulcer"])
                          | (f["mdd"] < b["mdd"] - 0.5) | (f["cagr"] < b["cagr"] - 0.3)).to(sc.dtype)
            for m, bq in zip(M[1:], B[1:]): pen -= 100 * (m["sharpe"] < 0.9 * bq["sharpe"]).to(sc.dtype)
            s = sc + pen
        else:
            pen -= 100 * ((f["cagr"] < 6.5) | (ep.min(0).values < -3.0) | (sc < Bsc)).to(sc.dtype)
            q = torch.stack([f["sharpe"] / b["sharpe"], f["calmar"] / b["calmar"], b["ulcer"] / f["ulcer"], b["mdd"] / f["mdd"]]).min(0).values
            s = q + pen
        res.append(torch.nan_to_num(s, nan=-1e9))
    return torch.cat(res)
g.score = score                                                    # climb() picks this up

if __name__ == "__main__":
    t0 = time.time(); rng = np.random.default_rng(g.SEED)
    print(f"MODE={MODE} | {g.DEV} | {g.A} assets | climbers {g.CLIMBERS} rounds {g.ROUNDS}", flush=True)
    print("C1 episodes: " + " | ".join(f"{n.split()[0]} {x:+.1f}" for (n, *_), x in zip(EPISODES, Bep.tolist())) + f"  -> scenario score {Bsc:.2f}")
    W = g.random_start(g.CLIMBERS, rng); W[0] = g.base_vec()[:, 0].long().to(g.DEV)
    sc = score(W.T.to(torch.float32)); W, sc = g.climb(W, sc)
    print(f"  initial climb best {sc.max().item():.3f} ({time.time()-t0:.0f}s)", flush=True)
    for r in range(g.ROUNDS):
        Wp = g.perturb(W, rng); sp = score(Wp.T.to(torch.float32)); Wp, sp = g.climb(Wp, sp)
        better = sp > sc; W[better] = Wp[better]; sc[better] = sp[better]
        print(f"  round {r+1}/{g.ROUNDS} best {sc.max().item():.3f} ({time.time()-t0:.0f}s)", flush=True)
    Wn = W.cpu().numpy(); order = np.argsort(-sc.cpu().numpy()); seen = set(); top = []
    for i in order:
        k = tuple(Wn[i])
        if k not in seen: seen.add(k); top.append(Wn[i])
        if len(top) == 15: break
    Wt = torch.tensor(np.array(top).T, dtype=torch.float64, device=g.DEV)
    s64 = score(Wt, g.G64).cpu().numpy(); M = g.metrics(Wt, g.G64); ep = episodes(Wt, g.G64).cpu().numpy()
    res = []
    for k in range(len(top)):
        alloc = {g.NAMES[j]: int(top[k][j]) for j in np.argsort(-top[k]) if top[k][j] > 0}
        f = {m: float(M[0][m][k]) for m in M[0]}
        res.append(dict(alloc=alloc, score=float(s64[k]), full=f, episodes=dict(zip([e[0] for e in EPISODES], ep[:, k].tolist())),
                        scenario=float(scen(torch.tensor(ep[:, k:k+1], device=g.DEV, dtype=torch.float64))[0]),
                        decade_sharpe=[float(M[p]["sharpe"][k]) for p in range(1, 5)]))
        if k < 8:
            a = " ".join(f"{n.replace('SIM','')}{v}" for n, v in alloc.items())
            print(f"#{k+1} {a:66} CAGR {f['cagr']:5.2f} MDD {f['mdd']:6.2f} Sh {f['sharpe']:.3f} Cal {f['calmar']:.3f} Ulc {f['ulcer']:.3f} | scen {res[-1]['scenario']:+.2f} worst {ep[:,k].min():+.1f}")
    json.dump(dict(mode=MODE, base=g.BASE, base_episodes=Bep.tolist(), base_scenario=Bsc, episodes=EPISODES, results=res), open(g.OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {g.OUT}")
