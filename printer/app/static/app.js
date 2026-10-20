/* Money Printer Forge (local app).
   1. Your situation (age -> years to plan for, dollars by tax treatment, bracket) mixes each printer's stats.
   2. The Pareto frontier is computed for that mix: printers no other printer beats on every measure.
   3. Your values (importance sliders) weight plain measures; the pick is the frontier printer with the highest weighted score.
      Only frontier printers can be picked. Alternatives are the best frontier printers that do clearly better on one value. */
(async () => {
const $ = id => document.getElementById(id);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt$ = x => (x < 0 ? "−$" : "$") + Math.round(Math.abs(x)).toLocaleString("en-US");
const trim = s => (s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s);
const fmtK = x => { const a = Math.abs(x), sg = x < 0 ? "−" : "";
  return a >= 1e9 ? `${sg}$${trim((a / 1e9).toFixed(a >= 1e10 ? 0 : 2))}B` : a >= 1e6 ? `${sg}$${trim((a / 1e6).toFixed(a >= 1e7 ? 0 : 2))}M` : a >= 1e3 ? `${sg}$${Math.round(a / 1e3)}k` : fmt$(x); };
const pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function toast(msg, ms = 2600) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), ms); }
async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`); return j;
}

const D = await (await fetch("/api/atlas")).json();
const F = Object.fromEntries(D.fields.map((f, i) => [f, i]));
const CLASS_ORDER = ["stocks", "boost", "trend", "gold", "bonds"];
const CLASS_NAME = { stocks: "Stocks", boost: "Leveraged / stacked", trend: "Trend-following", gold: "Gold", bonds: "Bonds & cash" };
const MONEY = ["typical", "bad", "early", "early_bad", "lean", "stress_typical", "stress_bad", "left"];

/* ---------- values: what the sliders weight (each part is a measure, + = more is better) ---------- */
const VALUES = [
  { k: "now", label: "A bigger paycheck now", parts: [["early", .7], ["typical", .3]] },
  { k: "bad", label: "Still fine in bad markets", parts: [["early_bad", .4], ["stress_typical", .3], ["bad", .3]] },
  { k: "steady", label: "The same amount every month", parts: [["steady", .6], ["never_cut", .4]] },
  { k: "last", label: "Never running out", parts: [["dry", .6, -1], ["lose", .4, -1]] },
  { k: "calm", label: "A calm balance", parts: [["dd90", 1, -1]] },
  { k: "legacy", label: "Leaving money to family", parts: [["left", 1]] },
  { k: "simple", label: "Keeping it simple", parts: [["simplicity", 1, -1]] },
];
const PRESETS = [
  { n: "Biggest paycheck", v: [100, 30, 20, 50, 10, 0, 20] }, { n: "Balanced", v: [60, 60, 40, 70, 40, 20, 30] },
  { n: "Sleep well", v: [40, 80, 80, 100, 90, 20, 40] }, { n: "Family first", v: [40, 60, 40, 80, 50, 100, 30] },
  { n: "Keep it simple", v: [50, 50, 40, 70, 40, 20, 100] },
];
const words = v => v <= 2 ? "Doesn't matter" : v < 25 ? "A little" : v < 50 ? "Somewhat" : v < 75 ? "A lot" : "Most";

/* ---------- state (mirrored in the URL so a link reopens the same pick) ---------- */
let S = { age: 60, free: 100000, deferred: 150000, taxable: 250000, bracket: "low", imp: PRESETS[1].v.slice(), pin: null, tab: "choose",
          mode: "living", start: "1972", rebal: "Printer rule", real: false, logy: true, roll: 5, compare: ["b0"] };
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1)); if (!h.has("a")) return;
  const n = k => (h.has(k) ? +h.get(k) : null);
  S.age = n("a") ?? S.age; S.free = n("f") ?? S.free; S.deferred = n("d") ?? S.deferred; S.taxable = n("t") ?? S.taxable;
  S.bracket = h.get("b") === "mid" ? "mid" : "low"; if (h.has("v")) S.imp = h.get("v").split(",").map(Number).slice(0, VALUES.length);
  S.pin = h.has("p") ? +h.get("p") : null; if (h.has("tab")) S.tab = h.get("tab");
}
function writeHash() {
  const h = new URLSearchParams({ a: S.age, f: S.free, d: S.deferred, t: S.taxable, b: S.bracket, v: S.imp.join(","), tab: S.tab });
  if (S.pin != null) h.set("p", S.pin); history.replaceState(null, "", "#" + h.toString());
}
readHash();

/* ---------- situation -> mixed stats for every printer ---------- */
let M = null;                                                                   // derived model for the current situation
function horizon() { return Math.max(D.horizons[0], Math.min(D.horizons[D.horizons.length - 1], Math.round((100 - S.age) / 5) * 5)); }
function total() { return Math.max(0, S.free) + Math.max(0, S.deferred) + Math.max(0, S.taxable); }
function derive() {
  const H = horizon(), tot = total() || 1, f = S.free / tot, d = S.deferred / tot, x = S.taxable / tot, br = D.brackets[S.bracket], it = br.income_tax;
  const R = D.accounts.roth.stats[H], X = D.accounts[br.taxable].stats[H], keep = f + d * (1 - it) + x;
  const stats = D.printers.map((p, i) => {
    const o = {};
    for (const k of D.fields) { const r = R[i][F[k]], t = X[i][F[k]]; o[k] = MONEY.includes(k) ? (f + d * (1 - it)) * r + x * t : (f + d) * r + x * t; }
    o.simplicity = p.alloc.length + (p.levered > 0 ? 2 : 0) + (p.k1 ? 2 : 0) + p.levered / 10; o.funds = p.alloc.length; o.base = p.base / 100 * keep;
    return o;
  });
  // Pareto frontier for this situation (rounded to differences a person would notice; only printers that run dry in <= 2% of histories)
  const OBJ = [["early", 1, .001], ["typical", 1, .001], ["bad", 1, .001], ["stress_typical", 1, .001], ["never_cut", 1, .01], ["steady", 1, .01],
               ["left", 1, .05], ["lose", -1, .01], ["dd90", -1, .01], ["dry", -1, .002], ["simplicity", -1, 1]];
  const ok = stats.map((s, i) => i).filter(i => stats[i].dry <= 0.02);
  const V = ok.map(i => OBJ.map(([k, sg, q]) => sg * Math.round(stats[i][k] / q)));
  const front = [];
  for (let a = 0; a < V.length; a++) {
    let dom = false; const va = V[a];
    for (let b = 0; b < V.length && !dom; b++) {
      if (a === b) continue; const vb = V[b]; let ge = true, gt = false;
      for (let j = 0; j < va.length; j++) { if (vb[j] < va[j]) { ge = false; break } if (vb[j] > va[j]) gt = true; }
      dom = ge && gt;
    }
    if (!dom) front.push(ok[a]);
  }
  // value scores in [0, 1] across the frontier
  const rng = {}; for (const k of [...D.fields, "simplicity"]) { const xs = front.map(i => stats[i][k]); rng[k] = [Math.min(...xs), Math.max(...xs)]; }
  const norm = (i, k, sg = 1) => { const [lo, hi] = rng[k]; const u = hi > lo ? (stats[i][k] - lo) / (hi - lo) : .5; return sg > 0 ? u : 1 - u; };
  const score = {}; for (const i of front) score[i] = VALUES.map(v => v.parts.reduce((a, [k, w, sg]) => a + w * norm(i, k, sg || 1), 0));
  M = { H, tot, f, d, x, it, keep, stats, front, score, rng, norm, frontSet: new Set(front) };
}
function utility(i) { const w = S.imp, s = M.score[i], tw = w.reduce((a, b) => a + b, 0) || 1; return s.reduce((a, v, j) => a + v * w[j], 0) / tw; }
function ranked() { return M.front.slice().sort((a, b) => utility(b) - utility(a) || M.stats[a].simplicity - M.stats[b].simplicity); }
function current() { return S.pin != null && M.frontSet.has(S.pin) ? S.pin : ranked()[0]; }
function alternatives(cur) {
  const out = [], used = new Set([cur]), order = VALUES.map((v, j) => j).sort((a, b) => S.imp[b] - S.imp[a]);
  const rk = ranked();
  for (const j of order) {
    const better = rk.find(i => !used.has(i) && M.score[i][j] >= M.score[cur][j] + 0.08);
    if (better != null) { out.push({ i: better, j }); used.add(better); }
    if (out.length === 3) break;
  }
  return out;
}

/* ---------- controls ---------- */
const money = id => { const el = $(id); el.value = fmt$(S[id.slice(2)]); el.addEventListener("change", () => {
  const raw = el.value.trim().toLowerCase(), m = raw.endsWith("m") ? 1e6 : raw.endsWith("k") ? 1e3 : 1; S[id.slice(2)] = Math.max(0, (+raw.replace(/[^0-9.]/g, "") || 0) * m);
  el.value = fmt$(S[id.slice(2)]); S.pin = null; situationChanged(); }); el.addEventListener("keydown", e => e.key === "Enter" && el.blur()); };
["m-free", "m-deferred", "m-taxable"].forEach(money);
$("age").value = S.age; $("age").addEventListener("change", () => { S.age = Math.max(30, Math.min(95, +$("age").value || 60)); $("age").value = S.age; S.pin = null; situationChanged(); });
for (const [k, b] of Object.entries(D.brackets)) {
  const btn = document.createElement("button"); btn.textContent = b.label; btn.dataset.k = k; btn.onclick = () => { S.bracket = k; S.pin = null; situationChanged(); }; $("bracket").append(btn);
}
const valEl = $("values");
VALUES.forEach((v, j) => {
  const w = document.createElement("div"); w.className = "value";
  w.innerHTML = `<div class="head"><b id="vl-${v.k}">${v.label}</b><span id="vw-${v.k}"></span></div><input type="range" id="v-${v.k}" min="0" max="100" step="1" aria-labelledby="vl-${v.k}">`;
  valEl.append(w); const r = w.querySelector("input"); r.value = S.imp[j];
  r.addEventListener("input", () => { S.imp[j] = +r.value; S.pin = null; paintSliders(); scheduleRender(); });
});
PRESETS.forEach(p => { const b = document.createElement("button"); b.textContent = p.n; b.onclick = () => { S.imp = p.v.slice(); S.pin = null; VALUES.forEach((v, j) => ($("v-" + v.k).value = S.imp[j])); paintSliders(); render(); }; $("presets").append(b); });
function paintSliders() { VALUES.forEach((v, j) => { const r = $("v-" + v.k); r.style.setProperty("--fill", S.imp[j] + "%"); $("vw-" + v.k).textContent = words(S.imp[j]); r.setAttribute("aria-valuetext", words(S.imp[j])); }); }
let raf = null; function scheduleRender() { if (!raf) raf = requestAnimationFrame(() => { raf = null; render(); }); }
let sitT = null; function situationChanged() { clearTimeout(sitT); sitT = setTimeout(() => { derive(); render(); }, 60); }

/* tabs */
function setTab(t) {
  S.tab = t; for (const k of ["choose", "backtest", "frontier"]) { $("tab-" + k).setAttribute("aria-selected", k === t); $("view-" + k).hidden = k !== t; }
  writeHash(); if (t === "backtest") runBacktest(); if (t === "frontier") FR.draw(); if (t === "choose") Charts.redraw();
}
for (const k of ["choose", "backtest", "frontier"]) $("tab-" + k).onclick = () => setTab(k);

/* ---------- plain-language descriptions ---------- */
const mix = p => p.alloc.map(([t, w]) => `${t} ${w}`).join(" · ");
const spec = (i, name) => { const p = D.printers[i]; return { name, alloc: p.alloc, base: p.base, skim: p.skim, bucket: p.bucket, cut_below: p.cut_below, cut_to: p.cut_to }; };
function rules(p) {
  const tot = M.tot, base = p.base / 100, out = [];
  out.push(["Monthly", `Sell ${fmt$(base * tot / 12)} (${p.base}% of the starting value a year) from whichever funds are furthest above target. Raise it with inflation every January.`]);
  out.push(["Bonus", p.skim != null && p.skim < 1.95 ? `Each January, if the accounts are above ${Math.round((1 + p.skim) * 100)}% of their inflation-adjusted start, move the extra to a cash bucket (T-bills or high-yield savings) and spend 1/${p.bucket} of it each month.` : "None: everything above the paycheck stays invested."]);
  if (p.cut_to < 0.999 && p.cut_below > 0) out.push(["Brake", `If a January finds the accounts below ${Math.round(p.cut_below * 100)}% of their inflation-adjusted start, cut the paycheck to ${Math.round(p.cut_to * 100)}% until they are back above 90%.`]);
  out.push(["Upkeep", "Rebalance to target when any fund drifts more than 6 points, at most once a year; any fund at twice its target, rebalance that day."]);
  const tx = []; if (M.d > 0) tx.push("tax-deferred withdrawals are taxed as income"); if (M.x > 0) tx.push("in the taxable account sell the highest-cost shares first");
  out.push(["Taxes", tx.length ? tx.join("; ").replace(/^./, c => c.toUpperCase()) + ". Have a tax preparer check each year." : "None: everything is in tax-free accounts."]);
  return out;
}

/* ---------- render: Choose ---------- */
const STAT_ROWS = [
  { h: "Paycheck", rows: [["First 10 years, typical", "early", "$"], ["First 10 years, unlucky (1 in 10)", "early_bad", "$"], ["Whole plan, average", "typical", "$"], ["If trend funds earn 2%/yr less", "stress_typical", "$"]] },
  { h: "Reliability", rows: [["Paycheck never cut", "never_cut", "%"], ["Years within ±25% of the last", "steady", "%"]] },
  { h: "Break risk", rows: [["Runs dry", "dry", "%1", -1], ["Ends below its starting value", "lose", "%", -1], ["Balance drop, bad case (1 in 10)", "dd90", "%", -1]] },
  { h: "Legacy", rows: [["Left at the end, typical", "left", "L"]] },
];
const show = (st, k, t) => t === "$" ? fmt$(st[k] * M.tot / 12) : t === "L" ? fmtK(st[k] * M.tot) : pct(st[k], t === "%1" ? 1 : 0);
let prev = null;
function render() {
  const cur = current(), p = D.printers[cur], st = M.stats[cur];
  document.body.classList.toggle("pinned", S.pin != null);
  $("bracket").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === S.bracket));
  $("total").textContent = fmt$(M.tot);
  $("horizon").textContent = `Planning for ${M.H} years, to age ${S.age + M.H}. ${M.front.length.toLocaleString()} printers are on the frontier for your situation.`;
  paintSliders();
  $("pick-state").textContent = S.pin != null ? "Your choice from the frontier · move a slider to return to the best match" : "Best match on the frontier for your values";
  tween($("amt"), st.early * M.tot / 12);
  $("sticky-amt").textContent = fmt$(st.early * M.tot / 12) + " a month"; $("sticky-sub").textContent = `${p.alloc.length} funds · runs dry ${pct(st.dry, 1)} · bad-case drop ${pct(st.dd90)}`;
  $("lede").textContent = `A typical month in the first 10 years, after tax, in today's dollars. In an unlucky history (1 in 10) the first decade pays ${show(st, "early_bad", "$")}; over the whole ${M.H} years it averages ${show(st, "typical", "$")} a month.`;
  $("facts").innerHTML = [[fmt$(st.base * M.tot / 12), "base paycheck before bonuses"], [pct(st.dry, 1), "chance it runs dry"],
    [pct(st.dd90), "balance drop, bad case"], [fmtK(st.left * M.tot), `left at age ${S.age + M.H}, typical`]]
    .map(([b, s]) => `<div class="fact"><b>${b}</b><span>${s}</span></div>`).join("");
  // why + stat sheet (bars = where it sits on the frontier, longer = better)
  const top = VALUES.map((v, j) => ({ v, j, s: M.score[cur][j] })).sort((a, b) => S.imp[b.j] * (b.s + .2) - S.imp[a.j] * (a.s + .2)).slice(0, 2);
  $("why").textContent = `Of the ${M.front.length.toLocaleString()} frontier printers for you, this one scores best on what you rated most: ` +
    top.map(t => `${t.v.label.toLowerCase()} (better than ${pct(rankOf(cur, t.j))} of them)`).join(" and ") + ".";
  $("stats").innerHTML = STAT_ROWS.map(b => `<div class="block"><h3>${b.h}</h3>` + b.rows.map(([lab, k, t, sg]) =>
    `<div class="stat"><span class="k">${lab}</span><span class="v"><span class="delta" data-k="${k}"></span>${show(st, k, t)}</span><div class="bar"><i style="width:${(6 + 94 * M.norm(cur, k, sg || 1)).toFixed(1)}%"></i></div></div>`).join("") + "</div>").join("");
  if (prev != null && prev !== cur) for (const el of document.querySelectorAll(".delta")) {
    const k = el.dataset.k, row = STAT_ROWS.flatMap(b => b.rows).find(r => r[1] === k), sg = row[3] || 1, dv = st[k] - M.stats[prev][k];
    const isMoney = row[2] === "$" || row[2] === "L", tiny = isMoney ? Math.abs(dv * M.tot / (row[2] === "$" ? 12 : 1)) < 1 : Math.abs(dv) < .005; if (tiny) continue;
    el.textContent = (dv > 0 ? "+" : "−") + (isMoney ? (row[2] === "$" ? fmt$(Math.abs(dv) * M.tot / 12) : fmtK(Math.abs(dv) * M.tot)).replace("$", "$") : (Math.abs(dv) * 100).toFixed(row[2] === "%1" ? 1 : 0) + " pt");
    el.className = "delta show " + (dv * sg > 0 ? "up" : "down");
  }
  clearTimeout(render.fade); render.fade = setTimeout(() => document.querySelectorAll(".delta.show").forEach(e => e.classList.remove("show")), 2200);
  // fund mix
  const sorted = p.alloc.slice().sort((a, b) => CLASS_ORDER.indexOf(D.funds[a[0]][1]) - CLASS_ORDER.indexOf(D.funds[b[0]][1]) || b[1] - a[1]);
  $("alloc").innerHTML = sorted.map(([t, w]) => `<i title="${t} ${w}%" style="flex-grow:${w};background:var(--c-${D.funds[t][1]})"></i>`).join("");
  $("alloc").setAttribute("aria-label", "Fund mix: " + mix(p));
  $("legend").innerHTML = CLASS_ORDER.filter(c => sorted.some(([t]) => D.funds[t][1] === c)).map(c => `<span><i style="background:var(--c-${c})"></i>${CLASS_NAME[c]} ${sorted.filter(([t]) => D.funds[t][1] === c).reduce((a, [, w]) => a + w, 0)}%</span>`).join("");
  $("funds").innerHTML = sorted.map(([t, w]) => `<li><i class="sw" style="background:var(--c-${D.funds[t][1]})"></i><span class="tk">${t}</span><span class="nm">${esc(D.funds[t][0])}</span><span class="w">${w}%</span><span class="d">${fmt$(M.tot * w / 100)}</span></li>`).join("");
  $("rules").innerHTML = rules(p).map(([h, t]) => `<li><b>${h}</b><span>${esc(t)}</span></li>`).join("");
  // alternatives
  const alts = alternatives(cur); ALTS = alts;
  $("alts").innerHTML = alts.length ? alts.map(({ i, j }) => {
    const a = M.stats[i], first = new Set(VALUES[j].parts.map(q => q[0]).concat(j === 6 ? ["funds"] : []));
    const diffs = DIFFS.slice().sort((u, v) => first.has(v[0]) - first.has(u[0]))
      .map(([k, lab, t, sg]) => { const dv = a[k] - st[k]; const tiny = t === "$" ? Math.abs(dv * M.tot / 12) < 5 : t === "L" ? Math.abs(dv * M.tot) < 1000 : t === "n" ? dv === 0 : Math.abs(dv) < .005;
        if (tiny) return ""; const val = t === "$" ? fmt$(Math.abs(dv) * M.tot / 12) + "/mo" : t === "L" ? fmtK(Math.abs(dv) * M.tot) : t === "n" ? Math.abs(dv) : (Math.abs(dv) * 100).toFixed(t === "%1" ? 1 : 0) + " pt";
        return `<li class="${dv * sg > 0 ? "up" : "down"}">${dv > 0 ? "+" : "−"}${val} ${lab}</li>`; }).filter(Boolean).slice(0, 5).join("");
    return `<div class="alt"><div class="eyebrow">More: ${VALUES[j].label.toLowerCase()}</div><div class="a-amt">${fmt$(a.early * M.tot / 12)} <small>a month now</small></div>
      <div class="mix">${esc(mix(D.printers[i]))}</div><ul>${diffs}</ul><div class="acts"><button data-pick="${i}">Choose this</button><button data-cmp="${i}">Compare in backtest</button></div></div>`;
  }).join("") : `<p class="hint">Your pick already leads on everything you rated; no frontier printer does clearly better on any one value.</p>`;
  $("method").textContent = `Stats come from ${D.paths} fresh simulated ${M.H}-year retirements per printer, reshuffled in whole years from 1972–2026 market data (funds, inflation and T-bills move together). ${D.printers.length.toLocaleString()} printers were found by a GPU search and checked on those fresh histories; only the frontier for your situation can be picked.`;
  prev = cur; writeHash(); scheduleFan(); if (S.tab === "frontier") FR.draw(); if (S.tab === "backtest") runBacktest();
}
let ALTS = [];
const DIFFS = [["early", "paycheck now", "$", 1], ["typical", "lifetime average", "$", 1], ["early_bad", "unlucky paycheck", "$", 1], ["stress_typical", "if trend funds lag", "$", 1],
  ["steady", "steady years", "%", 1], ["never_cut", "never cut", "%", 1], ["dry", "runs dry", "%1", -1], ["lose", "ends below start", "%", -1], ["dd90", "bad-case drop", "%", -1],
  ["left", "left at the end", "L", 1], ["funds", "funds", "n", -1]];
