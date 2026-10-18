"""Money Printer search: find the best printers (engine weights + print settings together) by printer stats.

Score = certainty-equivalent spending (CE): the steady after-tax real income the retiree would value as much as the printer's
uneven income stream (CRRA utility, risk aversion GAMMA; each year weighted by the chance a woman aged 60 is still alive,
Gompertz fit to US life tables: ~91% at 70, ~71% at 80, ~38% at 90). Lean years hurt far more than fat years help, so CE
rewards print AND reliability. Fitness = average CE over the base case and a stress case (trend funds earn 2%/yr less),
minus penalties for break risk: runs dry > 1% (base) or > 3% (stress), ends below its starting real value > LOSE_MAX,
base print cut in > 15% of histories.
Engine guard rails: <= 9 funds, <= 35% each, KMLM+DBMF <= 42%, leveraged funds <= 25%, AI/mega-tech exposure <= 25%,
every bad forward scenario (AI bust, oil stagflation, bond revolt, deflation, dollar crisis) >= -8.5%.
Search: lockstep GPU hill-climbers with periodic restarts from the best, common 256 weekly-step histories (CRN).
Usage: python3 printer/search.py balanced|max_print|fortress   -> results/printer_search_<mode>.json/.log"""
import os, sys, json, time, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "..", "lab"))
import money_printer as mp
import stress_forward as sf
from dataclasses import replace
MODES = ("balanced", "max_print", "fortress", "retiree")
MODE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in MODES else "balanced"
CFG = {"balanced": dict(gamma=3.0, lose_max=0.15), "max_print": dict(gamma=1.5, lose_max=0.20), "fortress": dict(gamma=6.0, lose_max=0.05),
       # the retiree's: worst case over base / trend bear / gold bear, at least CH-12's ages 60-70 print, no K-1 funds, dry <= 0.5%
       "retiree": dict(gamma=3.0, lose_max=0.10, worst=True, early_floor=0.055, dry_max=0.005, exclude={"UGLSIM", "UUPSIM"})}[MODE]
GAMMA, LOSE_MAX = CFG["gamma"], CFG["lose_max"]
UNIVERSE0 = ["DBMFSIM", "KMLMSIM", "GLDSIM", "VBRSIM", "XLVSIM", "TYDSIM", "TQQQSIM", "UUPSIM", "IEISIM", "IEFSIM", "ZROZSIM", "TLTSIM", "SHYSIM",
            "SPMOSIM", "GDESIM", "TMFSIM", "UGLSIM", "XLESIM", "XLPSIM", "XLUSIM", "VTISIM", "QLDSIM", "VTVSIM", "REITSIM", "NTSXSIM", "RSSBSIM", "BNDSIM"]
UNIVERSE = [u for u in UNIVERSE0 if u not in CFG.get("exclude", set())]
LEV = {"TQQQSIM", "TYDSIM", "TMFSIM", "UGLSIM", "QLDSIM", "UBTSIM"}; AI = {"TQQQSIM": 3, "QLDSIM": 2, "SPMOSIM": 0.6, "VTISIM": 0.35, "GDESIM": 0.36, "NTSXSIM": 0.36, "RSSBSIM": 0.3}
BAD = [k for k in sf.SC if not k.startswith("Soft")]
POP = int(os.environ.get("POP", "64")); PATHS = int(os.environ.get("PATHS", "256")); ITERS = int(os.environ.get("ITERS", "60")); STEP = 5
SURV = np.exp(-0.0594 * (np.exp(0.095 * np.arange(40)) - 1))

def valid(a):
    if any(t not in UNIVERSE for t in a): return False
    if len(a) > 9 or any(w > 35 or w < 1 for w in a.values()) or sum(a.values()) != 100: return False
    if a.get("KMLMSIM", 0) + a.get("DBMFSIM", 0) > 42 or sum(w for t, w in a.items() if t in LEV) > 25: return False
    if sum(AI.get(t, 0) * w for t, w in a.items()) > 25: return False
    return min(sum(w / 100 * sf.move(t, sf.SC[k]) for t, w in a.items()) for k in BAD) >= -8.5

