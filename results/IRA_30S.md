# Best IRA portfolio for our 30s (2026-10-18)

The couple is 30 with ~$8k in IRAs, adding $15k/yr ($7,500 each), retiring at 65. Inside an IRA there is no tax drag.
`printer/accumulate.py`: GPU search on reshuffled 1972–2026 histories. Contributions go to underweight funds first.
Rebalance when a fund is > 6 points off target (at most yearly), plus the 2× safety valve.

- **Score:** certainty-equivalent real wealth at 65 (risk aversion 3), averaged over the base case, trend funds −2%/yr
  and gold −3%/yr.
- **One search per drawdown limit:** the 90th-percentile drop lived through capped at 30%, 40%, 50% or 60%.
- **No-wipeout guard:** the worst single day of 1972–2026, including Oct 1987, must be no worse than −25%. Also:
  leveraged notional ≤ 200%, at most 9 funds, ≤ 50% each.
- **Validation:** daily on 2,000 fresh histories, plus 7 stress cases: trend −2%/−4%, gold −3%/−5%, leveraged funds
  costing 1%/yr more per unit of leverage, 3-month blocks, and recent era only. Engines also checked on testfol.io.

## Lineup (today's dollars)
| Portfolio | Engine | Robust CE @65 | Median @65 | Bad (p10) @65 | Median @55 | $1.75M by 55 | Drop lived (median / 1 in 10) | >50% drop | testfol 2000–26 |
|---|---|---|---|---|---|---|---|---|---|
| IRA Steady 30 | VBR 23 · KMLM 22 · GDE 20 · DBMF 19 · TQQQ 8 · GLD 4 · TLT 2 · TMF 2 | $3.02M | $5.0M | $2.36M | $1.75M | 50% | 26% / 33% | 0% | 12.2% / −23.0% |
| **IRA Accelerator 40** | VBR 29 · DBMF 24 · KMLM 17 · TQQQ 13 · GDE 10 · UGL 7 | **$3.2M** | **$6.1M** | **$2.49M** | $2.01M | 60% | 32% / 41% | 1% | 13.0% / −30.5% |
| IRA-50 | DBMF 22 · TQQQ 21 · VBR 19 · KMLM 17 · GLD 7 · GDE 6 · SPMO 6 · TMF 2 | $3.11M | $8.2M | $2.43M | $2.38M | 66% | 41% / 52% | 14% | 14.5% / −48.6% |
| IRA Max 60 | VBR 33 · KMLM 25 · GDE 18 · TQQQ 15 · XLE 6 · … | $3.30M | $7.8M | $2.53M | $2.30M | 66% | 42% / 53% | 14% | 17.7% / −45.1% (from 1988) |
| MP-2 engine (the retiree's printer) | DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · GLD 8 · TQQQ 2 | $2.67M | $3.8M | $2.16M | $1.48M | 33% | 24% / 28% | 0% | 11.0% / −22.1% |
| S13.5 | KMLM 35 · GLD 24 · TYD 18 · TQQQ 10 · XLE 9 · … | $2.24M | $3.5M | $1.75M | $1.35M | 29% | 24% / 29% | 0% | 12.8% / −19.4% (1988) |
| VTI (100% US stocks) | VTI 100 | $1.38M | $2.3M | $0.92M | $1.06M | 21% | 48% / 61% | 42% | 8.5% / −55.4% |
| 60/40 | VTI 60 · BND 40 | $1.29M | $1.6M | $0.89M | $0.84M | 3% | 30% / 38% | 1% | 7.1% / −34.0% |
| E24 (old "ceiling") | TQQQ 35 · TMF 29 · XLE 28 · … | $1.11M | $8.0M | $0.97M | $2.41M | 59% | 75% / 89% | 100% | 24.0% / −78.6% (1988) |
| HFEA | UPRO 55 · TMF 45 | $0.63M | $2.7M | $0.45M | $1.16M | 38% | 77% / 91% | 100% | 16.2% / −69.7% (1988) |

**Pick: IRA Accelerator 40.**
- It is within about 3% of the best score, but its 1-in-10 drop is 41% versus 53% for the 60% portfolios, and the
  chance of a drop over 50% is 1% versus 14%.
- It has the best bad case of the lineup ($2.49M p10).
- It reaches the $1.75M nest egg by 55 in 60% of histories (VTI: 21%, 60/40: 3%).
- If the broker can't hold UGL (a commodity pool), use **VBR 27 · DBMF 23 · KMLM 16 · TQQQ 13 · GDE 10 · GLD 11**:
  CE $3.75M base, drop p90 39%.

More leverage stops paying past about a 40% drop tolerance. E24 and HFEA have the biggest medians, but nearly certain
70–90% drops make their bad cases the worst of all, below plain VTI.
Plan: hold the Accelerator until about 50, then shift gradually into the money printer (MP-2 / CH-12) by retirement.
That glide has not been separately simulated.
*Research model on historical and reconstructed data; not financial advice.*
