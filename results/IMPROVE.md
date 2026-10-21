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

**Seeds:** every idea uses the same search (601) and fresh (701) histories, so ideas are compared like for like. Because
the fresh set is reused across many ideas, the final best printers get a last **confirmation on brand-new histories**
(new seeds, 4,000 paths) against where the night started.

## Overnight result (confirmed 2026-10-21 01:46 on 4,000 brand-new histories per case + the actual 40-year windows)
Retiree case: the retiree's taxes, taxable account; $/month after tax in today's dollars.

| | **Simple (M1, no credit): MP-2 → MP-2.1** | **Credit (IBKR/Schwab box loan)** |
|---|---|---|
| What changed | GLD → **IAUM**; cash bucket in **BOXX**; guardrail cuts the base to **60%** (was 65%); safety valve **4×** (was 2×) | the same IAUM and BOXX; loan **$12.5k (1.25×)** (was $10k); rebalance band **10 points**; valve **3×**; base restored above **80%**; **bucket pays the loan down** |
| Robust CE, $50k (per $100k) | $264 → **$268** (+1.7%), $528 → $537 | $287 → **$297** (+3.6%), $574 → $595 |
| Base paycheck at $50k | $240 (unchanged) | $219 (unchanged) |
| First 10 years, typical | $249 → $251 | $285 → **$300** |
| 40-year average, typical / bad history | $416 → $423 / $270 → $276 | $499 → **$523** / $347 → $368 |
| Base never cut · ends below start · dips < 70% · runs dry | 86→87% · 9→8% · 19→18% · 0.2→0.1% | 91→92% · 6→5% · 15→13% · 0.1→0.1% |
| Trend funds −4%/yr: 40-year typical / runs dry | $315 → $322 / 2.7% → 1.4% | $386 → $415 / 0.8% → 0.6% |
| Actual 40-year windows (1972–86 starts), 40-year typical | $457 → $483 | $539 → $593 |
| Margin calls (worst case) | — | ≤ 0.4% (0.7% with a box premium 0.6 pts wider) |

Break risk is no worse than at the start in **every** case on both tracks. On the actual 2000–2026 path
(`printer/replay.py MP-2.1`), MP-2.1 spent 2.06× its start (MP-2: 1.88×) and ended at 1.93× (1.83×).

**What the retiree does differently (simple track):**
1. Buy IAUM instead of GLD.
2. Keep the cash bucket in BOXX. Check that M1 lists it by adding it to the pie before funding.
3. Run the operator with `--printer MP-2.1`.

**What did not help:**
- different settings beyond these;
- glidepaths;
- income rules;
- stock/bond stacked funds;
- RSST (only with an optimistic proxy);
- calmer engines with more leverage;
- more GDE;
- a run line on top of the boost;
- tax-loss harvesting (too small for its manual work);
- weight hill-climbs (they overfit).

MP-2's fund weights are robust; the gains came from **cost, tax and rule settings**.

**Optional dials** (trade-offs, not free gains; your call):
- **Front-load the credit printer's base:** 5.50% for 15 years, then 5.00%. The retiree's guaranteed paycheck rises from $219 to
  **$229/month** at $50k for the first 15 years.
  - Break risk is no worse in every case, and robust CE is +0.4% (just under the bar).
  - 5.75% for 10 years, then 5.00%, gives $239, but the base-never-cut rate slips 2 points in one case.
- **Front-load the simple printer's base:** 6.00% for 10 years, then 5.50%. The guaranteed paycheck goes $240 → $250
  for 10 years, then $229 instead of $240 after that (robust CE −0.8%, break risk equal).
- **Skip the inflation raise after a losing year:** lower break risk (ends below start 8% → 5%), but about $7/month
  less in a bad first decade.

