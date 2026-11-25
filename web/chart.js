// Hand-drawn SVG charts: no library, so the site works offline.
const SVG = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

let gradientId = 0;
function areaGradient(svg, color) {
  const id = `g${gradientId += 1}`;
  const gradient = svgEl("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 });
  gradient.append(svgEl("stop", { offset: "0%", "stop-color": color, "stop-opacity": .28 }),
    svgEl("stop", { offset: "100%", "stop-color": color, "stop-opacity": 0 }));
  const defs = svgEl("defs");
  defs.append(gradient);
  svg.append(defs);
  return `url(#${id})`;
}

function scale(points, width, height, pad) {
  const values = points.map((p) => p[1]);
  const min = Math.min(...values); const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i) => pad.left + (i / (points.length - 1)) * (width - pad.left - pad.right);
  const y = (v) => pad.top + (1 - (v - min) / span) * (height - pad.top - pad.bottom);
  return { x, y, min, max };
}

function sparkline(points, up) {
  const width = 150; const height = 44;
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "spark", "aria-hidden": "true", preserveAspectRatio: "none" });
  if (points.length < 2) return svg;
  const color = up ? "#3fd492" : "#ff5d52";
  const { x, y } = scale(points, width, height, { top: 4, bottom: 4, left: 1, right: 1 });
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  svg.append(svgEl("path", { d: `${line}L${x(points.length - 1)},${height}L${x(0)},${height}Z`, fill: areaGradient(svg, color) }),
    svgEl("path", { d: line, fill: "none", stroke: color, "stroke-width": 1.6, "stroke-linejoin": "round", "vector-effect": "non-scaling-stroke" }));
  return svg;
}

// Detail chart with a crosshair that follows the pointer.
function lineChart(container, points, format) {
  container.replaceChildren();
  const width = container.clientWidth || 900; const height = container.clientHeight || 380;
  const pad = { top: 16, bottom: 30, left: 4, right: 56 };
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });
  const up = points[points.length - 1][1] >= points[0][1];
  const color = up ? "#3fd492" : "#ff5d52";
  const { x, y, min, max } = scale(points, width, height, pad);

  for (let k = 0; k <= 3; k += 1) {  // four quiet price levels on the right
    const value = min + ((max - min) * k) / 3;
    svg.append(svgEl("line", { x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value), stroke: "rgba(255,255,255,.06)" }));
    const label = svgEl("text", { x: width - pad.right + 10, y: y(value) + 4, fill: "#8a8a88", "font-size": 12 });
    label.textContent = format.price(value);
    svg.append(label);
  }
  const years = [...new Set(points.map((p) => p[0].slice(0, 4)))];
  for (const year of years.slice(1)) {  // a tick at each new year
    const i = points.findIndex((p) => p[0].startsWith(year));
    const label = svgEl("text", { x: x(i), y: height - 8, fill: "#8a8a88", "font-size": 12, "text-anchor": "middle" });
    label.textContent = year;
    svg.append(label);
  }

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  svg.append(svgEl("path", { d: `${line}L${x(points.length - 1)},${height - pad.bottom}L${x(0)},${height - pad.bottom}Z`, fill: areaGradient(svg, color) }),
    svgEl("path", { d: line, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round" }));

  const cross = svgEl("line", { y1: pad.top, y2: height - pad.bottom, stroke: "rgba(255,255,255,.35)", visibility: "hidden" });
  const dot = svgEl("circle", { r: 4.5, fill: color, stroke: "#000", "stroke-width": 2, visibility: "hidden" });
  svg.append(cross, dot);
  const tip = document.createElement("div");
  tip.className = "tip glass";
  tip.hidden = true;
  container.append(svg, tip);

  svg.addEventListener("pointermove", (event) => {
    const box = svg.getBoundingClientRect();
    const px = ((event.clientX - box.left) / box.width) * width;
    const i = Math.max(0, Math.min(points.length - 1, Math.round(((px - pad.left) / (width - pad.left - pad.right)) * (points.length - 1))));
    const cx = x(i); const cy = y(points[i][1]);
    for (const node of [cross, dot]) node.setAttribute("visibility", "visible");
    cross.setAttribute("x1", cx); cross.setAttribute("x2", cx);
    dot.setAttribute("cx", cx); dot.setAttribute("cy", cy);
    tip.hidden = false;
    tip.style.left = `${(cx / width) * 100}%`;
    tip.style.top = `${(cy / height) * 100}%`;
    tip.textContent = `${format.date(points[i][0])} · ${format.price(points[i][1])}`;
  });
  svg.addEventListener("pointerleave", () => {
    for (const node of [cross, dot]) node.setAttribute("visibility", "hidden");
    tip.hidden = true;
  });
}
