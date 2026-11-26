// Run with: node --test tests/test_asset_pages.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadPage(filename, globals = {}) {
  const listeners = {};
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      children: [], value: "", handlers: {},
      addEventListener(event, fn) { this.handlers[event] = fn; },
      replaceChildren(...children) { this.children = children; },
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    URLSearchParams, AbortController, setTimeout, clearTimeout, LANG: "en",
    document: { getElementById: element, addEventListener(event, fn) { listeners[event] = fn; } },
    el: (tag, attrs, ...children) => ({ tag, attrs, children }),
    t: (key) => key, fmt: (value, digits = 0) => Number(value).toFixed(digits),
    ...globals,
  });
  for (const file of ["search.js", filename]) vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "web", file), "utf8"), context);
  return { context, listeners, element, run: (script) => vm.runInContext(script, context) };
}

test("catalogue Enter opens the exact ISIN without waiting for the render debounce", async () => {
  const catalogue = [
    { isin: "OTHER", name: "A fund named GR123", category: "MTF" },
    { isin: "GR123", name: "National Bank of Greece", category: "Stock" },
  ];
  const { context, listeners, element } = loadPage("assets.js", {
    api: async (request) => request === "assets" ? catalogue : {},
    location: { href: "" }, setTimeout: () => 1, clearTimeout() {},
  });
  await listeners.DOMContentLoaded();
  const input = element("filter");
  input.value = " gr123 ";
  input.handlers.input();
  input.handlers.keydown({ key: "Enter" });
  assert.equal(context.location.href, "asset.html?isin=GR123&from=assets");
});

test("old catalogue prices cannot overwrite newer filtered results", async () => {
  const catalogue = [
    { isin: "A", name: "First asset", category: "MTF" },
    { isin: "B", name: "Second asset", category: "Stock" },
  ];
  let release;
  const firstPrices = new Promise((resolve) => { release = resolve; });
  const { context, element, run } = loadPage("assets.js", {
    catalogue, api: (request) => request.includes("A%2CB") ? firstPrices : Promise.resolve({}),
  });
  run("view.all = catalogue");
  const initial = context.render();
  run('view.query = "Second"');
  await context.render();
  release({});
  await initial;
  assert.deepEqual(element("list").children.map((row) => row.attrs.href), ["asset.html?isin=B&from=assets"]);
});

test("sparse price windows never use older quotes or fabricate volatility", () => {
  const { context } = loadPage("asset.js");
  const quotes = [["2018-03-01", 12], ["2022-03-01", 13]];
  assert.deepEqual(context.windowed(quotes, 1), [quotes[1]]);
  assert.equal(context.stats(quotes).vol, null);
});

test("asset explanation uses the exact stored session and falls back to the displayed facts after expiry", async () => {
  const view = {
    session: "session-uuid",
    result: {
      recommendation_id: "recommendation-uuid", ranking_source: "popularity", profile: { ceiling: 5 },
      items: [{ isin: "GR123", risk_class: 4, variance_change: -0.0042 }],
    },
  };
  const requests = [];
  const { context, element, run } = loadPage("asset.js", {
    sessionStorage: { getItem: () => JSON.stringify(view) },
    fetch: async (pathname, request) => {
      requests.push([pathname, JSON.parse(request.body)]);
      return { status: 404, ok: false };
    },
  });
  assert.equal(context.storedRecommendation(new URLSearchParams("rec=another"), "GR123"), null);
  assert.equal(context.storedRecommendation(new URLSearchParams("rec=recommendation-uuid&from=assets"), "GR123"), null);
  run('page.recommendation = storedRecommendation(new URLSearchParams("rec=recommendation-uuid"), "GR123")');
  await context.requestExplanation();
  assert.deepEqual(requests, [["explain", {
    recommendation_id: "recommendation-uuid", session_id: "session-uuid", isin: "GR123", language: "en",
  }]]);
  const markup = JSON.stringify(element("why").children);
  assert.match(markup, /why_popularity/);
  assert.match(markup, /why_explain_eligible/);
  assert.match(markup, /why_source_template/);
  assert.doesNotMatch(markup, /why_rank|why_source_llm/);
});

