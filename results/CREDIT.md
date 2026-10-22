# Credit for the Money Printer (2026-10-20)

**Question:** what is the easiest, cheapest credit to help the printer **run** (pay the paycheck in a down market
without selling) and **boost** it (hold more than the account is worth), after taxes?

Code: `printer/credit.py`, which uses the new credit options in `printer/money_printer.py` (`lev`, `lev_daily`,
`credit`, `rate_spread`, `interest_tax`). Results: `results/printer_credit.log` and `.json`. Every case uses the MP-2
printer: DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · GLD 8 · TQQQ 2, base 5.75%, skim above 140%, 48-month bucket,
guardrail 70% → 65%.

## Answer in one table
Per $100k, $/month after tax, today's dollars; the retiree's taxes (not working) unless noted; 2,000 fresh 40-year histories.
**Robust CE** is the certainty-equivalent paycheck (risk aversion 3) averaged over the base case and four stress cases:
trend funds −2%/yr, the 2000–2026 era only, 3-month blocks, and middle-bracket taxes.
| MP-2 with… | Robust CE | Typical | Bad history | First 10 yrs | Base never cut | Ends below start | Dips < 70% | Runs dry | Margin call | Middle-bracket CE | Trend −4%/yr CE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **no credit** | $529 | $826 | $536 | $494 | 85% | 9% | 20% | 0.3% | — | $478 | $442 |
| **Boost 1.2× with a box-spread loan** | **$586 (+11%)** | $997 | $665 | $582 | 87% | 7% | 20% | 0.1% | 0% | **$545** | $476 (1.2% margin calls) |
| Boost 1.33× box spread | $615 (+16%) | $1,100 | $742 | $645 | 86% | 7% | 23% | 0.1% | 0% | $580 | $486 (1.8%) |
| Boost 1.2× leverage inside funds | $578 (+9%) | $992 | $657 | $575 | 86% | 8% | 21% | 0.1% | — | $523 | $467 |
| Boost 1.2× IBKR margin | $569 (+8%) | $972 | $640 | $570 | 85% | 9% | 23% | 0.1% | 0% | $533 | — |
| Boost 1.2× M1 margin | $561 (+6%) | $961 | $627 | $565 | 84% | 9% | 24% | 0.2% | 0% | $524 | $442 (2.1%) |
| Boost 1.2× HELOC | $538 (+2%) | $929 | $588 | $550 | 81% | 12% | 27% | 0.5% | 0% | $500 | — |
| **Run: 25% box-spread line** | **$568 (+7%)** | $846 | $597 | $504 | **88%** | **5%** | 19% | 0.1% | 0% | $536 | **$480** (1.6%) |
| Run: 25% M1 margin line | $549 (+4%) | $843 | $590 | $503 | 87% | 6% | 20% | 0.1% | 0% | $499 | $437 (3.4%) |
| Run: 25% HELOC / HECM line | $528 (0%) | $843 | $582 | $503 | 86% | 6% | 21% | 0.3% | 0% | $479 | — |
| Run: 25% Schwab PAL | $496 (−6%) | $839 | $570 | $502 | 85% | 7% | 22% | 0.5% | 1% | $427 | — |
| **Run: 25% box line, base raised to 6.25%** | $578 (+9%) | $841 | $593 | **$530** | 84% | 8% | 23% | 0.1% | 0% | $541 | $457 (2.6%) |
| Boost 1.2× box spread, base 6.25% | $573 (+8%) | $987 | $651 | $597 | 82% | 10% | 25% | 0.4% | 0% | $517 | — |

- **Boost:** hold *lev* × the account's net worth. The loan is re-levered at each printer rebalance (or when leverage
  drifts more than 15%). A margin call (equity below 30%) sells down to a 50% loan.
- **Run:** while the account is below its inflation-adjusted start, the monthly base print is borrowed instead of
  sold, up to the line (25% of the start). The whole loan is repaid at the first year-end back above the start.
- **Leverage inside funds** resets daily, like GDE or a return-stacked ETF, so there is no loan and no margin call.
- **Roth** (no tax at all; only leverage inside funds is allowed): CE $600 with no credit, $659 at 1.2× (+10%),
  $693 at 1.33× (+16%).
- Every option was also run on the actual 40-year windows (1972–86 starts). The base was never cut in any of them.
  Typical print: $913 plain, $1,074 with a 1.2× box boost, $933 with the 25% box line.

