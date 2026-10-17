"""Break down why a portfolio works (local simulator, validated against testfol.io).
Usage: HIST=clean_X.json python3 analyze_portfolio.py C1 [FULL#1]"""
import os, sys, json, numpy as np, datetime as dt
os.environ.setdefault("HIST", "clean_X.json")
from simn import NAMES, P, RF, t, years, values, metrics, w_of

PF = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "portfolios.json")))
name = sys.argv[1] if len(sys.argv) > 1 else "C1"; ref = sys.argv[2] if len(sys.argv) > 2 else "FULL#1"
X = PF[name]["alloc"]; R = PF[ref]["alloc"]
lbl = lambda n: n.replace("SIM", "")
f = lambda a, idx=None: {k: float(v[0]) for k, v in metrics(values(w_of(a), idx), idx).items()}
fmt = lambda m: f"CAGR {m['cagr']:5.2f}  vol {m['std']:5.2f}  MDD {m['mdd']:6.2f}  Sharpe {m['sharpe']:.3f}  Calmar {m['calmar']:.3f}  Ulcer {m['ulcer']:.3f}"
yc = np.quantile(years, [.25, .5, .75])
DEC = [np.flatnonzero(m) for m in (years <= yc[0], (years > yc[0]) & (years <= yc[1]), (years > yc[1]) & (years <= yc[2]), years > yc[2])]
def dec_sharpe(a): return " ".join(f"{f(a, d)['sharpe']:.2f}" for d in DEC)
def row(label, a):
    m = f(a); print(f"  {label:34} {fmt(m)} | decade Sharpe {dec_sharpe(a)}")
    return m

print(f"=== {name}: " + " ".join(f"{lbl(k)} {v}" for k, v in X.items()))
base = row(name, X); row(ref, R)

# 1. components alone
print("\n1) EACH HOLDING ON ITS OWN, 1988-2026")
for n, wt in X.items():
    m = f({n: 100}); print(f"  {lbl(n):6} {wt:3}%   {fmt(m)}")

# 2. correlations (monthly) incl. US stocks
ym = np.array([dt.datetime.fromtimestamp(x, dt.UTC).strftime("%Y%m") for x in t])
ends = np.r_[np.flatnonzero(ym[1:] != ym[:-1]), len(t) - 1]
cols = [NAMES.index(n) for n in X] + [NAMES.index("VTISIM")]
Mr = P[ends][1:, cols] / P[ends][:-1, cols] - 1
C = np.corrcoef(Mr.T); hdr = [lbl(n) for n in X] + ["VTI"]
print("\n2) MONTHLY CORRELATIONS")
print("        " + " ".join(f"{h:>6}" for h in hdr))
for i, h in enumerate(hdr): print(f"  {h:6}" + " ".join(f"{C[i, j]:6.2f}" for j in range(len(hdr))))

# 3. risk / return contribution + diversification
D = P[1:, cols[:-1]] / P[:-1, cols[:-1]] - 1
S = np.cov(D.T) * 252; wv = np.array(list(X.values())) / 100
rc = wv * (S @ wv); rc /= rc.sum()
mu = np.log(P[-1, cols[:-1]] / P[0, cols[:-1]]) / (len(t) / 252)
print("\n3) WHO CARRIES THE RISK, WHO EARNS THE RETURN")
for i, n in enumerate(X): print(f"  {lbl(n):6} weight {wv[i]*100:4.0f}%   risk share {rc[i]*100:6.1f}%   return share {wv[i]*mu[i]/np.dot(wv,mu)*100:6.1f}%")
vols = np.sqrt(np.diag(S)); wavg_cagr = sum(w_ * f({n: 100})["cagr"] for n, w_ in zip(X, wv))
print(f"  weighted-avg holding vol {np.dot(wv, vols)*100:.2f}%  vs portfolio vol {base['std']:.2f}%  -> diversification ratio {np.dot(wv, vols)*100/base['std']:.2f}x")
print(f"  weighted-avg holding CAGR {wavg_cagr:.2f}%  vs portfolio CAGR {base['cagr']:.2f}%  -> rebalancing bonus {base['cagr']-wavg_cagr:+.2f} pts/yr")

# 4. ablation
print("\n4) REMOVE ONE HOLDING (others scaled up)        dCAGR   dMDD  dSharpe dCalmar  dUlcer")
for n in X:
    a = {k: v for k, v in X.items() if k != n}; s = sum(a.values()); a = {k: v * 100 / s for k, v in a.items()}
    m = f(a); print(f"  -{lbl(n):6}                                    {m['cagr']-base['cagr']:+6.2f} {m['mdd']-base['mdd']:+6.2f} {m['sharpe']-base['sharpe']:+8.3f} {m['calmar']-base['calmar']:+7.3f} {m['ulcer']-base['ulcer']:+7.3f}")

