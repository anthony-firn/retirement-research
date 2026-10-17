# Investment — portfolio research with testfol.io

Backtesting and optimizing a diversified portfolio against testfol.io's (undocumented) backtest API,
with a local simulator for fast searches. testfol.io is always the final judge.

## Rules for a valid result
- **Final test = one continuous testfol.io backtest**, 1987-12-31 → today (KMLMSIM sets the start).
- **Investable tickers only**: real ETFs/funds or testfol.io `…SIM` backfills of real ETFs.
  **No ticker modifiers** (`?L=`, `?E=` …) — e.g. `TLTSIM?L=-1&E=0.9` as a TBF stand-in is not allowed.
- ≤ 8 holdings, ≤ 35% per holding, yearly rebalance, dividends reinvested.
- Rank by **Sharpe, Calmar, Ulcer, max drawdown**; CAGR must not fall below the benchmark.
- Prefer portfolios that win in **every decade**, not just the full period (full-period-only
  optimization overfits to the 1988–2020 bond bull market).
- Avoid hindsight picks (star active managers like BRK-A, PRWCX) unless clearly labeled.

## Layout
```
lab/        scripts + data; run everything from inside lab/
  hist_long.json      master cache of raw testfol.io daily histories (committed)
  make_data.sh        rebuilds every derived dataset from hist_long.json
  sim_catalog.csv     testfol.io SIM ticker catalog (coverage, source)
results/    findings and portfolio definitions
```

## Quick start
```bash
cd lab
./make_data.sh                  # build derived datasets (gitignored)
python3 final_beat.py           # re-verify candidates on testfol.io
```

## testfol.io API notes
- `POST https://testfol.io/api/backtest` — see `lab/run.py` for the payload. No auth.
- Max 5 portfolios per request; Python's default User-Agent gets 403 (send a curl UA).
- Share links: `https://testfol.io/?d=<base64(zlib(json))>` — see `lab/make_link.py`.

## Script index (lab/)
| Area | Scripts |
|---|---|
| Fetch from testfol.io | `run.py` `fetch.py` `fetch_long.py` `fetch_univ.py` `fetch_more.py` `probe.py` |
| Datasets | `build_long.py` `build_univ.py` `build_native.py` `build_ext.py` `build_clean.py` `make_data.sh` |
| Local simulator | `sim.py` (spliced DBMF) · `simu.py` (28-asset) · `simn.py` (native; `HIST=` env picks dataset) |
| Optimizers (round 1, 2000/1988 spliced) | `opt.py` `opt2.py` `opt3.py` `variants.py` |
| Universe search + validation | `search.py` `search2.py` `reverse.py` `greedy.py` `cv.py` |
| Beat-the-benchmark search | `beat.py` `beat_robust.py` `beat2.py` `beat_r1.py` `run_clean.sh` |
| Verification / analysis | `verify.py` `verify2.py` `final.py` `final88.py` `final_beat.py` `analyze.py` `make_link.py` |
