"""Improvement harness: test PASSIVE changes (cost, tax, fund choice, settings, credit; no market signals) to the current best
money printers for the retiree case (the retiree's taxes, taxable account). Queue and verdicts: results/IMPROVE.md.

Two tracks, kept in results/improve_best.json:
  simple  the printer the retiree can run at M1 with no credit
  credit  the best printer with a box-spread loan (IBKR/Schwab)
Each IDEA maps a track's current best to candidate variants. SEARCH: all candidates + the reference on the same 1,000 histories in
5 cases (base, trend -2%/yr, trend -4%/yr, 2000-2026 era only, 3-month blocks). The 3 best candidates that keep break risk no worse than
the reference are re-run with it on 2,000 FRESH histories. ACCEPTED if, on the fresh histories: break risk is no worse in every case
(ends below start <= +1 pt, dips < 70% <= +2 pts, runs dry <= +0.2 pt, base never cut >= -2 pts, margin calls <= max(1%, reference)),
robust CE (risk aversion 3, mean of the 5 cases) is >= 0.5% higher (any gain for FREE ideas: same holdings, lower cost/tax), and the first-decade bad-history print is not lower.
Usage: IDEA=<name> THROTTLE=1 python3 printer/improve.py [--accept]   (writes results/improve/<name>.json and .log)"""
import os, sys, json, time, subprocess, datetime as dt, numpy as np
from dataclasses import asdict, replace
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); ACCEPT = "--accept" in sys.argv; sys.argv = [sys.argv[0]]
import money_printer as mp, search as se
P = mp.Printer; OUT = os.path.join(ROOT, "..", "results"); BEST_F = os.path.join(OUT, "improve_best.json")
PATHS = int(os.environ.get("PATHS", "1000")); FRESH = int(os.environ.get("FRESH", "2000")); THROTTLE = max(0.75, float(os.environ.get("THROTTLE", "1")))
S2 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65)
START = {"simple": asdict(P("MP-2", mp.load_alloc("MP-2 engine"), **S2)),
         "credit": asdict(P("MP-2 + $10k box loan (1.2x), base 5.25%", mp.load_alloc("MP-2 engine"), lev=1.2, rate_spread=0.6, interest_tax="capital", **{**S2, "base": 5.25}))}
def load_best(): return json.load(open(BEST_F)) if os.path.exists(BEST_F) else START

def cool(limit=80, resume=74):                                     # laptop heat guard (it shut down twice)
    try:
        t = int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.split()[0])
        while t >= limit:
            print(f"  GPU {t}C, cooling...", flush=True); time.sleep(60)
            t = int(subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True).stdout.split()[0])
            if t < resume: break
    except Exception: pass

I00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
def cases(seed, n):
    return {"base": (mp.make_idx(n, 40, seed=seed), {}), "trend -2%/yr": (mp.make_idx(n, 40, seed=seed + 1), dict(trend_haircut=0.02)),
            "trend -4%/yr": (mp.make_idx(n, 40, seed=seed + 2), dict(trend_haircut=0.04)), "recent era": (mp.make_idx(n, 40, seed=seed + 3, era=(I00, mp.T)), {}),
            "3-month blocks": (mp.make_idx(n, 40, block=63, seed=seed + 4), {})}
def evaluate(pr, C):
    res = {p.name: {} for p in pr}
    for lab, (IDX, kw) in C.items():
        for i in range(0, len(pr), 8):
            cool(); tb = time.time(); r = mp.simulate(pr[i:i + 8], IDX, **kw)
            for c, p in enumerate(pr[i:i + 8]): s = mp.score(r, c); s["ce"] = float(se.ce(r["spend"][c], gamma=3.0)); res[p.name][lab] = s
            time.sleep(THROTTLE * (time.time() - tb))
        print(f"    {lab} done", flush=True)
    for v in res.values(): v["robust_ce"] = float(np.mean([v[k]["ce"] for k in C])); v["worst_margin_call"] = max(v[k].get("margin_call", 0) for k in C)
    return res
def safe(v, ref, C):
    return all(v[k]["lose_value"] <= ref[k]["lose_value"] + .01 and v[k]["deep_dip"] <= ref[k]["deep_dip"] + .02 and v[k]["run_dry"] <= ref[k]["run_dry"] + .002
               and v[k]["base_never_cut"] >= ref[k]["base_never_cut"] - .02 for k in C) and v["worst_margin_call"] <= max(.01, ref["worst_margin_call"])
def better(v, ref, gain=0.005): return v["robust_ce"] > ref["robust_ce"] * (1 + gain) and v["base"]["print_y1_10_bad"] >= ref["base"]["print_y1_10_bad"] - 1e-6

