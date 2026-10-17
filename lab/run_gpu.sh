#!/usr/bin/env bash
# Full GPU searches vs FULL#1 (clean universes, no ticker modifiers).
set -e; cd "$(dirname "$0")"
export CLIMBERS=${CLIMBERS:-1024} ROUNDS=${ROUNDS:-10}
echo "######## CLEAN ETFs only";               HIST=clean_etf.json OUT=gpu_clean_etf.json python3 gpusearch.py
echo; echo "######## CLEAN ETFs + asset-class funds"; HIST=clean_A.json  OUT=gpu_clean_A.json  python3 gpusearch.py
