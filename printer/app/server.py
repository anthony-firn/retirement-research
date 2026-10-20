"""Money Printer Forge, hosted locally:  python3 printer/app/server.py [--port 8777] [--open]  ->  http://127.0.0.1:8777

Serves the single-page app (static/) and a small JSON API:
  GET  /api/atlas      every validated printer + stats per account type and horizon, fund names, brackets, benchmarks
  POST /api/backtest   {portfolios, start, end, rebalance, real}        testfol-style growth / drawdown / annual / rolling / stats
  POST /api/history    {printers, mix, bracket, start, end}           the printers running on real history (paychecks, bucket, brake)
  POST /api/fan        {spec, mix, bracket, years}                    percentiles of balance and paycheck over simulated futures
  POST /api/testfol    {portfolios, start_val, withdraw_month}        a testfol.io share link (deep link) for the portfolios
mix = dollars by tax treatment {free, deferred, taxable}; bracket = "low" | "mid" (see atlas_data.BRACKETS).
Results are cached in memory for the session. Binds to 127.0.0.1 only."""
import os, sys, json, argparse, functools, webbrowser, threading
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
import atlas_data, backtest as bt, share

app = FastAPI(title="Money Printer Forge", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=2000)
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
ATLAS = atlas_data.build()

def _bracket(q):
    b = q.get("bracket", "low")
    if b not in atlas_data.BRACKETS: raise HTTPException(400, f"unknown tax bracket {b!r}")
    if not any(float(q.get("mix", {}).get(k, 0)) > 0 for k in ("free", "deferred", "taxable")): raise HTTPException(400, "Enter how much money is in at least one account.")
    return b

def _check_alloc(alloc):
    if not alloc or abs(sum(w for _, w in alloc) - 100) > 0.6: raise HTTPException(400, "Fund weights must add up to 100%.")
    bad = [t for t, _ in alloc if t not in atlas_data.FUNDS]
    if bad: raise HTTPException(400, f"No history for {', '.join(bad)}.")

@functools.lru_cache(maxsize=512)
def _cached(kind, key):
    q = json.loads(key)
    if kind == "backtest": return bt.portfolio(q["portfolios"], q.get("start"), q.get("end"), q.get("rebalance", "Printer rule"), bool(q.get("real")))
    if kind == "history": return bt.history(q["printers"], q["mix"], _bracket(q), q.get("start"), q.get("end"))
    if kind == "fan": return bt.fan(q["spec"], q["mix"], _bracket(q), q.get("years", 40))

def run(kind, q):
    for s in q.get("portfolios", []) + q.get("printers", []) + ([q["spec"]] if "spec" in q else []): _check_alloc(s.get("alloc"))
    if len(q.get("portfolios", q.get("printers", []))) > 6: raise HTTPException(400, "Compare at most 6 at a time.")
    return JSONResponse(_cached(kind, json.dumps(q, sort_keys=True)))

@app.get("/")
def index(): return FileResponse(os.path.join(HERE, "static", "index.html"))
@app.get("/api/atlas")
def atlas(): return JSONResponse(ATLAS)
@app.post("/api/testfol")
def testfol(q: dict):
    for p in q.get("portfolios", []): _check_alloc(p.get("alloc"))
    return {"url": share.link(q["portfolios"], float(q.get("start_val", 10000)), float(q.get("withdraw_month", 0)))}
@app.post("/api/backtest")
def backtest(q: dict): return run("backtest", q)
@app.post("/api/history")
def history(q: dict): return run("history", q)
@app.post("/api/fan")
def fan(q: dict): return run("fan", q)

if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8777); ap.add_argument("--open", action="store_true"); a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}"; print(f"Money Printer Forge: {url}", flush=True)
    if a.open: threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")
