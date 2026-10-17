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
