"""Plans for the redesigned app: the strategy roster ("characters"), their stats for one person's situation, historical battles,
the future battle, the saving-years (build) plan, and operations (setup / today / record / sync) on top of printer/operate.py.

A situation is {amount, age, account: taxable | ira | roth, bracket: low | mid}. Taxable money uses the per-fund tax model; IRA money
is simulated tax-free and each paycheck loses the bracket's income tax (12% or 31.3%); Roth is tax-free. Loan strategies need a
taxable account (IRAs can't borrow). Simulations are weekly-step estimates on reshuffled 1972-2026 history (the validated numbers in
results/ use daily steps and more histories)."""
import os, sys, json, math, uuid, datetime as dt, threading, functools, numpy as np, torch
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, ".."))
sys.path.insert(0, os.path.join(ROOT, "..", "lab"))
_argv = sys.argv; sys.argv = sys.argv[:1]
import money_printer as mp, operate as op
import stress_forward as sf
sys.argv = _argv
from dataclasses import replace
import backtest as bt
GPU = bt.GPU
P = mp.Printer; PORT = json.load(open(os.path.join(ROOT, "..", "results", "portfolios.json")))
OPS_DIR = os.path.join(ROOT, "..", "private", "ops")                     # personal state files: gitignored
INCOME_TAX = {"low": 0.12, "mid": 0.313}; TAX_PROFILE = {"low": "retiree, not working", "mid": "middle bracket"}
MP21 = {"DBMFSIM": 27, "VBRSIM": 27, "GDESIM": 21, "KMLMSIM": 15, "IAUMSIM": 8, "TQQQSIM": 2}
S21 = dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.60, restore_above=0.90, valve=4.0, bucket_tax="boxx")
BOX = dict(rate_spread=0.6, interest_tax="capital")
NAMES = {"DBMF": "Trend-following (DBMF)", "KMLM": "Trend-following (KMLM)", "VBR": "Small value stocks (VBR)", "GDE": "Stocks + gold (GDE)", "IAUM": "Gold (IAUM)",
         "GLD": "Gold (GLD)", "TQQQ": "3x Nasdaq (TQQQ)", "XLV": "Health care stocks (XLV)", "TYD": "3x Treasuries (TYD)", "VTI": "US stock market (VTI)", "BND": "US bonds (BND)",
         "UGL": "2x gold (UGL)", "TMF": "3x long Treasuries (TMF)", "TLT": "Long Treasuries (TLT)"}

# ------------------------------------------------------------------ the roster
ROSTER = [
    dict(id="mp21", name="MP-2.1", tag="Simple", where="M1 Finance", loan=False, color="s1",
         blurb="Six funds, one pie, ten minutes a month.", printer=P("MP-2.1", MP21, **S21), op="MP-2.1"),
    dict(id="box", name="MP-2.1 Boosted", tag="Box loan", where="Interactive Brokers", loan=True, color="s2",
         blurb="Same funds, plus a cheap loan for 25% more. Lower floor, bigger average.",
         printer=P("MP-2.1 box loan", MP21, **{**S21, "base": 5.25, "cut_to": 0.65, "restore_above": 0.80, "valve": 3.0}, band=10.0, lev=1.25, **BOX), op="MP-2.1 box loan"),
    dict(id="crash", name="MP-2.1 Crash Buyer", tag="Loan after a fall", where="Interactive Brokers", loan=True, color="s3",
         blurb="No loan until the account falls 20%. Then it borrows to buy cheap.",
         printer=P("MP-2.1 crash buyer", MP21, **S21, lev_dd=0.20, lev_dd_to=1.25, **BOX), op="MP-2.1 crash buyer"),
    dict(id="mp2", name="MP-2", tag="Original", where="M1 Finance", loan=False, color="s4",
         blurb="The first version: GLD, a tighter safety valve.", printer=P("MP-2", mp.load_alloc("MP-2 engine"), base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65), op="MP-2"),
    dict(id="ch12", name="CH-12", tag="Calmer, older", where="M1 Finance", loan=False, color="s5",
         blurb="Crisis-hedged mix with Treasuries and health care.", printer=P("CH-12", mp.load_alloc("Crisis-Hedged 12 (no UUP)")), op="CH-12"),
    dict(id="three", name="Three-Fund", tag="Starter", where="Any broker", loan=False, color="s6",
         blurb="VBR, KMLM, gold. A flat paycheck, no bonus rules.", printer=P("Three-Fund", {"VBRSIM": 35, "KMLMSIM": 35, "IAUMSIM": 30}, base=5.25, skim=None, cut_below=-1), op=None),
    dict(id="6040", name="60/40", tag="Classic", where="Any broker", loan=False, color="s7",
         blurb="60% US stocks, 40% bonds, same paycheck rules.", printer=P("60/40", mp.load_alloc("60/40"), **S21), op=None),
    dict(id="vti", name="All Stocks", tag="Classic", where="Any broker", loan=False, color="s8",
         blurb="100% US stock market, same paycheck rules.", printer=P("All Stocks", mp.load_alloc("VTI (100% US stocks)"), **S21), op=None),
]
BY = {r["id"]: r for r in ROSTER}
BUILD = {"steady": dict(name="Steady", alloc={t: int(w) for t, w in PORT["IRA Steady 30"]["alloc"].items()}, blurb="Worst drops near 30%."),
         "faster": dict(name="Faster", alloc={t: int(w) for t, w in PORT["IRA Accelerator 40"]["alloc"].items()}, blurb="Grows faster. Drops near 40%.")}

