# Portfolio lineup — best candidate per CAGR bracket (2026-10-17)

All numbers: testfol.io continuous backtest 1987-12-31 → 2026-10-16, yearly rebalance, real ETFs via SIM backfill,
no ticker modifiers, ≤ 8 holdings, ≤ 35% each. "2022" and "2000–02" are the historical analog episodes;
"Worst forward" is the worst of six hypothetical 2026–27 scenarios in `lab/stress_forward.py`
(AI bust, oil stagflation, bond revolt, deflationary recession, dollar crisis, soft landing).
Built from existing verified results — no new searches. Definitions in `portfolios.json`.

## Lineup
| Tier | CAGR | Pick | Allocation | CAGR | Max DD | Sharpe | Calmar | Ulcer | Worst yr | 2022 | 2000–02 | Worst forward | 2018–26 CAGR/Sh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Preserve | ~6–7% | **Safe-Now** | SHY 35 · IEI 33 · KMLM 10 · VBR 7 · UUP 6 · XLP 4 · GLD 3 · TQQQ 2 | 6.82 | -4.6 | 1.050 | 1.49 | 1.10 | -3.2 | -2.7 | +15.6 | -2.9 | 4.6/0.58 |
| Conservative | ~8% | **C1-Now** | IEI 35 · KMLM 22 · GLD 14 · UUP 12 · XLE 6 · XLP 5 · XLV 4 · TQQQ 2 | 8.01 | -8.3 | 0.917 | 0.97 | 2.11 | -0.8 | +8.3 | +12.1 | -1.1 | 7.5/0.88 |
| Conservative+ | ~9% | **E9** | IEI 35 · SHY 24 · XLV 12 · KMLM 10 · XLE 8 · GLD 6 · TQQQ 4 · TMF 1 | 9.00 | -8.2 | 0.954 | 1.10 | 1.81 | -1.0 | -1.9 | +3.3 | -4.8 | 7.4/0.78 |
| Balanced | ~10% | **E10** | IEF 31 · IEI 18 · KMLM 14 · XLV 13 · GLD 8 · VBR 7 · XLE 5 · TQQQ 4 | 10.00 | -10.0 | 0.975 | 1.00 | 2.19 | -3.1 | -4.1 | +4.5 | -7.2 | 7.9/0.74 |
| Balanced+ | ~11% | **E11** | IEI 27 · KMLM 18 · XLV 15 · TYD 13 · VBR 11 · GLD 6 · XLE 6 · TQQQ 4 | 11.00 | -12.1 | 0.961 | 0.91 | 2.67 | -3.4 | -3.9 | +7.4 | -8.6 | 7.9/0.66 |
| Sweet spot | ~12% | **S12+** | KMLM 35 · VBR 18 · TYD 12 · GLD 11 · XLV 9 · IEI 9 · TQQQ 5 · XLE 1 | 11.90 | -13.7 | 0.957 | 0.87 | 3.38 | -3.2 | +2.8 | +4.1 | -6.8 | 9.1/0.73 |
| Sweet spot | ~12.5% | **S12.5** | KMLM 35 · TYD 18 · XLV 17 · VBR 14 · GLD 8 · TQQQ 5 · XLE 2 · XLP 1 | 12.49 | -15.4 | 0.952 | 0.81 | 3.70 | -2.5 | +1.7 | +4.4 | -8.1 | 9.0/0.69 |
| Sweet spot+ | ~13% | **S13** | KMLM 35 · GLD 19 · TYD 16 · XLP 8 · TQQQ 8 · VBR 8 · XLE 5 · SPMO 1 | 13.00 | -17.8 | 0.931 | 0.73 | 4.30 | -6.5 | +2.4 | -3.9 | -8.2 | 11.4/0.85 |
| Sweet spot+ | ~13.5% | **S13.5** | KMLM 35 · GLD 24 · TYD 18 · TQQQ 10 · XLE 9 · VBR 2 · REIT 1 · XLP 1 | 13.49 | -19.4 | 0.899 | 0.70 | 4.89 | -8.1 | +2.9 | -7.7 | -9.0 | 12.7/0.88 |
| Growth | ~14% | **E14** | TYD 30 · VBR 20 · KMLM 17 · XLE 12 · TQQQ 8 · GLD 6 · XLV 4 · REIT 3 | 14.01 | -21.1 | 0.899 | 0.66 | 4.51 | -9.2 | -10.7 | -0.0 | -16.0 | 9.8/0.61 |
| Growth | ~15% | **E15** | TYD 31 · VBR 22 · XLE 15 · KMLM 13 · TQQQ 10 · REIT 7 · UGL 2 | 14.99 | -25.8 | 0.860 | 0.58 | 5.65 | -11.8 | -14.4 | -6.1 | -18.6 | 10.7/0.59 |
| Aggressive | ~16.5% | **M25** | TYD 35 · VBR 24 · TQQQ 14 · KMLM 13 · XLE 9 · GLD 3 · REIT 1 · QLD 1 | 16.52 | -24.9 | 0.858 | 0.66 | 7.16 | -19.6 | -21.1 | -17.5 | -21.7 | 11.7/0.61 |
| Aggressive | ~17.5% | **M30** | TYD 30 · VBR 27 · TQQQ 16 · XLE 10 · KMLM 8 · TMF 4 · GDE 3 · REIT 2 | 17.43 | -30.0 | 0.830 | 0.58 | 8.65 | -23.3 | -26.1 | -24.4 | -25.0 | 12.4/0.59 |
| Aggressive+ | ~18.3% | **M35** | TYD 34 · VBR 31 · TQQQ 19 · XLE 8 · KMLM 6 · TMF 2 | 18.31 | -35.0 | 0.814 | 0.52 | 10.23 | -27.1 | -30.0 | -29.9 | -26.7 | 12.9/0.58 |
| Speculative | ~20% | **E20** | VBR 35 · TQQQ 24 · TYD 23 · TMF 10 · XLE 6 · KMLM 2 | 19.99 | -47.7 | 0.781 | 0.42 | 13.99 | -35.0 | -38.2 | -43.9 | -32.3 | 14.1/0.57 |