function rankOf(i, j) { const s = M.score[i][j]; return M.front.filter(k => M.score[k][j] < s).length / Math.max(1, M.front.length - 1); }
$("alts").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.pick) { S.pin = +b.dataset.pick; render(); }
  if (b.dataset.cmp) { const k = "p" + b.dataset.cmp; if (!S.compare.includes(k)) S.compare = [...S.compare, k].slice(-3); setTab("backtest"); }
});
let tw = null, shown = 0;
function tween(el, to) { const from = shown, t0 = performance.now(), dur = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 350; cancelAnimationFrame(tw);
  const step = t => { const u = dur ? Math.min(1, (t - t0) / dur) : 1, e = 1 - Math.pow(1 - u, 3); shown = from + (to - from) * e; el.textContent = fmt$(shown); if (u < 1) tw = requestAnimationFrame(step); }; tw = requestAnimationFrame(step);
  clearTimeout(tween.done); tween.done = setTimeout(() => { cancelAnimationFrame(tw); shown = to; el.textContent = fmt$(to); }, dur + 60); }

/* ---------- futures fan (server simulation, debounced) ---------- */
let fanT = null, fanKey = null;
function scheduleFan() { clearTimeout(fanT); fanT = setTimeout(loadFan, 450); }
async function loadFan() {
  const cur = current(), key = JSON.stringify([cur, S.free, S.deferred, S.taxable, S.bracket, M.H]); if (key === fanKey) return; fanKey = key;
  $("fan-note").textContent = "Simulating…";
  try {
    const r = await post("/api/fan", { spec: spec(cur, "pick"), mix: { free: S.free, deferred: S.deferred, taxable: S.taxable }, bracket: S.bracket, years: M.H });
    if (key !== fanKey) return; const T = M.tot;
    Charts.fan($("fan-income"), { x: r.years.slice(1), rows: r.income.map(q => q.map(v => v * T / 12)), fmt: v => fmtK(v), height: 230 });
    Charts.fan($("fan-balance"), { x: r.years, rows: r.balance.map(q => q.map(v => v * T)), fmt: v => fmtK(v), height: 230 });
    $("fan-note").textContent = `${r.paths} simulated futures · runs dry in ${pct(r.dry, 1)}`;
    $("fan-legend").innerHTML = `<span><i class="line" style="background:var(--accent)"></i>Typical</span><span><i style="background:var(--band2)"></i>Middle half of futures</span><span><i style="background:var(--band1)"></i>9 in 10 futures</span>`;
  } catch (e) { $("fan-note").textContent = e.message; }
}

