// Build a portfolio, choose a risk profile, and show ranked suggestions.
const QUESTIONS = ["horizon", "goal", "loss", "experience"];
const LAST_RESULT = "lastResult";
const DEFAULT_AMOUNT = 1000;
const MAX_HOLDINGS = 100;
const SUGGESTIONS = 8;

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
  session: load("session") || uuid(), catalog: [], chips: new Map(), answers: Object.fromEntries(QUESTIONS.map((q) => [q, 1])),
  years: 3, mode: "questionnaire", view: null, active: -1, suggestions: [], category: null, submission: 0, loading: false, error: null,
};
store("session", state.session);

const logEvent = (event) => api("log_interaction", { session_id: state.session, event }).catch(() => {});


/* ---------- Step 1: find assets and add them to the portfolio ---------- */

const CATEGORIES = ["Stock", "Bond", "MTF"];
const EXAMPLE_SIZE = 3;

const query = () => document.getElementById("query").value.trim();
const byPopularity = (assets) => [...assets].sort((a, b) => (a.popularity ?? Infinity) - (b.popularity ?? Infinity));

// With an empty box the list shows the most held assets, so nobody has to guess a name first.
function matches(text) {
  if (state.chips.size >= MAX_HOLDINGS) return [];
  const options = { limit: SUGGESTIONS, exclude: new Set(state.chips.keys()), category: state.category };
  return text ? searchAssets(state.catalog, text, options) : searchAssets(byPopularity(state.catalog), "", options);
}

function exactAsset() {
  const code = query().toUpperCase();
  return state.catalog.find((asset) => asset.isin === code && !state.chips.has(code) && state.chips.size < MAX_HOLDINGS);
}

function highlighted(text, words) {
  return highlightParts(text, words).map((p) => p.hit ? el("mark", {}, p.text) : p.text);
}

function hideSuggest() {
  document.getElementById("suggest-box").hidden = true;
  const input = document.getElementById("query");
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-activedescendant");
  state.active = -1;
  state.suggestions = [];
}

function renderSuggest() {
  const box = document.getElementById("suggest-box");
  const list = document.getElementById("suggest");
  const input = document.getElementById("query");
  if (!state.catalog.length) { hideSuggest(); return; }
  const text = query();
  const found = matches(text);
  state.suggestions = found;
  if (state.active >= found.length) state.active = -1;
  box.hidden = false;
  input.setAttribute("aria-expanded", String(found.length > 0));

  // pointerdown + preventDefault keeps the focus in the box, so the list does not close on click
  document.getElementById("suggest-tabs").replaceChildren(...[null, ...CATEGORIES].map((cat) => el("button", {
    type: "button", class: "tab", "aria-pressed": String(state.category === cat),
    onpointerdown: (e) => { e.preventDefault(); state.category = cat; state.active = -1; renderSuggest(); },
  }, cat ? t(`cat_${cat}_pl`) : t("filter_all"))));

  const head = document.getElementById("suggest-head");
  if (state.chips.size >= MAX_HOLDINGS) head.textContent = t("search_full", { n: MAX_HOLDINGS });
  else if (!found.length) head.textContent = t("search_none", { q: text });
  else head.textContent = text ? t("search_results") : t("search_popular");

  list.replaceChildren(...found.map((asset, i) => el("li", {
    role: "option", id: `opt-${i}`, "aria-selected": String(i === state.active),
    onpointerdown: (e) => { e.preventDefault(); addChip(asset); },
  },
  el("span", { class: "sname" }, ...highlighted(asset.name, text), el("small", {}, asset.isin)),
  el("span", { class: "smeta" },
    asset.category ? el("span", { class: "cat" }, t(`cat_${asset.category}`)) : null,
    asset.risk_class ? el("span", { class: "risk-pill", "data-risk": String(asset.risk_class) }, `${t("risk")} ${asset.risk_class}/7`) : null,
    el("span", { class: "add", "aria-hidden": "true" }, "+")))));
  if (state.active >= 0) input.setAttribute("aria-activedescendant", `opt-${state.active}`);
  else input.removeAttribute("aria-activedescendant");
}

