# Findings log

All numbers are testfol.io continuous backtests 1987-12-31 → 2026-10-16, yearly rebalance, unless noted.

## 2026-10-16 — round 1: tuning the original portfolio
- Original (VTI 30 / DBMF 23 / GLD 22 / BND 10 / TBF 10 / BIL 5) is already near-efficient.
- Free optimization overfits: walk-forward (pick 1988–2006, test 2007–2026) lost to the original.
- Holding DBMF limits history to 2000; KMLMSIM is the only managed-futures sim to 1988
  (MCISIM is not trend-like: −30% in 2008).
- Greedy "must improve in all 4 decades" found VTI→ZROZ 5%, BIL→UUP 5% (= Current+).

## 2026-10-16 — round 2: wider ETF universe (28 → 58 ETFs)
| Portfolio | CAGR | MDD | Sharpe | Calmar | Ulcer |
|---|---|---|---|---|---|
| Current (KMLM, proxies) | 7.88 | −14.15 | 0.70 | 0.56 | 3.06 |
| Current+ | 7.80 | −11.74 | 0.75 | 0.66 | 2.67 |
| FULL#1 | 8.27 | −9.79 | 0.86 | 0.85 | 2.42 |
| R1 *(uses TBF proxy — disallowed)* | 8.35 | −9.39 | 0.92 | 0.89 | 2.14 |
- Full-period-only winners (IEI/IEF-heavy + tiny TQQQ) beat FULL#1 hugely but lose 2018–2026
  and 2022 → bond-bull artifacts. Requiring every-decade wins fixes this.

## R1 anatomy (what drives this family of portfolios)
- **Barbell**: ~70% weight in mutually uncorrelated defenders (intermediate Treasuries, managed
  futures, gold, US dollar) + ~20% weight in high-octane equity (momentum, value, 2× Nasdaq).
- Equity is 20% of weight but ~60% of risk; IEF is 33% of weight but 7% of risk and 26% of return.
- KMLM was positive in every crisis tested (1990, 1994, 2000–02, 2008, 2015, 2020, 2022 +50%).
- IEF is the deflation-crash hedge (removing it: MDD −9.4 → −21.6); UUP is −0.39 correlated to gold.
- Small leveraged sleeve (QLD 4%) buys equity upside with little capital, freeing room for hedges.

## Rule change
- User: ticker modifiers (`?L=`, `?E=`) are not allowed → R1, Current, Current+ are not valid
  final candidates. Clean benchmark = FULL#1.

## 2026-10-16 — round 3: clean search on GPU (no ticker modifiers)
GPU-batched search (`lab/gpusearch.py`, ~51k portfolios/s on RTX 3050): 1,024 climbers × 10
ILS rounds per universe, ~5 min each. Objective: beat FULL#1 on full-period Sharpe/Calmar/Ulcer/MDD
(CAGR ≥) **and** each decade's Sharpe/Calmar/Ulcer. Top 4 of each universe verified on testfol —
**all 8 beat FULL#1 on the full run and in 4/4 decades** (`results/verify_top.log`).
Adding asset-class mutual funds did not help (best still pure ETF).

testfol.io, continuous 1987-12-31 → 2026-10-16:
| Portfolio | Allocation | CAGR | MDD | Sharpe | Sortino | Calmar | Ulcer | Vol |
|---|---|---|---|---|---|---|---|---|
| FULL#1 | SHY25 KMLM20 SPMO20 GLD15 UUP10 XLV5 ZROZ5 | 8.29 | −9.79 | 0.862 | 1.23 | 0.847 | 2.42 | 6.00 |
| **C1** | IEI34 KMLM20 UUP13 GLD11 SPMO11 XLP5 QLD3 XLE3 | 8.29 | −9.09 | **0.936** | **1.33** | 0.913 | **2.02** | **5.50** |
| **C2** | IEI34 KMLM20 UUP16 SPMO14 GLD10 GSG2 TQQQ2 XLF2 | 8.30 | **−8.72** | 0.922 | 1.31 | **0.951** | 2.05 | 5.60 |
| R1 *(modifier, invalid)* | IEF33 KMLM20 GLD12 SPMO10 UUP8 TBF*7 VOE6 QLD4 | 8.35 | −9.39 | 0.918 | 1.31 | 0.889 | 2.14 | 5.68 |

C1 decade Sharpe vs FULL#1: 1.06/1.01 · 0.77/0.67 · 0.98/0.89 · 0.95/0.91 (Ulcer lower in all four).
The clean winners beat even the modifier-based R1 on Sharpe, Calmar, Ulcer and MDD.
What changed vs FULL#1: SHY → IEI (a bit more duration), more UUP, less SPMO, tiny 2–3× leveraged
equity sleeve, small sector tilts (XLP/XLE or XLF/GSG).
