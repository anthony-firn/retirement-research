#!/usr/bin/env bash
# Extend the ETF-only guide: fill 12.5-14.5%, push 16-30%, and find max CAGR under drawdown caps.
set -e; cd "$(dirname "$0")"
export HIST=clean_etf.json SAFETY=absolute CLIMBERS=${CLIMBERS:-768} ROUNDS=${ROUNDS:-8}
echo "######## fill 12.5-14.5%"
SEEDS=E12,E13,E14,E15 TARGETS=12.5,13.5,14.5 SEED=41 OUT=frontier_etf_fill.json python3 frontier.py
echo; echo "######## push 16-30%"
SEEDS=E14,E15 TARGETS=16,17,18,19,20,21,22,23,24,25,26,28,30 SEED=42 OUT=frontier_etf_hi.json python3 frontier.py
echo; echo "######## max CAGR under max-drawdown caps (every decade, decade CAGR >= 0.7x)"
SAFETY=maxret SEEDS=E15 TARGETS=30,40,50,60 SEED=43 OUT=frontier_maxret.json python3 frontier.py
