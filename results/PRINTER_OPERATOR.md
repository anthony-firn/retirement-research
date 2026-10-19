# Running the Money Printer: the operator (2026-10-18)

`printer/operate.py` turns the printer into a checklist. Give it the state file. It looks up today's prices (Yahoo) and
inflation (CPI-U via testfol.io), or takes them on the command line, and prints exactly what to do: how much to spend,
which funds to sell or buy and how many shares, which tax lots, and why. **It uses the same rules that were tested.**
`printer/replay.py` runs it day by day through 1972–2026 and 2000–2026 and reproduces the simulator within 3.5–5.4%;
the gap is calendar months versus 21-trading-day months. Its default one-fund-at-a-time selling gives the same results
as the simulator's spread selling over 2,000 histories (`results/sell_mode_check.log`).

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
