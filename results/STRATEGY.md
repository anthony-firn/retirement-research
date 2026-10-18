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

## 3. Life-stage rule (GPU over every quarterly start 1988–2016, retire-on-goal, 4% withdrawals)
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

## Caveats
- History was used to choose all of this; lineup portfolios and leveraged ETFs are simulated before inception.
- Retire-on-goal and 4% inflation-indexed withdrawals are modelling assumptions.
- Daily rebalancing between tiers realises gains — intended for tax-advantaged accounts.
- For a vulnerable/simple case (e.g. the 60-year-old in RETIREE_60.md) a 5-fund leverage-free portfolio
  rebalanced yearly is preferable to the daily advisor.
