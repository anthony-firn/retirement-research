"""Printer Atlas: the best money printer for every mix of plain-language preferences, cached for the slider UI.

Five sliders, LEVELS steps each (0 = left end, 1 = right end):
  safety  'bigger paycheck' -> 'never run dry'   weight of the stress case (trend funds earn 2%/yr less) + break-risk caps
  steady  'big bonus years' -> 'same every month' risk aversion over the income stream (CRRA gamma) + penalty on jumpy years
  legacy  'spend it'        -> 'leave it'         value placed on what is left after 40 years (real, incl. the cash bucket)
  calm    'ride the waves'  -> 'calm balance'     penalty on the bad-case (1 in 10) drop of the balance from its high
  simple  'simple' .. 'sophisticated' (5 tiers)   hard limits: number of funds, leveraged funds, K-1 funds
Utility of printer x in cell (s, t, g, c):  [(1-ws) CE_b(gamma_t) + ws CE_s(gamma_t)] * (1 - 0.35 t (1 - steady))
                                            + LEG_W g min(left, 3) - CALM_W c dd90 - break-risk penalties(s)
Search, per account type: one shared archive of evaluated printers (256 weekly-step histories, base + stress, common to all);
each cell's champion = the archive member with the highest utility that its tier allows; every generation mutates the
current champions (tier-preserving) and evaluates the kids on the GPU. Next account type starts from the last one's champions.
Validate: each account's top 2 per cell re-run on 600 fresh histories; cells re-picked on fresh stats, then smoothed (a cell takes
a neighbour's printer when it is within TIE of its best), so the sliders move between few, stable printers.
Usage: python3 printer/atlas.py search  (resumes; RESTART=1 starts over) ->  results/printer_atlas_archive.json
       python3 printer/atlas.py validate -> results/printer_atlas.json
       python3 printer/atlas.py horizons -> results/printer_horizons.json (15-50 year stats per account; used by printer/app)"""
import os, sys, json, time, itertools, numpy as np, torch
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
MODE = sys.argv[1] if len(sys.argv) > 1 else "search"; sys.argv = [sys.argv[0]]
import money_printer as mp, search as se
from dataclasses import replace
OUT = os.path.join(ROOT, "..", "results")
LEG_W = 0.012                                 # 1x start left after 40 yrs ~ 0.016/yr of income at a 2% real discount; bequests count a bit less
CALM_W = 0.10                                 # 10 points less bad-case drop ~ worth 1%/yr of income at the calm end
LEVELS = 7; TIERS = 5; STEP = 5; YEARS = 40
GAMMA = np.array([1.5, 2.0, 2.75, 3.5, 4.5, 6.0, 8.0])                  # steady slider -> risk aversion over income
TAXES = {"roth": "none (IRA/Roth)", "taxable_low": "retiree, not working", "taxable_mid": "middle bracket"}
# simplicity tiers: max funds, max leveraged %, K-1 funds allowed
TIER = [dict(n=3, lev=0, k1=False, name="Starter"), dict(n=4, lev=0, k1=False, name="Simple"), dict(n=5, lev=5, k1=False, name="Standard"),
        dict(n=7, lev=15, k1=False, name="Advanced"), dict(n=9, lev=25, k1=True, name="Expert")]
K1 = {"UUPSIM", "UGLSIM"}
POP = int(os.environ.get("POP", "512")); PATHS = int(os.environ.get("PATHS", "256")); GENS = int(os.environ.get("GENS", "30"))
FRESH = int(os.environ.get("FRESH", "600")); THROTTLE = float(os.environ.get("THROTTLE", "0"))  # idle THROTTLE x busy time between GPU batches (laptop heat)
TIE = float(os.environ.get("TIE", "0.0004"))

def tier_of(a):
    n = len(a); lev = sum(w for t, w in a.items() if t in se.LEV); k1 = any(t in K1 for t in a)
    for i, T in enumerate(TIER):
        if n <= T["n"] and lev <= T["lev"] and (T["k1"] or not k1): return i
    return TIERS

def ok(a, tier): return se.valid(a) and tier_of(a) <= tier

