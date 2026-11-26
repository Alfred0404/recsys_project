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

// Plain words for the 1-7 risk scale, so a newcomer never has to decode "7/7".
const RISK_WORD = { 1: "very_low", 2: "very_low", 3: "low", 4: "medium", 5: "fairly_high", 6: "high", 7: "very_high" };
const riskWord = (risk) => t(`pick_risk_${RISK_WORD[risk] || "medium"}`);

// Catalogue names are in capitals ("NATIONAL BANK OF GREECE"): soften them, keep short tokens like SA or S.A.
const SMALL = new Set(["of", "and", "the", "de", "&"]);
function niceName(name) {
  if (name !== name.toUpperCase()) return name;
  return name.toLowerCase().split(" ").map((word, i) => {
    if (i && SMALL.has(word)) return word;
    if (/^(s\.?a\.?|plc|sa|ae|a\/k|\(cr\))$/.test(word)) return word.toUpperCase();
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(" ");
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
  const top = result.items[0];
  const asset = pick.catalog.get(top.isin);
  const before = top.volatility_before;
  const after = top.volatility_after;
  const hasVol = Number.isFinite(before) && Number.isFinite(after) && before > 0 && after < before;

  const held = holdings.map((isin) => pick.catalog.get(isin));
  const risks = held.map((a) => a.risk_class).filter(Boolean);
  const lo = Math.min(...risks), hi = Math.max(...risks);
  const heldRisk = !risks.length ? null : RISK_WORD[lo] === RISK_WORD[hi]
    ? t("pick_held_same", { n: held.length, risk: riskWord(hi) })
    : t("pick_held_range", { lo: riskWord(lo), hi: riskWord(hi) });

  const href = `asset.html?isin=${encodeURIComponent(top.isin)}`;
  const body = document.getElementById("pick-body");
  body.setAttribute("aria-labelledby", `pick-tab-${pick.index}`);
  body.replaceChildren(el("div", { class: "pick-view" },
    el("div", { class: "pick-step" },
      el("p", { class: "pick-label" }, t(`pick_who_${scenario.key}`)),
      el("p", { class: "pick-held" }, held.map((a) => niceName(a.name)).join(" · ")),
      heldRisk ? el("p", { class: "pick-sub", "data-risk": String(hi) }, heldRisk) : null),
    el("div", { class: "pick-step" },
      el("p", { class: "pick-label" }, t("pick_adds")),
      el("a", { class: "pick-top", href },
        el("span", { class: "pick-top-name" }, niceName(top.name)),
        el("span", { class: "pick-sub", "data-risk": String(top.risk_class) },
          [asset?.category ? t(`cat_${asset.category}`) : null, t("pick_risk", { risk: riskWord(top.risk_class) })].filter(Boolean).join(" · ")))),
    hasVol ? el("div", { class: "pick-result" },
      el("p", { class: "pick-big" }, el("b", { class: "num" }, pct(1 - after / before, 0, false)), " ", t("pick_less")),
      el("p", { class: "pick-expert num" }, t("pick_expert", { before: pct(before, 1, false), after: pct(after, 1, false) }))) : null,
    el("div", { class: "pick-actions" },
      el("button", { type: "button", class: "btn primary", onclick: () => openPick(entry, true) }, t("pick_see")),
      el("button", { type: "button", class: "pick-link", onclick: () => openPick(entry, false) }, t("pick_mine"), " →"))));

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