function addChip(asset, { keepOpen = true } = {}) {
  if (!state.chips.has(asset.isin) && state.chips.size < MAX_HOLDINGS) {
    state.chips.set(asset.isin, { name: asset.name, category: asset.category, risk: asset.risk_class, amount: String(DEFAULT_AMOUNT) });
  }
  const input = document.getElementById("query");
  input.value = "";
  state.active = -1;
  if (state.error === "err_selection") showError(null);
  renderChips();
  if (keepOpen && document.activeElement === input) renderSuggest(); else hideSuggest();
}

function addExample() {
  const picks = byPopularity(state.catalog).filter((a) => !state.chips.has(a.isin)).slice(0, EXAMPLE_SIZE);
  for (const asset of picks) addChip(asset, { keepOpen: false });
}

function renderChips() {
  const box = document.getElementById("chips");
  if (!state.chips.size) {
    box.replaceChildren(el("p", { class: "holdings-empty" }, t("holdings_empty")));
    return;
  }
  const total = Array.from(state.chips.values()).reduce((sum, h) => sum + (Number(h.amount) || 0), 0);
  const rows = Array.from(state.chips, ([isin, holding]) => el("div", { class: "holding" },
    el("span", { class: "hname" }, holding.name,
      el("small", {}, [isin, holding.category ? t(`cat_${holding.category}`) : "", holding.risk ? `${t("risk")} ${holding.risk}/7` : ""].filter(Boolean).join(" · "))),
    el("label", { class: "amount" }, el("input", {
      type: "number", min: "0.01", max: "1000000000000000", step: "0.01", required: "", inputmode: "decimal",
      value: holding.amount, "aria-label": t("amount", { name: holding.name }),
      oninput: (event) => { holding.amount = event.target.value; renderTotal(); },
    }), "€"),
    el("button", { type: "button", class: "remove", "aria-label": `${t("remove")} ${holding.name}`,
      onclick: () => { state.chips.delete(isin); renderChips(); } }, "×")));
  box.replaceChildren(
    el("p", { class: "holdings-head" }, t("holdings_title", { n: state.chips.size }),
      el("span", { id: "holdings-total", class: "num" }, t("holdings_total", { total: fmt(total, 0) }))),
    ...rows,
    el("button", { type: "button", class: "link-light clear", onclick: () => { state.chips.clear(); renderChips(); } }, t("holdings_clear")));
}

function renderTotal() {
  const total = Array.from(state.chips.values()).reduce((sum, h) => sum + (Number(h.amount) || 0), 0);
  const node = document.getElementById("holdings-total");
  if (node) node.textContent = t("holdings_total", { total: fmt(total, 0) });
}

/* ---------- Step 2 and 3: profile and chart period ---------- */

function renderOptions() {
  const selects = QUESTIONS.map((q) => {
    const select = el("select", { onchange: (e) => { state.answers[q] = Number(e.target.value); } },
      ...[0, 1, 2].map((i) => el("option", { value: String(i) }, t(`q_${q}_${i}`))));
    select.value = String(state.answers[q]);
    return el("label", {}, t(`q_${q}`), select);
  });
  document.getElementById("option-grid").replaceChildren(...selects);
  document.getElementById("option-grid").hidden = state.mode !== "questionnaire";
  const years = el("select", { onchange: (e) => { state.years = Number(e.target.value); } },
    ...[1, 3, 5].map((n) => el("option", { value: String(n) }, t(n === 1 ? "years" : "years_plural", { n }))));
  years.value = String(state.years);
  document.getElementById("years-box").replaceChildren(el("span", {}, t("chart_years")), years);
}

/* ---------- Request ---------- */

function showError(key) {
  state.error = key;
  const error = document.getElementById("error");
  error.textContent = key ? t(key) : "";
  error.hidden = !key;
}

function updateSubmit() {
  const go = document.getElementById("go");
  go.disabled = state.loading;
  go.textContent = t(state.loading ? "busy" : "go");
}

function showRanking(result, payload, years, review = null) {
  const view = {
    result, years, prices: {}, review, typedText: Boolean(payload.free_text),
    session: state.session, payload, feedback: false, reviewing: false, reviewError: false,
  };
  state.view = view;
  saveView(view);
  renderResults();
  return view;
}

