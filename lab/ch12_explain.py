"""Why CH-12 works: component stats, correlations, crisis behaviour, risk contributions, leave-one-out (1972-2026 local data,
testfol SIMs with proxies only before each fund's SIM starts)."""
import os, sys, json, numpy as np, datetime as dt
sys.path.insert(0, "../strategy"); os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import b40_risk as br, history70s as h
P = json.load(open("../results/portfolios.json")); A = P["CH-12"]["alloc"]; names = list(A)
comp = {n: (br.SUB[n] if n in br.SUB else h.rets(h.series(n))) for n in names}; comp["VTISIM"] = h.rets(h.series("VTISIM"))
ts = lambda s: int(np.searchsorted(h.CAL, int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.UTC).timestamp())))
def stats(r):
    v = np.cumprod(1 + r); y = len(r) / 252; c = (v[-1] ** (1 / y) - 1) * 100; m = (1 - v / np.maximum.accumulate(v)).max() * 100
    ex = r - h.rf; return c, r.std() * np.sqrt(252) * 100, m, ex.mean() / ex.std() * np.sqrt(252)
EP = [("73-74 stagfl", "1973-01-11", "1974-10-03"), ("79-81 Volcker", "1979-01-02", "1981-09-25"), ("1987 crash", "1987-08-25", "1987-12-04"),
      ("00-02 dot-com", "2000-03-24", "2002-10-09"), ("07-09 GFC", "2007-10-09", "2009-03-09"), ("2020 Covid", "2020-02-19", "2020-03-23"), ("2022 rates", "2022-01-03", "2022-10-14")]
def ep(r, a, b): v = np.cumprod(1 + r); return (v[ts(b)] / v[ts(a)] - 1) * 100
port = h.blend_series(A, br.SUB)
print("Component (weight)   CAGR   vol   maxDD Sharpe | corr VTI corr port | " + " ".join(f"{e[0]:>13}" for e in EP))
for n in names + ["VTISIM"]:
    r = comp[n]; c, vol, m, sh = stats(r); w = A.get(n, 0)
    print(f"{n.replace('SIM',''):6} ({w:2d}%)        {c:5.1f} {vol:5.1f} {m:6.1f} {sh:5.2f}  | {np.corrcoef(r, comp['VTISIM'])[0,1]:+.2f}     {np.corrcoef(r, port)[0,1]:+.2f}     | " + " ".join(f"{ep(r, a, b):+13.1f}" for _, a, b in EP))
c, vol, m, sh = stats(port); print(f"CH-12 portfolio     {c:5.1f} {vol:5.1f} {m:6.1f} {sh:5.2f}  |                   | " + " ".join(f"{ep(port, a, b):+13.1f}" for _, a, b in EP))
# rebalancing bonus: portfolio CAGR vs weighted avg of component CAGRs
wavg = sum(A[n] / 100 * stats(comp[n])[0] for n in names); print(f"\nWeighted average of component CAGRs {wavg:.2f}% vs portfolio {c:.2f}%  (rebalancing / diversification bonus {c - wavg:+.2f}%/yr)")
# risk contributions (daily covariance)
R = np.stack([comp[n] for n in names], 1); w = np.array([A[n] / 100 for n in names]); S = np.cov(R.T); pv = w @ S @ w; rc = w * (S @ w) / pv * 100
print("Share of portfolio risk: " + "  ".join(f"{n.replace('SIM','')} {x:.0f}%" for n, x in zip(names, rc)))
grp = {"Trend (KMLM+DBMF)": ["KMLMSIM", "DBMFSIM"], "Stocks (VBR+XLV+TQQQ)": ["VBRSIM", "XLVSIM", "TQQQSIM"], "Treasuries (TYD)": ["TYDSIM"], "Gold+dollar (GLD+UUP)": ["GLDSIM", "UUPSIM"]}
print("By sleeve:  " + "  ".join(f"{g}: weight {sum(A[x] for x in xs)}% / risk {sum(rc[names.index(x)] for x in xs):.0f}%" for g, xs in grp.items()))
# correlation of sleeves in stock selloffs
v = comp["VTISIM"]; bad = v < np.percentile(v, 5)
print("Average daily return on VTI's worst 5% of days: " + "  ".join(f"{n.replace('SIM','')} {comp[n][bad].mean()*100:+.2f}%" for n in names) + f"  VTI {v[bad].mean()*100:+.2f}%  CH-12 {port[bad].mean()*100:+.2f}%")
# leave-one-out
print("\nLeave one out (weights rescaled):   CAGR   maxDD  Sharpe  2022  73-74")
for n in [None] + names:
    a = {k: x for k, x in A.items() if k != n}; r = h.blend_series(a, br.SUB); c2, _, m2, s2 = stats(r)
    print(f"  {'(none - CH-12)' if n is None else 'without ' + n.replace('SIM',''):22} {c2:6.2f} {m2:6.1f}  {s2:5.2f}  {ep(r,'2022-01-03','2022-10-14'):+5.1f} {ep(r,'1973-01-11','1974-10-03'):+6.1f}")
