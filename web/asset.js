// Asset page: price history over a chosen range, with the stats a reader checks first.
const RANGES = [[1, "1A", "1Y"], [3, "3A", "3Y"], [5, "5A", "5Y"], [0, null, null]];
const page = { asset: null, years: 3, recommendation: null, explanation: null, explaining: false, explanationError: null };

function dateLabel(iso) {
  return new Date(iso).toLocaleDateString(LANG === "fr" ? "fr-FR" : "en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}
const price = (value) => `${fmt(value, value < 10 ? 3 : 2)} €`;

function windowed(points, years) {
  if (!years || !points.length) return points;
  const start = new Date(points[points.length - 1][0]);
  start.setUTCFullYear(start.getUTCFullYear() - years);
  const from = start.toISOString().slice(0, 10);
  return points.filter((p) => p[0] >= from);
}

function stats(points) {
  const values = points.map((p) => p[1]);
  const returns = values.slice(1).map((v, i) => v / values[i] - 1);
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((a, r) => a + (r - mean) ** 2, 0) / Math.max(1, returns.length - 1);
  let peak = values[0]; let worst = 0;
  for (const v of values) { peak = Math.max(peak, v); worst = Math.min(worst, v / peak - 1); }
  return { change: values[values.length - 1] / values[0] - 1,
    vol: returns.length > 1 ? Math.sqrt(variance * 252) : null, drawdown: worst };
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
  const points = windowed(a.prices, page.years);
  const change = document.getElementById("change");
  const chart = document.getElementById("chart");
  const cardsBox = document.getElementById("stats");
  if (points.length < 2) {
    change.className = "big-change num";
    change.textContent = t(a.prices.length ? "asset_range_unavailable" : "asset_missing");
    chart.replaceChildren();
    cardsBox.replaceChildren();
    return;
  }

  const s = stats(points);
  change.className = `big-change num ${s.change >= 0 ? "up" : "down"}`;
  change.replaceChildren(pct(s.change, 1));
  const sub = document.createElement("small");
  const samples = t("asset_samples", { n: fmt(points.length) });
  sub.textContent = `${t("asset_change")} · ${dateLabel(points[0][0])} – ${dateLabel(points[points.length - 1][0])} · ${samples}`;
  change.append(sub);
  lineChart(chart, points, { date: dateLabel, price });

  const last = points[points.length - 1];
  const cards = [
    [t("stat_last"), price(last[1])],
    [t("stat_vol"), s.vol === null ? "–" : pct(s.vol, 1, false)],
    [t("stat_dd"), pct(s.drawdown, 1)],
    [t("stat_class"), a.risk_class ? `${a.risk_class}/7` : "–"],
  ];
  cardsBox.replaceChildren(...cards.map(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat glass";
    card.innerHTML = "<small></small><b class=\"num\"></b>";
    card.querySelector("small").textContent = label;
    card.querySelector("b").textContent = value;
    return card;
  }));
}

function storedRecommendation(params, isin) {
  const id = params.get("rec");
  if (!id || params.get("from") === "assets") return null;
  let view = null;
  try { view = JSON.parse(sessionStorage.getItem("lastResult")); } catch (_) { return null; }
  const result = view?.result;
  if (!result || id !== result.recommendation_id || typeof view.session !== "string" || !Array.isArray(result.items)) return null;
  const index = result.items.findIndex((item) => item.isin === isin);
  return index < 0 ? null : { id, session: view.session, item: result.items[index], rank: index + 1,
    rankingSource: result.ranking_source, ceiling: result.profile.ceiling };
}

async function requestExplanation() {
  const current = page.recommendation;
  if (!current || page.explaining) return;
  page.explaining = true;
  page.explanationError = null;
  renderWhy();
  try {
    const response = await fetch("explain", {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: AbortSignal.timeout(22000),
      body: JSON.stringify({ recommendation_id: current.id, session_id: current.session, isin: current.item.isin }),
    });
    if (response.status === 404) { page.explanationError = "why_explain_expired"; return; }
    if (!response.ok) throw new Error(`explain ${response.status}`);
    const explanation = await response.json();
    const supported = explanation.source === "template" || (explanation.source === "llm" && explanation.status === "verified");
    if (!supported || explanation.isin !== current.item.isin || typeof explanation.explanation !== "string") {
      throw new Error("Unexpected explanation response");
    }
    page.explanation = explanation;
  } catch (_) {
    page.explanationError = "why_explain_error";
  } finally {
    page.explaining = false;
    renderWhy();
  }
}

function renderWhy() {
  const box = document.getElementById("why");
  const current = page.recommendation;
  if (!current) { box.hidden = true; return; }
  const { item, rankingSource, ceiling, rank } = current;
  const lines = [t("why_position", { rank })];
  if (rankingSource === "popularity") lines.push(t("why_popularity"));
  if (rankingSource === "portfolio_embeddings") lines.push(t("why_portfolio"));
  const explanation = page.explanation;
  if (!explanation) {
    lines.push(t("why_risk", { risk: item.risk_class, ceiling }));
    if (Number.isFinite(item.variance_change)) {
      const delta = Number(item.variance_change.toFixed(4)) || 0;
      lines.push(t("why_var_change", { v: `${delta > 0 ? "+" : ""}${fmt(delta, 4)}` }));
    }
  }
  const source = explanation ? (explanation.source === "llm" ? "why_source_llm" : "why_source_template") : "why_source_facts";
  const expired = page.explanationError === "why_explain_expired";
  const button = explanation || expired ? null : el("button", { class: "btn", type: "button", onclick: requestExplanation },
    t(page.explaining ? "why_explaining" : "why_explain"));
  if (button) button.disabled = page.explaining;
  const content = [
    el("h2", {}, t("why_title")),
    el("ul", {}, ...lines.map((line) => el("li", {}, line))),
    explanation ? el("p", { lang: "fr" }, explanation.explanation) : null,
    el("p", { class: "footnote" }, t(source)),
    button,
    page.explanationError ? el("p", { class: "footnote" }, t(page.explanationError)) : null,
  ];
  box.replaceChildren(...content.filter(Boolean));
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
  if (params.get("from") === "assets" || !params.has("rec")) {
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
  page.recommendation = storedRecommendation(params, page.asset.isin);
  renderHeader(); render(); renderWhy();
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); });
});
document.addEventListener("langchange", () => { if (page.asset) { renderHeader(); render(); renderWhy(); } });
