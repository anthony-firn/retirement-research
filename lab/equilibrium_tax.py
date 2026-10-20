"""Equilibrium income for Crisis-Hedged 12 with a per-fund tax model (taxable account), GPU, 40 years, bootstrap of 1972-2026.
Tax model (assumptions, see CRISIS_HEDGED_12.md):
- Distributions (reinvested, add to basis, taxed every year-end on the year-end value): VBR 2.0% and XLV 1.6% qualified dividends;
  DBMF 2.5%, KMLM 2.5%, TYD 2.0%, TQQQ 1.0% ordinary income (KMLM 2022-24 paid ~2-2.5%/yr, mostly ordinary; return of capital ignored).
- Sales: average-cost basis per fund; short-term share = fraction of the position bought within the last year; GLD gains = collectibles
  (ordinary rate, no 0% bracket); UUP = commodity pool, marked to market every year-end 60% long / 40% short.
- Net capital gains/losses netted each year, losses carried forward; tax paid from the portfolio at year-end.
- California taxes everything as ordinary income. Brackets are flat marginal rates per scenario (0% LTCG room assumed sufficient).
Income figures are after tax (spendable): withdrawals are what the retiree spends; taxes come out of the account separately."""
import os, sys, json, numpy as np, torch
os.environ.setdefault("YEARS", "40"); os.environ.setdefault("PATHS", "2000")
exec(open("equilibrium_gpu.py").read().split("if __name__")[0])
nm = [n.replace("SIM", "") for n in names]
DIVY = torch.tensor([{"VBR": .020, "XLV": .016, "DBMF": .025, "KMLM": .025, "TYD": .020, "TQQQ": .010}.get(n, 0.0) for n in nm], device=DEV)
QUAL = torch.tensor([n in ("VBR", "XLV") for n in nm], device=DEV)
COLL = torch.tensor([n == "GLD" for n in nm], device=DEV); MTM = torch.tensor([n == "UUP" for n in nm], device=DEV); NORM = ~(COLL | MTM)
SCEN = {"IRA / Roth (no tax)": dict(ord=0, lt=0, coll=0, ca=0), "retiree, not working": dict(ord=.10, lt=0, coll=.10, ca=.02),
        "retiree, working $40k": dict(ord=.12, lt=0, coll=.12, ca=.05), "middle bracket (22%/15%, CA 9.3%)": dict(ord=.22, lt=.15, coll=.22, ca=.093)}
