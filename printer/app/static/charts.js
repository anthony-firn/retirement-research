/* Chart helpers on uPlot: themed from the page's CSS tokens, rebuilt on resize and theme change.
   line(el, {x, series:[{label, data, i}], fmt, log, height})   time-series lines; series i picks --s1..--s4 (the 4th is dashed ink)
   fan(el, {x, q, rows, fmt, height})                            percentile bands (5-95, 25-75) + median, x = years from now
   bars(canvas, {groups, series:[{label, data, i}], fmt})        grouped bars (annual returns) with a hover readout */
const Charts = (() => {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const color = i => css(`--s${i + 1}`);
  const dash = i => (i === 3 ? [6, 4] : undefined);
  const live = new Map();                                                       // el -> {make}
  const font = () => `11px ${css("--f-data")}`;
  const axis = (fmt, size = 64, space = 40) => ({ stroke: css("--ink-3"), font: font(), size, space, grid: { stroke: css("--line"), width: 1 }, ticks: { stroke: css("--line"), width: 1 },
    values: fmt ? (u, s) => s.map(v => (v == null ? "" : fmt(v))) : undefined });

  function mount(el, make) { live.set(el, make); make(); }
  function redraw() { for (const [el, make] of live) if (el.isConnected) make(); }
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redraw, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", redraw);

  function line(el, o) {
    mount(el, () => {
      el.innerHTML = ""; const W = el.clientWidth || 600, H = o.height || el.clientHeight || 260;
      const opts = { width: W, height: H, padding: [8, 8, 0, 0], legend: { live: true },
        scales: { x: { time: o.time !== false }, y: o.log ? { distr: 3 } : { range: o.range } },
        series: [{ value: o.time !== false ? (u, v) => (v == null ? "" : new Date(v * 1000).toISOString().slice(0, 10)) : undefined },
          ...o.series.map(s => ({ label: s.label, stroke: color(s.i), width: s.i === 0 ? 2.2 : 1.7, dash: dash(s.i), points: { show: false },
            value: (u, v) => (v == null ? "–" : o.fmt(v)) }))],
        axes: [axis(o.xfmt, 36, 60), axis(o.fmt, o.ysize || 70, o.log ? 34 : 30)],
        cursor: { drag: { x: true, y: false }, points: { size: 7 } } };
      new uPlot(opts, [o.x, ...o.series.map(s => s.data)], el);
    });
  }

  function fan(el, o) {
    mount(el, () => {
      el.innerHTML = ""; const W = el.clientWidth || 400, H = o.height || 230, r = o.rows;   // rows: [p5, p10, p25, p50, p75, p90, p95]
      const none = "rgba(0,0,0,0)";
      const opts = { width: W, height: H, padding: [8, 22, 0, 0], legend: { show: false },
        scales: { x: { time: false } },
        series: [{}, ...[1, 2, 3, 4].map(() => ({ stroke: none, points: { show: false } })), { label: "Typical", stroke: css("--accent"), width: 2, points: { show: false } }],
        bands: [{ series: [2, 1], fill: css("--band1") }, { series: [4, 3], fill: css("--band2") }],
        axes: [axis(v => `${v} yr`, 32, 50), axis(o.fmt, 70)],
        cursor: { points: { show: false } },
        hooks: { setCursor: [u => { const i = u.cursor.idx; if (o.onHover) o.onHover(i == null ? null : i); }] } };
      new uPlot(opts, [o.x, r[0], r[6], r[2], r[4], r[3]], el);
    });
  }

  function bars(cv, o) {
    const draw = (hover = null) => {
      const dpr = Math.min(2, devicePixelRatio || 1), W = cv.clientWidth, H = cv.clientHeight, ctx = cv.getContext("2d");
      cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const m = { l: 56, r: 8, t: 10, b: 26 }, n = o.groups.length, k = o.series.length;
      const all = o.series.flatMap(s => s.data).filter(v => v != null); let lo = Math.min(0, ...all), hi = Math.max(0, ...all); const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
      const Y = v => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b), gw = (W - m.l - m.r) / n, bw = Math.max(1, Math.min(14, (gw * 0.8 - (k - 1) * 2) / k));
      ctx.font = font(); ctx.fillStyle = css("--ink-3"); ctx.strokeStyle = css("--line"); ctx.textAlign = "right";
      const step = niceStep(hi - lo, 5);
      for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) { const y = Y(v); ctx.beginPath(); ctx.moveTo(m.l, y); ctx.lineTo(W - m.r, y); ctx.stroke(); ctx.fillText(o.fmt(v), m.l - 6, y + 3.5); }
      ctx.strokeStyle = css("--ink-3"); ctx.beginPath(); ctx.moveTo(m.l, Y(0)); ctx.lineTo(W - m.r, Y(0)); ctx.stroke();
      ctx.textAlign = "center"; const every = Math.ceil(n / Math.max(1, Math.floor((W - m.l) / 44)));
      o.groups.forEach((g, gi) => {
        const x0 = m.l + gi * gw + (gw - (k * bw + (k - 1) * 2)) / 2;
        if (gi === hover) { ctx.fillStyle = css("--accent-soft"); ctx.fillRect(m.l + gi * gw, m.t, gw, H - m.t - m.b); }
        o.series.forEach((s, si) => {
          const v = s.data[gi]; if (v == null) return; const x = x0 + si * (bw + 2), y0 = Y(0), y1 = Y(v);
          ctx.fillStyle = color(s.i); const top = Math.min(y0, y1), h = Math.max(1, Math.abs(y1 - y0)); roundRect(ctx, x, top, bw, h, Math.min(3, bw / 2), v >= 0);
        });
        if (gi % every === 0) { ctx.fillStyle = css("--ink-3"); ctx.fillText(String(g), m.l + gi * gw + gw / 2, H - 8); }
      });
      return { m, gw };
    };
    let geo = draw();
    cv.onpointermove = e => { const r = cv.getBoundingClientRect(), gi = Math.floor((e.clientX - r.left - geo.m.l) / geo.gw); const ok = gi >= 0 && gi < o.groups.length; geo = draw(ok ? gi : null); o.onHover?.(ok ? gi : null, e); };
    cv.onpointerleave = () => { geo = draw(); o.onHover?.(null); };
    live.set(cv, () => { geo = draw(); });
  }
  function roundRect(ctx, x, y, w, h, r, up) {
    ctx.beginPath();
    if (up) { ctx.moveTo(x, y + h); ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r); ctx.lineTo(x + w, y + h); }
    else { ctx.moveTo(x, y); ctx.lineTo(x, y + h - r); ctx.quadraticCurveTo(x, y + h, x + r, y + h); ctx.lineTo(x + w - r, y + h); ctx.quadraticCurveTo(x + w, y + h, x + w, y + h - r); ctx.lineTo(x + w, y); }
    ctx.closePath(); ctx.fill();
  }
  function niceStep(span, n) { const s0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(s0))); return [1, 2, 2.5, 5, 10].map(m => m * mag).find(m => span / m <= n) || mag * 10; }
  return { line, fan, bars, color, dash, niceStep, redraw };
})();