## What it means
1. **The rate decides everything.** Borrowing pays only below about T-bill + 2%:
   - Box spreads (+11% at 1.2×), leverage inside funds (+9%), IBKR (+8%) and M1 (+6%) help.
   - A HELOC barely helps (+2%) and raises break risk: it ends below its start in 12% of histories instead of 9%.
   - The 8% Schwab line loses money.
   - This matches the earlier `results/heloc_test.log`: a HELOC at 8% invested at 60 lowered the retiree's plan odds.
2. **At box-spread rates, modest leverage improves all three printer qualities.** MP-2 earns well above T-bills with
   low swings, so 1.2× adds **+$171/month typical, +$129 in a bad history and +$88 in the first decade per $100k**.
   - Paycheck cuts and loss of real value both get slightly *less* likely.
   - There were no margin calls in 2,000 histories.
   - At 1.33× the chance of a deep dip starts to rise (23%), and under the harsh stress margin calls appear.
3. **The run line is the safest use of credit.**
   - Borrowing the paycheck instead of selling in a down market cuts the chance of ending below the start from 9% to
     5%, and raises the base never being cut from 85% to 88%.
   - It costs nothing until it is used.
   - Or spend that safety: it lets the base print rise from 5.75% to 6.25% (**+$42/month of guaranteed floor per
     $100k**, first decade $494 → $530) at about plain MP-2's break risk.
4. **Taxes favour the box spread.**
   - For the retiree's the capital-loss treatment is worth little (0% federal gains bracket, ~2% California).
   - In the middle bracket it is worth more: 1.2× box CE $545 versus $478 plain (+14%). M1 margin with the interest
     deducted (itemizing) reaches $524.
   - In a 400-history check, losing the itemized deduction cost the middle-bracket 1.2× margin printer about half a
     point of print a year (typical 9.19% → 8.70% of the start).
5. **Worse futures cut the benefit, and the cost of credit matters even more.** If trend funds earn 4%/yr less:
   - Box-rate boost and run still beat plain ($476–486 vs $442).
   - Margin calls appear in 1–3% of histories.
   - Credit at M1's 5.9% no longer helps at all.
   - So: box or IBKR rates only, leverage ≤ 1.2× for the retiree, and a capped line. A 15% line gives ~85% of the 25% line's
     benefit (CE +6.2% vs +7.4%) with a smaller loan (worst 1 in 10: 17% of the start vs 27%).
6. **Leverage inside funds is the only option in IRAs/Roths, and the simplest anywhere** (no loan, no margin call, no
   rolling). Scaling MP-2 by 1.2× is an idealisation. Real versions are GDE (already 21% of MP-2) and return-stacked
   ETFs (RSSB stocks + Treasuries, RSST stocks + trend, RSBT bonds + trend). **Next step:** add those funds to the
   Atlas universe and let the search build the engine with them.

## Retiree case: $50k in a taxable account, as much credit as makes sense
`MODE=sweep SIZE=50000 python3 printer/credit.py`, logged in `results/printer_credit_sweep.log`.
- **Search:** 62 designs, all on the retiree's taxes:
  - boost at 1.2×, 1.33×, 1.5×, 1.75× and 2× (2× is the Reg T limit; portfolio margin needs $110k+), each at
    today's box-spread rate (T-bill + 0.6) and at M1 margin (5.90%);
  - run lines of 15%, 25% and 35%;
  - each crossed with base prints from 5.25% to 6.75%;
  - five cases each: base, trend −2%/yr, trend −4%/yr, 2000–2026 era only, 3-month blocks.
- **Makes sense** means break risk no worse than plain MP-2 in every case (ends below start, dips below 70%, runs
  dry, base never cut), and margin calls ≤ 1% in the worst case.
- **Validation:** the finalists were re-run on 2,000 fresh histories. **One design passes:** a $10k box-spread loan
  (1.2×) with the base print at 5.25%.

