"""GPU-batched backtest of tier-switching strategies over the lineup (testfol.io daily data).

A strategy holds one lineup tier per day. Each day (decision at close t, executed next close -> 1-day lag):
  base      = B                                       (strategic max tier, from life stage)
  governor  = highest tier whose STRESS * M <= cushion,  cushion = L - drawdown(NAV vs decaying peak)
              STRESS = max(worst historical day, 1987 Black-Monday reconstruction, worst week / WEEKF)
  signals   = steps down for: SPY < SMA(n) | 20d realised vol > v | VIX > x | IEF 63d return < r
  target    = clamp(min(base, governor) - steps, 0);  rate shock -> swap to rate-hedged twin tier
  hysteresis: move down at once, move up only after the higher target has held for H days
Cost: COST per tier change. All N strategies advance in lockstep on the GPU.
"""
import json, os, math, datetime as dt
import numpy as np, torch

ROOT = os.path.dirname(os.path.abspath(__file__))
DEV = torch.device(os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu"))
LADDER = ["MinRisk", "Safe-Now", "C1-Now", "E9", "E10", "S12+", "S12.5", "S13", "S13.5", "E14", "E15", "M25", "M30", "M35", "E20", "E22", "E24"]
HEDGED = {"E9": "C1-Now", "E10": "C1-Now", "S12+": "S12-F5", "S12.5": "S12-F5"}      # rate-shock twins
COST = float(os.environ.get("COST", "0.001"))                                    # 0.10% per switch

# ------------------------------------------------------------------ data
P = json.load(open(os.path.join(ROOT, "data_portfolios.json"))); I = json.load(open(os.path.join(ROOT, "data_indicators.json")))
BM = json.load(open(os.path.join(ROOT, "black_monday.json")))
T_ts = np.array(P["t"]); T = len(T_ts)
DATES = np.array([dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in T_ts])
YEARS = np.array([int(d[:4]) for d in DATES])
VAL = {n: np.array(v) for n, v in zip(P["names"], P["v"])}
ALL_TIERS = LADDER + [h for h in sorted(set(HEDGED.values())) if h not in LADDER]
K = len(LADDER)
R = np.stack([VAL[n][1:] / VAL[n][:-1] - 1 for n in ALL_TIERS], 1)            # (T-1, tiers) daily returns
R = np.vstack([np.zeros((1, R.shape[1])), R])                                    # R[d] = return on day d
def worst(n, k): v = VAL[n]; return float((v[k:] / v[:-k] - 1).min()) * -100
STRESS_DAY = np.array([max(worst(n, 1), -BM.get(n, 0.0)) for n in ALL_TIERS])  # % loss, positive
STRESS_WEEK = np.array([worst(n, 5) for n in ALL_TIERS])
HEDGE_IDX = np.arange(len(ALL_TIERS))
for a, b in HEDGED.items(): HEDGE_IDX[ALL_TIERS.index(a)] = ALL_TIERS.index(b)

def align(name):
    t = np.array(I[name]["t"]); v = np.array(I[name]["v"]); idx = np.searchsorted(t, T_ts, side="right") - 1
    out = np.where(idx >= 0, v[np.clip(idx, 0, None)], np.nan); return out
SPY, VIXr, IEF = align("SPYSIM"), align("VIXSIM"), align("IEFSIM")
VIX = VIXr * 17.24                                                               # VIXSIM normalised to 1 on 1990-01-02 (VIX 17.24)
# extend SPY history backwards for SMAs (indicator series start long before 1988)
spy_t = np.array(I["SPYSIM"]["t"]); spy_v = np.array(I["SPYSIM"]["v"])
def sma_flag(n):                                                                 # SPY below its n-day SMA (known at close)
    c = np.cumsum(np.r_[0, spy_v]); sma = (c[n:] - c[:-n]) / n; s_t = spy_t[n - 1:]
    idx = np.searchsorted(s_t, T_ts, side="right") - 1
    return (SPY < sma[np.clip(idx, 0, None)]) & (idx >= 0)
def rvol(n=20):
    lr = np.diff(np.log(spy_v)); s = np.sqrt(np.convolve(lr ** 2, np.ones(n), "valid") / n) * math.sqrt(252) * 100
    s_t = spy_t[n:]; idx = np.searchsorted(s_t, T_ts, side="right") - 1; return s[np.clip(idx, 0, None)]
ief_t = np.array(I["IEFSIM"]["t"]); ief_v = np.array(I["IEFSIM"]["v"])
def ief_ret(n=63):
    r = ief_v[n:] / ief_v[:-n] - 1; s_t = ief_t[n:]; idx = np.searchsorted(s_t, T_ts, side="right") - 1; return r[np.clip(idx, 0, None)] * 100

SMA_N = [50, 100, 150, 200, 250]
SMA_FLAGS = torch.tensor(np.stack([sma_flag(n) for n in SMA_N]), device=DEV)   # (5, T) bool
RVOL = torch.tensor(rvol(20), device=DEV, dtype=torch.float32)
VIXT = torch.tensor(np.nan_to_num(VIX, nan=0.0), device=DEV, dtype=torch.float32)
IEF63 = torch.tensor(ief_ret(63), device=DEV, dtype=torch.float32)
RT = torch.tensor(R, device=DEV, dtype=torch.float32)
SDAY = torch.tensor(STRESS_DAY, device=DEV, dtype=torch.float32); SWEEK = torch.tensor(STRESS_WEEK, device=DEV, dtype=torch.float32)
HIDX = torch.tensor(HEDGE_IDX, device=DEV)
RF = align("TBILL"); RFD = torch.tensor(np.r_[0, RF[1:] / RF[:-1] - 1], device=DEV, dtype=torch.float32)

# ------------------------------------------------------------------ parameter space
SPACE = dict(
    B=list(range(K)),                         # strategic max tier index
    L=[5, 8, 10, 12, 15, 20, 25, 30, 40, 50],  # loss budget % (drawdown governor)
    M=[0.5, 1.0, 1.5, 2.0, 3.0],              # stress multiplier (higher = more cautious)
    WEEKF=[1.0, 1.5, 2.0, 99.0],              # stress = max(day, week/WEEKF); 99 ~ ignore week
    DECAY=[0.0, 0.0005, 0.001, 0.002, 0.004], # peak decay per day (0 = all-time high; 0.002 ~ budget refills over ~2y)
    SMA=[-1, 0, 1, 2, 3, 4],                  # index into SMA_N, -1 = off
    S_TREND=[0, 1, 2, 3, 4, 6],
    VOL=[0, 20, 25, 30, 40],                  # realised-vol threshold (0 = off)
    S_VOL=[0, 1, 2, 3, 4, 6],
    VIXL=[0, 25, 30, 35, 45],                 # VIX threshold (0 = off)
    S_VIX=[0, 1, 2, 3, 4],
    RATE=[0, -2, -3, -4, -6],                 # IEF 63d return threshold % (0 = off)
    S_RATE=[0, 1, 2],
    HEDGE=[0, 1],                             # swap to rate-hedged twin during rate shock
    H=[0, 5, 10, 20, 40, 60],                 # re-risk delay (days)
)
KEYS = list(SPACE)

def sample(n, g, fixed=None):
    P_ = {k: torch.tensor(g.choice(len(v), n), device=DEV) for k, v in SPACE.items()}
    if fixed:
        for k, v in fixed.items(): P_[k] = torch.full((n,), SPACE[k].index(v), device=DEV)
    return P_

def decode(P_, i): return {k: SPACE[k][int(P_[k][i])] for k in KEYS}

def run(P_, d0=0, d1=None, keep_tiers=False):
    """Simulate all strategies in P_ (dict of index tensors) over days [d0, d1). Returns metrics dict of (N,) tensors."""
    d1 = d1 or T; N = len(P_["B"]); f32 = torch.float32
    val = lambda k: torch.tensor(SPACE[k], device=DEV, dtype=f32)[P_[k]]
    B = P_["B"]; L = val("L"); M = val("M"); WF = val("WEEKF"); DEC = val("DECAY")
    smai = torch.tensor(SPACE["SMA"], device=DEV)[P_["SMA"]]; st = val("S_TREND").long()
    vth = val("VOL"); sv = val("S_VOL").long(); xth = val("VIXL"); sx = val("S_VIX").long()
    rth = val("RATE"); sr = val("S_RATE").long(); hedge = P_["HEDGE"].bool(); H = val("H")
    stress = torch.maximum(SDAY[None, :K], SWEEK[None, :K] / WF[:, None]) * M[:, None]       # (N, K)
    stress = torch.cummax(stress, 1).values                                                   # monotone along the ladder
    nav = torch.ones(N, device=DEV); peak = torch.ones(N, device=DEV)
    cur = torch.zeros(N, dtype=torch.long, device=DEV); pend = torch.zeros(N, device=DEV)    # held tier, days target>cur
    held = torch.zeros(N, dtype=torch.long, device=DEV)                                        # tier actually invested (1-day lag)
    mdd = torch.zeros(N, device=DEV); ulc = torch.zeros(N, device=DEV); s1 = torch.zeros(N, device=DEV); s2 = torch.zeros(N, device=DEV)
    switches = torch.zeros(N, device=DEV); worst_day = torch.zeros(N, device=DEV)
    ar = torch.arange(N, device=DEV); tiers_hist = [] if keep_tiers else None
    for d in range(d0, d1):
        # 1) today's return on yesterday-decided, today-executed position
        if d > d0:
            idx = torch.where(hedge & rate_on, HIDX[held], held) if d > d0 + 1 else held
            r = RT[d][idx]; nav = nav * (1 + r); s1 += r - RFD[d]; s2 += (r - RFD[d]) ** 2; worst_day = torch.minimum(worst_day, r)
        peak = torch.maximum(nav, peak * (1 - DEC)); peak = torch.maximum(peak, nav)
        dd = 1 - nav / torch.maximum(peak, nav)                       # current drawdown (fraction)
        # all-time drawdown for metrics
        if d == d0: hw = nav.clone()
        hw = torch.maximum(hw, nav); ddm = 1 - nav / hw; mdd = torch.maximum(mdd, ddm); ulc += (ddm * 100) ** 2
        # 2) decision at close d
        cushion = (L - dd * 100).clamp(min=0)
        gov = ((stress <= cushion[:, None]).long().sum(1) - 1).clamp(min=0)               # highest affordable tier (monotone stress)
        steps = torch.zeros(N, dtype=torch.long, device=DEV)
        trend = torch.where(smai >= 0, SMA_FLAGS[smai.clamp(min=0), d], torch.zeros(N, dtype=torch.bool, device=DEV))
        steps += torch.where(trend, st, 0)
        steps += torch.where((vth > 0) & (RVOL[d] > vth), sv, 0)
        steps += torch.where((xth > 0) & (VIXT[d] > xth), sx, 0)
        rate_on = (rth < 0) & (IEF63[d] < rth)
        steps += torch.where(rate_on, sr, 0)
        target = (torch.minimum(B, gov) - steps).clamp(min=0)
        up = target > cur; pend = torch.where(up, pend + 1, torch.zeros_like(pend))
        new = torch.where(target < cur, target, torch.where(up & (pend >= H), target, cur))
        changed = new != cur
        nav = nav * (1 - COST * changed.float()); switches += changed.float(); cur = new
        held = cur                                                                         # executes at next close
        if keep_tiers: tiers_hist.append(cur.clone())
    n = d1 - d0; yrs = n / 252
    cagr = (nav ** (1 / yrs) - 1) * 100
    mean = s1 / n; var = (s2 / n - mean ** 2).clamp(min=1e-12); sharpe = mean * 252 / (var.sqrt() * math.sqrt(252))
    out = dict(cagr=cagr, mdd=mdd * 100, ulcer=(ulc / n).sqrt(), sharpe=sharpe, calmar=cagr / (mdd * 100).clamp(min=1e-6),
               switches=switches / yrs, worst_day=worst_day * 100)
    if keep_tiers: out["tiers"] = torch.stack(tiers_hist)
    return out

def static(tier_name, d0=0, d1=None):
    """Buy-and-hold one tier (for comparison)."""
    v = VAL[tier_name][d0:d1 or T]; yrs = len(v) / 252; dd = 1 - v / np.maximum.accumulate(v)
    return dict(cagr=((v[-1] / v[0]) ** (1 / yrs) - 1) * 100, mdd=dd.max() * 100, ulcer=float(np.sqrt(((dd * 100) ** 2).mean())))

if __name__ == "__main__":
    import time
    g = np.random.default_rng(0); P_ = sample(20000, g); t0 = time.time()
    m = run(P_); torch.cuda.synchronize() if DEV.type == "cuda" else None
    print(f"{len(P_['B'])} strategies x {T} days in {time.time()-t0:.1f}s on {DEV}")
    ok = m["mdd"] <= 20
    print("feasible (MDD<=20%):", int(ok.sum()), " best CAGR:", float(m["cagr"][ok].max()))
