#!/usr/bin/env bash
# Runs after the main frontier: fills in 6-7% and builds an ETF-only 6-15% frontier.
set -e; cd "$(dirname "$0")"
while pgrep -f "python3 frontier.py" >/dev/null; do sleep 15; done
echo "######## mixed universe, 6-7%"
HIST=clean_X.json EXCLUDE=MCISIM,VWEHX,FKINX TARGETS=6,7 CLIMBERS=768 ROUNDS=8 SEED=22 OUT=frontier_lo.json python3 frontier.py
echo; echo "######## ETF-only universe, 6-15%"
HIST=clean_etf.json TARGETS=6,7,8,9,10,11,12,13,14,15 CLIMBERS=768 ROUNDS=8 SEED=23 OUT=frontier_etf.json python3 frontier.py
