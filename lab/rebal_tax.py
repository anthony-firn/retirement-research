"""Rebalancing rules with tax-lot tracking in a TAXABLE account (1972-2026 local data, $1 start, no cash flows).
Lots per fund, sales use HIFO (highest cost first), gains held > 1 year = long-term. Taxes on each year's net ST / LT gains
(losses offset within the year and carry forward) are paid out of the portfolio at year-end. Fund distributions are not modelled
(same for every rule). Tax cases: 'low' = the retiree's likely case (fed LTCG 0%, ST 12%, CA 2%), 'mid' = fed LTCG 15%, ST 22%, CA 6%."""
import os, sys, json, numpy as np
src = open("rebal_test.py").read(); exec(src[:src.index("S = [(")])
DAYS = np.array([d.toordinal() for d in D])
TAX = {"none": (0, 0, 0), "low": (0.00, 0.12, 0.02), "mid": (0.15, 0.22, 0.06)}
def run_tax(trigger, tax):
    lt_r, st_r, ca = TAX[tax]; px = np.ones(len(names)); w = W0.copy(); V = 1.0
    lots = [[(W0[a] / px[a], px[a], DAYS[0])] for a in range(len(names))]        # (units, cost per unit, buy day)
    out = np.zeros(T); n = 0; yST = yLT = 0.0; carry = 0.0; taxes_paid = 0.0; last = 0
    for d in range(1, T):
        px = px * (1 + R[d]); g = w * (1 + R[d]); pr = g.sum(); V *= pr; w = g / pr; out[d] = pr - 1
        if trigger(d, w, last):
            n += 1; last = d; tgt = W0 * V; cur = w * V
            for a in range(len(names)):
                diff = tgt[a] - cur[a]
                if diff < 0:                                                       # sell -diff dollars, HIFO
                    units = -diff / px[a]; lots[a].sort(key=lambda L: -L[1]); new = []
                    for (u, c, b) in lots[a]:
                        if units <= 1e-15: new.append((u, c, b)); continue
                        take = min(u, units); gain = take * (px[a] - c)
                        if DAYS[d] - b > 365: yLT += gain
                        else: yST += gain
                        units -= take
                        if u - take > 1e-15: new.append((u - take, c, b))
                    lots[a] = new
                elif diff > 0: lots[a].append((diff / px[a], px[a], DAYS[d]))
            cost = COST * np.abs(tgt - cur).sum(); V *= 1 - cost / V; out[d] = (1 + out[d]) * (1 - cost / (V + cost)) - 1; w = W0.copy()
        if d == T - 1 or Y[d + 1] != Y[d]:                                         # year-end tax bill
            st = yST; lt = yLT
            net = st + lt + carry
            if net <= 0: carry = net; taxbill = 0.0
            else:
                carry = 0.0
                # losses offset short-term first, then long-term (simplified)
                if st + lt > net:                                                  # carryforward used
                    lt = max(0.0, lt + min(0.0, st + carry) if st + carry < 0 else lt); st = max(0.0, st + carry) if st + carry >= 0 else 0.0
                if st < 0: lt += st; st = 0.0
                if lt < 0: st += lt; lt = 0.0
                taxbill = max(st, 0) * (st_r + ca) + max(lt, 0) * (lt_r + ca)
            if taxbill > 0:
                taxes_paid += taxbill; frac = taxbill / V; V -= taxbill; out[d] = (1 + out[d]) * (1 - frac) - 1
            yST = yLT = 0.0
    return out, n, taxes_paid
YE = lambda d: newm[d] and M[d] == 1
VALVE = lambda w: ((w - W0) / W0).max() >= 1.0
RULES = {
 "buy & hold (never)": lambda d, w, l: False,
 "yearly Jan": lambda d, w, l: YE(d),
 "yearly Jan + 2x valve (current)": lambda d, w, l: YE(d) or VALVE(w),
 "every 2 yrs (even Jan)": lambda d, w, l: YE(d) and Y[d] % 2 == 0,
 "every 2 yrs (odd Jan)": lambda d, w, l: YE(d) and Y[d] % 2 == 1,
 "every 2 yrs (even) + 2x valve": lambda d, w, l: (YE(d) and Y[d] % 2 == 0) or VALVE(w),
 "every 2 yrs (odd) + 2x valve": lambda d, w, l: (YE(d) and Y[d] % 2 == 1) or VALVE(w),
 "drift only: abs ±5pp": lambda d, w, l: np.abs(w - W0).max() * 100 > 5,
 "drift only: abs ±6pp OR 2x valve": lambda d, w, l: np.abs(w - W0).max() * 100 > 6 or VALVE(w),
 "drift only: rel ±60%": lambda d, w, l: (np.abs(w - W0) / W0).max() * 100 > 60,
 "drift only: rel ±75%": lambda d, w, l: (np.abs(w - W0) / W0).max() * 100 > 75,
 "drift, min 1y apart: abs ±5pp OR 2x valve": lambda d, w, l: VALVE(w) or (np.abs(w - W0).max() * 100 > 5 and DAYS[d] - DAYS[l] > 365),
}
print(f"{'rule':42} | pre-tax: CAGR   MDD  Sharpe | rebal/yr  avg gap | after-tax CAGR (taxable): the retiree's case  middle | 5y>20%")
res = []
for name, trig in RULES.items():
    r0, n, _ = run_tax(trig, "none"); f = met(r0)
    nav = np.cumprod(1 + r0[IDX], 1); p20 = np.mean((1 - nav / np.maximum.accumulate(nav, 1)).max(1) > 0.2) * 100
    rl, _, tl = run_tax(trig, "low"); rm, _, tm = run_tax(trig, "mid"); cl = met(rl)[0]; cm = met(rm)[0]; yrs = T / 252
    gap = yrs / n if n else float("nan")
    print(f"{name:42} | {f[0]:6.2f} {f[1]:5.1f} {f[2]:6.3f} | {n/yrs:5.2f}   {gap:5.1f}y  |                {cl:6.2f}   {cm:6.2f} | {p20:4.0f}%", flush=True)
    res.append(dict(rule=name, cagr=f[0], mdd=f[1], sharpe=f[2], per_year=n / yrs, after_tax_low=cl, after_tax_mid=cm, p20=p20))
json.dump(res, open("rebal_tax.json", "w"), indent=1)