| $/month after tax, today's $ | No credit (MP-2) | **+ $10k box-spread loan, base 5.25%** | + $37.5k loan (1.75×) | + $50k loan (2×, the limit) |
|---|---|---|---|---|
| Base paycheck (the floor) | $240 | **$219** | $219 | $219 |
| First 10 years, typical / bad history | $251 / $240 | **$286 / $219** | $429 / $219 | $497 / $220 |
| 40-year average, typical | $420 | **$505** | $713 | $808 |
| 40-year average, bad history (1 in 10) | $269 | **$350** | $494 | $551 |
| Base never cut | 86% | **90%** | 83% | 75% |
| Ends below its starting real value | 10% | **6%** | 9% | 10% |
| Dips below 70% of start | 20% | **16%** | 34% | 46% |
| Runs dry | 0.4% | **0.1%** | 0.2% | 0.2% |
| Margin call (worst case) | — | **0.5%** | 1.4% | 5.1% |
| Trend funds −4%/yr: typical / runs dry / ends below start | $310 / 2.9% / 34% | **$383 / 0.9% / 20%** | $543 / 1.4% / 21% | $609 / 1.9% / 24% |
| Passes | yes | **yes** | no: deep dips, margin calls | no |

- **The loan pays for itself.** About $40/month of interest at 4.69% buys roughly +$35/month in the first decade
  and +$85/month on the 40-year average, with less break risk on every measure.
- **The floor is $21/month lower.** That is the price: the extra return arrives as bonus prints rather than as a
  higher base. Keeping the 5.75% base with the same loan gives the same averages, but margin calls rise to 1.7% in
  the worst case (search run), so it just misses.
- **More credit raises the average print a lot but fails the retiree's test.** At 1.75× the chance of a deep dip goes from
  20% to 34%, the base is cut in 17% of histories, and margin calls appear.
- **At M1's 5.90% no amount of credit passes,** for boost or run. The cost eats the benefit, and in bad histories the
  run line's loan grows into margin calls. So the credit that makes sense for the retiree needs **IBKR or Schwab** (M1 has no
  options).
- **Mechanics:**
  - One 100-point SPX box is exactly a $10k loan: about $9,885 in now, $10,000 due in 3 months at 4.69%. Roll it
    each quarter.
  - No monthly payment: the interest is built into the roll.
  - The interest is a 60/40 capital loss, worth little to the retiree (0% federal gains bracket, ~2% California).
  - Rebalance the loan back to 1.2× at the printer's rebalances.

**Improved overnight (`results/IMPROVE.md`):**
- **Changes:**
  - IAUM for GLD, the bucket in BOXX;
  - a **$12.5k loan (1.25×)** with a 10-point rebalance band;
  - safety valve 3×, base restored above 80%;
  - the cash bucket paying the loan down.
- **Result on 4,000 fresh histories:** robust CE $287 → $297 at $50k (+3.6%), first decade $285 → $300, 40-year
  typical $499 → $523. Break risk no worse in every case; margin calls ≤ 0.4%.
- **Mechanics:** the loan is one 125-point SPX box.

## Retiree case at $150k: when the box loan makes sense (`results/improve/at150k.log`)
- **The edge is the same at any size, in percentage terms:** +11% robust CE over MP-2.1.
- **What changes with size is practical.** IBKR treats a short box as nearly riskless only under **portfolio margin**:
  $110k to open, about $100k to keep.
  - Under Reg T the box ties up margin about equal to its width.
  - So add a rule: **pay the box off if the account falls below ~$115k; re-borrow above ~$130k** (`lev_floor` /
    `lev_resume`).

$/month after tax, today's $, 2,000 new histories per case:

| At $150k | MP-2.1 (M1, no credit) | Box loan 1.25× | **Box loan 1.25× + pay off below $115k** |
|---|---|---|---|
| Robust CE | $795 | $881 | **$864** |
| Base paycheck | $719 | $656 | $656 (or $688 for 15 years with the front-load dial) |
| First 10 years, typical | $758 | $898 | **$897** |
| 40-year average, typical / bad history | $1,277 / $809 | $1,582 / $1,099 | **$1,581 / $1,088** |
| Base never cut · ends below start · dips < 70% · runs dry | 86% · 8% · 19% · 0.2% | 92% · 4% · 14% · 0.1% | 91% · 4% · 15% · 0.1% |
| Margin calls (worst case) | — | 0.4% | **0%** |
| Trend funds −4%/yr: 40-year typical, runs dry | $972, 1.8% | $1,253, 0.5% | $1,252, 1.3% |
| Actual 40-year windows, 40-year typical | $1,448 | $1,778 | $1,778 |

