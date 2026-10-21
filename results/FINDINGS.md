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

## 2026-10-17 — round 5: return vs safety guide (ETF-only efficient frontier, 6–15% CAGR)
`lab/frontier.py` (SAFETY=absolute): for each target CAGR, maximise the worst of {Ulcer, MaxDD} over the
full period **and every decade**, measured against C1's full-period values; every decade must earn ≥ 0.7×target.
Same rules (testfol 1988–2026 continuous, ≤8 ETFs, ≤35%, no modifiers). Verified: `results/verify_frontier_etf.log`.
(Two earlier definitions were discarded: ratios-vs-C1 returned C1 itself at 7%; same-decade drawdown
normalisation rated a riskier portfolio above Safe-Now.)

| Target | Allocation | CAGR | Vol | MaxDD | Sharpe | Calmar | Ulcer | Worst yr | 2018–26 CAGR / Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 6% | SHY35 IEI24 UUP13 VOE10 GLD6 KMLM6 XLV5 TECL1 | 6.30 | 3.3 | −4.1 | 0.967 | 1.53 | 0.89 | −2.2 | 5.1 / 0.72 |
| 7% | SHY32 IEI26 UUP12 VOE9 KMLM7 XLV7 GLD5 TQQQ2 | 7.13 | 4.0 | −4.8 | 0.993 | 1.49 | 1.10 | −2.9 | 5.6 / 0.75 |
| 8% | SHY34 IEI33 XLV11 KMLM10 XLE4 XLY3 TQQQ3 GLD2 | 8.08 | 5.1 | −5.7 | 0.977 | 1.43 | 1.41 | −2.5 | 6.1 / 0.70 |
| 9% | IEI35 SHY24 XLV12 KMLM10 XLE8 GLD6 TQQQ4 TMF1 | 9.00 | 6.1 | −8.2 | 0.954 | 1.10 | 1.81 | −1.0 | 7.4 / 0.78 |
| 10% | IEF31 IEI18 KMLM14 XLV13 GLD8 VBR7 XLE5 TQQQ4 | 10.00 | 7.0 | −10.0 | 0.975 | 1.01 | 2.19 | −3.1 | 7.9 / 0.74 |
| 11% | IEI27 KMLM18 XLV15 TYD13 VBR11 GLD6 XLE6 TQQQ4 | 11.00 | 8.1 | −12.1 | 0.961 | 0.91 | 2.67 | −3.4 | 7.9 / 0.66 |
| 12% | TYD18 KMLM17 XLV16 IEI14 VBR13 GLD11 XLE6 TQQQ5 | 11.99 | 9.4 | −14.4 | 0.939 | 0.83 | 3.19 | −5.7 | 9.1 / 0.69 |
| 13% | VBR21 TYD20 KMLM19 XLV19 GLD9 TQQQ5 XLE5 ZROZ2 | 12.99 | 10.6 | −17.1 | 0.924 | 0.76 | 3.67 | −6.8 | 9.4 / 0.64 |
| 14% | TYD30 VBR20 KMLM17 XLE12 TQQQ8 GLD6 XLV4 REIT3 | 14.01 | 12.1 | −21.1 | 0.899 | 0.66 | 4.51 | −9.2 | 9.8 / 0.61 |
| 15% | TYD31 VBR22 XLE15 KMLM13 TQQQ10 REIT7 UGL2 | 14.99 | 13.9 | −25.8 | 0.860 | 0.58 | 5.65 | −11.8 | 10.7 / 0.59 |

- Sweet spot 7–10%: Sharpe ≈ 0.95–0.99 throughout. Each step above 11% costs ~3–4.5 pts of max drawdown.
- How return is bought: Treasuries shift from SHY/IEI → IEF → 3× TYD; equity from defensive (XLV/VOE) →
  small-cap value VBR + TQQQ 4→10%; energy XLE grows; KMLM stays 6–19% throughout.
- Caveat: these are *historically* safest. They lean on Treasuries (including 3× TYD at 12%+), which benefited
  from 1988–2020 falling rates; in rate-shock analogs (2022, 2023) they lose where C1-Now gains, and their
  2018–26 Sharpe (0.59–0.78) is below C1 (0.95). Leveraged ETFs (TYD, TQQQ, TMF, UGL) are simulated pre-inception.

## 2026-10-17 — round 6: pushing the frontier higher (fill 12.5–14.5%, 16–26%, drawdown-capped max return)
Verified on testfol: `results/verify_frontier_hi.log`, `results/verify_maxret.log`.

