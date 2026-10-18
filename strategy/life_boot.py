"""Stress beyond history: block-bootstrap synthetic 40-year histories from 1988-2026 testfol data
(1-year blocks keep the joint returns of every lineup tier + CPI together), then run the life-plan policy
on the GPU for each profile/rule.  Reports run-out probability, real value after retiring, years to goal,
worst drawdown (breaker guarantee check) and how often the breaker engaged.
Env: PATHS (2000), BLOCK (252 days), YEARS (40), SEED."""
import os, json, time, numpy as np, torch
import life_gpu as lg, policy as pl

DEV = lg.DEV; f32 = torch.float32; K = lg.K
PATHS = int(os.environ.get("PATHS", "2000")); BLOCK = int(os.environ.get("BLOCK", "252")); YEARS = int(os.environ.get("YEARS", "40"))
SEED = int(os.environ.get("SEED", "7")); L = YEARS * 252
CPIR = torch.cat([torch.ones(1, device=DEV), lg.CPI[1:] / lg.CPI[:-1]])           # daily CPI ratio
T = lg.T

def make_index(paths, g):
    nb = L // BLOCK + 1; st = g.integers(1, T - BLOCK, size=(paths, nb))
    idx = (st[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(paths, -1)[:, :L]
    return torch.tensor(idx, device=DEV)

def run(profile, rules, IDX):
    """rules: list of (BASE, SLOPE, CAP, RET). Lanes = paths x rules."""
    Pn, R = IDX.shape[0], len(rules); N = Pn * R
    path_of = torch.arange(Pn, device=DEV).repeat_interleave(R)
    rl = torch.tensor(rules, device=DEV, dtype=f32).repeat(Pn, 1); BASE, SLOPE, CAP, RETB = rl.T
    egg = max(profile["spending"] - profile.get("other_income", 0), 0) / profile.get("swr", 0.04)
    v = torch.full((N,), float(profile["value"]), device=DEV); nav = torch.ones(N, device=DEV); peak = torch.ones(N, device=DEV)
    infl = torch.ones(N, device=DEV); x = torch.zeros(N, device=DEV); b = torch.zeros(N, device=DEV)
    retired = torch.full((N,), bool(profile.get("already_retired", False)), device=DEV)
    goal_day = torch.where(retired, torch.zeros(N, dtype=torch.long, device=DEV), torch.full((N,), -1, dtype=torch.long, device=DEV))
    dead = torch.zeros(N, dtype=torch.bool, device=DEV); low_after = torch.full((N,), 1e9, device=DEV)
    mdd = torch.zeros(N, device=DEV); engaged = torch.zeros(N, device=DEV)
    for d in range(L):
        rows = IDX[path_of, d]
        if d > 0:
            lo = x.floor().long().clamp(0, K - 1); hi = (lo + 1).clamp(max=K - 1); f = x - lo.float()
            r = (1 - f) * lg.RET[rows, lo] + f * lg.RET[rows, hi]
            live = ~dead; v = torch.where(live, v * (1 + r), v); nav = torch.where(live, nav * (1 + r), nav); infl = infl * CPIR[rows]
        peak = torch.maximum(peak, nav); dd = (1 - nav / peak) * 100; mdd = torch.where(~dead, torch.maximum(mdd, dd), mdd)
        if d % 21 == 0:                                                           # ~monthly
            age = profile["age"] + d / 252
            flow = torch.where(retired, -(egg * profile.get("swr", 0.04)) / 12 * infl, profile["contrib"] / 12 * infl)
            if d > 0: v = torch.where(~dead, v + flow, v)
            dead |= v <= 0; v = v.clamp(min=0)
            funded = v / infl / egg
            newly = ~dead & ~retired & (funded >= 1); goal_day = torch.where(newly, torch.full_like(goal_day, d), goal_day); retired |= newly
            yrs_left = max(profile["retire_age"] - age, 0.0)
            b = torch.where(retired, RETB, torch.minimum(CAP, BASE + SLOPE * yrs_left))
            low_after = torch.where(~dead & retired, torch.minimum(low_after, funded), low_after)
        cap_x = lg.x_of_budget(b); cushion = (b - pl.MARGIN_GAP - dd).clamp(min=0)
        gov = torch.where(cushion > lg.WD[0], lg.interp_pos(lg.WD, cushion), torch.zeros_like(cushion))
        new = torch.minimum(cap_x, gov); engaged += (gov < cap_x - 0.02).float()
        move = (new - x).abs() > 0.02
        cost = torch.where(move & ~dead, pl.COST * (new - x).abs(), torch.zeros_like(x)); v = v * (1 - cost); nav = nav * (1 - cost)
        x = torch.where(move | (d == 0), new, x)
    ytg = torch.where(goal_day >= 0, goal_day.float() / 252, torch.full((N,), float("nan"), device=DEV))
    sh = lambda z: z.view(Pn, R).cpu().numpy()
    return dict(ytg=sh(ytg), dead=sh(dead), low_after=sh(low_after), mdd=sh(mdd), engaged=sh(engaged / L))

RULES = {"old (8+1/yr, cap 40, ret 8)": (8, 1.0, 40, 8), "new (20+2.5/yr, cap 50, ret 15)": (20, 2.5, 50, 15), "new, comfort cap 30": (20, 2.5, 30, 15)}
PROFILES = dict(lg.PROFILES); PROFILES["Retired 60y $300k, 4% ($12k)"] = dict(age=60, value=300000, contrib=0, retire_age=60, spending=12000, already_retired=True)

if __name__ == "__main__":
    t0 = time.time(); g = np.random.default_rng(SEED); IDX = make_index(PATHS, g); out = {}
    print(f"{PATHS} synthetic {YEARS}-year histories ({BLOCK}-day blocks from 1988-2026 testfol data)")
    for name, prof in PROFILES.items():
        m = run(prof, list(RULES.values()), IDX); print(f"\n{name}  ({time.time()-t0:.0f}s)")
        print(f"   {'rule':32} | ran out | lowest real after retiring: p5   p50 | years to goal p50  p90  never | worst DD p99  max | breaker engaged")
        for j, rn in enumerate(RULES):
            y = m["ytg"][:, j]; lo = m["low_after"][:, j]; lo = lo[lo < 1e8]; dd = m["mdd"][:, j]
            never = np.isnan(y).mean() * 100; yy = y[~np.isnan(y)]
            print(f"   {rn:32} | {m['dead'][:, j].mean()*100:5.1f}% | {np.percentile(lo,5)*100 if len(lo) else float('nan'):10.0f}% {np.median(lo)*100 if len(lo) else float('nan'):5.0f}% | "
                  f"{np.median(yy) if len(yy) else float('nan'):13.1f} {np.percentile(yy,90) if len(yy) else float('nan'):5.1f} {never:5.1f}% | {np.percentile(dd,99):11.1f} {dd.max():5.1f} | {m['engaged'][:, j].mean()*100:5.1f}% of days")
            out.setdefault(name, {})[rn] = dict(ran_out=float(m['dead'][:, j].mean()), low_p5=float(np.percentile(lo, 5)) if len(lo) else None,
                low_p50=float(np.median(lo)) if len(lo) else None, ytg_p50=float(np.median(yy)) if len(yy) else None, ytg_p90=float(np.percentile(yy, 90)) if len(yy) else None,
                never=float(never), dd_p99=float(np.percentile(dd, 99)), dd_max=float(dd.max()), engaged=float(m['engaged'][:, j].mean()))
    json.dump(out, open(os.path.join(pl.ROOT, "life_boot.json"), "w"), indent=1); print(f"\ndone {time.time()-t0:.0f}s")