## Current best
| Track | Printer | Robust CE ($50k / $100k) | Since |
|---|---|---|---|
| simple | MP-2 with **IAUM** for GLD, the **cash bucket in BOXX**, the guardrail cutting to **60%** (was 65%), and the safety valve at **4×** (was 2×): DBMF 27 · VBR 27 · GDE 21 · KMLM 15 · IAUM 8 · TQQQ 2; base 5.75%, skim > 140%, 48-month bucket, guardrail below 70% → base × 0.60, restored above 90% | (see confirmation) | batch 7 |
| credit | the same engine with a **$12.5k box-spread loan (1.25×)**, base 5.25%, **rebalance band 10 points**, **safety valve 3×**, base restored above **80%** of the inflation-adjusted start (was 90%), and the **cash bucket paying the loan down** instead of sitting in cash | $296 / $592 (+3.5% vs start, fresh seed 701) | batch 5 |

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

### Batch 1 (2026-10-21, 00:05–00:11)
Fresh-history numbers at $50k; robust CE is relative to the reference.
- **cheap_gold: ACCEPTED on both tracks.** GLD → IAUM gives robust CE +0.3%, a 40-year typical of $416 vs $414,
  and break risk equal or lower. GLDM is the same (0.10% vs 0.09%). The gold and the collectible tax are unchanged.
- **bucket_tax: ACCEPTED on both tracks.** Holding the cash bucket in BOXX gives +0.1%, a 40-year typical of $417 vs
  $416, and ending below the start 8% vs 9%. A Treasury fund helps less, because the retiree's federal ordinary rate (10%) is
  above the retiree's California rate (2%).
  - **Caveat:** BOXX's treatment (box-spread gains instead of interest) is legal but untested by the IRS. Tax Notes
    flagged a possible challenge. If that ever happens, a Treasury fund (SGOV, or a Treasury money fund) is the
    fallback.

### Batch 2 (00:11–00:27): nothing accepted
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

### Batch 3 (00:27–00:50): one acceptance (credit track)
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
  - **Simple track: dropping the safety valve, or loosening it to 3–4×, gave +0.4–0.5%** with break risk equal,
    just under the bar. Same result in settings, settings2 and settings3, but on the same two history sets (every idea
    shares the search seed 601 and fresh seed 701), so these are not independent confirmations.
    - With TQQQ at 2% the valve rarely acts. It is worth adopting as a *simplification* (one rule fewer) if you want.
- **rsst** (RSST for VBR + DBMF, VTI + DBMF proxy): **REJECTED.** The optimistic proxy passed (+1.6% simple, +0.7%
  credit), but the pessimistic twin (3%/yr extra cost) fails on both tracks (−0.5% / −0.9%, break risk worse).
  - Over RSST's live years the proxy ran ~5%/yr above the real fund, so the gain depends on RSST's own trend sleeve
    matching DBMF.
  - `improve.py` now refuses proxy-based changes whose pessimistic twin fails. The harness's automatic acceptance was
    reverted by hand.

### Batch 4 (00:50–00:56): nothing accepted
- **lever_engines** (box loan on calmer engines: CH-12, CH-11.5, Gold-Stack 12, 3-fund VBR 35 / KMLM 35 / IAUM 30,
  at 1.2–1.5×):
  - At 1.2–1.35× all are worse than MP-2 at 1.2× (−2% to −13%).
  - At 1.5× some score higher (3-fund +1.3% to +2.4%, CH-12 +1.5–1.8%), but every one fails break risk in a stress
    case. MP-2 at 1.2× stays the best levered printer.
- **gde_stack** (more GDE for the same VBR + gold exposure): −1.7% to +0.3%, never safe. GDE's stocks are the
  S&P 500, so the swap gives up VBR's small-value tilt.

### Batch 5 (00:56–01:16): two acceptances (credit track)
- **bucket_offset: ACCEPTED (credit, +0.2%).** With a box loan, the cash bucket pays the loan down instead of sitting
  in BOXX. That avoids paying T-bill + 0.6% to hold cash earning T-bill − 0.2%. Bonus draws then re-borrow.
