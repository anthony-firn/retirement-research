/* Charts on uPlot, themed from CSS tokens, rebuilt on resize and theme change.
   lines(el, {x, xfmt, yfmt, series:[{label, color, data, dash}], band:{lo, hi, color}, ref:{y, label}, height})
     - one y-axis; 2px lines; direct labels at the line ends; crosshair + live legend on hover. */
const Charts = (() => {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const live = new Map();
  function mount(el, make) { live.set(el, make); make(); }
  function redraw() { for (const [el, make] of live) { if (el.isConnected) make(); else live.delete(el); } }
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redraw, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", redraw);
  const font = () => `14px ${css("--font")}`;
  const axis = (fmt, size) => ({ stroke: css("--muted"), font: font(), size, grid: { stroke: css("--grid"), width: 1 }, ticks: { stroke: css("--axis"), width: 1 },
    values: (u, v) => v.map(x => (x == null ? "" : fmt(x))) });

  function lines(el, o) {
    mount(el, () => {
      el.innerHTML = ""; const W = Math.max(280, el.clientWidth), H = o.height || 300;
      const S = o.series.map(s => ({ ...s, stroke: css(s.color) }));
      const data = [o.x]; const series = [{ value: (u, v) => (v == null ? "" : o.xfmt(v)) }]; const bands = [];
      if (o.band) {
        data.push(o.band.hi, o.band.lo); const bc = css(o.band.color);
        series.push({ label: o.band.label || "range", stroke: "transparent", points: { show: false }, value: (u, v) => (v == null ? "" : o.yfmt(v)) },
                    { label: "", stroke: "transparent", points: { show: false }, value: () => "" });
        bands.push({ series: [1, 2], fill: bc + "26" });
      }
      for (const s of S) { data.push(s.data); series.push({ label: s.label, stroke: s.stroke, width: 2, dash: s.dash, points: { show: false }, value: (u, v) => (v == null ? "–" : o.yfmt(v)) }); }
      if (o.ref) { data.push(o.x.map(() => o.ref.y)); series.push({ label: o.ref.label, stroke: css("--ink-2"), width: 1.5, dash: [6, 5], points: { show: false }, value: () => o.yfmt(o.ref.y) }); }
      const first = o.band ? 3 : 1;
      const ro = document.createElement("div"); ro.className = "readout";
      const read = i => {                                            // hover readout (and the last point when not hovering)
        if (i == null) { i = o.x.length - 1; }
        ro.innerHTML = `<b>${o.xfmt(o.x[i])}</b>` + S.map(s => `<span><i class="dot" style="--c:${s.stroke}"></i>${s.short || s.label} <b>${s.data[i] == null ? "–" : o.yfmt(s.data[i])}</b></span>`).join("")
          + (o.band ? `<span class="muted">range ${o.yfmt(o.band.lo[i])}–${o.yfmt(o.band.hi[i])}</span>` : "");
      };
      const xaxis = axis(o.xfmt, 40); if (o.xint) xaxis.incrs = [1, 2, 5, 10, 20, 50];
      const opts = { width: W, height: H, padding: [12, 96, 0, 4], legend: { show: false }, scales: { x: { time: false }, y: { range: (u, lo, hi) => [Math.min(0, lo), hi * 1.06] } },
        series, bands, axes: [xaxis, axis(o.yfmt, 76)], cursor: { points: { size: 9 }, drag: { x: false, y: false } },
        hooks: { setCursor: [u => read(u.cursor.idx)], draw: [u => {                                       // direct labels at the right end of each line (text in ink, not series color)
          const ctx = u.ctx, dpr = devicePixelRatio || 1; ctx.save(); ctx.font = `600 ${13 * dpr}px ${css("--font")}`; ctx.textBaseline = "middle";
          const placed = [];
          for (let k = first; k < first + S.length; k++) {
            const d = u.data[k]; let i = d.length - 1; while (i > 0 && d[i] == null) i--;
            const x = u.valToPos(u.data[0][i], "x", true), y0 = u.valToPos(d[i], "y", true); let y = y0;
            for (const p of placed) if (Math.abs(p - y) < 16 * dpr) y = p + 16 * dpr;
            placed.push(y); ctx.fillStyle = S[k - first].stroke; ctx.fillRect(x + 6 * dpr, y - 1.5 * dpr, 10 * dpr, 3 * dpr);
            ctx.fillStyle = css("--ink"); ctx.fillText(S[k - first].short || S[k - first].label, x + 20 * dpr, y);
          }
          if (o.ref) {                                               // the reference line gets its own direct label
            const y = u.valToPos(o.ref.y, "y", true), x = u.bbox.left + u.bbox.width; ctx.fillStyle = css("--ink-2"); ctx.fillText(o.ref.label, x + 8 * dpr, y);
          }
          ctx.restore();
        }] } };
      new uPlot(opts, data, el); el.appendChild(ro); read(null);
      el.setAttribute("role", "img"); el.setAttribute("aria-label", `Chart. ${o.xfmt(o.x[0])} to ${o.xfmt(o.x[o.x.length - 1])}. ` + S.map(s => `${s.label}: ends at ${o.yfmt(s.data[s.data.length - 1])}`).join(". "));
    });
  }
  return { lines, redraw };
})();
