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
| simple | MP-2 with **IAUM** for GLD and the **cash bucket in BOXX**: DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · IAUM 8 · TQQQ 2; base 5.75%, skim > 140%, 48-month bucket, guardrail 70% → 65% | $265 / $529 (+0.4% vs MP-2) | batch 1 |
| credit | the same + $10k box-spread loan (1.2×), base 5.25% | $287 / $575 (+0.4%) | batch 1 |

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

### Batch 1 (2026-10-21 00:05–00:15)
Fresh-history numbers at $50k; robust CE is relative to the reference.
- **cheap_gold: ACCEPTED on both tracks.** GLD → IAUM gives robust CE +0.3%, a 40-year typical of $416 vs $414,
  and break risk equal or lower. GLDM is the same (0.10% vs 0.09%). The gold and the collectible tax are unchanged.
- **bucket_tax: ACCEPTED on both tracks.** Holding the cash bucket in BOXX gives +0.1%, a 40-year typical of $417 vs
  $416, and ending below the start 8% vs 9%. A Treasury fund helps less, because the retiree's federal ordinary rate (10%) is
  above the retiree's California rate (2%).
  - **Caveat:** BOXX's treatment (box-spread gains instead of interest) is legal but untested by the IRS. Tax Notes
    flagged a possible challenge. If that ever happens, a Treasury fund (SGOV, or a Treasury money fund) is the
    fallback.
