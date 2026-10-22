"""Does optimizing MP-2.1's weights for RECENT Sharpe make it better?

1. Walk-forward test of the method: at each cut date T, pick weights that maximize Sharpe over the previous 10 (or 5) years
   ("recent"), and weights that maximize Sharpe over all data before T ("all history"); compare the NEXT 10 years.
2. Today's recent-Sharpe pick (last 10 / 5 years) run through the printer harness against MP-2.1 on fresh histories in the
   5 stress cases (the retiree's taxes, same printer settings).
Same six funds and guard rails as the engine search: 0-35% each, DBMF + KMLM <= 42%, AI/mega-tech exposure <= 25%. Portfolio
returns are a constant mix (daily rebalanced) for the Sharpe fits. Pre-inception fund histories are reconstructed.
Usage: THROTTLE=1 python3 printer/recent_sharpe.py   (writes results/recent_sharpe.log / .json)"""
import os, sys, json, datetime as dt, numpy as np
from scipy.optimize import minimize
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.argv = [sys.argv[0]]
import money_printer as mp, improve as im
from dataclasses import replace
sys.path.insert(0, os.path.join(ROOT, "..", "lab")); import stress_forward as sf, search as sr
F = ["DBMFSIM", "VBRSIM", "GDESIM", "KMLMSIM", "IAUMSIM", "TQQQSIM"]; MP21 = np.array([27, 27, 21, 15, 8, 2]) / 100
R = np.stack([mp.fund_returns(f) for f in F], 1); RF = mp.RF; CAL = np.asarray(mp.h.CAL); AIW = np.array([sr.AI.get(f, 0) for f in F])
day = lambda y, m=10, d=16: int(np.searchsorted(CAL, int(dt.datetime(y, m, d, tzinfo=dt.UTC).timestamp())))

def stats(w, a, b):
    r = R[a:b] @ w; ex = r - RF[a:b]; v = np.cumprod(1 + r); dd = v / np.maximum.accumulate(v) - 1
    return dict(sharpe=float(ex.mean() / ex.std() * np.sqrt(252)), cagr=float(v[-1] ** (252 / (b - a)) - 1), mdd=float(dd.min()), ulcer=float(np.sqrt((dd ** 2).mean()) * 100))

def opt(a, b, seed=0):
    rng = np.random.default_rng(seed); best = None
    neg = lambda w: -stats(w, a, b)["sharpe"]
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}, {"type": "ineq", "fun": lambda w: 0.42 - w[0] - w[3]}, {"type": "ineq", "fun": lambda w: 0.25 - AIW @ w}]
    for _ in range(12):
        x0 = rng.dirichlet(np.ones(len(F))); x0 = np.clip(x0, 0, .35); x0 /= x0.sum()
        r = minimize(neg, x0, method="SLSQP", bounds=[(0, .35)] * len(F), constraints=cons, options=dict(maxiter=300, ftol=1e-9))
        if r.success and (best is None or r.fun < best.fun): best = r
    w = np.round(np.clip(best.x, 0, .35) * 100).astype(int); w[np.argmax(w)] += 100 - w.sum(); return w / 100

def fwd_ok(w):                                                     # forward-scenario guard rail (>= -8.5% in every bad scenario)
    return min(sum(x * sf.move("GLDSIM" if f == "IAUMSIM" else f, sf.SC[k]) for f, x in zip(F, w)) for k in sr.BAD) >= -8.5