- With the pay-off rule, break risk is no worse than MP-2.1 in all 5 cases.
- The rule costs ~$17/month of robust CE. It removes margin calls, but deleverages at lows, so running dry with trend
  −4%/yr goes 0.5% → 1.3%; that is still under MP-2.1's 1.8%.
- **Rule of thumb:**
  - Under ~$50k: not worth the setup.
  - **From ~$110k (portfolio margin):** worth it if someone runs it.
  - The bigger the account above $115k, the less often the pay-off rule bites.

## What credit costs today (2026-10-20)
Benchmarks: SOFR 3.87%, fed funds 3.88% (target 3.75–4.00%, raised in September), 3-month T-bill 4.09%, 1-year
Treasury 4.50%, prime 7.00%.
| Credit | Rate now | Spread over the T-bill (used in the model) | Where it works | Needs |
|---|---|---|---|---|
| **An existing low fixed-rate mortgage** (e.g. 3–4% from before 2022) | 3–4% | −1 to 0 | — | already have it |
| **0% intro APR card** (Wells Fargo Reflect, U.S. Bank Visa Platinum) | 0% for 21 months, then ~18–29% | — | living costs only | credit approval, small limits, 5% fee on balance transfers |
| **Leverage inside funds** (GDE 90/90, return-stacked ETFs, TQQQ) | futures/swap financing ≈ SOFR + a little | +0.5 | **any account, including IRA/Roth** | nothing: it's just a fund |
| **SPX box-spread loan** (IBKR, Schwab; or SyntheticFi, $10k min) | 1 month 4.36%, 3 months 4.69%, 1 year 5.12%, 5 years 6.24% | +0.4 (today +0.6) | taxable margin account | options approval for spreads; IBKR portfolio margin from $110k |
| **IBKR Pro margin** | 5.38% first $100k, 4.88% $100k–$1M (Lite 6.38%) | +1.5 | taxable margin account | nothing |
| **M1 margin** | 5.90% | +2.0 | taxable M1 account ≥ $2k, up to 50% of value | nothing: one tap in the app the retiree already uses |
| **HELOC** | ~7.3% average (5.95%–10.9%) | +3.4 | needs home equity | **income and credit approval**; banks can freeze lines in a crisis (2008) |
| **HECM reverse-mortgage line** (age 62+) | ~5.5–6% + 0.5% yearly insurance | ≈ +2 to +3.4 | needs home equity | 2% upfront insurance on the home value (≈ $20k on $1M), origination up to $6k, closing costs; **must pay off any existing mortgage first**; HUD counselling |
| **Schwab Pledged Asset Line** | SOFR + 4.40% at a $100k line ≈ 8.3% (less with more assets) | +4.4 | taxable; can't buy securities with it | $100k+ line, $70k first draw |
| 401(k) loan | prime + 1% ≈ 8%, paid to yourself | — | a current employer plan | due in full if you leave the job, otherwise taxed + 10% penalty |

The box-spread premium over Treasuries is wider than usual right now: Cboe's average is ~0.3 points; today it is
0.4–0.6, and 1.3 points at 5 years. Fixed long-dated boxes are expensive. The short 1–3 month roll is the cheap part.

