#!/usr/bin/env bash
# Rebuild every derived dataset from the master cache hist_long.json (raw testfol.io histories).
set -e; cd "$(dirname "$0")"
python3 build_long.py                       # -> hist_spliced.json (1988+, DBMF spliced with vol-scaled KMLM pre-2000)
python3 build_univ.py                       # -> hist_univ.json    (28-asset universe, spliced DBMF)
python3 build_native.py                     # -> hist_native.json  (58 assets, native testfol series, no splicing)
python3 build_ext.py VWEHX,VFIIX,PRPFX,VGPMX,VWINX,VWELX,FKINX,VUSTX,VBMFX hist_extA.json
python3 build_ext.py VWEHX,VFIIX,PRPFX,VGPMX,VWINX,VWELX,FKINX,VUSTX,VBMFX,BRK-A,PRWCX,VPMCX,FCNTX,DODGX,FPURX hist_extB.json
python3 build_ext.py VWEHX,VFIIX,PRPFX,VGPMX,VWINX,VWELX,FKINX,VUSTX,VBMFX,SPXLSIM,SQQQSIM,URTYSIM,TNASIM,SPYSIM,MCISIM hist_extX.json   # funds + extra LETFs
python3 build_clean.py                      # -> clean_etf.json / clean_A.json (no '?' modifier tickers)
