"""The investment policy (single source of truth for advisor + life-plan backtests).

1. Life stage -> loss budget b (% max drawdown you can afford).
2. Tier: the lineup position x with historical max drawdown <= 75% of b and (MDD + worst day) <= 90% of the
   breaker level (continuous: blends two adjacent tiers), so the breaker only fires in an unprecedented crash.
3. Guaranteed breaker: L = b - 2 on the account's all-time high. Each day the position is capped at the highest
   tier whose worst historical day (incl. 1987 reconstruction) fits in the remaining cushion -> total loss is
   bounded by construction at ~L + one worst day of the tier held at the floor.
Market-timing signals were tested on the GPU and dropped: no reliable out-of-sample benefit (see results/STRATEGY.md).
"""
import json, os, math, numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
PF = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
D = json.load(open(os.path.join(ROOT, "data_portfolios.json")))
BM = json.load(open(os.path.join(ROOT, "black_monday.json")))
LADDER = ["MinRisk", "Safe-Now", "C1-Now", "E9", "E10", "S12+", "S12.5", "S13", "S13.5", "E14", "E15", "M25", "M30", "M35", "E20", "E22", "E24"]
VAL = {n: np.array(v) for n, v in zip(D["names"], D["v"])}
import datetime as _dt
DATES = np.array([_dt.datetime.fromtimestamp(x, _dt.UTC).date().isoformat() for x in D["t"]])
RET = np.stack([np.r_[0, VAL[n][1:] / VAL[n][:-1] - 1] for n in LADDER], 1)            # (T, K)
MDD = np.maximum.accumulate(np.array([(1 - VAL[n] / np.maximum.accumulate(VAL[n])).max() * 100 for n in LADDER]))
WORST_DAY = np.maximum.accumulate(np.array([max((1 - VAL[n][1:] / VAL[n][:-1]).max() * 100, -BM.get(n, 0)) for n in LADDER]))
TIER_FRAC, MARGIN_GAP, COST = 0.75, 2.0, 0.001
REAL = lambda t: "VNQ" if t == "REITSIM" else t.replace("SIM", "")

def interp_position(curve, level):
    """Continuous ladder position where a monotone curve reaches `level`."""
    if level <= curve[0]: return 0.0
    if level >= curve[-1]: return float(len(curve) - 1)
    k = int(np.searchsorted(curve, level, side="right") - 1)
    return k + (level - curve[k]) / max(curve[k + 1] - curve[k], 1e-9)

# Life-stage rule tuned on the GPU over every historical start (strategy/optimize_life2.py; chosen on 1988-2002
# starts, validated on 2003-2016 starts): budget = min(comfort cap, 50, 20 + 2.5 x years to retirement); retired/funded: 15.
RULE = dict(BASE=20.0, SLOPE=2.5, CAP=50.0, RET=15.0)
DROP_TO_CAP = 1 / 0.6          # worst drop actually lived through was ~60% of the cap in backtests (results/comfort_menu.log)

def cap_for_max_drop(max_drop): return min(RULE["CAP"], max(6.0, max_drop * DROP_TO_CAP))

def life_budget(age, value, contrib, retire_age, spending, other_income=0.0, swr=0.04, max_drop=None):
    need = max(spending - other_income, 0) / swr; funded = value / need if need > 0 else 99.0
    years = max(retire_age - age, 0.0); cap = cap_for_max_drop(max_drop) if max_drop else RULE["CAP"]
    if funded >= 1.0 or years <= 0: b = min(RULE["RET"], cap); stage = "retired / fully funded"
    else:
        b = min(cap, RULE["BASE"] + RULE["SLOPE"] * years); stage = "pre-retirement" if years <= 5 else "accumulating"
    return b, dict(stage=stage, years=years, nest_egg=need, funded=funded, cap=cap)

TRIGGER_FRAC = 0.9
def _at(curve, x):
    lo = int(math.floor(x)); hi = min(lo + 1, len(curve) - 1); f = x - lo; return (1 - f) * curve[lo] + f * curve[hi]

def tier_for_budget(b):
    """Position with MDD <= 75% of budget AND (MDD + worst day) <= 90% of the breaker level, so the breaker only
    fires in a crash worse than anything in the 1988-2026 record (+1987 day)."""
    x = interp_position(MDD, TIER_FRAC * b); lim = TRIGGER_FRAC * (b - MARGIN_GAP)
    while x > 0 and _at(MDD, x) + _at(WORST_DAY, x) > lim: x = max(0.0, x - 0.01)
    return x

def breaker(x_cap, dd_pct, b):
    """Highest position <= x_cap whose worst historical day fits in the cushion (L - drawdown)."""
    cushion = max(b - MARGIN_GAP - dd_pct, 0.0)
    return min(x_cap, interp_position(WORST_DAY, cushion)) if cushion > WORST_DAY[0] else 0.0

def blend(x):
    lo = int(math.floor(x)); hi = min(lo + 1, len(LADDER) - 1); f = x - lo
    w = {}
    for name, frac in ((LADDER[lo], 1 - f), (LADDER[hi], f)):
        if frac <= 0: continue
        for t, v in PF[name]["alloc"].items(): w[REAL(t)] = w.get(REAL(t), 0) + frac * v / 100
    return (LADDER[lo], LADDER[hi], f), dict(sorted(w.items(), key=lambda kv: -kv[1]))

def day_return(x, d):
    lo = int(math.floor(x)); hi = min(lo + 1, len(LADDER) - 1); f = x - lo
    return (1 - f) * RET[d, lo] + f * RET[d, hi]

def simulate(start, years, age, value, contrib, retire_age, spending, other_income=0.0, swr=0.04, cpi=None, fixed_budget=None):
    """Daily simulation from index `start`: monthly contributions until retirement, withdrawals after.
    Budget re-evaluated monthly from life stage (glide path). Breaker uses time-weighted NAV vs its peak."""
    end = min(len(DATES), start + int(years * 252)); v = value; nav = 1.0; peak = 1.0; x = 0.0; out = []
    month = DATES[start][:7]; a0 = age; b = None
    for d in range(start, end):
        t_years = (d - start) / 252; ag = a0 + t_years; infl = cpi[d] / cpi[start] if cpi is not None else 1.0
        if d > start:
            r = day_return(x, d); v *= 1 + r; nav *= 1 + r
            if DATES[d][:7] != month:                                  # month boundary: cash flow + re-plan
                month = DATES[d][:7]
                v += (contrib / 12 * infl) if ag < retire_age else -(max(spending - other_income, 0) / 12 * infl)
                if v <= 0: out.append((DATES[d], 0.0, x, b)); break
        if b is None or DATES[d][:7] != DATES[d - 1][:7]:
            b, _ = life_budget(ag, v / infl, contrib, retire_age, spending, other_income, swr) if fixed_budget is None else (fixed_budget, None)
        peak = max(peak, nav); dd = (1 - nav / peak) * 100
        new = breaker(tier_for_budget(b), dd, b)
        if abs(new - x) > 0.02 and d > start: v *= 1 - COST * abs(new - x); nav *= 1 - COST * abs(new - x)
        x = new; out.append((DATES[d], v / infl, x, b))
    return out
