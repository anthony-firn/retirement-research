"""Free/public data adapters (personal research use). Each returns (timestamps[int UTC seconds], values[float]).
- Ken French data library: daily US market (Mkt-RF + RF) and RF, 1926+  -> total-return index
- Yahoo Finance chart API: daily adjusted close (dividends & splits) for ETFs/mutual funds; yields for ^IRX ^FVX ^TNX ^TYX
Licensing: Ken French data is free for research; Yahoo data terms prohibit commercial redistribution (see ROADMAP Phase 2)."""
import io, json, os, time, zipfile, urllib.request, datetime as dt
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
UA = {"User-Agent": "Mozilla/5.0"}

def _get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def _cached(name, fn, max_age_days=1.0):
    path = os.path.join(CACHE, name + ".json")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_days * 86400:
        d = json.load(open(path)); return d["t"], d["v"]
    t, v = fn(); json.dump({"t": t, "v": v, "fetched": time.time()}, open(path, "w")); return t, v

def _ts(y, m, d): return int(dt.datetime(y, m, d, tzinfo=dt.UTC).timestamp())

def french_market_daily():
    """Total-return index of the US market from Fama-French daily factors: r = (Mkt-RF + RF)/100."""
    def fetch():
        z = zipfile.ZipFile(io.BytesIO(_get("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip")))
        txt = z.read(z.namelist()[0]).decode("latin1").splitlines(); t, v, lvl = [], [], 1.0
        for line in txt:
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 5 and p[0].isdigit() and len(p[0]) == 8:
                lvl *= 1 + (float(p[1]) + float(p[4])) / 100; t.append(_ts(int(p[0][:4]), int(p[0][4:6]), int(p[0][6:]))); v.append(lvl)
        return t, v
    return _cached("french_mkt_daily", fetch, 7)

def french_rf_daily():
    def fetch():
        z = zipfile.ZipFile(io.BytesIO(_get("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip")))
        txt = z.read(z.namelist()[0]).decode("latin1").splitlines(); t, v, lvl = [], [], 1.0
        for line in txt:
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 5 and p[0].isdigit() and len(p[0]) == 8:
                lvl *= 1 + float(p[4]) / 100; t.append(_ts(int(p[0][:4]), int(p[0][4:6]), int(p[0][6:]))); v.append(lvl)
        return t, v
    return _cached("french_rf_daily", fetch, 7)

def yahoo(ticker, field="adjclose"):
    """Daily adjusted close (total return incl. dividends) or 'close' (for yield indices like ^TNX)."""
    def fetch():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(ticker)}?period1=0&period2=9999999999&interval=1d&events=div,split"
        d = json.loads(_get(url))["chart"]["result"][0]; ts = d["timestamp"]
        vals = d["indicators"]["adjclose"][0]["adjclose"] if field == "adjclose" else d["indicators"]["quote"][0]["close"]
        pairs = [(int(dt.datetime.fromtimestamp(a, dt.UTC).replace(hour=0, minute=0, second=0).timestamp()), b) for a, b in zip(ts, vals) if b is not None]
        return [p[0] for p in pairs], [float(p[1]) for p in pairs]
    return _cached("yahoo_" + ticker.replace("^", "IDX_"), fetch, 1)
