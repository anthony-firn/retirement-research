"""Rebalancing strategies for a fixed-weight portfolio on 1972-2026 local data (testfol SIMs, proxies only pre-inception).
Calendar (monthly..2-yearly, every month offset), absolute / relative drift bands checked daily, hybrids, buy & hold.
Trading cost 0.05% of turnover (spread/slippage). Reports full-period + 1988+ / 2000+ CAGR, MDD, Sharpe, Ulcer, trades and turnover per year,
5-year odds of a >20% drop (bootstrap of each strategy's own daily returns, 1-year blocks)."""
import os, sys, json, numpy as np, datetime as dt
sys.path.insert(0, "../strategy"); os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import b40_risk as br, history70s as h
NAME = os.environ.get("PF", "Crisis-Hedged 12"); COST = float(os.environ.get("COST", "0.0005"))
P = json.load(open("../results/portfolios.json")); A = P[NAME]["alloc"]; names = list(A); W0 = np.array([A[n] for n in names], float); W0 /= W0.sum()
R = np.stack([br.SUB[n] if n in br.SUB else h.rets(h.series(n)) for n in names], 1); T = len(R)
D = [dt.datetime.fromtimestamp(x, dt.UTC) for x in h.CAL]; Y = np.array([d.year for d in D]); M = np.array([d.month for d in D])
newm = np.r_[True, M[1:] != M[:-1]]; i88 = int(np.searchsorted(Y, 1988)); i00 = int(np.searchsorted(Y, 2000))
def run(kind, p=None, offset=1, band_check=None):
    w = W0.copy(); out = np.zeros(T); trades = 0; turn = 0.0
    for d in range(1, T):
        g = w * (1 + R[d]); pr = g.sum(); out[d] = pr - 1; w = g / pr
        reb = False
        if kind == "cal": reb = newm[d] and ((M[d] - offset) % p == 0)
        elif kind == "cal2y": reb = newm[d] and M[d] == offset and Y[d] % 2 == 0
        elif kind == "abs": reb = np.abs(w - W0).max() * 100 > p
        elif kind == "rel": reb = (np.abs(w - W0) / W0).max() * 100 > p
        elif kind == "cal+rel": reb = (newm[d] and M[d] == offset) or (np.abs(w - W0) / W0).max() * 100 > p
        elif kind == "relcal": reb = newm[d] and M[d] in ((offset - 1) % 12 + 1, (offset + 2) % 12 + 1, (offset + 5) % 12 + 1, (offset + 8) % 12 + 1) and (np.abs(w - W0) / W0).max() * 100 > p   # quarterly look, trade only if drifted
        if reb:
            tv = np.abs(w - W0).sum() / 2; out[d] = (1 + out[d]) * (1 - COST * tv * 2) - 1; turn += tv; trades += 1; w = W0.copy()
    return out, trades, turn
def met(r):
    v = np.cumprod(1 + r); c = (v[-1] ** (252 / len(r)) - 1) * 100; dd = 1 - v / np.maximum.accumulate(v); ex = r - h.rf[-len(r):]
    return c, dd.max() * 100, ex.mean() / ex.std() * np.sqrt(252), np.sqrt((dd ** 2 * 1e4).mean())
g = np.random.default_rng(41); IDX = (g.integers(1, T - 252, size=(2000, 5))[:, :, None] + np.arange(252)[None, None, :]).reshape(2000, -1)
S = [("buy & hold (never)", "none", None, 1)]
S += [(f"monthly", "cal", 1, 1), ("quarterly (Jan/Apr/Jul/Oct)", "cal", 3, 1), ("semi-annual (Jan/Jul)", "cal", 6, 1)]
S += [(f"yearly in {dt.date(2000, m, 1):%b}", "cal", 12, m) for m in range(1, 13)]
S += [("every 2 years (Jan)", "cal2y", None, 1)]
S += [(f"band abs ±{b}pp (daily check)", "abs", b, 1) for b in (2, 3, 5, 7.5, 10)]
S += [(f"band rel ±{b}% (daily check)", "rel", b, 1) for b in (10, 15, 20, 25, 35, 50)]
S += [(f"yearly Jan + rel ±{b}% band", "cal+rel", b, 1) for b in (25, 35, 50)]
S += [(f"quarterly look, trade if rel >{b}%", "relcal", b, 1) for b in (10, 20, 30)]
res = []
print(f"{NAME}: {', '.join(f'{n.replace(chr(83)+chr(73)+chr(77),'')} {A[n]}' for n in names)} | cost {COST*100:.2f}% of traded value")
print(f"{'strategy':34} | 1972-2026: CAGR   MDD  Sharpe Ulcer | 1988+ CAGR  MDD | 2000+ CAGR  MDD | trades/yr turnover/yr | 5y>20%")
for lab, kind, p, off in S:
    r, n, tv = run(kind, p, off); f = met(r); a = met(r[i88:]); b = met(r[i00:]); yrs = T / 252
    nav = np.cumprod(1 + r[IDX], 1); p20 = np.mean((1 - nav / np.maximum.accumulate(nav, 1)).max(1) > 0.2) * 100
    res.append(dict(name=lab, cagr=f[0], mdd=f[1], sharpe=f[2], ulcer=f[3], cagr88=a[0], mdd88=a[1], cagr00=b[0], mdd00=b[1], trades=n / yrs, turnover=tv / yrs * 100, p20=p20))
    print(f"{lab:34} | {f[0]:6.2f} {f[1]:6.1f} {f[2]:6.3f} {f[3]:5.2f} | {a[0]:6.2f} {a[1]:5.1f} | {b[0]:6.2f} {b[1]:5.1f} | {n/yrs:6.2f}  {tv/yrs*100:7.1f}%     | {p20:4.0f}%", flush=True)
json.dump(res, open(f"rebal_{NAME}.json", "w"), indent=1)