def roster():
    out = []
    for r in ROSTER:
        p = r["printer"]
        out.append(dict(id=r["id"], name=r["name"], tag=r["tag"], where=r["where"], loan=r["loan"], color=r["color"], blurb=r["blurb"], operable=bool(r["op"]),
                        funds=[dict(t=t.replace("SIM", ""), w=w, name=NAMES.get(t.replace("SIM", ""), t.replace("SIM", ""))) for t, w in sorted(p.alloc.items(), key=lambda x: -x[1])],
                        rules=rules(p)))
    return out

def rules(p):
    r = [f"Pay yourself {p.base:g}% of the start each year, raised with inflation, paid monthly."]
    if p.skim is not None and p.skim >= 0: r.append(f"Each January, anything above {100 + p.skim * 100:.0f}% of the start goes to a cash bucket that pays 1/{p.bucket_months} a month extra.")
    if p.cut_below > 0: r.append(f"If the account falls below {p.cut_below * 100:.0f}% of the start, the paycheck drops to {p.cut_to * 100:.0f}% until it is back above {p.restore_above * 100:.0f}%.")
    if p.lev > 1: r.append(f"Borrow {p.lev - 1:.0%} more with an SPX box loan (about T-bill + {p.rate_spread:g}%).")
    if p.lev_dd > 0: r.append(f"Borrow {p.lev_dd_to - 1:.0%} more only while the account is {p.lev_dd * 100:.0f}% below its high.")
    r.append(f"Rebalance when a fund is {p.band:g}+ points off (at most once a year) or reaches {p.valve:g}x its target.")
    return r

# ------------------------------------------------------------------ one situation -> printers with the right taxes and loan floor
def situation(q):
    amt = float(q.get("amount", 100000)); age = int(q.get("age", 60)); acct = q.get("account", "taxable"); br = q.get("bracket", "low")
    if acct not in ("taxable", "ira", "roth") or br not in INCOME_TAX: raise ValueError("bad situation")
    years = int(max(15, min(50, 100 - age)))
    return dict(amount=amt, age=age, account=acct, bracket=br, years=years, keep=(1 - INCOME_TAX[br]) if acct == "ira" else 1.0,
                tax=TAX_PROFILE[br] if acct == "taxable" else "none (IRA/Roth)")

def tuned(r, s):
    """The roster printer for this situation; None if it can't be used (loans need a taxable account)."""
    p = r["printer"]
    if r["loan"] and s["account"] != "taxable": return None
    kw = dict(tax=s["tax"], name=r["id"])
    if r["loan"] and s["amount"] >= 130000: kw.update(lev_floor=115000 / s["amount"], lev_resume=130000 / s["amount"])
    if s["account"] != "taxable" and p.bucket_tax != "ordinary": kw["bucket_tax"] = "ordinary"
    return replace(p, **kw)

