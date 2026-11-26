// Brand name: change it here only, it updates every page.
const BRAND = "Spread";

const STRINGS = {
  fr: {
    hero: "Diversifier, avec raison.",
    how_title: "Comment ça marche", how_lede: "Trois étapes, moins d’une minute.",
    s1_title: "Décrivez", s1_body: "Ce que vous détenez et ce que vous cherchez, en une phrase.",
    s2_title: "Spread analyse", s2_body: "Pertinence par le graphe, filtre selon votre risque, priorité à la diversification.",
    s3_title: "Explorez", s3_body: "Risque, évolution du cours, et la raison de chaque suggestion.",
    how_ex1: "J’ai National Bank of Greece, je veux diversifier", how_try: "Essayer cet exemple",
    how_ex2: "{a} actifs → {b} suggestions", how_ex3: "sur 3 ans · risque {r}/7",
    nav_search: "Recherche", nav_assets: "Actifs",
    catalog_title: "Tous les actifs", catalog_lede: "{n} actions, obligations et fonds du catalogue FAR-Trans. Cliquez sur un actif pour voir son cours.",
    catalog_search: "Rechercher un actif par nom ou ISIN", filter_all: "Tous",
    cat_Stock_pl: "Actions", cat_Bond_pl: "Obligations", cat_MTF_pl: "Fonds",
    more: "Afficher plus", catalog_none: "Aucun actif ne correspond à « {q} ».", back_assets: "Retour aux actifs",
    hero_sub: "Décrivez votre portefeuille en une phrase. Nous trouvons les actifs qui le complètent, filtrés selon votre tolérance au risque, avec la raison de chacun.",
    cta_try: "Essayer maintenant",
    preview_query: "J’ai National Bank of Greece, je veux diversifier",
    preview_foot: "Suggestions réelles du modèle, cours sur 3 ans",
    ask_title: "Demandez à Spread",
    placeholder: "Décrivez votre portefeuille et ce que vous voulez…",
    search_label: "Décrivez votre portefeuille et ce que vous voulez",
    go: "Recommander", busy: "Analyse…",
    hint: "Citez vos actifs (ex. National Bank of Greece) : ils s’ajoutent au portefeuille. Sans actif, les suggestions partent des plus détenus.",
    options: "Options : horizon, objectif, réaction aux baisses",
    chart_years: "Période des courbes", years: "{n} an", years_plural: "{n} ans",
    remove: "Retirer",
    results_title: "{n} suggestions pour vous",
    results_profile: "Profil {level}, plafond de risque {ceiling} sur 7",
    level_1: "prudent", level_2: "modéré", level_3: "équilibré", level_4: "dynamique",
    popularity: "Aucun actif reconnu : classement à partir des actifs les plus détenus.",
    text_rules: "Votre texte n’a pas pu être lu par le modèle local : le profil vient des options.",
    over: "sur {n} ans", over_1: "sur 1 an",
    risk: "risque",
    none: "Aucun actif ne respecte votre plafond de risque. Élargissez vos options.",
    footnote: "Cours historiques FAR-Trans, jusqu’au 29 novembre 2022. Outil éducatif, pas un conseil en investissement.",
    fb_q: "Ces suggestions vous sont utiles ?", fb_yes: "Oui", fb_no: "Pas vraiment", fb_thanks: "Merci pour votre retour.",
    err_api: "Le serveur ne répond pas. Lancez l’API puis rechargez la page.",
    err_recommend: "Les suggestions n’ont pas pu être calculées. Réessayez.",
    back: "Retour aux suggestions",
    asset_change: "sur la période", range_max: "Tout",
    stat_last: "Dernier cours", stat_vol: "Volatilité annuelle", stat_dd: "Pire baisse", stat_class: "Classe de risque",
    why_title: "Pourquoi cet actif vous est suggéré",
    why_rank: "Le modèle de graphe le classe n° {rank} pour un portefeuille comme le vôtre.",
    why_risk: "Classe de risque {risk} sur 7, sous votre plafond de {ceiling}.",
    why_var_down: "Avec 10 % de votre portefeuille, la variance annuelle baisse de {v}.",
    why_var_up: "Avec 10 % de votre portefeuille, la variance annuelle monte de {v}.",
    asset_missing: "Cet actif n’a pas d’historique de cours.",
    cat_Stock: "Action", cat_Bond: "Obligation", cat_MTF: "Fonds",
    q_horizon: "Horizon de placement", q_horizon_0: "Moins de 2 ans", q_horizon_1: "2 à 5 ans", q_horizon_2: "Plus de 5 ans",
    q_goal: "Objectif", q_goal_0: "Préserver le capital", q_goal_1: "Équilibrer sécurité et croissance", q_goal_2: "Chercher la croissance",
    q_loss: "Réaction à une baisse de 20 %", q_loss_0: "Vendre", q_loss_1: "Conserver", q_loss_2: "Accepter et envisager de renforcer",
    q_experience: "Expérience des placements", q_experience_0: "Débutant", q_experience_1: "Intermédiaire", q_experience_2: "Expérimenté",
  },
  en: {
    hero: "Diversify, with reason.",
    how_title: "How it works", how_lede: "Three steps, under a minute.",
    s1_title: "Describe", s1_body: "What you hold and what you are after, in one sentence.",
    s2_title: "Spread analyses", s2_body: "Relevance from the graph, a filter for your risk, priority to diversification.",
    s3_title: "Explore", s3_body: "Risk, price history, and the reason behind each suggestion.",
    how_ex1: "I hold National Bank of Greece, I want to diversify", how_try: "Try this example",
    how_ex2: "{a} assets → {b} suggestions", how_ex3: "over 3 years · risk {r}/7",
    nav_search: "Search", nav_assets: "Assets",
    catalog_title: "All assets", catalog_lede: "{n} stocks, bonds and funds from the FAR-Trans catalogue. Click an asset to see its price.",
    catalog_search: "Search an asset by name or ISIN", filter_all: "All",
    cat_Stock_pl: "Stocks", cat_Bond_pl: "Bonds", cat_MTF_pl: "Funds",
    more: "Show more", catalog_none: "No asset matches “{q}”.", back_assets: "Back to assets",
    hero_sub: "Describe your portfolio in one sentence. We find the assets that complete it, filtered by your risk tolerance, each with its reason.",
    cta_try: "Try it now",
    preview_query: "I hold National Bank of Greece, I want to diversify",
    preview_foot: "Real model suggestions, 3-year prices",
    ask_title: "Ask Spread",
    placeholder: "Describe your portfolio and what you want…",
    search_label: "Describe your portfolio and what you want",
    go: "Recommend", busy: "Analysing…",
    hint: "Name your assets (e.g. National Bank of Greece): they are added to the portfolio. With none, suggestions start from the most held.",
    options: "Options: horizon, goal, reaction to drops",
    chart_years: "Chart period", years: "{n} year", years_plural: "{n} years",
    remove: "Remove",
    results_title: "{n} suggestions for you",
    results_profile: "{level} profile, risk ceiling {ceiling} out of 7",
    level_1: "Cautious", level_2: "Moderate", level_3: "Balanced", level_4: "Growth",
    popularity: "No asset recognised: ranking from the most held assets.",
    text_rules: "The local model could not read your text: the profile comes from the options.",
    over: "over {n} years", over_1: "over 1 year",
    risk: "risk",
    none: "No asset meets your risk ceiling. Widen your options.",
    footnote: "Historical FAR-Trans prices, up to 29 November 2022. Educational tool, not investment advice.",
    fb_q: "Are these suggestions useful?", fb_yes: "Yes", fb_no: "Not really", fb_thanks: "Thanks for your feedback.",
    err_api: "The server is not responding. Start the API, then reload the page.",
    err_recommend: "The suggestions could not be computed. Try again.",
    back: "Back to suggestions",
    asset_change: "over the period", range_max: "All",
    stat_last: "Last price", stat_vol: "Annual volatility", stat_dd: "Worst drop", stat_class: "Risk class",
    why_title: "Why this asset is suggested to you",
    why_rank: "The graph model ranks it number {rank} for a portfolio like yours.",
    why_risk: "Risk class {risk} out of 7, under your ceiling of {ceiling}.",
    why_var_down: "With 10% of your portfolio, annual variance drops by {v}.",
    why_var_up: "With 10% of your portfolio, annual variance rises by {v}.",
    asset_missing: "This asset has no price history.",
    cat_Stock: "Stock", cat_Bond: "Bond", cat_MTF: "Fund",
    q_horizon: "Investment horizon", q_horizon_0: "Under 2 years", q_horizon_1: "2 to 5 years", q_horizon_2: "Over 5 years",
    q_goal: "Goal", q_goal_0: "Preserve capital", q_goal_1: "Balance safety and growth", q_goal_2: "Seek growth",
    q_loss: "Reaction to a 20% drop", q_loss_0: "Sell", q_loss_1: "Hold", q_loss_2: "Accept it and consider buying more",
    q_experience: "Investing experience", q_experience_0: "Beginner", q_experience_1: "Intermediate", q_experience_2: "Experienced",
  },
};

