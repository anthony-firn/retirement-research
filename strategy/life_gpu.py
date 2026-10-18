"""GPU life-plan optimiser: tune the life-stage glide path of the policy over every historical start.

Lane = (start quarter, parameter set). Daily, in lockstep on the GPU:
  - return of the held tier blend (testfol.io daily data of the lineup)
  - breaker: position capped by the worst-day curve vs cushion (budget - 2 - drawdown of time-weighted NAV)
  - month start: contribution (before goal) or inflation-indexed withdrawal (after goal); budget re-planned:
      before goal: b = min(CAP, BASE + SLOPE * years_to_planned_retirement), de-risked toward RET as funded -> 1
      after goal (retire-on-goal): b = RET
Metrics per lane: years to goal, depleted after retiring, lowest real value after retiring / nest egg, max drawdown.
"""
import os, json, math, itertools, numpy as np, torch, datetime as dt
import policy as pl

DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu"); f32 = torch.float32
I = json.load(open(os.path.join(pl.ROOT, "data_indicators.json")))
t_ts = np.array(pl.D["t"]); ci = np.array(I["INFLATION"]["t"]); cv = np.array(I["INFLATION"]["v"])
CPI = torch.tensor(cv[np.clip(np.searchsorted(ci, t_ts, side="right") - 1, 0, None)], device=DEV, dtype=f32)
T = len(pl.DATES); K = len(pl.LADDER)
RET = torch.tensor(pl.RET, device=DEV, dtype=f32)                                   # (T, K)
MONTH = torch.tensor(np.r_[False, np.array([pl.DATES[i][:7] != pl.DATES[i - 1][:7] for i in range(1, T)])], device=DEV)
WD = torch.tensor(pl.WORST_DAY, device=DEV, dtype=f32)                              # monotone worst-day curve
BGRID = np.arange(0, 80.01, 0.25); XTAB = torch.tensor([pl.tier_for_budget(b) for b in BGRID], device=DEV, dtype=f32)

def x_of_budget(b):                                                                 # vectorised policy.tier_for_budget
    i = (b / 0.25).clamp(0, len(BGRID) - 1); lo = i.floor().long(); hi = (lo + 1).clamp(max=len(BGRID) - 1); f = i - lo
    return (1 - f) * XTAB[lo] + f * XTAB[hi]

def interp_pos(curve, level):                                                       # position where monotone curve reaches level
    k = (torch.searchsorted(curve, level.contiguous(), right=True) - 1).clamp(0, K - 2)
    a = curve[k]; b = curve[k + 1]; x = k.float() + ((level - a) / (b - a).clamp(min=1e-6)).clamp(0, 1)
    return torch.where(level <= curve[0], torch.zeros_like(x), torch.where(level >= curve[-1], torch.full_like(x, K - 1), x))

def run(profile, params, starts, years=40):
    """params: dict of (P,) tensors BASE, SLOPE, CAP, RET, F0. Returns metrics (S*P,)."""
    S = len(starts); P = len(params["BASE"]); N = S * P
    st = torch.tensor(starts, device=DEV).repeat_interleave(P); rep = lambda v: v.repeat(S)
    BASE, SLOPE, CAP, RETB, F0 = (rep(params[k]) for k in ("BASE", "SLOPE", "CAP", "RET", "F0"))
    egg = max(profile["spending"] - profile.get("other_income", 0), 0) / profile.get("swr", 0.04)
    v = torch.full((N,), float(profile["value"]), device=DEV); nav = torch.ones(N, device=DEV); peak = torch.ones(N, device=DEV)
    x = torch.zeros(N, device=DEV); b = torch.zeros(N, device=DEV)
    retired = torch.zeros(N, dtype=torch.bool, device=DEV) | torch.tensor(profile.get("already_retired", False), device=DEV)
    goal_day = torch.full((N,), -1, dtype=torch.long, device=DEV); goal_day = torch.where(retired, st, goal_day)
    dead = torch.zeros(N, dtype=torch.bool, device=DEV); low_after = torch.full((N,), 1e9, device=DEV); mdd = torch.zeros(N, device=DEV)
    end = torch.clamp(st + int(years * 252), max=T - 1)
    for d in range(int(min(starts)), T):
        act = (d > st) & (d <= end) & ~dead
        if not act.any():
            if d > int(end.max()): break
            continue
        infl = CPI[d] / CPI[st]
        lo = x.floor().long().clamp(0, K - 1); hi = (lo + 1).clamp(max=K - 1); f = x - lo.float()
        r = (1 - f) * RET[d][lo] + f * RET[d][hi]
        v = torch.where(act, v * (1 + r), v); nav = torch.where(act, nav * (1 + r), nav)
        peak = torch.maximum(peak, nav); dd = (1 - nav / peak) * 100; mdd = torch.where(act, torch.maximum(mdd, dd), mdd)
        if bool(MONTH[d]):
            age = profile["age"] + (d - st).float() / 252
            flow = torch.where(retired, -(egg * profile.get("swr", 0.04)) / 12 * infl, profile["contrib"] / 12 * infl)
            v = torch.where(act, v + flow, v); dead |= act & (v <= 0); v = v.clamp(min=0)
            real = v / infl; funded = real / egg
            newly = act & ~retired & (funded >= 1.0); goal_day = torch.where(newly, torch.full_like(goal_day, d), goal_day); retired |= newly
            yrs_left = (profile["retire_age"] - age).clamp(min=0)
            b_acc = torch.minimum(CAP, BASE + SLOPE * yrs_left)
            w = ((funded - F0) / (1 - F0).clamp(min=1e-6)).clamp(0, 1)                     # de-risk toward RET near the goal
            b_acc = torch.where(F0 < 1, b_acc - w * (b_acc - RETB).clamp(min=0), b_acc)
            b = torch.where(retired, RETB, b_acc)
            low_after = torch.where(act & retired, torch.minimum(low_after, funded), low_after)
        cap_x = x_of_budget(b); cushion = (b - pl.MARGIN_GAP - dd).clamp(min=0)
        gov = torch.where(cushion > WD[0], interp_pos(WD, cushion), torch.zeros_like(cushion))
        new = torch.minimum(cap_x, gov)
        move = (new - x).abs() > 0.02
        cost = torch.where(act & move, pl.COST * (new - x).abs(), torch.zeros_like(x))
        v = v * (1 - cost); nav = nav * (1 - cost); x = torch.where(move | (d == st), new, x)
    ytg = torch.where(goal_day >= 0, (goal_day - st).float() / 252, torch.full((N,), float("nan"), device=DEV))
    span = (end - st).float() / 252
    return dict(ytg=ytg.view(S, P), dead=dead.view(S, P), low_after=low_after.view(S, P), mdd=mdd.view(S, P), span=span.view(S, P))

def grid():
    G = list(itertools.product([4, 6, 8, 10, 12], [0.5, 0.75, 1.0, 1.25, 1.5], [20, 25, 30, 35, 40, 50], [6, 8, 10, 12, 15, 20], [0.6, 0.8, 1.0]))
    keys = ("BASE", "SLOPE", "CAP", "RET", "F0")
    return {k: torch.tensor([g[i] for g in G], device=DEV, dtype=f32) for i, k in enumerate(keys)}, G

PROFILES = {
    "25y $20k +$12k, wants $60k": dict(age=25, value=20000, contrib=12000, retire_age=65, spending=60000),
    "40y $250k +$20k, wants $70k": dict(age=40, value=250000, contrib=20000, retire_age=62, spending=70000),
    "55y $800k +$25k, wants $70k": dict(age=55, value=800000, contrib=25000, retire_age=65, spending=70000),
}