function saveView({ result, years, prices, review, typedText, session }) {
  // The detail page can explain the issued result without retaining portfolio or text inputs in storage.
  store(LAST_RESULT, { result, years, prices, review, typedText, session });
}

function currentView(view, submission) {
  return state.view === view && state.submission === submission;
}

async function addPrices(view, submission) {
  const isins = view.result.items.map((item) => item.isin).join(",");
  if (!isins) return;
  let prices;
  try {
    prices = await api(`prices?isins=${encodeURIComponent(isins)}&years=${view.years}`);
  } catch (_) {
    return; // optional historical data cannot invalidate a scored list
  }
  if (!currentView(view, submission)) return;
  view.prices = prices;
  saveView(view);
  renderResults();
}

async function submit(event) {
  event.preventDefault();
  if (state.loading) return;
  if (query()) {  // text left in the box: take the best match instead of failing
    const asset = exactAsset() || matches(query())[0];
    if (asset) addChip(asset, { keepOpen: false });
  }
  if (query()) {
    showError("err_selection");
    return;
  }
  const textMode = state.mode === "text";
  const text = textMode ? document.getElementById("objective").value.trim() : "";
  if (textMode && !text) {
    showError("err_objective");
    return;
  }
  const holdings = Object.fromEntries(Array.from(state.chips, ([isin, holding]) => [isin, Number(holding.amount)]));
  const payload = { holdings, answers: textMode ? {} : { ...state.answers }, free_text: text, session_id: state.session };
  const years = state.years;
  const submission = ++state.submission;
  state.loading = true;
  if (state.view) state.view.reviewing = false;
  updateSubmit();
  showError(null);

  try {
    const result = await api("recommend", payload);
    const view = showRanking(result, payload, years);
    logEvent("portfolio_entered"); logEvent("recommendation_viewed");
    document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
    void addPrices(view, submission);
  } catch (_) {
    showError("err_recommend");
  } finally {
    state.loading = false;
    updateSubmit();
    renderResults();
  }
}

async function refreshProfile(view) {
  if (state.view !== view || state.loading || view.reviewing || !view.payload) return;
  const submission = state.submission;
  view.reviewing = true;
  view.reviewError = false;
  renderResults();
  logEvent("profile_review_requested");
  try {
    const review = await api("profile", view.payload);
    if (!currentView(view, submission)) return;
    const result = await api("recommend", view.payload);
    if (!currentView(view, submission)) return;
    if (!result.profile_cache_hit) throw new Error("Reviewed profile unavailable");
    const refreshed = showRanking(result, view.payload, view.years, review);
    logEvent("recommendation_viewed");
    void addPrices(refreshed, submission);
  } catch (_) {
    if (!currentView(view, submission)) return;
    view.reviewing = false;
    view.reviewError = true;
    renderResults();
  }
}

/* ---------- Results ---------- */

