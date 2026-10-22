"""Money Printer OPERATOR: tells you exactly what to do, from the current situation, using the same rules that were tested.

  python3 printer/operate.py init   --state printer/ex_state.json --printer MP-2 --value 90000      # first purchase plan
  python3 printer/operate.py run    --state printer/ex_state.json [--date 2026-12-01] [--deposit 100000] [--bucket 1234] [--commit]
  python3 printer/operate.py status --state printer/ex_state.json
  python3 printer/operate.py sync   --state printer/ex_state.json --shares "DBMF=471.389,VBR=63.364,..." [--bucket 1234]   # match the broker

Run it at least once a month (the 1st trading day is ideal; any day works). It decides from the state + today's prices + CPI:
  1 DEPOSIT     new money (e.g. an insurance payout) goes to the most underweight funds first and raises the baseline
  2 YEAR-END    first run of a new year (January): skim anything above (1+skim) x inflation-adjusted baseline into the cash
                bucket; then the guardrail (real value < cut_below x baseline -> base print x cut_to; > restore_above -> back to 1)
  3 MONTHLY     first run of a new month: base print = base% x baseline x inflation / 12 x guardrail; sold from the most
                overweight funds first; plus 1/bucket_months of the cash bucket
  4 SAFETY      any fund at valve x its target weight -> rebalance everything now
  5 DRIFT       any fund more than `band` points off target AND at least min_days since the last rebalance -> rebalance
  6 TAXES       sales use the highest-cost long-term lots first (then highest-cost short-term); estimated gains and tax shown
With --commit the trades are recorded in the state file as done (at the quoted prices); otherwise nothing changes.
Rules and numbers match printer/money_printer.py (the simulator); printer/replay.py checks that they reproduce it."""
import os, sys, json, math, argparse, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(ROOT, ".."))

PRINTERS = {   # ticker -> target %, and printer settings (from results/PRINTER_SEARCH.md / MONEY_PRINTER.md)
    "MP-2": dict(targets={"DBMF": 27, "VBR": 27, "GDE": 21, "KMLM": 15, "GLD": 8, "TQQQ": 2},
                 settings=dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65, restore_above=0.90, band=6.0, min_days=365, valve=2.0)),
    # MP-2.1 (results/IMPROVE.md, 2026-10-21): MP-2 with IAUM for GLD (same gold, 0.09% fee), the guardrail cutting the base to 60%,
    # and the safety valve at 4x; keep the cash bucket in BOXX (box-spread ETF, taxed as long-term gains)
    "MP-2.1": dict(targets={"DBMF": 27, "VBR": 27, "GDE": 21, "KMLM": 15, "IAUM": 8, "TQQQ": 2},
                   settings=dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.60, restore_above=0.90, band=6.0, min_days=365, valve=4.0)),
    # with an SPX box-spread loan at IBKR/Schwab (results/IMPROVE.md, results/CREDIT.md): always 1.25x, or only after a 20% fall
    "MP-2.1 box loan": dict(targets={"DBMF": 27, "VBR": 27, "GDE": 21, "KMLM": 15, "IAUM": 8, "TQQQ": 2},
                            settings=dict(base=5.25, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.65, restore_above=0.80, band=10.0, min_days=365, valve=3.0),
                            loan=dict(lev=1.25, dd=0.0, dd_to=1.0, spread=0.6)),
    "MP-2.1 crash buyer": dict(targets={"DBMF": 27, "VBR": 27, "GDE": 21, "KMLM": 15, "IAUM": 8, "TQQQ": 2},
                               settings=dict(base=5.75, skim=0.40, bucket_months=48, cut_below=0.70, cut_to=0.60, restore_above=0.90, band=6.0, min_days=365, valve=4.0),
                               loan=dict(lev=1.0, dd=0.20, dd_to=1.25, spread=0.6)),
    "CH-12": dict(targets={"DBMF": 25, "KMLM": 16, "GLD": 15, "VBR": 15, "XLV": 13, "TYD": 11, "TQQQ": 5},
                  settings=dict(base=4.0, skim=0.25, bucket_months=36, cut_below=0.70, cut_to=0.80, restore_above=0.90, band=6.0, min_days=365, valve=2.0)),
    "MP-Fortress": dict(targets={"KMLM": 22, "VBR": 20, "DBMF": 16, "GLD": 15, "UGL": 8, "XLV": 7, "SPMO": 5, "UUP": 4, "TQQQ": 3},
                        settings=dict(base=4.5, skim=0.35, bucket_months=60, cut_below=0.65, cut_to=0.80, restore_above=0.90, band=6.0, min_days=365, valve=2.0)),
}
TAXP = {"retiree, not working": dict(ord=.10, lt=0, coll=.10, ca=.02), "retiree, working $40k": dict(ord=.12, lt=0, coll=.12, ca=.05),
        "middle bracket": dict(ord=.22, lt=.15, coll=.22, ca=.093), "IRA": dict(ord=0, lt=0, coll=0, ca=0)}
