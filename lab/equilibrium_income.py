"""How much income a Crisis-Hedged 12 account can pay forever while keeping its inflation-adjusted value (the retiree's 40-year horizon).
A) fixed real income: rate where the 40-year real ending value >= start in 90% / 75% / 50% of histories;
B) 'skim' plan: fixed real base income + each year-end, skim anything above (1+buffer) x the inflation-adjusted start as a bonus.
Bootstrap histories (1-year blocks of 1972-2026). Sensitivities: middle tax bracket, trend funds earning 2%/yr less, 3-month blocks."""
import os, sys, json, numpy as np
os.environ.setdefault("YEARS", "40"); os.environ.setdefault("PATHS", "2000")
exec(open("equilibrium_gpu.py").read().split("if __name__")[0])
RULE = dict(name="band ±6pp, min 1y, valve 2x", band=6, gap=252, valve=2.0); CUR = dict(name="yearly + 2x valve", yearly=True, valve=2.0)
rates = [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9]; out = {}
def fixed(label, IDX, taxr=TAXR):
    re, mn, nreb, dead = simulate([RULE, CUR], rates, IDX, taxr=taxr)
    for c, ru in enumerate([RULE, CUR]):
        q = {p: eq_rate(rates, [np.percentile(re[c, k], 100 - p) for k in range(len(rates))]) for p in (90, 75, 50)}
        k5 = rates.index(5); dip = np.percentile(mn[c, k5], 10)
        print(f"  {label:42} {ru['name']:28} | 90%: {q[90]:5.2f}%  75%: {q[75]:5.2f}%  50%: {q[50]:5.2f}% | at 5%: real low point p10 {dip*100:4.0f}% of start, ran out {dead[c, k5]*100:.1f}%", flush=True)
        out[f"{label}|{ru['name']}"] = q
IDX = make_idx(11)
print(f"A) Fixed inflation-adjusted income, {YEARS} years, keep the real starting value (bootstrap, {IDX.shape[0]} histories)")
fixed("base case (the retiree's taxes ~3% of gains)", IDX)
fixed("middle tax bracket (~20% of gains)", IDX, taxr=0.20)
HAIR = 0.02; Rn2 = R.copy()
for n in ("KMLMSIM", "DBMFSIM"): Rn2[:, names.index(n)] -= HAIR / 252
Rg_save = Rg; Rg = torch.tensor(Rn2, device=DEV, dtype=f32); fixed("trend funds earn 2%/yr less", IDX); Rg = Rg_save
g = np.random.default_rng(12); nb = L // 63 + 1; s_ = g.integers(1, T - 63, size=(PATHS, nb)); IDX3 = torch.tensor((s_[:, :, None] + np.arange(63)[None, None, :]).reshape(PATHS, -1)[:, :L], device=DEV)
fixed("harsher reshuffle (3-month blocks)", IDX3)
os.environ["HIST"] = "1"; L_save = L
print(f"\nB) Skim plan: fixed real base income + skim the excess above a buffer each year-end ({YEARS} years, bootstrap)")
print(f"  {'base':>5} {'buffer':>6} | avg income/yr: p10   median  | worst year (=base) | income in a typical year: p25 / median / p75 | real end value p10 / median | real low point p10")
for base in (4.0, 4.5, 5.0):
    for buf in (0.10, 0.25):
        r = simulate([RULE], [base], IDX, skim=buf, full=True); inc = r["inc"][0, 0][:, 1:]   # drop partial first year
        avg = inc.mean(1) * 100; allyrs = inc.flatten() * 100; re = r["real_end"][0, 0]; mn = r["minreal"][0, 0]
        print(f"  {base:4.1f}% {buf*100:5.0f}% |          {np.percentile(avg,10):5.2f}%  {np.median(avg):5.2f}%  |       {base:4.1f}%        |            {np.percentile(allyrs,25):5.2f}% / {np.median(allyrs):5.2f}% / {np.percentile(allyrs,75):5.2f}%      |     {np.percentile(re,10):5.2f} / {np.median(re):5.2f}      |  {np.percentile(mn,10)*100:4.0f}%", flush=True)
json.dump(out, open("equilibrium_income.json", "w"), indent=1)
