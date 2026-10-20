"""testfol.io share links (same payload as lab/make_link.py): https://testfol.io/?d=<urlencoded base64(zlib(json))>.
The printer's base paycheck goes in as a monthly, inflation-adjusted withdrawal; testfol has no bonus bucket or safety brake,
so the link shows the portfolio living off its base paycheck. Rebalancing: Yearly plus a 100% relative band (the 2x valve)."""
import json, zlib, base64, urllib.parse

def _portfolio(name, alloc):
    return {"name": name, "tickers": [{"ticker": t + "SIM", "percent": w} for t, w in alloc], "investDividends": True, "rebalanceFreq": "Yearly",
            "rebalanceOffset": 0, "drag": 0, "absoluteDev": 0, "relativeDev": 100, "rebalanceBandMode": "SYMMETRIC",
            "absoluteDevBelow": 0, "absoluteDevAbove": 0, "relativeDevBelow": 0, "relativeDevAbove": 0}

def link(portfolios, start_val=10000, withdraw_month=0.0):
    gp = {"start_date": "", "end_date": "", "start_val": round(start_val), "adj_inflation": False, "adjust_cashflows_for_inflation": bool(withdraw_month),
          "annual_cashflow_growth_rate": 0, "target_currency": "USD", "cashflow": -round(withdraw_month), "cashflow_freq": "Monthly", "cashflow_offset": 0,
          "match_first_portfolio_income_cashflows": False, "one_time_cashflows": [], "rolling_window": 60, "withdrawal_surface_include": False,
          "withdrawal_surface_projection": "NONE", "withdrawal_surface_projection_min_years": 10, "withdrawal_surface_start_years": 5,
          "withdrawal_surface_end_years": 50, "withdrawal_surface_step_years": 1, "cashflow_legs": []}
    data = {"globalParams": gp, "portfolios": [_portfolio(p.get("name") or "Portfolio", p["alloc"]) for p in portfolios[:5]], "glidePortfolios": []}
    d = base64.b64encode(zlib.compress(json.dumps(data, separators=(",", ":")).encode(), 9)).decode()
    return "https://testfol.io/?d=" + urllib.parse.quote(d, safe="")
