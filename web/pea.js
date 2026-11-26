// PEA view: country exposure of a PEA ETF portfolio before and after adding one ETF.
// Independent of the trained model: it only reads /pea/etfs and /pea/exposure.
const PEA_TOP = 8;
const COUNTRY_FR = {
  "United States": "États-Unis", "United Kingdom": "Royaume-Uni", "Germany": "Allemagne", "France": "France",
  "Netherlands": "Pays-Bas", "Spain": "Espagne", "Switzerland": "Suisse", "Japan": "Japon", "Canada": "Canada",
  "Ireland": "Irlande", "Luxembourg": "Luxembourg", "India": "Inde", "Taiwan": "Taïwan",
};
const pea = { etfs: [], held: {}, candidate: null, share: 0.1, data: null };

const peaPct = (value) => pct(value, 0, false);

function countryName(country) {
  if (country === "Other") return t("pea_other");
  if (country === "Non renseigné") return t("pea_unknown_country");
  return LANG === "fr" ? (COUNTRY_FR[country] || country) : country;
}

function renderPeaControls() {
  const names = Object.fromEntries(pea.etfs.map((e) => [e.isin, e.name]));
  const options = () => pea.etfs.map((e) => el("option", { value: e.isin }, e.name));
  const pick = document.getElementById("pea-pick");
  const keep = pick.value;
  pick.replaceChildren(...options());
  if (keep) pick.value = keep;
  const candidate = document.getElementById("pea-candidate");
  candidate.replaceChildren(...options());
  candidate.value = pea.candidate;
  document.getElementById("pea-held").replaceChildren(...Object.entries(pea.held).map(([isin, amount]) =>
    el("div", { class: "pea-row" },
      el("span", {}, names[isin]),
      el("input", { type: "number", min: "1", step: "100", value: String(amount), "aria-label": `${t("pea_amount")} ${names[isin]}`,
        onchange: (e) => { pea.held[isin] = Number(e.target.value); updatePea(); } }),
      el("button", { type: "button", class: "remove", "aria-label": `${t("pea_remove")} ${names[isin]}`,
        onclick: () => { delete pea.held[isin]; renderPeaControls(); updatePea(); } }, "×"))));
  document.getElementById("pea-share-value").textContent = peaPct(pea.share);
}

async function updatePea() {
  const holdings = Object.fromEntries(Object.entries(pea.held).filter(([, amount]) => amount > 0));
  try {
    pea.data = await api("pea/exposure", { holdings, candidate: pea.candidate, share: pea.share });
  } catch (_) {
    pea.data = null;
  }
  renderPeaChart();
}

function renderPeaChart() {
  const bars = document.getElementById("pea-bars");
  const facts = document.getElementById("pea-facts");
  const data = pea.data;
  if (!data) { bars.replaceChildren(el("p", { class: "hint" }, t("pea_error"))); facts.replaceChildren(); return; }
  const rows = data.rows.slice(0, PEA_TOP);
  const max = Math.max(...rows.flatMap((r) => [r.before, r.after]), 1);
  const bar = (kind, value) => {
    const fill = el("i");
    fill.style.width = `${(value / max) * 100}%`;
    return el("span", { class: `pea-bar ${kind}` }, fill);
  };
  bars.replaceChildren(...rows.map((r) => el("div", { class: "pea-country" },
    el("span", { class: "pea-name" }, countryName(r.country)),
    el("span", { class: "pea-pair" }, data.before ? bar("before", r.before) : null, bar("after", r.after)),
    el("span", { class: "pea-val num" }, data.before ? `${peaPct(r.before / 100)} → ${peaPct(r.after / 100)}` : peaPct(r.after / 100)))));

  const lines = [];
  const b = data.before; const a = data.after;
  if (b && b.top_share !== null && a.top_share !== null) {
    lines.push(t("pea_top", { a: countryName(b.top_country), x: peaPct(b.top_share), b: countryName(a.top_country), y: peaPct(a.top_share) }));
  }
  if (b && b.hhi !== null && a.hhi !== null) lines.push(t("pea_hhi", { x: fmt(b.hhi, 2), y: fmt(a.hhi, 2) }));
  if ((b && b.unknown_share) || a.unknown_share) lines.push(t("pea_unknown", { x: peaPct(b ? b.unknown_share : 0), y: peaPct(a.unknown_share) }));
  facts.replaceChildren(...lines.map((line) => el("p", {}, line)));
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    pea.etfs = await api("pea/etfs");
  } catch (_) {
    document.getElementById("pea").hidden = true;  // the rest of the page works without this view
    return;
  }
  // Start from the classic overlap: a portfolio of S&P 500, then add MSCI Europe.
  const byTicker = (ticker) => pea.etfs.find((e) => e.ticker === ticker)?.isin || pea.etfs[0].isin;
  pea.held = { [byTicker("PSP5")]: 5000 };
  pea.candidate = byTicker("PCEU");
  renderPeaControls();
  updatePea();
  document.getElementById("pea-add").addEventListener("click", () => {
    const isin = document.getElementById("pea-pick").value;
    if (!(isin in pea.held)) { pea.held[isin] = 1000; renderPeaControls(); updatePea(); }
  });
  document.getElementById("pea-candidate").addEventListener("change", (e) => { pea.candidate = e.target.value; updatePea(); });
  document.getElementById("pea-share").addEventListener("input", (e) => {
    pea.share = Number(e.target.value) / 100;
    document.getElementById("pea-share-value").textContent = peaPct(pea.share);
    updatePea();
  });
});

document.addEventListener("langchange", () => { if (pea.etfs.length) { renderPeaControls(); renderPeaChart(); } });