@functools.lru_cache(maxsize=64)
def _sim(key):
    s = json.loads(key); ids = s.pop("ids"); prs = [(i, tuned(BY[i], s)) for i in ids]; prs = [(i, p) for i, p in prs if p is not None]
    if not prs: return {}
    IDXb = mp.make_idx(1000, s["years"], step=5, seed=3101); IDXs = mp.make_idx(1000, s["years"], step=5, seed=3102)
    with GPU:
        rb = mp.simulate([p for _, p in prs], IDXb, step=5); rs = mp.simulate([p for _, p in prs], IDXs, step=5, trend_haircut=0.04)
    out = {}; Z = s["amount"]; k = s["keep"]; Y = s["years"]
    for c, (i, p) in enumerate(prs):
        sc = mp.score(rb, c); st = mp.score(rs, c); yrs = rb["spend"][c][:, :Y * 12].reshape(-1, Y, 12).sum(2) * k
        bal = np.c_[np.ones(yrs.shape[0]), rb["yreal"][c][:, :Y] + rb["ybucket"][c][:, :Y]]
        mo = lambda x: float(x * Z * k / 12)
        out[i] = dict(floor=mo(p.base / 100), first10=mo(sc["print_y1_10_typ"]), first10_bad=mo(sc["print_y1_10_bad"]), life=mo(sc["print_typical"]), life_bad=mo(sc["print_bad"]),
                      never_cut=sc["base_never_cut"], dry=sc["run_dry"], below_start=sc["lose_value"], deep_dip=sc["deep_dip"], left=float(sc["left_typical"] * Z),
                      stress_life=mo(st["print_typical"]), stress_dry=st["run_dry"], margin_call=sc.get("margin_call", 0.0),
                      fan=dict(years=list(range(Y + 1)), pay=[np.percentile(yrs, q, axis=0).round(5).tolist() for q in (10, 50, 90)],
                               bal=[np.percentile(bal, q, axis=0).round(4).tolist() for q in (10, 50, 90)]))
    return out

def profiles(q):
    """Character stats for the chosen strategies in this situation, with 0-10 bars relative to the group."""
    s = situation(q); ids = [i for i in q.get("ids", [r["id"] for r in ROSTER]) if i in BY][:6]
    raw = _sim(json.dumps({**s, "ids": ids}, sort_keys=True))
    out = []
    for i in ids:
        r = BY[i]; x = raw.get(i)
        if x is None: out.append(dict(id=i, available=False, why="Loans need a taxable account (IRAs can't borrow).")); continue
        p = tuned(r, s); funds = len(p.alloc)
        ease = 10 - (funds - 3) * 0.8 - (3 if r["loan"] else 0) - (0.5 if p.skim is not None and p.skim >= 0 else 0)
        out.append(dict(id=i, available=True, **{k: v for k, v in x.items() if k != "fan"}, fan=x["fan"],
                        needs_pm=r["loan"] and s["amount"] < 110000, ease=round(max(1, min(10, ease)), 1)))
    av = [o for o in out if o["available"]]
    if av:
        def bar(key, hi=True):                                     # 0-10 from zero, relative to the best in the group (lower-is-better uses 1 - value)
            val = lambda o: o[key] if hi else 1 - o[key]; top = max(val(o) for o in av) or 1
            for o in av: o.setdefault("bars", {})[key] = round(10 * max(0.0, val(o)) / top, 1)
        for key, hi in (("life", True), ("floor", True), ("never_cut", True), ("deep_dip", False), ("stress_life", True), ("left", True)): bar(key, hi)
        for o in av: o["bars"]["ease"] = o["ease"]
    return dict(situation=s, strategies=out)

# ------------------------------------------------------------------ battles
CAL = np.asarray(mp.h.CAL)
def _day(s): return int(np.searchsorted(CAL, int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.UTC).timestamp())))
EPISODES = [("1973", "1970s inflation", "1973-01-11", 8, "Prices up 9% a year, stocks down 48%."),
            ("1987", "1987 crash", "1987-08-25", 4, "Stocks fell 22% in one day."),
            ("2000", "Dot-com bust", "2000-03-24", 8, "Tech bubble burst; Nasdaq fell 78%."),
            ("2008", "2008 crisis", "2007-10-09", 8, "Banks failed; stocks fell 55%."),
            ("2020", "Covid crash", "2020-02-19", 4, "Stocks fell 34% in five weeks."),
            ("2022", "2022 rate shock", "2022-01-03", 4, "Stocks and bonds fell together.")]

