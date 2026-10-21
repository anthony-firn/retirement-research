"""Money Printer: one fully coordinated plan for living off an account.

  ENGINE       the portfolio (fund weights)
  MAINTENANCE  rebalance when any fund is > `band` points off target, never sooner than `gap_days` after the last
               rebalance; safety valve: rebalance any time a fund reaches `valve` x its target (or `yearly` calendar rule)
  OUTPUT       base print: `base` % of the starting value per year, paid monthly, raised with inflation, sold from the most
               overweight funds first; bonus print: each year-end anything above (1 + `skim`) x the inflation-adjusted start
               is skimmed into a cash bucket (T-bills) that pays out 1/`bucket_months` of its balance every month
  GUARDRAIL    if the real value is below `cut_below` x start at a year-end, the base print drops to `cut_to` x base until the
               real value is back above `restore_above` x start
  CREDIT       optional (off by default): BOOST = hold `lev` x net worth (account loan re-levered at rebalances, or `lev_daily`
               leverage inside the funds); RUN = borrow the base print from a `credit` line while below the start, repay above it;
               loan rate = T-bills + `rate_spread`; `interest_tax` = how the interest is deducted (results/CREDIT.md)
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
        "BNDSIM": (.035, "o"), "GDESIM": (.010, "o"), "IEFSIM": (.032, "o"), "TLTSIM": (.038, "o"), "SHYSIM": (.035, "o"), "ZROZSIM": (.040, "o"),
        "XLESIM": (.032, "q"), "XLPSIM": (.026, "q"), "XLUSIM": (.030, "q"), "VTVSIM": (.023, "q"), "REITSIM": (.035, "o"), "QLDSIM": (.003, "o"),
        "NTSXSIM": (.012, "q"), "RSSBSIM": (.015, "o"), "UBTSIM": (.012, "o"), "RSSTSIM": (.030, "o"), "RSSTPSIM": (.030, "o")}
COLLECTIBLE = {"GLDSIM", "GLDMSIM", "IAUMSIM"}; MARK_TO_MARKET = {"UUPSIM", "UGLSIM"}
# funds with a near-twin to swap into for tax-loss harvesting (VBR <-> IJS/SLYV, gold trusts GLD/GLDM/IAUM, VTI <-> ITOT, XLV <-> VHT, ...)
HARVEST = {"VBRSIM", "GLDSIM", "GLDMSIM", "IAUMSIM", "VTISIM", "XLVSIM", "VTVSIM", "XLESIM", "SPMOSIM"}
# cheaper share classes of the same holdings: (source fund, yearly expense-ratio saving); GLD 0.40% -> GLDM 0.10% / IAUM 0.09%
ALIAS = {"GLDMSIM": ("GLDSIM", 0.0030), "IAUMSIM": ("GLDSIM", 0.0031)}
# return-stacked funds rebuilt from their sleeves (no long local history): sum of sleeves - T-bills for the borrowed part - extra cost.
# RSST (0.99% fee) = US stocks + managed futures; DBMF stands in for its trend sleeve (an approximation); extra 0.5%/yr = fee gap +
# equity-futures financing above T-bills. Over RSST's live years (2023-2026) this proxy ran ~5%/yr above the real fund (its trend
# sleeve differs from DBMF), so "RSSTPSIM" is the same proxy with a pessimistic 3%/yr extra cost; a change only counts if it passes with it
COMPOSITE = {"RSSTSIM": ({"VTISIM": 1.0, "DBMFSIM": 1.0}, 0.005), "RSSTPSIM": ({"VTISIM": 1.0, "DBMFSIM": 1.0}, 0.030)}
TAX = {"none (IRA/Roth)": dict(ord=0, lt=0, coll=0, ca=0), "retiree, not working": dict(ord=.10, lt=0, coll=.10, ca=.02),
       "retiree, working $40k": dict(ord=.12, lt=0, coll=.12, ca=.05), "middle bracket": dict(ord=.22, lt=.15, coll=.22, ca=.093, item=1)}
# item=1: itemizes on the federal return (with the $40k SALT cap a California homeowner in the middle bracket usually does);
# California's standard deduction is small, so everyone is assumed to itemize on the state return.

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
    # CREDIT (all off by default). Loan interest = T-bill rate + `rate_spread` %/yr.
    lev: float = 1.0            # BOOST: hold lev x net worth in the funds
    lev_daily: bool = False     #   True: leverage inside the funds (reset daily, like GDE/TQQQ/futures): no loan, no margin call
                                #   False: an account loan (margin / box spread), re-levered at each rebalance, margin call below 30% equity
    credit: float = 0.0         # RUN (can be combined with BOOST; tracked as a separate loan): standby line, share of the inflation-adjusted start. While the real net value is below
    draw_below: float = 1.0     #   draw_below x start, the base print is borrowed instead of sold; the whole loan is repaid at the
    repay_above: float = 1.0    #   first year-end with the real net value above repay_above x start
    rate_spread: float = 0.0
    harvest: float = 0.0        # TAX-LOSS HARVESTING: at each year-end swap any HARVEST fund >= `harvest` below its cost into its near-twin
                                #   (loss realized, new cost and holding period; twin assumed to track the same; 2 x trading cost)
    bucket_offsets_loan: bool = False  # with an account loan, the cash bucket pays the loan down instead of sitting in cash: it earns the
                                       #   loan rate, untaxed (avoided interest, so the interest deduction shrinks with it); bonus draws re-borrow
    bucket_fill: bool = False   # while the guardrail has cut the base print, top it back up from the cash bucket (if there is any)
    no_raise_after_loss: bool = False  # skip the yearly inflation raise of the base print after a year the portfolio lost money (no catch-up)
    glide: dict = None          # GLIDEPATH: target weights reached after `glide_years` (same funds as alloc), moved linearly each
    glide_years: int = 10       #   year-end from alloc; withdrawals and the drift rule move the holdings toward the new targets
    bucket_tax: str = "ordinary"  # cash bucket: "ordinary" = T-bill interest (federal + CA); "treasury" = Treasury fund (no CA tax);
                                  #   "boxx" = box-spread ETF (0.19% fee; growth taxed as long-term gains)
    interest_tax: str = "none"  # "capital": a 60/40 capital loss (box spread, section 1256); "investment": investment interest
                                #   (itemized, up to the year's ordinary investment income: federal if the bracket itemizes, plus CA);
                                #   "home": California home-equity interest (state return only); "none": not deductible

# ------------------------------------------------------------------ market data (all funds any printer may use)
T = len(h.CAL)
_cpi = np.asarray(h.cpi, float); _cpi = np.where(np.isnan(_cpi), np.nanmin(_cpi), _cpi); CPIR = np.r_[1.0, _cpi[1:] / _cpi[:-1]]
RF = np.asarray(h.rf, float)
def fund_returns(n):
    if n in ALIAS: src, save = ALIAS[n]; return fund_returns(src) + save / 252
    if n in COMPOSITE:
        legs, cost = COMPOSITE[n]; return sum(w * fund_returns(a) for a, w in legs.items()) - (sum(legs.values()) - 1) * RF - cost / 252
    return np.asarray(br.SUB[n] if n in br.SUB else h.rets(h.series(n)), float)

def make_idx(paths, years, block=252, seed=11, hist=False, step=1, era=None):
    """Histories as row indices into step-day compounded returns. step=1: daily; step=5: weekly (50 steps per model year).
    era=(first_day, last_day) restricts the bootstrap blocks to that part of 1972-2026 (e.g. 2000-2026 only)."""
    spy = 252 if step == 1 else 250 // step; L = years * spy; bs = max(1, round(block / step)) if step > 1 else block
    if hist: st = np.arange(1, T - years * spy * step, 21); return torch.tensor(st[:, None] + step * np.arange(L)[None, :], device=DEV)
    lo, hi = (1, T) if era is None else era
    g = np.random.default_rng(seed); nb = L // bs + 1; s = g.integers(lo, hi - bs * step, size=(paths, nb))
    return torch.tensor((s[:, :, None] + step * np.arange(bs)[None, None, :]).reshape(paths, -1)[:, :L], device=DEV)

def _compound(x, k):                                              # k-day compounded growth factors starting at each day
    if k == 1: return x
    lg = np.log(np.maximum(x, 1e-12)); cs = np.cumsum(np.concatenate([np.zeros((1,) + lg.shape[1:]), lg], 0), 0)
    out = np.exp(cs[k:] - cs[:-k]); pad = np.ones((k - 1,) + x.shape[1:]); return np.concatenate([out, pad], 0)

def simulate(printers, IDX, trend_haircut=0.0, step=1, drag=None, sell_mode="spread", tilt=None, trace=False):
    """tilt: optional dict(sig=(T, nS) 0/1 signal states on the calendar, dirs=[per printer: list of nS dicts {asset: weight change when that signal is on}]);
    signals are read monthly; targets = base + sum of active tilts (clipped at 0, renormalised); a change of state triggers a rebalance."""
    """printers: list of Printer. Lanes = printers x histories (each lane keeps only its own funds, <= Kmax slots).
    trace=True also returns every step's nominal portfolio value, cash bucket, inflation index and paycheck multiplier (lanes x steps;
    meant for a few lanes, e.g. one historical path per printer)."""
    assets = sorted({a for p in printers for a in p.alloc}); A = len(assets); K = max(len(p.alloc) for p in printers)
    Rm = np.stack([fund_returns(a) for a in assets], 1)
    for a in ("KMLMSIM", "DBMFSIM"):
        if a in assets and trend_haircut: Rm[:, assets.index(a)] -= trend_haircut / 252
    for a, x in (drag or {}).items():                              # extra annual drag on specific funds (stress tests)
        if a in assets: Rm[:, assets.index(a)] -= x / 252
    Rg = torch.tensor(_compound(1 + Rm, step) - 1, device=DEV, dtype=f32); Cg = torch.tensor(_compound(CPIR, step), device=DEV, dtype=f32)
    Fg = torch.tensor(_compound(1 + RF, step) - 1, device=DEV, dtype=f32)
    S = 252 if step == 1 else 250 // step
    divy_a = torch.tensor([DIST.get(a, (0, "o"))[0] for a in assets], device=DEV); qual_a = torch.tensor([DIST.get(a, (0, "o"))[1] == "q" for a in assets], device=DEV)
    coll_a = torch.tensor([a in COLLECTIBLE for a in assets], device=DEV); mtm_a = torch.tensor([a in MARK_TO_MARKET for a in assets], device=DEV)
    C, P = len(printers), IDX.shape[0]; N = C * P; L = IDX.shape[1]; Y = L // S; M = -(-L * 12 // S)              # months incl. a partial last year (= Y * 12 for whole years)
    ci = torch.arange(C, device=DEV).repeat_interleave(P); pi = torch.arange(P, device=DEV).repeat(C)
    pv = lambda f, dt=f32: torch.tensor([f(p) for p in printers], device=DEV, dtype=dt)[ci]
    sid_c = torch.zeros(C, K, dtype=torch.long, device=DEV); W0c = torch.zeros(C, K, device=DEV)
    for c, p in enumerate(printers):
        tot = sum(p.alloc.values())
        for k, (a, w) in enumerate(p.alloc.items()): sid_c[c, k] = assets.index(a); W0c[c, k] = w / tot
    sid = sid_c[ci]; W0 = W0c[ci]; has = W0 > 0
    any_g = any(p.glide for p in printers)
    if any_g:
        assert tilt is None, "glide and tilt can't be combined"
        W1c = W0c.clone()
        for c, p in enumerate(printers):
            if p.glide:
                assert set(p.glide) <= set(p.alloc), "glide funds must be in alloc (weight 0 allowed)"
                gt = sum(p.glide.values()); W1c[c] = torch.tensor([p.glide.get(a, 0) / gt for a in p.alloc] + [0.0] * (K - len(p.alloc)), device=DEV)
        W1 = W1c[ci]; gl = pv(lambda p: bool(p.glide), torch.bool); gy = pv(lambda p: p.glide_years); has = has | (W1 > 0)
    divy = divy_a[sid]; qual = qual_a[sid]; coll = coll_a[sid]; mtm = mtm_a[sid]; norm = ~(coll | mtm)
    band = pv(lambda p: p.band if p.band else 1e9); gap = pv(lambda p: round(p.gap_days / step), torch.long); valve = pv(lambda p: p.valve if p.valve else 1e9)
    yearly = pv(lambda p: p.yearly, torch.bool); base = pv(lambda p: p.base / 100); skim = pv(lambda p: p.skim if (p.skim is not None and p.skim >= 0) else 1e9)
    bmon = pv(lambda p: p.bucket_months); cutb = pv(lambda p: p.cut_below); cutt = pv(lambda p: p.cut_to); rest = pv(lambda p: p.restore_above)
    tx = {k: pv(lambda p, k=k: TAX[p.tax][k]) for k in ("ord", "lt", "coll", "ca")}
    r_o = tx["ord"] + tx["ca"]; r_l = tx["lt"] + tx["ca"]; r_c = tx["coll"] + tx["ca"]; r_m = 0.6 * tx["lt"] + 0.4 * tx["ord"] + tx["ca"]
    lev = pv(lambda p: p.lev); levd = pv(lambda p: p.lev_daily and p.lev != 1, torch.bool); levl = pv(lambda p: not p.lev_daily and p.lev != 1, torch.bool)
    cred = pv(lambda p: p.credit); drawb = pv(lambda p: p.draw_below); repa = pv(lambda p: p.repay_above)
    icap = pv(lambda p: p.interest_tax == "capital", torch.bool); iinv = pv(lambda p: p.interest_tax == "investment", torch.bool); ihom = pv(lambda p: p.interest_tax == "home", torch.bool)
    item = pv(lambda p: TAX[p.tax].get("item", 0)); ded = torch.zeros(N, device=DEV)
    spr = pv(lambda p: p.rate_spread / 100 / S)
    any_d = any(p.lev_daily and p.lev != 1 for p in printers); any_l = any(not p.lev_daily and p.lev != 1 for p in printers)
    any_c = any(p.credit > 0 for p in printers); any_loan = any_l or any_c
    any_bt = any(p.bucket_tax != "ordinary" for p in printers); any_bf = any(p.bucket_fill for p in printers); any_nr = any(p.no_raise_after_loss for p in printers)
    if any_bf: bfill = pv(lambda p: p.bucket_fill, torch.bool)
    any_h = any(p.harvest > 0 for p in printers)
    if any_h: hthr = pv(lambda p: p.harvest); hok = torch.tensor([a in HARVEST for a in assets], device=DEV)[sid] & (pv(lambda p: p.harvest > 0, torch.bool)[:, None])
    any_bo = any(p.bucket_offsets_loan and (p.lev != 1 and not p.lev_daily) for p in printers)
    if any_bo: boff = pv(lambda p: p.bucket_offsets_loan and (p.lev != 1 and not p.lev_daily), torch.bool)
    if any_nr: nr = pv(lambda p: p.no_raise_after_loss, torch.bool)
    if any_bt:
        bfee = pv(lambda p: 0.0019 / S if p.bucket_tax == "boxx" else 0.0)
        r_b = torch.where(pv(lambda p: p.bucket_tax == "treasury", torch.bool), tx["ord"], torch.where(pv(lambda p: p.bucket_tax == "boxx", torch.bool), r_l, r_o))
    Wt = W0.clone(); state = None
    if tilt is not None:
        SIG = torch.tensor(np.asarray(tilt["sig"], np.float32), device=DEV); nS = SIG.shape[1]; Dc = torch.zeros(C, nS, K, device=DEV)
        for c, p in enumerate(printers):
            for si, dd in enumerate(tilt["dirs"][c]):
                for a, x in dd.items(): Dc[c, si, list(p.alloc).index(a)] = x
        DIR = Dc[ci]
        def tilted(st):
            w_ = (W0 + (st[:, :, None] * DIR).sum(1)).clamp(min=0); return w_ / w_.sum(1, keepdim=True)
        state = SIG[IDX[pi, 0]]; Wt = tilted(state); has = Wt > 0
    val = Wt * torch.where(levl, lev, torch.ones_like(lev))[:, None] if any_l else Wt.clone()
    loan = torch.where(levl, lev - 1, torch.zeros_like(lev)); rloan = torch.zeros(N, device=DEV); lint = torch.zeros(N, device=DEV); lmax = loan.clone(); mcall = torch.zeros(N, dtype=torch.bool, device=DEV)
    basis = val.clone(); lastb = torch.zeros(N, K, device=DEV); bfrac = torch.ones(N, K, device=DEV)
    last = torch.zeros(N, dtype=torch.long, device=DEV); infl = torch.ones(N, device=DEV); bucket = torch.zeros(N, device=DEV); mult = torch.ones(N, device=DEV)
    gST, gLT, gC, gM, carry, intr = (torch.zeros(N, device=DEV) for _ in range(6))
    dead = torch.zeros(N, dtype=torch.bool, device=DEV); cut_ever = torch.zeros(N, dtype=torch.bool, device=DEV); minreal = torch.ones(N, device=DEV)
    spend = torch.zeros(N, M, device=DEV); yreal = torch.zeros(N, Y, device=DEV); ymult = torch.ones(N, Y, device=DEV); ybucket = torch.zeros(N, Y, device=DEV); taxreal = torch.zeros(N, device=DEV); nreb = torch.zeros(N, device=DEV)
    def realize(sell, d):
        nonlocal basis, gST, gLT, gC, gM
        frac = (sell / val.clamp(min=1e-12)).clamp(0, 1); g = sell - basis * frac; basis = basis * (1 - frac)
        stf = torch.where((d - lastb) < S, bfrac, torch.zeros_like(bfrac))
        gST += (g * stf * norm).sum(1); gLT += (g * (1 - stf) * norm).sum(1); gC += (g * coll).sum(1); gM += (g * mtm).sum(1)
    def sell_amount(amt, d):                                       # take `amt` from the most overweight funds first
        nonlocal val
        V = val.sum(1); amt = amt.clamp(max=V.clamp(min=0)); tgt = Wt * V[:, None]; exc = (val - tgt).clamp(min=0); se = exc.sum(1)
        if sell_mode == "greedy":                                  # operator default: biggest excess first, remainder from the top fund
            es, order = torch.sort(exc, dim=1, descending=True); before = torch.cumsum(es, 1) - es
            take_sorted = (amt[:, None] - before).clamp(min=0); take_sorted = torch.minimum(take_sorted, es)
            s = torch.zeros_like(val).scatter_(1, order, take_sorted); rem = (amt - s.sum(1)).clamp(min=0)
            top = order[:, :1]; s = s.scatter_add(1, top, torch.minimum(rem[:, None], val.gather(1, top) - s.gather(1, top)))
            realize(s, d); val = val - s; return s.sum(1)
        te = torch.minimum(amt, se); rem = amt - te; s1 = exc * (te / se.clamp(min=1e-12))[:, None]
        s = s1 + (val - s1) * (rem / (V - te).clamp(min=1e-12))[:, None]; realize(s, d); val = val - s; return s.sum(1)
    if any_nr: pinf = torch.ones(N, device=DEV); infl_y = torch.ones(N, device=DEV); gidx = torch.ones(N, device=DEV)
    if trace: TR = {k: torch.zeros(N, L, device=DEV) for k in ("value", "bucket", "infl", "mult")}; TR["value"][:, 0] = val.sum(1); TR["infl"][:, 0] = 1; TR["mult"][:, 0] = 1
    for d in range(1, L):
        rows = IDX[pi, d]; R = Rg[rows[:, None], sid]
        if any_d: R = torch.where(levd[:, None], lev[:, None] * R - (lev - 1)[:, None] * (Fg[rows] + spr)[:, None], R)
        if any_nr: gidx = gidx * ((val * (1 + R)).sum(1) / val.sum(1).clamp(min=1e-12))
        val = val * (1 + R); infl = infl * Cg[rows]; bi = bucket * (Fg[rows] - bfee) if any_bt else bucket * Fg[rows]
        if any_bo:                                                 # bucket parked against the loan: earns the loan rate, untaxed
            off = boff & (loan >= bucket); bo_i = bucket * (Fg[rows] + spr)
            lint -= torch.where(off, bo_i, torch.zeros_like(bo_i)); intr += torch.where(off, torch.zeros_like(bi), bi); bi = torch.where(off, bo_i, bi)
        else: intr += bi
        bucket = bucket + bi
        if any_loan:
            li = loan * (Fg[rows] + spr); loan = loan + li; lint += li; V = val.sum(1)
            if any_c: ri = rloan * (Fg[rows] + spr); rloan = rloan + ri; lint += ri
            debt = loan + rloan; mc = (debt > 0.70 * V) & ~dead     # margin call: sell so the debt is 50% of what is left (run line first)
            if bool(mc.any()):
                x = torch.where(mc, (2 * debt - V).clamp(min=0), torch.zeros_like(V)); x = torch.minimum(x, V); fr = x / V.clamp(min=1e-12)
                realize(val * fr[:, None], d); val = val * (1 - fr)[:, None]; xr = torch.minimum(x, rloan); rloan = rloan - xr; loan = loan - (x - xr); mcall |= mc
        mo = d * 12 // S; force = None
        if mo != (d - 1) * 12 // S:
            if state is not None:                                  # monthly signal check: new targets, rebalance on a change of state
                new = SIG[rows]; Wn = tilted(new); force = (Wn - Wt).abs().max(1).values > 1e-6; state = new; Wt = Wn; has = Wt > 0
            amt = base / 12 * (pinf if any_nr else infl) * mult
            if any_c:                                              # borrow the base print instead of selling in a down market
                V = val.sum(1); z = torch.zeros_like(amt)
                dr = (cred > 0) & ((V - loan - rloan) / infl < drawb) & (rloan + amt <= cred * infl) & (loan + rloan + amt <= 0.5 * V)
                got = sell_amount(torch.where(dr, z, amt), d) + torch.where(dr, amt, z); rloan = rloan + torch.where(dr, amt, z)
            else: got = sell_amount(amt, d)
            draw = bucket / bmon
            if any_bf: draw = draw + torch.where(bfill & (mult < 1), torch.minimum(bucket - draw, (1 - mult) * base / 12 * (pinf if any_nr else infl)), torch.zeros_like(draw))
            bucket = bucket - draw
            spend[:, min(mo - 1, M - 1)] = (got + draw) / infl; dead |= val.sum(1) - loan - rloan <= 1e-6
            if any_loan:
                val = torch.where(dead[:, None], torch.zeros_like(val), val); loan = torch.where(dead, torch.zeros_like(loan), loan); rloan = torch.where(dead, torch.zeros_like(rloan), rloan)
                lmax = torch.maximum(lmax, (loan + rloan) / infl)
        V = val.sum(1); w = val / V.clamp(min=1e-12)[:, None]; since = d - last
        rel = torch.where(has, w / Wt.clamp(min=1e-12), torch.zeros_like(w)).max(1).values
        drift = (w - Wt).abs().max(1).values * 100 > band
        if any_l: drift = drift | (levl & ((V / (V - loan - rloan).clamp(min=1e-12) / lev - 1).abs() > 0.15))      # leverage drifted > 15%
        trig = ((drift & (since > gap)) | (rel >= valve) | (yearly & (since >= S))) & ~dead
        if force is not None: trig = trig | (force & ~dead)
        if trig.any():
            Vt = torch.where(levl, lev * (V - loan - rloan), V) if any_l else V                               # re-lever to lev x net worth
            tgt = Wt * Vt[:, None]; over = (val > tgt) & trig[:, None]; under = (val < tgt) & trig[:, None]
            realize(torch.where(over, val - tgt, torch.zeros_like(val)), d)
            buy = torch.where(under, tgt - val, torch.zeros_like(val)); basis = basis + buy
            bfrac = torch.where(under, buy / tgt.clamp(min=1e-12), bfrac); lastb = torch.where(under, torch.full_like(lastb, float(d)), lastb)
            cost = COST * (tgt - val).abs().sum(1) * trig; val = torch.where(trig[:, None], tgt * (1 - cost / Vt.clamp(min=1e-12))[:, None], val)
            if any_l: loan = torch.where(trig & levl, loan + Vt - V, loan)
            last = torch.where(trig, torch.full_like(last, d), last); nreb += trig
        if (d + 1) % S == 0:
            y = d // S
            dist = val * divy; basis = basis + dist; divq = (dist * qual).sum(1); divo = (dist * ~qual).sum(1)
            gM += ((val - basis) * mtm).sum(1); basis = torch.where(mtm, val, basis)
            if any_h:                                                                                     # tax-loss harvest into near-twins
                lossy = hok & (val > 0) & (val < basis * (1 - hthr[:, None])) & ~dead[:, None]
                if bool(lossy.any()):
                    realize(torch.where(lossy, val, torch.zeros_like(val)), d); basis = torch.where(lossy, val, basis)
                    lastb = torch.where(lossy, torch.full_like(lastb, float(d)), lastb); bfrac = torch.where(lossy, torch.ones_like(bfrac), bfrac)
                    val = torch.where(lossy, val * (1 - 2 * COST), val)
            if any_loan:
                gM -= torch.where(icap, lint, torch.zeros_like(lint))                                    # box-spread interest: 60/40 capital loss
                inv = torch.minimum(lint, divo + intr); ded = torch.where(iinv, inv * (item * tx["ord"] + tx["ca"]), torch.where(ihom, lint * tx["ca"], torch.zeros_like(lint)))
                lint.zero_()
                if any_c:                                                                                 # back above repay_above: repay the line
                    rp = (cred > 0) & (rloan > 0) & ((val.sum(1) - loan - rloan) / infl > repa)
                    if bool(rp.any()): rloan = rloan - sell_amount(torch.where(rp, rloan, torch.zeros_like(rloan)), d)
            V = val.sum(1); net = V - loan - rloan; bonus = ((net / infl - (1 + skim)).clamp(min=0) * infl)    # bonus print -> bucket
            if bool((bonus > 0).any()):                                                                  # (sold pro rata; a loan shrinks with it)
                fr = bonus / net.clamp(min=1e-12); realize(val * fr[:, None], d); val = val * (1 - fr)[:, None]; loan = loan * (1 - fr); rloan = rloan * (1 - fr); bucket = bucket + bonus
            pos = [gST.clamp(min=0), gLT.clamp(min=0), gC.clamp(min=0), gM.clamp(min=0)]; net = gST + gLT + gC + gM + carry
            wr = (pos[0] * r_o + pos[1] * r_l + pos[2] * r_c + pos[3] * r_m) / sum(pos).clamp(min=1e-12)
            if any_bt: tax = torch.where(net > 0, net * wr, torch.zeros_like(net)) + divq * r_l + divo * r_o + intr * r_b
            else: tax = torch.where(net > 0, net * wr, torch.zeros_like(net)) + divq * r_l + (divo + intr) * r_o
            carry = net.clamp(max=0)
            if any_loan: tax = (tax - ded).clamp(min=0); ded.zero_()                                    # itemized interest deduction
            gST.zero_(); gLT.zero_(); gC.zero_(); gM.zero_(); intr.zero_()
            V = val.sum(1); f = (tax / V.clamp(min=1e-12)).clamp(0, 1); val = val * (1 - f)[:, None]; basis = basis * (1 - f)[:, None]; taxreal += tax / infl
            real = (val.sum(1) - loan - rloan) / infl; yreal[:, min(y, Y - 1)] = real
            mult = torch.where(real < cutb, cutt, torch.where(real > rest, torch.ones_like(mult), mult)); cut_ever |= real < cutb; ymult[:, min(y, Y - 1)] = mult; ybucket[:, min(y, Y - 1)] = bucket / infl
            if any_g: Wt = torch.where(gl[:, None], W0 + (W1 - W0) * ((y + 1) / gy).clamp(max=1)[:, None], Wt)
            if any_nr: pinf = torch.where(nr & (gidx < 1), pinf, pinf * infl / infl_y); infl_y = infl.clone(); gidx = torch.ones_like(gidx)
        minreal = torch.minimum(minreal, (val.sum(1) - loan - rloan) / infl)
        if trace: TR["value"][:, d] = val.sum(1) - loan - rloan; TR["bucket"][:, d] = bucket; TR["infl"][:, d] = infl; TR["mult"][:, d] = mult
    sh = lambda x: x.view(C, P, *x.shape[1:]).cpu().numpy()
    extra = {f"trace_{k}": sh(v) for k, v in TR.items()} if trace else {}
    return dict(**extra, spend=sh(spend), yreal=sh(yreal), ymult=sh(ymult), ybucket=sh(ybucket), real_end=sh((val.sum(1) - loan - rloan) / infl), minreal=sh(minreal), dead=sh(dead), cut=sh(cut_ever),
                tax=sh(taxreal / Y), reb=sh(nreb / Y), bucket_end=sh(bucket / infl), loan_end=sh((loan + rloan) / infl), loan_max=sh(lmax), margin_call=sh(mcall))

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
        **({"margin_call": float(r["margin_call"][c].mean()), "loan_max_bad": float(np.percentile(r["loan_max"][c], 90)), "loan_end_typical": float(np.median(r["loan_end"][c]))} if "loan_max" in r and (r["loan_max"][c].max() > 0 or r["margin_call"][c].any()) else {}),
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
