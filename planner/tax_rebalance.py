"""Tax-aware rebalancing in a TAXABLE account: component-level simulation with average-cost basis.
Daily testfol.io SIM series of each ETF (lab/hist_long.json), 1988-2026. Capital-gains tax (LTCG + state)
on net realised gains each year, losses carried forward. Dividends/interest are inside the total-return series
and identical across methods, so they are left out of the comparison.
Methods: annual | band5 | band10 | cashflow (contributions to underweights, sell only past 10-pt band) | band10+TLH.
Usage: python3 tax_rebalance.py [portfolio names...]"""
import json, os, sys, numpy as np, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(ROOT, "..", "lab", "hist_long.json"))); PF = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
TAX = float(os.environ.get("CG_TAX", "0.20"))                     # 15% federal LTCG + 5% state
START = int(dt.datetime(1987, 12, 31, tzinfo=dt.UTC).timestamp())

def prices(alloc):
    names = list(alloc); t = np.array(H[names[0]]["t"]); t = t[t >= START]
    for n in names[1:]: tt = np.array(H[n]["t"]); t = np.intersect1d(t, tt[tt >= START])
    P = np.stack([np.array(H[n]["v"])[np.searchsorted(H[n]["t"], t)] for n in names], 1)
    return names, t, P

def run(alloc, method, contrib=0.0, start=100000.0):
    names, t, P = prices(alloc); w = np.array([alloc[n] for n in names], float) / 100
    years = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in t]); months = np.array([dt.datetime.fromtimestamp(x, dt.UTC).month for x in t])
    sh = start * w / P[0]; basis = start * w.copy(); carry = 0.0; tax_paid = 0.0; realised_y = 0.0; drift = []; peak = start; mdd = 0.0; flows = start
    for d in range(1, len(t)):
        val = sh * P[d]; tot = val.sum(); cw = val / tot
        newmonth = months[d] != months[d - 1]; newyear = years[d] != years[d - 1]
        if newmonth and contrib:                                  # monthly contribution
            c = contrib / 12
            if method == "cashflow":
                gap = np.clip(w * (tot + c) - val, 0, None); alloc_c = c * gap / gap.sum() if gap.sum() > 0 else c * w
            else: alloc_c = c * w
            sh += alloc_c / P[d]; basis += alloc_c; val = sh * P[d]; tot = val.sum(); cw = val / tot
        trade = None
        if method == "annual" and newyear: trade = w * tot
        elif method in ("band5", "band10", "band10+TLH", "cashflow") and newmonth:
            band = 0.05 if method == "band5" else 0.10
            if (np.abs(cw - w) > band).any(): trade = w * tot
        if method == "band10+TLH" and newmonth:                   # harvest losses: lots >=15% below cost
            loss = (val < 0.85 * basis) & (val > 0)
            if loss.any():
                realised_y += (val[loss] - basis[loss]).sum(); basis[loss] = val[loss]   # sell & buy a similar fund: basis resets
        if trade is not None:
            sell = np.clip(val - trade, 0, None)                  # sell overweights
            frac = np.where(val > 0, sell / val, 0); realised_y += (sell - basis * frac).sum(); basis = basis * (1 - frac)
            buy = np.clip(trade - val, 0, None); basis += buy; sh = trade / P[d]
        drift.append(np.abs(cw - w).sum() / 2)
        if not contrib: peak = max(peak, tot); mdd = max(mdd, 1 - tot / peak)
        if newyear:                                               # pay last year's capital-gains tax from the account
            net = realised_y + carry
            if net > 0: tax = net * TAX; carry = 0.0
            else: tax = 0.0; carry = net
            tax_paid += tax; realised_y = 0.0
            if tax:
                val = sh * P[d]; sell = tax * val / val.sum(); frac = sell / val; realised_y += (sell - basis * frac).sum(); basis *= (1 - frac); sh *= (1 - frac)   # selling to pay tax also realises gains
    val = sh * P[-1]; tot = val.sum(); unreal = max(tot - basis.sum(), 0)
    yrs = (t[-1] - t[0]) / 86400 / 365.25; invested = start + contrib * yrs
    return dict(end=tot, after_liq=tot - unreal * TAX, tax_paid=tax_paid, drift=float(np.mean(drift)) * 100, years=yrs, mdd=mdd * 100,
                cagr=((tot / start) ** (1 / yrs) - 1) * 100 if not contrib else None)

def notax(alloc, start=100000.0):
    names, t, P = prices(alloc); w = np.array([alloc[n] for n in names], float) / 100
    years = np.array([dt.datetime.fromtimestamp(x, dt.UTC).year for x in t]); sh = start * w / P[0]
    for d in range(1, len(t)):
        if years[d] != years[d - 1]: tot = (sh * P[d]).sum(); sh = w * tot / P[d]
    return (sh * P[-1]).sum()

if __name__ == "__main__":
    names = sys.argv[1:] or ["S12+", "Simple-6.8", "C1-Now"]
    print(f"Taxable account, $100k start, 1988-2026, capital-gains tax {TAX*100:.0f}% on net realised gains (losses carried forward)")
    out = {}
    for n in names:
        a = PF[n]["alloc"]; nt = notax(a)
        print(f"\n{n}: {', '.join(f'{k.replace(chr(83)+chr(73)+chr(77),'')} {v}' for k, v in a.items())}   (no-tax annual rebalance ends at ${nt:,.0f})")
        print(f"   {'method':11} | end value  | after-tax if sold | tax paid  | avg drift | max DD | cost of taxes vs no-tax")
        for m in ("annual", "band5", "band10", "cashflow", "band10+TLH"):
            r = run(a, m); cost = (1 - r["after_liq"] / nt) * 100; out.setdefault(n, {})[m] = dict(r, cost_vs_notax=cost)
            print(f"   {m:11} | ${r['end']:>9,.0f} | ${r['after_liq']:>14,.0f} | ${r['tax_paid']:>7,.0f} | {r['drift']:6.1f}%   | {r['mdd']:5.1f}% | {cost:5.1f}%")
        print("   with $12k/yr contributions:")
        for m in ("annual", "band10", "cashflow"):
            r = run(a, m, contrib=12000); out[n][m + "+contrib"] = r
            print(f"   {m:11} | ${r['end']:>9,.0f} | ${r['after_liq']:>14,.0f} | ${r['tax_paid']:>7,.0f} | {r['drift']:6.1f}%")
    json.dump(out, open(os.path.join(ROOT, "tax_rebalance.json"), "w"), indent=1, default=float)
