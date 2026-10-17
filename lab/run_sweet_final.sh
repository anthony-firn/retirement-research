#!/usr/bin/env bash
# Polish pass for the 12-13.5% sweet spot (longer search, seeded with all previous winners).
set -e; cd "$(dirname "$0")"
export HIST=clean_etf.json SAFETY=nowsafe CLIMBERS=${CLIMBERS:-1024} ROUNDS=${ROUNDS:-12} EP_FLOOR=-8 EP22_FLOOR=-3
echo "######## 12-12.5%: episodes >= -8%, 2022 >= -3%, AI <= 15%"
AIX=15 TARGETS=12,12.5 SEEDS=V4-12,V4-12.5,V1-12,V1-12.5,E12,E12.5,C1-Now SEED=61 OUT=sweet_final_lo.json python3 frontier.py
echo; echo "######## 13-13.5%: episodes >= -8%, 2022 >= -3%"
TARGETS=13,13.5 SEEDS=V1-13,V1-13.5,V4-12.5,E13,E13.5,V2-12.5 SEED=62 OUT=sweet_final_hi.json python3 frontier.py
