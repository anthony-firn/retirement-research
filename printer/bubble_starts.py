"""What if the retiree starts the printer right at a market top? Each printer runs on the ACTUAL path from each peak (1972 Nifty Fifty,
1987, 2000 dot-com, 2007, 2020, 2022) to October 2026 (at most 25 years). The retiree's taxes, $150k, $/month after tax in today's
dollars. Pre-inception fund histories are reconstructed.  Usage: python3 printer/bubble_starts.py   (writes results/bubble_starts.log)"""
import os, sys, datetime as dt, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.argv = [sys.argv[0]]
import money_printer as mp, improve as im
from dataclasses import replace
Z = 150_000; CAL = np.asarray(mp.h.CAL)
day = lambda s: int(np.searchsorted(CAL, int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.UTC).timestamp())))
TOPS = [("1972 Nifty Fifty top", "1972-12-11"), ("1987 pre-crash top", "1987-08-25"), ("2000 dot-com top", "2000-03-24"),
        ("2007 credit top", "2007-10-09"), ("2020 pre-Covid top", "2020-02-19"), ("2022 rate-shock top", "2022-01-03")]
def printers():
    B = im.load_best(); s = im.P(**B["simple"]); c = im.P(**B["credit"]); box = dict(rate_spread=0.6, interest_tax="capital"); fl = dict(lev_floor=115 / 150, lev_resume=130 / 150)
    extra = [p for p in (globals().get("EXTRA") or [])]
    return [replace(s, name="MP-2.1 (no loan)"), replace(c, name="box loan 1.25x + pay off below $115k", **fl),
            replace(s, name="crash buyer: no loan, 1.25x after a 20% fall", lev_dd=0.20, lev_dd_to=1.25, bucket_offsets_loan=True, **box, **fl),
            replace(s, name="phase in: 50% in SHY for the first year", alloc={**{k: w / 2 for k, w in s.alloc.items()}, "SHYSIM": 50}, glide={**s.alloc, "SHYSIM": 0}, glide_years=1),
            replace(s, name="60/40 printer (same rules)", alloc=mp.load_alloc("60/40"))] + extra
if __name__ == "__main__":
    pr = printers(); log = open(os.path.join(ROOT, "..", "results", "bubble_starts.log"), "w")
    def say(x=""): print(x, flush=True); log.write(x + "\n"); log.flush()
    say(f"Starting at a market top: actual paths, the retiree's taxes, ${Z:,.0f}, $/month after tax (today's $)")
    for lab, s0 in TOPS:
        i = day(s0); yrs = min(25, (len(CAL) - 2 - i) // 252); L = yrs * 252
        IDX = torch.tensor((i + np.arange(L))[None, :], device=mp.DEV); r = mp.simulate(pr, IDX)
        say(f"\n{lab} ({s0}, {yrs} years)   {'first 5 yrs avg':>15} {'whole-window avg':>16} {'lowest real value':>18} {'real value now':>15}  base cut?  margin call?")
        for c, p in enumerate(pr):
            sp = r["spend"][c][0]; m5 = sp[:60].mean() * Z; mall = sp[:yrs * 12].mean() * Z
            say(f"  {p.name:46} {'$' + format(m5, ',.0f'):>15} {'$' + format(mall, ',.0f'):>16} {r['minreal'][c][0] * 100:16.0f}%  {r['real_end'][c][0] * 100:13.0f}%   "
                f"{'yes' if r['cut'][c][0] else 'no':>6}     {'yes' if r['margin_call'][c][0] else 'no':>6}")
