"""At what age does an IRA reach a money-printer nest egg? Start $8k at age 30 (Roth), hold a portfolio (default IRA Accelerator 40),
contribute $X/month (real, rises with inflation like the IRA limit). Daily simulation on 2,000 reshuffled 1972-2026 histories out to age 90;
same rebalancing rule (> 6 points off target at most yearly + 2x valve), contributions to underweight funds first, no tax (Roth).
Target default $1.74M (today's dollars) = MP-2 base print of $100k/yr. Usage: python3 printer/retire_age.py [--target 1740000]"""
import os, sys, json, argparse, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--portfolio", default="IRA Accelerator 40"); ap.add_argument("--start", type=float, default=8000)
ap.add_argument("--age", type=int, default=30); ap.add_argument("--to-age", type=int, default=90); ap.add_argument("--targets", default="1740000,2050000")
ap.add_argument("--paths", type=int, default=2000); a = ap.parse_args(); sys.argv = [sys.argv[0]]
import money_printer as mp
DEV, f32 = mp.DEV, mp.f32
P = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json"))); alloc = {t: int(w) for t, w in P[a.portfolio]["alloc"].items()}
LEVELS = list(range(0, 1201, 100)) + [1250]                                      # $/month; 1250 = 2 x $7,500 (2026 couple limit)
YEARS = a.to_age - a.age; S = 252; L = YEARS * S; COST = 0.0005
assets = list(alloc); K = len(assets)
R = torch.tensor(np.stack([mp.fund_returns(t) for t in assets], 1), device=DEV, dtype=f32); C = torch.tensor(mp.CPIR, device=DEV, dtype=f32)
W0 = torch.tensor([alloc[t] / 100 for t in assets], device=DEV, dtype=f32)
IDX = mp.make_idx(a.paths, YEARS, seed=701); Pn = IDX.shape[0]; N = len(LEVELS) * Pn
li = torch.arange(len(LEVELS), device=DEV).repeat_interleave(Pn); pi = torch.arange(Pn, device=DEV).repeat(len(LEVELS))
contrib = torch.tensor(LEVELS, device=DEV, dtype=f32)[li]
val = W0[None, :].repeat(N, 1) * a.start; infl = torch.ones(N, device=DEV); last = torch.zeros(N, dtype=torch.long, device=DEV); yreal = torch.zeros(N, YEARS, device=DEV)
for d in range(1, L):
    rows = IDX[pi, d]; val = val * (1 + R[rows]); infl = infl * C[rows]
    if d % 21 == 0:                                                               # monthly contribution, underweight funds first
        amt = contrib * infl; V = val.sum(1); tgt = W0 * (V + amt)[:, None]; short = (tgt - val).clamp(min=0); ss = short.sum(1)
        fill = torch.minimum(amt, ss); val = val + short * (fill / ss.clamp(min=1e-9))[:, None] + W0 * (amt - fill)[:, None]
    V = val.sum(1); w = val / V.clamp(min=1e-9)[:, None]; since = d - last
    trig = (((w - W0).abs().max(1).values * 100 > 6) & (since > 252)) | ((w / W0).max(1).values >= 2.0)
    if bool(trig.any()):
        tgt = W0 * V[:, None]; cost = COST * (tgt - val).abs().sum(1) * trig
        val = torch.where(trig[:, None], tgt * (1 - cost / V.clamp(min=1e-9))[:, None], val); last = torch.where(trig, torch.full_like(last, d), last)
    if (d + 1) % S == 0: yreal[:, (d + 1) // S - 1] = val.sum(1) / infl
Wr = yreal.view(len(LEVELS), Pn, YEARS).cpu().numpy(); ages = a.age + 1 + np.arange(YEARS)
res = {}
for target in [float(x) for x in a.targets.split(",")]:
    print(f"\n{a.portfolio}: ${a.start:,.0f} at {a.age}, + $X/month (today's dollars, rising with inflation), Roth. 'Retire' = reach ${target/1e6:.2f}M in today's dollars"
          f" (MP-2 base print ${target*0.0575/1000:,.0f}k/yr)")
    print(f"{'per month':>10} {'per year':>9} | {'typical age':>11} {'lucky (1 in 4)':>15} {'unlucky (1 in 4)':>17} {'bad (1 in 10)':>14} | by 50   by 55   by 60   by 65  never by {a.to_age}")
    for k, m in enumerate(LEVELS):
        hit = Wr[k] >= target; first = np.where(hit.any(1), ages[hit.argmax(1)], 999)
        q = lambda p: (f"{int(np.percentile(first, p))}" if np.percentile(first, p) < 999 else f">{a.to_age}")
        pr = lambda age: (first <= age).mean() * 100
        print(f"${m:>9,} ${m*12:>8,} | {q(50):>11} {q(25):>15} {q(75):>17} {q(90):>14} | {pr(50):4.0f}%  {pr(55):4.0f}%  {pr(60):4.0f}%  {pr(65):4.0f}%  {(first == 999).mean()*100:4.0f}%")
        res[f"{int(target)}|{m}"] = dict(median=float(np.percentile(first, 50)), p25=float(np.percentile(first, 25)), p75=float(np.percentile(first, 75)), p90=float(np.percentile(first, 90)),
                                          by55=pr(55), by65=pr(65), never=float((first == 999).mean() * 100), med_at_65=float(np.median(Wr[k][:, 65 - a.age - 1])))
json.dump(res, open(os.path.join(ROOT, "..", "results", "retire_age.json"), "w"), indent=1, default=float)