## Why each pick
- **~6–7% Safe-Now** — Highest Sharpe of everything (1.05); worst analog −2.7%; +15.6% in 2000–02. Weak recent decade.
- **~8% C1-Now** — Best fit for today: +8.3% in 2022, worst forward scenario only −1.1%, worst year −0.8%. E8 has the smaller MDD (−5.7%).
- **~9% E9** — Historically safest at 9%; bond-revolt scenario −4.8%. (No today-tuned version at 9%.)
- **~10% E10** — Market-like return with −10% MDD. Bond-revolt scenario −7.2% (leans on Treasuries).
- **~11% E11** — E11 has lower Ulcer/MDD; S12+ (11.9%) is much sturdier for today (2022 +2.8 vs −3.9, worst analog −7.7 vs −9.4).
- **~12% S12+** — Safest at 12% by history; S12-F5 is the today-hedged twin (+8.5% in 2022, every forward scenario ≥ −5%).
- **~12.5% S12.5** — Best Sharpe in the range (0.952); 2022 +1.7%, worst analog −8%. AI exposure ≤ 15%.
- **~13% S13** — Today-tuned: worst analog −7.9% vs −14.4% for E13. Cost: −3.9% in a 2000-style tech bust (TQQQ 8%).
- **~13.5% S13.5** — Best recent decade in the range (12.7%/0.88). −7.7% in a tech bust (AI exposure ~30%).
- **~14% E14** — −21% MDD, 5 negative years, 2022 −10.7%. No today-tuned version; bond revolt −16%.
- **~15% E15** — −26% MDD, worst year −11.8%; leveraged Treasuries + TQQQ 10%. Bond revolt −18.6%.
- **~16.5% M25** — Most return for a −25% drawdown cap (beats E16: −32% MDD). Worst year −19.6%.
- **~17.5% M30** — −30% MDD cap; worst year −23%.
- **~18.3% M35** — −35% MDD cap; 2022 −30%; leveraged Nasdaq 19%.
- **~20% E20** — Half-crash territory: −48% MDD, worst year −35%. Not recommended.

