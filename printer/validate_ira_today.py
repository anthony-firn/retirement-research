"""Validate the 'safer for today' aggressive IRA portfolios against IRA Max 60 and friends.
Daily, 2,000 fresh histories (35 years, $8k + $15k/yr real, no tax), base + 7 stresses incl. the AI unwind, plus forward scenarios
and testfol.io. Writes results/accumulate_today_validate.log/.json."""
import os, sys, json, numpy as np, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "..", "lab"))
sys.argv = [sys.argv[0]]
import money_printer as mp, accumulate as ac, stress_forward as sf
P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json"))); C = {}
for i, r in enumerate(json.load(open(os.path.join(ROOT, "..", "results", "accumulate_today_cap45.json")))[:4]): C[f"Today-safe #{i+1}"] = {t: int(w) for t, w in r["alloc"].items()}
for n in ("IRA Max 60", "IRA Accelerator 40", "IRA Steady 30", "MP-2 engine", "VTI (100% US stocks)"): C[n] = {t: int(w) for t, w in P[n]["alloc"].items()}
names = list(C); al = [C[n] for n in names]
i00 = int(np.searchsorted(mp.h.CAL, int(dt.datetime(2000, 1, 3, tzinfo=dt.UTC).timestamp())))
runs = {"base": (mp.make_idx(2000, 35, seed=502), {}), "AI unwind": (mp.make_idx(2000, 35, seed=503), dict(drag=ac.AI_UNWIND)),
        "trend -4%": (mp.make_idx(2000, 35, seed=504), dict(trend_haircut=0.04)), "gold -5%": (mp.make_idx(2000, 35, seed=505), dict(drag={"GLDSIM": .05, "GDESIM": .045, "UGLSIM": .10})),
        "lev cost +1%/x": (mp.make_idx(2000, 35, seed=506), dict(drag={t: (x - 1) * 0.01 for t, x in ac.LEVX.items()})),
        "3-month blocks": (mp.make_idx(2000, 35, block=63, seed=507), {}), "recent era": (mp.make_idx(2000, 35, seed=508, era=(i00, mp.T)), {})}
res = {n: {} for n in names}
for lab, (IDX, kw) in runs.items():
    for i in range(0, len(al), 8):
        r = ac.simulate(al[i:i + 8], IDX, step=1, **kw)
        for c, n in enumerate(names[i:i + 8]):
            w65, w55, dd = r["wealth"][65][c], r["wealth"][55][c], r["mdd"][c] * 100
            res[n][lab] = dict(ce=ac.ce(w65), med=float(np.median(w65)), p10=float(np.percentile(w65, 10)), med55=float(np.median(w55)), nest55=float((w55 >= 1750).mean()),
                               dd50=float(np.median(dd)), dd90=float(np.percentile(dd, 90)), p50=float((dd > 50).mean()))
    print(f"  {lab} done", flush=True)
M = lambda x: f"${x/1000:.2f}M"; BAD = [k for k in sf.SC if not k.startswith("Soft")]
print("| Portfolio | Engine | Robust CE @65 | Worst-case CE | Median @65 | Bad (p10) | Median @55 | $1.75M by 55 | Drop lived median / 1-in-10 | >50% drop | AI exposure | Gold | Worst forward scenario | Worst day | CE: AI unwind / trend -4% / gold -5% / lev cost / 3-mo / recent era | testfol CAGR / MDD / Sharpe |")
print("|" + "---|" * 17)
for n in names:
    v = res[n]; v["robust_ce"] = float(np.mean([v[k]["ce"] for k in runs])); v["worst_ce"] = float(min(v[k]["ce"] for k in runs)); a = C[n]
    v["alloc"] = a; v["ai"] = ac.ai_x(a); v["gold"] = ac.gold_x(a); v["fwd"] = {k: float(sum(w / 100 * sf.move(t, sf.SC[k]) for t, w in a.items())) for k in sf.SC}
    v["worst_day"] = float(sum(w / 100 * mp.fund_returns(t) for t, w in a.items())[1:].min() * 100); v["testfol"] = ac.testfol(a)
for n in sorted(names, key=lambda n: -res[n]["robust_ce"]):
    v = res[n]; b = v["base"]; eng = " · ".join(f"{t.replace('SIM','')} {w}" for t, w in sorted(v["alloc"].items(), key=lambda x: -x[1]))
    wf = min(BAD, key=lambda k: v["fwd"][k])
    print(f"| {n} | {eng} | **{M(v['robust_ce'])}** | {M(v['worst_ce'])} | {M(b['med'])} | {M(b['p10'])} | {M(b['med55'])} | {b['nest55']*100:.0f}% | {b['dd50']:.0f}% / {b['dd90']:.0f}% | {b['p50']*100:.0f}% | {v['ai']:.0f}% | {v['gold']:.0f}% | {v['fwd'][wf]:.1f}% ({wf.split(' (')[0]}) | {v['worst_day']:.1f}% | "
          + " / ".join(M(v[k]["ce"]) for k in runs if k != "base") + f" | {v['testfol']} |")
json.dump(res, open(os.path.join(ROOT, "..", "results", "accumulate_today_validate.json"), "w"), indent=1, default=float)
