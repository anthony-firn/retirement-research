#!/usr/bin/env bash
# Long GPU searches with C1 as the benchmark to beat (clean universes, no ticker modifiers).
set -e; cd "$(dirname "$0")"
export BASE='{"IEISIM":34,"KMLMSIM":20,"UUPSIM":13,"GLDSIM":11,"SPMOSIM":11,"XLPSIM":5,"QLDSIM":3,"XLESIM":3}'
export CLIMBERS=${CLIMBERS:-2048} ROUNDS=${ROUNDS:-20}
echo "######## vs C1: expanded universe (ETFs + funds + extra LETFs)"; HIST=clean_X.json  SEED=1 OUT=gpu_c1_X.json   python3 gpusearch.py
echo; echo "######## vs C1: ETFs only, new seed";                     HIST=clean_etf.json SEED=2 OUT=gpu_c1_etf.json python3 gpusearch.py
