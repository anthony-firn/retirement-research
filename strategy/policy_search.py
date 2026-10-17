"""Final policy search: life-stage tier (incl. half-tier blends) + guaranteed catastrophe breaker, NO timing signals.
Exhaustive grid on the GPU. For each budget b: breaker L <= b-2 on the all-time high (DECAY=0, M>=1) so
total loss is capped by construction; MDD <= b required in every decade and the full period.
Selection: best worst-decade CAGR. Also walk-forward: select on 1988-2006, report 2007-2026."""
import os, json, itertools, numpy as np, torch
import gpu_strategy as gs

yr = gs.YEARS
def rng(a, b): return int(np.searchsorted(yr, a)), int(np.searchsorted(yr, b + 1))
FOLDS = {"1988-1997": rng(1987, 1997), "1998-2007": rng(1998, 2007), "2008-2017": rng(2008, 2017), "2018-2026": rng(2018, 2026), "full": (0, gs.T),
         "is": rng(1987, 2006), "oos": rng(2007, 2026)}
BUDGETS = [6, 8, 10, 12, 15, 20, 25, 30, 40, 50]
off = dict(DECAY=0, SMA=gs.SPACE["SMA"].index(-1), S_TREND=0, VOL=0, S_VOL=0, VIXL=0, S_VIX=0, RATE=0, S_RATE=0, HEDGE=0)
grid = []
for B, L, M, WF, H, DB in itertools.product(range(len(gs.SPACE["B"])), range(len(gs.SPACE["L"])), [gs.SPACE["M"].index(x) for x in (1.0, 1.5, 2.0)],
                                            range(len(gs.SPACE["WEEKF"])), range(len(gs.SPACE["H"])), range(len(gs.SPACE["DB"]))):
    grid.append(dict(off, B=B, L=L, M=M, WEEKF=WF, H=H, DB=DB))
P = {k: torch.tensor([g[k] for g in grid], device=gs.DEV) for k in gs.KEYS}
print(f"{len(grid)} tier+breaker policies", flush=True)
M = {}
for f, (a, b) in FOLDS.items():
    out = {k: [] for k in ("cagr", "mdd", "ulcer", "sharpe", "switches")}
    for c in range(0, len(grid), 60000):
        sub = {k: v[c:c + 60000] for k, v in P.items()}; m = gs.run(sub, a, b)
        for k in out: out[k].append(m[k].cpu().numpy())
    M[f] = {k: np.concatenate(v) for k, v in out.items()}; print("  fold", f, "done", flush=True)
Lv = np.array(gs.SPACE["L"])[P["L"].cpu().numpy()]
DEC = ["1988-1997", "1998-2007", "2008-2017", "2018-2026"]
res = {}
print(f"\n{'budget':>6} | {'policy (all decades)':58} | full CAGR/MDD | 2007-26 | walk-forward pick (IS) -> 2007-26")
for bgt in BUDGETS:
    ok = (Lv <= bgt - 2) & (M["full"]["mdd"] <= bgt)
    for f in DEC: ok &= M[f]["mdd"] <= bgt
    s = np.where(ok, np.min([M[f]["cagr"] for f in DEC], 0), -1e9); i = int(np.argmax(s))
    okw = (Lv <= bgt - 2) & (M["is"]["mdd"] <= bgt) & (M["1988-1997"]["mdd"] <= bgt) & (M["1998-2007"]["mdd"] <= bgt)
    sw = np.where(okw, np.minimum(M["1988-1997"]["cagr"], M["1998-2007"]["cagr"]), -1e9); j = int(np.argmax(sw))
    pol = {k: gs.SPACE[k][grid[i][k]] for k in gs.KEYS}; polw = {k: gs.SPACE[k][grid[j][k]] for k in gs.KEYS}
    def desc(p):
        lo = int(p["B"]); f = p["B"] - lo; name = gs.LADDER[lo] if f == 0 else f"{1-f:.0%} {gs.LADDER[lo]} + {f:.0%} {gs.LADDER[lo+1]}"
        return f"{name}, breaker {p['L']}% (x{p['M']}, wk/{p['WEEKF']}), re-entry {p['H']}d, band {p['DB']}"
    res[bgt] = dict(policy=pol, metrics={f: {k: float(M[f][k][i]) for k in M[f]} for f in M}, walkforward=dict(policy=polw, oos={k: float(M["oos"][k][j]) for k in M["oos"]}))
    print(f"{bgt:>5}% | {desc(pol):58} | {M['full']['cagr'][i]:5.2f}/{M['full']['mdd'][i]:5.1f} | {M['oos']['cagr'][i]:5.2f}/{M['oos']['mdd'][i]:5.1f} | "
          f"{desc(polw)[:40]:40} -> {M['oos']['cagr'][j]:5.2f}/{M['oos']['mdd'][j]:5.1f}")
json.dump(res, open(os.path.join(gs.ROOT, "policy.json"), "w"), indent=1)