def norm100(w):
    """Integer weights summing to 100 with every weight in [1, 35] (largest-remainder), or None."""
    tot = sum(w.values()); x = {t: v * 100 / tot for t, v in w.items()}
    for _ in range(10): x = {t: min(v, 35.0) for t, v in x.items()}; s = sum(x.values()); x = {t: v * 100 / s for t, v in x.items()}
    f = {t: int(v) for t, v in x.items()}; rem = 100 - sum(f.values())
    for t in sorted(x, key=lambda t: -(x[t] - f[t]))[:rem]: f[t] += 1
    f = {t: v for t, v in f.items() if v >= 1}
    return f if sum(f.values()) == 100 and max(f.values()) <= 35 else None

SETTINGS = lambda p: (p.base, p.skim, p.bucket_months, p.cut_below, p.cut_to)
def key(p): return (tuple(sorted(p.alloc.items())),) + tuple(None if v is None else round(float(v), 4) for v in SETTINGS(p))

def mutate(p, rng, tier):
    U = [u for u in se.UNIVERSE if TIER[tier]["k1"] or u not in K1]
    for _ in range(60):
        q = replace(p, alloc=dict(p.alloc)); r = rng.random()
        if r < 0.45:                                                           # shift weight between funds (new fund only if room)
            a = rng.choice(list(q.alloc)); b = rng.choice(U); d = int(rng.choice([1, 2, 3, 5]))
            if a == b or q.alloc[a] < d or (b not in q.alloc and len(q.alloc) >= TIER[tier]["n"] and q.alloc[a] != d): continue
            q.alloc[a] -= d; q.alloc[b] = q.alloc.get(b, 0) + d
            if q.alloc[a] == 0: del q.alloc[a]
        elif r < 0.6:                                                          # swap one fund for another
            a = rng.choice(list(q.alloc)); b = rng.choice(U)
            if b in q.alloc: continue
            q.alloc[b] = q.alloc.pop(a)
        else:
            k = rng.integers(6)
            if k == 0: q.base = float(np.clip(q.base + rng.choice([-0.25, 0.25]), 2.5, 7.0))
            elif k == 1:
                if q.skim is None: q.skim = 0.4
                elif rng.random() < 0.15: q.skim = None                       # no bonus print at all
                else: q.skim = float(np.clip(q.skim + rng.choice([-0.05, 0.05]), 0.05, 1.0))
            elif k == 2: q.bucket_months = int(np.clip(q.bucket_months + rng.choice([-12, 12]), 12, 60))
            elif k == 3: q.cut_below = float(np.clip(q.cut_below + rng.choice([-0.05, 0.05]), 0.5, 0.9))
            elif k == 4: q.cut_to = float(np.clip(q.cut_to + rng.choice([-0.05, 0.05]), 0.5, 1.0))
            else: q.base = float(np.clip(q.base + rng.choice([-0.5, 0.5]), 2.5, 7.0))
        if ok(q.alloc, tier): return q
    return p

def seeds(rng):
    """Starting pool: earlier search finalists and lineup portfolios, pruned into every tier, plus random small portfolios."""
    allocs = []
    for m in ("retiree", "balanced", "max_print", "fortress"):
        f = os.path.join(OUT, f"printer_search_{m}.json")
        if os.path.exists(f): allocs += [(r["printer"]["alloc"], r["printer"]) for r in json.load(open(f))]
    for n, v in json.load(open(os.path.join(OUT, "portfolios.json"))).items():
        if all(t in se.UNIVERSE for t in v["alloc"]): allocs.append((v["alloc"], None))
    core = ["VBRSIM", "VTISIM", "DBMFSIM", "KMLMSIM", "GLDSIM", "GDESIM", "IEISIM", "IEFSIM", "SHYSIM", "XLVSIM", "XLPSIM", "BNDSIM", "SPMOSIM", "VTVSIM", "NTSXSIM", "RSSBSIM", "TLTSIM", "XLUSIM"]
    for _ in range(300):                                                       # random 3-5 fund mixes
        k = int(rng.integers(3, 6)); ts = rng.choice(core, k, replace=False); allocs.append(({t: float(rng.uniform(10, 40)) for t in ts}, None))
    pool, seen = [], set()
    def add(a, q):
        a = norm100(a) if a else None
        if not a or not se.valid(a): return
        st = q or {}
        for base, skim in ((st.get("base", 4.5), st.get("skim", 0.35)), (float(rng.choice([3.5, 4, 4.5, 5, 5.5])), [0.25, 0.4, 0.6, None][int(rng.integers(4))])):
            p = mp.Printer("seed", a, base=float(base), skim=skim, bucket_months=int(st.get("bucket_months", 36)), cut_below=float(st.get("cut_below", 0.7)), cut_to=float(st.get("cut_to", 0.8)))
            if key(p) not in seen: seen.add(key(p)); pool.append(p)
    for a, q in allocs:
        a = {t: float(w) for t, w in a.items()}; add(a, q)
        nolev = {t: w for t, w in a.items() if t not in se.LEV and t not in K1}
        for k in (3, 4, 5, 7):                                                 # pruned into the smaller tiers
            src = nolev if k <= 5 else {t: w for t, w in a.items() if t not in K1}
            top = dict(sorted(src.items(), key=lambda x: -x[1])[:k])
            if len(top) >= 2: add(top, q)
    return pool[:int(os.environ.get("SEEDS_MAX", "100000"))]

