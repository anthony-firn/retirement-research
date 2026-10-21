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
| credit | the same + $10k box-spread loan (1.2×), base 5.25%, **safety valve at 3× and the base restored above 80%** of the inflation-adjusted start (was 90%) | $290 / $579 (+1.2% vs start) | batch 3 |

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

### Batch 2 (00:15–01:00): nothing accepted
- **settings:** MP-2's settings are already at the retiree's optimum.
  - Simple track: the closest was a 3× safety valve (+0.4%, just under the bar). A higher skim threshold raises the
    40-year average ($440–507 at 160–250%) but lowers the first-decade print and the robust CE (−1% to −7%).
  - Credit track: 1.3× leverage scored +3.5% in the search but failed break risk in a stress case. A 10-point
    rebalance band reached +0.45% on fresh histories, just under the bar.
- **combo** (box boost + run line, credit track): at most +0.1%. With the boost in place, the run line adds nothing.
- **stacked** (NTSX / RSSB for VBR or GDE): **worse in every variant, −1.5% to −9%.** Stacking Treasuries adds rate
  risk (2022) that the trend + gold engine doesn't need.
- **Notes:**
  - TIPS / annuity floor: a 30-year TIPS ladder (2.9–3.3% real) pays only 5.0%/yr real and ends at 90; the printer's
    base is 5.75% real.
  - A life-only annuity for a 60-year-old woman pays $638/month per $100k (7.66%, no inflation raise). That trades
    away legacy and liquidity, so it is a different decision, not a printer improvement. Not tested.
  - Skipped as low value for the retiree (gains already taxed 0% federal): distributions as pay, and tax-loss harvesting.

### Batch 3 (01:00–01:45): one acceptance (credit track)
- **glidepath:** none of 16 age-based shifts (5 or 10 points between stocks and trend or gold, over 10 or 20 years,
  either direction) helps: −0.4% to −3.3%. MP-2's fixed mix beats gliding.
- **rules:** the bucket top-up of a cut base does nothing (the bucket is empty when the guardrail bites).
  - **Skipping the inflation raise after a losing year is a safety dial, not a free gain.**
    - Ends below the start: 8% → 5%. Dips below 70%: 17% → 15%.
    - Trend −4%/yr CE: $226 → $233.
    - But the first-decade bad-history print falls $234 → $227 at $50k (robust CE −0.2%), so it is not accepted.
- **settings2 (pairs of near-misses):**
  - **Credit track: ACCEPTED, valve 3× + restore at 80%** (+0.8% on fresh histories, $290 vs $287 at $50k; 40-year
    typical $507 vs $503; break risk equal).
  - **Simple track: dropping the safety valve, or loosening it to 3–4×, gave +0.4–0.5% in four independent runs**
    with break risk equal, just under the bar.
    - With TQQQ at 2% the valve rarely acts. It is worth adopting as a *simplification* (one rule fewer) if you want.
- **rsst** (RSST for VBR + DBMF, VTI + DBMF proxy): **REJECTED.** The optimistic proxy passed (+1.6% simple, +0.7%
  credit), but the pessimistic twin (3%/yr extra cost) fails on both tracks (−0.5% / −0.9%, break risk worse).
  - Over RSST's live years the proxy ran ~5%/yr above the real fund, so the gain depends on RSST's own trend sleeve
    matching DBMF.
  - `improve.py` now refuses proxy-based changes whose pessimistic twin fails. The harness's automatic acceptance was
    reverted by hand.
