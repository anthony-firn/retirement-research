# engine — our own testfol-style backtester (Phase 1)

```
python3 engine/validate.py                                   # validation gates
python3 -m uvicorn engine.api:app --host 127.0.0.1 --port <p> # testfol-compatible API: POST /api/backtest
ENGINE_DATA=own ...                                          # use our own SIM recipes where validated
```
- `data/sources.py` — Ken French (daily market + RF, 1926+), Yahoo (daily adjusted close, yield indices). Cached in `data/cache/`.
- `store.py` — ticker resolution: own recipe → testfol cache → Yahoo. Every response reports each ticker's source.
- `sims.py` — SIM recipes (splice older proxies onto the real fund).
- `backtest.py` — portfolio backtester; stats defined like testfol (CAGR, std, max DD, Sharpe, Sortino, Calmar, Ulcer, UPI).

## Validation status (results/engine_validation.log)
- **Engine:** matches testfol.io on 13 lineup portfolios — worst CAGR gap 0.013 pts/yr; MDD/Ulcer equal; Sharpe within ~0.005.
- **VTISIM recipe** (French → VTSMX → VTI): 1950–1991 and 2001–2026 within ±0.08 pts/yr (daily corr ≥ 0.998);
  open gaps: 1927–49 −0.36, 1992–2000 −0.62 (Yahoo mutual-fund dividend adjustment suspected).

## SIM recipes still to build (sources from lab/sim_catalog.csv)
| SIM | testfol source | Our planned free source |
|---|---|---|
| SHY/IEI/IEF/TLT/ZROZ | Treasury-yield total-return models | US Treasury par-yield CSV (1990+), Fed H.15 / Yahoo ^IRX ^FVX ^TNX ^TYX (1962/1970+) |
| BNDSIM | VBMFX → BND | Yahoo VBMFX (1986+) → BND |
| GLDSIM | LBMA PM gold → GLD | free gold history (monthly pre-2000) + GLD |
| UUPSIM | DXY + cash → UUP | Yahoo DX-Y.NYB (1971+) + T-bill → UUP |
| Sector/style (XLV, XLP, XLE, VBR, VOE, VTV …) | Fama-French industry / size-value portfolios | Ken French 49-industry & 6/25 size-BM daily files |
| VEASIM | MSCI EAFE net → VTMGX → VEA | Ken French international (monthly) → VTMGX → VEA |
| KMLMSIM | KFA MLM Index → KMLM | MLM Index history (Mount Lucas) or trend proxy (strategy/history70s.py) |
| Leveraged (TQQQ, TYD, TMF, UGL …) | k× underlying daily − financing − fees | derive from our underlying + T-bill financing |
Each recipe must pass gate 2 (≤ 0.1 pt/yr per period, daily corr ≥ 0.99) before `ENGINE_DATA=own` uses it.