COLLECTIBLE = {"GLD", "GLDM", "IAUM", "IAU"}; K1 = {"UUP", "UGL"}

# ------------------------------------------------------------------ market data
def live_prices(tickers):
    from engine.data import sources as src
    out = {}
    for t in tickers:
        ts, v = src.yahoo(t, field="close"); out[t] = float(v[-1])
    return out

def live_cpi():
    """Latest CPI-U level (testfol.io INFLATION series; falls back to the cached indicator file)."""
    try:
        import urllib.request
        body = {"start_date": "2020-01-01", "end_date": "2100-01-01", "start_val": 1, "adj_inflation": False, "cashflow": 0, "cashflow_freq": "Yearly", "rolling_window": 60,
                "backtests": [{"invest_dividends": True, "rebalance_freq": "Yearly", "rebalance_offset": 0, "drag": 0, "allocation": {"INFLATION": 100}}]}
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://testfol.io/api/backtest", json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}), timeout=120))
        return float(d["charts"]["history"][1][-1]) * 1e6        # relative level; only ratios are used
    except Exception:
        I = json.load(open(os.path.join(ROOT, "..", "strategy", "data_indicators.json"))); return float(I["INFLATION"]["v"][-1]) * 1e6 / I["INFLATION"]["v"][0]

# ------------------------------------------------------------------ core rules (pure functions, shared with replay.py)
def value(state, prices): return sum(h["shares"] * prices[t] for t, h in state["holdings"].items())

def weights(state, prices):
    V = value(state, prices); return {t: (state["holdings"].get(t, {"shares": 0})["shares"] * prices[t] / V if V > 0 else 0.0) for t in state["targets"]}

SPREAD = False                                                  # True = sell from every overweight fund in proportion (simulator style)
MIN_TRADE = 25.0
def sell_plan(state, prices, amount):
    """Dollars to sell per fund to raise `amount`, most overweight funds first.
    Default (practical): take it from the most overweight fund, then the next, ... (usually 1-2 funds, no trade under MIN_TRADE).
    SPREAD: from every overweight fund in proportion to its excess, then pro-rata (exactly the simulator's rule)."""
    if not SPREAD:
        V = value(state, prices); T = {t: w / 100 for t, w in state["targets"].items()}; out = {}; need = min(amount, V)
        cur = {t: state["holdings"].get(t, {"shares": 0})["shares"] * prices[t] for t in T}
        order = sorted(T, key=lambda t: -(cur[t] - T[t] * V))              # most overweight vs today's targets
        for t in order:                                                    # use each fund's excess, biggest first
            exc = cur[t] - T[t] * V
            if need <= 0.005 or exc < MIN_TRADE: break
            take = min(need, exc); out[t] = take; need -= take
        if need > 0.005:                                                   # remainder from the most overweight fund
            out[order[0]] = out.get(order[0], 0.0) + min(need, cur[order[0]] - out.get(order[0], 0.0))
        return {t: x for t, x in out.items() if x > 0.005}
    V = value(state, prices); T = {t: w / 100 for t, w in state["targets"].items()}
    cur = {t: state["holdings"].get(t, {"shares": 0})["shares"] * prices[t] for t in T}
    exc = {t: max(0.0, cur[t] - T[t] * V) for t in T}; se = sum(exc.values()); take = min(amount, se); out = {t: (exc[t] / se * take if se > 0 else 0.0) for t in T}
    rest = min(amount, V) - take; left = {t: cur[t] - out[t] for t in T}; sl = sum(left.values())
    for t in T: out[t] += left[t] / sl * rest if sl > 0 else 0.0
    return {t: x for t, x in out.items() if x > 0.005}

def buy_plan(state, prices, amount):
    """Dollars to buy per fund with `amount` of new money: most underweight funds first, then at target weights."""
    V = value(state, prices) + amount; T = {t: w / 100 for t, w in state["targets"].items()}
    cur = {t: state["holdings"].get(t, {"shares": 0})["shares"] * prices[t] for t in T}
    short = {t: max(0.0, T[t] * V - cur[t]) for t in T}; ss = sum(short.values()); fill = min(amount, ss)
    out = {t: (short[t] / ss * fill if ss > 0 else 0.0) for t in T}; rest = amount - fill
    for t in T: out[t] += T[t] * rest
    return {t: x for t, x in out.items() if x > 0.005}

