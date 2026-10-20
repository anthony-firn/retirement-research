# Crisis-Hedged 12 — portfolio, rebalancing and living-off research for a 60-year-old retiree (2026-10-18)

Portfolio research from the retiree case study. The household's own inputs and plan notes live in the gitignored
`private/` folder; "plan odds" columns come from a private example plan that is not published.

## Portfolio re-optimised for a 60-year-old retiree (2026-10-18) — Crisis-Hedged 12 (true 12%) and Crisis-Hedged 11.5 (calmer)
GPU search (`lab/ex_optimize.py`) on 1972–2026 data incl. the 1970s, requiring CAGR ≥ 12% over 1972–2026 **and** over
1988–2026 (the lineup's yardstick), beating S12+ split on Sharpe/Calmar/Ulcer/MDD, with guard rails for today
(2022-type rate shock, AI exposure ≤ 15%, bond-revolt/stagflation scenarios, trend-following ≤ 40%). Then the retiree's plan and
early-drop odds (`lab/ex_stage2.py`), a trend-following haircut test (`lab/ex_mf_robust.py`) and testfol.io.

**Crisis-Hedged 12: DBMF 24 · KMLM 16 · GLD 15 · VBR 14 · XLV 13 · TYD 10 · TQQQ 5 · UUP 3**
**Crisis-Hedged 11.5: DBMF 23 · KMLM 17 · VBR 17 · IEI 15 · GLD 12 · TYD 6 · XLV 5 · TQQQ 5**
| | S12+ split | **Crisis-Hedged 12** | Crisis-Hedged 11.5 |
|---|---|---|---|
| CAGR 1972–2026 / 1988–2026 | 12.8% / 11.9% | 12.9% / 12.0% | 12.6% / 11.5% |
| testfol.io 2000–2026 CAGR / worst drop / Sharpe | 9.59% / −13.5% / 0.880 | **9.78% / −13.5% / 0.887** | 9.26% / −12.8% / 0.884 |
| Worst drop 1972–2026 / worst real year | −21.1% / −10.6% | −21.0% / −8.0% | −19.2% / −8.6% |
| Chance of a >20% drop in the first 5 years | 12% | 12% | **2%** |
| 1973–74 stagflation / 2022 rate shock | −1.5% / 0.0% | +4.6% / +3.1% | +6.1% / +3.4% |
| Bond-revolt scenario (10y → 6.5%, stocks −15%) | −7.2% | −5.5% | −4.9% |
| Plan odds (three example cases) | 99 / 94 / 94% | 99 / 96 / 96% | 99 / 96 / 95% |
| Plan odds avg if trend-following earns 2% / 4% less a year / only T-bills | 91 / 85 / 77% | 93 / 85 / 76% | 91 / 82 / 71% |
Crisis-Hedged 12 is the best portfolio at a true 12%; Crisis-Hedged 11.5 trades ~0.4%/yr for far lower odds of an early 20% drop but leans
more on trend-following. The earlier H12 / H12-8 looked like 12% only because a proxy bug (fixed) used reconstructed
KMLM/TQQQ/QQQ/BND/GSG returns after those funds' real data starts; on real data they are ~10% portfolios.
Logs: `results/ex_optimize88.log`, `results/ex_stage2_88_*.log`, `results/ex_mf_robust2.log`, `results/verify_ex_final2.log`.

### Gold-Stack 12 — 12% on testfol.io's own 2000–2026 window (2026-10-18)
testfol.io can only start DBMF portfolios in 2000 (dot-com peak), so Crisis-Hedged 12 shows 9.78% there (11.93% from 1988 in its
KMLM-only form). Searching for the safest portfolio with CAGR ≥ 12% on 1972+, 1988+ **and** 2000+ (moderate guard rails:
AI exposure ≤ 25%, scenarios ≥ −8%, 2022 ≥ −5%; full guard rails only reached −33% worst drop) gives
**Gold-Stack 12: GDE 25 · DBMF 23 · KMLM 17 · VBR 14 · GLD 12 · TQQQ 5 · TMF 4**.
| | Crisis-Hedged 12 | Gold-Stack 12 |
|---|---|---|
| testfol.io 2000–2026 CAGR / worst drop / Sharpe / Ulcer | 9.78% / −13.5% / 0.887 / 3.21 | **12.02%** / −19.6% / 0.834 / 5.13 |
| 1972–2026 CAGR / worst drop / worst real year | 12.9% / −21.0% / −8.0% | 14.4% / −26.9% / −14.3% |
| Dot-com 2000–02 / 2008 / Covid / 2022 | +4.0 / −1.1 / −11.7 / +3.1% | −11.6 / −9.1 / −16.5 / −1.3% |
| Chance of a >15% / >20% drop in the first 5 years | 29% / 12% | 70% / 28% |
| Plan odds (avg of 3 cases) / if trend-following = T-bills | 97% / 76% | 98% / 84% |
Gold exposure is ~34% (GDE = 90% S&P 500 + 90% gold futures; real fund since 2022, simulated before). Plan odds gain is
1 point; the price is 2–3× the odds of an early large drop. Logs: `results/ex_optimize00.log`, `results/ex_stage2_00.log`,
`results/ex_mf_robust3.log`, `results/verify_ch12T.log`.

### Rebalancing rule for Crisis-Hedged 12 (2026-10-18)
Tested 40+ rules on 1972–2026 (`lab/rebal_test.py`, `lab/rebal_plan.py`; logs `results/rebal_*.log`) and on testfol.io
(`results/verify_rebal_testfol.log`). Findings:
- **Calendar timing is luck.** Yearly rebalancing ranges 12.2–13.0% CAGR and 1–17% odds of a >20% drop within 5 years
  depending only on the month (January, used in the search, was one of the lucky months). Quarterly also varies by offset.
- **Rebalancing more than once a year, or on drift, cuts the early-drop risk** (5-year >20% odds 1–2% vs 3–17% yearly; worst
  drop 17–19% vs 19–24%) for about the same long-run return. Main reason: the 3x funds (TQQQ, TYD) can't balloon for a
  whole year before a crash.
- Never rebalancing costs ~1.8%/yr and doubles the worst drop.

**Rule (revised after the testfol.io check): rebalance once a year at year-end, plus a safety valve — rebalance early
if any holding reaches twice its target weight** (testfol.io: Yearly + 100% relative band; in practice TQQQ above 10%,
UUP above 6%). testfol.io's 2000–2026 data favours year-end yearly rebalancing (best Sharpe of all 12 months, 0.887; average
of the 12 months 0.836; quarterly 0.820), and the weights were tuned with that date. The safety valve fixes its one weak spot:
in 1987 TQQQ ballooned January→August and the October crash gave the portfolio's worst drop (−21%).
| | Yearly (year-end) | **Yearly + 2x safety valve** | Quarterly check, trade if >35% off |
|---|---|---|---|
| testfol.io 2000–2026 CAGR / worst drop / Sharpe | 9.78% / −13.5% / 0.887 | 9.59% / −13.5% / 0.878 | 9.45% / −14.7% / 0.820 (testfol checks bands daily) |
| 1972–2026 CAGR / worst drop / Sharpe | 12.90% / −21.0% / 0.860 | 12.71% / −18.1% / **0.869** | 12.93% / −18.9% / 0.866 |
| Odds of a >20% drop within 5 years | 10% | **1%** | 1% |
| The retiree's plan odds (avg of 3 cases) | 97% | 97% | 97% |
| Trades per year | 1 | 1.2 (4 early trades in 2000–2026) | 1.3 |
Use withdrawals and new money to trim overweight / fill underweight holdings first — fewer taxable sales.