**Safest-at-target (E, Ulcer/MDD safety):**
| Target | Allocation | CAGR | MaxDD | Sharpe | Ulcer | Worst yr | 2018–26 CAGR |
|---|---|---|---|---|---|---|---|
| 12.5% | TYD23 KMLM20 VBR20 XLV14 GLD9 TQQQ5 XLE5 UUP4 | 12.51 | −15.6 | 0.936 | 3.42 | −6.4 | 9.0 |
| 13.5% | TYD25 KMLM19 VBR18 GLD10 XLV10 TQQQ7 XLE7 REIT4 | 13.50 | −18.8 | 0.920 | 4.07 | −9.1 | 9.9 |
| 14.5% | TYD31 KMLM17 REIT14 XLE13 TQQQ10 VBR9 GLD5 XLB1 | 14.49 | −23.4 | 0.878 | 5.14 | −12.5 | 10.2 |
| 16% | TYD35 XLE19 REIT16 TQQQ13 VBR11 KMLM5 UGL1 | 16.00 | −32.3 | 0.817 | 7.09 | −17.0 | 11.6 |
| 18% | TYD30 VBR30 TQQQ18 XLE8 REIT7 KMLM4 TMF3 | 17.99 | −37.6 | 0.803 | 10.0 | −27.7 | 12.6 |
| 20% | VBR35 TQQQ24 TYD23 TMF10 XLE6 KMLM2 | 19.99 | −47.7 | 0.781 | 14.0 | −35.0 | 14.1 |
| 22% | TQQQ32 TYD21 VBR17 TMF15 XLE12 REIT3 | 21.99 | −61.9 | 0.762 | 18.6 | −40.0 | 16.5 |
| 24% | TQQQ35 TMF29 XLE28 TECL6 VBR1 UPRO1 | 23.99 | −78.5 | 0.733 | 27.0 | −42.3 | 21.9 |
- **25% is infeasible** under the rules (best 24.7%, MDD −86%); search stopped at 26%.

**Max CAGR under a max-drawdown cap (M, every period incl. each decade):**
| Cap | Allocation | CAGR | MaxDD | Sharpe | Calmar | Ulcer | Worst yr |
|---|---|---|---|---|---|---|---|
| 25% | TYD35 VBR24 TQQQ14 KMLM13 XLE9 GLD3 REIT1 QLD1 | 16.52 | −25.0 | 0.858 | 0.66 | 7.16 | −19.6 |
| 30% | TYD30 VBR27 TQQQ16 XLE10 KMLM8 TMF4 GDE3 REIT2 | 17.43 | −30.0 | 0.830 | 0.58 | 8.65 | −23.3 |
| 35% | TYD34 VBR31 TQQQ19 XLE8 KMLM6 TMF2 | 18.31 | −35.0 | 0.814 | 0.52 | 10.2 | −27.1 |
| 40% | VBR35 TYD31 TQQQ21 XLE5 KMLM4 TMF3 VOE1 | 18.97 | −40.0 | 0.796 | 0.47 | 11.8 | −31.1 |
| 50% | VBR32 TYD29 TQQQ26 TMF8 XLE5 | 20.37 | −49.9 | 0.772 | 0.41 | 15.0 | −38.7 |

- M25 beats E15/E16 on CAGR and MaxDD (16.5% at −25%) but has higher Ulcer and a −19.6% worst year:
  the E curve minimises time-under-water (Ulcer), the M curve minimises the single worst drop.
- Above ~15%, return comes from leverage: 3× Treasuries (TYD/TMF at the 35% cap) + 3× Nasdaq
  (TQQQ 14→35%) + small-cap value. Diversifiers (KMLM, GLD, XLV) are squeezed out.
- **2022 is the worst year for every high-return portfolio** (TYD/TMF and TQQQ fell together when
  stock–bond correlation turned positive) — the same regime as today (see MARKET_2026-10.md).
- 2018–26 decade Sharpe ≈ 0.56–0.62 for all points ≥ 15% vs ~1.0 in 2008–17: the leverage engine
  worked best in the falling-rate era.

## 2026-10-17 — round 7: sweet spot 12–13.5%, safest with today's-economy guard rails
`lab/frontier.py SAFETY=nowsafe`: historical absolute safety (Ulcer/MDD every decade) **plus** guard rails from
`MARKET_2026-10.md`: every analog episode ≥ −8%, the 2022 inflation/war/rates episode ≥ −3%, and (12–12.5%)
AI/mega-tech notional exposure ≤ 15% (TQQQ counts 3×, S&P ≈ 40% AI). Variants V1–V4 mapped the trade-off
(−6% floor caps CAGR at ~12.5%; AI ≤ 10% caps it at ~11.8%); a seeded polish pass gave the finals.
Verified: `results/verify_sweet_final.log`.