def rebalance_plan(state, prices, total=None):
    V = value(state, prices) if total is None else total; out = {}
    for t, w in state["targets"].items():
        d = w / 100 * V - state["holdings"].get(t, {"shares": 0})["shares"] * prices[t]
        if abs(d) > 0.005: out[t] = d                              # + buy, - sell
    return out

def third_friday(y, m):
    d = dt.date(y, m, 15); return d + dt.timedelta(days=(4 - d.weekday()) % 7)
def box_expiry(today, min_days=80):
    """The SPX monthly expiry (third Friday) at least `min_days` away: a ~3-month box."""
    y, m = today.year, today.month
    while True:
        e = third_friday(y, m)
        if (e - today).days >= min_days: return e
        m += 1; y, m = (y + 1, 1) if m > 12 else (y, m)

def box_order(debt, today, spx, rate):
    """A short SPX box that borrows about `debt` until a ~3-month expiry: you receive the credit now and owe the face at expiry.
    Strikes 5 points apart -> face in $500 steps; strikes centred on today's SPX (any strikes work; near the money trades best)."""
    e = box_expiry(today); T = (e - today).days / 365; face = math.ceil(debt * (1 + rate) ** T / 500) * 500; width = face // 100
    k1 = int(round((spx - width / 2) / 5) * 5); k2 = k1 + int(width); credit = face / (1 + rate) ** T
    return dict(expiry=e.isoformat(), face=float(face), width=int(width), k1=k1, k2=k2, credit=float(credit), rate=float(rate), days=(e - today).days,
                legs=[f"BUY 1 SPX {e:%b %d %Y} {k1} call", f"SELL 1 SPX {e:%b %d %Y} {k2} call", f"SELL 1 SPX {e:%b %d %Y} {k1} put", f"BUY 1 SPX {e:%b %d %Y} {k2} put"])