def ce(spend, gamma=GAMMA, floor=0.005):
    P, M = spend.shape; Y = M // 12; yrs = spend[:, :Y * 12].reshape(P, Y, 12).sum(2); s = SURV[:Y]
    u = np.maximum(yrs, floor) ** (1 - gamma) / (1 - gamma); EU = (u * s).sum(1).mean()
    return ((1 - gamma) * EU / s.sum()) ** (1 / (1 - gamma))

def fitness(rb, rs, c, rg=None):
    cb, cs = ce(rb["spend"][c]), ce(rs["spend"][c]); dry_b, dry_s = rb["dead"][c].mean(), rs["dead"][c].mean()
    lose = (rb["real_end"][c] < 1).mean(); cut = rb["cut"][c].mean(); dmax = CFG.get("dry_max", 0.01)
    pen = 2 * max(0, dry_b - dmax) + 1 * max(0, dry_s - 0.03) + 0.2 * max(0, lose - LOSE_MAX) + 0.1 * max(0, cut - 0.15)
    sp = rb["spend"][c]; Y = sp.shape[1] // 12; early = np.median(sp[:, :120].reshape(sp.shape[0], 10, 12).sum(2).mean(1))
    if "early_floor" in CFG: pen += 1.0 * max(0, CFG["early_floor"] - early)
    if CFG.get("worst") and rg is not None:
        cg = ce(rg["spend"][c]); return min(cb, cs, cg) - pen, dict(ce_base=cb, ce_stress=cs, ce_gold=cg, dry=dry_b, dry_stress=dry_s, lose=lose, cut=cut, early=early)
    return 0.5 * (cb + cs) - pen, dict(ce_base=cb, ce_stress=cs, dry=dry_b, dry_stress=dry_s, lose=lose, cut=cut, early=early)

def mutate(p, rng):
    for _ in range(50):
        q = replace(p, alloc=dict(p.alloc))
        if rng.random() < 0.7:
            a = rng.choice(list(q.alloc)); b = rng.choice(UNIVERSE); d = int(rng.choice([1, 2, 3, 5]))
            if a == b or q.alloc[a] < d: continue
            q.alloc[a] -= d; q.alloc[b] = q.alloc.get(b, 0) + d
            if q.alloc[a] == 0: del q.alloc[a]
        else:
            k = rng.integers(5)
            if k == 0: q.base = float(np.clip(q.base + rng.choice([-0.25, 0.25]), 3.0, 6.5))
            elif k == 1: q.skim = float(np.clip(q.skim + rng.choice([-0.05, 0.05]), 0.05, 0.75))
            elif k == 2: q.bucket_months = int(np.clip(q.bucket_months + rng.choice([-12, 12]), 12, 60))
            elif k == 3: q.cut_below = float(np.clip(q.cut_below + rng.choice([-0.05, 0.05]), 0.5, 0.9))
            else: q.cut_to = float(np.clip(q.cut_to + rng.choice([-0.05, 0.05]), 0.6, 1.0))
        if valid(q.alloc): return q
    return p

GOLD3 = {"GLDSIM": .03, "GDESIM": .027, "UGLSIM": .06}
def evaluate(pop, IDX):
    rb = mp.simulate(pop, IDX, step=STEP); rs = mp.simulate(pop, IDX, trend_haircut=0.02, step=STEP)
    rg = mp.simulate(pop, IDX, step=STEP, drag=GOLD3) if CFG.get("worst") else None
    return [fitness(rb, rs, c, rg) for c in range(len(pop))]

def key(p): return (tuple(sorted(p.alloc.items())), p.base, p.skim, p.bucket_months, p.cut_below, p.cut_to)

