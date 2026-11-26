// One-pager: describe the portfolio in words, get ranked suggestions with their price trend.
const QUESTIONS = ["horizon", "goal", "loss", "experience"];
const LAST_RESULT = "lastResult";

// randomUUID only exists on secure origins; the booth may serve over a LAN IP.
function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

function store(key, value) {
  try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* storage blocked: the asset page just skips the reasons */ }
}
function load(key) {
  try { return JSON.parse(sessionStorage.getItem(key)); } catch (_) { return null; }
}

const state = {
  session: load("session") || uuid(), catalog: [], chips: {}, answers: Object.fromEntries(QUESTIONS.map((q) => [q, 1])),
  years: 3, view: null, feedback: false, active: -1,
};
store("session", state.session);

const logEvent = (event) => api("log_interaction", { session_id: state.session, event }).catch(() => {});


const normalize = (text) => text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const LEGAL = /\b(s ?a|plc|ag|nv|inc|ltd|holdings?|group|the)\b/g;
const core = (name) => normalize(name).replace(LEGAL, " ").replace(/\s+/g, " ").trim();

/* ---------- Search box: autocomplete assets into chips ---------- */

function fragment() {
  const text = document.getElementById("query").value;
  return normalize(text.split(/,|;|\bet\b|\band\b/i).pop() || "");
}

function matches(query) {
  if (query.length < 3) return [];
  return state.catalog.filter((a) => !(a.isin in state.chips)
    && (normalize(a.name).includes(query) || a.isin.toLowerCase().startsWith(query))).slice(0, 6);
}

function renderSuggest() {
  const list = document.getElementById("suggest");
  const input = document.getElementById("query");
  const found = matches(fragment());
  state.suggestions = found;
  list.hidden = !found.length;
  input.setAttribute("aria-expanded", String(found.length > 0));
  list.replaceChildren(...found.map((asset, i) => el("li", {
    role: "option", id: `opt-${i}`, "aria-selected": String(i === state.active),
    onmousedown: (e) => { e.preventDefault(); addChip(asset); },
  }, el("span", {}, asset.name), el("small", {}, asset.isin))));
  input.setAttribute("aria-activedescendant", state.active >= 0 ? `opt-${state.active}` : "");
}

function addChip(asset) {
  state.chips[asset.isin] = asset.name;
  const input = document.getElementById("query");
  const parts = input.value.split(/(,|;)/);  // drop the half-typed fragment that picked the asset
  parts[parts.length - 1] = "";
  input.value = parts.join("").replace(/[,;]\s*$/, "").trim();
  state.active = -1;
  renderChips(); renderSuggest(); input.focus();
}

function renderChips() {
  document.getElementById("chips").replaceChildren(...Object.entries(state.chips).map(([isin, name]) =>
    el("span", { class: "chip glass" }, name,
      el("button", { type: "button", "aria-label": `${t("remove")} ${name}`,
        onclick: () => { delete state.chips[isin]; renderChips(); } }, "×"))));
}

// Assets named in full in the free text count as holdings too.
function namedInText(text) {
  const words = ` ${normalize(text)} `;
  return state.catalog.filter((a) => { const c = core(a.name); return c.length >= 6 && words.includes(` ${c} `); });
}

function renderOptions() {
  const selects = QUESTIONS.map((q) => {
    const select = el("select", { onchange: (e) => { state.answers[q] = Number(e.target.value); } },
      ...[0, 1, 2].map((i) => el("option", { value: String(i) }, t(`q_${q}_${i}`))));
    select.value = String(state.answers[q]);
    return el("label", {}, t(`q_${q}`), select);
  });
  const years = el("select", { onchange: (e) => { state.years = Number(e.target.value); } },
    ...[1, 3, 5].map((n) => el("option", { value: String(n) }, t(n === 1 ? "years" : "years_plural", { n }))));
  years.value = String(state.years);
  document.getElementById("option-grid").replaceChildren(...selects, el("label", {}, t("chart_years"), years));
}

/* ---------- Request ---------- */