function readLang() {
  try { const saved = localStorage.getItem("lang"); if (saved in STRINGS) return saved; } catch (_) { /* storage blocked */ }
  return (navigator.language || "fr").toLowerCase().startsWith("fr") ? "fr" : "en";
}

let LANG = readLang();

function t(key, vars = {}) {
  const text = STRINGS[LANG][key] ?? STRINGS.fr[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in vars ? vars[name] : `{${name}}`));
}

function fmt(value, digits = 0) {
  return Number(value).toLocaleString(LANG === "fr" ? "fr-FR" : "en-GB",
    { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(value, digits = 0, signed = true) {
  const sign = signed ? (value > 0 ? "+" : value < 0 ? "−" : "") : "";
  return `${sign}${fmt(Math.abs(value) * 100, digits)}${LANG === "fr" ? " %" : "%"}`;
}

function applyI18n(root = document) {
  document.documentElement.lang = LANG;
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  root.querySelectorAll("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nLabel)); });
  root.querySelectorAll("[data-brand]").forEach((el) => { el.textContent = BRAND; });
  const toggle = document.querySelector(".lang");
  if (toggle) toggle.textContent = LANG === "fr" ? "EN" : "FR";
}

function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem("lang", lang); } catch (_) { /* storage blocked */ }
  applyI18n();
  document.dispatchEvent(new CustomEvent("langchange"));
}

// Shared by every page: JSON calls to the API and a small element builder.
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children.filter((child) => child !== null && child !== undefined && child !== false));
  return node;
}

// The light source: glass surfaces and buttons reflect it where the pointer is.
document.addEventListener("pointermove", (event) => {
  const surface = event.target.closest?.(".glass, .btn");
  if (!surface) return;
  const box = surface.getBoundingClientRect();
  surface.style.setProperty("--mx", `${event.clientX - box.left}px`);
  surface.style.setProperty("--my", `${event.clientY - box.top}px`);
});

document.addEventListener("DOMContentLoaded", () => {
  document.title = BRAND;
  applyI18n();
  document.querySelector(".lang")?.addEventListener("click", () => setLang(LANG === "fr" ? "en" : "fr"));
});