| testfol 1988–2026 | Allocation | CAGR | MaxDD | Sharpe | Calmar | Ulcer | Worst yr | 2022 ep. | 2000–02 | Worst analog | 2018–26 CAGR/Sh | 2026 YTD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E12 | TYD18 KMLM17 XLV16 IEI14 VBR13 GLD11 XLE6 TQQQ5 | 11.99 | −14.4 | 0.939 | 0.83 | 3.19 | −5.7 | −6.9 | +4.1 | −11.2 | 9.1/0.69 | +8.8 |
| **S12** | KMLM35 VBR19 TYD14 GLD14 XLV9 TQQQ5 UUP3 GSG1 | 12.01 | **−13.9** | **0.950** | **0.86** | 3.47 | **−3.2** | **+2.9** | +4.0 | **−7.9** | **9.5/0.75** | +10.3 |
| E12.5 | TYD23 KMLM20 VBR20 XLV14 GLD9 TQQQ5 XLE5 UUP4 | 12.51 | −15.6 | 0.936 | 0.80 | 3.42 | −6.4 | −6.5 | +4.9 | −12.1 | 9.0/0.65 | +9.2 |
| **S12.5** | KMLM35 TYD18 XLV17 VBR14 GLD8 TQQQ5 XLE2 XLP1 | 12.49 | **−15.4** | **0.952** | **0.81** | 3.70 | **−2.5** | **+1.7** | +4.4 | **−8.0** | 9.0/0.69 | +10.9 |
| E13 | VBR21 TYD20 KMLM19 XLV19 GLD9 TQQQ5 XLE5 ZROZ2 | 12.99 | −17.1 | 0.924 | 0.76 | 3.67 | −6.8 | −7.9 | +1.9 | −14.4 | 9.4/0.64 | +10.0 |
| **S13** | KMLM35 GLD19 TYD16 XLP8 TQQQ8 VBR8 XLE5 SPMO1 | 13.00 | −17.8 | **0.931** | 0.73 | 4.30 | **−6.5** | **+2.4** | −3.9 | **−7.9** | **11.4/0.85** | +11.2 |
| E13.5 | TYD25 KMLM19 VBR18 GLD10 XLV10 TQQQ7 XLE7 REIT4 | 13.50 | −18.8 | 0.920 | 0.72 | 4.07 | −9.1 | −9.9 | +0.9 | −14.5 | 9.9/0.65 | +9.5 |
| **S13.5** | KMLM35 GLD24 TYD18 TQQQ10 XLE9 VBR2 REIT1 XLP1 | 13.49 | −19.4 | 0.899 | 0.70 | 4.89 | **−8.1** | **+2.9** | −7.7 | **−8.0** | **12.7/0.88** | +11.6 |

- S12/S12.5 dominate E12/E12.5 on everything except long-run Ulcer (+0.3): better Sharpe, MDD, worst year,
  2022, every analog, and still positive in the 2000–02 tech bust. AI exposure ≤ 15%.
- S13/S13.5 need TQQQ 8–10% (AI exposure 25–30%) → negative in the tech-bust analog (−3.9 / −7.7).
- Managed futures hits the 35% cap in every final. Implementation: split KMLM18/DBMF17 — testfol 2000–26
  improves Sharpe 0.834→0.883 (S12), 0.813→0.862 (S12.5) and Ulcer 3.65→3.20 / 3.81→3.39.
- Expectation check: 2000–2026 CAGR is ~9.5–9.8% for S12/S12.5 (1988–99 lifts the full-period figure).

## 2026-10-17 — round 8: safer than S12 at ~12%
1. **Beat-S12 search** (`SAFETY=beat`): must beat S12 on full Sharpe/Calmar/Ulcer/MDD, every decade's Ulcer
   and MDD, and the worst analog, under the same guard rails (analogs ≥ −8%, 2022 ≥ −3%, AI ≤ 15%), CAGR ≥ 11.9%.
   Two seeds and the expanded universe all converge to **S12+** → effectively the optimum; it is better on
   everything except the worst analog, which is a tie within the local/testfol gap.
2. **Forward-looking stress** (`lab/stress_forward.py`, hypothetical 2026–27 moves: AI bust, oil stagflation,
   bond revolt 10y→6.5%, deflationary recession, dollar crisis, soft landing). S12's weak spot: bond revolt −7.2%
   (TYD 14%). `FWD_FLOOR` constraint gives **S12-F5** (all scenarios ≥ −5%); ≥ −4% costs too much history.

