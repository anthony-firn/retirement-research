#!/usr/bin/env bash
# Find portfolios safer than S12 on every measure at ~12% CAGR, with today's-economy guard rails.
set -e; cd "$(dirname "$0")"
export BASE='{"KMLMSIM":35,"VBRSIM":19,"TYDSIM":14,"GLDSIM":14,"XLVSIM":9,"TQQQSIM":5,"UUPSIM":3,"GSGSIM":1}' SAFETY=beat TARGETS=11.9 EP_FLOOR=-8 EP22_FLOOR=-3 AIX=15 CLIMBERS=${CLIMBERS:-1536} ROUNDS=${ROUNDS:-12} SEEDS=S12,V4-12,E12,S12.5,C1-Now
echo "######## ETFs, seed A"; HIST=clean_etf.json SEED=71 OUT=beat_s12_a.json python3 frontier.py
echo; echo "######## ETFs, seed B"; HIST=clean_etf.json SEED=72 OUT=beat_s12_b.json python3 frontier.py
echo; echo "######## ETFs + SPXL/URTY/TNA/SPY"; HIST=clean_X.json EXCLUDE=MCISIM,VWEHX,FKINX,VFIIX,PRPFX,VGPMX,VWINX,VWELX,VUSTX,VBMFX SEED=73 OUT=beat_s12_x.json python3 frontier.py
