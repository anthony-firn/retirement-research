/* Money Printer — plain-words app for growing money and paying yourself from it.
   Views (all deep-linkable): #/  #/build  #/retire  #/compare?s=mp21,box  #/setup?s=mp21  #/today?n=name
   Situation params everywhere: amount, age, acct (taxable|ira|roth), br (low|mid). */
"use strict";
const $ = s => document.querySelector(s);
const app = $("#app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = x => (x == null || !isFinite(x) ? "–" : (x < 0 ? "−$" : "$") + Math.round(Math.abs(x)).toLocaleString("en-US"));
const kmoney = x => (Math.abs(x) >= 1e7 ? "$" + Math.round(x / 1e6) + "M" : Math.abs(x) >= 1e6 ? "$" + (x / 1e6).toFixed(1) + "M" : Math.abs(x) >= 1e4 ? "$" + Math.round(x / 1e3) + "k" : money(x));
const pct = (x, d = 0) => (x == null ? "–" : (x * 100).toFixed(d) + "%");
const num = s => Number(String(s).replace(/[^0-9.\-]/g, "")) || 0;
function toast(m, ms = 2600) { const t = $("#toast"); t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), ms); }
async function api(url, body) {
  const r = await fetch(url, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || "Something went wrong."); return j;
}
const ICON = {
  grow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21v-9"/><path d="M12 12c0-4 3-7 8-7 0 5-3 8-8 7Z"/><path d="M12 14c0-3-2-6-7-6 0 4 2 7 7 6Z"/></svg>',
  pay: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/><path d="M6 9.5v5M18 9.5v5"/></svg>',
  vs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l9 9M13 4 4 13"/><path d="M15 15l5 5M20 15l-5 5"/><path d="M11 20l9-9"/></svg>',
  today: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="16" rx="2"/><path d="M8 2.5v4M16 2.5v4M3.5 9.5h17"/><path d="m8.5 15 2.3 2.3 4.7-4.6"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.5"/><path d="m7.5 12.5 3 3 6-6.5"/></svg>',
  trophy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8.5 20h7M10 17h4"/></svg>',
  cash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.8"/></svg>',
  swap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h13l-3-3M20 16H7l3 3"/></svg>',
  loan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10 12 4l9 6"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/></svg>',
  jan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3.5" y="4.5" width="17" height="16" rx="2"/><path d="M8 2.5v4M16 2.5v4M3.5 9.5h17"/></svg>',
};
const STEP = { "MONTHLY PRINT": ["Pay yourself", ICON.cash], "YEAR-END": ["January check", ICON.jan], REBALANCE: ["Even out the funds", ICON.swap], DEPOSIT: ["Invest new money", ICON.grow],
  "BOX LOAN": ["Low-cost loan", ICON.loan], "PAY OFF THE LOAN": ["Pay off the loan", ICON.loan], "INITIAL PURCHASE": ["Buy the funds", ICON.grow] };

// ------------------------------------------------------------------ state + deep links
const S = { amount: 150000, age: 60, acct: "taxable", br: "low", sex: "f", ids: ["mp21", "box", "6040"], s: "mp21", n: "", battle: "2008",
  b: { age: 35, saved: 20000, monthly: 500, want: 4000, ss: 1500, acct: "roth", mix: "steady", sex: "f", claim: "best", other: 0, br: "low", pay: "mp21", health: 1, raise: 1 } };