# ------------------------------------------------------------------ ideas: track best -> candidate variants (names must be unique)
def swap(p, old, new, label):
    a = dict(p.alloc)
    if old not in a: return []
    a[new] = a.get(new, 0) + a.pop(old); return [replace(p, name=f"{p.name} | {label}", alloc=a)]
FREE = {"cheap_gold", "bucket_tax"}                                # same holdings, lower cost or tax: any gain counts (no 0.5% bar)
IDEAS = {
    "cheap_gold": lambda p: swap(p, "GLDSIM", "GLDMSIM", "GLD -> GLDM") + swap(p, "GLDSIM", "IAUMSIM", "GLD -> IAUM"),
    "bucket_tax": lambda p: [replace(p, name=f"{p.name} | bucket in Treasury fund", bucket_tax="treasury"), replace(p, name=f"{p.name} | bucket in BOXX", bucket_tax="boxx")],
}

def run(idea):
    best = load_best(); logp = os.path.join(OUT, "improve", f"{idea}.log"); os.makedirs(os.path.dirname(logp), exist_ok=True); log = open(logp, "w")
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    say(f"IDEA {idea} — {dt.datetime.now():%Y-%m-%d %H:%M}"); out = {}; new_best = dict(best)
    for track, spec in best.items():
        ref = P(**spec); cand = IDEAS[idea](ref)
        if not cand: say(f"  [{track}] no candidates"); continue
        say(f"  [{track}] reference: {ref.name}; {len(cand)} candidates; search {PATHS} histories x 5 cases")
        R = evaluate([ref] + cand, cases(601, PATHS)); C = list(cases(0, 1)); gain = 0.0 if idea in FREE else 0.005
        ok = sorted([p for p in cand if safe(R[p.name], R[ref.name], C)], key=lambda p: -R[p.name]["robust_ce"])[:3]
        V = evaluate([ref] + ok, cases(701, FRESH)) if ok else {}
        gain = 0.0 if idea in FREE else 0.005
        verdict = [p for p in ok if safe(V[p.name], V[ref.name], C) and better(V[p.name], V[ref.name], gain)]
        win = max(verdict, key=lambda p: V[p.name]["robust_ce"]) if verdict else None
        out[track] = dict(search=R, validate=V, winner=win.name if win else None)
        mo = lambda x, z: f"${x * z / 12:,.0f}"
        for title, T in (("search", R), ("fresh", V)):
            if not T: continue
            say(f"  [{track}] {title}: {'printer':70} | robust CE $50k / $100k | first 10 yrs typ/bad ($50k) | 40-yr typ/bad ($50k) | never cut  lose  dip  dry | trend -4% CE | safe better")
            for n, v in sorted(T.items(), key=lambda kv: -kv[1]["robust_ce"]):
                b = v["base"]; r0 = T[ref.name]
                say(f"  {'':10} {n[:70]:70} | {mo(v['robust_ce'], 5e4):>6} / {mo(v['robust_ce'], 1e5):>6} ({(v['robust_ce'] / r0['robust_ce'] - 1) * 100:+.1f}%) | "
                    f"{mo(b['print_y1_10_typ'], 5e4)} / {mo(b['print_y1_10_bad'], 5e4)} | {mo(b['print_typical'], 5e4)} / {mo(b['print_bad'], 5e4)} | "
                    f"{b['base_never_cut'] * 100:3.0f}%  {b['lose_value'] * 100:3.0f}%  {b['deep_dip'] * 100:3.0f}%  {b['run_dry'] * 100:3.1f}% | {mo(v['trend -4%/yr']['ce'], 5e4)} | "
                    f"{'yes' if safe(v, r0, C) else 'no ':3}  {'yes' if better(v, r0, gain) else 'no'}")
        say(f"  [{track}] VERDICT: " + (f"ACCEPT {win.name} (robust CE {(V[win.name]['robust_ce'] / V[ref.name]['robust_ce'] - 1) * 100:+.1f}% on fresh histories)" if win else "keep the reference"))
        if win: new_best[track] = asdict(win)
    json.dump(out, open(os.path.join(OUT, "improve", f"{idea}.json"), "w"), indent=1, default=str)
    if ACCEPT and new_best != best: json.dump(new_best, open(BEST_F, "w"), indent=1); say("  improve_best.json updated")
    return out

if __name__ == "__main__":
    idea = os.environ.get("IDEA")
    if idea not in IDEAS: print("IDEA must be one of:", ", ".join(IDEAS)); sys.exit(1)
    run(idea)
