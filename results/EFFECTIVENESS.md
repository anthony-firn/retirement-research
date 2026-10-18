# How effective is the policy? (2026-10-17)

Head-to-head with what people actually use, same investors and cash flows (retire on reaching the nest egg,
then 4% inflation-indexed withdrawals). Data: testfol.io SIM components 1972–2026 (pre-1988 tiers rebuilt,
managed futures via a haircut trend proxy). Scripts: `strategy/benchmark_life.py`, logs in `results/`.

## Life-plan outcomes
| Investor | Approach | Years to goal p75 (history / synthetic) | Ran out (synthetic) | p5 lowest real after retiring (history / synthetic) | Worst drawdown p99 (history) |
|---|---|---|---|---|---|
| 40y, $250k, +$20k/yr | 100% stocks | 19.8 / 23.1 | 3.8% | 33% / 8% | 55% |
| | 60/40 | 22.3 / 26.5 | 0.9% | 60% / 34% | 34% |
| | Target-date (110−age) | 22.8 / 27.3 | 0.6% | 61% / 36% | 39% |
| | **Policy** | **15.5 / 19.1** | **0.0%** | **78% / 68%** | **29%** |
| 55y, $800k, +$25k/yr | 100% stocks | 9.7 / 11.0 | 8.3% | 42% / 0% | 55% |
| | 60/40 | 10.7 / 13.1 | 4.8% | 59% / 2% | 34% |
| | Target-date | 11.8 / 14.1 | 4.8% | 54% / 1% | 30% |
| | **Policy** | **8.7 / 10.1** | **0.1%** | **80% / 59%** | **29%** |
| Retired 60y, $300k, 4% | 60/40 | — | 12.7% | 51% / 0% | 34% |
| | Target-date | — | 17.1% | 43% / 0% | 27% |
| | **Policy** | — | **0.9%** | **78% / 52%** | **13%** |
(History = every quarterly start 1972–2016; synthetic = 2000 bootstrapped 40-year histories, 1-year blocks.)

## Is the edge real or hindsight?
- **Out of sample for portfolio composition (1972–1987, never seen by the portfolio search):**
  60/40 10.1% CAGR, −29.5% MDD, Sharpe 0.23 · C1-Now 13.4%, −12.5%, 0.67 · S12+ 15.2%, −21.7%, 0.64 ·
  Simple-6.8 12.9%, −11.3%, 0.75.
- **With managed futures replaced by cash** (assume trend-following adds nothing) the tiers still beat 60/40
  (C1-Now 11.1% / −12.2%). The edge is structural diversification (intermediate Treasuries, gold, dollar,
  value, energy, trend), not one lucky fund.
- **Costs:** with an extra 0.5–1.0%/yr drag on every tier the policy still wins for accumulators; for retirees the
  synthetic run-out rises to 2.9–7.5% (benchmarks 12.7–17.1%).
- **What did not work:** market-timing signals (no out-of-sample benefit), tight drawdown breakers (lock-in),
  leveraged high-end tiers (wrecked in 1973–74).

## Product readiness — honest view
Valuable: a personalised, testable risk budget (age, savings, goal, tolerance) → a concrete diversified
portfolio, a guaranteed loss cap, a withdrawal rule, and a trade list. Backtests beat 100% stocks, 60/40 and
target-date funds on both speed-to-retirement and worst-case outcomes.

Before offering it to other people:
1. **Regulation.** Personalised recommendations for others is investment advice (SEC/state adviser registration,
   suitability, disclosures). Get a securities lawyer; an "education/planning tool" framing is not automatically safe.
2. **Data dependence.** It relies on testfol.io's undocumented API and simulated (SIM) histories; production needs
   licensed price data and its own simulations.
3. **Model risk.** Pre-inception data for KMLM, TYD, TQQQ etc. is simulated; the 1970s managed-futures leg is a proxy.
4. **Suitability & simplicity.** Leveraged ETFs and daily breaker checks don't suit everyone; offer the leverage-free
   5-fund variants for simple/vulnerable users (see RETIREE_60.md).
5. **Taxes & execution.** Daily switching realises gains; taxable accounts need drift bands / loss harvesting.
6. **Missing inputs that matter more than the portfolio for many users:** Social Security timing, pensions, health
   costs before Medicare, emergency fund, debts.
