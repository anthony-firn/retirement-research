# Indicator tilts for the money printer — tested, rejected (2026-10-18)

The idea: tilt MP-2's target weights a few points while market indicators flash, to squeeze out more reliability.
`printer/signals.py` (indicator states from data available at the time), `printer/tilt_search.py`, `results/tilt_*.log`.
- **Signals, checked monthly:**
  - S&P below its 10-month average.
  - S&P 3-month volatility above 20%.
  - 10-year yield below the 3-month yield.
  - CPI up more than 4% over 12 months (lagged 1 month).
  - Gold below its 10-month average.
- **Tilts while a signal is on:** move 5, 10 or 15 points from stocks to short Treasuries or the trend funds; from VBR
  to gold (inflation signal); or from gold to defensive (gold signal).
- **Testing:** the printer rebalances to the tilted targets when the signal state changes, and trading costs and the retiree's
  taxes are included. Variants were picked on 1972–1999-only histories and judged on 2000–2026 histories they never saw.

**Result 1 — the best combined rules are overfit.** The 10 best of 2,048 variants beat plain MP-2 by 12–14% on
1972–99. **Every one of them was worse on 2000–26:** CE $492–522 vs $542 per $100k per month. They also had lower
reliability (base never cut 73–78% vs 80%; dips below 70% in 27–32% of histories vs 25%) and spent less on the actual
2000–26 path ($491–520 vs $573/month).

**Result 2 — no single indicator helps in both eras:**
| Signal (best size) | 1972–99 | 2000–26 |
|---|---|---|
| S&P below 10-month average | −0.8% | −0.1% |
| High volatility | −0.8% | −1.0% |
| Inverted yield curve | +4.4% | −5.7% |
| High inflation → gold | −3.1% | +3.4% |
| Gold below 10-month average | +10.6% | −1.4% |
Each one either hurt in both periods or helped in one and hurt in the other. That is the signature of a pattern
that belonged to its era, not a rule: gold's 1980–2000 bear market, and yield-curve inversions that predicted 1970s–90s
recessions but not the 2022–24 boom.

**Why:**
- **The timing is already inside.** MP-2 already holds 42% in trend-following funds (DBMF, KMLM), which do disciplined
  timing internally.
- **It already adapts.** The printer adapts on its own: it sells from overweight funds, skims only when ahead, and the
  guardrail cuts spending in slumps.
- **Extra layers cost money.** Another layer of timing adds trades and taxes, with no proven edge.
This matches the earlier walk-forward finding: timing signals had no out-of-sample benefit.
**Decision: MP-2 stays as is. The operator stays rule-based on prices, inflation and drift — no forecasting.**