def live_market():
    """S&P 500 level and today's ~3-month box-spread rate (boxtrades.com; fallback: 3-month T-bill + 0.6)."""
    from engine.data import sources as src
    out = {}
    try: ts, v = src.yahoo("^GSPC", field="close"); out["spx"] = float(v[-1])
    except Exception: out["spx"] = None
    try:
        import re, urllib.request
        html = urllib.request.urlopen(urllib.request.Request("https://www.boxtrades.com/", headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "ignore")
        ys = [float(x) for x in re.findall(r'"yield":([0-9.]+)', html)]; out["box_rate"] = ys[2] / 100; out["box_source"] = "boxtrades.com (3-month SPX box)"
    except Exception:
        try: ts, v = src.yahoo("^IRX", field="close"); out["box_rate"] = float(v[-1]) / 100 + 0.006; out["box_source"] = "3-month T-bill + 0.6 (boxtrades.com unavailable)"
        except Exception: out["box_rate"] = 0.047; out["box_source"] = "assumed 4.7%"
    return out

def plan(state, date, prices, cpi, deposit=0.0, bucket=None, market=None):
    """Everything to do today. Returns a dict of steps; pure (does not modify state). With a box loan (state["loan"]) the net
    value (funds - loan) drives the skim, guardrail and leverage; `market` = {spx, box_rate} (fetched live when needed)."""
    S = state["settings"]; B = state["baseline"]; d = dt.date.fromisoformat(date); notes = []; steps = []
    work = json.loads(json.dumps(state)); cbucket = state["cash_bucket"] if bucket is None else float(bucket)
    infl = cpi / B["start_cpi"]
    def apply_trades(trades):                                   # update a working copy so later steps see earlier trades
        for t, dollars in trades.items():
            h = work["holdings"].setdefault(t, {"shares": 0.0, "lots": []}); h["shares"] += dollars / prices[t]
    L = work.get("loan"); debt = 0.0
    if L: debt = L["balance"] * (1 + L["rate"]) ** (max(0, (d - dt.date.fromisoformat(L["last_accrual"])).days) / 365)
    # 1 deposit
    if deposit > 0:
        bp = buy_plan(work, prices, deposit); apply_trades(bp); B2 = B["start_value"] + deposit / infl
        steps.append(dict(step="DEPOSIT", why=f"${deposit:,.0f} of new money goes to the most underweight funds first; the baseline rises to ${B2:,.0f} (today's dollars at the start)",
                          trades=bp, baseline_new=B2)); start_value = B2
    else: start_value = B["start_value"]
    mult = state["guardrail_mult"]
    # 2 year-end (first run in a new calendar year)
    if d.year > state["last_year_end"]:
        V = value(work, prices); line = (1 + S["skim"]) * start_value * infl; skim = max(0.0, V - debt - line)
        sell = skim if not debt else skim * V / (V - debt)                 # with a loan: sell pro rata and pay the loan down by the same share
        sp = sell_plan(work, prices, sell) if skim > 0 else {}
        if sp: apply_trades({t: -x for t, x in sp.items()}); cbucket_after = cbucket + skim; paid_down = sell - skim; debt -= paid_down
        else: cbucket_after = cbucket; paid_down = 0.0
        real = (value(work, prices) - debt) / (start_value * infl)
        new_mult = S["cut_to"] if real < S["cut_below"] else (1.0 if real > S["restore_above"] else mult)
        steps.append(dict(step="YEAR-END", why=f"Skim line ${line:,.0f} (= {1+S['skim']:.2f} x baseline x inflation {infl:.3f}); {'net value' if L else 'account'} ${V - (debt + paid_down):,.0f} -> "
                          + (f"skim ${skim:,.0f} into the cash bucket" if skim > 0 else "nothing to skim") + (f" and pay the box loan down by ${paid_down:,.0f}" if paid_down > 0.5 else "")
                          + f". Real value {real*100:.0f}% of baseline -> guardrail {'CUT: base print x ' + format(new_mult, '.2f') if new_mult < 1 else 'normal (base print x 1.00)'}",
                          trades={t: -x for t, x in sp.items()}, skim=skim, bucket_after=cbucket_after, guardrail=new_mult, year=d.year, paid_down=paid_down))
        cbucket, mult = cbucket_after, new_mult
    # 3 monthly print (first run in a new month)
    ym = d.strftime("%Y-%m"); switched = False
    if ym > state["last_month_paid"]:
        ly, lm = map(int, state["last_month_paid"].split("-")); owed = min(3, (d.year - ly) * 12 + d.month - lm)   # missed months are paid too (max 3)
        base_amt = owed * S["base"] / 100 * start_value * infl / 12 * mult; draw = cbucket * (1 - (1 - 1 / S["bucket_months"]) ** owed)
        if owed > 1: notes.append(f"{owed} months were due (missed runs are caught up, up to 3 months)")
        sp = sell_plan(work, prices, base_amt); apply_trades({t: -x for t, x in sp.items()})
        steps.append(dict(step="MONTHLY PRINT", why=f"Base print {S['base']}% x baseline ${start_value:,.0f} x inflation {infl:.3f} / 12 x guardrail {mult:.2f}" + (f" x {owed} months" if owed > 1 else "") + f" = ${base_amt:,.0f}"
                          + f"; bonus from the cash bucket ({owed} x 1/{S['bucket_months']}) of ${cbucket:,.0f} = ${draw:,.0f}. SPEND THIS MONTH: ${base_amt + draw:,.0f}",
                          trades={t: -x for t, x in sp.items()}, base=base_amt, bucket_draw=draw, spend=base_amt + draw, month=ym))
        cbucket -= draw
        if L:                                                          # monthly loan checks (the simulator checks at month ends too)
            netv = value(work, prices) - debt; nr = netv / (start_value * infl); L["hwm_real"] = max(L.get("hwm_real", 1.0), nr)
            if L.get("dd", 0) > 0:
                if not L["dd_on"] and nr < (1 - L["dd"]) * L["hwm_real"]:
                    L["dd_on"] = True; switched = True; notes.append(f"Net value is {(1 - nr / L['hwm_real']) * 100:.0f}% below its high: the crash-buyer loan switches ON ({L['dd_to']}x)")
                elif L["dd_on"] and nr > (1 - L["dd"] / 2) * L["hwm_real"]:
                    L["dd_on"] = False; switched = True; notes.append(f"Net value is back within {L['dd'] * 50:.0f}% of its high: the crash-buyer loan switches OFF")
            if L.get("floor_usd") and not L["paused"] and debt > 0.5 and netv < L["floor_usd"]:
                sp2 = sell_plan(work, prices, debt); apply_trades({t: -x for t, x in sp2.items()}); paid = sum(sp2.values())
                steps.append(dict(step="PAY OFF THE LOAN", why=f"Net value ${netv:,.0f} is below the ${L['floor_usd']:,.0f} floor (portfolio-margin minimum): sell ${paid:,.0f} of funds and pay the box loan off. "
                                  f"Borrow again once net value is above ${L['resume_usd']:,.0f}", trades={t: -x for t, x in sp2.items()})); debt -= paid; L["paused"] = True
            elif L.get("paused") and netv > L.get("resume_usd", 0): L["paused"] = False; notes.append(f"Net value ${netv:,.0f} is above ${L['resume_usd']:,.0f}: the loan can be used again (at the next rebalance)")
    # 4/5 rebalancing checks
    w = weights(work, prices); T = {t: x / 100 for t, x in state["targets"].items()}
    valve = [t for t in T if w[t] >= S["valve"] * T[t]]; drift = max(abs(w[t] - T[t]) * 100 for t in T)
    days = (d - dt.date.fromisoformat(state["last_rebalance"])).days
    lt = 1.0; levdrift = False
    if L:
        V = value(work, prices); netv = V - debt; lt = 1.0 if L["paused"] else (L["dd_to"] if L["dd_on"] else L["lev"])
        levdrift = netv > 0 and abs(V / netv / lt - 1) > 0.15
    if valve or (drift > S["band"] and days >= S["min_days"]) or (L and ((levdrift and days >= S["min_days"]) or switched)):
        total = lt * (value(work, prices) - debt) if L else None
        rp = rebalance_plan(work, prices, total); apply_trades(rp)
        if L: debt += sum(rp.values())                                  # buying more than you sell is financed by the box loan (and vice versa)
        why = (f"SAFETY VALVE: {', '.join(valve)} reached {S['valve']:.0f}x target" if valve else f"Drift {drift:.1f} points > {S['band']:.0f} and {days} days since the last rebalance"
               if drift > S["band"] and days >= S["min_days"] else f"Loan target is now {lt:g}x net value" if switched else f"Leverage drifted more than 15% from {lt:g}x")
        steps.append(dict(step="REBALANCE", why=why + (f" -> funds back to target weights at {lt:g}x net value; box loan becomes ${max(0, debt):,.0f}" if L else " -> everything back to target weights"), trades=rp))
    else:
        notes.append(f"No rebalance: largest drift {drift:.1f} points (trigger {S['band']:.0f} after {S['min_days']} days; {days} days since last), no fund at {S['valve']:.0f}x target")
    # 6 the box spread itself: open / roll / close so it matches the loan
    if L:
        debt = max(0.0, debt); box = L.get("box"); market = market or live_market(); rate = market.get("box_rate") or L["rate"]
        due = box and (dt.date.fromisoformat(box["expiry"]) - d).days <= 7
        box_pv = box["face"] / (1 + box["rate"]) ** (max(0, (dt.date.fromisoformat(box["expiry"]) - d).days) / 365) if box else 0.0
        if debt < 250 and box:
            steps.append(dict(step="BOX LOAN", why=f"Close the box: buy it back for about ${box_pv:,.0f} (" + "; ".join(box["legs"]) + " - reverse each leg)", trades={}, box=None)); L["box"] = None
        elif debt >= 250 and (not box or due or abs(debt - box_pv) > max(500, 0.05 * debt)):
            if not market.get("spx"): notes.append("S&P 500 level unavailable: cannot size the box today")
            else:
                o = box_order(debt, d, market["spx"], rate); L["box"] = o; L["rate"] = rate
                steps.append(dict(step="BOX LOAN", why=(("Roll: close the current box (buy it back for about $" + format(box_pv, ",.0f") + "), then ") if box else "")
                                  + f"SELL a {o['width']}-point SPX box expiring {o['expiry']} ({o['days']} days) as ONE combo order at a limit near ${o['credit']:,.0f} credit "
                                  f"(about {rate*100:.2f}%/yr; {market.get('box_source', '')}). You owe ${o['face']:,.0f} at expiry. Legs: " + "; ".join(o["legs"]), trades={}, box=o))
    # watch levels for the rest of the month/year
    V = value(work, prices); line = (1 + S["skim"]) * start_value * infl; netv = V - debt
    watch = dict(account_value=V, real_value_pct=netv / (start_value * infl) * 100, skim_line=line, guardrail_line=S["cut_below"] * start_value * infl,
                 restore_line=S["restore_above"] * start_value * infl, bucket=cbucket,
                 valve_levels={t: f">= {S['valve']*T[t]*100:.0f}% (now {w2*100:.1f}%)" for t, w2 in weights(work, prices).items()})
    if L:
        watch.update(debt=debt, net_value=netv, leverage=V / netv if netv > 0 else None, margin_call_line=debt / 0.70 if debt > 0 else None,
                     floor_line=L.get("floor_usd"), resume_line=L.get("resume_usd"), loan_target=lt,
                     crash_line=(1 - L["dd"]) * L.get("hwm_real", 1.0) * start_value * infl if L.get("dd", 0) > 0 and not L["dd_on"] else None,
                     crash_off_line=(1 - L["dd"] / 2) * L.get("hwm_real", 1.0) * start_value * infl if L.get("dd", 0) > 0 and L["dd_on"] else None)
    return dict(date=date, prices=prices, cpi=cpi, steps=steps, notes=notes, watch=watch, work=work, start_value=start_value, bucket_after=cbucket, guardrail=mult,
                debt_after=debt, loan_after=L)

def tax_lots(state, t, dollars, price, date, profile):
    """Pick lots for selling `dollars` of t: long-term highest cost first, then short-term highest cost. Returns lot picks + gain/tax estimate."""
    need = dollars / price; lots = sorted(state["holdings"].get(t, {}).get("lots", []), key=lambda L: ((dt.date.fromisoformat(date) - dt.date.fromisoformat(L["date"])).days <= 365, -L["cost"]))
    picks, lt, st = [], 0.0, 0.0
    for L in lots:
        if need <= 1e-9: break
        q = min(L["shares"], need); g = q * (price - L["cost"]); long = (dt.date.fromisoformat(date) - dt.date.fromisoformat(L["date"])).days > 365
        picks.append(dict(lot_date=L["date"], cost=L["cost"], shares=q, gain=g, term="long" if long else "short")); need -= q
        lt += g if long else 0; st += 0 if long else g
    r = TAXP[profile]; coll = t in COLLECTIBLE
    tax = (max(lt, 0) * ((r["coll"] if coll else r["lt"]) + r["ca"]) + max(st, 0) * (r["ord"] + r["ca"]))
    return picks, lt, st, tax

def apply(state, p, date, profile):
    """Record the planned trades as executed: update shares and tax lots, bucket, guardrail, dates, log."""
    log = dict(date=date, steps=[]); gains = 0.0
    for s in p["steps"]:
        for t, dollars in s["trades"].items():
            px = p["prices"][t]; h = state["holdings"].setdefault(t, {"shares": 0.0, "lots": []})
            if dollars > 0: h["shares"] += dollars / px; h["lots"].append(dict(shares=dollars / px, cost=px, date=date))
            else:
                picks, lt, st, tax = tax_lots(state, t, -dollars, px, date, profile); gains += lt + st
                for pk in picks:
                    for L in h["lots"]:
                        if L["date"] == pk["lot_date"] and abs(L["cost"] - pk["cost"]) < 1e-9 and L["shares"] > 0:
                            take = min(L["shares"], pk["shares"]); L["shares"] -= take; pk["shares"] -= take
                h["lots"] = [L for L in h["lots"] if L["shares"] > 1e-9]; h["shares"] = max(0.0, h["shares"] + dollars / px)
        if s["step"] == "DEPOSIT": state["baseline"]["start_value"] = s["baseline_new"]
        if s["step"] == "YEAR-END": state["last_year_end"] = s["year"]; state["guardrail_mult"] = s["guardrail"]
        if s["step"] == "MONTHLY PRINT": state["last_month_paid"] = s["month"]; state.setdefault("paid", []).append(dict(month=s["month"], spend=s["spend"], base=s["base"], bucket=s["bucket_draw"]))
        if s["step"] == "REBALANCE": state["last_rebalance"] = date
        log["steps"].append(dict(step=s["step"], why=s["why"], trades={t: round(x, 2) for t, x in s["trades"].items()}))
    if p.get("loan_after") is not None:
        state["loan"] = json.loads(json.dumps(p["loan_after"])); state["loan"]["balance"] = p["debt_after"]; state["loan"]["last_accrual"] = date
    state["cash_bucket"] = p["bucket_after"]; state["realized_gains_by_year"] = state.get("realized_gains_by_year", {})
    y = date[:4]; state["realized_gains_by_year"][y] = state["realized_gains_by_year"].get(y, 0.0) + gains
    state.setdefault("log", []).append(log); return state

def init_state(printer, value, date, prices, cpi, tax="retiree, not working", market=None):
    """A new state file and the first-purchase plan. Loan printers buy lev x value of funds and borrow the rest with an SPX box;
    if the start is at least $130k the loan is paid off whenever net value falls below $115k (portfolio-margin minimum ~$100-110k)."""
    cfg = PRINTERS[printer]; lc = cfg.get("loan"); lev = lc["lev"] if lc else 1.0
    st = dict(printer=printer, targets=cfg["targets"], settings=cfg["settings"], baseline=dict(start_value=value, start_cpi=cpi, start_date=date),
              holdings={t: {"shares": 0.0, "lots": []} for t in cfg["targets"]}, cash_bucket=0.0, guardrail_mult=1.0, last_rebalance=date,
              last_month_paid=date[:7], last_year_end=int(date[:4]), tax=tax, log=[])
    bp = {t: value * lev * w / 100 for t, w in cfg["targets"].items()}
    steps = [dict(step="INITIAL PURCHASE", why=f"Invest ${value * lev:,.0f} at target weights" + (f" (${value:,.0f} of your money + ${value * (lev - 1):,.0f} borrowed with the box)" if lev > 1 else ""), trades=bp)]
    if lc:
        market = market or live_market(); rate = market.get("box_rate") or 0.047; debt = value * (lev - 1)
        st["loan"] = dict(lev=lev, dd=lc.get("dd", 0.0), dd_to=lc.get("dd_to", 1.0), spread=lc["spread"], rate=rate, balance=0.0, last_accrual=date, hwm_real=1.0,
                          dd_on=False, paused=False, floor_usd=115000.0 if value >= 130000 else None, resume_usd=130000.0 if value >= 130000 else None, box=None)
        if debt > 0 and market.get("spx"):
            o = box_order(debt, dt.date.fromisoformat(date), market["spx"], rate); st["loan"]["box"] = o
            steps.insert(0, dict(step="BOX LOAN", why=f"First, SELL a {o['width']}-point SPX box expiring {o['expiry']} ({o['days']} days) as ONE combo order at a limit near ${o['credit']:,.0f} credit "
                                 f"(about {rate*100:.2f}%/yr; {market.get('box_source', '')}). You owe ${o['face']:,.0f} at expiry. Legs: " + "; ".join(o["legs"]), trades={}, box=o))
    p = dict(date=date, prices=prices, steps=steps, bucket_after=0.0, debt_after=value * (lev - 1), loan_after=st.get("loan"), notes=[], watch={})
    return st, p

# ------------------------------------------------------------------ printing
def sheet(state, p, profile, whole_shares=False):
    out = [f"=== MONEY PRINTER ACTION SHEET — {state['printer']} — {p['date']} ===",
           f"Account ${p['watch']['account_value']:,.0f} after today's steps | real value {p['watch']['real_value_pct']:.0f}% of baseline | cash bucket ${p['bucket_after']:,.0f} | guardrail x{p['guardrail']:.2f}"]
    if not p["steps"]: out.append("\nNOTHING TO DO TODAY. (Next: monthly print on the 1st trading day of next month.)")
    for i, s in enumerate(p["steps"], 1):
        out.append(f"\n{i}. {s['step']}: {s['why']}")
        for t, dollars in sorted(s["trades"].items(), key=lambda kv: kv[1]):
            px = p["prices"][t]; sh = abs(dollars) / px
            if whole_shares: sh = math.ceil(sh) if dollars < 0 else math.floor(sh)
            line = f"     {'SELL' if dollars < 0 else 'BUY '} {t:5} {sh:10.3f} shares @ ${px:,.2f} = ${sh * px:,.0f}" + (f" (plan ${abs(dollars):,.0f}; extra stays as cash)" if whole_shares and abs(sh * px - abs(dollars)) > 0.5 else "")
            if dollars < 0 and state["holdings"].get(t, {}).get("lots"):
                picks, lt, st, tax = tax_lots(state, t, -dollars, px, p["date"], profile)
                lots_txt = ", ".join("{:.2f}sh from {} ({})".format(pk["shares"], pk["lot_date"], pk["term"]) for pk in picks)
                line += f"   lots: {lots_txt} | gain ${lt+st:,.0f} | est. tax ${tax:,.0f}"
                if t in COLLECTIBLE: line += " (collectible: taxed at ordinary rates)"
            if t in K1: line += " [K-1 fund]"
            out.append(line)
        if s["step"] == "MONTHLY PRINT": out.append(f"     -> move ${s['base']:,.0f} (sale proceeds) + ${s['bucket_draw']:,.0f} (from the cash bucket) = ${s['spend']:,.0f} to checking")
        if s["step"] == "YEAR-END" and s["skim"] > 0: out.append(f"     -> move the ${s['skim']:,.0f} of sale proceeds into the cash bucket (T-bills / high-yield savings)")
    w = p["watch"]
    if w.get("debt") is not None:
        out.append(f"\nBOX LOAN: owe ${w['debt']:,.0f} | net value ${w['net_value']:,.0f} | leverage {w['leverage'] or 0:.2f}x (target {w['loan_target']:g}x)"
                   + (f" | pay off if net value < ${w['floor_line']:,.0f}" if w.get("floor_line") else "") + (f" | margin call if funds < ${w['margin_call_line']:,.0f}" if w.get("margin_call_line") else "")
                   + (f" | crash-buyer loan turns ON if net value < ${w['crash_line']:,.0f}" if w.get("crash_line") else "") + (f" | turns OFF above ${w['crash_off_line']:,.0f}" if w.get("crash_off_line") else ""))
    out += ["\nWATCH LEVELS (for the rest of the period):",
            f"   skim line (checked in January): account above ${w['skim_line']:,.0f}",
            f"   guardrail (checked in January): below ${w['guardrail_line']:,.0f} -> base print x {state['settings']['cut_to']:.2f}; back to normal above ${w['restore_line']:,.0f}",
            f"   safety valve (check any time; rebalance at once if any fund reaches {state['settings']['valve']:g}x its target): " + " | ".join(f"{t} {lv}" for t, lv in w["valve_levels"].items())]
    out += [f"   note: {n}" for n in p["notes"]]
    y = p["date"][:4]; g = state.get("realized_gains_by_year", {}).get(y, 0.0)
    out.append(f"\nTAXES: realized gains recorded so far in {y} (before today): ${g:,.0f}. Keep total taxable income under the 0% long-term-gains bracket if possible (2026 joint: $98,900; single from 2027: $49,450).")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["init", "run", "status", "sync"]); ap.add_argument("--state", required=True)
    ap.add_argument("--shares", help='actual holdings from the broker, e.g. "DBMF=471.389,VBR=63"')
    ap.add_argument("--printer", default="MP-2"); ap.add_argument("--value", type=float); ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--deposit", type=float, default=0.0); ap.add_argument("--bucket", type=float); ap.add_argument("--cpi", type=float); ap.add_argument("--prices", help="JSON {ticker: price} instead of live prices")
    ap.add_argument("--tax", default="retiree, not working", choices=list(TAXP)); ap.add_argument("--whole-shares", action="store_true"); ap.add_argument("--commit", action="store_true")
    ap.add_argument("--spread", action="store_true", help="sell from every overweight fund in proportion (simulator style)")
    a = ap.parse_args(); global SPREAD; SPREAD = a.spread
    if a.cmd == "init":
        if os.path.exists(a.state): sys.exit(f"{a.state} exists; refusing to overwrite")
        cfg = PRINTERS[a.printer]; prices = json.loads(a.prices) if a.prices else live_prices(cfg["targets"]); cpi = a.cpi or live_cpi()
        st, p = init_state(a.printer, a.value, a.date, prices, cpi, a.tax)
        print(f"=== INITIAL PURCHASE — {a.printer} — {a.date} ===")
        for s_ in p["steps"]:
            if s_["step"] == "BOX LOAN": print("   " + s_["why"])
        for t, x in p["steps"][-1]["trades"].items(): print(f"   BUY {t:5} {x / prices[t]:10.3f} shares @ ${prices[t]:,.2f} = ${x:,.0f}" + (" [K-1 fund]" if t in K1 else ""))
        print("First monthly print: next month's 1st trading day. Keep 12 months of expenses in high-yield savings outside the printer.")
        if a.commit: st = apply(st, p, a.date, a.tax); json.dump(st, open(a.state, "w"), indent=1); print(f"saved {a.state}")
        return
    st = json.load(open(a.state)); prices = json.loads(a.prices) if a.prices else live_prices(st["targets"]); cpi = a.cpi or live_cpi()
    if a.cmd == "sync":                                             # record the broker's actual shares (whole-share brokers, partial fills)
        for kv in (a.shares or "").split(","):
            if not kv.strip(): continue
            t, q = kv.split("="); t = t.strip().upper(); q = float(q); h = st["holdings"].setdefault(t, {"shares": 0.0, "lots": []}); diff = q - h["shares"]
            if diff > 1e-9: h["lots"].append(dict(shares=diff, cost=prices[t], date=a.date))
            elif diff < -1e-9: tax_sold, need = 0, -diff; h["lots"].sort(key=lambda L: -L["cost"])
            if diff < -1e-9:
                for L in h["lots"]:
                    take = min(L["shares"], need); L["shares"] -= take; need -= take
                h["lots"] = [L for L in h["lots"] if L["shares"] > 1e-9]
            print(f"  {t}: {h['shares']:.3f} -> {q:.3f} shares"); h["shares"] = q
        if a.bucket is not None: st["cash_bucket"] = a.bucket; print(f"  cash bucket set to ${a.bucket:,.2f}")
        json.dump(st, open(a.state, "w"), indent=1); print(f"synced {a.state}"); return
    p = plan(st, a.date, prices, cpi, deposit=a.deposit, bucket=a.bucket)
    if a.cmd == "status": p["steps"] = []
    print(sheet(st, p, st.get("tax", a.tax), a.whole_shares))
    if a.commit and a.cmd == "run": st = apply(st, p, a.date, st.get("tax", a.tax)); json.dump(st, open(a.state, "w"), indent=1); print(f"\nrecorded in {a.state}")

if __name__ == "__main__": main()
