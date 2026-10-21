# Improving the printer passively: overnight queue and log (started 2026-10-21)

**Goal:** raise the retiree-case printer's performance without market timing. Changes can be to costs, taxes, fund choice,
settings, structure or credit.
- **Setting:** the retiree's taxes (not working), a taxable account, reported at $50k and per $100k.
- **Judged on:** PRINT, RELIABILITY and BREAK RISK.
- **Harness:** `printer/improve.py` (`IDEA=<name> THROTTLE=1 python3 printer/improve.py --accept`).
- **Two tracks**, kept in `results/improve_best.json`: **simple** (M1, no credit) and **credit** (with the box-spread
  loan from `CREDIT.md`).

**Accepted only if, on 2,000 fresh histories,** in every case (base, trend −2%/yr, trend −4%/yr, 2000–2026 era,
3-month blocks):
- break risk is no worse than the current best, and
- the robust CE is ≥ 0.5% higher, and
- the first-decade bad-history print is not lower.

`printer/regress.py check` must say *identical* before every commit.

## Current best
| Track | Printer | Robust CE ($50k / $100k) | Since |
|---|---|---|---|
| simple | MP-2: DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · GLD 8 · TQQQ 2; base 5.75%, skim > 140%, 48-month bucket, guardrail 70% → 65% | (first run) | start |
| credit | MP-2 + $10k box-spread loan (1.2×), base 5.25% | (first run) | `CREDIT.md` |

## Queue (passive ideas, roughly by value ÷ effort)
1. **cheap_gold:** GLD (0.40%) → GLDM (0.10%) or IAUM (0.09%). Same gold, same collectible tax.
2. **bucket_tax:** hold the cash bucket in a Treasury fund (no California tax), or in BOXX (box-spread ETF, taxed as
   long-term gains, which is 0% federal for the retiree).
3. **settings:** re-tune around the current best: skim threshold up to 300% (the Atlas winners sat at the 200% edge),
   bucket 24–96 months, guardrail levels, base ±0.25.
4. **stacked funds:** swap parts of VBR/GDE/DBMF for return-stacked funds (RSSB, NTSX in local data; RSST/RSBT need a
   backfill from their parts).
5. **tax-loss harvesting:** swap to a near-twin fund when a holding is ≥ 10% below cost (VBR ↔ a similar small-value
   fund, TQQQ ↔ QLD). Losses offset gains and up to $3k/yr of ordinary income.
6. **credit combo:** box-spread boost plus a run line, with separate loan tracking.
7. **distributions as pay:** take fund distributions in cash as part of the monthly print instead of reinvesting and
   then selling.
8. **glidepath by age:** shift the engine slowly with age (passive, calendar-based).
9. **TIPS / annuity floor:** research first. Today's real yields are high (10-year TIPS 2.88%), so a ladder or annuity
   could carry part of the base print.

## Log
