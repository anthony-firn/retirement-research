# Running the Money Printer: the operator (2026-10-18)

`printer/operate.py` turns the printer into a checklist. Give it the state file. It looks up today's prices (Yahoo) and
inflation (CPI-U via testfol.io), or takes them on the command line, and prints exactly what to do: how much to spend,
which funds to sell or buy and how many shares, which tax lots, and why. **It uses the same rules that were tested.**
`printer/replay.py` runs it day by day through 1972–2026 and 2000–2026 and reproduces the simulator within 3.5–5.4%;
the gap is calendar months versus 21-trading-day months. Its default one-fund-at-a-time selling gives the same results
as the simulator's spread selling over 2,000 histories (`results/sell_mode_check.log`).

**MP-2.1 (2026-10-21, `results/IMPROVE.md`):**
- **What:** MP-2 with IAUM instead of GLD, the guardrail cutting the base to 60%, and the safety valve at 4×. Use
  `--printer MP-2.1`.
- **Cash bucket:** keep it in **BOXX**, a box-spread ETF whose growth is taxed as long-term gains (0% federal for the retiree).
  A Treasury fund such as SGOV is the fallback if BOXX's tax treatment is ever challenged.
- **Tested:** on fresh histories, +1.7% robust CE with break risk no worse in any stress case.

## Commands
```
python3 printer/operate.py init   --state printer/ex_state.json --printer MP-2 --value 90000 --commit   # buy at target weights
python3 printer/operate.py run    --state printer/ex_state.json                                       # what to do today (no changes)
python3 printer/operate.py run    --state printer/ex_state.json --commit                              # ...after doing it: record it
python3 printer/operate.py run    --state printer/ex_state.json --deposit 100000 --commit             # new money (insurance, workers' comp)
python3 printer/operate.py run    --state printer/ex_state.json --bucket 5321.77                      # tell it the real cash-bucket balance
python3 printer/operate.py status --state printer/ex_state.json                                       # dashboard + watch levels only
```
Options:
- `--printer`: MP-2 (default), CH-12, or MP-Fortress.
- `--tax`: retiree, not working / retiree, working $40k / middle bracket / IRA.
- `--whole-shares`: for brokers without fractional shares.
- `--spread`: use the simulator's exact selling rule.
- `--prices '{"VBR": 236.5, ...}'` and `--cpi`: supply prices and inflation manually.

## The rules it applies, in order (MP-2 numbers)
1. **New money.** Buy the most underweight funds first, then at target weights. The baseline rises by the deposit, in
   inflation-adjusted dollars.
2. **January (first run of a new year).**
   - **Skim:** if the account is above **1.40 × baseline × inflation since the start**, sell the excess (most
     overweight funds first) into the **cash bucket** (T-bills or high-yield savings).
   - **Guardrail:** if the account is below **0.70 × baseline × inflation**, the base print becomes **65%** of normal.
     It returns to normal once the account is above **0.90 × baseline × inflation**.
3. **Each month (first run of a new month).**
   - **Base print:** 5.75% × baseline × inflation ÷ 12 × guardrail, sold from the most overweight fund (a second fund
     only if needed).
   - **Bonus:** 1/48 of the cash bucket.
   - **Spend:** the base print plus the bonus. Missed months are caught up (up to 3).
4. **Safety valve, any day:** if any fund reaches **2× its target** (TQQQ ≥ 4%, GLD ≥ 16%, KMLM ≥ 30%, …), rebalance
   everything back to target now.
5. **Drift:** if any fund is **more than 6 points off target** and the last rebalance was **at least 365 days ago**,
   rebalance everything.
6. **Taxes.** Sales use **long-term lots with the highest cost first**, then short-term lots with the highest cost.
   Each sale shows its gain and estimated tax. GLD gains are collectibles (ordinary rates), and K-1 funds are flagged.
   It also tracks the realized gains for the year, so the retiree can stay in the 0% long-term bracket (2026 joint filing up to
   $98,900; single from 2027 up to $49,450).

Every action sheet ends with **watch levels** in dollars: the skim line, the guardrail line, the restore line, and each
fund's safety-valve trigger. That way the retiree always knows what would change the plan.

## The retiree's routine
- **1st trading day of each month:**
  1. `run`.
  2. Place the 1–2 sells it lists.
  3. Move the stated amount to checking.
  4. `run --commit`.
- **Early January:** the same. That run also does the skim and the guardrail check. Give it the real bucket balance
  with `--bucket`.
- **When money arrives:** `run --deposit <amount> --commit` and place the buys.
- **Any big market day:** `status`. If a fund is at its safety-valve level, `run` will say to rebalance.
- **Outside the printer:** keep 12 months of expenses in high-yield savings. That cash is separate from the bonus bucket.

What it does not do:
- **It doesn't place trades or talk to the broker.** That's deliberate.
- **It doesn't do the retiree's tax return.** Its estimates use flat marginal rates.
- **It doesn't predict markets.** Like the tested printer, it only reacts to prices and inflation.

*Research tool; have a tax preparer and fee-only fiduciary review before relying on it.*

## Running it at M1 Finance (checked 2026-10-18)
- **Every fund has an M1 security page with "Invest in … on M1":** all six MP-2 funds (DBMF, VBR, GDE, KMLM, GLD, TQQQ),
  plus GLDM/IAUM (cheaper gold) and the other printers' funds (XLV, TYD, UUP, UGL, SPMO, TLT). Mutual funds and fake
  tickers return 404 on the same URL pattern. M1 also shows a page for an over-the-counter ADR (NSRGY), so a page isn't
  absolute proof: **build the pie in the app before funding it** (adding slices needs no money).
- **Fractional shares:** every pie is fractional, so weights are exact.
- **How M1 maps to the rules:**
  - **Monthly print = "withdraw $X".** M1 sells overweight slices first, the same idea as the operator's rule. Then run
    `operate.py sync` with M1's holdings.
  - **Deposits:** new money goes to underweight slices first, which matches the deposit rule.
  - **Rebalance (drift or safety valve) = M1's Rebalance button.** It executes in the next trade window.
  - **The valve and drift checks are not automatic at M1.** The operator tells the retiree when to press the button.
- **Trade windows:** 9:30 ET and 3:00 PM ET. With under $25k, M1 allows one window a day. Trades are not instant, which
  is fine for monthly rules.
- **Tax lots:** M1 always uses its own tax-minimizing lot order (no FIFO/LIFO choice), which is close to the operator's
  highest-cost-long-term-first estimate. For the tax return, use M1's 1099.
- **Cash bucket:** keep it outside the pie (M1 cash account or high-yield savings) and give its balance with `--bucket`.
- **Cost:** $0 above $10k (a $3/month fee below $10k).
