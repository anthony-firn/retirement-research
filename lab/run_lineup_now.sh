#!/usr/bin/env bash
# Today's-economy-tuned ("N") portfolio for each CAGR bracket outside 12-13.5%.
# Guard rails scale with target: every analog >= -0.65*T, 2022 >= -3%, AI <= 15% (20% at 14-15%).
set -e; cd "$(dirname "$0")"
export HIST=clean_etf.json SAFETY=nowsafe EP22_FLOOR=-3 CLIMBERS=${CLIMBERS:-768} ROUNDS=${ROUNDS:-8}
for T in 6 7 8 9 10 11 14 15; do
  FLOOR=$(python3 -c "print(round(-max(3, 0.65*$T), 2))")
  AI=$([ "$T" -ge 14 ] && echo 20 || echo 15)
  echo "######## N$T: analogs >= $FLOOR%, 2022 >= -3%, AI <= $AI%"
  TARGETS=$T EP_FLOOR=$FLOOR AIX=$AI SEEDS=E$T,E$((T>6?T-1:T)),E$((T<15?T+1:T)),C1-Now,Safe-Now,S12+ SEED=$((90+T)) OUT=lineup_n$T.json python3 frontier.py
done
