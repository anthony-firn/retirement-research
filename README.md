# Retirement Research

Open tools and evidence for preparing for retirement and turning savings into spendable income.
One web interface serves desktop, installable web apps, iOS and Android native shells, with one shared Python research engine.

Original code and documentation use [Apache License 2.0](LICENSE), allowing community and proprietary reuse.
Third-party software and market data have [separate rights and notices](THIRD_PARTY.md).

## Start here

- **Use the local app:** `./forge` opens [localhost:8777](http://127.0.0.1:8777).
- **Understand the evidence:** [research library](docs/research/README.md), [history](docs/research/HISTORY.md), [data limits](docs/research/DATA.md).
- **Reproduce or improve a search:** [method and commands](docs/research/METHOD.md), [experiment template](docs/research/EXPERIMENT_TEMPLATE.md).
- **Build phone apps:** [iOS/Android instructions](mobile/README.md), [shared architecture](docs/ARCHITECTURE.md).
- **Help:** [contributor guide](CONTRIBUTING.md), [roadmap](ROADMAP.md).

The app's Research link opens the public library, cached for offline reading after browser installation and bundled in native builds.
Calculations and tracker actions require the Python server. Native packaging is implemented; signed store releases are still pending.
The current backend belongs to one household and must not share its private tracker directory between unrelated users.

## Development

Use Python 3.11 or 3.12 in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 tools/research_snapshot.py --output /tmp/retirement-inputs.json
python3 tools/build_offline.py
CUDA_VISIBLE_DEVICES='' python3 -m unittest discover -s printer/app/tests -v
node --test mobile/build.test.mjs
./forge
```

A fresh checkout needs the generated datasets checked by the snapshot tool; follow [the dependency chain](docs/research/DATA.md).
Installing packages alone does not supply those inputs. Remote availability and redistribution rights remain limitations.
The current local installation already has them. Native tooling requires Node 22+.

For an isolated small experiment:

```bash
CUDA_VISIBLE_DEVICES='' python3 tools/run_experiment.py --idea bucket_tax --name bucket-smoke --paths 8 --fresh 8 --seed 202610210
```

This records fingerprints and output in a new directory without promoting a winner. Tiny runs test wiring, not performance.
The planner uses simplified US/California tax and benefit assumptions. Some histories are reconstructed. Bootstrap paths reuse
observed data, and the legacy acceptance test allows [documented risk tolerances](docs/research/METHOD.md).

## Original portfolio lab

The conventions below describe the original lineup research and third-party comparisons. Other strategy families must state
their own constraints. The public research library explains the later income-printer and retirement-planning work.

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
printer/    money printers: simulator, searches, operator, Printer Atlas, local app (app/, run ./forge)
results/    findings and portfolio definitions
private/    personal household inputs, notes and outputs — gitignored, never committed
```

## Quick start
```bash
./forge                         # Money Printer Forge: local app at http://127.0.0.1:8777 (results/PRINTER_FORGE.md)
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
