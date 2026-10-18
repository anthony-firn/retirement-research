# Money Printer search: the best printers found (2026-10-18)

## The system
| Step | Code | What it does |
|---|---|---|
| Simulate | `printer/money_printer.py` | A whole printer (engine + rebalancing + base/bonus print + guardrail + per-fund taxes) on the GPU, daily or weekly steps |
| Search | `printer/search.py balanced\|max_print\|fortress\|the retiree's` | 64 GPU hill-climbers evolve fund weights (27-fund universe) and print settings together on 256 shared histories |
| Validate | `printer/validate.py` | Re-runs the finalists **daily on 2,000 fresh histories** plus 6 stress cases, and checks each engine on testfol.io |

- **Score: certainty-equivalent (CE) spending.** This is the steady after-tax monthly amount worth the same to the retiree as the
  printer's actual uneven income. It uses risk aversion 3, and each year is weighted by the chance a 60-year-old woman is
  still alive. Lean years weigh far more than fat ones, so CE rises with the print and with its reliability.
- **Break-risk penalties:** runs dry in more than 1% of histories (3% under the trend stress), ends below its starting
  real value too often, or cuts the base too often.
- **Engine guard rails:** at most 9 funds and 35% in any one; trend funds ≤ 42%, leveraged funds ≤ 25%, AI/mega-tech
  exposure ≤ 25%; every bad forward scenario ≥ −8.5%.
- **Searches:**
  - `balanced`: the main ranking.
  - `max_print`: less risk-averse.
  - `fortress`: very risk-averse, and may lose real value in at most 5% of histories.
  - `retiree`: maximizes the worst case over the base, trend-bear (−2%/yr) and gold-bear (−3%/yr) scenarios. Requires at
    least CH-12's ages 60–70 print, no K-1 funds, and runs dry in at most 0.5% of histories.
- **Robust CE** = the average CE over the base case plus 6 stress cases: trend funds −2% and −4%/yr, 3-month-block
  reshuffle, recent era only (2000–2026 blocks), gold −3% and −5%/yr. **Worst-case CE** = the lowest of the seven.

## Results (fresh validation histories, the retiree's taxes, per $100k, $/month in today's dollars)
| Printer | Engine | Robust CE | Worst-case CE | Typical | Bad history | Ages 60–70 | Base print | Base never cut | Loses value | Dry | testfol 2000–26 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **MP-2 (retiree search, 6 funds)** | DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · GLD 8 · TQQQ 2 | **$518** | **$452** | $833 | $551 | **$494** | **$479** | 86% | 9% | 0.1% | 11.00% / −22.1% / 0.782 |
| retiree #1 (9 funds) | DBMF 27 · VBR 25 · GDE 19 · KMLM 15 · GLD 8 · TQQQ 2 · ZROZ 2 · TYD 1 · XLP 1 | $514 | $442 | $811 | $537 | $488 | $479 | 87% | 9% | 0.1% | 10.77% / −19.8% / 0.809 |
| Balanced #1 | GDE 23 · VBR 23 · DBMF 21 · KMLM 16 · GLD 10 · UGL 3 · … | $461 | $372 | $856 | $500 | $479 | $479 | 87% | 8% | 0.9% | 11.47% / −21.7% / 0.794 |
| **MP-Fortress** | KMLM 22 · VBR 20 · DBMF 16 · GLD 15 · UGL 8 · XLV 7 · SPMO 5 · UUP 4 · TQQQ 3 | $458 | $424 | $722 | $509 | $405 | $375 | **97%** | **5%** | **0.0%** | 9.90% / −16.5% / 0.785 |
| Max-print #3 | GDE 25 · DBMF 25 · KMLM 15 · VBR 14 · GLD 12 · TQQQ 5 · … | $451 | $371 | $848 | $554 | $523 | $438 | 87% | 15% | 0.9% | 11.82% / −20.5% / 0.813 |
| CH-12 Printer (previous) | DBMF 25 · KMLM 16 · GLD 15 · VBR 15 · XLV 13 · TYD 11 · TQQQ 5 | $442 | $398 | $718 | $496 | $458 | $333 | 94% | 10% | 0.1% | 9.80% / −14.0% / 0.878 |
| 60/40 Printer | VTI 60 · BND 40 | $300 | $264 | $468 | $284 | $354 | $333 | 40% | 59% | 7.0% | 7.06% / −34.0% / 0.492 |
| VTI Printer | VTI 100 | $251 | $212 | $631 | $285 | $501 | $333 | 22% | 60% | 12.7% | 8.50% / −55.4% / 0.419 |

Printer settings:
- **MP-2:** base 5.75%; skim above 140%; 48-month bucket; guardrail cuts the base to 65% below 70% of start.
- **MP-Fortress:** base 4.5%; skim above 135%; 60-month bucket; guardrail cuts to 80% below 65% of start.
- **CH-12:** base 4%; skim above 125%; 36-month bucket; guardrail cuts to 80% below 70% of start.
- **All printers:** rebalance when any fund is > 6 points off target, at most once a year, plus the 2× valve.
- **Full details:** `results/printer_validate_table.md`, `printer_validate.json`, `printer_mp2_simplify.log`.

## Verdict
- **MP-2 is the best money printer found for the retiree.** It has the highest robust and worst-case CE, and the highest base
  print ($479 per $100k vs $333). It also pays the most in the retiree's 60s ($494 vs $458) and never needs a K-1 fund.
  - It is better than CH-12 in every one of the 7 scenarios. Its worst case, trend funds earning 4% a year less, is
    $452 versus CH-12's $398.
  - **The price:** the account swings more. It dips below 70% of its inflation-adjusted start in 19% of histories
    (CH-12: 8%), and the guardrail cuts the base in 14% of histories (CH-12: 6%). Even cut, the base ($311) is about
    CH-12's normal base.
  - On testfol.io it is a higher-return, bumpier portfolio: 11.0% a year from 2000 with a −22% worst drop (CH-12:
    9.8%, −14%).
- **MP-Fortress is the lowest-break-risk printer:** runs dry 0.0%, loses value 5%, base never cut in 97% of histories.
  It prints less early ($405 in the retiree's 60s) and holds two K-1 funds (UGL, UUP), so it suits an IRA better than the retiree's
  taxable account.
- **The search's gold-heavy winners didn't hold up.** Balanced #1 and the max-print printers held 34–39% effective
  gold, and they fell apart in the gold-bear stress (worst-case CE $350–372). The `retiree` search was built to avoid
  that; MP-2 has about 27% effective gold.

## Caveats
- **All of it is history-based.** It reshuffles real and reconstructed 1972–2026 history. GDE has only been a real
  fund since 2022, and KMLM and DBMF since 2019–2020; before that they are simulated.
- **The search was tuned on 256 histories and checked on 2,000 fresh ones.** The fresh-data results held up (MP-2 CE
  $584 versus the search's ~$575 at weekly steps), but tuning always flatters the winner a little.
- **Budget on the base print; the bonus is extra.**
- **Research model, not financial advice.** The retiree's tax preparer and a fee-only fiduciary should review it before use.
