"""How effective is the policy? Head-to-head life plans vs what people actually use.
Same investors, same cash flows (retire on reaching the nest egg, then 4% inflation-indexed withdrawals),
same 1972-2026 data (testfol SIM components; policy tiers extended per history70s.py):
  100% stocks (VTI) | 60/40 VTI/BND yearly-rebalanced | target-date glide path (stocks = 110-age, 30..90%) | our policy
Evaluated on every quarterly start 1972-2016 and on 2000 bootstrapped 40-year histories (1-year blocks)."""
import os, json, numpy as np, torch
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import life_gpu as lg, life_boot as lb, policy as pl

DEV = lg.DEV; f32 = torch.float32
H = json.load(open(os.path.join(pl.ROOT, "..", "lab", "hist_long.json")))
t = np.array(pl.D["t"])
def ser(name):
    tt = np.array(H[name]["t"]); vv = np.array(H[name]["v"]); i = np.searchsorted(tt, t, side="right") - 1
    v = np.where(i >= 0, vv[np.clip(i, 0, None)], np.nan); return v
def r(v): return np.nan_to_num(np.r_[0, v[1:] / v[:-1] - 1])
bnd = ser("BNDSIM"); iei = ser("IEISIM"); bond = np.where(np.isnan(bnd), r(iei), r(np.nan_to_num(bnd, nan=1.0))); bond[np.isnan(np.r_[np.nan, bnd[:-1]]) & ~np.isnan(bnd)] = r(iei)[np.isnan(np.r_[np.nan, bnd[:-1]]) & ~np.isnan(bnd)]
STK = torch.tensor(r(ser("VTISIM")), device=DEV, dtype=f32); BND = torch.tensor(bond, device=DEV, dtype=f32)

def sim_simple(profile, kinds, idx_rows, L, lane_end=None):
    """kinds: list of 'vti' | '6040' | 'tdf'. idx_rows(d) -> (N,) row indices for day d. Lanes = paths x kinds."""
    Pn = idx_rows(0).shape[0] // len(kinds); R = len(kinds); N = Pn * R
    kind = torch.tensor([{"vti": 0, "6040": 1, "tdf": 2}[k] for k in kinds], device=DEV).repeat(Pn)
    egg = profile["spending"] / 0.04; v = torch.full((N,), float(profile["value"]), device=DEV); infl = torch.ones(N, device=DEV)
    w_st = torch.where(kind == 0, 1.0, 0.6).float(); wcur = w_st.clone(); nav = torch.ones(N, device=DEV); peak = torch.ones(N, device=DEV)
    retired = torch.full((N,), bool(profile.get("already_retired", False)), device=DEV); goal = torch.where(retired, 0, -1).to(DEV)
    dead = torch.zeros(N, dtype=torch.bool, device=DEV); low = torch.full((N,), 1e9, device=DEV); mdd = torch.zeros(N, device=DEV)
    for d in range(L):
        rows = idx_rows(d)
        if lane_end is not None: dead = dead | (d > lane_end)                 # history exhausted: freeze lane (not a failure)
        if d > 0:
            rs, rb = STK[rows], BND[rows]; rr = wcur * rs + (1 - wcur) * rb
            wcur = wcur * (1 + rs) / (1 + rr); live = ~dead; v = torch.where(live, v * (1 + rr), v); nav = torch.where(live, nav * (1 + rr), nav)
            infl = infl * lb.CPIR[rows]
        peak = torch.maximum(peak, nav); mdd = torch.where(~dead, torch.maximum(mdd, (1 - nav / peak) * 100), mdd)
        if d % 21 == 0:
            age = profile["age"] + d / 252
            flow = torch.where(retired, -egg * 0.04 / 12 * infl, profile["contrib"] / 12 * infl)
            if d > 0: v = torch.where(~dead, v + flow, v)
            dead |= v <= 0; v = v.clamp(min=0); funded = v / infl / egg
            newly = ~dead & ~retired & (funded >= 1); goal = torch.where(newly, torch.full_like(goal, d), goal); retired |= newly
            low = torch.where(~dead & retired, torch.minimum(low, funded), low)
            tdf = torch.full((N,), min(0.9, max(0.3, (110 - age) / 100)), device=DEV)
            target = torch.where(kind == 2, tdf, w_st)
            if d % 252 == 0: wcur = target                                    # yearly rebalance (TDF glides yearly)
    sh = lambda z: z.view(Pn, R).cpu().numpy()
    ytg = torch.where(goal >= 0, goal.float() / 252, torch.full((N,), float("nan"), device=DEV))
    failed = (v <= 0) if lane_end is None else (v <= 0)                       # ran out = money gone, not history ended
    return dict(ytg=sh(ytg), dead=sh(failed), low=sh(low), mdd=sh(mdd))