let R = [], RB = {};
function readHash() {
  const [path, qs] = location.hash.replace(/^#\/?/, "").split("?"); const q = new URLSearchParams(qs || "");
  for (const k of ["amount", "age"]) if (q.has(k)) S[k] = num(q.get(k));
  for (const k of ["acct", "br", "s", "n", "battle", "sex"]) if (q.has(k)) S[k] = q.get(k);
  for (const k of ["goal", "borrow"]) if (q.has(k)) Q[k] = q.get(k);
  if (q.has("ids")) S.ids = q.get("ids").split(",").filter(i => RB[i]).slice(0, 4);
  for (const k of ["bage", "saved", "monthly", "want", "ss", "other", "health", "raise"]) if (q.has(k)) S.b[k === "bage" ? "age" : k] = num(q.get(k));
  for (const [k, f] of [["bacct", "acct"], ["mix", "mix"], ["bsex", "sex"], ["claim", "claim"], ["bbr", "br"], ["pay", "pay"]]) if (q.has(k)) S.b[f] = q.get(k);
  return path || "";
}
function link(view, extra = {}) {
  const sit = { amount: S.amount, age: S.age, acct: S.acct, br: S.br, sex: S.sex }, b = S.b;
  const q = { build: { bage: b.age, saved: b.saved, monthly: b.monthly, want: b.want, ss: b.ss, bacct: b.acct, mix: b.mix, bsex: b.sex, claim: b.claim, other: b.other, bbr: b.br, pay: b.pay, health: b.health, raise: b.raise },
              "start-result": { ...sit, goal: Q.goal || "steady", borrow: Q.borrow || "no" },
              retire: sit, compare: { ...sit, ids: S.ids.join(","), battle: S.battle }, setup: { ...sit, s: S.s }, today: S.n ? { n: S.n } : {} }[view] || {};
  const p = new URLSearchParams({ ...q, ...extra }).toString(); return `#/${view}${p ? "?" + p : ""}`;
}
function setHash(view) { history.replaceState(null, "", link(view)); }
const sit = () => ({ amount: S.amount, age: S.age, account: S.acct, bracket: S.br, sex: S.sex });

// ------------------------------------------------------------------ shared pieces
function seg(id, opts, val) { return `<div class="seg" role="group" id="${id}">${opts.map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${v === val}">${l}</button>`).join("")}</div>`; }
function onSeg(id, fn) { $("#" + id).onclick = e => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#" + id).children) x.setAttribute("aria-pressed", x === b); fn(b.dataset.v); }; }
function field(id, label, val, hint = "") { return `<label class="field"><span>${label}${hint ? ` <small class="muted">${hint}</small>` : ""}</span><input id="${id}" inputmode="numeric" value="${esc(val)}"></label>`; }
function moneyInput(id, fn) { const el = $("#" + id); let t; el.oninput = () => { clearTimeout(t); t = setTimeout(() => fn(num(el.value)), 450); };
  el.onblur = () => { const v = num(el.value); el.value = id.includes("age") ? v : v.toLocaleString("en-US"); }; }
function situationBar(onchange) {
  return { html: `<section class="card"><div class="ask">
      ${field("s-amount", "Money to use", S.amount.toLocaleString("en-US"))}${field("s-age", "Age", S.age)}
      <div class="field wide"><span>Where it is</span>${seg("s-acct", [["taxable", "Regular"], ["ira", "IRA / 401(k)"], ["roth", "Roth"]], S.acct)}</div>
      <div class="field"><span>Income tax</span>${seg("s-br", [["low", "Low"], ["mid", "Middle"]], S.br)}</div>
      <div class="field"><span>You are</span>${seg("s-sex", [["f", "Woman"], ["m", "Man"]], S.sex)}</div></div><p class="hint" id="s-plan" style="margin-top:8px"></p></section>`,
    wire() { moneyInput("s-amount", v => { S.amount = Math.max(5000, v); onchange(); }); moneyInput("s-age", v => { S.age = Math.max(30, Math.min(95, v)); onchange(); });
             onSeg("s-acct", v => { S.acct = v; onchange(); }); onSeg("s-br", v => { S.br = v; onchange(); }); onSeg("s-sex", v => { S.sex = v; onchange(); }); } };
}
function planNote(s) { const el = $("#s-plan"); if (el && s) el.textContent = `Plans to age ${s.plan_age} (average life + 1 standard deviation). Paychecks rise with prices.`; }
const color = id => `var(--${(RB[id] || {}).color || "s1"})`;
function badge(kind, text) { const i = { good: "✓", warn: "!", bad: "×" }[kind]; return `<span class="badge ${kind}"><i aria-hidden="true">${i}</i>${text}</span>`; }
function safety(p) {
  const cut = 1 - p.never_cut, k = (x, a, b) => (x < a ? "good" : x < b ? "warn" : "bad");
  return `<div class="badges">${badge(k(cut, .15, .3), `Pay cut: ${pct(cut)} chance`)}${badge(k(p.dry, .01, .05), `Runs out: ${pct(p.dry, p.dry < .01 ? 1 : 0)}`)}${badge(k(p.deep_dip, .2, .35), `Big drop: ${pct(p.deep_dip)}`)}</div>`;
}
function fundList(funds) { return `<ul class="funds">${funds.map(f => `<li><b>${f.w}%</b><span>${esc(f.name)}</span></li>`).join("")}</ul>`; }
const loading = (msg = "Working it out…") => `<p class="hint">${msg}</p>`;

// ------------------------------------------------------------------ HOME
async function home() {
  let mine = []; try { mine = await api("/api/ops/list"); } catch {}
  app.innerHTML = `<section class="view">
    <h1>What do you want to do?</h1>
    <a class="tile start" href="#/start">${ICON.vs}<b>Start here: make my plan</b><span>8 easy questions. Get a tested plan made for you.</span></a>
    <div class="tiles">
      <a class="tile" href="${link("build")}">${ICON.grow}<b>Grow my money</b><span>Still working. See when you can stop.</span></a>
      <a class="tile" href="${link("retire")}">${ICON.pay}<b>Pay myself</b><span>Turn savings into a monthly paycheck.</span></a>
      <a class="tile" href="${link("compare")}">${ICON.vs}<b>Compare plans</b><span>Side by side, through real crashes.</span></a>
      <a class="tile" href="${link("today", mine[0] ? { n: mine[0].name } : {})}">${ICON.today}<b>Today</b><span>${mine.length ? `Your plan: ${esc(mine[0].name)}. What to do now.` : "Set up a plan first."}</span></a>
    </div>
    </section>`;
}

// ------------------------------------------------------------------ START: the quest (one question per screen)
const Q = { step: 0, working: null, goal: null, borrow: null };
const QUESTS = [
  { k: "working", q: "Are you still working?", opts: [["yes", "Yes, still working"], ["no", "No, or stopping soon"]] },
  { k: "age", q: "How old are you?", input: "age" },
  { k: "amount", q: "How much money can you use?", input: "money", hint: "Savings you can invest. Not your house." },
  { k: "acct", q: "Where is that money?", opts: [["taxable", "Regular account or bank"], ["ira", "IRA or 401(k)"], ["roth", "Roth IRA"]] },
  { k: "br", q: "Your yearly income?", opts: [["low", "Under $50k (couple: $100k)"], ["mid", "More than that"]] },
  { k: "sex", q: "You are…", opts: [["f", "A woman"], ["m", "A man"]], hint: "Women live longer on average, so the plan lasts longer." },
  { k: "goal", q: "What matters most?", opts: [["steady", "A paycheck that rarely drops"], ["most", "The biggest paycheck"], ["calm", "Small drops in bad times"], ["legacy", "Money left for family"], ["simple", "Keep it simple"]] },
  { k: "borrow", q: "Borrow to earn more?", opts: [["no", "No"], ["crash", "Only after a big drop"], ["yes", "Yes"]], hint: "Borrowing raises pay and risk. Needs $110,000+ and age under 75." },
];
function start() {
  const i = Q.step, t = QUESTS[i], bar = `<div class="meter" aria-label="Step ${i + 1} of ${QUESTS.length}"><i style="--w:${(i + 1) / QUESTS.length * 100}%"></i></div>`;
  const val = t.input === "age" ? S.age : t.input === "money" ? S.amount.toLocaleString("en-US") : "";
  app.innerHTML = `<section class="view quest">${bar}<p class="label">Question ${i + 1} of ${QUESTS.length}</p><h1>${t.q}</h1>
    ${t.opts ? `<div class="answers">${t.opts.map(([v, l]) => `<button class="btn answer" data-v="${v}">${l}</button>`).join("")}</div>`
             : `<label class="field"><span class="sr">${t.q}</span><input id="q-in" inputmode="numeric" value="${val}" style="font-size:28px;min-height:64px"></label><button class="btn go" id="q-next" style="min-height:56px">Next</button>`}
    ${t.hint ? `<p class="hint">${t.hint}</p>` : ""}
    <div class="row">${i ? '<button class="btn" id="q-back">Back</button>' : ""}</div></section>`;
  const next = () => { Q.step++; if (Q.step >= QUESTS.length) { Q.step = 0; location.hash = link("start-result"); } else start(); };
  if (t.opts) $(".answers").onclick = e => { const b = e.target.closest("button"); if (!b) return; const v = b.dataset.v;
    if (t.k === "working") { Q.working = v; if (v === "yes") { Q.step = 0; location.hash = link("build"); return; } }
    else if (t.k === "goal" || t.k === "borrow") Q[t.k] = v; else S[t.k] = v; next(); };
  else { const go = () => { const el = $("#q-in"), v = Number(el.value.replace(/[$,\s]/g, "")), age = t.input === "age";
      const valid = Number.isFinite(v) && (age ? Number.isInteger(v) && v >= 30 && v <= 95 : v >= 5000 && v <= 50000000);
      el.setCustomValidity(valid ? "" : age ? "Enter an age from 30 to 95." : "Enter an amount from $5,000 to $50,000,000.");
      if (!valid) { el.reportValidity(); return; } S[age ? "age" : "amount"] = v; next(); };
    $("#q-in").oninput = () => $("#q-in").setCustomValidity("");
    $("#q-next").onclick = go; $("#q-in").onkeydown = e => { if (e.key === "Enter") go(); }; $("#q-in").focus(); }
  if (i) $("#q-back").onclick = () => { Q.step--; start(); };
}
async function startResult() {
  app.innerHTML = `<section class="view">${loading("Testing plans on 50 years of markets…")}</section>`; let r;
  try { r = await api("/api/quest", { ...sit(), goal: Q.goal || "steady", borrow: Q.borrow || "no" }); } catch (e) { app.innerHTML = `<section class="view"><p class="err">${esc(e.message)}</p><a class="btn" href="#/start">Start again</a></section>`; return; }
  const p = r.profile, m = RB[r.pick]; S.s = r.pick;
  app.innerHTML = `<section class="view">
    <section class="card plan" style="--c:${color(r.pick)}"><span class="label">Your class</span><h1>${esc(r.cls)}</h1><p>${esc(r.tagline)}</p>
      <div><span class="label">Usually pays</span><div class="big">${money(p.life)}<small>/mo</small></div></div>
      <div class="facts"><div class="fact"><b>${money(p.floor)}</b><span>steady pay (not guaranteed)</span></div><div class="fact"><b>${money(p.first10)}</b><span>first 10 years</span></div><div class="fact"><b>${r.wins} of ${r.battles}</b><span>crashes won vs a 60/40 mix</span></div></div>
      <div class="stats">${STATS.map(([k, lab, f]) => `<div class="stat"><span class="lab">${lab}</span><span class="meter" aria-hidden="true"><i style="--w:${p.bars[k] * 10}%"></i></span><span class="val">${f(p)}</span></div>`).join("")}</div>
      ${safety(p)}<ul class="small" style="margin:0;padding-left:18px">${r.why.map(w => `<li>${esc(w)}</li>`).join("")}<li>Plan: ${esc(m.name)} at ${esc(m.where)}. Plans to age ${r.situation.plan_age}.</li></ul>
      ${r.blocked.length ? `<p class="hint">${r.blocked.map(b => esc(b.why)).filter((x, i, a) => a.indexOf(x) === i).join(" ")}</p>` : ""}
    </section>
    <section class="card stack"><h2>Your quests</h2><ol class="steps">
      <li><div><b>Set it up.</b> Open the account and place the first orders. <a href="${link("setup", { s: r.pick })}">Start this quest</a></div></li>
      <li><div><b>Save your tracker</b> at the end of setup.</div></li>
      <li><div><b>Once a month,</b> open <a href="#/today">Today</a> and do what it says. That's it.</div></li>
      <li><div><b>In a crash, open Today.</b> Check the plan's instructions, especially if you have a loan.</div></li></ol></section>
    <div class="row"><a class="btn go" href="${link("setup", { s: r.pick })}">Set it up</a><a class="btn" href="${link("compare", { ids: [r.pick, ...r.others.map(o => o.id), "6040"].join(",") })}">See the battles</a><a class="btn" href="#/start">Start again</a></div>
  </section>`;
}

// ------------------------------------------------------------------ GROW (saving years)
async function build() {
  const b = S.b; let open = false; try { open = localStorage.getItem("more") === "1"; } catch {}
  app.innerHTML = `<section class="view"><h1>When can I stop working?</h1>
    <section class="card stack"><div class="ask">
      ${field("b-age", "Age", b.age)}${field("b-saved", "Saved now", b.saved.toLocaleString("en-US"))}${field("b-monthly", "Save each month", b.monthly.toLocaleString("en-US"))}
      ${field("b-want", "Want each month later", b.want.toLocaleString("en-US"))}${field("b-ss", "Social Security at 67", b.ss.toLocaleString("en-US"), "per month")}
    </div>
    <details id="b-more" ${open ? "open" : ""}><summary>More</summary><div class="ask" style="margin-top:12px">
      <div class="field"><span>You are</span>${seg("b-sex", [["f", "Woman"], ["m", "Man"]], b.sex)}</div>
      <div class="field wide"><span>Start Social Security</span>${seg("b-claim", [["best", "Best"], ["62", "62"], ["67", "67"], ["70", "70"]], String(b.claim))}</div>
      ${field("b-other", "Other income or benefits", b.other.toLocaleString("en-US"), "per month")}
      <div class="field wide"><span>Account</span>${seg("b-acct", [["roth", "Roth IRA"], ["trad", "401(k) / IRA"], ["taxable", "Regular"]], b.acct)}</div>
      <div class="field"><span>Income tax</span>${seg("b-br", [["low", "Low"], ["mid", "Middle"]], b.br)}</div>
      <div class="field wide"><span>Paycheck plan later</span>${seg("b-pay", [["mp21", "Simple"], ["box", "Boosted"], ["crash", "Crash Buyer"]], b.pay)}</div>
      <div class="field"><span>Mix now</span>${seg("b-mix", [["steady", "Steady"], ["faster", "Faster"]], b.mix)}</div>
      <div class="field"><span>Health care</span>${seg("b-health", [["1", "Include"], ["0", "Leave out"]], String(b.health))}</div>
      <div class="field"><span>Saving rises with prices</span>${seg("b-raise", [["1", "Yes"], ["0", "No"]], String(b.raise))}</div>
    </div><p class="hint" style="margin-top:8px">Social Security amount: your statement at <a href="https://www.ssa.gov/myaccount/" target="_blank" rel="noopener">ssa.gov/myaccount</a> (benefit at full retirement age).</p></details>
    </section><div id="b-out">${loading()}</div></section>`;
  $("#b-more").ontoggle = () => { try { localStorage.setItem("more", $("#b-more").open ? "1" : "0"); } catch {} };
  const go = () => { setHash("build"); paintBuild(); };
  for (const [id, k] of [["b-age", "age"], ["b-saved", "saved"], ["b-monthly", "monthly"], ["b-want", "want"], ["b-ss", "ss"], ["b-other", "other"]]) moneyInput(id, v => { S.b[k] = v; go(); });
  for (const [id, k, n] of [["b-sex", "sex"], ["b-claim", "claim"], ["b-acct", "acct"], ["b-br", "br"], ["b-pay", "pay"], ["b-mix", "mix"], ["b-health", "health", 1], ["b-raise", "raise", 1]])
    onSeg(id, v => { S.b[k] = n ? +v : v; go(); });
  paintBuild();
}
async function paintBuild() {
  const out = $("#b-out"); let r; const b = S.b;
  try { r = await api("/api/build", { age: b.age, saved: b.saved, monthly: b.monthly, want: b.want, ss: b.ss, claim: b.claim, other: b.other, sex: b.sex, account: b.acct, bracket: b.br, pay: b.pay, mix: b.mix, health: !!b.health, raise: !!b.raise }); }
  catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  const t = r.retire, bd = r.breakdown, age = b.age, R = t.typical, yr = new Date().getFullYear() + (R ? R - age : 0), pay = RB[r.pay];
  const lv = r.levels.slice(1).map(l => `<span class="chip">Save ${money(l.monthly)}/mo → ${l.typical ?? "90+"}</span>`).join("");
  const c = r.contrib; const cnote = c.overflow > 1 && b.acct !== "taxable" ? `${b.acct === "roth" ? "Roth" : "401(k)"} limit: ${money(c.limit)}/mo. The other ${money(c.overflow)}/mo goes to a regular account.`
    : c.pretax ? `Pre-tax: your ${money(b.monthly)} becomes ${money(c.in_account)}/mo in the 401(k).` : "";
  const bestNeed = r.ss_table.length ? Math.min(...r.ss_table.map(x => x.need)) : 0;
  const ssRows = r.ss_table.length ? `<div class="tablewrap"><table><thead><tr><th>Start at</th><th class="num">Per month for life</th><th class="num">Extra savings needed</th></tr></thead><tbody>
      ${r.ss_table.map(x => `<tr${x.age === bd.claim ? ' style="font-weight:700"' : ""}><td>${x.age}${x.age === bd.claim ? " ✓ best" : ""}</td><td class="num">${money(x.monthly)}</td><td class="num">${x.need - bestNeed < 500 ? "—" : "+" + kmoney(x.need - bestNeed)}</td></tr>`).join("")}</tbody></table></div>` : "";
  const plan = r.plan ? `<p>Then <b>${esc(pay.name)}</b> pays a base of <b>${money(r.plan.floor)}/mo</b> (${r.plan.base_pct.toFixed(2)}% a year), usually <b>${money(r.plan.life)}/mo</b>. ${safety(r.plan)}</p>` : "";
  out.innerHTML = `<div class="grid two">
    <section class="card plan" style="--c:var(--s1)">
      <span class="label">You can stop at about</span>
      <div class="big">${R ? `Age ${R}` : "Not by 90"}</div>
      <div class="facts"><div class="fact"><b>${t.lucky ?? "–"}</b><span>if lucky (1 in 4)</span></div><div class="fact"><b>${t.unlucky ?? "–"}</b><span>if unlucky (1 in 4)</span></div><div class="fact"><b>${t.bad ?? "90+"}</b><span>bad luck (1 in 10)</span></div></div>
      ${R ? `<p>You need <b>${kmoney(r.need)}</b> in today's dollars. That is about <b>${kmoney(r.need * r.prices.factor)}</b> in ${yr} dollars.</p>
      <ul class="small" style="margin:0;padding-left:18px">
        <li>${kmoney(bd.printer)} for your paycheck for life</li>
        ${bd.bridge > 1 ? `<li>${kmoney(bd.bridge)} to cover ${bd.ss_gap_years} years until Social Security</li>` : ""}
        <li>Social Security from ${bd.claim}: ${money(bd.ss)}/mo</li>
        ${b.health ? `<li>Health care: ${money(bd.health65)}/mo at 65, ${money(bd.health85)}/mo at 85 (today's $)</li>` : ""}
        <li>Plans to age ${r.plan_age} (average ${Math.round(r.life.mean)} + ${Math.round(r.life.sd)} years)</li>
      </ul>${plan}` : `<p>Save more, want less, or add income.</p>`}
      <div class="row">${lv}</div>${cnote ? `<p class="hint">${cnote}</p>` : ""}
    </section>
    <section class="card"><h2>Your money by age</h2><p class="hint">Today's dollars. Line = typical. Shaded = 1 in 10 to 9 in 10. Dashed = enough to stop.</p><div class="chart" id="b-chart"></div></section>
  </div>
  <div class="grid two">
    <section class="card stack"><h2>What to buy now — ${esc(r.mix.name)}</h2><p class="hint">${esc(r.mix.blurb)}</p>${fundList(r.mix.funds)}</section>
    <section class="card stack"><h2>Set it up</h2><ol class="steps">
      <li><div><b>Open the account.</b> ${b.acct === "roth" ? "A Roth IRA at M1 Finance." : b.acct === "trad" ? "Your 401(k), or a traditional IRA at M1 Finance." : "A regular account at M1 Finance."}</div></li>
      <li><div><b>Automate ${money(b.monthly)} a month</b> on payday${b.raise ? ", and raise it with prices each year" : ""}.</div></li>
      <li><div><b>Make a pie</b> with these funds at these percents.</div></li>
      <li><div><b>Once a year,</b> press Rebalance only if a fund is 6+ points off its target.</div></li>
      <li><div><b>When you stop,</b> <a href="${link("retire", { amount: Math.round(bd.printer || r.need), age: R || age })}">open Pay myself</a>.</div></li>
    </ol></section></div>
  ${ssRows ? `<section class="card stack"><h2>When to start Social Security</h2><p class="hint">If you stop at ${R}. Later = bigger checks for life, but more savings to cover the wait.</p>${ssRows}</section>` : ""}
  <section class="card stack"><h2>Also check</h2><ul class="small" style="margin:0;padding-left:18px">
    <li>Medicare at 65 (already in the health numbers).</li><li>If income is low: Medicare Savings Program, Extra Help with drugs, SNAP (CalFresh in California), utility discounts.</li>
    <li>Married? The higher earner waiting until 70 raises the check for whoever lives longer.</li>
    <li>Find yours: <a href="https://www.benefitscheckup.org/" target="_blank" rel="noopener">BenefitsCheckUp.org</a>. Most look at income, many at savings too. Add any you will get under More → Other income.</li></ul></section>`;
  const end = Math.min(r.ages.length, Math.max(t.bad || R || 65, 65) + 5 - age + 1), cut = a => a.slice(0, end);
  Charts.lines($("#b-chart"), { x: cut(r.ages), xfmt: v => `${v}`, xint: true, yfmt: kmoney, height: 300,
    band: { lo: cut(r.bal[0]), hi: cut(r.bal[2]), color: "--s1", label: "Range" },
    series: [{ label: "Typical", short: "Typical", color: "--s1", data: cut(r.bal[1]) }, { label: "Enough", short: "Enough", color: "--ink-2", dash: [6, 5], data: cut(r.need_curve) }] });
}

// ------------------------------------------------------------------ PAY MYSELF
async function retire() {
  const bar = situationBar(() => { setHash("retire"); paintRetire(); });
  app.innerHTML = `<section class="view"><h1>Pay myself</h1>${bar.html}<div id="r-out">${loading()}</div></section>`; bar.wire(); paintRetire();
}
async function paintRetire() {
  const out = $("#r-out"); let r;
  try { r = await api("/api/profiles", { ...sit(), ids: ["mp21", "box", "crash"] }); } catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  planNote(r.situation); const av = r.strategies.filter(p => p.available); const by = Object.fromEntries(av.map(p => [p.id, p]));
  const bestId = by.box && S.amount >= 110000 ? "box" : "mp21"; const best = by[bestId]; const others = av.filter(p => p.id !== bestId);
  const card = (p, hero) => { const m = RB[p.id];
    return `<section class="card plan" style="--c:${color(p.id)}">
      <div class="name"><b>${esc(m.name)}</b><span class="chip">${esc(m.tag)}</span><span class="chip">${esc(m.where)}</span>${hero ? '<span class="chip" style="color:var(--good-ink)">Best for you</span>' : ""}</div>
      <div><span class="label">Usually pays</span><div class="big">${money(p.life)}<small>/mo</small></div></div>
      <div class="facts"><div class="fact"><b>${money(p.floor)}</b><span>steady pay, rises with prices (not guaranteed)</span></div><div class="fact"><b>${money(p.first10)}</b><span>first 10 years</span></div><div class="fact"><b>${money(p.life_bad)}</b><span>bad luck (1 in 10)</span></div></div>
      ${safety(p)}${p.needs_pm ? '<p class="hint">Needs $110,000+ for the cheapest loan setup.</p>' : ""}
      ${hero ? `<div class="chart short" id="r-fan"></div>` : `<p class="small muted">${esc(m.blurb)}</p>`}
      <div class="row"><a class="btn go" href="${link("setup", { s: p.id })}">Set it up</a>${hero ? `<a class="btn" href="${link("compare", { ids: ["mp21", "box", "crash", "6040"].filter(i => i === "6040" || by[i]).join(",") })}">Compare</a>` : ""}</div>
    </section>`; };
  out.innerHTML = `<div class="grid two">${card(best, true)}<div class="stack">${others.map(p => card(p, false)).join("")}</div></div>
    <p class="hint">After tax, in today's dollars. "Usually" = typical over your life. Steady pay drops only if the account falls a lot.</p>
    ${S.acct === "ira" ? `<p class="hint">Your IRA may require yearly minimum withdrawals based on your birth year. Ask your provider for the amount and start date. This estimate does not model those withdrawals. <a href="https://www.irs.gov/retirement-plans/retirement-plan-and-ira-required-minimum-distributions-faqs" target="_blank" rel="noopener">IRS rules</a>.</p>` : ""}`;
  const yrs = best.fan.years.map(y => S.age + y), mo = a => a.map(v => v * S.amount / 12);
  Charts.lines($("#r-fan"), { x: yrs.slice(1), xfmt: v => `age ${v}`, xint: true, yfmt: money, height: 230,
    band: { lo: mo(best.fan.pay[0]), hi: mo(best.fan.pay[2]), color: color(bestId).slice(4, -1), label: "Range" },
    series: [{ label: "Monthly pay by age", short: "Typical", color: color(bestId).slice(4, -1), data: mo(best.fan.pay[1]) }] });
}

// ------------------------------------------------------------------ COMPARE (characters + battles)
async function compare() {
  const bar = situationBar(() => { setHash("compare"); paintCompare(); });
  app.innerHTML = `<section class="view"><div class="row between"><h1>Compare plans</h1><button class="btn" id="c-share">Copy link</button></div>
    <section class="card stack"><span class="label">Pick up to 4</span><div class="picker" id="c-pick">${R.map(r => `<button type="button" data-id="${r.id}" aria-pressed="${S.ids.includes(r.id)}" style="--c:var(--${r.color})"><span class="dot"></span>${esc(r.name)}</button>`).join("")}</div></section>
    ${bar.html}<div id="c-cards">${loading()}</div><div id="c-battles"></div></section>`;
  bar.wire();
  $("#c-pick").onclick = e => { const b = e.target.closest("button"); if (!b) return; const id = b.dataset.id, on = S.ids.includes(id);
    if (!on && S.ids.length >= 4) return toast("Up to 4 at a time.");
    if (on && S.ids.length <= 1) return; S.ids = on ? S.ids.filter(i => i !== id) : [...S.ids, id]; b.setAttribute("aria-pressed", !on); setHash("compare"); paintCompare(); };
  $("#c-share").onclick = async () => { setHash("compare"); try { await navigator.clipboard.writeText(location.href); toast("Link copied."); } catch { toast(location.href, 6000); } };
  paintCompare();
}
const STATS = [["life", "Paycheck", p => money(p.life)], ["floor", "Steady pay", p => money(p.floor)], ["never_cut", "Rarely cut", p => `${pct(p.never_cut)} never cut`],
  ["deep_dip", "Calm", p => `${pct(p.deep_dip)} big drop`], ["stress_life", "Tough times", p => `${money(p.stress_life)} if unlucky`], ["left", "Leaves", p => kmoney(p.left)], ["ease", "Easy", p => `${p.ease}/10`]];
async function paintCompare() {
  const cards = $("#c-cards"), bt = $("#c-battles"); const ids = S.ids.slice();
  cards.innerHTML = loading(); bt.innerHTML = "";
  let pr, ba;
  try { [pr, ba] = await Promise.all([api("/api/profiles", { ...sit(), ids }), api("/api/battles", { ...sit(), ids })]); } catch (e) { cards.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  planNote(pr.situation);
  cards.innerHTML = `<div class="grid">${pr.strategies.map(p => { const m = RB[p.id];
    if (!p.available) return `<section class="card plan off" style="--c:${color(p.id)}"><div class="name"><b>${esc(m.name)}</b></div><p>${esc(p.why)}</p></section>`;
    return `<section class="card plan" style="--c:${color(p.id)}">
      <div class="name"><b>${esc(m.name)}</b><span class="chip">${esc(m.tag)}</span></div>
      <div><span class="label">Usually pays</span><div class="big" style="font-size:44px">${money(p.life)}<small>/mo</small></div></div>
      <div class="stats">${STATS.map(([k, lab, f]) => `<div class="stat"><span class="lab">${lab}</span><span class="meter" aria-hidden="true"><i style="--w:${p.bars[k] * 10}%"></i></span><span class="val">${f(p)}</span></div>`).join("")}</div>
      <p class="small muted">${esc(m.blurb)} · ${esc(m.where)}</p>
      ${m.operable ? `<a class="btn" href="${link("setup", { s: p.id })}">Set it up</a>` : ""}
    </section>`; }).join("")}</div>`;
  const tabs = [...ba.episodes.map(e => [e.code, e.name]), ["future", "The future"], ["whatif", "What ifs"]];
  if (!tabs.some(t => t[0] === S.battle)) S.battle = "2008";
  bt.innerHTML = `<section class="card stack"><h2>Battles</h2><div class="tabs" role="tablist" id="c-tabs">${tabs.map(([c, n]) => `<button role="tab" data-c="${c}" aria-selected="${c === S.battle}">${n}</button>`).join("")}</div><div id="c-fight"></div></section>`;
  $("#c-tabs").onclick = e => { const b = e.target.closest("button"); if (!b) return; S.battle = b.dataset.c; for (const x of $("#c-tabs").children) x.setAttribute("aria-selected", x === b); setHash("compare"); fight(pr, ba); };
  fight(pr, ba);
}
function legendOf(ids) { return `<div class="legend">${ids.map(i => `<span style="--c:${color(i)}"><i class="ln"></i>${esc(RB[i].name)}</span>`).join("")}</div>`; }
function fight(pr, ba) {
  const el = $("#c-fight"), av = pr.strategies.filter(p => p.available), ids = av.map(p => p.id), v = c => color(c).slice(4, -1);
  if (!av.length) { el.innerHTML = "<p>None of these can be used with this account.</p>"; return; }
  if (S.battle === "future") {
    const yrs = av[0].fan.years.map(y => S.age + y);
    el.innerHTML = `<p>Thousands of possible futures from past markets. Line = typical.</p>${legendOf(ids)}
      <div class="grid two"><div><h3>Monthly pay</h3><div class="chart" id="f-pay"></div></div><div><h3>Money left, bad luck (1 in 10)</h3><div class="chart" id="f-bal"></div></div></div>`;
    Charts.lines($("#f-pay"), { x: yrs.slice(1), xfmt: x => `age ${x}`, xint: true, yfmt: money, series: av.map(p => ({ label: RB[p.id].name, short: RB[p.id].name, color: v(p.id), data: p.fan.pay[1].map(x => x * S.amount / 12) })) });
    Charts.lines($("#f-bal"), { x: yrs, xfmt: x => `age ${x}`, xint: true, yfmt: kmoney, series: av.map(p => ({ label: RB[p.id].name, short: RB[p.id].name, color: v(p.id), data: p.fan.bal[0].map(x => x * S.amount) })) });
    return;
  }
  if (S.battle === "whatif") {
    const all = ba.scenarios.flatMap(s => ids.map(i => Math.abs(s.moves[i] ?? 0))); const top = Math.max(5, ...all);
    el.innerHTML = `<p>A sudden shock, one day. Percent of your money gained or lost.</p>${legendOf(ids)}<div class="scen">${ba.scenarios.map(s => `<div class="r"><b>${esc(s.name)}</b><span class="hint">${esc(s.detail)}</span>
      ${ids.map(i => { const m = s.moves[i] ?? 0, w = Math.min(100, Math.abs(m) / top * 100); return `<div class="hbrow" style="--c:${color(i)}"><span>${esc(RB[i].name)}</span>
        <div class="hb"><span class="neg" style="--w:${m < 0 ? w : 0}%"></span><span class="pos axis0" style="--w:${m > 0 ? w : 0}%"></span></div><span class="v">${m > 0 ? "+" : ""}${m.toFixed(1)}%</span></div>`; }).join("")}</div>`).join("")}</div>`;
    return;
  }
  const e = ba.episodes.find(x => x.code === S.battle); const F = e.fighters; const xs = F[0].path.map((_, k) => +(k * e.step_days / 252).toFixed(2));
  const win = RB[e.winner];
  el.innerHTML = `<div class="row between"><p><b>${esc(e.name)}</b> · from ${e.start}, ${e.years} years. ${esc(e.story)}</p><span class="winner">${ICON.trophy}${esc(win.name)} wins</span></div>
    ${legendOf(F.map(f => f.id))}<div class="chart" id="e-chart"></div>
    <div class="tablewrap"><table><thead><tr><th>Plan</th><th class="num">Lowest point</th><th class="num">At the end</th><th class="num">Paid each month</th><th>Pay cut?</th></tr></thead><tbody>
    ${F.map(f => `<tr><td><span class="row" style="gap:8px"><span class="dot" style="--c:${color(f.id)}"></span>${esc(RB[f.id].name)}</span></td><td class="num">${f.low.toFixed(0)}% of start</td><td class="num">${f.end.toFixed(0)}% of start</td><td class="num">${money(f.paid)}</td><td>${f.cut ? "Yes" : "No"}</td></tr>`).join("")}
    </tbody></table></div><p class="hint">Money left after paychecks, in today's dollars, as a share of what you started with.</p>`;
  Charts.lines($("#e-chart"), { x: xs, xfmt: x => `year ${+x.toFixed(1)}`, xint: true, yfmt: y => `${Math.round(y)}%`, series: F.map(f => ({ label: RB[f.id].name, short: RB[f.id].name, color: v(f.id), data: f.path })), ref: { y: 100, label: "Start" } });
}

// ------------------------------------------------------------------ SET IT UP
async function setup() {
  const m = RB[S.s] || RB.mp21; S.s = m.id;
  const bar = situationBar(() => { setHash("setup"); paintSetup(); });
  app.innerHTML = `<section class="view"><div class="row between"><h1>Set up ${esc(m.name)}</h1><div class="picker" id="u-pick">${R.filter(r => r.operable).map(r => `<button type="button" data-id="${r.id}" aria-pressed="${r.id === S.s}" style="--c:var(--${r.color})"><span class="dot"></span>${esc(r.name)}</button>`).join("")}</div></div>
    ${bar.html}<div id="u-out">${loading("Getting today's prices…")}</div></section>`;
  bar.wire(); $("#u-pick").onclick = e => { const b = e.target.closest("button"); if (!b) return; S.s = b.dataset.id; setHash("setup"); setup(); };
  paintSetup();
}
function ordersHTML(actions) {
  return actions.map(a => { const [title, icon] = STEP[a.step] || [a.step, ICON.swap];
    const box = a.box ? `<div class="boxorder"><b>One combo order: SELL this ${a.box.width}-point SPX box (this is the loan)</b>${a.box.legs.map(l => `<code>${esc(l)}</code>`).join("")}
      <span>Limit: about <b>${money(a.box.credit)}</b> credit. You owe <b>${money(a.box.face)}</b> on ${a.box.expiry}. Rate ≈ ${(a.box.rate * 100).toFixed(2)}%/yr.</span></div>` : "";
    const tr = a.trades.length ? `<div class="tablewrap"><table><thead><tr><th></th><th>Fund</th><th class="num">Shares</th><th class="num">Price</th><th class="num">Amount</th>${a.trades.some(t => t.tax != null) ? '<th class="num">Est. tax</th>' : ""}</tr></thead><tbody>
      ${a.trades.map(t => `<tr><td class="${t.side === "BUY" ? "trade-buy" : "trade-sell"}">${t.side === "BUY" ? "Buy" : "Sell"}</td><td><b>${esc(t.t)}</b></td><td class="num">${t.shares.toFixed(3)}</td><td class="num">$${t.price.toFixed(2)}</td><td class="num">${money(t.dollars)}</td>${a.trades.some(x => x.tax != null) ? `<td class="num">${t.tax != null ? money(t.tax) : ""}</td>` : ""}</tr>`).join("")}</tbody></table></div>` : "";
    const spend = a.spend != null ? `<p class="big" style="font-size:40px">${money(a.spend)}<small>→ your bank</small></p><p class="small muted">${money(a.base)} from the sales${a.bucket_draw > 0.5 ? ` + ${money(a.bucket_draw)} from bonus savings` : ""}.</p>` : "";
    return `<section class="card action"><div class="t">${icon}<h2>${title}</h2></div>${spend}${box}${tr}<details><summary>Why</summary><p class="small">${esc(a.why)}</p></details></section>`; }).join("");
}
async function paintSetup() {
  const out = $("#u-out"); const m = RB[S.s]; let r;
  if (!m.operable) { out.innerHTML = `<p>This one is for comparing only.</p>`; return; }
  try { r = await api("/api/ops/setup", { id: S.s, amount: S.amount, account: S.acct, bracket: S.br, age: S.age, sex: S.sex }); } catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  const key = `steps:${S.s}`; let done = []; try { done = JSON.parse(localStorage.getItem(key) || "[]"); } catch {}
  out.innerHTML = `<div class="grid two"><section class="stack"><h2>Do these in order</h2><ol class="steps" id="u-steps">${r.steps.map((s, i) => `<li class="${done.includes(i) ? "done" : ""}" data-i="${i}"><div><b>${esc(s.title)}.</b> ${esc(s.text)}</div></li>`).join("")}</ol>
      <p class="hint">Tap a step when it is done.</p></section>
    <section class="stack"><h2>Your first orders <small class="muted">(${r.date} prices)</small></h2><p class="hint">Base paycheck: ${r.base.toFixed(2)}% a year of what you put in, raised with prices. Plans to age ${r.plan_age}.</p>${S.s !== "box" && S.s !== "crash" ? `<section class="card stack"><b>Pie slices</b>${fundList(m.funds)}</section>` : ""}${ordersHTML(r.orders)}
      <section class="card stack"><h2>Save your tracker</h2><div class="row"><label class="field" style="flex:1"><span>Name</span><input id="u-name" value="my-plan"></label><button class="btn go" id="u-create" style="align-self:end">Create tracker</button></div>
      <p class="hint">Only after the orders above are placed. Saved on this computer only.</p></section></section></div>`;
  $("#u-steps").onclick = e => { const li = e.target.closest("li"); if (!li) return; const i = +li.dataset.i; done = done.includes(i) ? done.filter(x => x !== i) : [...done, i]; li.classList.toggle("done");
    try { localStorage.setItem(key, JSON.stringify(done)); } catch {} };
  $("#u-create").onclick = async () => { try { const c = await api("/api/ops/create", { id: S.s, amount: S.amount, account: S.acct, bracket: S.br, age: S.age, sex: S.sex, name: $("#u-name").value });
    S.n = c.name; location.hash = link("today"); toast("Tracker saved."); } catch (e) { toast(e.message, 5000); } };
}

// ------------------------------------------------------------------ TODAY
async function today() {
  let mine = []; try { mine = await api("/api/ops/list"); } catch {}
  if (!mine.length) { app.innerHTML = `<section class="view"><div class="card empty">${ICON.today}<h1>No plan yet</h1><p>Set one up and it will tell you exactly what to do.</p><a class="btn go" href="${link("retire")}">Pay myself</a></div></section>`; return; }
  if (!mine.some(t => t.name === S.n)) S.n = mine[0].name; setHash("today");
  app.innerHTML = `<section class="view"><div class="row between"><h1>Today</h1>
      <div class="row"><label class="field"><span>Plan</span><select id="t-n" class="btn">${mine.map(t => `<option ${t.name === S.n ? "selected" : ""}>${esc(t.name)}</option>`).join("")}</select></label>
      <label class="field"><span>Add money?</span><input id="t-dep" inputmode="numeric" placeholder="$0" style="width:140px"></label><button class="btn" id="t-go" style="align-self:end">Check</button></div></div>
    <div id="t-out">${loading("Getting today's prices…")}</div></section>`;
  $("#t-n").onchange = () => { S.n = $("#t-n").value; today(); };
  $("#t-go").onclick = () => paintToday(num($("#t-dep").value)); paintToday(0);
}
async function paintToday(deposit) {
  const out = $("#t-out"); let r;
  try { r = await api("/api/ops/today", { name: S.n, deposit }); } catch (e) { out.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
  const st = r.status, next = r.calendar[0];
  const todo = r.nothing ? `<section class="card empty">${ICON.check}<h1>Nothing to do today</h1><p>Next: <b>${esc(next.what)}</b> on ${next.date}.</p></section>`
    : `<section class="stack"><h2>To do today</h2>${ordersHTML(r.actions)}<button class="btn go" id="t-done" style="justify-self:start">I placed these trades — save</button></section>`;
  const tiles = [[money(st.net), st.debt ? "your money (funds − loan)" : "account value"], [`${Math.round(st.real_pct)}%`, "of what you started with (today's $)"], [money(st.bucket), "bonus savings"]];
  if (st.debt) tiles.push([money(st.debt), `loan · you own ${st.leverage ? Math.round((st.leverage - 1) * 100) + "% more" : ""} than your money`]);
  if (st.guardrail < 1) tiles.push([`${Math.round(st.guardrail * 100)}%`, "pay level for now (lowered)"]);
  out.innerHTML = `${todo}
    <section class="card"><div class="facts">${tiles.map(([b, s]) => `<div class="fact"><b>${b}</b><span>${s}</span></div>`).join("")}</div></section>
    <div class="grid two">
      <section class="card stack"><h2>Watch list</h2>${r.bonus ? `<p class="small">Bonus: if your money tops <b>${money(r.bonus.line)}</b> in January, the extra goes to bonus savings (${Math.abs(r.bonus.away).toFixed(0)}% to go).</p>` : ""}
      ${r.triggers.map(t => { const a = t.away; const kind = t.kind === "info" ? "good" : a == null ? "good" : Math.abs(a) < 5 ? "bad" : Math.abs(a) < 15 ? "warn" : "good";
        return `<div class="trig"><span>${esc(t.what)} <span class="muted">(${t.dir} ${money(t.line)})</span></span><span class="meter" style="--st:var(--${kind === "bad" ? "critical" : kind})"><i style="--w:${Math.max(4, Math.min(100, 100 - Math.abs(a ?? 0) * 3))}%"></i></span><span class="tab">${a == null ? "" : `${Math.abs(a).toFixed(0)}% away`}</span></div>`; }).join("")}
        <p class="hint">Fuller bar = closer. Look again after any big market day.</p></section>
      <section class="card stack"><h2>Coming up</h2><ul class="cal">${r.calendar.map(c => `<li><b>${c.date}</b><span>${esc(c.what)}</span></li>`).join("")}</ul></section>
    </div>
    <section class="card stack"><h2>What you own</h2><div class="tablewrap"><table><thead><tr><th>Fund</th><th class="num">Shares</th><th class="num">Value</th><th class="num">Now</th><th class="num">Target</th></tr></thead><tbody>
      ${r.holdings.map(h => `<tr><td><b>${esc(h.t)}</b></td><td class="num">${h.shares.toFixed(3)}</td><td class="num">${money(h.value)}</td><td class="num">${h.now.toFixed(1)}%</td><td class="num">${h.target}%</td></tr>`).join("")}</tbody></table></div>
      <details><summary>My broker shows different numbers</summary><div class="ask" id="t-sync" style="margin-top:10px">${r.holdings.map(h => field("sy-" + h.t, h.t + " shares", h.shares.toFixed(4))).join("")}${field("sy-bucket", "Bonus savings $", Math.round(st.bucket))}${st.debt ? field("sy-debt", "Loan owed $", Math.round(st.debt)) : ""}</div>
      <button class="btn" id="t-save" style="margin-top:10px">Save these numbers</button></details></section>
    ${r.paid.length ? `<section class="card stack"><h2>Paid so far</h2><div class="tablewrap"><table><thead><tr><th>Month</th><th class="num">To your bank</th></tr></thead><tbody>${r.paid.slice().reverse().map(p => `<tr><td>${p.month}</td><td class="num">${money(p.spend)}</td></tr>`).join("")}</tbody></table></div></section>` : ""}
    ${r.notes.length ? `<details class="card"><summary>Details</summary><ul>${r.notes.map(n => `<li class="small">${esc(n)}</li>`).join("")}</ul></details>` : ""}`;
  if (!r.nothing) $("#t-done").onclick = async () => { try { await api("/api/ops/commit", { token: r.token }); toast("Saved."); paintToday(0); } catch (e) { toast(e.message, 5000); } };
  $("#t-save").onclick = async () => { const shares = Object.fromEntries(r.holdings.map(h => [h.t, num($("#sy-" + h.t).value)]));
    try { await api("/api/ops/sync", { name: S.n, shares, bucket: num($("#sy-bucket").value), debt: st.debt ? num($("#sy-debt").value) : null }); toast("Saved."); paintToday(0); } catch (e) { toast(e.message, 5000); } };
}

// ------------------------------------------------------------------ router
const VIEWS = { "": home, start, "start-result": startResult, build, retire, compare, setup, today };
async function route() {
  const v = readHash();
  for (const a of document.querySelectorAll("nav.main a[data-v]")) { if (a.dataset.v === v) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); }
  window.scrollTo(0, 0); await (VIEWS[v] || home)();
}
(async () => {
  try { R = await api("/api/roster"); RB = Object.fromEntries(R.map(r => [r.id, r])); } catch { app.innerHTML = `<p class="err">The app server is not running.</p>`; return; }
  addEventListener("hashchange", route); route();
})();