# ------------------------------------------------------------------ stats per printer (vectors the cell utilities are built from)
def maxdd(yreal):                                                              # (P, Y) year-end real values -> max drop from the high
    y = np.concatenate([np.ones((yreal.shape[0], 1)), yreal], 1); return (1 - y / np.maximum.accumulate(y, 1)).max(1)

def stats(rb, rs, c):
    sb, ss = rb["spend"][c], rs["spend"][c]
    P, M = sb.shape; yrs = sb[:, :(M // 12) * 12].reshape(P, -1, 12).sum(2)
    return dict(ce_b=[float(se.ce(sb, gamma=g)) for g in GAMMA], ce_s=[float(se.ce(ss, gamma=g)) for g in GAMMA],
                steady=float(np.mean(np.abs(np.diff(yrs, axis=1)) / np.maximum(yrs[:, :-1], 1e-9) < 0.25)),
                left=float(np.median(rb["real_end"][c] + rb["bucket_end"][c])), dd90=float(np.percentile(maxdd(rb["yreal"][c]), 90)),
                dry_b=float(rb["dead"][c].mean()), dry_s=float(rs["dead"][c].mean()), lose=float((rb["real_end"][c] < 1).mean()), cut=float(rb["cut"][c].mean()))

def evaluate(printers, IDX, tax, chunk=512):
    out = []
    for i in range(0, len(printers), chunk):
        pp = [replace(p, tax=tax) for p in printers[i:i + chunk]]
        rb = mp.simulate(pp, IDX, step=STEP); rs = mp.simulate(pp, IDX, step=STEP, trend_haircut=0.02)
        out += [stats(rb, rs, c) for c in range(len(pp))]
    return out

# ------------------------------------------------------------------ cell utilities
LV = np.linspace(0, 1, LEVELS)
def utilities(S, dev=mp.DEV):
    """S: list of stats dicts -> tensor U (A, s, t, g, c) of cell utilities (tiers applied separately)."""
    f = lambda k: torch.tensor([x[k] for x in S], device=dev, dtype=torch.float32)
    ceb = torch.tensor([x["ce_b"] for x in S], device=dev); ces = torch.tensor([x["ce_s"] for x in S], device=dev)          # (A, t)
    L = torch.tensor(LV, device=dev, dtype=torch.float32)
    ws = 0.2 + 0.6 * L                                                                                                        # (s,)
    core = (1 - ws)[None, :, None] * ceb[:, None, :] + ws[None, :, None] * ces[:, None, :]                                    # (A, s, t)
    core = core * (1 - 0.35 * L[None, None, :] * (1 - f("steady"))[:, None, None])
    dry_cap = 0.02 * (0.05 ** L); lose_cap = 0.25 - 0.20 * L; cut_cap = 0.35 - 0.30 * L                                       # caps tighten with safety
    pen = 2 * (f("dry_b")[:, None] - dry_cap).clamp(min=0) + (f("dry_s")[:, None] - 3 * dry_cap).clamp(min=0) \
        + 0.2 * (f("lose")[:, None] - lose_cap).clamp(min=0) + 0.1 * (f("cut")[:, None] - cut_cap).clamp(min=0)                # (A, s)
    leg = LEG_W * L[None, :] * f("left").clamp(max=3)[:, None]                                                                # (A, g)
    calm = CALM_W * L[None, :] * f("dd90")[:, None]                                                                             # (A, c)
    return (core - pen[:, :, None])[:, :, :, None, None] + leg[:, None, None, :, None] - calm[:, None, None, None, :]

def champions(S, tiers, topk=1):
    """Best archive index per cell (tier, s, t, g, c); topk > 1 also returns runners-up (distinct indices)."""
    U = utilities(S); tt = torch.tensor(tiers, device=mp.DEV); best = []
    for k in range(TIERS):
        Uk = torch.where((tt <= k)[:, None, None, None, None], U, torch.full_like(U, -1e9))
        best.append(torch.topk(Uk, min(topk, Uk.shape[0]), dim=0).indices if topk > 1 else Uk.argmax(0))
    return torch.stack(best).cpu().numpy(), U

def search(tax_key, start, rng, IDX):
    tax = TAXES[tax_key]; t0 = time.time()
    archive = {}                                                               # key -> (printer, stats, tier)
    def add_all(pp):
        pp = [p for p in pp if key(p) not in archive]; pp = list({key(p): p for p in pp}.values())
        for p, s in zip(pp, evaluate(pp, IDX, tax)): archive[key(p)] = (p, s, tier_of(p.alloc))
    add_all(start)
    for gen in range(1, GENS + 1):
        keys = list(archive); S = [archive[k][1] for k in keys]; tiers = [archive[k][2] for k in keys]
        best, _ = champions(S, tiers); flat = best.reshape(-1); uniq, wins = np.unique(flat, return_counts=True)
        kids, tries = [], 0
        while len(kids) < POP and tries < 20 * POP:
            tries += 1
            i = uniq[rng.integers(len(uniq))] if rng.random() < 0.5 else rng.choice(uniq, p=wins / wins.sum())
            p, _, tier = archive[keys[i]]; q = p
            for _ in range(int(rng.integers(1, 4))): q = mutate(q, rng, tier)
            if key(q) not in archive: kids.append(q)
        add_all(kids)
        print(f"  [{tax_key}] gen {gen:2d} ({time.time()-t0:5.0f}s) archive {len(archive)} | distinct champions {len(uniq)} | most cells: "
              + " ".join(f"{t.replace('SIM','')}{w}" for t, w in sorted(archive[keys[uniq[wins.argmax()]]][0].alloc.items(), key=lambda x: -x[1])), flush=True)
    return archive

def pdict(p): return dict(alloc=p.alloc, base=p.base, skim=p.skim, bucket_months=p.bucket_months, cut_below=p.cut_below, cut_to=p.cut_to)
def pload(d): return mp.Printer("atlas", {t: int(w) for t, w in d["alloc"].items()}, base=d["base"], skim=d["skim"], bucket_months=int(d["bucket_months"]), cut_below=d["cut_below"], cut_to=d["cut_to"])

def smooth(choice, U, cand_tiers, tie=TIE, passes=4):
    """choice: (TIERS, s,t,g,c) archive indices; U: (A, s,t,g,c) utilities. A cell switches to the printer most common among its
    neighbours (same tier) when that printer is allowed in the tier and within `tie` of the cell's best utility."""
    ch = choice.copy(); Un = U.cpu().numpy(); tiers = np.array(cand_tiers)
    for _ in range(passes):
        changed = 0
        for k in range(TIERS):
            for cell in itertools.product(range(LEVELS), repeat=4):
                best = Un[(ch[k][cell],) + cell]; votes = {}
                for ax in range(4):
                    for d in (-1, 1):
                        nb = list(cell); nb[ax] += d
                        if 0 <= nb[ax] < LEVELS: j = ch[k][tuple(nb)]; votes[j] = votes.get(j, 0) + 1
                for j, _ in sorted(votes.items(), key=lambda x: -x[1]):
                    if j != ch[k][cell] and tiers[j] <= k and Un[(j,) + cell] >= best - tie and votes[j] > votes.get(ch[k][cell], 0):
                        ch[k][cell] = j; changed += 1; break
        if not changed: break
    return ch


HORIZONS = (15, 20, 25, 30, 35, 40, 45, 50)                                    # years of retirement the app can plan for (age -> 100)
def horizon_stats(rb, rs, c, H):
    """Display stats over the first H years of the same histories (one long simulation serves every horizon)."""
    P = rb["spend"][c].shape[0]; yrs = rb["spend"][c][:, :H * 12].reshape(P, H, 12).sum(2); syr = rs["spend"][c][:, :H * 12].reshape(P, H, 12).sum(2)
    avg, savg, early = yrs.mean(1), syr.mean(1), yrs[:, :min(10, H)].mean(1)
    yr, yb, ym = rb["yreal"][c][:, :H], rb["ybucket"][c][:, :H], rb["ymult"][c][:, :H]; dd = maxdd(yr)
    return dict(typical=np.median(avg), bad=np.percentile(avg, 10), early=np.median(early), early_bad=np.percentile(early, 10),
                lean=np.percentile(rb["spend"][c][:, :H * 12], 10) * 12, never_cut=1 - (ym < 0.999).any(1).mean(),
                steady=np.mean(np.abs(np.diff(yrs, axis=1)) / np.maximum(yrs[:, :-1], 1e-9) < 0.25), lose=(yr[:, -1] < 1).mean(), dip70=(yr.min(1) < 0.7).mean(),
                dry=(yr[:, -1] <= 1e-6).mean(), left=np.median(yr[:, -1] + yb[:, -1]), dd50=np.median(dd), dd90=np.percentile(dd, 90),
                stress_typical=np.median(savg), stress_bad=np.percentile(savg, 10), stress_dry=(rs["yreal"][c][:, H - 1] <= 1e-6).mean(),
                no_bonus_10y=np.mean(yrs[:, :10].max(1) <= yrs[:, :10].min(1) * 1.001))
HFIELDS = ("typical", "bad", "early", "early_bad", "lean", "never_cut", "steady", "lose", "dip70", "dry", "left", "dd50", "dd90", "stress_typical", "stress_bad", "stress_dry", "no_bonus_10y")

def display_stats(r_b, r_s, c, p):
    s = mp.score(r_b, c); st = mp.score(r_s, c); y = r_b["yreal"][c]; dd = maxdd(y)
    return dict(base=p.base / 100, typical=s["print_typical"], bad=s["print_bad"], lean=s["print_lean_month"], early=s["print_y1_10_typ"],
                early_bad=s["print_y1_10_bad"], never_cut=s["base_never_cut"], steady=s["steady"], lose=s["lose_value"], dip70=s["deep_dip"], dry=s["run_dry"],
                left=s["left_typical"], dd50=float(np.median(dd)), dd90=float(np.percentile(dd, 90)), stress_typical=st["print_typical"], stress_bad=st["print_bad"],
                stress_dry=st["run_dry"], no_bonus_10y=s["no_bonus_first_10y"], tax=s["tax_per_year"], rebal=s["rebalances_per_year"])

if __name__ == "__main__":
    rng = np.random.default_rng(2026)
    if MODE == "search":
        IDX = mp.make_idx(PATHS, YEARS, step=STEP, seed=101); start = seeds(rng)
        fa = os.path.join(OUT, "printer_atlas_archive.json")                  # resume: account types already searched are kept
        res = json.load(open(fa)) if os.path.exists(fa) and not os.environ.get("RESTART") else {}
        print(f"Printer Atlas search: {LEVELS}^4 preference cells x {TIERS} tiers, pop {POP}, {GENS} generations, {PATHS} histories; {len(start)} seed printers", flush=True)
        for tk in TAXES:
            if tk in res:
                start = [pload(r["printer"]) for r in res[tk]] + start[:256]; print(f"  [{tk}] already searched, resuming after it", flush=True); continue
            arch = search(tk, start, rng, IDX)
            keys = list(arch); S = [arch[k][1] for k in keys]; tiers = [arch[k][2] for k in keys]
            top, _ = champions(S, tiers, topk=3); keep = sorted(set(top.reshape(-1).tolist()))
            res[tk] = [dict(printer=pdict(arch[keys[i]][0]), tier=arch[keys[i]][2], **arch[keys[i]][1]) for i in keep]
            start = [arch[keys[i]][0] for i in keep] + start[:256]                  # next account type starts from these
            json.dump(res, open(os.path.join(OUT, "printer_atlas_archive.json"), "w"), default=float)
            print(f"  [{tk}] kept {len(keep)} champions/runners-up", flush=True)
    elif MODE == "horizons":                                                   # every validated candidate, every horizon, every account type
        A = json.load(open(os.path.join(OUT, "printer_atlas.json"))); cands = [pload(dict(p, bucket_months=p["bucket_months"])) for p in A["printers"]]
        IDX = mp.make_idx(FRESH, max(HORIZONS), step=STEP, seed=909); out = dict(horizons=list(HORIZONS), fields=list(HFIELDS), paths=FRESH, accounts={})
        print(f"horizons: {len(cands)} printers x {len(TAXES)} account types x {len(HORIZONS)} horizons on {FRESH} fresh {max(HORIZONS)}-year histories", flush=True)
        for tk, tax in TAXES.items():
            t0 = time.time(); acc = {str(H): [] for H in HORIZONS}
            for i in range(0, len(cands), 256):
                pp = [replace(p, tax=tax) for p in cands[i:i + 256]]
                tb = time.time(); rb = mp.simulate(pp, IDX, step=STEP); rs = mp.simulate(pp, IDX, step=STEP, trend_haircut=0.02)
                for c in range(len(pp)):
                    for H in HORIZONS: st = horizon_stats(rb, rs, c, H); acc[str(H)].append([round(float(st[f]), 4) for f in HFIELDS])
                time.sleep(THROTTLE * (time.time() - tb))
            out["accounts"][tk] = acc; print(f"  [{tk}] {time.time()-t0:.0f}s", flush=True)
        json.dump(out, open(os.environ.get("HORIZONS_OUT", os.path.join(OUT, "printer_horizons.json")), "w"), separators=(",", ":"))
        print("done", flush=True)
    elif MODE == "validate":
        arch = json.load(open(os.path.join(OUT, "printer_atlas_archive.json"))); IDX = mp.make_idx(FRESH, YEARS, step=STEP, seed=909)
        allp = {}; out = dict(levels=LEVELS, tiers=TIER, gamma=GAMMA.tolist(), paths=FRESH, accounts={}, printers=[])
        for tk, rows in arch.items():                                          # each account's top 2 per cell (search stats, final weights);
            top, _ = champions(rows, [r["tier"] for r in rows], topk=2)        # every account type then re-scores all of them
            for i in sorted(set(top.reshape(-1).tolist())): allp.setdefault(json.dumps(rows[i]["printer"], sort_keys=True), pload(rows[i]["printer"]))
        cands = list(allp.values()); print(f"validate {len(cands)} printers x {len(TAXES)} account types on {FRESH} fresh histories", flush=True)
        for tk, tax in TAXES.items():
            t0 = time.time(); S, D = [], []
            for i in range(0, len(cands), 256):
                pp = [replace(p, tax=tax) for p in cands[i:i + 256]]
                tb = time.time(); rb = mp.simulate(pp, IDX, step=STEP); rs = mp.simulate(pp, IDX, step=STEP, trend_haircut=0.02)
                S += [stats(rb, rs, c) for c in range(len(pp))]; D += [display_stats(rb, rs, c, p) for c, p in enumerate(pp)]
                time.sleep(THROTTLE * (time.time() - tb))
            tiers = [tier_of(p.alloc) for p in cands]; best, U = champions(S, tiers); ch = smooth(best, U, tiers)
            used = sorted(set(ch.reshape(-1).tolist())); out["accounts"][tk] = dict(tax=tax, cells=ch.tolist(), stats=D)   # stats of every candidate (frontier view)
            print(f"  [{tk}] {time.time()-t0:.0f}s | {len(set(best.reshape(-1).tolist()))} distinct champions -> {len(used)} after smoothing", flush=True)
        out["printers"] = [dict(pdict(p), tier=tier_of(p.alloc)) for p in cands]
        json.dump(out, open(os.environ.get("ATLAS_OUT", os.path.join(OUT, "printer_atlas.json")), "w"), default=float)
        print("done", flush=True)
