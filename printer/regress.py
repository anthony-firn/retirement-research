"""Regression check for printer/money_printer.py: new options must default to the old behaviour.
Runs a fixed set of printers (plain, credit, tilt-free) on 200 fixed histories and compares every score exactly with
results/regress_baseline.json.  Usage: python3 printer/regress.py check | save"""
import os, sys, json
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); mode = sys.argv[1] if len(sys.argv) > 1 else "check"; sys.argv = [sys.argv[0]]
import money_printer as mp
BASE = os.path.join(ROOT, "..", "results", "regress_baseline.json")
AL = mp.load_alloc("MP-2 engine"); S2 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65); P = mp.Printer
PR = [P("MP-2", AL, **S2), P("CH-12", mp.load_alloc("Crisis-Hedged 12 (no UUP)")), P("MP-2 middle", AL, tax="middle bracket", **S2),
      P("MP-2 box 1.2x base 5.25", AL, lev=1.2, rate_spread=0.6, interest_tax="capital", **{**S2, "base": 5.25}),
      P("MP-2 in-fund 1.2x", AL, lev=1.2, lev_daily=True, rate_spread=0.5, **S2), P("MP-2 run 25% M1", AL, credit=0.25, rate_spread=2.0, **S2),
      P("MP-2 margin middle", AL, lev=1.33, rate_spread=1.5, interest_tax="investment", tax="middle bracket", **S2)]
def run():
    r = mp.simulate(PR, mp.make_idx(200, 40, seed=5)); return {p.name: mp.score(r, c) for c, p in enumerate(PR)}
if __name__ == "__main__":
    out = run()
    if mode == "save": json.dump(out, open(BASE, "w"), indent=0); print(f"saved {BASE}")
    else:
        ref = json.load(open(BASE)); bad = [(n, k, ref[n][k], out[n].get(k)) for n in ref for k in ref[n] if ref[n][k] != out[n].get(k)]
        extra = [(n, k) for n in out for k in out[n] if k not in ref.get(n, {})]
        print("regression: identical" if not bad and not extra else f"regression: DIFFERENT {bad[:5]} {extra[:5]}"); sys.exit(1 if bad or extra else 0)
