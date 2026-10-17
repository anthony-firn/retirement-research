#!/usr/bin/env bash
# Sweet spot 12-13.5% CAGR: historically safest AND guarded for the Oct-2026 economy (see results/MARKET_2026-10.md).
set -e; cd "$(dirname "$0")"
export HIST=clean_etf.json SAFETY=nowsafe TARGETS=12,12.5,13,13.5 CLIMBERS=${CLIMBERS:-768} ROUNDS=${ROUNDS:-8} SEEDS=E12,E12.5,E13,E13.5,C1-Now,C1
echo "######## V1: every analog >= -8%, 2022 >= -3%";            EP_FLOOR=-8 EP22_FLOOR=-3 SEED=51 OUT=sweet_v1.json python3 frontier.py
echo; echo "######## V2: every analog >= -6%, 2022 >= 0%";        EP_FLOOR=-6 EP22_FLOOR=0  SEED=52 OUT=sweet_v2.json python3 frontier.py
echo; echo "######## V3: V2 + AI exposure <= 10%";                EP_FLOOR=-6 EP22_FLOOR=0 AIX=10 SEED=53 OUT=sweet_v3.json python3 frontier.py
