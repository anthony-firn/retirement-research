#!/usr/bin/env bash
# Adaptive (non-guaranteed) v2 searches: full selection + walk-forward. Waits for any running search first.
set -e; S="$(cd "$(dirname "$0")" && pwd)"; cd "$S"
while pgrep -f "python3 $S/search_v2.py" >/dev/null || pgrep -f "python3 search_v2.py" >/dev/null; do sleep 15; done
echo "######## ADAPTIVE (budget refills)"; PYTHONUNBUFFERED=1 N=300000 GUARANTEE=0 WALKFWD=0 SEED=4 python3 "$S/search_v2.py"
echo; echo "######## ADAPTIVE WALK-FORWARD";   PYTHONUNBUFFERED=1 N=300000 GUARANTEE=0 WALKFWD=1 SEED=5 python3 "$S/search_v2.py"
