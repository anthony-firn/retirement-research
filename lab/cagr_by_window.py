"""CAGR / worst drop of named portfolios over several windows on local data (testfol SIMs, proxies only before inception)."""
import os, sys, json, numpy as np, datetime as dt
sys.path.insert(0, "../strategy"); os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import b40_risk as br, history70s as h
P = json.load(open("../results/portfolios.json")); names = sys.argv[1:] or ["H12-8", "H12", "S12+ split", "S12+", "S12.5", "S13", "S13.5", "E14", "60/40"]
W = [("1972-2026", "1972-01-03"), ("1988-2026", "1988-01-04"), ("2000-2026", "2000-01-03"), ("2009-2026", "2009-03-09")]
ts = lambda s: int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.UTC).timestamp())
print("Local data (testfol SIMs; proxies only before each fund's SIM starts). CAGR % / worst drop %")
print(f"{'':12}" + "".join(f"{w:>18}" for w, _ in W))
for n in names:
    r = h.blend_series(P[n]["alloc"], br.SUB); v = np.cumprod(1 + r); out = []
    for _, s in W:
        i = int(np.searchsorted(h.CAL, ts(s))); x = v[i:] / v[i]; c = (x[-1] ** (252 / (len(x) - 1)) - 1) * 100; m = (1 - x / np.maximum.accumulate(x)).max() * 100
        out.append(f"{c:6.2f} / {m:5.1f}")
    print(f"{n:12}" + "".join(f"{o:>18}" for o in out))
