// Hero graph: every dot is a real catalogue asset, stacked in its risk class (1-7).
// Client-to-asset links are illustrative. The slider moves the risk ceiling live.
const GRAPH = { width: 600, height: 440, base: 392, top: 132, gap: 8.6, perRow: 8, clients: 12 };
const RISK_COLORS = ["#2B6CB0", "#2A9D8F", "#6FA35A", "#D9A033", "#E07A3F", "#C8553D", "#8E2C48"];

const graph = { assets: [], edges: [], svg: null, ceiling: 4 };

function laneX(k) {
  return 30 + (k - 0.5) * ((GRAPH.width - 30) / 7);
}

function seeded(seed) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

function buildGraph(catalog) {
  const byClass = new Map();
  for (const asset of catalog) {
    const k = Number(asset.risk_class);
    if (k >= 1 && k <= 7) byClass.set(k, [...(byClass.get(k) || []), asset]);
  }
  const maxRows = Math.floor((GRAPH.base - GRAPH.top) / GRAPH.gap);
  const width = (GRAPH.perRow - 1) * GRAPH.gap;
  const dots = [];
  for (let k = 1; k <= 7; k += 1) {
    const list = (byClass.get(k) || []).slice(0, maxRows * GRAPH.perRow);
    list.forEach((asset, i) => {
      const row = Math.floor(i / GRAPH.perRow);
      const col = i % GRAPH.perRow;
      dots.push({ k, row, name: asset.name, x: laneX(k) - width / 2 + col * GRAPH.gap, y: GRAPH.base - row * GRAPH.gap });
    });
  }
  const rnd = seeded(11);
  const edges = [];
  for (let c = 0; c < GRAPH.clients; c += 1) {
    const cx = 60 + c * ((GRAPH.width - 90) / (GRAPH.clients - 1));
    for (let m = 0; m < 3 && dots.length; m += 1) edges.push({ cx, dot: dots[Math.floor(rnd() * dots.length)] });
  }
  return { dots, edges, total: catalog.length };
}

function drawGraph(data) {
  const box = document.getElementById("graph");
  const svg = svgEl("svg", { viewBox: `0 0 ${GRAPH.width} ${GRAPH.height}`, role: "img" });
  const shade = svgEl("rect", { class: "g-shade", y: GRAPH.top - 18, height: GRAPH.base - GRAPH.top + 30, rx: 10 });
  svg.append(shade);

  const clientsY = 34;
  const label = (x, y, key, anchor = "start") => {
    const node = svgEl("text", { x, y, class: "g-label", "text-anchor": anchor, "data-key": key });
    svg.append(node);
    return node;
  };
  label(0, 14, "graph_clients");

  data.edges.forEach((edge, i) => {
    const d = edge.dot;
    edge.node = svgEl("path", {
      class: "g-edge", d: `M${edge.cx} ${clientsY + 6} C ${edge.cx} ${clientsY + 70}, ${d.x} ${d.y - 90}, ${d.x} ${d.y}`,
      pathLength: 1, style: `--delay: ${(i * 0.025).toFixed(3)}s`,
    });
    svg.append(edge.node);
  });
  const clientXs = [...new Set(data.edges.map((e) => e.cx))];
  clientXs.forEach((x, i) => svg.append(svgEl("circle", { class: "g-client", cx: x, cy: clientsY, r: 6.5, style: `--delay: ${(i * 0.04).toFixed(2)}s` })));

  data.dots.forEach((dot) => {
    dot.node = svgEl("circle", {
      class: "g-dot", cx: dot.x.toFixed(1), cy: dot.y.toFixed(1), r: 3.1, fill: RISK_COLORS[dot.k - 1],
      style: `--delay: ${(0.35 + dot.row * 0.035 + dot.k * 0.02).toFixed(3)}s`,
    });
    const title = svgEl("title");
    title.textContent = dot.name;
    dot.node.append(title);
    svg.append(dot.node);
  });

  for (let k = 1; k <= 7; k += 1) {
    const text = svgEl("text", { x: laneX(k), y: GRAPH.height - 18, class: "g-lane num", "text-anchor": "middle", fill: RISK_COLORS[k - 1] });
    text.textContent = String(k);
    const lane = data.dots.filter((dot) => dot.k === k);
    const top = Math.min(GRAPH.base, ...lane.map((dot) => dot.y));
    const count = svgEl("text", { x: laneX(k), y: top - 10, class: "g-count num", "text-anchor": "middle" });
    count.textContent = String(lane.length);
    svg.append(text, count);
  }
  label(GRAPH.width / 2, GRAPH.height - 1, "graph_axis", "middle");

  const line = svgEl("line", { class: "g-ceiling", y1: GRAPH.top - 24, y2: GRAPH.base + 14 });
  svg.append(line);
  box.replaceChildren(svg);
  Object.assign(graph, { svg, shade, line, data });
  requestAnimationFrame(() => box.classList.add("ready"));
}

function updateCeiling() {
  if (!graph.svg) return;
  const k = graph.ceiling;
  const x = k >= 7 ? GRAPH.width : (laneX(k) + laneX(k + 1)) / 2;
  graph.line.setAttribute("x1", x); graph.line.setAttribute("x2", x);
  graph.line.style.opacity = k >= 7 ? 0 : 1;
  graph.shade.setAttribute("x", x); graph.shade.setAttribute("width", Math.max(0, GRAPH.width - x));
  let kept = 0;
  for (const dot of graph.data.dots) {
    const out = dot.k > k;
    dot.node.classList.toggle("out", out);
    if (!out) kept += 1;
  }
  for (const edge of graph.data.edges) edge.node.classList.toggle("out", edge.dot.k > k);
  graph.svg.setAttribute("aria-label", t("graph_label"));
  graph.svg.querySelectorAll("[data-key]").forEach((node) => { node.textContent = t(node.dataset.key); });
  document.getElementById("ceiling-label").textContent = t("ceiling_label", { n: k });
  document.getElementById("graph-caption").textContent = t("graph_caption", { kept: fmt(kept), total: fmt(graph.data.dots.length) });
}

document.addEventListener("DOMContentLoaded", async () => {
  const slider = document.getElementById("ceiling");
  slider.addEventListener("input", () => { graph.ceiling = Number(slider.value); updateCeiling(); });
  try {
    drawGraph(buildGraph(await api("assets")));
    updateCeiling();
  } catch (_) {
    document.getElementById("graph-card").hidden = true;  // no API: the copy still stands on its own
  }
});

document.addEventListener("langchange", updateCeiling);
