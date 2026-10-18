"""Bootstrap version of young_ceiling.py: 2000 synthetic 35-year histories (1-year and 3-month blocks of 1972-2026 data,
all tiers + CPI moving together). Phase 1 = hold a tier statically (no breaker) until an age, phase 2 = life-stage policy
(budget min(50, 25 + 3 x years left), daily breaker at budget - 2 on the worst-day curve)."""
import os, numpy as np, json
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import policy as pl
I = json.load(open(os.path.join(pl.ROOT, "data_indicators.json"))); ci = np.array(I["INFLATION"]["t"]); cv = np.array(I["INFLATION"]["v"])
T_ts = np.array(pl.D["t"]); CPI = cv[np.clip(np.searchsorted(ci, T_ts, side="right") - 1, 0, None)]; CPIR = np.r_[1, CPI[1:] / CPI[:-1]]
AGE, V0, C, RA = 30, 8000.0, 15000.0, 65; L = (RA - AGE) * 252; T = len(pl.DATES); K = len(pl.LADDER); WD = np.array(pl.WORST_DAY)
BT = {b: pl.tier_for_budget(b) for b in np.arange(0, 50.01, 0.5)}
def interp_wd(c):
    k = np.clip(np.searchsorted(WD, c, side="right") - 1, 0, len(WD) - 2); x = k + np.clip((c - WD[k]) / np.maximum(WD[k + 1] - WD[k], 1e-9), 0, 1)
    return np.where(c <= WD[0], 0.0, np.where(c >= WD[-1], len(WD) - 1.0, x))
def tret(x, rows):
    lo = np.floor(x).astype(int).clip(0, K - 1); hi = np.minimum(lo + 1, K - 1); f = x - lo
    return (1 - f) * pl.RET[rows, lo] + f * pl.RET[rows, hi]
def run(IDX, tier, until):
    N = IDX.shape[0]; v = np.full(N, V0); nav = np.ones(N); peak = np.ones(N); infl = np.ones(N); x = np.zeros(N); vpk = v.copy(); mdd = np.zeros(N)
    k_static = pl.LADDER.index(tier) if tier else None
    for d in range(L):
        rows = IDX[:, d]; age = AGE + d / 252; static = tier is not None and age < until
        if d > 0:
            r = pl.RET[rows, k_static] if static else tret(x, rows)
            v *= 1 + r; nav *= 1 + r; infl *= CPIR[rows]
            if d % 21 == 0: v += C / 12 * infl
        vpk = np.maximum(vpk, v / infl); mdd = np.maximum(mdd, 1 - nav / np.maximum.accumulate(nav[None], 0)[0] if False else mdd)
        peak = np.maximum(peak, nav); dd = (1 - nav / peak) * 100; mdd = np.maximum(mdd, dd)
        if static: continue
        if tier is not None and abs(age - until) < 0.5 / 252: peak = nav.copy(); dd = np.zeros(N)       # policy starts fresh at hand-over
        b = round(min(50.0, 25 + 3 * max(RA - age, 0)) * 2) / 2; cap = BT[b]
        cush = np.maximum(b - pl.MARGIN_GAP - dd, 0); gov = np.where(cush > WD[0], interp_wd(cush), 0.0); new = np.minimum(cap, gov)
        mv = np.abs(new - x) > 0.02; cost = np.where(mv & (d > 0), pl.COST * np.abs(new - x), 0); v *= 1 - cost; nav *= 1 - cost; x = np.where(mv | (d == 0), new, x)
    return v / infl, mdd
VAR = {"Policy (glide, budget 50 -> 25)": (None, 0), "S13.5 static to 65": ("S13.5", 65), "E20 to 45, then policy": ("E20", 45),
       "E24 to 45, then policy": ("E24", 45), "E24 static to 65": ("E24", 65)}
for block, lab in ((252, "1-year blocks"), (63, "3-month blocks (harsher)")):
    g = np.random.default_rng(11); nb = L // block + 1; st = g.integers(1, T - block, size=(2000, nb)); IDX = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(2000, -1)[:, :L]
    print(f"\n=== {lab}: age 30, $8k, +$15k/yr real to 65, 2000 histories. Real $ at 65 ===")
    print(f"{'':34} {'p5':>10} {'p25':>10} {'median':>11} {'p75':>11} | <$1.5M  | drop>50%  drop>70% | median worst drop")
    for n, (t, u) in VAR.items():
        f, m = run(IDX, t, u); m *= 1
        print(f"{n:34} {np.percentile(f,5):10,.0f} {np.percentile(f,25):10,.0f} {np.median(f):11,.0f} {np.percentile(f,75):11,.0f} | {np.mean(f<1.5e6)*100:5.1f}%  | {np.mean(m>50)*100:6.1f}%  {np.mean(m>70)*100:6.1f}%  | {np.median(m):5.1f}%", flush=True)