test("a popularity suggestion explains historical rank and risk eligibility without a portfolio simulation", async () => {
  const { context, element, run } = loadPage("asset.js", {
    fetch: async () => assert.fail("Risk facts do not need a model call when impact is unavailable"),
    t: (key, values) => values ? `${key} ${Object.values(values).join(" ")}` : key,
  });
  run(`page.recommendation = { id: "r", session: "s", item: { isin: "GR123", risk_class: 4, popularity_rank: 33 },
      rank: 4, rankingSource: "popularity", ceiling: 5, catalogSize: 288 }`);
  await context.requestExplanation();
  const paragraph = element("why").children.find((node) => node.attrs.lang === "en");
  assert.equal(paragraph.children[0], "why_explain_popularity_rank 33 288 why_explain_eligible 4 5 why_explain_add_holdings");
  assert.doesNotMatch(JSON.stringify(element("why").children), /why_explain_impact|why_source_llm/);
});

test("asset explanation appears immediately and adopts verified text in the active language", async () => {
  let resolveResponse;
  const { context, element, run } = loadPage("asset.js", {
    fetch: () => new Promise((resolve) => { resolveResponse = resolve; }),
    t: (key, values) => values ? `${key} ${Object.values(values).join(" ")}` : key,
  });
  run(`page.recommendation = { id: "r", session: "s", item: { isin: "GR123", risk_class: 3, variance_change: -0.02254 },
      rank: 1, ceiling: 5, rankingSource: "portfolio_embeddings" }`);
  const paragraph = () => element("why").children.find((node) => node.attrs.lang);
  const pending = context.requestExplanation();
  assert.equal(paragraph().attrs.lang, "en");
  assert.equal(paragraph().children[0], "why_explain_portfolio why_explain_eligible 3 5 why_explain_impact -0.0225");
  assert.match(JSON.stringify(element("why").children), /why_explaining/);
  resolveResponse({ ok: true, json: async () => ({
    isin: "GR123", language: "en", status: "verified", source: "llm", explanation: "Verified in English.",
  }) });
  await pending;
  assert.equal(paragraph().children[0], "why_explain_portfolio why_explain_cap 5 Verified in English.");
  assert.match(JSON.stringify(element("why").children), /why_source_llm/);
  run('LANG = "fr"; renderWhy()');
  assert.equal(paragraph().attrs.lang, "fr");
  assert.doesNotMatch(JSON.stringify(element("why").children), /Verified in English|why_source_llm/);
});

test("unverified model text leaves the calculated explanation in place", async () => {
  const { context, element, run } = loadPage("asset.js", {
    fetch: async () => ({ ok: true, json: async () => ({
      isin: "GR123", language: "en", status: "incorrect_facts", source: "llm", explanation: "Incorrect text.",
    }) }),
  });
  run(`page.recommendation = { id: "r", session: "s", item: { isin: "GR123", risk_class: 3, variance_change: -0.0225 },
      rank: 1, ceiling: 5, rankingSource: "portfolio_embeddings" }`);
  await context.requestExplanation();
  const markup = JSON.stringify(element("why").children);
  assert.match(markup, /why_explain_eligible/);
  assert.match(markup, /why_source_template/);
  assert.doesNotMatch(markup, /Incorrect text|why_source_llm/);
});

test("search matches words in any order, ignores accents, ranks ISIN and name starts first", () => {
  const { context, run } = loadPage("assets.js", { api: async () => [] });
  context.catalog = [
    { isin: "FR0007052782", name: "Amundi CAC 40 UCITS ETF", category: "MTF" },
    { isin: "XX1", name: "Société Générale", category: "Stock" },
    { isin: "XX2", name: "Cacao Holdings", category: "Stock" },
  ];
  const names = (q, o) => context.searchAssets(context.catalog, q, o).map((a) => a.isin).join();
  assert.equal(names("cac amundi"), "FR0007052782");
  assert.equal(names("societe generale"), "XX1");
  assert.equal(names("fr000705"), "FR0007052782");
  assert.equal(names("cac"), "XX2,FR0007052782");  // name starts with beats a later word
  assert.equal(names("stock"), "XX2,XX1");  // category is searchable
  assert.equal(names("", { limit: 1 }), "FR0007052782");
  assert.equal(names("zzz"), "");
  assert.equal(names("a", { exclude: new Set(["FR0007052782"]) }), "XX2,XX1");
});
