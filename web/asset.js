// Asset page: price history over a chosen range, with the stats a reader checks first.
const RANGES = [[1, "1A", "1Y"], [3, "3A", "3Y"], [5, "5A", "5Y"], [0, null, null]];
const page = { asset: null, years: 3 };

function dateLabel(iso) {
  return new Date(iso).toLocaleDateString(LANG === "fr" ? "fr-FR" : "en-GB", { day: "numeric", month: "short", year: "numeric" });
}
const price = (value) => `${fmt(value, value < 10 ? 3 : 2)} €`;

function windowed(points, years) {
  if (!years) return points;
  const start = new Date(points[points.length - 1][0]);
  start.setFullYear(start.getFullYear() - years);
  const from = start.toISOString().slice(0, 10);
  const kept = points.filter((p) => p[0] >= from);
  return kept.length >= 2 ? kept : points;
}

function stats(points) {
  const values = points.map((p) => p[1]);
  const returns = values.slice(1).map((v, i) => v / values[i] - 1);
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((a, r) => a + (r - mean) ** 2, 0) / Math.max(1, returns.length - 1);
  let peak = values[0]; let worst = 0;
  for (const v of values) { peak = Math.max(peak, v); worst = Math.min(worst, v / peak - 1); }
  return { change: values[values.length - 1] / values[0] - 1, vol: Math.sqrt(variance * 252), drawdown: worst };
}

function render() {
  const a = page.asset;
  const ranges = document.getElementById("ranges");
  ranges.replaceChildren(...RANGES.map(([years, fr, en]) => {
    const button = document.createElement("button");
    button.className = "btn"; button.type = "button";
    button.textContent = years ? (LANG === "fr" ? fr : en) : t("range_max");
    button.setAttribute("aria-pressed", String(years === page.years));
    button.addEventListener("click", () => { page.years = years; render(); });
    return button;
  }));
  if (a.prices.length < 2) { document.getElementById("change").textContent = t("asset_missing"); return; }

  const points = windowed(a.prices, page.years);
  const s = stats(points);
  const change = document.getElementById("change");
  change.className = `big-change num ${s.change >= 0 ? "up" : "down"}`;
  change.replaceChildren(pct(s.change, 1));
  const sub = document.createElement("small");
  sub.textContent = `${t("asset_change")} · ${dateLabel(points[0][0])} – ${dateLabel(points[points.length - 1][0])}`;
  change.append(sub);
  lineChart(document.getElementById("chart"), points, { date: dateLabel, price });

  const last = points[points.length - 1];
  const cards = [
    [t("stat_last"), price(last[1])],
    [t("stat_vol"), pct(s.vol, 1, false)],
    [t("stat_dd"), pct(s.drawdown, 1)],
    [t("stat_class"), a.risk_class ? `${a.risk_class}/7` : "–"],
  ];
  document.getElementById("stats").replaceChildren(...cards.map(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat glass";
    card.innerHTML = "<small></small><b class=\"num\"></b>";
    card.querySelector("small").textContent = label;
    card.querySelector("b").textContent = value;
    return card;
  }));
}

function renderWhy() {
  let view = null;
  try { view = JSON.parse(sessionStorage.getItem("lastResult")); } catch (_) { /* no stored result */ }
  const items = view?.result?.items || [];
  const rank = items.findIndex((item) => item.isin === page.asset.isin);
  const box = document.getElementById("why");
  if (rank < 0) { box.hidden = true; return; }
  const item = items[rank];
  const ceiling = view.result.profile.ceiling;
  const lines = [t("why_rank", { rank: rank + 1 }), t("why_risk", { risk: item.risk_class, ceiling })];
  if (item.variance_change !== null) {
    lines.push(t(item.variance_change < 0 ? "why_var_down" : "why_var_up", { v: fmt(Math.abs(item.variance_change), 4) }));
  }
  const title = document.createElement("h2");
  title.textContent = t("why_title");
  const list = document.createElement("ul");
  list.append(...lines.map((line) => { const li = document.createElement("li"); li.textContent = line; return li; }));
  box.replaceChildren(title, list);
  box.hidden = false;
}

function renderHeader() {
  const a = page.asset;
  document.getElementById("name").textContent = a.name;
  document.title = `${a.name} · ${BRAND}`;
  const category = a.category ? t(`cat_${a.category}`) : null;
  document.getElementById("meta").textContent = [...new Set([a.isin, category, a.subcategory, a.sector].filter(Boolean))].join(" · ");
}

document.addEventListener("DOMContentLoaded", async () => {
  const params = new URLSearchParams(location.search);
  const isin = params.get("isin") || "";
  if (params.get("from") === "assets") {  // came from the catalogue, not from the suggestions
    const back = document.querySelector(".back");
    back.href = "assets.html"; back.dataset.i18n = "back_assets"; back.textContent = t("back_assets");
  }
  try {
    const response = await fetch(`asset/${encodeURIComponent(isin)}`);
    if (!response.ok) throw new Error(String(response.status));
    page.asset = await response.json();
  } catch (_) {
    document.getElementById("name").textContent = t("asset_missing");
    return;
  }
  renderHeader(); render(); renderWhy();
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
});
document.addEventListener("langchange", () => { if (page.asset) { renderHeader(); render(); renderWhy(); } });