async function submit(event) {
  event.preventDefault();
  const text = document.getElementById("query").value.trim();
  for (const asset of namedInText(text)) state.chips[asset.isin] = asset.name;
  renderChips();
  const holdings = Object.fromEntries(Object.keys(state.chips).map((isin) => [isin, 1000]));
  const payload = { holdings, answers: { ...state.answers }, free_text: text, session_id: state.session };

  const go = document.getElementById("go");
  const error = document.getElementById("error");
  go.disabled = true; go.replaceChildren(document.getElementById("loader").content.cloneNode(true), t("busy")); error.hidden = true;
  try {
    let result = await api("recommend", payload);
    let review = null;
    if (text && result.profile_review_available) {  // the local model reads the text, then the ranking is refreshed
      logEvent("profile_review_requested");
      review = await api("profile", payload).catch(() => null);
      if (review) result = await api("recommend", payload);
    }
    const isins = result.items.map((item) => item.isin).join(",");
    const prices = isins ? await api(`prices?isins=${isins}&years=${state.years}`).catch(() => ({})) : {};
    state.view = { result, prices, years: state.years, review, typedText: Boolean(text) };
    state.feedback = false;
    store(LAST_RESULT, state.view);
    logEvent("portfolio_entered"); logEvent("recommendation_viewed");
    renderResults();
    document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (_) {
    error.textContent = t("err_recommend"); error.hidden = false;
  }
  go.disabled = false; go.textContent = t("go");
}

/* ---------- Results ---------- */

function renderResults() {
  const box = document.getElementById("results");
  if (!state.view) { box.hidden = true; return; }
  const { result, prices, years } = state.view;
  const p = result.profile;
  const notes = [];
  if (result.ranking_source === "popularity") notes.push(t("popularity"));
  if (state.view.typedText && state.view.review?.status === "rules_fallback") notes.push(t("text_rules"));

  const rows = result.items.map((item, i) => {
    const series = prices[item.isin];
    const up = series ? series.change >= 0 : true;
    return el("a", { class: "row", href: `asset.html?isin=${encodeURIComponent(item.isin)}` },
      el("span", { class: "rank num" }, String(i + 1)),
      el("span", { class: "name" }, item.name, el("small", {}, item.isin)),
      el("span", { class: "risk" }, el("b", { class: "num" }, `${item.risk_class}/7`), el("br"), t("risk")),
      series ? sparkline(series.points, up) : el("span"),
      series ? el("span", { class: `change num ${up ? "up" : "down"}` }, pct(series.change),
        el("small", {}, t(years === 1 ? "over_1" : "over", { n: years }))) : el("span"));
  });

  box.hidden = false;
  box.replaceChildren(
    el("div", { class: "results-head" },
      el("h2", {}, t("results_title", { n: result.items.length })),
      el("p", {}, t("results_profile", { level: t(`level_${p.risk_level}`), ceiling: p.ceiling }))),
    ...notes.map((note) => el("p", { class: "footnote" }, note)),
    result.items.length ? el("div", { class: "rows glass" }, ...rows) : el("p", { class: "footnote" }, t("none")),
    el("div", { class: "feedback" }, ...(state.feedback ? [t("fb_thanks")] : [
      el("span", {}, t("fb_q")),
      el("button", { class: "btn", type: "button", onclick: () => sendFeedback("feedback_positive") }, t("fb_yes")),
      el("button", { class: "btn", type: "button", onclick: () => sendFeedback("feedback_negative") }, t("fb_no"))])),
    el("p", { class: "footnote" }, t("footnote")),
  );
}

function sendFeedback(event) {
  logEvent(event);
  state.feedback = true;
  renderResults();
}

/* ---------- Hero preview: the real answer to the example query ---------- */

async function renderPreview() {
  const box = document.getElementById("preview-rows");
  try {
    const result = await api("recommend", { holdings: { GRS003003035: 1000 }, answers: { ...state.answers } });
    const items = result.items.slice(0, 3);
    const prices = await api(`prices?isins=${items.map((i) => i.isin).join(",")}&years=3`).catch(() => ({}));
    box.replaceChildren(...items.map((item) => {
      const series = prices[item.isin];
      const up = series ? series.change >= 0 : true;
      return el("div", { class: "preview-row" },
        el("span", {}, el("b", {}, item.name), el("small", {}, `${item.isin} · ${item.risk_class}/7`)),
        series ? sparkline(series.points, up) : el("span"),
        el("span", { class: `change num ${up ? "up" : "down"}` }, series ? pct(series.change) : ""));
    }));
  } catch (_) { box.closest(".preview").hidden = true; }
}

/* ---------- How it works: one sequence when the section comes into view ---------- */

const HOW_ASSET = "GRF000045002";  // real example: DHLOS Synthesis fund, shown with its real 3-year trend
const how = { played: false, change: null, risk: 5 };

function countTo(node, from, to, ms, render) {
  const start = performance.now();
  node.textContent = render(from);
  const tick = (now) => {
    const k = Math.min(1, (now - start) / ms);
    node.textContent = render(from + (to - from) * (1 - (1 - k) ** 3));
    if (k < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function howFinal() {  // static end state: reduced motion, language change, or already played
  document.getElementById("how-typed").textContent = `« ${t("how_ex1")} »`;
  document.getElementById("how-count").textContent = t("how_ex2", { a: state.catalog.length || 288, b: 10 });
  if (how.change !== null) document.getElementById("how-change").textContent = `${pct(how.change)} ${t("how_ex3", { r: how.risk })}`;
  document.getElementById("how-spark").classList.add("drawn");
  document.querySelectorAll(".how-step").forEach((step) => step.classList.add("on"));
  document.getElementById("how").classList.add("play");
}

function playHow() {
  if (how.played) return;
  how.played = true;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { howFinal(); return; }
  const steps = document.querySelectorAll(".how-step");
  document.getElementById("how").classList.add("play");
  steps[0].classList.add("on");
  const text = `« ${t("how_ex1")} »`;
  const typed = document.getElementById("how-typed");
  [...text].forEach((_, i) => setTimeout(() => { typed.textContent = text.slice(0, i + 1); }, 300 + i * 28));
  setTimeout(() => {
    steps[1].classList.add("on");
    const total = state.catalog.length || 288;
    countTo(document.getElementById("how-count"), total, 10, 1200, (v) => t("how_ex2", { a: total, b: Math.round(v) }));
  }, 800);
  setTimeout(() => {
    steps[2].classList.add("on");
    document.getElementById("how-spark").classList.add("drawn");
    if (how.change !== null) {
      countTo(document.getElementById("how-change"), 0, how.change, 1200, (v) => `${pct(v)} ${t("how_ex3", { r: how.risk })}`);
    }
  }, 1600);
}

async function setupHow() {
  document.getElementById("how-try").addEventListener("click", () => {  // step 1 starts the live demo
    const input = document.getElementById("query");
    input.value = t("how_ex1");
    document.getElementById("ask").scrollIntoView({ behavior: "smooth", block: "center" });
    input.focus({ preventScroll: true });
  });
  try {
    const series = (await api(`prices?isins=${HOW_ASSET}&years=3`))[HOW_ASSET];
    how.change = series.change;
    const spark = sparkline(series.points, series.change >= 0);
    spark.lastChild.setAttribute("pathLength", "1");
    document.getElementById("how-spark").replaceChildren(spark);
    how.risk = state.catalog.find((a) => a.isin === HOW_ASSET)?.risk_class ?? how.risk;
  } catch (_) { /* no price history: the step keeps its text only */ }
  new IntersectionObserver((entries, observer) => {
    if (entries.some((e) => e.isIntersecting)) { playHow(); observer.disconnect(); }
  }, { threshold: 0.4 }).observe(document.getElementById("how"));
}

/* ---------- Start ---------- */

document.addEventListener("DOMContentLoaded", async () => {
  renderOptions();
  renderPreview();
  const toggle = document.getElementById("toggle");
  toggle.addEventListener("click", () => {
    const panel = document.getElementById("options");
    const open = panel.classList.toggle("open");
    panel.inert = !open;  // closed options stay out of the tab order
    toggle.setAttribute("aria-expanded", String(open));
  });
  const input = document.getElementById("query");
  document.getElementById("form").addEventListener("submit", submit);
  input.addEventListener("input", () => { state.active = -1; renderSuggest(); });
  input.addEventListener("blur", () => { document.getElementById("suggest").hidden = true; });
  input.addEventListener("keydown", (e) => {
    const n = (state.suggestions || []).length;
    if (!n) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      state.active = (state.active + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
      renderSuggest();
    } else if (e.key === "Enter" && state.active >= 0) {
      e.preventDefault();
      addChip(state.suggestions[state.active]);
    } else if (e.key === "Escape") {
      document.getElementById("suggest").hidden = true;
    }
  });

  try {
    state.catalog = await api("assets");
  } catch (_) {
    const error = document.getElementById("error");
    error.textContent = t("err_api"); error.hidden = false;
  }
  setupHow();
  if (location.hash === "#results" && (state.view = load(LAST_RESULT))) {  // back from an asset page
    renderResults();
    document.getElementById("results").scrollIntoView({ block: "start" });
  }
});

document.addEventListener("langchange", () => { renderOptions(); renderChips(); renderResults(); if (how.played) howFinal(); });