## The tax side of each
| Credit | How the interest is taxed | Other tax effects |
|---|---|---|
| **Box spread** | SPX options are section 1256 contracts. The built-in interest shows up as a **60% long-term / 40% short-term capital loss**, marked to market every December 31. It is usable **without itemizing**, with no investment-income limit, and offsets gains first; then $3k/yr against ordinary income, with the rest carried forward. The IRS has not ruled on boxes specifically, so check with the tax preparer. | Most valuable to someone with taxable gains: the middle bracket, and California, which taxes gains as ordinary income. **For the retiree's it is worth little**, because the retiree's federal gains are in the 0% bracket and the retiree's California rate is ~2%. |
| **Margin / HELOC used to invest** | Investment interest (Form 4952): deductible **only if you itemize**, and only up to *ordinary* investment income (interest and non-qualified dividends). MP-2 throws off a lot of that (DBMF/KMLM pay ordinary distributions), so the limit rarely binds. Qualified dividends and long-term gains count only if you give up their low rate. Excess carries forward. | With the 2026 standard deduction ($16,100 single / $32,200 joint), **the retiree won't itemize federally**; a California middle-bracket homeowner usually does, now that the SALT cap is $40,400. California's own standard deduction is tiny, so the **state deduction usually works for everyone**. |
| **Margin / pledged line used to spend** | Personal interest: **not deductible.** | — |
| **HELOC / HECM used to spend** | Federal: not deductible, because the money wasn't used to buy, build or improve the home (OBBBA made this permanent). **California: deductible on up to $100k of home-equity debt for any use** (California never adopted the 2018 change). HECM interest counts only when it's actually paid, usually at the end. | HECM payments are loan proceeds, not income. |
| **Leverage inside funds** | The financing cost is netted inside the fund, so it is **deducted automatically** at your full rate. | Futures and swap funds pay ordinary or 60/40 distributions every year. That is tax-inefficient in a taxable account and irrelevant in a Roth/IRA, which is where to hold them. |
| **Every loan, versus selling** | Borrowed money is **not income**. Selling appreciated funds creates taxable gains that raise MAGI. | 2026 is the first year back on the old ACA rules: subsidies shrink as MAGI rises, and they vanish above 400% of the poverty line (~$62,600 single). Until 65, every $1 of realized gain can cost the retiree Covered California help even when its federal tax is 0%. From 65, MAGI also drives Medicare IRMAA, and later the tax on Social Security. |
| **IRA / Roth** | You **cannot borrow** in or against an IRA: pledging it counts as taking it out. Only leverage inside funds works there. | — |

## Practical setup, easiest first
1. **Keep any low fixed-rate mortgage.** Don't prepay or recast a mortgage below ~4%. T-bills pay 4.09%
   (state-tax-free), so even cash beats its cost. A HECM has to pay the mortgage off first, swapping cheap debt for ~6%
   + insurance. That only makes sense as a cash-flow decision at 62+ (no monthly payment), not as printer credit.
2. **Easiest run line, available today: M1 margin on the retiree's taxable pie.**
   - Nothing to open: accounts of $2k or more can borrow up to 50%.
   - Use it only as the run line: at most 15–25% of the start, only while the account is below its inflation-adjusted
     start, repaid at the first year-end above it.
   - Result: CE +4%, chance of ending below the start 9% → 6%. At 5.90% it is fine for this but **not for boosting**.
3. **Cheapest: a box-spread line at IBKR (or Schwab).**
   - Open a margin account with spread approval.
   - When the run rule says borrow, sell a 1–3-month SPX box. The strike width × 100 is what you owe at expiry, so a
     100-point box means $10,000 due. Enter at the mid price and roll it before expiry. XSP boxes are 1/10 the size
     but trade thinner.
   - SyntheticFi does it for you from a $10k loan, for a fee.
   - Today ~4.4–4.7%; the interest becomes a 60/40 capital loss.
   - IBKR Pro's plain margin (5.38%, or 4.88% above $100k) is the no-options fallback and still clears the bar.
4. **Boost only with someone experienced running it,** for the retiree ≤ 1.2×.
   - 1.1–1.2× through box spreads at IBKR, re-levered at the printer's rebalances, never above 1.33×.
   - Leveraged ETFs such as TQQQ carry higher house margin requirements.
   - For the middle-bracket household this is the biggest lever found (+14% CE).
5. **0% intro APR card: a free 21-month bridge** for a few months of paychecks in a bad year. Charge normal spending
   and clear it before the promo ends.
   - It needs credit approval, limits are small, there is a 5% fee on balance transfers, and the rate after the promo
     is ~18–29%.
   - A supplement to the run line, not a replacement (not modelled).
6. **Roth/IRA: leverage inside funds only** (see point 6 under "What it means").
7. **Skip for the printer:** HELOC (≈ 7.3%, income-qualified, can be frozen), Schwab PAL (≈ 8.3%), 401(k) loans, and
   any credit above about T-bill + 2%.
8. **Not built yet:** `printer/operate.py` doesn't know the run line yet. The next step is adding "borrow $X this month
   instead of selling" and the year-end repayment to its checklist, with the line balance in the state file.

*Research model on historical and simulated data (pre-inception fund histories are reconstructed; T-bills 1972–2026
set the loan rate, so the 1980s rate spikes are included). Tax treatments are simplified: flat marginal rates, and the
ACA/IRMAA effects are described but not modelled. Not financial, tax or legal advice: have the tax preparer confirm the
box-spread and interest-deduction treatment before using them.*