## Alternatives worth knowing
| Bracket | Alternative | Allocation | CAGR | Max DD | Sharpe | Ulcer | 2022 | Worst forward |
|---|---|---|---|---|---|---|---|---|
| ~6–7% | E7 | SHY 32 · IEI 26 · UUP 12 · VOE 9 · KMLM 7 · XLV 7 · GLD 5 · TQQQ 2 | 7.13 | -4.8 | 0.993 | 1.10 | -3.0 | -3.3 |
| ~8% | E8 | SHY 34 · IEI 33 · XLV 11 · KMLM 10 · XLE 4 · XLY 3 · TQQQ 3 · GLD 2 | 8.08 | -5.7 | 0.977 | 1.41 | -3.2 | -3.8 |
| ~11% | S12+ | KMLM 35 · VBR 18 · TYD 12 · GLD 11 · XLV 9 · IEI 9 · TQQQ 5 · XLE 1 | 11.90 | -13.7 | 0.957 | 3.38 | +2.8 | -6.8 |
| ~12% | S12-F5 | KMLM 35 · GLD 19 · XLV 15 · TYD 11 · XLE 9 · TQQQ 5 · IWC 4 · SHY 2 | 11.90 | -16.0 | 0.917 | 3.81 | +8.5 | -5.0 |
| ~13% | E13 | VBR 21 · TYD 20 · KMLM 19 · XLV 19 · GLD 9 · TQQQ 5 · XLE 5 · ZROZ 2 | 12.99 | -17.0 | 0.924 | 3.67 | -7.9 | -12.5 |
| ~13.5% | E13.5 | TYD 25 · KMLM 19 · VBR 18 · GLD 10 · XLV 10 · TQQQ 7 · XLE 7 · REIT 4 | 13.50 | -18.7 | 0.920 | 4.07 | -9.9 | -14.2 |
| ~16.5% | E16 | TYD 35 · XLE 19 · REIT 16 · TQQQ 13 · VBR 11 · KMLM 5 · UGL 1 | 16.00 | -32.3 | 0.817 | 7.09 | -21.6 | -22.7 |
| ~20% | M50 | VBR 32 · TYD 29 · TQQQ 26 · TMF 8 · XLE 5 | 20.37 | -49.9 | 0.772 | 15.00 | -42.1 | -33.9 |

## Reading the trade-off
- Up to ~12% CAGR, safety is cheap: Sharpe stays ≈ 0.92–1.05 and max drawdown grows ~1.5–2 pts per extra 1% CAGR.
- 12–13.5% is the knee: the today-tuned S portfolios keep every analog ≥ −8% and are positive in 2022.
- Above ~14%, return comes from leverage (3× Treasuries + 3× Nasdaq): each extra 1% CAGR costs ~4–6 pts of
  max drawdown, 2022 becomes the worst year, and 2018–26 Sharpe drops to ~0.6.
- 9–11% and 14–15% only have historically-optimised (E) versions; they are more exposed to a bond revolt.
- Since 2000, realised CAGRs are roughly 2–2.5 pts below the full-period figures (1988–99 was exceptionally strong).
- Leveraged ETFs and KMLM are simulated before inception; history was used to choose these. Not financial advice.

## Beyond E20 — the ceiling (testfol-verified)
| Portfolio | Allocation | CAGR | Max DD | Sharpe | Ulcer | Worst yr |
|---|---|---|---|---|---|---|
| E21 | TQQQ28 VBR28 TYD24 TMF11 XLE7 KMLM2 | 20.99 | −54.7 | 0.773 | 16.1 | −38.0 |
| E22 | TQQQ32 TYD21 VBR17 TMF15 XLE12 REIT3 | 21.99 | −61.9 | 0.762 | 18.6 | −40.0 |
| E23 | TQQQ35 TMF25 XLE18 VBR14 TYD8 | 23.00 | −69.0 | 0.754 | 21.4 | −39.0 |
| E24 | TQQQ35 TMF29 XLE28 TECL6 VBR1 UPRO1 | 23.99 | −78.5 | 0.733 | 27.0 | −42.3 |
| **Ceiling** | TQQQ35 TECL22 TMF22 XLE21 | **24.81** | −89.8 | 0.680 | 39.5 | −53.0 |
| TQQQ alone | TQQQ100 | 14.58 | −99.98 | 0.524 | 80.4 | −91.9 |
| QQQ alone | QQQ100 | 14.93 | −83.0 | 0.555 | 36.8 | −41.7 |
| VTI alone | VTI100 | 11.55 | −55.4 | 0.539 | 13.5 | −37.0 |

- ~24.8% CAGR is the physical ceiling under the rules (35% cap, ≤ 8 holdings, yearly rebalance), with or
  without the decade floor. More leverage *lowers* return (volatility drag): TQQQ alone earns only 14.6%.
- The ceiling works only by rebalancing between uncorrelated 3× sleeves (Nasdaq, tech, long Treasuries)
  plus energy — and still loses 77–83% in a 2000–02 tech bust and ~46% in 2022.