| testfol 1988–2026 | Allocation | CAGR | MaxDD | Sharpe | Calmar | Ulcer | Worst yr | Worst analog | 2022 | 2018–26 CAGR/Sh | 2026 YTD | Bond revolt | Oil stagfl. | AI bust |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S12 | KMLM35 VBR19 TYD14 GLD14 XLV9 TQQQ5 UUP3 GSG1 | 12.01 | −13.9 | 0.950 | 0.864 | 3.47 | −3.2 | −7.9 | +2.9 | 9.5/0.75 | +10.3 | −7.2 | −1.7 | −2.4 |
| **S12+** | KMLM35 VBR18 TYD12 GLD11 XLV9 IEI9 TQQQ5 XLE1 | 11.90 | **−13.7** | **0.957** | **0.870** | **3.38** | −3.2 | **−7.7** | +2.8 | 9.1/0.73 | +10.2 | −6.8 | −1.9 | −2.6 |
| **S12-F5** | KMLM35 GLD19 XLV15 TYD11 XLE9 TQQQ5 IWC4 SHY2 | 11.90 | −16.0 | 0.917 | 0.745 | 3.81 | −3.7 | −8.0 | **+8.5** | **11.0/0.86** | **+13.7** | **−5.0** | **+4.8** | **−1.5** |
| S12-F4 | KMLM35 XLV29 GLD17 UUP5 TQQQ5 TYD5 VBR3 IEF1 | 11.89 | −18.6 | 0.901 | 0.641 | 4.05 | −6.3 | −7.9 | +7.1 | 11.0/0.89 | +12.1 | −3.8 | +2.0 | −2.0 |

- S12+ = direct upgrade of S12 by history (swaps 2% TYD + some VBR/GLD for 9% IEI, i.e. less 3× duration).
- S12-F5 = built for today's specific risks (more gold/energy/health care, less leveraged duration); best recent
  decade and 2026 YTD, but weaker 1988–97 and slightly negative in the 2000–02 tech-bust analog (−1.1).

## 2026-10-20 — credit for the printer (`results/CREDIT.md`, `printer/credit.py`)
MP-2 with each kind of credit at today's rates and its own tax treatment. Per $100k, robust CE, the retiree's taxes; plain MP-2 = $529.
- **Boost at 1.2×** (hold 1.2× the account): box-spread loan $586 (+11%), leverage inside funds $578, IBKR margin $569,
  M1 margin $561, HELOC $538. At box rates every printer quality improves slightly, with no margin calls. In the middle
  bracket, box 1.2× gives $545 vs $478. In a Roth, leverage inside funds at 1.2× gives $659 vs $600.
- **Run line** (borrow the paycheck while below the start, repay above it): a 25% box line gives $568 (+7%), and the
  chance of ending below the start falls from 9% to 5%. It also allows a 6.25% base at plain MP-2's break risk.
- **Credit above about T-bill + 2% doesn't pay:** HELOC/HECM ≈ 0, Schwab PAL −6%. If trend funds earn 4%/yr less, only
  box-rate credit still helps, and margin calls appear in 1–3% of histories.
- **Keep any low fixed-rate mortgage** (below ~4%). IRAs can't borrow, so leverage inside funds is the only option there. Next step: add
  RSSB/RSST/RSBT to the Atlas, and the run line to the operator.
- **Retiree case, $50k taxable, as much credit as makes sense** (`MODE=sweep`, 62 designs, 2× Reg T limit): only a
  **$10k box-spread loan (1.2×) with a 5.25% base** keeps break risk at or below plain MP-2 in all 5 cases.
  - Result: $505/month typical 40-year average (vs $420), $350 bad (vs $269), first decade $286 (vs $251).
  - The floor is $219 instead of $240.
  - 1.75–2× raises the average to $713–808 but fails (deep dips 34–46%, margin calls up to 5%).
  - Nothing at M1's 5.90% passes.

## 2026-10-21 — passive improvements, overnight (`results/IMPROVE.md`, `printer/improve.py`)
- Batch 1: GLD → IAUM (+0.3% robust CE) and the cash bucket in BOXX (+0.1%), accepted on both tracks with break risk
  no worse. Both are free: same holdings, lower fee or tax.
- Batch 2: settings re-tune, credit combo and stock/bond stacked funds (NTSX, RSSB): no improvement passes. MP-2's
  settings are at the retiree's optimum, and bond stacking hurts the trend + gold engine.
- Batch 3: glidepaths and income rules don't help. Skipping raises after a losing year trades early income for
  safety. Credit track: valve 3× + restore at 80% accepted (+0.8%). RSST is rejected: it passes only with an
  optimistic proxy.
- Batches 4–5: calmer engines with leverage, GDE stacking and a weight hill-climb don't pass (the climb overfits its
  own histories). Credit track: bucket pays the loan down (+0.2%), then leverage 1.25× with a 10-point band (+2.0%).
