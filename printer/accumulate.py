"""Accumulation search: the best IRA portfolio for a 30-year-old couple (no taxes inside the IRA), by drawdown tolerance.

Simulation (GPU, reshuffled 1972-2026 histories): start $8k, contribute $15k/yr real (monthly, raised with inflation), new money
goes to underweight funds first; rebalance when any fund is > 6 points off target (at most yearly) or a fund hits 2x target.
Score: certainty-equivalent real wealth at 65 (CRRA, GAMMA=3: bad outcomes weigh heavily), averaged over the base case,
trend funds -2%/yr and gold -3%/yr. Constraint: 90th-percentile max drawdown lived through (of the invested NAV) <= CAP.
Guard rails: <= 9 funds, <= 50% each, no-wipeout: worst single day of 1972-2026 (incl. Oct 1987) >= -25%,
leveraged notional <= 200%, every bad forward scenario >= -40%.
Usage: python3 printer/accumulate.py search <cap%> | validate"""
import os, sys, json, time, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "..", "lab"))
import money_printer as mp
import stress_forward as sf
DEV, f32 = mp.DEV, mp.f32
YEARS = 35; V0 = 8.0; CONTRIB = 15.0; GAMMA = 3.0; COST = 0.0005          # $k
UNIVERSE = ["VTISIM", "VBRSIM", "VTVSIM", "SPMOSIM", "XLVSIM", "XLESIM", "XLPSIM", "VXUSSIM", "UPROSIM", "SSOSIM", "QLDSIM", "TQQQSIM", "TMFSIM", "TYDSIM",
            "UBTSIM", "UGLSIM", "GDESIM", "NTSXSIM", "RSSBSIM", "KMLMSIM", "DBMFSIM", "GLDSIM", "ZROZSIM", "TLTSIM", "IEISIM", "REITSIM", "UUPSIM"]
LEVX = {"UPROSIM": 3, "SSOSIM": 2, "QLDSIM": 2, "TQQQSIM": 3, "TMFSIM": 3, "TYDSIM": 3, "UBTSIM": 2, "UGLSIM": 2, "GDESIM": 1.8, "NTSXSIM": 1.5, "RSSBSIM": 2}
BAD = [k for k in sf.SC if not k.startswith("Soft")]
RD = {n: mp.fund_returns(n) for n in UNIVERSE}
def valid(a):
    if len(a) > 9 or any(w < 1 or w > 50 for w in a.values()) or sum(a.values()) != 100 or any(t not in UNIVERSE for t in a): return False
    if sum(LEVX.get(t, 1) * w for t, w in a.items()) > 200: return False
    day = sum(w / 100 * RD[t] for t, w in a.items())
    if day[1:].min() < -0.25: return False
    return min(sum(w / 100 * sf.move(t, sf.SC[k]) for t, w in a.items()) for k in BAD) >= -40