/* ---------- Backtest ---------- */
const startSel = $("start"); for (let y = 1972; y <= 2021; y++) startSel.add(new Option(String(y), String(y))); startSel.value = S.start;
startSel.onchange = () => { S.start = startSel.value; runBacktest(); };
$("rebal").value = S.rebal; $("rebal").onchange = () => { S.rebal = $("rebal").value; runBacktest(); };
$("real").checked = S.real; $("real").onchange = () => { S.real = $("real").checked; runBacktest(); };
$("logy").checked = S.logy; $("logy").onchange = () => { S.logy = $("logy").checked; runBacktest(); };
$("mode").onclick = e => { const v = e.target.dataset?.v; if (v) { S.mode = v; runBacktest(); } };
$("roll").onclick = e => { const v = e.target.dataset?.v; if (v) { S.roll = +v; runBacktest(); } };
function compareList() {
  const cur = current(), list = [{ key: "pick", label: "Your pick", spec: spec(cur, "Your pick") }];
  for (const k of S.compare) {
    if (k[0] === "b") { const b = D.benchmarks[+k.slice(1)]; if (b) list.push({ key: k, label: b.name, spec: { ...b } }); }
    if (k[0] === "p") { const i = +k.slice(1); if (i !== cur && D.printers[i]) list.push({ key: k, label: mix(D.printers[i]), spec: spec(i, mix(D.printers[i])) }); }
  }
  return list.slice(0, 4);
}
function paintCompare(list) {
  $("chips").innerHTML = list.map((c, i) => `<span class="chip"><i style="background:${Charts.color(i)}${i === 3 ? ";background:repeating-linear-gradient(90deg,var(--s4) 0 5px,transparent 5px 8px)" : ""}"></i>${esc(c.label)}${c.key === "pick" ? "" : `<button aria-label="Remove ${esc(c.label)}" data-rm="${c.key}">×</button>`}</span>`).join("");
  const add = $("add"); add.innerHTML = ""; add.add(new Option(list.length >= 4 ? "Up to 4 at a time" : "+ Add a comparison", ""));
  if (list.length < 4) {
    D.benchmarks.forEach((b, i) => { if (!S.compare.includes("b" + i)) add.add(new Option(b.name, "b" + i)); });
    ALTS.forEach(({ i, j }) => { if (!S.compare.includes("p" + i)) add.add(new Option(`Alternative: more ${VALUES[j].label.toLowerCase()}`, "p" + i)); });
  }
  add.disabled = list.length >= 4;
}
$("chips").onclick = e => { const k = e.target.dataset?.rm; if (k) { S.compare = S.compare.filter(x => x !== k); runBacktest(); } };
$("add").onchange = e => { const k = e.target.value; if (k) { S.compare = [...S.compare, k]; runBacktest(); } };
let btKey = null;
async function runBacktest() {
  const list = compareList(); paintCompare(list);
  $("mode").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === S.mode));
  $("roll").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", +b.dataset.v === S.roll));
  document.querySelectorAll(".port-only").forEach(el => (el.hidden = S.mode !== "portfolio"));
  $("bt-living").hidden = S.mode !== "living"; $("bt-portfolio").hidden = S.mode !== "portfolio";
  const mixd = { free: S.free, deferred: S.deferred, taxable: S.taxable };
  const key = JSON.stringify([S.mode, S.start, S.rebal, S.real, S.logy, S.roll, list.map(c => c.spec), mixd, S.bracket]); if (key === btKey) return; btKey = key;
  $("bt-status").textContent = "Running the backtest…";
  try {
    if (S.mode === "living") {
      const r = await post("/api/history", { printers: list.map(c => c.spec), mix: mixd, bracket: S.bracket, start: `${S.start}-01-01` }); if (key !== btKey) return;
      drawLiving(r, list);
      $("bt-status").textContent = `${r.start} to ${r.end} · each printer starts with ${fmt$(M.tot)} split across your accounts · daily data, monthly paychecks`;
    } else {
      const r = await post("/api/backtest", { portfolios: list.map(c => ({ name: c.label, alloc: c.spec.alloc })), start: `${S.start}-01-01`, rebalance: S.rebal, real: S.real }); if (key !== btKey) return;
      drawPortfolio(r, list);
      $("bt-status").textContent = `${r.start} to ${r.end} · growth of ${fmt$(M.tot)} with nothing withdrawn · rebalance: ${S.rebal.toLowerCase()}${S.real ? " · inflation-adjusted" : ""}`;
    }
  } catch (e) { $("bt-status").textContent = e.message; }
}
function drawLiving(r, list) {
  const T = M.tot, ser = (k, f) => r.printers.map((p, i) => ({ label: list[i].label, i, data: p[k].map(f) }));
  Charts.line($("c-paid"), { x: r.months, series: ser("paid", v => v * T), fmt: v => fmt$(v), height: 320 });
  Charts.line($("c-bal"), { x: r.dates, series: ser("real", v => Math.max(v * T, 1)), fmt: v => fmtK(v), log: S.logy, height: 320 });
  Charts.line($("c-bdd"), { x: r.dates, series: ser("real_dd", v => v), fmt: v => v.toFixed(0) + "%", height: 240 });
  const rows = [["Paid in total, today's $", s => fmtK(s.total_paid * T)], ["Average a year", s => fmt$(s.avg_year * T)], ["Worst calendar year", s => fmt$(s.worst_year * T)],
    ["Best calendar year", s => fmt$(s.best_year * T)], ["Months with the paycheck cut", s => s.months_cut], ["Lowest balance", s => `${fmtK(s.low_real * T)} (${s.low_date.slice(0, 7)})`],
    ["Balance at the end", s => fmtK(s.end_real * T)], ["Largest balance drop", s => s.max_real_dd.toFixed(1) + "%"], ["Ran dry", s => (s.ran_dry ? "Yes" : "No")]];
  table($("t-living"), list, rows.map(([lab, f]) => [lab, r.printers.map(p => f(p.summary))]));
}
function drawPortfolio(r, list) {
  const T = M.tot / 10000, ser = (k, f) => r.portfolios.map((p, i) => ({ label: list[i].label, i, data: p[k].map(f) }));
  $("growth-sub").textContent = S.real ? "today's dollars" : "nominal dollars";
  Charts.line($("c-growth"), { x: r.dates, series: ser("growth", v => v * T), fmt: v => fmtK(v), log: S.logy, height: 320 });
  Charts.line($("c-dd"), { x: r.dates, series: ser("drawdown", v => v), fmt: v => v.toFixed(0) + "%", height: 240 });
  const k = String(S.roll); Charts.line($("c-roll"), { x: r.dates, series: r.portfolios.map((p, i) => ({ label: list[i].label, i, data: p.rolling[k] || p.dates?.map(() => null) || [] })), fmt: v => v.toFixed(0) + "%", height: 240 });
  Charts.bars($("c-annual"), { groups: r.years, series: r.portfolios.map((p, i) => ({ label: list[i].label, i, data: p.annual })), fmt: v => v.toFixed(0) + "%",
    onHover: (gi, e) => { if (gi == null) { $("bt-status").dataset.hover = ""; return; } $("bt-status").textContent = `${r.years[gi]}: ` + r.portfolios.map((p, i) => `${list[i].label} ${p.annual[gi] == null ? "–" : p.annual[gi].toFixed(1) + "%"}`).join(" · "); } });
  const st = [["Start → end balance", p => `${fmtK(T * 10000)} → ${fmtK(p.stats.end_val * T)}`], ["CAGR", p => p.stats.cagr.toFixed(2) + "%"], ["Standard deviation", p => p.stats.std.toFixed(2) + "%"],
    ["Max drawdown", p => p.stats.max_drawdown.toFixed(1) + "% (" + p.stats.max_dd_date.slice(0, 7) + ")"], ["Longest time under water", p => p.stats.longest_dd_years.toFixed(1) + " yrs"],
    ["Sharpe", p => p.stats.sharpe.toFixed(3)], ["Sortino", p => p.stats.sortino.toFixed(3)], ["Calmar", p => p.stats.calmar.toFixed(3)], ["Ulcer index", p => p.stats.ulcer_index.toFixed(2)],
    ["UPI", p => p.stats.upi.toFixed(2)], ["Best year", p => p.stats.best_year.toFixed(1) + "%"], ["Worst year", p => p.stats.worst_year.toFixed(1) + "%"],
    ["Positive months", p => p.stats.positive_months.toFixed(0) + "%"], ["Worst month", p => p.stats.worst_month.toFixed(1) + "%"]];
  table($("t-stats"), list, st.map(([lab, f]) => [lab, r.portfolios.map(f)]));
}
function table(el, list, rows) {
  el.innerHTML = `<thead><tr><th></th>${list.map((c, i) => `<th><span class="sw2" style="background:${Charts.color(i)}"></span>${esc(c.label.length > 34 ? c.label.slice(0, 32) + "…" : c.label)}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map(([lab, vals]) => `<tr><td>${lab}</td>${vals.map(v => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

/* ---------- Frontier explorer ---------- */
const FR = (() => {
  const DIMS = [
    { k: "early", l: "Paycheck now", g: "Paycheck", t: "$" }, { k: "early_bad", l: "Unlucky", g: "Paycheck", t: "$" }, { k: "typical", l: "Whole plan", g: "Paycheck", t: "$" },
    { k: "stress_typical", l: "Trend −2%/yr", g: "Reliability", t: "$" }, { k: "never_cut", l: "Never cut", g: "Reliability", t: "%" }, { k: "steady", l: "Steady", g: "Reliability", t: "%" },
    { k: "dry", l: "Runs dry", g: "Break risk", t: "%1", lo: true }, { k: "lose", l: "Ends below start", g: "Break risk", t: "%", lo: true }, { k: "dd90", l: "Bad-case drop", g: "Break risk", t: "%", lo: true },
    { k: "left", l: "Left at end", g: "Legacy", t: "L" }, { k: "funds", l: "Funds", g: "Simple", t: "n", lo: true },
  ];
  const pc = $("pc"), sc = $("sc"), tip = $("tip"), pctx = pc.getContext("2d"), sctx = sc.getContext("2d");
  let brush = {}, hover = null, dragging = null, axisX = [], box = {}, pts = [];
  const sel = { x: "dd90", y: "early" };
  const val = (i, d) => M.stats[i][d.k];
  const fmtv = (d, v) => d.t === "$" ? fmt$(v * M.tot / 12) : d.t === "L" ? fmtK(v * M.tot) : d.t === "n" ? String(v) : pct(v, d.t === "%1" ? 1 : 0);
  const ext = d => { const xs = M.front.map(i => val(i, d)); let lo = Math.min(...xs), hi = Math.max(...xs); if (hi - lo < 1e-9) hi = lo + 1; return [lo, hi]; };
  const up = (i, d, e) => { const u = (val(i, d) - e[0]) / (e[1] - e[0]); return d.lo ? 1 - u : u; };
  const inBrush = (i, E) => DIMS.every((d, j) => !brush[d.k] || (u => u >= brush[d.k][0] - 1e-9 && u <= brush[d.k][1] + 1e-9)(up(i, d, E[j])));
  const ramp = i => { const u = utility(i); return `color-mix(in oklab, var(--accent) ${Math.round(25 + 75 * u)}%, var(--line))`; };
  function size(cv, ctx) { const dpr = Math.min(2, devicePixelRatio || 1), W = cv.clientWidth, H = cv.clientHeight; cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H); return [W, H]; }
  function colorOf(i) { const u = utility(i); const a = css("--accent"); return [a, u]; }
  function drawPC(E, cur) {
    const [W, H] = size(pc, pctx), top = 46, bot = 30, padX = 48, h = H - top - bot; axisX = DIMS.map((d, j) => padX + j * (W - 2 * padX) / (DIMS.length - 1)); box = { top, h };
    const yOf = (i, j) => top + (1 - up(i, DIMS[j], E[j])) * h;
    const line = i => { pctx.beginPath(); DIMS.forEach((d, j) => (j ? pctx.lineTo(axisX[j], yOf(i, j)) : pctx.moveTo(axisX[j], yOf(i, j)))); pctx.stroke(); };
    const any = Object.keys(brush).length > 0, acc = css("--accent"), ln = css("--line");
    pctx.lineWidth = 1;
    const order = M.front.slice().sort((a, b) => utility(a) - utility(b));
    for (const i of order) { const on = !any || inBrush(i, E); pctx.strokeStyle = on ? acc : ln; pctx.globalAlpha = on ? 0.06 + 0.5 * Math.pow(utility(i), 3) : 0.35; line(i); }
    pctx.globalAlpha = 1; pctx.textAlign = "center"; let gPrev = null;
    DIMS.forEach((d, j) => {
      const x = axisX[j]; pctx.strokeStyle = css("--ink-3"); pctx.lineWidth = 1; pctx.beginPath(); pctx.moveTo(x, top); pctx.lineTo(x, top + h); pctx.stroke();
      pctx.font = `500 11px ${css("--f-body")}`;
      if (d.g !== gPrev) { const js = DIMS.map((e, i) => (e.g === d.g ? i : -1)).filter(i => i >= 0), cx = (axisX[js[0]] + axisX[js[js.length - 1]]) / 2, t = d.g.toUpperCase(), w = pctx.measureText(t).width;
        pctx.fillStyle = css("--ink-3"); pctx.fillText(t, Math.max(w / 2 + 2, Math.min(W - w / 2 - 2, cx)), 13); gPrev = d.g; }
      pctx.fillStyle = css("--ink"); pctx.fillText(d.l, x, 31); pctx.fillStyle = css("--ink-2"); pctx.font = `400 10.5px ${css("--f-data")}`;
      pctx.fillText(fmtv(d, d.lo ? E[j][0] : E[j][1]), x, top - 4); pctx.fillText(fmtv(d, d.lo ? E[j][1] : E[j][0]), x, top + h + 14);
      if (brush[d.k]) { const [a, b] = brush[d.k]; pctx.fillStyle = acc; pctx.globalAlpha = .18; pctx.fillRect(x - 7, top + (1 - b) * h, 14, (b - a) * h); pctx.globalAlpha = 1; pctx.strokeStyle = acc; pctx.strokeRect(x - 7, top + (1 - b) * h, 14, (b - a) * h); }
    });
    for (const [i, w, c] of [[hover, 2, css("--ink-2")], [cur, 3, css("--mint")]]) { if (i == null) continue; pctx.strokeStyle = c; pctx.lineWidth = w; line(i); pctx.fillStyle = c; DIMS.forEach((d, j) => { pctx.beginPath(); pctx.arc(axisX[j], yOf(i, j), 3.2, 0, 7); pctx.fill(); }); }
    pctx.lineWidth = 1;
  }
  function drawSC(E, cur) {
    const [W, H] = size(sc, sctx), m = { l: 64, r: 14, t: 12, b: 40 }, dx = DIMS.find(d => d.k === sel.x), dy = DIMS.find(d => d.k === sel.y);
    const conv = (d, v) => (d.t === "$" ? v * M.tot / 12 : d.t === "L" ? v * M.tot : d.t === "n" ? v : v * 100);
    const xs = M.front.map(i => conv(dx, val(i, dx))), ys = M.front.map(i => conv(dy, val(i, dy)));
    let [x0, x1] = [Math.min(...xs), Math.max(...xs)], [y0, y1] = [Math.min(...ys), Math.max(...ys)]; const px = (x1 - x0) * .05 || 1, py = (y1 - y0) * .05 || 1; x0 -= px; x1 += px; y0 -= py; y1 += py;
    const X = v => m.l + (v - x0) / (x1 - x0) * (W - m.l - m.r), Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
    const ax = (d, v) => (d.t === "$" ? fmt$(v) : d.t === "L" ? fmtK(v) : d.t === "n" ? String(Math.round(v)) : v.toFixed(d.t === "%1" ? 1 : 0) + "%");
    sctx.font = `400 10.5px ${css("--f-data")}`; sctx.fillStyle = css("--ink-3"); sctx.strokeStyle = css("--line");
    const sx = Charts.niceStep(x1 - x0, Math.max(3, Math.floor(W / 110))), sy = Charts.niceStep(y1 - y0, 5);
    sctx.textAlign = "center"; for (let v = Math.ceil(x0 / sx) * sx; v <= x1; v += sx) { const x = X(v); sctx.beginPath(); sctx.moveTo(x, m.t); sctx.lineTo(x, H - m.b); sctx.stroke(); sctx.fillText(ax(dx, v), x, H - m.b + 14); }
    sctx.textAlign = "right"; for (let v = Math.ceil(y0 / sy) * sy; v <= y1; v += sy) { const y = Y(v); sctx.beginPath(); sctx.moveTo(m.l, y); sctx.lineTo(W - m.r, y); sctx.stroke(); sctx.fillText(ax(dy, v), m.l - 6, y + 3.5); }
    sctx.font = `500 11.5px ${css("--f-body")}`; sctx.fillStyle = css("--ink-2"); sctx.textAlign = "center";
    sctx.fillText(`${dx.l}${dx.lo ? " (lower is better)" : ""} →`, (m.l + W - m.r) / 2, H - 8);
    sctx.save(); sctx.translate(13, (m.t + H - m.b) / 2); sctx.rotate(-Math.PI / 2); sctx.fillText(`${dy.l}${dy.lo ? " (lower is better)" : ""} →`, 0, 0); sctx.restore();
    const any = Object.keys(brush).length > 0; pts = []; const acc = css("--accent"), ln = css("--line"), pan = css("--panel");
    for (const i of M.front.slice().sort((a, b) => utility(a) - utility(b))) {
      const x = X(conv(dx, val(i, dx))), y = Y(conv(dy, val(i, dy))), on = !any || inBrush(i, E); pts.push([x, y, i]);
      sctx.beginPath(); sctx.arc(x, y, on ? 4 : 3, 0, 7); sctx.fillStyle = on ? acc : ln; sctx.globalAlpha = on ? 0.15 + 0.85 * Math.pow(utility(i), 2) : .6; sctx.fill();
      if (on) { sctx.globalAlpha = 1; sctx.strokeStyle = pan; sctx.lineWidth = 1; sctx.stroke(); }
    }
    sctx.globalAlpha = 1;
    for (const [i, r, w, c] of [[hover, 6, 1.5, css("--ink")], [cur, 8, 3, css("--mint")]]) { if (i == null) continue; sctx.beginPath(); sctx.arc(X(conv(dx, val(i, dx))), Y(conv(dy, val(i, dy))), r, 0, 7); sctx.strokeStyle = c; sctx.lineWidth = w; sctx.stroke(); }
  }
  function draw() {
    if ($("view-frontier").hidden) return; const E = DIMS.map(ext), cur = current(); drawPC(E, cur); drawSC(E, cur);
    const n = M.front.filter(i => inBrush(i, E)).length;
    $("fr-sub").textContent = `${M.front.length.toLocaleString()} printers: each beats every other on at least one of these ${DIMS.length} measures. Darker = closer to your values. ` +
      (Object.keys(brush).length ? `${n} pass your filters.` : "Drag up or down along an axis to keep only a range; up is better on every axis.");
    $("fr-clear").hidden = !Object.keys(brush).length;
  }
  function tipFor(i, ev) {
    const p = D.printers[i], st = M.stats[i], wr = pc.closest(".frontier").getBoundingClientRect();
    tip.innerHTML = `<b>${esc(mix(p))}</b><br>${fmt$(st.early * M.tot / 12)}/mo now · unlucky ${fmt$(st.early_bad * M.tot / 12)} · runs dry ${pct(st.dry, 1)}<br>base ${p.base}% · ${p.skim == null || p.skim >= 1.95 ? "no bonus" : `bonus above ${Math.round((1 + p.skim) * 100)}%`} · match ${Math.round(utility(i) * 100)}`;
    tip.hidden = false; tip.style.left = Math.min(ev.clientX - wr.left + 14, wr.width - 300) + "px"; tip.style.top = ev.clientY - wr.top + 14 + "px";
  }
  const pcPos = ev => { const r = pc.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; };
  function nearest(x, y) {
    const E = DIMS.map(ext), j = axisX.findIndex((a, k) => k < axisX.length - 1 && x >= a && x <= axisX[k + 1]); if (j < 0) return null;
    const f = (x - axisX[j]) / (axisX[j + 1] - axisX[j]); let best = null, bd = 7;
    for (const i of M.front) { if (Object.keys(brush).length && !inBrush(i, E)) continue;
      const a = box.top + (1 - up(i, DIMS[j], E[j])) * box.h, b = box.top + (1 - up(i, DIMS[j + 1], E[j + 1])) * box.h, d = Math.abs(a + (b - a) * f - y); if (d < bd) { bd = d; best = i; } }
    return best;
  }
  pc.addEventListener("pointerdown", ev => { const [x, y] = pcPos(ev), j = axisX.findIndex(a => Math.abs(a - x) < 14); if (j < 0) return;
    dragging = { k: DIMS[j].k, u0: Math.max(0, Math.min(1, 1 - (y - box.top) / box.h)), moved: false }; pc.setPointerCapture(ev.pointerId); ev.preventDefault(); });
  pc.addEventListener("pointermove", ev => { const [x, y] = pcPos(ev);
    if (dragging) { const u = Math.max(0, Math.min(1, 1 - (y - box.top) / box.h)); if (Math.abs(u - dragging.u0) > .02) { dragging.moved = true; brush[dragging.k] = [Math.min(u, dragging.u0), Math.max(u, dragging.u0)]; draw(); } return; }
    const i = nearest(x, y); if (i !== hover) { hover = i; draw(); } if (i != null) tipFor(i, ev); else tip.hidden = true;
    pc.style.cursor = axisX.some(a => Math.abs(a - x) < 14) ? "ns-resize" : i != null ? "pointer" : "crosshair"; });
  pc.addEventListener("pointerup", () => { if (dragging && !dragging.moved) { delete brush[dragging.k]; draw(); } dragging = null; });
  pc.addEventListener("click", ev => { if (hover != null && !axisX.some(a => Math.abs(a - pcPos(ev)[0]) < 14)) { S.pin = hover; render(); } });
  pc.addEventListener("pointerleave", () => { hover = null; tip.hidden = true; draw(); });
  const scPick = ev => { const r = sc.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top; let best = null, bd = 9; for (const [px, py, i] of pts) { const d = Math.hypot(px - x, py - y); if (d < bd) { bd = d; best = i; } } return best; };
  sc.addEventListener("pointermove", ev => { const i = scPick(ev); if (i !== hover) { hover = i; draw(); } if (i != null) tipFor(i, ev); else tip.hidden = true; sc.style.cursor = i != null ? "pointer" : "crosshair"; });
  sc.addEventListener("pointerleave", () => { hover = null; tip.hidden = true; draw(); });
  sc.addEventListener("click", ev => { const i = scPick(ev); if (i != null) { S.pin = i; render(); } });
  $("fr-clear").onclick = () => { brush = {}; draw(); };
  for (const [id, key] of [["sx", "x"], ["sy", "y"]]) { const el = $(id); el.innerHTML = DIMS.map(d => `<option value="${d.k}">${d.g}: ${d.l}</option>`).join(""); el.value = sel[key]; el.onchange = () => { sel[key] = el.value; draw(); }; }
  $("fr-legend").innerHTML = `<span><i class="line" style="background:var(--accent)"></i>Frontier printer (darker = closer to your values)</span><span><i class="line" style="background:var(--mint)"></i>Your pick</span>`;
  addEventListener("resize", () => draw()); matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => draw());
  return { draw };
})();

/* ---------- sharing ---------- */
async function testfolUrl() {
  const list = compareList(), cur = current();
  const r = await post("/api/testfol", { portfolios: list.map(c => ({ name: c.label.slice(0, 40), alloc: c.spec.alloc })), start_val: M.tot, withdraw_month: D.printers[cur].base / 100 * M.tot / 12 });
  return r.url;
}
async function copy(text) { try { await navigator.clipboard.writeText(text); return true; } catch { return false; } }
$("share-testfol").onclick = async () => { try { const u = await testfolUrl(); window.open(u, "_blank", "noopener"); toast("Opened in testfol.io. It shows the base paycheck as a monthly, inflation-adjusted withdrawal; testfol has no bonus bucket or brake."); } catch (e) { toast(e.message); } };
$("copy-testfol").onclick = async () => { try { const u = await testfolUrl(); toast((await copy(u)) ? "testfol.io link copied. Anyone can open it." : u, 6000); } catch (e) { toast(e.message); } };
$("copy-app").onclick = async () => { writeHash(); toast((await copy(location.href)) ? "App link copied. It opens this exact pick in a running Forge." : location.href, 6000); };

/* ---------- go ---------- */
derive(); render(); setTab(S.tab);
addEventListener("hashchange", () => { readHash(); derive(); render(); });
})();