- **settings3: ACCEPTED (credit) — leverage 1.25× + rebalance band 10 points.**
  - Fresh histories: +2.0%, $296 vs $290 at $50k. First decade $297 vs $287. 40-year typical $524 vs $509.
  - Break risk equal or better (ends below start 4%, dips 15%, margin calls ≤ 1%).
  - Leverage 1.25× alone gives +1.8%. In batch 2, 1.3× failed break risk. The wider band means fewer re-levering
    trades.
  - The loan is $12.5k on $50k: one 125-point SPX box (strikes come in 5-point steps).
  - Simple track: dropping the valve gives +0.4–0.5% again (same history sets as before).
- **climb** (30-generation GPU hill-climb on the weights, guard rails as `search.py`): **no change.** Every climbed
  engine looked better on the climb's own 256 histories but was 2–3.5% worse on the harness's 1,000. That is
  in-sample overfit, caught as designed. MP-2's weights are robust.

### Batch 6 (01:16–01:28): one acceptance (simple track)
- **tlh** (tax-loss harvesting into near-twins): "accepted" at +0.1% simple / +0.0% credit under the old any-gain rule.
  That is about $0.30/month at $50k for recurring manual swaps, and swaps between gold trusts carry wash-sale
  uncertainty.
  - **Removed by hand.** Changes that add recurring manual work now need ≥ 0.25% (`OPS` in `improve.py`).
- **settings_local** (one step each way on every setting):
  - **Simple: ACCEPTED, the guardrail cuts the base to 60% instead of 65%** (+0.8% on fresh histories). A deeper cut
    in a deep slump protects the account. The first-decade bad-history print is unchanged at $240.
    - (Run with harvesting in the reference; harvesting is worth ~0.1%, and the final confirmation tests the exact
      final spec without it.)
  - **Credit: no change.** The 1.25× printer is at a local optimum on every setting.

### Batch 7 (01:28–01:42): one acceptance (simple track)
- **settings_local, simple, second pass: ACCEPTED, safety valve 4×** (+0.5% on fresh histories). Every earlier pass
  showed it just under the bar; with the 60% cut it crosses it.
  - In practice the immediate rebalance now fires only if a fund reaches 4× its target (TQQQ at 8%, IAUM at 32%).
    The yearly drift rule still applies.
- **climb, bigger** (512 histories, new seed 911, 20 generations): **no change on either track.** MP-2's weights are
  robust.

### Batch 8 (01:42–01:48): converged and confirmed
- **settings_local, simple, third pass: no change.** Both tracks are at a local optimum on every setting.
- **Confirmation on brand-new histories:** see the table at the top. Both tracks keep break risk no worse in every
  case.
  - Credit track with a box premium 0.6 points wider than assumed: still better than the start (CE $307 → $319 base,
    $248 → $258 with trend −4%/yr; margin calls 0.7%).
- `operate.py` now has **MP-2.1**. The safety-valve line now shows the printer's own valve, not a fixed "2x".
  `replay.py MP-2.1` reproduces the simulator within 1.9%.

### Batch 9 (01:52–02:10): front-loaded base, no acceptance (dials recorded above)
- **Simple:** every front-load lowers robust CE (−0.8% to −2.1%), but it raises the first-decade floor. Best safe
  version: 6.00% for 10 years, then 5.50%.
- **Credit:** 5.50% for 15 years, then 5.00%, is safe at +0.4%, with the floor $219 → $229 for 15 years. 5.75% for 10
  years, then 5.00%, is +0.7% with the floor $239, but the base-never-cut rate is 2 points lower in a stress case.

## Where this leaves things (stopping the overnight loop)
- **Settings:** both tracks are at a local optimum on every setting (three passes).
- **Fund weights:** robust (hill-climbs overfit).
- **Structure:** stacked funds, glidepaths, calmer levered engines, run line on top of the boost, and harvesting all
  fail or are too small.
- **Next, needing a decision or new data:**
  1. Pick the dials above.
  2. A dedicated engine search with the box loan (long GPU run; the laptop's heat limits it).
  3. A live-fund check of RSST's trend sleeve as more history arrives.
  4. Teach the operator the box-loan mechanics for the credit track.
