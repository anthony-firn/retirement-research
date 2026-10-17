# Case study: 60-year-old retiree, $50k–$300k (2026-10-17)

Research only — backtests on partly simulated history (testfol.io SIM tickers, 1988–2026). Not financial advice.
Script: `strategy/retiree_plan.py`; full table: `results/retiree_plan.log`.

## Portfolios considered
| Name | Allocation | CAGR | Max DD | 2022 | Notes |
|---|---|---|---|---|---|
| **Simple-7.5** | IEI 31 · SHY 31 · KMLM 18 · QQQ 10 · VOE 10 | 7.5% | −7.8% | −1.1% | 5 funds, no leverage; Sharpe 0.97 |
| **Simple-6.8** | IEI 34 · UUP 20 · KMLM 17 · VOE 17 · GLD 12 | 6.8% | −6.8% | +4.5% | 5 funds, no leverage; most inflation/war-resilient |
| Simple-6 | SHY 34 · IEI 25 · VOE 17 · KMLM 13 · UUP 11 | 6.2% | −5.6% | +1.3% | 5 funds, no leverage; lowest drawdown |
| Safe-Now / C1-Now | see LINEUP.md | 6.8% / 8.0% | −4.6% / −8.3% | −2.7% / +8.3% | 8 funds incl. 2% TQQQ |
(Simple-* found by GPU search: ≤ 5 ETFs, no leveraged/stacked funds, every analog episode ≥ −4%, 2022 ≥ −3%, AI ≤ 10%.)

## Withdrawals, inflation-adjusted, every historical start month (testfol data)
- All diversified portfolios survived **every** 20-year (227 starts) and 30-year (107 starts) window at 3%, 4% and 5%.
- Cash (T-bills) failed most 30-year windows at 4%+ (inflation).
- $300k, 4%/yr ($12k, inflation-indexed), 30 years: Simple-7.5 never fell below $280.7k real (median end $487k);
  Simple-6.8 lowest $235.6k (median $334k); C1-Now lowest $273.1k (median $567k).
- 30-year windows only start 1988–1996 (generally favourable starts); 20-year windows include 2000 and 2007 starts.

## Bigger levers than the portfolio
- **Emergency fund** (6–12 months of expenses) in savings/T-bills, outside the portfolio.
- **Health insurance from 60 to Medicare at 65** (marketplace/COBRA) — budget for it.
- **Withdrawal rate**: ≤ 4% kept real value roughly intact in all history; 5% survived but eroded the real balance.
- **Simplicity**: 5 funds, rebalance once a year. Daily switching/timing added no reliable value out of sample.
- A **fee-only fiduciary** (flat fee, no commissions) is worth an hour to check SS timing, taxes and the plan;
  be wary of high-fee annuities and unsolicited "advisers" (retirees are frequent scam targets).
