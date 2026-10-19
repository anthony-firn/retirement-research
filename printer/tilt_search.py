"""Indicator tilts for the MP-2 printer, with a strict out-of-sample test.
Tilt family (checked monthly; while a signal is on, move X points of the portfolio):
  trend_off / vol_high / curve_inv : stocks (VBR 55%, GDE 35%, TQQQ 10% of X) -> defensive
  infl_high                        : VBR -> GLD
  gold_off                         : GLD and GDE (half each) -> defensive
  X in {0, 5, 10, 15} per signal; defensive = short Treasuries (SHY) or the trend funds (DBMF 60% / KMLM 40%): 2,048 variants.
Step 1 (in-sample): rank all variants on histories drawn only from 1972-1999 (512 paths, weekly steps).
Step 2 (out-of-sample): the 10 best in-sample variants vs plain MP-2 on 2000-2026 data they never saw (2,000 era-bootstrap
histories and the actual 2000-2026 path, daily), plus the full-period bootstrap. The retiree's taxes; trading costs and taxes of tilt trades
are included."""
import os, sys, json, itertools, datetime as dt, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.argv = [sys.argv[0]]
import money_printer as mp, search as se, signals
SG = signals.load(); SN = signals.NAMES
P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json"))); S2 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65)
ALLOC = dict(P["MP-2 engine"]["alloc"]); ALLOC["SHYSIM"] = 0
EQ = {"VBRSIM": .55, "GDESIM": .35, "TQQQSIM": .10}; DEF = {"SHY": {"SHYSIM": 1.0}, "trend": {"DBMFSIM": .6, "KMLMSIM": .4}}
def dirs(sizes, dname):
    D = DEF[dname]; out = []
    for sname, x in zip(SN, sizes):
        d = {}
        if x:
            if sname in ("trend_off", "vol_high", "curve_inv"): src_ = EQ
            elif sname == "infl_high": src_, D_ = {"VBRSIM": 1.0}, {"GLDSIM": 1.0}
            else: src_ = {"GLDSIM": .5, "GDESIM": .5}
            for a, f in src_.items(): d[a] = d.get(a, 0) - x * f
            for a, f in (D_ if sname == "infl_high" else D).items(): d[a] = d.get(a, 0) + x * f
        out.append(d)
    return out
def label(sizes, dname):
    on = [f"{n} {int(x*100)}" for n, x in zip(SN, sizes) if x]
    return ("; ".join(on) + f" -> {dname}") if on else "no tilt (plain MP-2)"
def idx_of(date): return int(np.searchsorted(mp.h.CAL, int(dt.datetime.fromisoformat(date).replace(tzinfo=dt.UTC).timestamp())))
I00, I72 = idx_of("2000-01-03"), idx_of("1972-06-01")

def run(cands, IDX, step=1, chunk=64):
    out = []
    for i in range(0, len(cands), chunk):
        cc = cands[i:i + chunk]; pr = [mp.Printer(label(*c), ALLOC, **S2) for c in cc]
        r = mp.simulate(pr, IDX, step=step, tilt=dict(sig=SG, dirs=[dirs(*c) for c in cc]))
        for k in range(len(cc)): s = mp.score(r, k); s["ce"] = float(se.ce(r["spend"][k], gamma=3.0)); out.append(s)
        print(f"    {min(i + chunk, len(cands))}/{len(cands)}", flush=True)
    return out
if __name__ == "__main__":
    combos = [(sz, dn) for dn in ("SHY", "trend") for sz in itertools.product([0, .05, .10, .15], repeat=5)]
    combos = [c for c in combos if any(c[0]) or c[1] == "SHY"]                         # one plain MP-2
    print(f"Step 1: {len(combos)} variants on 1972-1999-only histories (in-sample)", flush=True)
    IS = run(combos, mp.make_idx(512, 40, step=5, seed=601, era=(I72, I00)), step=5)
    base_i = combos.index(((0, 0, 0, 0, 0), "SHY")); b = IS[base_i]
    order = np.argsort([-x["ce"] for x in IS]); top = [combos[i] for i in order[:10]]
    print(f"\n  plain MP-2 in-sample CE ${b['ce']*100000/12:,.0f}/mo per $100k; best variants:")
    for i in order[:10]: print(f"   ${IS[i]['ce']*100000/12:,.0f}  never cut {IS[i]['base_never_cut']*100:.0f}% dip<70 {IS[i]['deep_dip']*100:.0f}%  {label(*combos[i])}")
    final = [((0, 0, 0, 0, 0), "SHY")] + top
    tests = {"IN-SAMPLE 1972-99 (fresh paths)": mp.make_idx(2000, 40, seed=602, era=(I72, I00)), "OUT-OF-SAMPLE 2000-26 bootstrap": mp.make_idx(2000, 40, seed=603, era=(I00, mp.T)),
             "full 1972-2026 bootstrap": mp.make_idx(2000, 40, seed=604)}
    res = {label(*c): {} for c in final}
    for lab, IDX in tests.items():
        print(f"Step 2: {lab}", flush=True); out = run(final, IDX)
        for c, s in zip(final, out): res[label(*c)][lab] = s
    Yh = (mp.T - 1 - I00) // 252; IDXh = torch.tensor((I00 + np.arange(Yh * 252))[None, :], device=mp.DEV)
    out = run(final, IDXh)
    for c, s in zip(final, out): res[label(*c)]["actual 2000-2026 path"] = s
    json.dump(res, open(os.path.join(ROOT, "..", "results", "tilt_search.json"), "w"), indent=1, default=float)
    mo = lambda x: f"${x*100000/12:,.0f}"
    print("\n| Tilt rule | CE in-sample 72-99 | CE OUT-OF-SAMPLE 00-26 | CE full | actual 2000-26: avg spend / end value | OOS base never cut | OOS dip<70% | OOS loses value | OOS dry |")
    print("|" + "---|" * 9)
    for n, v in res.items():
        o = v["OUT-OF-SAMPLE 2000-26 bootstrap"]; a = v["actual 2000-2026 path"]
        print(f"| {n} | {mo(v['IN-SAMPLE 1972-99 (fresh paths)']['ce'])} | **{mo(o['ce'])}** | {mo(v['full 1972-2026 bootstrap']['ce'])} | {mo(a['print_typical'])} / {a['left_typical']*100:.0f}% | {o['base_never_cut']*100:.0f}% | {o['deep_dip']*100:.0f}% | {o['lose_value']*100:.0f}% | {o['run_dry']*100:.1f}% |")