## Living off Crisis-Hedged 12 — the equilibrium (2026-10-18)
`lab/equilibrium_gpu.py` (142 rebalancing rules × withdrawal rates × 1,000–2,000 reshuffled histories, GPU),
`lab/equilibrium_income.py`; logs `results/equilibrium_*.log`. Monthly withdrawals come from the most overweight funds first;
taxable account with the retiree's likely tax (~3% of realized gains), 0.05% trading cost.

**Rebalancing rule hardly matters once the retiree is withdrawing:** every reasonable rule sustains 5.14–5.27%/yr (90% of
histories keep the real value) and 7.36–7.49% (typical) — withdrawals do most of the rebalancing. Chosen for fewest
taxable trades: **rebalance when any fund is > 6 points off target, never sooner than 1 year after the last rebalance;
safety valve (any fund at 2× its target) any time** — about 0.4 rebalances a year, nearly all long-term gains.
(Not reproducible in testfol.io, which has no minimum-spacing setting; links use Yearly + 100% band.)

**Fixed inflation-adjusted income that keeps the real value, 40 years** (share of the starting value per year):
| | 90% of histories | 75% | 50% |
|---|---|---|---|
| Base case | 5.2% | 6.2% | 7.4% |
| Middle tax bracket | 4.5% | 5.5% | 6.6% |
| Trend funds earn 2%/yr less | 4.5% | 5.5% | 6.6% |
| Harsher reshuffle (3-month blocks) | 5.2% | 6.2% | 7.5% |
Spending down to $0 at 100 instead adds little safely: 5% runs out in 3% of histories, 5.5% in 8%, 6% in 14%.