def summarize(label, y, dead, low, mdd, span=None):
    c = np.where(np.isnan(y), (span if span is not None else 41) + 1, y); lo = low[low < 1e8]
    return dict(label=label, median=float(np.median(c)), p75=float(np.percentile(c, 75)), never=float(np.isnan(y).mean() * 100),
                ran_out=float(dead.mean() * 100), low_p5=float(np.percentile(lo, 5) * 100) if len(lo) else float("nan"), worst_dd=float(np.percentile(mdd, 99)))

if __name__ == "__main__":
    profs = dict(lg.PROFILES); profs["Retired 60y $300k, 4%"] = dict(age=60, value=300000, contrib=0, retire_age=60, spending=12000, already_retired=True)
    starts = [i for i in range(len(pl.DATES)) if (i == 0 or (pl.DATES[i][5:7] in ("01", "04", "07", "10") and pl.DATES[i][:7] != pl.DATES[i - 1][:7])) and pl.DATES[i] < "2017"]
    g = np.random.default_rng(21); lb.L = 40 * 252; IDX = lb.make_index(2000, g)
    kinds = ["vti", "6040", "tdf"]; rule = tuple(pl.RULE[k] for k in ("BASE", "SLOPE", "CAP", "RET"))
    out = {}
    for name, prof in profs.items():
        print(f"\n{name}")
        print(f"   {'approach':24} | HISTORY 1972-2016 starts: yrs to goal med/p75  ran-out  p5 low-real  p99 DD | 2000 SYNTHETIC: med/p75 yrs  never  ran-out  p5 low-real  p99 DD")
        # historical starts: lanes = starts x kinds; rows = start + d (clipped)
        S = torch.tensor(starts, device=DEV); Lh = 40 * 252
        lane_end = (lg.T - 1 - S).repeat_interleave(len(kinds))
        hist = sim_simple(prof, kinds, lambda d: (S.repeat_interleave(len(kinds)) + d).clamp(max=lg.T - 1), Lh, lane_end)
        boot = sim_simple(prof, kinds, lambda d: IDX[:, d].repeat_interleave(len(kinds)), lb.L)
        span = np.array([(lg.T - 1 - s) / 252 for s in starts])
        P = {k: torch.tensor([v], device=DEV, dtype=f32) for k, v in zip(("BASE", "SLOPE", "CAP", "RET", "F0"), rule + (1.0,))}
        mh = lg.run(prof, P, starts, years=40); mb = lb.run(prof, [rule], IDX)
        rows = []
        for j, k in enumerate(kinds):
            rows.append((k, summarize(k, hist["ytg"][:, j], hist["dead"][:, j], hist["low"][:, j], hist["mdd"][:, j], span),
                         summarize(k, boot["ytg"][:, j], boot["dead"][:, j], boot["low"][:, j], boot["mdd"][:, j])))
        rows.append(("OUR POLICY", summarize("policy", mh["ytg"][:, 0].cpu().numpy(), mh["dead"][:, 0].cpu().numpy(), mh["low_after"][:, 0].cpu().numpy(), mh["mdd"][:, 0].cpu().numpy(), span),
                     summarize("policy", mb["ytg"][:, 0], mb["dead"][:, 0], mb["low_after"][:, 0], mb["mdd"][:, 0])))
        lab = {"vti": "100% stocks (VTI)", "6040": "60/40 VTI/BND", "tdf": "target-date (110-age)", "OUR POLICY": "OUR POLICY"}
        for k, h_, b_ in rows:
            print(f"   {lab[k]:24} | {h_['median']:10.1f}/{h_['p75']:<5.1f} {h_['ran_out']:7.1f}% {h_['low_p5']:9.0f}% {h_['worst_dd']:7.1f}% | "
                  f"{b_['median']:6.1f}/{b_['p75']:<5.1f} {b_['never']:6.1f}% {b_['ran_out']:6.1f}% {b_['low_p5']:9.0f}% {b_['worst_dd']:6.1f}%")
            out.setdefault(name, {})[lab[k]] = dict(history=h_, synthetic=b_)
    json.dump(out, open(os.path.join(pl.ROOT, "benchmark_life.json"), "w"), indent=1)
