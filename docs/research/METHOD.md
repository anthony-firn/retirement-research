# Reproduce a result, then improve it

## Set up and check the inputs

Use Python 3.11 or 3.12 and a virtual environment. Install `requirements.txt`. Choose the appropriate PyTorch CPU/CUDA
distribution for your machine. Then run:

```bash
python3 tools/research_snapshot.py --output /tmp/retirement-inputs.json
CUDA_VISIBLE_DEVICES='' python3 -m unittest discover -s printer/app/tests -v
THROTTLE=1 python3 printer/regress.py check
```

The snapshot records public code/data hashes, versions, commit and missing generated inputs. Missing inputs are a blocker for
the simulator, not an invitation to substitute unrelated data. See DATA.md. Exact baseline equality is expected on the original
GPU path; different CPU reductions can differ in the last few decimal places. Report that difference rather than resaving the baseline.

## Write down the question before searching

Copy EXPERIMENT_TEMPLATE.md. Specify population, jurisdiction, horizon, tax profile, baseline, candidate family, costs,
objective and risk tolerances. Use generic example households. Keep a simple stock/bond baseline and the existing printer baseline.
Agree on the meaning of improvement before looking at the results.

## Re-run an existing passive idea without replacing historical artifacts

The runner creates a new directory, copies the current reference specification, records input hashes and captures stdout/stderr.
It does not promote a winner or change the app. A small run checks plumbing only:

```bash
CUDA_VISIBLE_DEVICES='' python3 tools/run_experiment.py --idea cheap_gold --name gold-smoke --paths 8 --fresh 8 --seed 202610210
```

For a research run, choose a new seed family and adequate sample size; record it before seeing results:

```bash
python3 tools/run_experiment.py --idea cheap_gold --name gold-replication --paths 1000 --fresh 2000 --seed 202610310
```

The five cases are the base block bootstrap, trend returns reduced 2%/year and 4%/year, the post-2000 era, and three-month blocks.
Real history windows and explicit unobserved shocks provide additional checks. Report dollars per month after tax in today's dollars,
early-retirement and lifetime income, low-percentile outcomes, cuts, deep dips, real loss, depletion, margin calls, costs and complexity.

## What the existing acceptance code actually checks

`printer/improve.py:safe` permits, per stress case, up to **1 percentage point more real loss**, **2 points more deep dips**,
**0.2 points more depletion**, and **2 points fewer histories with an uncut base paycheck**, relative to the reference.
The maximum margin-call probability may be no higher than the greater of 1% and the reference's maximum.
These are engineering tolerances in the legacy search, not proof that risk is equal or lower.

`better` also requires a category-specific increase in mean certainty-equivalent spending and no reduction in base-case
low-percentile first-decade spending. The thresholds and candidate categories are defined in the code; copy them into your record.
The certainty-equivalent objective uses risk aversion gamma=3 and is not the same as the median paycheck.

## Stronger validation for new recommendations

Do not silently call legacy acceptance strict dominance. Report differences and uncertainty for every metric and stress case.
For a strict no-increase rule, require every specified risk estimate to be no worse; explain that sampling uncertainty can still hide harm.
Use paired common paths for candidate/baseline comparisons, multiple held-out seed families, proxy alternatives, cost/rate sensitivity,
historical starts, and walk-forward selection where feasible. Preserve the full candidate count and rejected runs to expose multiple testing.
Bootstrap confidence intervals require a justified resampling unit; overlapping histories are not independent real-world observations.

The original harness uses fixed seed families. The new runner supplies distinct search and validation families; changing them does
not create new observations or repair hindsight in a fund proxy. Independent datasets and prospective tracking remain valuable.

## Thermal and promotion rules

Keep one GPU study active at a time. The runner sets `THROTTLE=1`, checks temperature, and refuses to start at 80°C or above.
The harness also cools between batches. Use CPU mode for tiny checks. A smoke test does not establish financial performance.

Review a candidate's full results, source rights and implementation feasibility before promotion. Update the specification, public
explanation, rejected-idea log and relevant regression checks together. Do not change existing default results merely to pass a test.
