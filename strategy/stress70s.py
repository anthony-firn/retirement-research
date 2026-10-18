"""1970s stress: run the policy over 1972-2026 (tiers extended with documented proxies, see history70s.py).
Set PORT_FILE=data_portfolios_1972.json; STATS_FILE chooses which history the tier choice is calibrated on.
Reports (1) fixed-budget policy vs static tier, 1972-2026 and the 1973-74 crash; (2) life plans for start
quarters 1972-1987 (stagflation cohort) and 1972-2016 (all)."""
import os, json, numpy as np, torch
assert os.environ.get("PORT_FILE"), "set PORT_FILE=data_portfolios_1972.json"
import life_gpu as lg, policy as pl

tag = os.environ.get("TAG", "")
print(f"=== {tag}  returns: {os.environ['PORT_FILE']}  tier stats: {os.environ.get('STATS_FILE', os.environ['PORT_FILE'])} ===")
# (1) fixed budgets, no cash flows
print(f"{'budget':>6} {'position':>8} | policy 1972-2026 CAGR/MDD | breaker-engaged | static tier at that position CAGR/MDD")
i74a, i74b = int(np.searchsorted(pl.DATES, "1973-01-02")), int(np.searchsorted(pl.DATES, "1974-12-31"))
for b in (10, 15, 20, 25, 30, 40, 50):
    path = pl.simulate(0, 60, 30, 1.0, 0, 200, 0, fixed_budget=b); v = np.array([p[1] for p in path]); xs = np.array([p[2] for p in path])
    c = ((v[-1] / v[0]) ** (252 / len(v)) - 1) * 100; mdd = (1 - v / np.maximum.accumulate(v)).max() * 100; x0 = pl.tier_for_budget(b)
    eng = (xs < x0 - 0.05).mean() * 100
    lo = int(np.floor(x0)); hi = min(lo + 1, len(pl.LADDER) - 1); f = x0 - lo
    sv = np.cumprod(1 + (1 - f) * pl.RET[:, lo] + f * pl.RET[:, hi]); sc = ((sv[-1] / sv[0]) ** (252 / len(sv)) - 1) * 100; smdd = (1 - sv / np.maximum.accumulate(sv)).max() * 100
    print(f"{b:>5}% {x0:8.2f} | {c:6.2f}% / {mdd:5.1f}%          | {eng:5.1f}% of days  | {sc:6.2f}% / {smdd:5.1f}%")
# (2) life plans
starts = [i for i in range(len(pl.DATES)) if (i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])) and pl.DATES[i] < "2017"]
coh = np.array([pl.DATES[s] < "1988" for s in starts])
rules = {"old rule": (8, 1.0, 40, 8, 1.0), "1988 rule": (20, 2.5, 50, 15, 1.0), "1972 rule": (25, 3.0, 50, 25, 1.0), "1972 rule, cap 30": (25, 3.0, 30, 25, 1.0)}
P = {k: torch.tensor([r[i] for r in rules.values()], device=lg.DEV, dtype=torch.float32) for i, k in enumerate(("BASE", "SLOPE", "CAP", "RET", "F0"))}
profs = dict(lg.PROFILES); profs["Retired 60y $300k, 4%"] = dict(age=60, value=300000, contrib=0, retire_age=60, spending=12000, already_retired=True)
out = {}
for name, prof in profs.items():
    m = lg.run(prof, P, starts, years=40); print(f"\n{name}")
    print(f"   {'rule':22} | cohort 1972-87: ran out  low-real-after  p75 yrs  worst DD | all 1972-2016: ran out  low-real-after  p75 yrs  worst DD")
    for j, rn in enumerate(rules):
        y = m["ytg"][:, j].cpu().numpy(); sp = m["span"][:, j].cpu().numpy(); cens = np.where(np.isnan(y), sp + 1, y)
        dead = m["dead"][:, j].cpu().numpy(); low = m["low_after"][:, j].cpu().numpy(); dd = m["mdd"][:, j].cpu().numpy()
        def cell(mask):
            lo_ = low[mask]; lo_ = lo_[lo_ < 1e8]
            return f"{dead[mask].sum():3d}/{mask.sum():<3d}  {(lo_.min()*100 if len(lo_) else float('nan')):9.0f}%  {np.percentile(cens[mask],75):7.1f}  {dd[mask].max():6.1f}%"
        print(f"   {rn:22} | {cell(coh):43} | {cell(np.ones_like(coh)):43}")
        out.setdefault(name, {})[rn] = dict(cohort_dead=int(dead[coh].sum()), all_dead=int(dead.sum()), worst_dd=float(dd.max()))
json.dump(out, open(os.path.join(pl.ROOT, f"stress70s_{tag or 'run'}.json"), "w"), indent=1)
