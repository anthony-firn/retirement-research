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

## Why C1 works (full output: `results/C1_breakdown.txt`, script `lab/analyze_portfolio.py`)
1. **Four uncorrelated defenders + a small growth sleeve.** IEI/KMLM/UUP/GLD are 78% of weight but
   41% of risk; SPMO/QLD/XLP/XLE are 22% of weight but 59% of risk. Pairwise monthly correlations
   among the defenders are −0.39…+0.18; KMLM −0.27 and UUP −0.20 vs US stocks.
2. **Diversification ratio 2.23×**: average holding vol 12.3% → portfolio vol 5.5%.
3. **Rebalancing bonus +1.23 pts/yr**: portfolio CAGR 8.30% vs 7.07% weighted average of holdings.
4. **Every crisis covered by something**: deflationary crashes → IEI (+35% 2000–02, +17% 2008);
   inflation/rate shocks → KMLM (+50%), UUP (+18%), XLE (+45%) in 2022; KMLM positive in all 10
   US-stock drawdowns since 1990. C1 never lost more than 3.5% in any of them.
5. **IEI is the duration sweet spot**: SHY too short (MDD −10.5), TLT too long (2018–26 Sharpe 0.65).
   Removing IEI: MDD −9.1 → −21.7. It is 5% of risk but 24% of return.
6. **Small 2× sleeve beats a bigger unlevered one**: QLD 3% vs QQQ 6% → Calmar 0.92 vs 0.79.
   Yearly rebalancing caps the damage (QLD −99% in 2000–02, C1 still +1.6%) and frees capital for IEI.
   TQQQ 2% instead of QLD 3% is better still on full period (Sharpe 0.942, Calmar 1.04) but just
   misses decade 1.
7. **Path FULL#1 → C1**: SHY+ZROZ→IEI gives most of the Calmar/MDD gain (0.846→0.937); the
   leverage-sleeve step gives most of the Sharpe/Ulcer gain (0.870→0.907, 2.26→2.11); GLD→XLE/UUP
   adds the last Sharpe/Ulcer and fixes decade 1.
8. Result: 36 of 39 full calendar years positive; worst year −1.8% (2002, VTI −20.5%).
- **Fragile bits**: XLP 5% and XLE 3% are small tilts — removing either barely matters (Calmar even
  improves), so treat them as noise-level. The structural parts are IEI, KMLM, UUP, GLD and the small
  leveraged equity sleeve. KMLM (launched 2020) and QLD (2006) are simulated before inception.

## 2026-10-17 — round 4: tuned for the current environment (see `results/MARKET_2026-10.md`)
Regime-aware search (`lab/regime.py`) scores portfolios on 10 historical analogs of today's risks
(AI/tech bust, oil/war shock, Fed hiking into inflation, 10y→5%, credit stress, policy shock).
Excluded: MCISIM (Barings Corporate Investors = private credit), VWEHX (high yield); FKINX-based
"safe" picks rejected for the same credit reason. Verified on testfol.io (`results/verify_regime.log`).

| testfol 1988–2026 | Allocation | CAGR | MDD | Sharpe | Calmar | Ulcer | Scenario score | Worst analog | 2026 YTD |
|---|---|---|---|---|---|---|---|---|---|
| C1 | IEI34 KMLM20 UUP13 GLD11 SPMO11 XLP5 QLD3 XLE3 | 8.30 | −9.09 | 0.937 | 0.913 | 2.02 | −1.54 | −4.3 | +9.3 |
| **C1-Now** | IEI35 KMLM22 GLD14 UUP12 XLE6 XLP5 XLV4 TQQQ2 | 8.01 | −8.27 | 0.916 | 0.968 | 2.11 | **+2.43** | **−2.8** | +9.2 |
| **Safe-Now** | SHY35 IEI33 KMLM10 VBR7 UUP6 XLP4 GLD3 TQQQ2 | 6.83 | **−4.59** | **1.051** | **1.487** | **1.10** | +0.14 | −2.7 | +4.3 |

- C1-Now vs C1: 2000–02 +12.1 vs +1.7, 2008 +13.6 vs +8.5, 2022 +8.3 vs +4.7, 2025 tariffs −2.8 vs −4.3.
  Cost: −0.3 pts CAGR, Sharpe −0.02, Ulcer +0.10. Calmar and MDD improve.
- Safe-Now: 68% Treasuries (SHY+IEI, yielding ~4–5% today) + 10% KMLM + small value/staples/gold/dollar
  + 2% TQQQ. Weak spot = rate shocks (2022 −2.7, 2023 −2.3) — exactly today's regime — but losses stay small.
