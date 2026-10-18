# Roadmap — from personal tool to a product that helps people

Written 2026-10-17. The regulatory notes are a general orientation, **not legal advice** — confirm each step
with a securities attorney / compliance consultant in the states where you operate.

## Phase 0 — Personal research tool (now)
- Lineup portfolios, policy (life-stage tier + guaranteed breaker), advisor, withdrawal rule (done).
- Retirement planner: Social Security, pensions, account types, taxes (in progress — `planner/`).
- Tax-aware rebalancing + asset location study (in progress).
- Data: testfol.io API (undocumented; fine for personal research, not for a product).

## Phase 1 — Own backtest engine ("our testfol") (next)
- `engine/` package: data layer, simulated ("SIM") backfills, portfolio backtester, testfol-compatible JSON API.
- Free/public sources: Ken French data library (US equity 1926+, factors, industries), FRED (Treasury yields,
  T-bills, CPI), Shiller (S&P/CPI 1871+), Yahoo/Stooq daily ETF prices for personal use.
- SIM recipes mirror testfol's documented sources (`lab/sim_catalog.csv`): e.g. VTISIM = Fama-French Rm-Rf + Rf →
  VTSMX → VTI; IEF/TLT SIMs = Treasury-yield total-return models; GLDSIM = LBMA gold.
- Validation gate: every SIM and every lineup portfolio must match testfol within ~0.1%/yr CAGR and ~0.5 pt MDD
  before testfol is retired from the pipeline.
- Self-host: FastAPI service + simple web UI, local first.

## Phase 2 — Product hardening (before any outside user)
- Licensed market data for anything redistributed (Yahoo/Stooq terms generally prohibit commercial use).
- Suitability flow: risk questionnaire, income/tax/SS inputs, leverage-free default for simple/vulnerable users.
- Security & privacy: no credentials stored, encryption at rest, privacy policy (GLBA-style safeguards).
- Audit trail of every recommendation (inputs, data version, model version).
- Marketing hygiene: the SEC Marketing Rule restricts hypothetical/backtested performance in advertising.

## Phase 3 — Regulatory ladder (US, typical path — verify with counsel)
1. **Personal use only** — no registration needed.
2. **Free general education** (articles, generic model portfolios, calculators) — the "publisher" exclusion can
   apply to impersonal, bona-fide, regularly published content; *personalised* tool output is a grey zone.
3. **State-registered investment adviser (RIA)** — required in most states once you give personalised advice for
   compensation (de-minimis client exemptions vary by state). Typical steps: Series 65 (or CFP/CFA waiver), Form ADV
   Parts 1 & 2 via IARD, compliance manual, code of ethics, books & records, E&O insurance.
4. **SEC registration** — generally at ~$100M+ regulatory AUM, or via the internet-adviser exemption
   (Rule 203A-2(e), amended 2024 — check current conditions). Annual ADV updates, CCO, compliance program.
5. Optional credibility: CFP® certification; avoid custody (use client-owned brokerage accounts + broker APIs).

## Guiding principles
- Honest testing: walk-forward, out-of-sample, stress beyond the data, costs included — keep the logs.
- Default to the simplest portfolio that meets the need; complexity must earn its keep.
- The tool informs; the person decides.