def simulate(allocs, IDX, step=5, trend_haircut=0.0, drag=None, band=6.0, gap_days=252, valve=2.0):
    assets = sorted({a for al in allocs for a in al}); K = max(len(a) for a in allocs)
    Rm = np.stack([mp.fund_returns(a) for a in assets], 1)
    for a in ("KMLMSIM", "DBMFSIM"):
        if a in assets and trend_haircut: Rm[:, assets.index(a)] -= trend_haircut / 252
    for a, x in (drag or {}).items():
        if a in assets: Rm[:, assets.index(a)] -= x / 252
    Rg = torch.tensor(mp._compound(1 + Rm, step) - 1, device=DEV, dtype=f32); Cg = torch.tensor(mp._compound(mp.CPIR, step), device=DEV, dtype=f32)
    S = 252 if step == 1 else 250 // step; C, P = len(allocs), IDX.shape[0]; N = C * P; L = IDX.shape[1]
    ci = torch.arange(C, device=DEV).repeat_interleave(P); pi = torch.arange(P, device=DEV).repeat(C)
    sid_c = torch.zeros(C, K, dtype=torch.long, device=DEV); W0c = torch.zeros(C, K, device=DEV)
    for c, al in enumerate(allocs):
        for k, (a, w) in enumerate(al.items()): sid_c[c, k] = assets.index(a); W0c[c, k] = w / 100
    sid = sid_c[ci]; W0 = W0c[ci]; has = W0 > 0; gap = round(gap_days / step)
    val = W0 * V0; infl = torch.ones(N, device=DEV); nav = torch.ones(N, device=DEV); peak = torch.ones(N, device=DEV); mdd = torch.zeros(N, device=DEV)
    last = torch.zeros(N, dtype=torch.long, device=DEV); checkpoints = {}; ages = {15: 45, 25: 55, 35: 65}
    for d in range(1, L):
        rows = IDX[pi, d]; g = 1 + Rg[rows[:, None], sid]; Vb = val.sum(1); val = val * g; infl = infl * Cg[rows]
        nav = nav * val.sum(1) / Vb.clamp(min=1e-9); peak = torch.maximum(peak, nav); mdd = torch.maximum(mdd, 1 - nav / peak)
        mo = d * 12 // S
        if mo != (d - 1) * 12 // S:                                      # monthly contribution, underweight funds first
            amt = CONTRIB / 12 * infl; V = val.sum(1); tgt = W0 * (V + amt)[:, None]; short = (tgt - val).clamp(min=0) * has; ss = short.sum(1)
            fill = torch.minimum(amt, ss); rest = amt - fill
            val = val + short * (fill / ss.clamp(min=1e-9))[:, None] + W0 * rest[:, None]
        V = val.sum(1); w = val / V.clamp(min=1e-9)[:, None]; since = d - last
        rel = torch.where(has, w / W0.clamp(min=1e-9), torch.zeros_like(w)).max(1).values
        trig = (((w - W0).abs().max(1).values * 100 > band) & (since > gap)) | (rel >= valve)
        if trig.any():
            tgt = W0 * V[:, None]; cost = COST * (tgt - val).abs().sum(1) * trig
            val = torch.where(trig[:, None], tgt * (1 - cost / V.clamp(min=1e-9))[:, None], val); last = torch.where(trig, torch.full_like(last, d), last)
        if (d + 1) % S == 0 and (d + 1) // S in ages: checkpoints[ages[(d + 1) // S]] = (val.sum(1) / infl).view(C, P).cpu().numpy()
    return dict(wealth=checkpoints, mdd=mdd.view(C, P).cpu().numpy())

def ce(w, gamma=GAMMA): return float(np.mean(np.maximum(w, 1e-3) ** (1 - gamma)) ** (1 / (1 - gamma)))

GOLD3 = {"GLDSIM": .03, "GDESIM": .027, "UGLSIM": .06}
def evaluate(allocs, IDX, cap):
    rb = simulate(allocs, IDX); rt = simulate(allocs, IDX, trend_haircut=0.02); rg = simulate(allocs, IDX, drag=GOLD3); out = []
    for c in range(len(allocs)):
        ces = [ce(r["wealth"][65][c]) for r in (rb, rt, rg)]; dd90 = float(np.percentile(rb["mdd"][c], 90) * 100)
        out.append((np.log(np.mean(ces)) - 0.05 * max(0.0, dd90 - cap), dict(ce=np.mean(ces), ce_base=ces[0], dd90=dd90, med=float(np.median(rb["wealth"][65][c])), p10=float(np.percentile(rb["wealth"][65][c], 10)))))
    return out

def mutate(a, rng):
    for _ in range(80):
        b = dict(a); x = rng.choice(list(b)); y = rng.choice(UNIVERSE); d = int(rng.choice([1, 2, 3, 5, 8]))
        if x == y or b[x] < d: continue
        b[x] -= d; b[y] = b.get(y, 0) + d
        if b[x] == 0: del b[x]
        if valid(b): return b
    return a

