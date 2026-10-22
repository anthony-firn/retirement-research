"""Bring MP-2.1 inside the forward-scenario guard rail (every bad scenario >= -8.5%; today it is -10.1% in the deflationary
recession) with the smallest cost to the printer, and favour changes that also help when yields keep rising (bond revolt,
stagflation). Candidates are small swaps out of VBR / TQQQ into gold (IAUM), defensive stocks (XLV, XLP), intermediate or short
Treasuries (IEI, SHY). Each candidate must pass the scenario rail; survivors go through the printer test (the retiree's taxes, 5 stress
cases: search on 1,000 histories, top 4 re-run on 2,000 fresh ones) against MP-2.1 on both tracks.
Usage: THROTTLE=1 python3 printer/deflation_fix.py   (writes results/deflation_fix.log / .json)"""
import os, sys, json, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.argv = [sys.argv[0]]
import money_printer as mp, improve as im
from dataclasses import replace
sys.path.insert(0, os.path.join(ROOT, "..", "lab")); import stress_forward as sf
SCN = list(sf.SC); BAD = [k for k in SCN if not k.startswith("Soft")]
short = {SCN[0]: "AI bust", SCN[1]: "stagflation", SCN[2]: "bond revolt", SCN[3]: "deflation", SCN[4]: "dollar crisis", SCN[5]: "soft landing"}
def scen(a): return {k: sum(w / 100 * sf.move("GLDSIM" if t in ("IAUMSIM", "GLDMSIM") else t, sf.SC[k]) for t, w in a.items()) for k in SCN}
def swaps(base):
    out = {}
    def add(lab, moves):
        a = dict(base)
        for t, d in moves.items(): a[t] = a.get(t, 0) + d
        if min(a.values()) < 0: return
        out[lab] = {t: w for t, w in a.items() if w > 0}
    add("TQQQ 2 -> IAUM", {"TQQQSIM": -2, "IAUMSIM": 2})
    add("TQQQ 2 -> IEI", {"TQQQSIM": -2, "IEISIM": 2})
    add("TQQQ 2 -> GDE", {"TQQQSIM": -2, "GDESIM": 2})
    for x in (3, 4, 5, 6, 8):
        for dst in ("IAUMSIM", "XLVSIM", "XLPSIM", "IEISIM", "SHYSIM"):
            add(f"VBR {x} -> {dst[:-3]}", {"VBRSIM": -x, dst: x})
            add(f"TQQQ 2 -> IAUM + VBR {x} -> {dst[:-3]}", {"TQQQSIM": -2, "IAUMSIM": 2, "VBRSIM": -x, dst: x})
    add("VBR 4 -> IAUM 2 + IEI 2", {"VBRSIM": -4, "IAUMSIM": 2, "IEISIM": 2})
    add("VBR 6 -> IAUM 3 + XLV 3", {"VBRSIM": -6, "IAUMSIM": 3, "XLVSIM": 3})
    add("GDE 5 -> IAUM 5", {"GDESIM": -5, "IAUMSIM": 5})
    add("TQQQ 2 + GDE 3 -> IAUM 5", {"TQQQSIM": -2, "GDESIM": -3, "IAUMSIM": 5})
    return out

if __name__ == "__main__":
    best = im.load_best(); log = open(os.path.join(ROOT, "..", "results", "deflation_fix.log"), "w"); out = {}
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    ref_alloc = best["simple"]["alloc"]; s0 = scen(ref_alloc)
    say("Forward scenarios (hypothetical one-shot moves, % of the portfolio; rail: every bad scenario >= -8.5%)")
    say(f"  {'MP-2.1':44} " + " | ".join(f"{short[k]} {s0[k]:+5.1f}" for k in SCN))
    cands = swaps(ref_alloc); keep = {}
    for lab, a in cands.items():
        s = scen(a)
        if min(s[k] for k in BAD) >= -8.5: keep[lab] = (a, s)
    say(f"  {len(keep)} of {len(cands)} swaps pass the rail")
    for track in ("simple", "credit"):
        ref = im.P(**best[track]); pr = [ref] + [replace(ref, name=f"{ref.name} | {lab}", alloc=a) for lab, (a, s) in keep.items()]
        say(f"\n[{track}] reference: {ref.name}; search {im.PATHS} histories x 5 cases"); C = list(im.cases(0, 1))
        R = im.evaluate(pr, im.cases(601, im.PATHS)); r0 = R[ref.name]
        okk = sorted([p for p in pr[1:] if im.safe(R[p.name], r0, C)], key=lambda p: -R[p.name]["robust_ce"])[:4]
        V = im.evaluate([ref] + okk, im.cases(701, im.FRESH)) if okk else {}
        out[track] = dict(search=R, validate=V)
        mo = lambda x: f"${x * 5e4 / 12:,.0f}"
        for title, T in (("search", R), ("fresh", V)):
            if not T: continue
            say(f"  [{track}] {title}: {'change':44} | robust CE $50k | first 10 yrs | 40-yr typ / bad | lose dip dry | trend -4% CE | deflation / AI bust / bond revolt / stagflation | break risk no worse")
            for n, v in sorted(T.items(), key=lambda kv: -kv[1]["robust_ce"])[:12 if title == "search" else 6]:
                lab = n.split(" | ")[-1] if n != ref.name else "MP-2.1 (reference)"; b = v["base"]; s = keep[lab][1] if lab in keep else s0
                say(f"    {lab:44} | {mo(v['robust_ce'])} ({(v['robust_ce'] / T[ref.name]['robust_ce'] - 1) * 100:+.1f}%) | {mo(b['print_y1_10_typ'])} | {mo(b['print_typical'])} / {mo(b['print_bad'])} | "
                    f"{b['lose_value']*100:.0f}% {b['deep_dip']*100:.0f}% {b['run_dry']*100:.1f}% | {mo(v['trend -4%/yr']['ce'])} | {s[SCN[3]]:+.1f} / {s[SCN[0]]:+.1f} / {s[SCN[2]]:+.1f} / {s[SCN[1]]:+.1f} | "
                    f"{'yes' if im.safe(v, T[ref.name], C) else 'no'}")
    json.dump(dict(out=out, scenarios={lab: s for lab, (a, s) in keep.items()}, ref_scenarios=s0), open(os.path.join(ROOT, "..", "results", "deflation_fix.json"), "w"), indent=1, default=float)
