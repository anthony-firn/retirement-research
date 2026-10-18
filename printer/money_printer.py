"""Money Printer: one fully coordinated plan for living off an account.

  ENGINE       the portfolio (fund weights)
  MAINTENANCE  rebalance when any fund is > `band` points off target, never sooner than `gap_days` after the last
               rebalance; safety valve: rebalance any time a fund reaches `valve` x its target (or `yearly` calendar rule)
  OUTPUT       base print: `base` % of the starting value per year, paid monthly, raised with inflation, sold from the most
               overweight funds first; bonus print: each year-end anything above (1 + `skim`) x the inflation-adjusted start
               is skimmed into a cash bucket (T-bills) that pays out 1/`bucket_months` of its balance every month
  GUARDRAIL    if the real value is below `cut_below` x start at a year-end, the base print drops to `cut_to` x base until the
               real value is back above `restore_above` x start
  TAXES        per-fund tax character in a taxable account (qualified / ordinary distributions, collectibles, mark-to-market),
               short- vs long-term by holding time, losses carried forward, California taxes everything as ordinary income

evaluate() runs many printers at once on the GPU over reshuffled 1972-2026 market histories (joint daily returns of all
funds + CPI + T-bills, 1-year blocks) and scores what matters:
  PRINT        spendable $ per month after all taxes (typical history, bad history, lean months)
  RELIABILITY  how steady the monthly print is and how often the base print had to be cut
  BREAK RISK   chance it loses real value, dips deep, runs dry; and how much less it prints if the future is worse
Usage:  python3 printer/money_printer.py compare | grid | stress   (writes results/printer_*.log / .json)"""
import os, sys, json, numpy as np, torch
from dataclasses import dataclass, asdict, replace
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, "..", "strategy"))
os.environ.setdefault("PORT_FILE", "data_portfolios_1972.json")
import history70s as h, b40_risk as br

DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu"); f32 = torch.float32
COST = 0.0005                                                     # trading cost, share of traded value
# taxable-account character: yearly distribution yield and type (q = qualified dividends, o = ordinary income)
DIST = {"VBRSIM": (.020, "q"), "XLVSIM": (.016, "q"), "VTISIM": (.013, "q"), "SPMOSIM": (.012, "q"), "DBMFSIM": (.025, "o"),
        "KMLMSIM": (.025, "o"), "TYDSIM": (.020, "o"), "TQQQSIM": (.010, "o"), "TMFSIM": (.015, "o"), "IEISIM": (.030, "o"),
        "BNDSIM": (.035, "o"), "GDESIM": (.010, "o")}
COLLECTIBLE = {"GLDSIM"}; MARK_TO_MARKET = {"UUPSIM"}
TAX = {"none (IRA/Roth)": dict(ord=0, lt=0, coll=0, ca=0), "retiree, not working": dict(ord=.10, lt=0, coll=.10, ca=.02),
       "retiree, working $40k": dict(ord=.12, lt=0, coll=.12, ca=.05), "middle bracket": dict(ord=.22, lt=.15, coll=.22, ca=.093)}

@dataclass
class Printer:
    name: str
    alloc: dict
    band: float = 6.0
    gap_days: int = 252
    valve: float = 2.0
    yearly: bool = False
    base: float = 4.0
    skim: float = 0.25          # None/negative = no bonus print
    bucket_months: int = 36
    cut_below: float = 0.70
    cut_to: float = 0.80
    restore_above: float = 0.90
    tax: str = "retiree, not working"

# ------------------------------------------------------------------ market data (all funds any printer may use)
T = len(h.CAL)
_cpi = np.asarray(h.cpi, float); _cpi = np.where(np.isnan(_cpi), np.nanmin(_cpi), _cpi); CPIR = np.r_[1.0, _cpi[1:] / _cpi[:-1]]
RF = np.asarray(h.rf, float)
def fund_returns(n): return np.asarray(br.SUB[n] if n in br.SUB else h.rets(h.series(n)), float)

def make_idx(paths, years, block=252, seed=11, hist=False):
    L = years * 252
    if hist: st = np.arange(1, T - L, 21); return torch.tensor(st[:, None] + np.arange(L)[None, :], device=DEV)
    g = np.random.default_rng(seed); nb = L // block + 1; s = g.integers(1, T - block, size=(paths, nb))
    return torch.tensor((s[:, :, None] + np.arange(block)[None, None, :]).reshape(paths, -1)[:, :L], device=DEV)