@functools.lru_cache(maxsize=32)
def _battles(key):
    s = json.loads(key); ids = s.pop("ids"); prs = [(i, tuned(BY[i], s)) for i in ids]; prs = [(i, p) for i, p in prs if p is not None]
    out = []
    for code, name, start, yrs, story in EPISODES:
        i0 = _day(start); L = min(yrs * 252, len(CAL) - 2 - i0); L -= L % 21; IDX = torch.tensor((i0 + np.arange(L))[None, :], device=mp.DEV)
        with GPU: r = mp.simulate([p for _, p in prs], IDX, trace=True)
        step = max(1, L // 160); fighters = []
        for c, (i, p) in enumerate(prs):
            real = (r["trace_value"][c, 0] + r["trace_bucket"][c, 0]) / r["trace_infl"][c, 0]; dd = real / np.maximum.accumulate(real) - 1
            M = L * 12 // 252; paid = r["spend"][c, 0, :M] * s["amount"] * s["keep"]          # spend = each month's paycheck as a share of the start
            fighters.append(dict(id=i, path=(real[::step] * 100).round(2).tolist(), low=float(real.min() * 100), end=float(real[-1] * 100), worst_drop=float(dd.min() * 100),
                                 paid=float(paid.mean()), cut=bool(r["cut"][c, 0])))
        best = max(fighters, key=lambda f: (f["end"] + 0.5 * f["low"]))["id"] if fighters else None
        out.append(dict(code=code, name=name, start=start, years=round(L / 252, 1), story=story, step_days=step, fighters=fighters, winner=best))
    scen = []
    for k, mv in sf.SC.items():
        row = dict(name=k.split(" (")[0], detail=k[k.find("(") + 1:-1] if "(" in k else "", moves={})
        for i, p in prs:
            m = sum(w / 100 * sf.move("GLDSIM" if t in ("IAUMSIM", "GLDMSIM") else t, mv) for t, w in p.alloc.items()) / (sum(p.alloc.values()) / 100)
            row["moves"][i] = round(m * (p.lev if p.lev > 1 else 1.0), 1)
        scen.append(row)
    return dict(episodes=out, scenarios=scen)

def battles(q):
    s = situation(q); ids = [i for i in q.get("ids", []) if i in BY][:6]
    return _battles(json.dumps({**s, "ids": ids}, sort_keys=True))

# ------------------------------------------------------------------ saving years
@functools.lru_cache(maxsize=64)
def _build(key):
    q = json.loads(key); age = q["age"]; s0 = q["saved"]; m = q["monthly"]; want = q["want"]; ss = q["ss"]; acct = q["account"]
    al = BUILD[q["mix"]]["alloc"]; assets = list(al); W0 = torch.tensor([al[t] / 100 for t in assets], device=mp.DEV, dtype=mp.f32)
    need = max(0.0, want - ss) * 12 / 0.0575 / ((1 - 0.12) if acct == "trad" else 1.0); drag = 0.004 if acct == "taxable" else 0.0
    Y = max(5, 90 - age); step = 5; Sy = 250 // step; IDX = mp.make_idx(1000, Y, step=step, seed=5151)
    levels = [m, m + 100, m + 250, m + 500]; nL = len(levels); Pn = IDX.shape[0]; N = nL * Pn
    Rm = np.stack([mp.fund_returns(t) for t in assets], 1) - drag / 252
    Rg = torch.tensor(mp._compound(1 + Rm, step) - 1, device=mp.DEV, dtype=mp.f32); Cg = torch.tensor(mp._compound(mp.CPIR, step), device=mp.DEV, dtype=mp.f32)
    li = torch.arange(nL, device=mp.DEV).repeat_interleave(Pn); pi = torch.arange(Pn, device=mp.DEV).repeat(nL)
    contrib = torch.tensor(levels, device=mp.DEV, dtype=mp.f32)[li]; val = W0[None, :].repeat(N, 1) * s0; infl = torch.ones(N, device=mp.DEV)
    last = torch.zeros(N, dtype=torch.long, device=mp.DEV); yreal = torch.zeros(N, Y, device=mp.DEV)
    with GPU:
        for d in range(1, Y * Sy):
            rows = IDX[pi, d]; val = val * (1 + Rg[rows]); infl = infl * Cg[rows]
            if (d * 12) // Sy != ((d - 1) * 12) // Sy:                    # monthly saving into the most underweight funds first
                amt = contrib * infl; V = val.sum(1); tgt = W0 * (V + amt)[:, None]; short = (tgt - val).clamp(min=0); ssum = short.sum(1)
                fill = torch.minimum(amt, ssum); val = val + short * (fill / ssum.clamp(min=1e-9))[:, None] + W0 * (amt - fill)[:, None]
            V = val.sum(1); w = val / V.clamp(min=1e-9)[:, None]
            trig = (((w - W0).abs().max(1).values * 100 > 6) & (d - last > Sy)) | ((w / W0).max(1).values >= 2.0)
            if bool(trig.any()): val = torch.where(trig[:, None], W0 * V[:, None], val); last = torch.where(trig, torch.full_like(last, d), last)
            if (d + 1) % Sy == 0: yreal[:, (d + 1) // Sy - 1] = val.sum(1) / infl
    Wr = yreal.view(nL, Pn, Y).cpu().numpy(); ages = age + 1 + np.arange(Y)
    def retire(k):
        hit = Wr[k] >= need if need > 0 else np.ones_like(Wr[k], bool); first = np.where(hit.any(1), ages[hit.argmax(1)], 999)
        pct = lambda p: int(np.percentile(first, p)) if np.percentile(first, p) < 999 else None
        return dict(typical=pct(50), lucky=pct(25), unlucky=pct(75), bad=pct(90), never=float((first == 999).mean()),
                    by={a: float((first <= a).mean()) for a in (50, 55, 60, 62, 65, 67, 70)})
    k0 = retire(0)
    return dict(need=need, levels=[dict(monthly=lv, **retire(k)) for k, lv in enumerate(levels)], retire=k0,
                ages=[age] + ages.tolist(), bal=[[s0] + np.percentile(Wr[0], q, axis=0).round(0).tolist() for q in (10, 50, 90)],
                mix=dict(name=BUILD[q["mix"]]["name"], blurb=BUILD[q["mix"]]["blurb"],
                         funds=[dict(t=t.replace("SIM", ""), w=w, name=NAMES.get(t.replace("SIM", ""), t.replace("SIM", ""))) for t, w in sorted(al.items(), key=lambda x: -x[1])]))

def build(q):
    k = dict(age=int(q.get("age", 35)), saved=float(q.get("saved", 0)), monthly=float(q.get("monthly", 500)), want=float(q.get("want", 4000)), ss=float(q.get("ss", 0)),
             account=q.get("account", "roth") if q.get("account") in ("roth", "trad", "taxable") else "roth", mix=q.get("mix", "steady") if q.get("mix") in BUILD else "steady")
    k["age"] = max(18, min(80, k["age"])); return _build(json.dumps(k, sort_keys=True))

# ------------------------------------------------------------------ operations on top of printer/operate.py
_PRICES = {}; _LOCK = threading.Lock(); PLANS = {}
def _prices(tickers):
    now = dt.datetime.now().timestamp(); key = tuple(sorted(tickers))
    if key in _PRICES and now - _PRICES[key][0] < 600: return _PRICES[key][1]
    p = op.live_prices(list(tickers)); _PRICES[key] = (now, p); return p
@functools.lru_cache(maxsize=4)
def _cpi(day): return op.live_cpi()
@functools.lru_cache(maxsize=4)
def _market(day): return op.live_market()

def _path(name):
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_") or "plan"; return os.path.join(OPS_DIR, safe + ".json")

def _trades(p, st):
    rows = []
    for s in p["steps"]:
        tr = []
        for t, dollars in sorted(s["trades"].items(), key=lambda kv: kv[1]):
            px = p["prices"][t]; row = dict(t=t, side="SELL" if dollars < 0 else "BUY", shares=round(abs(dollars) / px, 4), price=px, dollars=round(abs(dollars), 2))
            if dollars < 0 and st["holdings"].get(t, {}).get("lots"):
                picks, lt, stg, tax = op.tax_lots(st, t, -dollars, px, p["date"], st.get("tax", "retiree, not working")); row.update(gain=round(lt + stg, 2), tax=round(tax, 2))
            tr.append(row)
        rows.append(dict(step=s["step"], why=s["why"], trades=tr, spend=s.get("spend"), base=s.get("base"), bucket_draw=s.get("bucket_draw"), skim=s.get("skim"), box=s.get("box")))
    return rows

def _calendar(st, today):
    d = dt.date.fromisoformat(today); nm = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    while nm.weekday() >= 5 or (nm.month == 1 and nm.day == 1): nm += dt.timedelta(days=1)       # first trading day (skips New Year's Day)
    ev = [dict(date=nm.isoformat(), what="Monthly paycheck: open Today")]
    jan = dt.date(d.year + 1, 1, 2)
    while jan.weekday() >= 5: jan += dt.timedelta(days=1)
    ev.append(dict(date=jan.isoformat(), what="January: skim, guardrail check, raise for inflation"))
    rb = dt.date.fromisoformat(st["last_rebalance"]) + dt.timedelta(days=st["settings"]["min_days"]); ev.append(dict(date=rb.isoformat(), what="Earliest yearly rebalance (only if a fund drifted)"))
    box = (st.get("loan") or {}).get("box")
    if box: ev.append(dict(date=(dt.date.fromisoformat(box["expiry"]) - dt.timedelta(days=7)).isoformat(), what=f"Roll the box loan (expires {box['expiry']})"))
    return sorted(ev, key=lambda e: e["date"])

def ops_list():
    os.makedirs(OPS_DIR, exist_ok=True)
    return [dict(name=f[:-5], printer=json.load(open(os.path.join(OPS_DIR, f)))["printer"]) for f in sorted(os.listdir(OPS_DIR)) if f.endswith(".json")]

def ops_setup(q):
    """Exact setup checklist + first orders for a strategy, at today's prices (nothing is saved)."""
    r = BY[q["id"]]; amt = float(q["amount"]); acct = q.get("account", "taxable"); tax = TAX_PROFILE.get(q.get("bracket", "low")) if acct == "taxable" else "IRA"
    if not r["op"]: raise ValueError("This one is for comparison only.")
    if r["loan"] and acct != "taxable": raise ValueError("Loans need a taxable account.")
    cfg = op.PRINTERS[r["op"]]; today = dt.date.today().isoformat(); prices = _prices(cfg["targets"]); cpi = _cpi(today)
    st, p = op.init_state(r["op"], amt, today, prices, cpi, tax if tax in op.TAXP else "IRA", market=_market(today) if r["loan"] else None)
    ibkr = r["where"] == "Interactive Brokers"; steps = [dict(title="Keep a cash cushion", text="Keep 12 months of living costs in a high-yield savings account. Not in the plan.")]
    if ibkr:
        steps += [dict(title="Open the account", text="Interactive Brokers: IBKR Pro, individual, margin account, in the retiree's name. Optionally add a trusted advisor as an authorized trader."),
                  dict(title="Ask for two permissions", text="Options trading (spreads) and portfolio margin. Portfolio margin needs $110,000+."),
                  dict(title="Deposit", text=f"${amt:,.0f}.")]
        if r["id"] == "crash": steps.append(dict(title="No loan yet", text="It only borrows after a 20% fall. Today shows when."))
    else:
        steps += [dict(title="Open the account", text="M1 Finance: individual" + (" IRA (roll the money in)." if acct != "taxable" else " taxable account.")),
                  dict(title="Deposit", text=f"${amt:,.0f}."), dict(title="Make a pie", text="Add these six slices with these exact weights. Then press Invest.")]
    steps.append(dict(title="Cash bucket", text="Hold the bonus cash in BOXX. It starts at $0." if acct == "taxable" else "Hold the bonus cash in a Treasury money fund. It starts at $0."))
    steps.append(dict(title="Save your tracker", text="Press Create tracker below. Then open Today on the first trading day of every month."))
    return dict(strategy=r["id"], name=r["name"], where=r["where"], steps=steps, orders=_trades(p, st), date=today, notes=["Prices are today's; fill at market or a limit near them."])

def ops_create(q):
    r = BY[q["id"]]; name = q.get("name") or "plan"; path = _path(name)
    if os.path.exists(path): raise ValueError(f"A tracker called {name!r} already exists.")
    amt = float(q["amount"]); acct = q.get("account", "taxable"); tax = TAX_PROFILE.get(q.get("bracket", "low")) if acct == "taxable" else "IRA"
    cfg = op.PRINTERS[r["op"]]; today = q.get("date") or dt.date.today().isoformat(); prices = _prices(cfg["targets"]); cpi = _cpi(today)
    st, p = op.init_state(r["op"], amt, today, prices, cpi, tax, market=_market(today) if r["loan"] else None)
    st = op.apply(st, p, today, tax); os.makedirs(OPS_DIR, exist_ok=True); json.dump(st, open(path, "w"), indent=1)
    return dict(name=os.path.basename(path)[:-5])

def ops_today(q):
    path = _path(q["name"]); st = json.load(open(path)); today = q.get("date") or dt.date.today().isoformat()
    prices = _prices(st["targets"]); cpi = _cpi(today); market = _market(today) if st.get("loan") else None
    p = op.plan(st, today, prices, cpi, deposit=float(q.get("deposit") or 0), market=market); token = uuid.uuid4().hex; PLANS[token] = (q["name"], p)
    w = p["watch"]; V = w["account_value"]; netv = w.get("net_value", V)
    def dist(line, below=True): return None if not line else round((netv - line) / netv * 100 if below else (line - netv) / netv * 100, 1)
    triggers = [dict(what="Skim to the cash bucket (January)", line=w["skim_line"], away=dist(w["skim_line"], False), dir="above"),
                dict(what="Paycheck cut (January)", line=w["guardrail_line"], away=dist(w["guardrail_line"]), dir="below")]
    if w.get("floor_line"): triggers.append(dict(what="Pay the loan off", line=w["floor_line"], away=dist(w["floor_line"]), dir="below"))
    if w.get("crash_line"): triggers.append(dict(what="Crash buyer borrows", line=w["crash_line"], away=dist(w["crash_line"]), dir="below"))
    if w.get("margin_call_line"): triggers.append(dict(what="Broker margin call (funds value)", line=w["margin_call_line"], away=round((V - w["margin_call_line"]) / V * 100, 1), dir="below"))
    holdings = [dict(t=t, shares=round(h["shares"], 4), price=prices[t], value=round(h["shares"] * prices[t], 2), target=st["targets"][t],
                     now=round(h["shares"] * prices[t] / V * 100, 1) if V else 0, valve=st["settings"]["valve"] * st["targets"][t]) for t, h in st["holdings"].items() if t in prices]
    paid = st.get("paid", [])[-12:]
    return dict(token=token, name=q["name"], printer=st["printer"], date=today, actions=_trades(p, st), notes=p["notes"], holdings=holdings,
                status=dict(value=V, net=netv, debt=w.get("debt"), leverage=w.get("leverage"), bucket=p["bucket_after"], real_pct=w["real_value_pct"], guardrail=p["guardrail"],
                            start_value=st["baseline"]["start_value"], start_date=st["baseline"]["start_date"]),
                triggers=triggers, calendar=_calendar(st, today), paid=paid, nothing=not p["steps"])

def ops_commit(q):
    name, p = PLANS.pop(q["token"]); path = _path(name); st = json.load(open(path))
    st = op.apply(st, p, p["date"], st.get("tax", "retiree, not working")); json.dump(st, open(path, "w"), indent=1); return dict(ok=True)

def ops_sync(q):
    path = _path(q["name"]); st = json.load(open(path)); today = dt.date.today().isoformat(); prices = _prices(st["targets"])
    for t, sh in (q.get("shares") or {}).items():
        t = t.upper(); sh = float(sh); h = st["holdings"].setdefault(t, {"shares": 0.0, "lots": []}); diff = sh - h["shares"]
        if diff > 1e-9: h["lots"].append(dict(shares=diff, cost=prices.get(t, 0), date=today))
        elif diff < -1e-9:
            need = -diff; h["lots"].sort(key=lambda L: -L["cost"])
            for L in h["lots"]: take = min(L["shares"], need); L["shares"] -= take; need -= take
            h["lots"] = [L for L in h["lots"] if L["shares"] > 1e-9]
        h["shares"] = sh
    if q.get("bucket") not in (None, ""): st["cash_bucket"] = float(q["bucket"])
    if q.get("debt") not in (None, "") and st.get("loan"): st["loan"]["balance"] = float(q["debt"]); st["loan"]["last_accrual"] = today
    json.dump(st, open(path, "w"), indent=1); return dict(ok=True)
