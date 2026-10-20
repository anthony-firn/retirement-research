# Money Printer Forge and the Printer Atlas (2026-10-19)

**What it is.** The Forge is a character-creator page (`printer/ui/forge.html`, self-contained, opens offline). Four
plain-language sliders plus a complexity tier pick a ready-made money printer: fund mix, monthly paycheck, bonus rule and
safety brake. Below them is a Pareto-frontier explorer. Every pick is cached ahead of time in the Printer Atlas, so the
sliders respond instantly.

| Slider (left → right) | What it changes in the score |
|---|---|
| Paycheck or safety net | Weight on the stress case (trend funds earn 2%/yr less) goes from 20% to 80%. Run-dry, lose-value and paycheck-cut caps tighten. |
| Bonus years or same every month | Risk aversion over the income stream (CRRA γ 1.5 → 8), plus a penalty on jumpy years |
| Spend it or leave it | Value placed on what is left after 40 years (up to 0.012 of income per 1× start left, capped at 3×) |
| How much swing you can watch | Penalty on the bad-case (1 in 10) drop of the balance from its high (up to 0.10 per unit) |
| How many moving parts | Hard limits on each tier |

Tier limits:
- **Starter:** ≤ 3 funds, no leveraged funds.
- **Simple:** ≤ 4 funds, no leveraged funds.
- **Standard:** ≤ 5 funds, ≤ 5% leveraged.
- **Advanced:** ≤ 7 funds, ≤ 15% leveraged.
- **Expert:** ≤ 9 funds, ≤ 25% leveraged, K-1 funds allowed.

## How the Atlas was built
- **Search** (`printer/atlas.py search`). There are 7⁴ preference cells × 5 tiers = 12,005 cells per account type.
  - One shared GPU archive of evaluated printers (256 weekly-step 40-year histories, base case plus trend stress).
    Each cell adopts the archive member with its highest score.
  - Each generation mutates the current winners (512 kids, tier-preserving). There were 30 generations per account,
    about 16,000 printers each, using the usual guard rails: ≤ 35% per fund, trend ≤ 42%, AI exposure ≤ 25%, and
    forward scenarios ≥ −8.5%.
- **Validate** (`printer/atlas.py validate`). Each account's top 2 printers per cell (2,229 in total) were re-run on
  600 fresh histories for every account type. Cells were re-picked on the fresh stats, then smoothed: a cell takes a
  neighbour's printer when it is within 0.04% of start a year of its own best.
- **Results:**

  | Account | Distinct printers across cells | Pareto frontier |
  |---|---|---|
  | Roth | 271 | 1,357 |
  | Taxable, low income | 246 | 1,200 |
  | Taxable, middle income | 44 | 236 |

  The frontier uses 11 objectives, counting only printers that run dry in ≤ 2% of histories.
- **Build** (`printer/build_ui.py`) inlines everything into the page (1.4 MB).

## What the presets pick (per $100k, $/month after tax, today's $, fresh histories)
| Preset | Account | First 10 yrs | 40-yr average | Unlucky (1 in 10) | Base never cut | Bad-case drop | Left at 40 yrs | Engine |
|---|---|---|---|---|---|---|---|---|
| Max paycheck | Taxable, low | $542 | $874 | $501 | 68% | 47% | 1.8× | DBMF 23 · VBR 23 · KMLM 18 · GDE 17 · GLD 10 · TQQQ 5 · TMF 4 |
| Balanced | Taxable, low | $458 | $982 | $502 | 80% | 36% | 2.5× | VBR 24 · DBMF 23 · KMLM 19 · GDE 15 · GLD 10 · TQQQ 5 · TMF 4 |
| Sleep well | Taxable, low | $375 | $1,004 | $542 | 93% | 33% | 2.6× | DBMF 24 · VBR 24 · KMLM 18 · GDE 15 · GLD 10 · TQQQ 5 · TMF 4 |
| Keep it simple | Taxable, low | $437 | $437 | $417 | 85% | 35% | 6.5× | VBR 35 · KMLM 35 · GLD 30 (no bonus rule) |
| Balanced | Roth | $479 | $1,035 | $528 | 80% | 36% | 2.5× | same family as above |
| Balanced | Taxable, middle | $375 | $729 | $374 | 88% | 43% | 2.2× | DBMF 24 · VBR 24 · KMLM 18 · GDE 15 · GLD 10 · TQQQ 5 · TMF 4 |

## Findings
- **The engine barely changes across preferences.** The Starter tier uses one engine (VBR · KMLM · GLD) in 99–100% of
  cells. The Expert tier uses about 30 engines, but they are variations of one family: trend-following about 41%, plus
  small-cap value, GDE (stocks + gold) and gold. The sliders mostly move the **settings** instead: the base paycheck
  (4.25–6.75%), how high the bonus threshold sits, and the safety brake.
- **The search likes to bank bonuses.** Many winners only skim above 195–200% of the inflation-adjusted start. That was
  the edge of the allowed range, so it is worth widening next time. As a result the 40-year average is often twice the
  first-decade print. The page therefore leads with the first-10-years number and shows the 40-year average beside it.
- **A three-fund printer is competitive.** VBR 35 · KMLM 35 · GLD 30 with a flat 5.25% paycheck and no bonus prints a
  very steady $437 per $100k (99% of years within ±25%), with no leverage, and typically leaves a large legacy.
- **Middle-bracket taxes cost about 25–30% of the print** compared with the low-income taxable case.
- **The frontier is large because there are 11 objectives.** With that many measures, most printers are best at
  something. The brushable parallel-coordinates view is the way to narrow it: drag a range on the axes you care about.

## Caveats
- **Taxable, middle income has no dedicated search.** It re-scores the Roth and taxable-low candidates, because the
  laptop shut down twice during the long GPU runs (the logs show fan-controller ACPI errors). That is why it has only
  44 distinct printers. `python3 printer/atlas.py search` resumes, and `THROTTLE=0.75` idles the GPU between batches.
- **Same history caveats as every printer result.** The model reshuffles 1972–2026 history, much of it reconstructed
  before the funds existed (KMLM, DBMF, GDE). Tuning on 256 histories flatters the winners a little; the stats shown
  come from the fresh 600.
- **Research model, not financial advice.**

Rebuild: `python3 printer/atlas.py search && THROTTLE=0.75 python3 printer/atlas.py validate && python3 printer/build_ui.py`