def simulate(printers, IDX, trend_haircut=0.0):
    """printers: list of Printer. Lanes = printers x histories. Returns dict of per-lane numpy arrays."""
    assets = sorted({a for p in printers for a in p.alloc}); A = len(assets)
    Rm = np.stack([fund_returns(a) for a in assets], 1)
    for a in ("KMLMSIM", "DBMFSIM"):
        if a in assets and trend_haircut: Rm[:, assets.index(a)] -= trend_haircut / 252
    Rg = torch.tensor(Rm, device=DEV, dtype=f32); Cg = torch.tensor(CPIR, device=DEV, dtype=f32); Fg = torch.tensor(RF, device=DEV, dtype=f32)
    divy = torch.tensor([DIST.get(a, (0, "o"))[0] for a in assets], device=DEV); qual = torch.tensor([DIST.get(a, (0, "o"))[1] == "q" for a in assets], device=DEV)
    coll = torch.tensor([a in COLLECTIBLE for a in assets], device=DEV); mtm = torch.tensor([a in MARK_TO_MARKET for a in assets], device=DEV); norm = ~(coll | mtm)
    C, P = len(printers), IDX.shape[0]; N = C * P; L = IDX.shape[1]; Y = L // 252; M = L // 21
    ci = torch.arange(C, device=DEV).repeat_interleave(P); pi = torch.arange(P, device=DEV).repeat(C)
    pv = lambda f, dt=f32: torch.tensor([f(p) for p in printers], device=DEV, dtype=dt)[ci]
    W0c = torch.tensor([[p.alloc.get(a, 0) / sum(p.alloc.values()) for a in assets] for p in printers], device=DEV, dtype=f32); W0 = W0c[ci]
    has = W0 > 0
    band = pv(lambda p: p.band if p.band else 1e9); gap = pv(lambda p: p.gap_days, torch.long); valve = pv(lambda p: p.valve if p.valve else 1e9)
    yearly = pv(lambda p: p.yearly, torch.bool); base = pv(lambda p: p.base / 100); skim = pv(lambda p: p.skim if (p.skim is not None and p.skim >= 0) else 1e9)
    bmon = pv(lambda p: p.bucket_months); cutb = pv(lambda p: p.cut_below); cutt = pv(lambda p: p.cut_to); rest = pv(lambda p: p.restore_above)
    tx = {k: pv(lambda p, k=k: TAX[p.tax][k]) for k in ("ord", "lt", "coll", "ca")}
    r_o = tx["ord"] + tx["ca"]; r_l = tx["lt"] + tx["ca"]; r_c = tx["coll"] + tx["ca"]; r_m = 0.6 * tx["lt"] + 0.4 * tx["ord"] + tx["ca"]
    val = W0.clone(); basis = val.clone(); lastb = torch.zeros(N, A, device=DEV); bfrac = torch.ones(N, A, device=DEV)
    last = torch.zeros(N, dtype=torch.long, device=DEV); infl = torch.ones(N, device=DEV); bucket = torch.zeros(N, device=DEV); mult = torch.ones(N, device=DEV)
    gST, gLT, gC, gM, carry, intr = (torch.zeros(N, device=DEV) for _ in range(6))
    dead = torch.zeros(N, dtype=torch.bool, device=DEV); cut_ever = torch.zeros(N, dtype=torch.bool, device=DEV); minreal = torch.ones(N, device=DEV)
    spend = torch.zeros(N, M, device=DEV); yreal = torch.zeros(N, Y, device=DEV); taxreal = torch.zeros(N, device=DEV); nreb = torch.zeros(N, device=DEV)
    def realize(sell, d):
        nonlocal basis, gST, gLT, gC, gM
        frac = (sell / val.clamp(min=1e-12)).clamp(0, 1); g = sell - basis * frac; basis = basis * (1 - frac)
        stf = torch.where((d - lastb) < 252, bfrac, torch.zeros_like(bfrac))
        gST += (g * stf * norm).sum(1); gLT += (g * (1 - stf) * norm).sum(1); gC += (g * coll).sum(1); gM += (g * mtm).sum(1)
    def sell_amount(amt, d):                                       # take `amt` from the most overweight funds first
        nonlocal val
        V = val.sum(1); amt = amt.clamp(max=V.clamp(min=0)); tgt = W0 * V[:, None]; exc = (val - tgt).clamp(min=0); se = exc.sum(1)
        te = torch.minimum(amt, se); rem = amt - te; s1 = exc * (te / se.clamp(min=1e-12))[:, None]
        s = s1 + (val - s1) * (rem / (V - te).clamp(min=1e-12))[:, None]; realize(s, d); val = val - s; return s.sum(1)
    for d in range(1, L):
        rows = IDX[pi, d]; val = val * (1 + Rg[rows]); infl = infl * Cg[rows]; bi = bucket * Fg[rows]; bucket = bucket + bi; intr += bi
        if d % 21 == 0:
            m = d // 21 - 1
            got = sell_amount(base / 12 * infl * mult, d); draw = bucket / bmon; bucket = bucket - draw
            spend[:, min(m, M - 1)] = (got + draw) / infl; dead |= val.sum(1) <= 1e-6
        V = val.sum(1); w = val / V.clamp(min=1e-12)[:, None]; since = d - last
        rel = torch.where(has, w / W0.clamp(min=1e-12), torch.zeros_like(w)).max(1).values
        trig = ((((w - W0).abs().max(1).values * 100 > band) & (since > gap)) | (rel >= valve) | (yearly & (since >= 252))) & ~dead
        if trig.any():
            tgt = W0 * V[:, None]; over = (val > tgt) & trig[:, None]; under = (val < tgt) & trig[:, None]
            realize(torch.where(over, val - tgt, torch.zeros_like(val)), d)
            buy = torch.where(under, tgt - val, torch.zeros_like(val)); basis = basis + buy
            bfrac = torch.where(under, buy / tgt.clamp(min=1e-12), bfrac); lastb = torch.where(under, torch.full_like(lastb, float(d)), lastb)
            cost = COST * (tgt - val).abs().sum(1) * trig; val = torch.where(trig[:, None], tgt * (1 - cost / V.clamp(min=1e-12))[:, None], val)
            last = torch.where(trig, torch.full_like(last, d), last); nreb += trig
        if d % 252 == 251:
            y = d // 252
            dist = val * divy; basis = basis + dist; divq = (dist * qual).sum(1); divo = (dist * ~qual).sum(1)
            gM += ((val - basis) * mtm).sum(1); basis = torch.where(mtm, val, basis)
            V = val.sum(1); bonus = ((V / infl - (1 + skim)).clamp(min=0) * infl)                    # bonus print -> bucket
            if bool((bonus > 0).any()):
                realize(val * (bonus / V.clamp(min=1e-12))[:, None], d); val = val * (1 - bonus / V.clamp(min=1e-12))[:, None]; bucket = bucket + bonus
            pos = [gST.clamp(min=0), gLT.clamp(min=0), gC.clamp(min=0), gM.clamp(min=0)]; net = gST + gLT + gC + gM + carry
            wr = (pos[0] * r_o + pos[1] * r_l + pos[2] * r_c + pos[3] * r_m) / sum(pos).clamp(min=1e-12)
            tax = torch.where(net > 0, net * wr, torch.zeros_like(net)) + divq * r_l + (divo + intr) * r_o; carry = net.clamp(max=0)
            gST.zero_(); gLT.zero_(); gC.zero_(); gM.zero_(); intr.zero_()
            V = val.sum(1); f = (tax / V.clamp(min=1e-12)).clamp(0, 1); val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]; taxreal += tax / infl
            real = val.sum(1) / infl; yreal[:, min(y, Y - 1)] = real
            mult = torch.where(real < cutb, cutt, torch.where(real > rest, torch.ones_like(mult), mult)); cut_ever |= real < cutb
        minreal = torch.minimum(minreal, val.sum(1) / infl)
    sh = lambda x: x.view(C, P, *x.shape[1:]).cpu().numpy()
    return dict(spend=sh(spend), yreal=sh(yreal), real_end=sh(val.sum(1) / infl), minreal=sh(minreal), dead=sh(dead), cut=sh(cut_ever),
                tax=sh(taxreal / Y), reb=sh(nreb / Y), bucket_end=sh(bucket / infl))

