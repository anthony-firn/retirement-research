#!/usr/bin/env bash
# Regime-aware searches for the Oct-2026 environment (see results/MARKET_2026-10.md).
# Excludes MCISIM (Barings Corporate Investors = private credit) and VWEHX (high yield) given current credit stress.
set -e; cd "$(dirname "$0")"
export HIST=clean_X.json EXCLUDE=MCISIM,VWEHX CLIMBERS=${CLIMBERS:-1024} ROUNDS=${ROUNDS:-10}
echo "######## MODE=now  (C1 quality, best in today's scenarios)"; MODE=now  SEED=11 OUT=regime_now.json  python3 regime.py
echo; echo "######## MODE=safe (safe + sharp for today)";          MODE=safe SEED=12 OUT=regime_safe.json python3 regime.py