function renderResults() {
  const box = document.getElementById("results");
  const view = state.view;
  if (!view) { box.hidden = true; return; }
  const { result, prices, review } = view;
  const p = result.profile;
  const notes = [];
  if (result.ranking_source === "popularity") notes.push(t("popularity"));
  if (view.typedText && view.payload && !result.profile_cache_hit) notes.push(t("text_pending"));
  if (review?.llm_status === "not_configured") notes.push(t("review_no_model"));
  else if (review?.llm_status === "model_unavailable") notes.push(t("review_unavailable"));
  else if (review?.status === "verified") notes.push(t("review_verified"));
  else if (review?.status === "refined") notes.push(t("review_refined"));
  else if (review?.status === "rules_fallback") notes.push(t("text_rules"));
  if (view.reviewError) notes.push(t("review_error"));
  const canReview = view.payload && (view.typedText || result.profile_review_available);
  const reviewAction = canReview ? [el("div", { class: "review-actions" }, el("button", {
    class: "btn", type: "button", ...(state.loading || view.reviewing ? { disabled: "" } : {}),
    onclick: () => refreshProfile(view),
  }, t(view.reviewing ? "review_busy" : view.typedText ? "review_text" : "review_quiz")))] : [];

  const rows = result.items.map((item, i) => {
    const series = prices[item.isin];
    const up = series ? series.change >= 0 : true;
    const rec = result.recommendation_id ? `&rec=${encodeURIComponent(result.recommendation_id)}` : "";
    return el("a", { class: "row", href: `asset.html?isin=${encodeURIComponent(item.isin)}${rec}` },
      el("span", { class: "rank num" }, String(i + 1)),
      el("span", { class: "name" }, item.name, el("small", {}, item.isin)),
      el("span", { class: "risk", "data-risk": String(item.risk_class) }, el("b", { class: "num" }, `${item.risk_class}/7`), el("br"), t("risk")),
      series ? sparkline(series.points, up) : el("span"),
      series ? el("span", { class: `change num ${up ? "up" : "down"}` }, pct(series.change),
        series.start && series.end ? el("small", {}, `${series.start} – ${series.end}`) : null) : el("span"));
  });

  box.hidden = false;
  box.replaceChildren(
    el("div", { class: "results-head" },
      el("h2", {}, t("results_title", { n: result.items.length })),
      el("p", {}, t("results_profile", { level: t(`level_${p.risk_level}`), ceiling: p.ceiling }))),
    ...notes.map((note) => el("p", { class: "footnote" }, note)),
    result.items.length ? el("div", { class: "rows glass" }, ...rows) : el("p", { class: "footnote" }, t("none")),
    ...reviewAction,
    el("div", { class: "feedback" }, ...(view.feedback ? [t("fb_thanks")] : [
      el("span", {}, t("fb_q")),
      el("button", { class: "btn", type: "button", onclick: () => sendFeedback("feedback_positive") }, t("fb_yes")),
      el("button", { class: "btn", type: "button", onclick: () => sendFeedback("feedback_negative") }, t("fb_no"))])),
    el("p", { class: "footnote" }, t("footnote")),
  );
}

function sendFeedback(event) {
  logEvent(event);
  state.view.feedback = true;
  renderResults();
}

/* ---------- Start ---------- */

document.addEventListener("DOMContentLoaded", async () => {
  const modes = Array.from(document.querySelectorAll('input[name="profile-mode"]'));
  const changeMode = () => {
    state.mode = modes.find((mode) => mode.checked).value;
    document.getElementById("text-profile").hidden = state.mode !== "text";
    if (state.error === "err_objective") showError(null);
    renderOptions();
  };
  for (const mode of modes) mode.addEventListener("change", changeMode);
  changeMode();
  renderChips();
  const input = document.getElementById("query");
  document.getElementById("form").addEventListener("submit", submit);
  document.getElementById("example").addEventListener("click", addExample);
  input.addEventListener("input", () => {
    state.active = -1;
    if (state.error === "err_selection") showError(null);
    renderSuggest();
  });
  input.addEventListener("focus", renderSuggest);
  input.addEventListener("click", renderSuggest);  // reopen after Escape without leaving the box
  input.addEventListener("blur", hideSuggest);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!state.suggestions.length) renderSuggest();
      const n = state.suggestions.length;
      if (!n) return;
      e.preventDefault();
      const step = e.key === "ArrowDown" ? 1 : -1;
      state.active = state.active < 0 ? (step === 1 ? 0 : n - 1) : (state.active + step + n) % n;
      renderSuggest();
    } else if (e.key === "Enter" && (query() || state.active >= 0)) {
      e.preventDefault();  // Enter in the box adds an asset; it never submits the form
      const asset = state.suggestions[state.active] || exactAsset() || (query() ? state.suggestions[0] : null);
      if (asset) addChip(asset);
      else { showError("err_selection"); renderSuggest(); }
    } else if (e.key === "Escape") {
      hideSuggest();
    }
  });

  try {
    state.catalog = await api("assets");
    if (document.activeElement === input) renderSuggest();
  } catch (_) {
    showError("err_api");
  }
  const saved = load(LAST_RESULT);
  if (location.hash === "#results" && saved?.session === state.session) { // back from an asset page
    state.view = saved;
    renderResults();
    document.getElementById("results").scrollIntoView({ block: "start" });
  }
});

document.addEventListener("langchange", () => {
  renderOptions(); renderChips(); renderResults(); updateSubmit(); showError(state.error);
});