def score(r, c):
    """Score card for printer c (fractions of the starting value; multiply by size for $)."""
    S = r["spend"][c][:, 1:]; P, M = S.shape; avg = S.mean(1) * 12; yrs = S[:, :(M // 12) * 12].reshape(P, -1, 12).sum(2)
    return dict(
        print_typical=float(np.median(avg)), print_bad=float(np.percentile(avg, 10)), print_lean_month=float(np.percentile(S, 10) * 12),
        print_typical_month=float(np.median(S) * 12), worst_year_bad=float(np.percentile(yrs.min(1), 10)),
        steady=float(np.mean(np.abs(np.diff(yrs, axis=1)) / np.maximum(yrs[:, :-1], 1e-9) < 0.25)),   # share of years within ±25% of the year before
        base_never_cut=float(1 - r["cut"][c].mean()), lose_value=float((r["real_end"][c] < 1).mean()),
        deep_dip=float((r["minreal"][c] < 0.70).mean()), run_dry=float(r["dead"][c].mean()),
        left_typical=float(np.median(r["real_end"][c] + r["bucket_end"][c])), tax_per_year=float(np.median(r["tax"][c])), rebalances_per_year=float(np.median(r["reb"][c])),
        no_bonus_first_10y=float(np.mean(yrs[:, :10].max(1) <= yrs[:, :10].min(1) * 1.001)),
        **{f"print_y{a+1}_{b}_{q}": float(np.percentile(yrs[:, a:b].mean(1), {"typ": 50, "bad": 10}[q])) for a, b in ((0, 10), (10, 20), (20, 40)) for q in ("typ", "bad")})

def sheet(name, s, sizes=(100_000,)):
    mo = lambda x, z: f"${x * z / 12:,.0f}"
    lines = [f"  {name}"]
    for z in sizes:
        lines.append(f"    PRINT per month on ${z:,.0f} (after tax, today's $): typical {mo(s['print_typical'], z)}  |  bad history {mo(s['print_bad'], z)}  |  lean month (1 in 10) {mo(s['print_lean_month'], z)}")
    lines.append(f"    RELIABILITY: base print never cut in {s['base_never_cut']*100:.0f}% of histories | {s['steady']*100:.0f}% of years within ±25% of the year before | worst year (bad history) {s['worst_year_bad']*100:.1f}% of start")
    lines.append(f"    BY DECADE (typical / bad, % of start per yr): ages 60-70 {s['print_y1_10_typ']*100:.1f} / {s['print_y1_10_bad']*100:.1f} | 70-80 {s['print_y11_20_typ']*100:.1f} / {s['print_y11_20_bad']*100:.1f} | 80-100 {s['print_y21_40_typ']*100:.1f} / {s['print_y21_40_bad']*100:.1f} | no bonus in first 10 yrs {s['no_bonus_first_10y']*100:.0f}%")
    lines.append(f"    BREAK RISK: loses real value by the end {s['lose_value']*100:.0f}% | dips below 70% of start {s['deep_dip']*100:.0f}% | runs dry {s['run_dry']*100:.1f}% | left at the end (typical) {s['left_typical']*100:.0f}% of start")
    return "\n".join(lines)

def load_alloc(name):
    return json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))[name]["alloc"]

