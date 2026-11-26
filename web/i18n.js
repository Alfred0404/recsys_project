// Brand name: change it here only, it updates every page.
const BRAND = "Complément";

const STRINGS = {
  fr: {
    hero: "Diversifier, avec raison.",
    nav_search: "Recherche", nav_assets: "Actifs",
    catalog_title: "Tous les actifs", catalog_lede: "{n} actions, obligations et fonds du catalogue FAR-Trans. Cliquez sur un actif pour voir son cours.",
    catalog_search: "Rechercher un actif par nom ou ISIN", filter_all: "Tous",
    cat_Stock_pl: "Actions", cat_Bond_pl: "Obligations", cat_MTF_pl: "Fonds",
    more: "Afficher plus", catalog_none: "Aucun actif ne correspond à « {q} ».", back_assets: "Retour aux actifs",
    hero_sub: "Composez votre portefeuille et choisissez votre profil de risque. Explorez les suggestions, leur historique de cours et leurs explications.",
    cta_try: "Essayer maintenant",
    preview_query: "National Bank of Greece · 1 000 €",
    preview_foot: "Suggestions réelles du modèle et cours historiques",
    ask_title: "Quels actifs détenez-vous ?",
    placeholder: "Rechercher un actif par nom ou ISIN…",
    search_label: "Rechercher un actif à ajouter au portefeuille",
    go: "Recommander", busy: "Recherche…",
    hint: "Sélectionnez vos actifs dans la liste. Le montant initial de 1 000 € par actif est modifiable. Sans actif, le classement part de la popularité.",
    options: "Options : horizon, objectif, réaction aux baisses",
    chart_years: "Période des courbes", years: "{n} an", years_plural: "{n} ans",
    remove: "Retirer",
    amount: "Montant en euros pour {name}",
    mode_label: "Profil de risque", mode_quiz: "Questionnaire", mode_text: "Texte libre",
    objective_label: "Objectif, horizon et pertes acceptables",
    objective_placeholder: "Ex. Je veux préserver mon capital sur deux ans.",
    review_text: "Analyser le texte et actualiser", review_quiz: "Vérifier le profil",
    review_busy: "Vérification en cours…",
    review_verified: "Profil confirmé par le modèle local.", review_refined: "Profil corrigé et vérifié.",
    review_no_model: "Modèle local non configuré. Profil établi par les règles.",
    review_unavailable: "Modèle local indisponible. Profil établi par les règles.",
    review_error: "L’actualisation du profil a échoué. Le classement précédent reste affiché.",
    text_pending: "Profil prudent provisoire. Analysez le texte pour actualiser les suggestions.",
    err_selection: "Sélectionnez un actif suggéré ou effacez votre recherche.",
    err_objective: "Décrivez votre objectif ou choisissez le questionnaire.",
    results_title: "{n} suggestions pour vous",
    results_profile: "Profil {level}, plafond de risque {ceiling} sur 7",
    level_1: "prudent", level_2: "modéré", level_3: "équilibré", level_4: "dynamique",
    popularity: "Aucun actif reconnu : classement à partir des actifs les plus détenus.",
    text_rules: "Les règles de secours ont établi le profil.",
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
    why_risk: "Classe de risque {risk} sur 7, pour un plafond de {ceiling}.",
    why_position: "Position n° {rank} dans les suggestions affichées.",
    why_popularity: "Le classement part des actifs les plus détenus et applique le plafond de risque.",
    why_portfolio: "Le classement tient compte des actifs détenus, du plafond de risque et des données de portefeuille disponibles.",
    why_explain: "Demander une explication", why_explaining: "Préparation de l’explication…",
    why_source_llm: "Explication vérifiée du modèle local",
    why_source_template: "Gabarit factuel", why_source_facts: "Faits calculés par la démo",
    why_explain_expired: "Ce classement a expiré. Relancez la recherche pour obtenir une nouvelle explication.",
    why_explain_error: "L’explication est indisponible. Les faits calculés restent affichés.",
    why_var_change: "Variation de variance annuelle simulée pour une allocation de 10 % : {v}.",
    asset_range_unavailable: "Moins de deux cours disponibles sur cette période.",
    asset_samples: "{n} cours disponibles",
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
    nav_search: "Search", nav_assets: "Assets",
    catalog_title: "All assets", catalog_lede: "{n} stocks, bonds and funds from the FAR-Trans catalogue. Click an asset to see its price.",
    catalog_search: "Search an asset by name or ISIN", filter_all: "All",
    cat_Stock_pl: "Stocks", cat_Bond_pl: "Bonds", cat_MTF_pl: "Funds",
    more: "Show more", catalog_none: "No asset matches “{q}”.", back_assets: "Back to assets",
    hero_sub: "Build your portfolio and choose your risk profile. Explore suggestions, historical prices and explanations.",
    cta_try: "Try it now",
    preview_query: "National Bank of Greece · €1,000",
    preview_foot: "Real model suggestions and historical prices",
    ask_title: "Which assets do you hold?",
    placeholder: "Search an asset by name or ISIN…",
    search_label: "Search for an asset to add to your portfolio",
    go: "Recommend", busy: "Searching…",
    hint: "Select your assets from the list. You can edit the initial €1,000 per asset. With no holdings, ranking starts from popularity.",
    options: "Options: horizon, goal, reaction to drops",
    chart_years: "Chart period", years: "{n} year", years_plural: "{n} years",
    remove: "Remove",
    amount: "Amount in euros for {name}",
    mode_label: "Risk profile", mode_quiz: "Questionnaire", mode_text: "Free text",
    objective_label: "Goal, time horizon and acceptable losses",
    objective_placeholder: "E.g. I want to preserve my capital over two years.",
    review_text: "Review text and refresh", review_quiz: "Review profile",
    review_busy: "Reviewing…",
    review_verified: "Profile confirmed by the local model.", review_refined: "Profile refined and verified.",
    review_no_model: "Local model not configured. Rules were used for the profile.",
    review_unavailable: "Local model unavailable. Rules were used for the profile.",
    review_error: "Profile refresh failed. The previous ranking is still shown.",
    text_pending: "Temporary cautious profile. Review the text to refresh the suggestions.",
    err_selection: "Choose a suggested asset or clear your search.",
    err_objective: "Describe your objective or choose the questionnaire.",
    results_title: "{n} suggestions for you",
    results_profile: "{level} profile, risk ceiling {ceiling} out of 7",
    level_1: "Cautious", level_2: "Moderate", level_3: "Balanced", level_4: "Growth",
    popularity: "No asset recognised: ranking from the most held assets.",
    text_rules: "The profile was set using fallback rules.",
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
    why_risk: "Risk class {risk} out of 7, with a ceiling of {ceiling}.",
    why_position: "Position {rank} in the displayed suggestions.",
    why_popularity: "The ranking starts from the most held assets and applies your risk ceiling.",
    why_portfolio: "The ranking uses your holdings, your risk ceiling and available portfolio data.",
    why_explain: "Request an explanation", why_explaining: "Preparing the explanation…",
    why_source_llm: "Verified explanation from the local model",
    why_source_template: "Factual template", why_source_facts: "Facts calculated by the demo",
    why_explain_expired: "This ranking has expired. Run the search again to request a new explanation.",
    why_explain_error: "The explanation is unavailable. The calculated facts are still shown.",
    why_var_change: "Simulated change in annual variance for a 10% allocation: {v}.",
    asset_range_unavailable: "Fewer than two quotes are available in this period.",
    asset_samples: "{n} available quotes",
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
  try { const saved = localStorage.getItem("lang"); if (Object.hasOwn(STRINGS, saved)) return saved; } catch (_) { /* storage blocked */ }
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
  if (!response.ok) {
    const error = new Error(`${path} ${response.status}`);
    error.status = response.status;
    throw error;
  }
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