**Skim plan (recommended): base income 4% of the starting value (inflation-adjusted) + each year-end skim anything
above 125% of the inflation-adjusted start into a cash "bonus bucket".** Average income over 40 years: 6.2% (bad
history, p10) / 9.2% (typical); the real value ends ≥ the start in 90% of histories; its low point (p10) is 74% of start.
Bonuses are lumpy (in a typical year only the base; 1 year in 4 pays ≥ 11.5%) — spend the bucket over ~3 years.
Per $100k: base $4,000/yr ($333/mo) + bonuses → average ~$6,200/yr bad case, ~$9,150/yr typical.

### Taxes in the equilibrium (2026-10-18) — `lab/equilibrium_tax.py`, `results/equilibrium_tax*.log`
Per-fund tax model in a taxable account: VBR/XLV qualified dividends (2.0% / 1.6%); KMLM, DBMF (2.5%), TYD (2%), TQQQ (1%)
ordinary-income distributions (KMLM paid ~2–2.5%/yr in 2022–24, mostly ordinary); GLD gains taxed as collectibles (ordinary
rate, no 0% bracket); UUP a commodity pool (K-1, marked to market yearly, 60/40); short-term vs long-term by holding time;
losses carried forward; California taxes everything as ordinary income. Income below is after tax (spendable).
| Tax situation | Fixed real income keeping real value: 90% / 75% / 50% | Skim plan 4% + above 125%: avg income p10 / median |
|---|---|---|
| IRA / Roth (no tax) | 5.3% / 6.3% / 7.6% | 6.5% / 9.5% |
| The retiree's, not working (fed 10% ordinary, 0% LTCG, CA ~2%) | 5.0% / 6.0% / 7.2% | 6.0% / 8.9% |
| The retiree's, working $40k (fed 12%, 0% LTCG, CA ~5%) | 4.8% / 5.8% / 7.0% | 5.6% / 8.5% |
| Middle bracket (22% / 15%, CA 9.3%) | 4.0% / 4.9% / 6.0% | 4.2% / 6.6% (4% base too high here) |
**Taxable-account variant: Crisis-Hedged 12 (no UUP)** — DBMF 25 · KMLM 16 · GLD 15 · VBR 15 · XLV 13 · TYD 11 · TQQQ 5:
the retiree's not-working case 5.1% / 6.1% / 7.4%, skim 6.1% / 9.1%; no K-1. In an IRA the original (with UUP) is fine.
Tax tips: Use GLDM/IAUM (0.09–0.10% fee) instead of GLD (0.40%) — same tax, lower cost.