if __name__ == "__main__":
    t0 = time.time(); rng = np.random.default_rng({"balanced": 1, "max_print": 2, "fortress": 3, "retiree": 4}[MODE])
    P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
    seeds = [n for n in ("Crisis-Hedged 12 (no UUP)", "Crisis-Hedged 12", "Crisis-Hedged 11.5", "Gold-Stack 12", "S12+ split", "Plan-b40-split", "S12+", "S13 split", "H12-8",
                         "S13.5", "E14", "S12.5-split", "E11", "Simple-6.8") if n in P and all(t in UNIVERSE for t in P[n]["alloc"]) and valid({t: int(w) for t, w in P[n]["alloc"].items()})]
    extra = []                                                          # seed with earlier search finalists that are valid here
    for m in ("fortress", "balanced", "max_print"):
        f = os.path.join(ROOT, "..", "results", f"printer_search_{m}.json")
        if os.path.exists(f):
            for r in json.load(open(f))[:10]:
                a = {t: int(w) for t, w in r["printer"]["alloc"].items()}
                if valid(a): q = r["printer"]; extra.append(mp.Printer(f"{m} finalist", a, base=q["base"], skim=q["skim"], bucket_months=int(q["bucket_months"]), cut_below=q["cut_below"], cut_to=q["cut_to"]))
    pop = extra[:POP // 4]
    for i in range(POP - len(pop)):
        n = seeds[i % len(seeds)]; base = [4.0, 3.5, 4.5, 5.0][(i // len(seeds)) % 4]
        p = mp.Printer(n, {t: int(w) for t, w in P[n]["alloc"].items()}, base=base)
        for _ in range(i // len(seeds) * 3): p = mutate(p, rng)
        pop.append(p)
    IDX = mp.make_idx(PATHS, 40, step=STEP, seed=101)
    print(f"[{MODE}] gamma {GAMMA}, lose-value cap {LOSE_MAX:.0%}, {POP} climbers x {PATHS} histories, seeds: {seeds} + {len(extra[:POP // 4])} earlier finalists, universe {len(UNIVERSE)} funds", flush=True)
    fit = evaluate(pop, IDX); best_seen = {}
    for it in range(1, ITERS + 1):
        kids = [mutate(p, rng) for p in pop]; kf = evaluate(kids, IDX)
        for i in range(POP):
            if kf[i][0] > fit[i][0]: pop[i], fit[i] = kids[i], kf[i]
        for p, f in zip(pop, fit): best_seen[key(p)] = (f, p)
        if it % 10 == 0:                                                 # restart the weakest quarter from perturbed copies of the best
            order = np.argsort([-f[0] for f in fit])
            for j in order[-POP // 4:]:
                src = pop[order[rng.integers(POP // 4)]]; q = src
                for _ in range(4): q = mutate(q, rng)
                pop[j] = q
            fit = evaluate(pop, IDX)
        b = max(range(POP), key=lambda i: fit[i][0]); f = fit[b]
        print(f"  iter {it:3d} ({time.time()-t0:5.0f}s) best fitness {f[0]*100:.3f} | CE base {f[1]['ce_base']*100:.2f}% stress {f[1]['ce_stress']*100:.2f}% gold {f[1].get('ce_gold', float('nan'))*100:.2f}% early {f[1]['early']*100:.2f}% dry {f[1]['dry']*100:.1f}% lose {f[1]['lose']*100:.0f}% cut {f[1]['cut']*100:.0f}% | base {pop[b].base} skim {pop[b].skim:.2f} bucket {pop[b].bucket_months} cut {pop[b].cut_below:.2f}->{pop[b].cut_to:.2f} | "
              + " ".join(f"{t.replace('SIM','')}{w}" for t, w in sorted(pop[b].alloc.items(), key=lambda x: -x[1])), flush=True)
    top = sorted(best_seen.values(), key=lambda x: -x[0][0])[:30]
    json.dump([dict(fitness=f[0], **f[1], printer=dict(alloc=p.alloc, base=p.base, skim=p.skim, bucket_months=p.bucket_months, cut_below=p.cut_below, cut_to=p.cut_to)) for f, p in top],
              open(os.path.join(ROOT, "..", "results", f"printer_search_{MODE}.json"), "w"), indent=1, default=float)
    print("done", flush=True)
