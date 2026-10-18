"""Series store. Resolution order for a ticker:
  1. our own SIM recipe (engine/sims.py) when ENGINE_DATA=own and a recipe exists
  2. cached testfol.io SIM series (lab/hist_long.json)   <- current source of truth until each recipe is validated
  3. Yahoo Finance adjusted close (plain tickers)
Every series is (t[int UTC day], v[total-return index])."""
import json, os, numpy as np
from .data import sources
ROOT = os.path.dirname(os.path.abspath(__file__))
_TF = None
def _testfol():
    global _TF
    if _TF is None: _TF = json.load(open(os.path.join(ROOT, "..", "lab", "hist_long.json")))
    return _TF

def get(ticker, mode=None):
    mode = mode or os.environ.get("ENGINE_DATA", "testfol")
    if mode == "own":
        from . import sims
        if ticker in sims.RECIPES: return sims.RECIPES[ticker]()
    tf = _testfol()
    if ticker in tf: return np.array(tf[ticker]["t"]), np.array(tf[ticker]["v"])
    t, v = sources.yahoo(ticker); return np.array(t), np.array(v)

def source_of(ticker, mode=None):
    mode = mode or os.environ.get("ENGINE_DATA", "testfol")
    from . import sims
    if mode == "own" and ticker in sims.RECIPES: return "own recipe"
    return "testfol cache" if ticker in _testfol() else "yahoo"