CANDIDATES = lambda: [
    Printer("CH-12 Printer (taxable: no UUP)", load_alloc("Crisis-Hedged 12 (no UUP)")),
    Printer("CH-12 Printer (with UUP)", load_alloc("Crisis-Hedged 12")),
    Printer("CH-11.5 Printer", load_alloc("Crisis-Hedged 11.5")),
    Printer("Gold-Stack 12 Printer", load_alloc("Gold-Stack 12")),
    Printer("S12+ split Printer", load_alloc("S12+ split")),
    Printer("CH-12 fixed 5% (no bonus, no guardrail)", load_alloc("Crisis-Hedged 12 (no UUP)"), base=5.0, skim=None, cut_below=-1),
    Printer("60/40 Printer", load_alloc("60/40")),
    Printer("VTI Printer", load_alloc("VTI (100% US stocks)")),
]

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "compare"; YEARS = int(os.environ.get("YEARS", "40")); PATHS = int(os.environ.get("PATHS", "2000"))
    out_log = os.path.join(ROOT, "..", "results", f"printer_{mode}.json")
    if mode == "compare":
        pr = CANDIDATES(); IDX = make_idx(PATHS, YEARS); r = simulate(pr, IDX); res = {}
        print(f"Money printers: base 4% + skim above 125% -> 36-month bucket, guardrail 70%->80% base; the retiree's taxes (not working); {YEARS} years, {PATHS} histories\n")
        for c, p in enumerate(pr): s = score(r, c); res[p.name] = s; print(sheet(p.name, s) + "\n", flush=True)
    elif mode == "grid":
        al = load_alloc("Crisis-Hedged 12 (no UUP)"); pr = []
        for b in (3.5, 4.0, 4.5, 5.0):
            for sk in (0.10, 0.25, 0.50):
                for bm in (12, 36, 60):
                    for ct in (0.80, 1.0):
                        pr.append(Printer(f"base {b}% skim>{int(sk*100)}% bucket {bm}m cut {'to 80%' if ct < 1 else 'none'}", al, base=b, skim=sk, bucket_months=bm, cut_to=ct, cut_below=0.70 if ct < 1 else -1))
        IDX = make_idx(PATHS, YEARS); res = {}
        for i in range(0, len(pr), 24):
            r = simulate(pr[i:i + 24], IDX)
            for c, p in enumerate(pr[i:i + 24]): res[p.name] = score(r, c)
            print(f"  {min(i + 24, len(pr))}/{len(pr)}", flush=True)
        ok = {k: v for k, v in res.items() if v["lose_value"] <= 0.10 and v["run_dry"] <= 0.01}
        print(f"\nCH-12 (no UUP) printer settings, the retiree's taxes. Feasible = loses real value <= 10% and runs dry <= 1% of histories. Ranked by typical print:")
        print(f"  {'settings':44} | print/yr typical  bad   lean-month | base never cut | steady | lose value  dip<70%  dry")
        for k, v in sorted(ok.items(), key=lambda kv: -kv[1]["print_typical"])[:20]:
            print(f"  {k:44} |       {v['print_typical']*100:5.2f}%  {v['print_bad']*100:5.2f}%  {v['print_lean_month']*100:5.2f}%  |      {v['base_never_cut']*100:4.0f}%     |  {v['steady']*100:3.0f}%  |   {v['lose_value']*100:4.0f}%     {v['deep_dip']*100:4.0f}%   {v['run_dry']*100:4.1f}%", flush=True)
    elif mode == "decades":
        al = load_alloc("Crisis-Hedged 12 (no UUP)"); pr = [Printer(f"base {b}% skim>{int(sk*100)}% bucket 36m", al, base=b, skim=sk) for b in (4.0, 4.5) for sk in (0.10, 0.25, 0.35, 0.50, 0.75)]
        r = simulate(pr, make_idx(PATHS, YEARS)); res = {}
        for c, p in enumerate(pr): s = score(r, c); res[p.name] = s; print(sheet(p.name, s) + "\n", flush=True)
    elif mode == "stress":
        p0 = Printer("CH-12 Printer", load_alloc("Crisis-Hedged 12 (no UUP)"), **json.loads(os.environ.get("SETTINGS", "{}"))); res = {}
        runs = [("base case", dict(), make_idx(PATHS, YEARS)), ("trend funds earn 2%/yr less", dict(trend_haircut=0.02), make_idx(PATHS, YEARS)),
                ("trend funds earn 4%/yr less", dict(trend_haircut=0.04), make_idx(PATHS, YEARS)), ("harsher reshuffle (3-month blocks)", dict(), make_idx(PATHS, YEARS, block=63, seed=12)),
                ("actual 40-year windows 1972-1986 starts", dict(), make_idx(0, YEARS, hist=True))]
        for lab, kw, IDX in runs:
            r = simulate([p0, replace(p0, tax="retiree, working $40k"), replace(p0, tax="middle bracket")], IDX, **kw)
            for c, t in enumerate(("retiree, not working", "retiree, working $40k", "middle bracket")):
                s = score(r, c); res[f"{lab} | {t}"] = s; print(sheet(f"{lab} | taxes: {t}", s) + "\n", flush=True)
    json.dump(res, open(out_log, "w"), indent=1)
