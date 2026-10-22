# Research history and where to inspect it

This is an index of the repository's recorded work. It is not a claim that every exploratory run was preserved or independently verified.
Historical figures and product rates in older reports describe the report date and need rechecking before use.

| Question | Implementation | Evidence and discussion |
| --- | --- | --- |
| Which diversified portfolios survive different decades? | `lab/beat*.py`, `lab/cv.py`, `lab/verify*.py` | `results/STRATEGY.md`, `results/LINEUP.md`, committed lab result JSON/logs |
| Can we reproduce portfolio backtests ourselves? | `engine/backtest.py`, `engine/sims.py`, `engine/validate.py` | `engine/README.md`, `results/engine_validation.log` |
| How can savings produce an after-tax monthly paycheck? | `printer/money_printer.py`, `printer/search.py`, `printer/validate.py` | `results/MONEY_PRINTER.md`, `results/PRINTER_SEARCH.md`, `results/printer_validate_table.md` |
| Does cheap credit help after taxes and forced-sale risk? | `printer/credit.py` | `results/CREDIT.md`, corresponding credit sweep JSON/logs |
| Which passive changes improve the income/risk trade-off? | `printer/improve.py` | `results/IMPROVE.md`, `results/improve/*.json`, `.log` and `.err` |
| Are apparent gains caused by unrealistic reconstructed funds? | `strategy/history70s.py`, `printer/recent_sharpe.py`, `printer/deflation_fix.py` | `results/FINDINGS.md`, rejected candidates and pessimistic proxy tests in `results/IMPROVE.md` |
| What happens from real market peaks? | `printer/bubble_starts.py`, `printer/backtest_real.py` | bubble-start and actual-history result files in `results/` |
| Does the operational tracker follow the simulator? | `printer/operate.py`, `printer/replay.py` | `results/PRINTER_OPERATOR.md`, replay output and limits in `results/PRINTER_FORGE.md` |
| How do saving, retirement age, Social Security, health costs and account taxes interact? | `printer/app/plans.py`, `printer/safe_base.py`, `planner/` | `results/safe_base.json`, `results/PRINTER_FORGE.md`; simplified assumptions are visible in the code |
| Can someone understand and operate this on a phone? | `printer/app/static/`, `mobile/` | browser checks, API tests, native build instructions; physical-device testing remains necessary |

## Reading the passive-improvement sequence

The 2026-10-21 log in `results/IMPROVE.md` records cheaper gold, bonus-bucket tax treatment, spending settings,
combined loans, stacked-fund proxies, glidepaths, harvest rules, changing allocations, additional trend exposure,
crash leverage, phase-in and real-asset ideas. Many were rejected or retained only as optional trade-offs.
Use the JSON metrics and reference specification from each run; do not reconstruct a conclusion solely from a summary paragraph.

`results/FINDINGS.md` gives the broader running record. `git log --oneline -- printer strategy lab results` shows changes to the
methods and conclusions. This preserves public research decisions without publishing raw household conversations.

## Known evidence gaps

- Seeds used repeatedly during development are no longer untouched validation seeds.
- New bootstrap paths are not new market regimes. Model risk, multiple testing and shared proxy errors remain.
- The legacy acceptance predicate permits small absolute risk regressions; read METHOD.md before repeating the phrase “no worse.”
- The latest selected settings still need prospective tracking and independent replication.
- Life expectancy estimates, healthcare assumptions, benefits and taxes need broader review and jurisdiction-specific modules.
- The data pipeline still depends on third-party historical caches and an undocumented external API in places.
