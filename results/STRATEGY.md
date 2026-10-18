# Switching strategy — findings (2026-10-17)

All strategy backtests run daily on testfol.io daily histories of the lineup portfolios (1988–2026), with a
1-day execution lag, 0.10% cost per full tier moved, and continuous blends between adjacent tiers.
Code: `strategy/` (GPU engine `gpu_strategy.py`, life-plan engine `life_gpu.py`, policy `policy.py`, advisor `advisor.py`).

## 1. Market-timing signals do not survive out of sample
GPU search over ~1.2M strategies (SMA trend, realised vol, VIX, IEF rate-shock, hedged twins, re-entry delays,
deadbands, drawdown governors). In-sample they beat buy-and-hold at every drawdown budget; **walk-forward
(choose on 1988–2006, test 2007–2026) they roughly matched buy-and-hold and broke their budget 4 of 9 times.**
Timing signals were dropped from the policy.

## 2. A guaranteed drawdown breaker works — if it has margin
Breaker on the all-time high, checked daily: position capped at the tier whose worst historical day
(incl. a 1987 Black Monday reconstruction) fits in the remaining cushion → total loss bounded by construction.
- Held its budget 9/9 out of sample. Tight breakers on aggressive tiers lock in losses after a trip
  (E20 with a 30% breaker: 10.4% vs 20.0% CAGR). With margin it costs 0.0–0.4 pts CAGR.
- Final rule: tier with MDD ≤ 75% of budget and (MDD + worst day) ≤ 90% of the breaker level; breaker = budget − 2.
  The breaker never fires in 1988–2026 — it exists for an unprecedented crash.

## 3. Life-stage rule, first pass on 1988–2016 starts (superseded by the 1972 calibration in section 5)
`budget = min(comfort cap, 50, 20 + 2.5 × years to retirement)`; retired / funded: `15`.
Chosen on 1988–2002 starts, validated on 2003–2016 starts (same rule both ways).
| Profile | Old rule p75 years to goal | New rule | Lowest real value after retiring (old → new) |
|---|---|---|---|
| 25y, $20k, +$12k/yr, $60k spending | 25.3 | 20.3 | 48% → 71% of nest egg |
| 40y, $250k, +$20k/yr, $70k | 23.0 | 12.4 | 20% → 71% |
| 55y, $800k, +$25k/yr, $70k | 15.7 | 7.1 | 23% → 71% |
- Retirees: an 8% budget let real wealth fall to 21% of the start (too little return for 4% + inflation);
  15–20% keeps the worst case at 73–84%. "Safest" by drawdown is not safest for someone withdrawing.

## 4. Comfort cap: drop you can sit through vs retiring sooner (40y, $250k, +$20k/yr)
| Worst drop lived through | 7.5% | 10% | 14% | 18% | 24% | 30% |
|---|---|---|---|---|---|---|
| Years to retire (median / p75) | 21.6/25.1 | 17.8/21.3 | 16.0/18.8 | 14.8/16.8 | 13.3/14.7 | 11.2/12.4 |
Actual worst drop ≈ 60% of the cap → `advisor.py --max-drop X` sets cap = X / 0.6.
Full menus for all profiles: `results/comfort_menu.log`.

## 5. Stress beyond 1988: the 1970s and 2000 synthetic histories
- Tiers rebuilt back to 1972 from testfol SIM components (`strategy/history70s.py`); KMLM before 1988 = 12-month
  trend proxy on stocks/bonds/gold/commodities/dollar, **haircut** to KMLM's 1988–2026 return (7.4% vs 7.7%, corr 0.39).
- 1970s reality check: aggressive tiers are far riskier than 1988–2026 shows (E15 −36%, M25 −39%, M30 −46%,
  E20 −59% max drawdown); over 1972–2026 budgets above ~30% earned no extra return.
- The 1988-calibrated policy run through 1972–2026 (true out-of-sample): breaker held every budget, nobody ran out.
- **Final calibration uses 1972–2026 tier risk** and the rule `25 + 3 × years` (cap 50), retired 25 →
  max budget maps to S13.5/E14 (worst drop 28.7% 1972–2026); leveraged E15+ tiers are no longer selected.
- Block bootstrap (2000 × 40-year histories, 1-year blocks from 1972–2026): retiree (4%, 40 years) ran out
  old rule 44.6% → 1988 rule 14.1% → final 1.4%; age 55: 2.6% → 0.2%; breaker held in every history.

## 6. Withdrawal rule for retirees (`strategy/withdraw_rules.py`)
| Rule (on $300k, 40 years, harsh histories) | Ran out | p5 lowest real | Avg spending vs plan | Deepest cut |
|---|---|---|---|---|
| fixed 4% | 1.1% | 48% | 100% | 0% |
| fixed 3.5% | 0.1% | 70% | 100% | 0% |
| guardrail 4% | 0.1% | 60% | 99% | 20% |
| **floor-ceiling 4%** (4% of current value, within 85–120% of plan) | **0.1%** | **66%** | **112%** | **15%** |
The advisor prints this year's floor-ceiling withdrawal for retirees.

## Caveats
- History was used to choose all of this; lineup portfolios and leveraged ETFs are simulated before inception.
- Retire-on-goal and 4% inflation-indexed withdrawals are modelling assumptions.
- Daily rebalancing between tiers realises gains — intended for tax-advantaged accounts.
- For a vulnerable/simple case (e.g. the 60-year-old in RETIREE_60.md) a 5-fund leverage-free portfolio
  rebalanced yearly is preferable to the daily advisor.
