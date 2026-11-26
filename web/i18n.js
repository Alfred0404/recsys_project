// Brand name: change it here only, it updates every page.
const BRAND = "Spread by Masdaq";
const BRAND_NAME = "Spread";
const BRAND_BY = "by masdaq";

const STRINGS = {
  fr: {
    hero: "Ce qui manque à votre portefeuille.",
    nav_search: "Recherche", nav_assets: "Actifs", nav_method: "Méthode", nav_results: "Résultats",
    cta_method: "Voir la méthode",
    disclaimer: "Outil éducatif, pas un conseil en investissement.",
    graph_label: "Graphe des achats : clients en haut, actifs du catalogue rangés par classe de risque de 1 à 7",
    ceiling_label: "Votre plafond de risque : {n} sur 7",
    graph_caption: "Chaque point est un actif réel du catalogue, rangé par classe de risque. Les liens illustrent des achats. {kept} actifs sur {total} restent sous votre plafond.",
    graph_axis: "classe de risque",
    graph_clients: "clients",
    facts_title: "Les données",
    fact_tx: "transactions réelles, de 2018 à 2022",
    fact_clients: "clients particuliers d’une banque grecque",
    fact_assets: "actions, obligations et fonds achetés",
    fact_median: "actif détenu par le client médian",
    fact_top_v: "48 %", fact_top: "des achats concentrés sur 10 actifs",
    method_title: "Quatre étapes, de vos actifs à une suggestion.",
    method_lede: "Chaque suggestion passe par les mêmes étapes, dans cet ordre. Vous pouvez vérifier chacune dans la démo.",
    step_1_n: "Étape 1", step_1_t: "Le graphe des achats",
    step_1_d: "Clients et actifs forment un graphe. Un réseau de neurones sur graphe (NLGCL) apprend quels actifs vont ensemble, à partir de 158 053 achats.",
    step_2_n: "Étape 2", step_2_t: "Votre niveau de risque",
    step_2_d: "Quatre questions, ou une phrase libre lue par un modèle de langage local, donnent un plafond de risque de 1 à 7.",
    step_3_n: "Étape 3", step_3_t: "Le filtre, puis la variance",
    step_3_d: "Tout actif au-dessus du plafond est écarté. Les autres sont reclassés selon la variance qu’ils ajouteraient à votre portefeuille.",
    step_4_n: "Étape 4", step_4_t: "Une explication vérifiée",
    step_4_d: "Chaque suggestion vient avec ses faits calculés. L’explication du modèle de langage est contrôlée contre ces faits avant d’être affichée.",
    ev_title: "Noté sur les achats futurs de 3 455 clients.",
    ev_lede: "Le modèle apprend sur les achats d’avant juillet 2021. Il est noté sur les achats faits après février 2022, dont ceux de 1 035 clients absents de l’entraînement.",
    ev_bars_title: "Retrouver l’actif que le client a vraiment acheté",
    ev_bars_sub: "NDCG@10 sur le test, plus haut = mieux",
    m_random: "Au hasard", m_popular: "Les plus achetés", m_nlgcl: "NLGCL (notre modèle)", m_lightgcn: "LightGCN (ablation)",
    ev_bars_note: "Le graphe fait 14 % de mieux que les actifs les plus achetés. Sa version sans apprentissage contrastif (LightGCN) fait un peu mieux encore : nous l’affichons tel quel.",
    ev_violation: "des suggestions brutes du modèle dépassaient le plafond de risque du client. Après le filtre, aucune.",
    ev_suitable: "NDCG@10 pour les 564 clients dont l’achat réel respectait leur plafond : quand le client suit son profil, le filtre l’aide à trouver le bon actif.",
    lim_title: "Ce qui ne marche pas encore",
    lim_1: "Sur l’ensemble des clients, le filtre coûte de la précision (NDCG@10 de 0,189 à 0,051) : beaucoup achètent au-dessus de leur profil déclaré.",
    lim_2: "Sans historique, la suggestion vient de la popularité. Avec deux actifs ou moins, NLGCL ne fait pas mieux que les plus achetés.",
    lim_3: "Le reclassement par la variance (MPT) réduit très peu le risque par rapport au filtre seul.",
    team_title: "L’équipe",
    eyebrow_demo: "Démo",
    role_ethan: "Chef de projet, évaluation", role_alfred: "Données et site",
    role_nicolas: "Modèle de graphe et reclassement", role_thomas: "Modèle de langage et API",
    footer_data: "Données FAR-Trans, Université de Glasgow (CC BY 4.0). Outil éducatif, pas un conseil en investissement.",
    footer_code: "Code sur GitHub",
    catalog_title: "Tous les actifs", catalog_lede: "{n} actions, obligations et fonds du catalogue FAR-Trans. Cliquez sur un actif pour voir son cours.",
    catalog_search: "Rechercher un actif par nom ou ISIN", filter_all: "Tous",
    cat_Stock_pl: "Actions", cat_Bond_pl: "Obligations", cat_MTF_pl: "Fonds",
    more: "Afficher plus", catalog_none: "Aucun actif ne correspond à « {q} ».", back_assets: "Retour aux actifs",
    hero_sub: "Spread apprend des achats de 29 090 vrais investisseurs quel actif va avec ceux que vous détenez, puis écarte tout ce qui dépasse votre niveau de risque.",
    cta_try: "Essayer la démo",
    preview_query: "National Bank of Greece · 1 000 €",
    preview_foot: "Suggestions réelles du modèle et cours historiques",
    ask_title: "Quels actifs détenez-vous ?",
    placeholder: "Rechercher un actif : nom, mot ou ISIN",
    search_label: "Rechercher un actif à ajouter au portefeuille",
    search_none: "Aucun actif pour « {q} ». Essayez un autre mot ou une autre catégorie.", search_browse: "Parcourir tout le catalogue",
    search_popular: "Les plus détenus par les clients. Cliquez pour ajouter.", search_results: "Résultats. Cliquez ou appuyez sur Entrée pour ajouter.",
    search_full: "Limite de {n} actifs atteinte.",
    step_assets: "Vos actifs", step_assets_help: "Cliquez dans la barre pour voir les actifs les plus courants, ou tapez un mot du nom (alpha, bank, hellenic…) ou un ISIN.",
    step_go: "Vos suggestions", try_example: "Essayer avec un exemple",
    holdings_empty: "Aucun actif ajouté. Vous pouvez quand même lancer : les suggestions partiront des actifs les plus populaires.",
    holdings_title: "Votre portefeuille ({n})", holdings_total: "Total {total} €", holdings_clear: "Tout retirer",
    go: "Voir mes suggestions", busy: "Recherche…",
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
    err_selection: "Aucun actif ne correspond à votre recherche. Modifiez-la ou effacez-la.",
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
    hero: "What your portfolio is missing.",
    nav_search: "Search", nav_assets: "Assets", nav_method: "Method", nav_results: "Results",
    cta_method: "See the method",
    disclaimer: "Educational tool, not investment advice.",
    graph_label: "Purchase graph: clients on top, catalogue assets sorted by risk class from 1 to 7",
    ceiling_label: "Your risk ceiling: {n} out of 7",
    graph_caption: "Each dot is a real asset from the catalogue, sorted by risk class. Links illustrate purchases. {kept} of {total} assets stay under your ceiling.",
    graph_axis: "risk class",
    graph_clients: "clients",
    facts_title: "The data",
    fact_tx: "real transactions, 2018 to 2022",
    fact_clients: "retail clients of a Greek bank",
    fact_assets: "stocks, bonds and funds bought",
    fact_median: "asset held by the median client",
    fact_top_v: "48%", fact_top: "of purchases go to 10 assets",
    method_title: "Four steps from your holdings to a suggestion.",
    method_lede: "Every suggestion goes through the same steps, in this order. You can check each one in the demo.",
    step_1_n: "Step 1", step_1_t: "The purchase graph",
    step_1_d: "Clients and assets form a graph. A graph neural network (NLGCL) learns which assets go together from 158,053 purchases.",
    step_2_n: "Step 2", step_2_t: "Your risk level",
    step_2_d: "Four questions, or one free sentence read by a local language model, set a risk ceiling from 1 to 7.",
    step_3_n: "Step 3", step_3_t: "The filter, then variance",
    step_3_d: "Any asset above the ceiling is removed. The rest are re-ranked by the variance they would add to your portfolio.",
    step_4_n: "Step 4", step_4_t: "A checked explanation",
    step_4_d: "Each suggestion comes with its computed facts. The language model's explanation is checked against those facts before it is shown.",
    ev_title: "Scored on the future purchases of 3,455 clients.",
    ev_lede: "The model learns from purchases made before July 2021. It is scored on purchases made after February 2022, including those of 1,035 clients absent from training.",
    ev_bars_title: "Finding the asset the client actually bought",
    ev_bars_sub: "Test NDCG@10, higher is better",
    m_random: "Random", m_popular: "Most bought", m_nlgcl: "NLGCL (our model)", m_lightgcn: "LightGCN (ablation)",
    ev_bars_note: "The graph beats the most bought assets by 14%. Its version without contrastive learning (LightGCN) does slightly better still: we show it as it is.",
    ev_violation: "of the model's raw suggestions were above the client's risk ceiling. After the filter, none.",
    ev_suitable: "NDCG@10 for the 564 clients whose real purchase was within their ceiling: when clients follow their profile, the filter helps find the right asset.",
    lim_title: "What does not work yet",
    lim_1: "Across all clients, the filter costs accuracy (NDCG@10 from 0.189 to 0.051): many buy above their stated profile.",
    lim_2: "With no history, the suggestion comes from popularity. With two assets or fewer, NLGCL does no better than the most bought.",
    lim_3: "Re-ranking by variance (MPT) lowers risk very little compared with the filter alone.",
    team_title: "The team",
    eyebrow_demo: "Demo",
    role_ethan: "Project lead, evaluation", role_alfred: "Data and website",
    role_nicolas: "Graph model and re-ranking", role_thomas: "Language model and API",
    footer_data: "FAR-Trans data, University of Glasgow (CC BY 4.0). Educational tool, not investment advice.",
    footer_code: "Code on GitHub",
    catalog_title: "All assets", catalog_lede: "{n} stocks, bonds and funds from the FAR-Trans catalogue. Click an asset to see its price.",
    catalog_search: "Search an asset by name or ISIN", filter_all: "All",
    cat_Stock_pl: "Stocks", cat_Bond_pl: "Bonds", cat_MTF_pl: "Funds",
    more: "Show more", catalog_none: "No asset matches “{q}”.", back_assets: "Back to assets",
    hero_sub: "Spread learns from the purchases of 29,090 real investors which asset goes with the ones you hold, then removes anything above your risk level.",
    cta_try: "Try the demo",
    preview_query: "National Bank of Greece · €1,000",
    preview_foot: "Real model suggestions and historical prices",
    ask_title: "Which assets do you hold?",
    placeholder: "Search an asset: name, word or ISIN",
    search_none: "No asset for “{q}”. Try another word or category.", search_browse: "Browse the full catalogue",
    search_popular: "Most held by clients. Click to add.", search_results: "Results. Click or press Enter to add.",
    search_full: "Limit of {n} assets reached.",
    step_assets: "Your assets", step_assets_help: "Click the bar to see the most common assets, or type a word from the name (alpha, bank, hellenic…) or an ISIN.",
    step_go: "Your suggestions", try_example: "Try with an example",
    holdings_empty: "No asset added yet. You can still run it: suggestions will start from the most popular assets.",
    holdings_title: "Your portfolio ({n})", holdings_total: "Total €{total}", holdings_clear: "Remove all",
    search_label: "Search for an asset to add to your portfolio",
    go: "Show my suggestions", busy: "Searching…",
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
    err_selection: "No asset matches your search. Change it or clear it.",
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
  root.querySelectorAll("[data-brand]").forEach((el) => {
    const by = document.createElement("small");
    by.textContent = BRAND_BY;
    el.replaceChildren(BRAND_NAME, by);
  });
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
