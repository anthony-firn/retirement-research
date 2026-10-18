"""testfol-compatible HTTP API:  uvicorn engine.api:app --port 8765   then POST /api/backtest (same JSON as testfol)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .backtest import backtest
app = FastAPI(title="Investment engine", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost", "http://127.0.0.1"], allow_methods=["POST", "GET"], allow_headers=["*"])
@app.get("/api/health")
def health(): return {"ok": True}
@app.post("/api/backtest")
def api_backtest(req: dict): return backtest(req)
