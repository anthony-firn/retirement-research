#!/usr/bin/env bash
# The guide: safest ETF-only portfolio at every CAGR 6..15% (drawdown-based safety, every decade).
set -e; cd "$(dirname "$0")"
HIST=clean_etf.json SAFETY=drawdown TARGETS=${TARGETS:-6,7,8,9,10,11,12,13,14,15} CLIMBERS=${CLIMBERS:-768} ROUNDS=${ROUNDS:-8} \
SEED=31 OUT=frontier_etf.json python3 frontier.py
