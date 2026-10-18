"""Retiree withdrawal rules under harsh synthetic histories (block bootstrap from 1972-2026 incl. the 1970s).
Portfolio: the policy at the retiree budget (tier + breaker). Each rule sets the monthly withdrawal:
  fixed X%        : X% of the starting value, inflation-indexed, never changed
  guardrail       : start at X%; if real value < 80% of start cut spending 10% (< 60%: 20%); restore when back >= 100%
  floor-ceiling   : X% of current real value, but never below 85% / above 120% of the planned real amount
Reports: ran out %, p5 lowest real value, average real spending as % of planned, worst year of spending cut."""
import os, json, numpy as np, torch
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import life_gpu as lg, life_boot as lb, policy as pl

DEV = lg.DEV; K = lg.K
def run(IDX, rule, rate, years=40, value=300000.0, budget=None):
    budget = budget or pl.RULE["RET"]; Pn = IDX.shape[0]; L = years * 252
    v = torch.full((Pn,), value, device=DEV); nav = torch.ones(Pn, device=DEV); peak = torch.ones(Pn, device=DEV); infl = torch.ones(Pn, device=DEV)
    x = torch.zeros(Pn, device=DEV); dead = torch.zeros(Pn, dtype=torch.bool, device=DEV); low = torch.full((Pn,), 1.0, device=DEV)
    adj = torch.ones(Pn, device=DEV); spent = torch.zeros(Pn, device=DEV); months = 0; min_adj = torch.ones(Pn, device=DEV)
    base = value * rate / 12; b = torch.full((Pn,), float(budget), device=DEV); cap_x = lg.x_of_budget(b)
    for d in range(L):
        rows = IDX[:, d]
        if d > 0:
            lo = x.floor().long().clamp(0, K - 1); hi = (lo + 1).clamp(max=K - 1); f = x - lo.float()
            r = (1 - f) * lg.RET[rows, lo] + f * lg.RET[rows, hi]; live = ~dead
            v = torch.where(live, v * (1 + r), v); nav = torch.where(live, nav * (1 + r), nav); infl = infl * lb.CPIR[rows]
        peak = torch.maximum(peak, nav); dd = (1 - nav / peak) * 100
        if d % 21 == 0 and d > 0:
            real = v / infl / value
            if rule == "guardrail":
                adj = torch.where(real < 0.6, torch.full_like(adj, 0.8), torch.where(real < 0.8, torch.minimum(adj, torch.full_like(adj, 0.9)), torch.where(real >= 1.0, torch.ones_like(adj), adj)))
                w = base * adj * infl
            elif rule == "floor-ceiling":
                w = (v * rate / 12).clamp(min=0.85 * base * infl, max=1.2 * base * infl); adj = w / (base * infl)
            else: w = base * infl
            v = torch.where(~dead, v - w, v); spent += torch.where(~dead, adj, torch.zeros_like(adj)); months += 1
            min_adj = torch.minimum(min_adj, adj); dead |= v <= 0; v = v.clamp(min=0); low = torch.where(~dead, torch.minimum(low, v / infl / value), low)
        cushion = (b - pl.MARGIN_GAP - dd).clamp(min=0)
        gov = torch.where(cushion > lg.WD[0], lg.interp_pos(lg.WD, cushion), torch.zeros_like(cushion)); new = torch.minimum(cap_x, gov)
        move = (new - x).abs() > 0.02; cost = torch.where(move & ~dead, pl.COST * (new - x).abs(), torch.zeros_like(x)); v = v * (1 - cost); nav = nav * (1 - cost)
        x = torch.where(move | (d == 0), new, x)
    return dict(dead=dead.float().mean().item() * 100, low_p5=np.percentile(low.cpu().numpy(), 5) * 100,
                spend=(spent / months).mean().item() * 100, deepest_cut=(1 - min_adj).max().item() * 100)

if __name__ == "__main__":
    g = np.random.default_rng(11); lb.L = 40 * 252; IDX = lb.make_index(2000, g)
    print(f"Retiree, $300k, 40 years, policy at retiree budget {pl.RULE['RET']:.0f}%, 2000 bootstrapped histories from {pl.DATES[0][:4]}-2026")
    print(f"   {'rule':26} | ran out | p5 lowest real value | avg real spending vs plan | deepest cut")
    out = {}
    for rule, rate in [("fixed", 0.04), ("fixed", 0.035), ("fixed", 0.03), ("guardrail", 0.04), ("guardrail", 0.045), ("floor-ceiling", 0.04), ("floor-ceiling", 0.045)]:
        m = run(IDX, rule, rate); key = f"{rule} {rate*100:.1f}%"; out[key] = m
        print(f"   {key:26} | {m['dead']:5.1f}%  | {m['low_p5']:8.0f}%            | {m['spend']:8.1f}%                | {m['deepest_cut']:4.0f}%")
    json.dump(out, open(os.path.join(pl.ROOT, "withdraw_rules.json"), "w"), indent=1)
