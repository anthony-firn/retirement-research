"""Money Printer Forge, hosted locally:  python3 printer/app/server.py [--port 8777] [--open]  ->  http://127.0.0.1:8777

Serves the single-page app (static/) and a small JSON API:
  GET  /api/atlas      every validated printer + stats per account type and horizon, fund names, brackets, benchmarks
  POST /api/backtest   {portfolios, start, end, rebalance, real}        testfol-style growth / drawdown / annual / rolling / stats
  POST /api/history    {printers, mix, bracket, start, end}           the printers running on real history (paychecks, bucket, brake)
  POST /api/fan        {spec, mix, bracket, years}                    percentiles of balance and paycheck over simulated futures
  POST /api/testfol    {portfolios, start_val, withdraw_month}        a testfol.io share link (deep link) for the portfolios
  GET  /api/roster, POST /api/profiles | /api/battles | /api/build      the redesigned app (plans.py): strategies, their stats for a
                                                                     situation, historical and future battles, the saving-years plan
  /api/ops/list | setup | create | today | commit | sync              operations on printer/operate.py (state files in private/ops/)
The redesigned app is at / ; the original Forge (frontier, backtests) is at /classic.
mix = dollars by tax treatment {free, deferred, taxable}; bracket = "low" | "mid" (see atlas_data.BRACKETS).
Results are cached in memory for the session. Binds to 127.0.0.1 only."""
import os, sys, json, gzip, argparse, functools, webbrowser, threading
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from security import guard
import atlas_data, backtest as bt, share, plans

app = FastAPI(title="Money Printer Forge", docs_url=None, redoc_url=None)
API_TOKEN = os.environ.get("MONEY_PRINTER_API_TOKEN", "")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("MONEY_PRINTER_ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(GZipMiddleware, minimum_size=2000)
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
ATLAS = atlas_data.build()
ATLAS_JSON = json.dumps(ATLAS, separators=(",", ":")).encode(); ATLAS_GZ = gzip.compress(ATLAS_JSON, 6)   # built once: ~6 MB -> ~1 MB

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
@app.get("/classic")
def classic(): return FileResponse(os.path.join(HERE, "static", "classic", "index.html"))

app.middleware("http")(guard(API_TOKEN, ALLOWED_ORIGINS))

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(HERE, "static", "sw.js"), media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})

def _plain(fn, q):
    try: return JSONResponse(fn(q))
    except (ValueError, KeyError, FileNotFoundError) as e: raise HTTPException(400, str(e).strip("'\""))
@app.get("/api/roster")
def roster(): return plans.roster()
@app.post("/api/profiles")
def profiles(q: dict): return _plain(plans.profiles, q)
@app.post("/api/battles")
def battles(q: dict): return _plain(plans.battles, q)
@app.post("/api/build")
def build(q: dict): return _plain(plans.build, q)
@app.post("/api/quest")
def quest(q: dict): return _plain(plans.quest, q)
@app.get("/api/ops/list")
def ops_list(): return plans.ops_list()
@app.post("/api/ops/setup")
def ops_setup(q: dict): return _plain(plans.ops_setup, q)
@app.post("/api/ops/create")
def ops_create(q: dict): return _plain(plans.ops_create, q)
@app.post("/api/ops/today")
def ops_today(q: dict): return _plain(plans.ops_today, q)
@app.post("/api/ops/commit")
def ops_commit(q: dict): return _plain(plans.ops_commit, q)
@app.post("/api/ops/sync")
def ops_sync(q: dict): return _plain(plans.ops_sync, q)
@app.get("/api/atlas")
def atlas(request: Request):
    if "gzip" in request.headers.get("accept-encoding", ""): return Response(ATLAS_GZ, media_type="application/json", headers={"Content-Encoding": "gzip", "Cache-Control": "no-cache"})
    return Response(ATLAS_JSON, media_type="application/json")
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

if API_TOKEN and ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])

if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8777); ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--open", action="store_true"); a = ap.parse_args()
    if a.host not in ("127.0.0.1", "localhost", "::1") and not API_TOKEN:
        ap.error("Set MONEY_PRINTER_API_TOKEN before listening beyond localhost. Use HTTPS for phone access.")
    url = f"http://127.0.0.1:{a.port}"; print(f"Money Printer Forge: {url}", flush=True)
    if a.open: threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
