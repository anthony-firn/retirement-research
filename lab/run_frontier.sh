#!/usr/bin/env bash
# Return/safety efficient frontier, 8%..16% CAGR (clean universe, no private credit / high yield).
set -e; cd "$(dirname "$0")"
HIST=clean_X.json EXCLUDE=MCISIM,VWEHX,FKINX TARGETS=${TARGETS:-8,9,10,11,12,13,14,15,16} \
CLIMBERS=${CLIMBERS:-768} ROUNDS=${ROUNDS:-8} SEED=21 OUT=frontier.json python3 frontier.py
