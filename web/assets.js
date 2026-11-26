// Catalogue: every asset, filtered as you type, 20 at a time with their 1-year trend.
const PAGE = 20;
const CATEGORIES = ["Stock", "Bond", "MTF"];
const view = { all: [], query: "", category: null, shown: PAGE, prices: {}, revision: 0 };

const normalize = (text) => text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

function matching() {
  const q = normalize(view.query.trim());
  const matches = view.all.filter((a) => (!view.category || a.category === view.category)
    && (!q || normalize(a.name).includes(q) || a.isin.toLowerCase().includes(q)));
  const exact = matches.find((a) => a.isin.toLowerCase() === q);
  return exact ? [exact, ...matches.filter((a) => a !== exact)] : matches;
}

async function loadPrices(assets) {
  const missing = assets.map((a) => a.isin).filter((isin) => !(isin in view.prices));
  const jobs = [];
  for (let offset = 0; offset < missing.length; offset += PAGE) {
    const batch = missing.slice(offset, offset + PAGE);
    jobs.push(api(`prices?isins=${encodeURIComponent(batch.join(","))}&years=1`).then((data) => {
      for (const isin of batch) view.prices[isin] = data[isin] || null;
    }).catch(() => {})); // leave failed requests uncached so a later render can retry
  }
  await Promise.all(jobs);
}

async function render() {
  const revision = ++view.revision;
  const found = matching();
  const visible = found.slice(0, view.shown);
  await loadPrices(visible);
  if (revision !== view.revision) return;
  const list = document.getElementById("list");
  list.hidden = !found.length;
  list.replaceChildren(...visible.map((a) => {
    const series = view.prices[a.isin];
    const up = series ? series.change >= 0 : true;
    return el("a", { class: "row", href: `asset.html?isin=${encodeURIComponent(a.isin)}&from=assets` },
      el("span", { class: "name" }, a.name, el("small", {}, a.isin)),
      el("span", { class: "cat" }, a.category ? t(`cat_${a.category}`) : ""),
      el("span", { class: "risk", "data-risk": String(a.risk_class || "") }, el("b", { class: "num" }, a.risk_class ? `${a.risk_class}/7` : "–"), el("br"), t("risk")),
      series ? sparkline(series.points, up) : el("span"),
      series ? el("span", { class: `change num ${up ? "up" : "down"}` }, pct(series.change),
        el("small", {}, `${series.start} – ${series.end}`)) : el("span"));
  }));
  const error = document.getElementById("error");
  error.hidden = found.length > 0 || !view.all.length;
  error.textContent = t("catalog_none", { q: view.query.trim() });
  document.getElementById("more").hidden = found.length <= view.shown;
}

function renderChrome() {
  document.getElementById("lede").textContent = t("catalog_lede", { n: view.all.length });
  document.getElementById("filters").replaceChildren(...[null, ...CATEGORIES].map((cat) =>
    el("button", { class: "btn", type: "button", "aria-pressed": String(view.category === cat),
      onclick: () => { view.category = cat; view.shown = PAGE; renderChrome(); render(); } },
    cat ? t(`cat_${cat}_pl`) : t("filter_all"))));
}

document.addEventListener("DOMContentLoaded", async () => {
  const input = document.getElementById("filter");
  let timer;
  input.addEventListener("input", () => {  // small debounce: each keystroke would otherwise fetch prices
    view.query = input.value;
    view.shown = PAGE;
    view.revision += 1;
    clearTimeout(timer);
    timer = setTimeout(render, 150);
  });
  input.addEventListener("keydown", (e) => {  // Enter opens the first match
    if (e.key !== "Enter" || !input.value.trim()) return;
    view.query = input.value;
    const first = matching()[0];
    if (first) location.href = `asset.html?isin=${encodeURIComponent(first.isin)}&from=assets`;
  });
  document.getElementById("more").addEventListener("click", () => { view.shown += PAGE; render(); });
  try {
    view.all = (await api("assets")).sort((a, b) => a.name.localeCompare(b.name));
  } catch (_) {
    const error = document.getElementById("error");
    error.textContent = t("err_api"); error.hidden = false;
    return;
  }
  renderChrome(); render();
});
document.addEventListener("langchange", () => { renderChrome(); render(); });