def simulate_tax(rules, rates, IDX, tx, skim=None):
    C, K, P = len(rules), len(rates), IDX.shape[0]; N = C * K * P; A = len(nm)
    ci = torch.arange(C, device=DEV).repeat_interleave(K * P); ki = torch.arange(K, device=DEV).repeat_interleave(P).repeat(C); pi = torch.arange(P, device=DEV).repeat(C * K)
    X = torch.tensor([r.get("band", 1e9) for r in rules], device=DEV, dtype=f32)[ci]; G = torch.tensor([r.get("gap", 0) for r in rules], device=DEV)[ci]
    VM = torch.tensor([r.get("valve", 1e9) for r in rules], device=DEV, dtype=f32)[ci]; YR = torch.tensor([bool(r.get("yearly", False)) for r in rules], device=DEV)[ci]
    rate = torch.tensor(rates, device=DEV, dtype=f32)[ki] / 100
    ro, rl, rc, ca = tx["ord"] + tx["ca"], tx["lt"] + tx["ca"], tx["coll"] + tx["ca"], tx["ca"]; rm = 0.6 * tx["lt"] + 0.4 * tx["ord"] + tx["ca"]
    val = W0g.repeat(N, 1).clone(); basis = val.clone(); lastb = torch.zeros(N, A, device=DEV); bfrac = torch.ones(N, A, device=DEV)
    last = torch.zeros(N, dtype=torch.long, device=DEV); infl = torch.ones(N, device=DEV); minreal = torch.ones(N, device=DEV); dead = torch.zeros(N, dtype=torch.bool, device=DEV)
    gST = torch.zeros(N, device=DEV); gLT = torch.zeros(N, device=DEV); gC = torch.zeros(N, device=DEV); gM = torch.zeros(N, device=DEV); carry = torch.zeros(N, device=DEV)
    taxreal = torch.zeros(N, device=DEV); inc = torch.zeros(N, YEARS, device=DEV); yi = 0
    def realize(sell, d):
        nonlocal basis, gST, gLT, gC, gM
        frac = (sell / val.clamp(min=1e-12)).clamp(0, 1); g = sell - basis * frac; basis = basis * (1 - frac)
        stf = torch.where((d - lastb) < 252, bfrac, torch.zeros_like(bfrac))
        gST += (g * stf * NORM).sum(1); gLT += (g * (1 - stf) * NORM).sum(1); gC += (g * COLL).sum(1); gM += (g * MTM).sum(1)
    for d in range(1, L):
        rows = IDX[pi, d]; val = val * (1 + Rg[rows]); infl = infl * Cg[rows]; V = val.sum(1)
        if d % 21 == 0:
            amt = (rate / 12 * infl).clamp(max=V.clamp(min=0)); tgt = W0g * V[:, None]; exc = (val - tgt).clamp(min=0); se = exc.sum(1)
            te = torch.minimum(amt, se); rest = amt - te; s1 = exc * (te / se.clamp(min=1e-12))[:, None]
            sell = s1 + (val - s1) * (rest / (V - te).clamp(min=1e-12))[:, None]
            realize(sell, d); val = val - sell; inc[:, min(yi, YEARS - 1)] += sell.sum(1) / infl; V = val.sum(1); dead |= V <= 1e-6
        w = val / V.clamp(min=1e-12)[:, None]; since = d - last
        trig = ((((w - W0g).abs().max(1).values * 100 > X) & (since > G)) | ((w / W0g).max(1).values >= VM) | (YR & (since >= 252))) & ~dead
        if trig.any():
            tgt = W0g * V[:, None]; over = (val > tgt) & trig[:, None]; under = (val < tgt) & trig[:, None]
            realize(torch.where(over, val - tgt, torch.zeros_like(val)), d)
            buy = torch.where(under, tgt - val, torch.zeros_like(val)); basis = basis + buy
            bfrac = torch.where(under, buy / tgt.clamp(min=1e-12), bfrac); lastb = torch.where(under, torch.full_like(lastb, float(d)), lastb)
            cost = (COST * (tgt - val).abs().sum(1)) * trig; val = torch.where(trig[:, None], tgt * (1 - cost / V.clamp(min=1e-12))[:, None], val)
            last = torch.where(trig, torch.full_like(last, d), last)
        if d % 252 == 251:
            dist = val * DIVY; basis = basis + dist                                         # reinvested distributions
            divq = (dist * QUAL).sum(1); divo = (dist * ~QUAL).sum(1)
            mg = ((val - basis) * MTM).sum(1); gM += mg; basis = torch.where(MTM, val, basis)  # UUP mark-to-market
            pos = [gST.clamp(min=0), gLT.clamp(min=0), gC.clamp(min=0), gM.clamp(min=0)]; rts = [ro, rl, rc, rm]
            net = gST + gLT + gC + gM + carry; psum = sum(pos); wr = sum(p * r for p, r in zip(pos, rts)) / psum.clamp(min=1e-12)
            tax = torch.where(net > 0, net * wr, torch.zeros_like(net)) + divq * rl + divo * ro; carry = net.clamp(max=0)
            gST.zero_(); gLT.zero_(); gC.zero_(); gM.zero_()
            if skim is not None:
                V = val.sum(1); bonus = ((V / infl - (1 + skim)).clamp(min=0) * infl).clamp(max=V); realize(val * (bonus / V.clamp(min=1e-12))[:, None], d + 0)
                val = val * (1 - bonus / V.clamp(min=1e-12))[:, None]; inc[:, min(yi, YEARS - 1)] += bonus / infl
            V = val.sum(1); f = (tax / V.clamp(min=1e-12)).clamp(0, 1); val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]; taxreal += tax / infl; yi += 1
        minreal = torch.minimum(minreal, val.sum(1) / infl)
    sh = (C, K, P)
    return dict(real_end=(val.sum(1) / infl).view(sh).cpu().numpy(), minreal=minreal.view(sh).cpu().numpy(), dead=dead.view(sh).float().mean(2).cpu().numpy(),
                tax=(taxreal / YEARS).view(sh).cpu().numpy(), inc=inc.view(C, K, P, YEARS).cpu().numpy())
RULE = dict(name="band ±6pp, min 1y, valve 2x", band=6, gap=252, valve=2.0); CUR = dict(name="yearly + 2x valve", yearly=True, valve=2.0)
rates = [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9]; IDX = make_idx(11); res = {}
print(f"Crisis-Hedged 12, {YEARS} years, {IDX.shape[0]} reshuffled histories. Income is AFTER tax (what the retiree can spend), inflation-adjusted, % of the starting value per year.\n")
print(f"{'tax situation':36} {'rule':28} | fixed income keeping real value: 90%   75%   50% | avg tax/yr (at 5%) | skim plan 4% + above 125%: avg income p10 / median, real end p10")
for sname, tx in SCEN.items():
    r = simulate_tax([RULE, CUR], rates, IDX, tx); k5 = rates.index(5)
    for c, ru in enumerate([RULE, CUR]):
        q = {p: eq_rate(rates, [np.percentile(r["real_end"][c, k], 100 - p) for k in range(len(rates))]) for p in (90, 75, 50)}
        line = f"{sname:36} {ru['name']:28} |                               {q[90]:5.2f}% {q[75]:5.2f}% {q[50]:5.2f}% |      {np.median(r['tax'][c, k5])*100:4.2f}%       |"
        if c == 0:
            s = simulate_tax([RULE], [4.0], IDX, tx, skim=0.25); inc = s["inc"][0, 0][:, 1:].mean(1) * 100; re = s["real_end"][0, 0]
            line += f"  {np.percentile(inc, 10):5.2f}% / {np.median(inc):5.2f}%, {np.percentile(re, 10):4.2f}"
            res[sname] = dict(eq=q, skim_p10=float(np.percentile(inc, 10)), skim_med=float(np.median(inc)), skim_end_p10=float(np.percentile(re, 10)), tax=float(np.median(r["tax"][c, k5])))
        print(line, flush=True)
json.dump(res, open("equilibrium_tax.json", "w"), indent=1)
