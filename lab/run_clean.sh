cd "$(dirname "$0")"
export BASE='{"SHYSIM":25,"SPMOSIM":20,"GLDSIM":15,"KMLMSIM":20,"UUPSIM":10,"XLVSIM":5,"ZROZSIM":5}' NSTART=128
echo "######## CLEAN ETFs only"; HIST=clean_etf.json OUT=clean_etf_res.json python3 beat_r1.py
echo; echo "######## CLEAN ETFs + asset-class funds"; HIST=clean_A.json OUT=clean_A_res.json python3 beat_r1.py
