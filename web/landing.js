// Hero card: a real recommendation, computed live by the API for three sample portfolios.
// Only the portfolios and profiles are fixed here; every name and figure comes from the model.
const PICK_SCENARIOS = [
  { key: "prudent", level: 0, holdings: ["GRS001003037", "GRS260333000", "GRS015003007"] },
  { key: "balanced", level: 1, holdings: ["GRS395363005", "GRS213213002", "GRS087003000"] },
  { key: "dynamic", level: 2, holdings: ["GRS343313003", "GRS393503008", "GRF000022001"] },
];
const PICK_QUESTIONS = ["horizon", "goal", "loss", "experience"];
const PICK_ROTATE_MS = 7000;

const pick = { catalog: new Map(), results: [], index: 0, timer: 0, auto: true, paused: false };

async function loadPicks() {
  // The catalogue and the three recommendations are fetched in parallel.
  const [catalog, ...results] = await Promise.all([api("assets"), ...PICK_SCENARIOS.map((scenario) => api("recommend", {
    holdings: Object.fromEntries(scenario.holdings.map((isin) => [isin, 1000])),
    answers: Object.fromEntries(PICK_QUESTIONS.map((q) => [q, scenario.level])),
  }))]);
  pick.catalog = new Map(catalog.map((asset) => [asset.isin, asset]));
  pick.results = PICK_SCENARIOS.map((scenario, i) => ({
    scenario, result: results[i], holdings: scenario.holdings.filter((isin) => pick.catalog.has(isin)),
  }));
  pick.results = pick.results.filter((entry) => entry.holdings.length && entry.result.items.length);
  if (!pick.results.length) throw new Error("No sample recommendation");
}

function riskPill(risk) {
  return el("span", { class: "risk-pill num", "data-risk": String(risk) }, `${t("risk")} ${risk}/7`);
}

function renderPickTabs() {
  const tabs = document.getElementById("pick-tabs");
  tabs.replaceChildren(...pick.results.map((entry, i) => el("button", {
    type: "button", role: "tab", class: "pick-tab", id: `pick-tab-${i}`, "aria-controls": "pick-body",
    "aria-selected": String(i === pick.index), tabindex: i === pick.index ? "0" : "-1",
    onclick: () => { pick.auto = false; showPick(i); },
    onkeydown: (event) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      const n = pick.results.length;
      pick.auto = false;
      showPick((pick.index + (event.key === "ArrowRight" ? 1 : -1) + n) % n);
      document.getElementById(`pick-tab-${pick.index}`).focus();
    },
  }, t(`pick_${entry.scenario.key}`))));
}

function renderPick() {
  const entry = pick.results[pick.index];
  if (!entry) return;
  const { scenario, holdings, result } = entry;
  const [top, ...rest] = result.items;
  const asset = pick.catalog.get(top.isin);
  const before = top.volatility_before;
  const after = top.volatility_after;
  const hasVol = Number.isFinite(before) && Number.isFinite(after) && before > 0;

  const held = el("ul", { class: "pick-held" }, ...holdings.map((isin) => {
    const a = pick.catalog.get(isin);
    return el("li", {}, el("span", { class: "pick-held-name" }, a.name), a.risk_class ? riskPill(a.risk_class) : null);
  }));

  const metric = hasVol ? el("div", { class: "pick-metric" },
    el("p", { class: "pick-metric-head" }, el("span", {}, t("pick_vol")),
      el("b", { class: "pick-drop num" }, pct(after / before - 1))),
    el("div", { class: "pick-vol" },
      el("span", { class: "pick-vol-label" }, t("pick_today")),
      el("i", { style: "--w: 100%" }), el("b", { class: "num" }, pct(before, 1, false))),
    el("div", { class: "pick-vol after" },
      el("span", { class: "pick-vol-label" }, t("pick_with")),
      el("i", { style: `--w: ${((after / before) * 100).toFixed(1)}%` }), el("b", { class: "num" }, pct(after, 1, false))),
    el("p", { class: "pick-note" }, t("pick_alloc"))) : null;

  const href = (isin) => `asset.html?isin=${encodeURIComponent(isin)}`;
  const body = document.getElementById("pick-body");
  body.setAttribute("aria-labelledby", `pick-tab-${pick.index}`);
  body.replaceChildren(el("div", { class: "pick-view" },
    el("p", { class: "pick-kicker" }, t("pick_hold")),
    held,
    el("p", { class: "pick-kicker accent" }, el("span", { class: "pick-arrow", "aria-hidden": "true" }, "↓"), t("pick_adds")),
    el("a", { class: "pick-top", href: href(top.isin) },
      el("span", { class: "pick-top-name" }, top.name),
      el("span", { class: "pick-top-meta" },
        riskPill(top.risk_class),
        asset?.category ? el("span", { class: "pick-cat" }, t(`cat_${asset.category}`)) : null,
        el("span", { class: "pick-fit" }, t("pick_fit", { ceiling: result.profile.ceiling })))),
    metric,
    rest.length ? el("p", { class: "pick-more" }, t("pick_more", { n: rest.length }),
      ...rest.slice(0, 2).flatMap((item, i) => [i ? " · " : " ", el("a", { href: href(item.isin) }, item.name)])) : null,
    el("div", { class: "pick-actions" },
      el("button", { type: "button", class: "btn primary", onclick: () => openPick(entry, true) }, t("pick_see", { n: result.items.length })),
      el("button", { type: "button", class: "btn ghost", onclick: () => openPick(entry, false) }, t("pick_mine")))));

  const card = document.getElementById("pick-card");
  card.dataset.ceiling = String(result.profile.ceiling);
  document.dispatchEvent(new CustomEvent("ceilingchange"));
}

function showPick(i) {
  pick.index = i;
  renderPickTabs();
  renderPick();
  schedulePick();
}

function schedulePick() {
  clearTimeout(pick.timer);
  const card = document.getElementById("pick-card");
  const rotating = pick.auto && !pick.paused && pick.results.length > 1
    && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  card.classList.toggle("rotating", rotating);
  card.style.setProperty("--rotate", `${PICK_ROTATE_MS}ms`);
  if (rotating) pick.timer = setTimeout(() => showPick((pick.index + 1) % pick.results.length), PICK_ROTATE_MS);
}

// "See the suggestions" runs the demo on this portfolio; "With my portfolio" goes to the search box.
function openPick(entry, run) {
  pick.auto = false;
  schedulePick();
  if (!run) {
    document.getElementById("ask").scrollIntoView({ behavior: "smooth", block: "start" });
    document.getElementById("query").focus({ preventScroll: true });
    return;
  }
  const assets = entry.holdings.map((isin) => pick.catalog.get(isin));
  if (typeof loadPortfolio === "function") loadPortfolio(assets, entry.scenario.level, true);
}

document.addEventListener("DOMContentLoaded", async () => {
  const card = document.getElementById("pick-card");
  const pause = (on) => { pick.paused = on; schedulePick(); };
  card.addEventListener("pointerenter", () => pause(true));
  card.addEventListener("pointerleave", () => pause(false));
  card.addEventListener("focusin", () => pause(true));
  card.addEventListener("focusout", (event) => { if (!card.contains(event.relatedTarget)) pause(false); });
  try {
    await loadPicks();
    card.classList.add("ready");
    showPick(0);
  } catch (_) {
    card.hidden = true;  // no API: the copy still stands on its own
    document.dispatchEvent(new CustomEvent("ceilingchange"));
  }
});

document.addEventListener("langchange", () => { if (pick.results.length) { renderPickTabs(); renderPick(); } });
