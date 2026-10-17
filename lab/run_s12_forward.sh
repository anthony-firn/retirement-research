#!/usr/bin/env bash
# ~12% CAGR, safest historically + today's guard rails + forward-scenario floor (bond revolt etc.).
set -e; cd "$(dirname "$0")"
while pgrep -f "python3 frontier.py" >/dev/null; do sleep 15; done
export BASE='{"KMLMSIM":35,"VBRSIM":19,"TYDSIM":14,"GLDSIM":14,"XLVSIM":9,"TQQQSIM":5,"UUPSIM":3,"GSGSIM":1}'
export HIST=clean_etf.json SAFETY=nowsafe TARGETS=11.9 EP_FLOOR=-8 EP22_FLOOR=-3 AIX=15 CLIMBERS=${CLIMBERS:-1536} ROUNDS=${ROUNDS:-12} SEEDS=S12,V4-12,E12,S12.5,C1-Now
echo "######## forward scenarios >= -5%"; FWD_FLOOR=-5 SEED=81 OUT=s12_fwd5.json python3 frontier.py
echo; echo "######## forward scenarios >= -4%"; FWD_FLOOR=-4 SEED=82 OUT=s12_fwd4.json python3 frontier.py
