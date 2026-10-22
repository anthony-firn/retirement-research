"""Safe base paycheck for each Pay-myself plan by account, tax bracket and length of retirement.

The tested plans were tuned for the retiree taxes (low bracket, taxable) over 40 years. In a regular account at middle-bracket taxes, or over
50 years, the same base is too high. Rule: the highest base (step 0.25%, never above the plan's tested base) whose base paycheck is
never cut in >= 84% of histories (85% target, 1 point of tolerance for the weekly-step estimate; daily validation put the tested
MP-2.1 at 86-87%) and runs dry in <= 1%. 2,000 reshuffled 1972-2026 histories (weekly steps), plan settings otherwise
unchanged. Usage: THROTTLE=1 python3 printer/safe_base.py   (writes results/safe_base.json / .log)"""
import os, sys, json, time, numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "app")); sys.argv = [sys.argv[0]]
import money_printer as mp
from dataclasses import replace
import plans as pl
THROTTLE = max(0.75, float(os.environ.get("THROTTLE", "1"))); OUT = os.path.join(ROOT, "..", "results")
TAXES = {"free": "none (IRA/Roth)", "taxable_low": "retiree, not working", "taxable_mid": "middle bracket"}
TESTED = {"mp21": 5.75, "crash": 5.75, "box": 5.25}
if __name__ == "__main__":
    res = {}; log = open(os.path.join(OUT, "safe_base.log"), "w")
    def say(x): print(x, flush=True); log.write(x + "\n"); log.flush()
    say("Safe base paycheck (% of the start per year, inflation-adjusted): highest base <= the tested one with base never cut >= 84% and runs dry <= 1%")
    for H in (20, 30, 40, 50):
        IDX = mp.make_idx(2000, H, step=5, seed=4401)
        for pay in ("mp21", "crash", "box"):
            for acct, tax in TAXES.items():
                if pay == "box" and acct == "free": continue
                bases = [b for b in np.arange(3.5, TESTED[pay] + 0.001, 0.25)]
                p0 = pl.BY[pay]["printer"]; pr = [replace(p0, name=f"{b:.2f}", base=float(b), tax=tax) for b in bases]
                t0 = time.time(); r = mp.simulate(pr, IDX, step=5); time.sleep(THROTTLE * (time.time() - t0))
                ok = [float(b) for c, b in enumerate(bases) if (1 - r["cut"][c].mean()) >= 0.84 and r["dead"][c].mean() <= 0.01]
                best = max(ok) if ok else float(bases[0]); res[f"{pay}|{acct}|{H}"] = best
                c = list(bases).index(min(bases, key=lambda b: abs(b - best)))
                say(f"  {H} years | {pay:5} | {acct:12} -> base {best:.2f}%  (never cut {(1 - r['cut'][c].mean()) * 100:.0f}%, runs dry {r['dead'][c].mean() * 100:.1f}%)")
    json.dump(res, open(os.path.join(OUT, "safe_base.json"), "w"), indent=1)