# 5. path from reference to portfolio (C1-specific)
if name == "C1" and ref == "FULL#1":
    print("\n5) STEP BY STEP FROM FULL#1 TO C1")
    s0 = dict(R); row("FULL#1", s0)
    s1 = {"IEISIM": 30, "KMLMSIM": 20, "SPMOSIM": 20, "GLDSIM": 15, "UUPSIM": 10, "XLVSIM": 5}; row("a) SHY25+ZROZ5 -> IEI30", s1)
    s2 = {"IEISIM": 30, "KMLMSIM": 20, "SPMOSIM": 20, "GLDSIM": 15, "UUPSIM": 10, "XLPSIM": 5}; row("b) XLV5 -> XLP5", s2)
    s3 = {"IEISIM": 34, "KMLMSIM": 20, "SPMOSIM": 11, "QLDSIM": 3, "GLDSIM": 15, "UUPSIM": 12, "XLPSIM": 5}; row("c) SPMO-9 -> QLD3 +IEI4 +UUP2", s3)
    row("d) GLD-4 -> XLE3 +UUP1  (= C1)", X)

    print("\n6) WHY IEI? swap the 34% bond sleeve")
    for alt in ["SHYSIM", "IEISIM", "IEFSIM", "BNDSIM", "TLTSIM"]:
        a = dict(X); a.pop("IEISIM"); a[alt] = a.get(alt, 0) + 34; row(f"bond sleeve = {lbl(alt)}", a)

    print("\n7) WHY A 2x SLEEVE? replace QLD3 with unlevered QQQ (takes room from IEI)")
    row("C1 (QLD 3)", X)
    a = dict(X); a.pop("QLDSIM"); a["QQQSIM"] = 6; a["IEISIM"] -= 3; row("QQQ 6, IEI 31 (same Nasdaq exposure)", a)
    a = dict(X); a.pop("QLDSIM"); a["SPMOSIM"] += 3; row("no leverage: SPMO +3", a)
    a = dict(X); a.pop("QLDSIM"); a["TQQQSIM"] = 2; a["IEISIM"] += 1; row("TQQQ 2 instead", a)

# 8. crises
E = [("1990 Gulf War", "1990-07-16", "1990-10-11"), ("1994 bond crash", "1994-01-31", "1994-11-22"), ("1998 LTCM", "1998-07-17", "1998-10-08"),
     ("2000-02 dot-com", "2000-03-24", "2002-10-09"), ("2008 GFC", "2007-10-09", "2009-03-09"), ("2011 Euro crisis", "2011-04-29", "2011-10-03"),
     ("2015-16 selloff", "2015-05-21", "2016-02-11"), ("2018 Q4", "2018-09-20", "2018-12-24"), ("2020 Covid", "2020-02-19", "2020-03-23"),
     ("2022 rate shock", "2022-01-03", "2022-10-14")]
td = np.array([dt.datetime.fromtimestamp(x, dt.UTC).date().isoformat() for x in t])
VX = values(w_of(X))[:, 0]; VR = values(w_of(R))[:, 0]; VT = P[:, NAMES.index("VTISIM")]
print(f"\n8) CRISES (% over each US-stock drawdown)\n  {'episode':17} {'VTI':>6} {name:>6} {ref:>6} | " + " ".join(f"{lbl(n):>5}" for n in X))
for e, a, b in E:
    i = np.searchsorted(td, a); j = np.searchsorted(td, b); r = lambda x: (x[j] / x[i] - 1) * 100
    print(f"  {e:17} {r(VT):6.1f} {r(VX):6.1f} {r(VR):6.1f} | " + " ".join(f"{r(P[:, NAMES.index(n)]):5.1f}" for n in X))

# 9. calendar years
yrs = sorted(set(years)); ann = []
for y in yrs:
    idx = np.flatnonzero(years == y); a = max(idx[0] - 1, 0); b = idx[-1]
    ann.append((y, (VX[b] / VX[a] - 1) * 100, (VR[b] / VR[a] - 1) * 100, (VT[b] / VT[a] - 1) * 100))
A_ = np.array([x[1] for x in ann]); B_ = np.array([x[2] for x in ann])
print(f"\n9) CALENDAR YEARS  {name}: positive {int((A_>0).sum())}/{len(A_)}, worst {A_.min():.1f}% ({ann[int(A_.argmin())][0]}), best {A_.max():.1f}%   |   {ref}: positive {int((B_>0).sum())}/{len(B_)}, worst {B_.min():.1f}%")
print("  worst 5 years for " + name + ": " + ", ".join(f"{y} {a:.1f}% (VTI {v:.1f}%)" for y, a, _, v in sorted(ann, key=lambda x: x[1])[:5]))