SEEDS = lambda P: [{t: int(w) for t, w in P[n]["alloc"].items()} for n in ("S13.5", "E14", "E15", "M25", "M30", "M35", "E20", "E22", "E24", "MP-2 engine", "Crisis-Hedged 12", "S12+", "Gold-Stack 12") if n in P] + \
                  [{"UPROSIM": 55, "TMFSIM": 45}, {"VTISIM": 100}, {"SSOSIM": 100}, {"UPROSIM": 40, "TMFSIM": 20, "KMLMSIM": 20, "GLDSIM": 20}, {"NTSXSIM": 50, "GDESIM": 30, "KMLMSIM": 20}]
if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "search":
        cap = float(sys.argv[2]); rng = np.random.default_rng(int(cap)); POP = int(os.environ.get("POP", "64")); ITERS = int(os.environ.get("ITERS", "50"))
        P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json"))); seeds = [s for s in SEEDS(P) if valid(s)]
        pop = [seeds[i % len(seeds)] for i in range(POP)]
        for i in range(len(seeds), POP):
            for _ in range(3 + i // len(seeds)): pop[i] = mutate(pop[i], rng)
        IDX = mp.make_idx(256, YEARS, step=5, seed=301); t0 = time.time(); fit = evaluate(pop, IDX, cap); seen = {}
        print(f"[accumulate cap {cap:.0f}%] {len(seeds)} valid seeds, {POP} climbers", flush=True)
        for it in range(1, ITERS + 1):
            kids = [mutate(p, rng) for p in pop]; kf = evaluate(kids, IDX, cap)
            for i in range(POP):
                if kf[i][0] > fit[i][0]: pop[i], fit[i] = kids[i], kf[i]
            for p, f in zip(pop, fit): seen[tuple(sorted(p.items()))] = f
            if it % 10 == 0:
                order = np.argsort([-f[0] for f in fit])
                for j in order[-POP // 4:]:
                    q = pop[order[rng.integers(POP // 4)]]
                    for _ in range(4): q = mutate(q, rng)
                    pop[j] = q
                fit = evaluate(pop, IDX, cap)
            b = max(range(POP), key=lambda i: fit[i][0]); m = fit[b][1]
            print(f"  iter {it:3d} ({time.time()-t0:4.0f}s) CE ${m['ce']*1000:,.0f} (base ${m['ce_base']*1000:,.0f}) median ${m['med']*1000:,.0f} p10 ${m['p10']*1000:,.0f} dd90 {m['dd90']:.0f}% | "
                  + " ".join(f"{t.replace('SIM','')}{w}" for t, w in sorted(pop[b].items(), key=lambda x: -x[1])), flush=True)
        top = sorted(seen.items(), key=lambda kv: -kv[1][0])[:20]
        json.dump([dict(alloc=dict(k), fitness=f[0], **f[1]) for k, f in top], open(os.path.join(ROOT, "..", "results", f"accumulate_cap{int(cap)}.json"), "w"), indent=1, default=float)

def testfol(alloc):
    import urllib.request
    body = {"start_date": "1987-12-31", "end_date": "2026-10-16", "start_val": 10000, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
            "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": alloc, "absolute_dev": 0, "relative_dev": 100}]}
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}), timeout=240))
        s = d["stats"][0]; return f"{s['cagr']:.2f}% / {s['max_drawdown']:.1f}% / {s['sharpe']:.3f} ({d['start_date'][:4]})"
    except Exception as e: return f"err {str(e)[:40]}"

