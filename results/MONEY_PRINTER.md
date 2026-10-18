# The Money Printer (2026-10-18)

> **Update:** the printer search (`results/PRINTER_SEARCH.md`) found **MP-2** — DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · GLD 8 ·
> TQQQ 2, base 5.75%, skim > 140%, 48-month bucket, guardrail 70% → 65% — which beats the CH-12 Printer below in every
> validation and stress case (robust CE $518 vs $442 per $100k/month). The CH-12 Printer remains the calmer option.

A **money printer** is one fully coordinated plan for living off an account. Scoring and simulation:
`printer/money_printer.py` (GPU: 2,000 reshuffled 40-year market histories from 1972–2026 data, every fund, inflation
and T-bills moving together). It is rated on three things only:

| Quality | Question | Measured as |
|---|---|---|
| **PRINT** | How much can the retiree spend each month, after all taxes? | Spendable $/month (today's dollars): typical history, bad history (1 in 10), lean month, and by decade of life |
| **RELIABILITY** | Does it print what we expect? | Chance the base print never has to be cut; share of years within ±25% of the year before; worst year |
| **BREAK RISK** | How likely is it to lose value or stop working? | Chance it ends below its starting real value, dips below 70% of it, or runs dry, plus how much less it prints if the future is worse (stress tests) |

## The five parts of the printer
1. **Engine: the portfolio.** Crisis-Hedged 12 for a taxable account: **DBMF 25 · KMLM 16 · GLD 15 · VBR 15 · XLV 13 ·
   TYD 11 · TQQQ 5** (no UUP, to avoid its K-1 and yearly tax). In an IRA the version with UUP 3% works equally well.
   GLDM or IAUM can replace GLD: same gold and tax, a quarter of the fee.
2. **Maintenance: rebalancing.**
   - Rebalance everything back to target when any fund is more than 6 points off target, but never sooner than 1 year
     after the last rebalance. That's about 0.4 times a year, and nearly every sale is a long-term gain.
   - **Safety valve:** rebalance at any time if a fund reaches 2× its target. In practice that means TQQQ above 10%.
3. **Output: the print.**
   - **Base print:** 4% of the starting value per year, raised with inflation every year, paid monthly. It is sold
     from the most overweight funds first, so the withdrawals also do much of the rebalancing.
   - **Bonus print:** at each year-end, anything above 125% of the inflation-adjusted starting value is skimmed into
     a cash bucket (T-bills/high-yield savings). The bucket pays out 1/36 of its balance each month.
4. **Guardrail.** If the account is below 70% of its inflation-adjusted start at a year-end, the base print drops to
   80% of normal. It goes back to normal once the account is back above 90%.
5. **Taxes.** The per-fund tax model, sales from the most overweight funds and highest-cost lots first, 2026 joint
   filing, and any IRA money holding the tax-heavy funds (DBMF, KMLM, TYD, TQQQ, GLD).

## Spec sheet: CH-12 Printer, the retiree's taxes (not working)
| Per month, after tax, today's $ | per $100k |
|---|---|
| Base print (the floor) | $333 |
| Ages 60–70, typical history | $458 |
| Ages 60–70, bad history | $333 |
| 40-year average, typical | $712 |
| 40-year average, bad history | $488 |

- **Reliability:**
  - The base print never has to be cut in 94% of histories.
  - 86% of years are within ±25% of the year before.
  - In a bad history the worst year still pays the full base (4%).
  - Bonuses come in lumps, which is why the bucket spreads them out. In 21% of histories there is no bonus at all in
    the first 10 years.
- **Break risk:**
  - Ends below its starting real value: 10%.
  - Dips below 70% of the start at some point: 9%.
  - Runs dry: 0.0%.
  - Typical amount left at 100: 137% of the start, in today's dollars.

## Why these settings
- **Engine, compared with the same output, guardrail and taxes:**
  | Printer | Typical $/mo per $100k | Bad history | Base never cut | Loses value |
  |---|---|---|---|---|
  | **CH-12 (no UUP)** | **$712** | **$488** | 94% | 10% |
  | CH-12 with UUP | $689 | $468 | 94% | 10% |
  | CH-11.5 | $657 | $450 | 94% | 10% |
  | S12+ split | $686 | $451 | 91% | 12% |
  | Gold-Stack 12 | $828 | $558 | 88% | 14% |
  | 60/40 | $457 | $281 | 40% | 57% |
  | 100% VTI | $620 | $281 | 23% | 60% |

  Gold-Stack prints more but breaks more often: a deep dip in 17% of histories versus 9%, and about a third of its
  money is in gold. A fixed 5% with no bonus pays a steady $416 but runs dry in 3.5% of histories.
- **Skim threshold.** A higher threshold looks better on 40-year averages because it delays the bonuses. Above 150%,
  for example, gives $780 typical with only a 2% chance of losing value, but just $342/month in the retiree's 60s versus $458 at
  the 125% threshold. The retiree needs money early, so the threshold stays at 125%. Above 135% is the middle ground: $408
  in the retiree's 60s and a 5% chance of losing value.
- **Bucket length.** A 12-month bucket gives bigger but bumpier bonuses (only about 55% of years within ±25%). The
  36-month bucket gives about 86%.
- **Rebalancing rule.** Once the retiree is withdrawing, every reasonable rule sustains about the same amount (5.14–5.27%
  with 90% of histories keeping their real value). This one was chosen for the fewest taxable trades.

## Stress tests: how the printer behaves if the future is worse (per $100k)
| Scenario | Typical $/mo | Bad history | Ages 60–70 typical | Base never cut | Loses value | Runs dry |
|---|---|---|---|---|---|---|
| Base case | $712 | $488 | $458 | 94% | 10% | 0.0% |
| Harsher reshuffle (3-month blocks) | $710 | $483 | $475 | 91% | 14% | 0.1% |
| Trend funds earn 2%/yr less | $624 | $392 | $408 | 86% | 20% | 0.1% |
| Trend funds earn 4%/yr less | $539 | $319 | $367 | 74% | 33% | 1.1% |
| Middle tax bracket instead of hers | $543 | $353 | $408 | 78% | 34% | 0.2% |
| Actual 40-year windows (1972–86 starts) | $906 | $805 | $658 | 100% | 0% | 0% |

The printer degrades gradually rather than breaking. Even if trend-following earns 4% a year less than its history,
it almost never runs dry (1.1%); it just prints less and needs the guardrail more often. The base print is the number
to budget on, and the bonus is extra.

## Operating manual
- **Monthly:**
  - Sell the base print from the most overweight funds and spend it, together with 1/36 of the cash bucket.
  - Check the safety valve: is any fund at 2× its target (TQQQ above 10%)? If so, rebalance everything that day.
- **Each year-end (early January for taxes):**
  1. If the account is above 125% of its inflation-adjusted starting value, move the excess to the cash bucket.
  2. Check the guardrail: below 70% means cut the base to 80%; back above 90% means restore it.
  3. Rebalance if any fund is more than 6 points off target and the last rebalance was over a year ago.
  4. Raise the base print by last year's inflation.
- **Taxes:** sell the highest-cost lots first and keep taxable income in the 0% long-term bracket where possible.
  Have a tax preparer confirm the brackets each year.
- **Re-score anytime:** `python3 printer/money_printer.py compare | grid | decades | stress`.
  Change `Printer(...)` settings or the portfolio in `printer/money_printer.py` to rate a new printer.

*Research model on historical and simulated data (pre-inception fund histories are reconstructed). Not a guarantee and
not financial, tax or legal advice.*