fmt = lambda w: " ".join(f"{f[:-3]} {round(x * 100)}" for f, x in sorted(zip(F, w), key=lambda t: -t[1]) if x > 0)
if __name__ == "__main__":
    out = dict(walk=[]); log = open(os.path.join(ROOT, "..", "results", "recent_sharpe.log"), "w")
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    say("1. WALK-FORWARD: pick weights at T, judge the next 10 years (Sharpe / CAGR / max drawdown)")
    say(f"{'T':6} | {'recent 10y pick':38} in-sample -> next 10y | {'recent 5y pick':38} in-sample -> next 10y | {'all-history pick':38} -> next 10y | MP-2.1 weights next 10y")
    for T in (1992, 1997, 2002, 2007, 2012, 2016):
        t, t10, t5, nxt = day(T), day(T - 10), day(T - 5), min(day(T + 10), len(CAL))
        picks = {"recent10": opt(t10, t), "recent5": opt(t5, t), "all": opt(1, t)}
        row = dict(T=T, picks={k: dict(w=w.tolist(), ins=stats(w, {"recent10": t10, "recent5": t5, "all": 1}[k], t), oos=stats(w, t, nxt)) for k, w in picks.items()}, mp21=stats(MP21, t, nxt))
        out["walk"].append(row); p = row["picks"]; s = lambda d: f"{d['sharpe']:.2f} / {d['cagr'] * 100:4.1f}% / {d['mdd'] * 100:5.1f}%"
        say(f"{T:6} | {fmt(picks['recent10']):38} {p['recent10']['ins']['sharpe']:.2f} -> {s(p['recent10']['oos'])} | {fmt(picks['recent5']):38} {p['recent5']['ins']['sharpe']:.2f} -> {s(p['recent5']['oos'])} | "
            f"{fmt(picks['all']):38} -> {s(p['all']['oos'])} | {s(row['mp21'])}")
    for k in ("recent10", "recent5", "all"):
        o = [r["picks"][k]["oos"]["sharpe"] for r in out["walk"]]; i = [r["picks"][k]["ins"]["sharpe"] for r in out["walk"]]
        say(f"  {k:9} pick: average in-sample Sharpe {np.mean(i):.2f} -> next-10-year Sharpe {np.mean(o):.2f}")
    say(f"  MP-2.1 weights (chosen with hindsight): average next-10-year Sharpe {np.mean([r['mp21']['sharpe'] for r in out['walk']]):.2f}")

    say("\n2. TODAY'S RECENT-SHARPE PICKS vs MP-2.1 (portfolio stats, then the printer on fresh histories)")
    now = len(CAL); picks = {"recent 10y (2016-2026)": opt(day(2016), now), "recent 5y (2021-2026)": opt(day(2021), now)}
    for n, w in list(picks.items()) + [("MP-2.1", MP21)]:
        a, b, c = stats(w, day(2016), now), stats(w, day(2000, 1, 3), now), stats(w, 1, now)
        say(f"  {n:24} {fmt(w):40} | Sharpe 2016-26 {a['sharpe']:.2f} | 2000-26 {b['sharpe']:.2f} | 1972-26 {c['sharpe']:.2f} (CAGR {c['cagr']*100:.1f}%, max DD {c['mdd']*100:.1f}%) | forward scenarios ok: {fwd_ok(w)}")
    best = im.load_best(); ref = im.P(**best["simple"])
    pr = [ref] + [replace(ref, name=f"MP-2.1 settings | weights from {n}", alloc={f: int(round(x * 100)) for f, x in zip(F, w) if x > 0}) for n, w in picks.items()]
    C = im.cases(1301, 2000); Rr = im.evaluate(pr, C); K = list(C); out["printer"] = Rr; mo = lambda x: f"${x * 5e4 / 12:,.0f}"
    say(f"\n  Printer, the retiree's taxes, $50k, 2,000 fresh histories x 5 cases:")
    for p in pr:
        v = Rr[p.name]; b = v["base"]
        say(f"  {p.name[-48:]:48} | robust CE {mo(v['robust_ce'])} ({(v['robust_ce'] / Rr[ref.name]['robust_ce'] - 1) * 100:+.1f}%) | first 10 yrs {mo(b['print_y1_10_typ'])} | 40-yr {mo(b['print_typical'])} / bad {mo(b['print_bad'])} | "
            f"lose {b['lose_value']*100:.0f}% dip {b['deep_dip']*100:.0f}% dry {b['run_dry']*100:.1f}% | trend -4% CE {mo(v['trend -4%/yr']['ce'])} | recent-era CE {mo(v['recent era']['ce'])} | break risk no worse: {im.safe(v, Rr[ref.name], K)}")
    json.dump(out, open(os.path.join(ROOT, "..", "results", "recent_sharpe.json"), "w"), indent=1, default=float)