if __name__ == "__main__" and sys.argv[1] == "validate":
    import datetime as dt
    P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json"))); cands = {}
    for c in (30, 40, 50, 60):
        f = os.path.join(ROOT, "..", "results", f"accumulate_cap{c}.json")
        if os.path.exists(f):
            for i, r in enumerate(json.load(open(f))[:3]): cands[f"IRA-{c} #{i+1}"] = {t: int(w) for t, w in r["alloc"].items()}
    for n in ("S13.5", "E24", "MP-2 engine", "Crisis-Hedged 12", "60/40", "VTI (100% US stocks)"):
        if n in P: cands[n] = {t: int(w) for t, w in P[n]["alloc"].items()}
    cands["HFEA (UPRO 55 / TMF 45)"] = {"UPROSIM": 55, "TMFSIM": 45}
    names = list(cands); allocs = [cands[n] for n in names]
    i00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
    levdrag = {t: (x - 1) * 0.01 for t, x in LEVX.items()}
    runs = {"base": (mp.make_idx(2000, YEARS, seed=402), {}), "trend -2%": (mp.make_idx(2000, YEARS, seed=403), dict(trend_haircut=0.02)),
            "trend -4%": (mp.make_idx(2000, YEARS, seed=404), dict(trend_haircut=0.04)), "gold -3%": (mp.make_idx(2000, YEARS, seed=405), dict(drag=GOLD3)),
            "gold -5%": (mp.make_idx(2000, YEARS, seed=406), dict(drag={"GLDSIM": .05, "GDESIM": .045, "UGLSIM": .10})),
            "leverage costs +1%/yr per x": (mp.make_idx(2000, YEARS, seed=407), dict(drag=levdrag)), "3-month blocks": (mp.make_idx(2000, YEARS, block=63, seed=408), {}),
            "recent era 2000-2026": (mp.make_idx(2000, YEARS, seed=409, era=(i00, mp.T)), {})}
    res = {n: {} for n in names}
    for lab, (IDX, kw) in runs.items():
        for i in range(0, len(allocs), 8):
            r = simulate(allocs[i:i + 8], IDX, step=1, **kw)
            for c, n in enumerate(names[i:i + 8]):
                w65 = r["wealth"][65][c]; w55 = r["wealth"][55][c]; dd = r["mdd"][c] * 100
                res[n][lab] = dict(ce=ce(w65), med=float(np.median(w65)), p10=float(np.percentile(w65, 10)), p25=float(np.percentile(w65, 25)), med55=float(np.median(w55)),
                                   p_nest=float((w65 >= 1750).mean()), p_nest55=float((w55 >= 1750).mean()), dd50=float(np.median(dd)), dd90=float(np.percentile(dd, 90)), p_dd50=float((dd > 50).mean()))
        print(f"  {lab} done", flush=True)
    for n in names:
        v = res[n]; v["robust_ce"] = float(np.mean([v[k]["ce"] for k in runs])); v["worst_ce"] = float(min(v[k]["ce"] for k in runs)); v["alloc"] = cands[n]
        day = sum(w / 100 * RD.get(t, mp.fund_returns(t)) for t, w in cands[n].items()); v["worst_day"] = float(day[1:].min() * 100); v["testfol"] = testfol(cands[n])
    json.dump(res, open(os.path.join(ROOT, "..", "results", "accumulate_validate.json"), "w"), indent=1, default=float)
    M = lambda x: f"${x/1000:.2f}M"
    print("| Portfolio | Engine | Robust CE @65 | Worst-case CE | Median @65 | Bad (p10) @65 | Median @55 | Reach $1.75M by 55 / 65 | Drop lived: median / p90 | Chance of a >50% drop | Worst day | CE: trend -2/-4, gold -3/-5, lev cost, 3-mo, recent era | testfol CAGR / MDD / Sharpe |")
    print("|" + "---|" * 13)
    for n in sorted(names, key=lambda n: -res[n]["robust_ce"]):
        v = res[n]; b = v["base"]; eng = " · ".join(f"{t.replace('SIM','')} {w}" for t, w in sorted(v["alloc"].items(), key=lambda x: -x[1]))
        print(f"| {n} | {eng} | **{M(v['robust_ce'])}** | {M(v['worst_ce'])} | {M(b['med'])} | {M(b['p10'])} | {M(b['med55'])} | {b['p_nest55']*100:.0f}% / {b['p_nest']*100:.0f}% | {b['dd50']:.0f}% / {b['dd90']:.0f}% | {b['p_dd50']*100:.0f}% | {v['worst_day']:.1f}% | "
              + " / ".join(M(v[k]["ce"]) for k in runs if k != "base") + f" | {v['testfol']} |")
