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
    URLSearchParams, AbortSignal,
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

test("asset explanation uses the exact stored session and leaves facts visible after expiry", async () => {
  const view = {
    session: "session-uuid",
    result: {
      recommendation_id: "recommendation-uuid", ranking_source: "popularity", profile: { ceiling: 5 },
      items: [{ isin: "GR123", risk_class: 4, variance_change: null }],
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
    recommendation_id: "recommendation-uuid", session_id: "session-uuid", isin: "GR123",
  }]]);
  const markup = JSON.stringify(element("why").children);
  assert.match(markup, /why_popularity/);
  assert.match(markup, /why_source_facts/);
  assert.match(markup, /why_explain_expired/);
  assert.doesNotMatch(markup, /why_rank|why_source_llm/);
});

test("only a verified model response receives the local model label", async () => {
  let explanation = { isin: "GR123", status: "verified", source: "llm", explanation: "Verified text." };
  const { context, element, run } = loadPage("asset.js", {
    fetch: async () => ({ status: 200, ok: true, json: async () => explanation }),
  });
  run('page.recommendation = { id: "r", session: "s", item: { isin: "GR123" }, rank: 1 }');
  await context.requestExplanation();
  assert.match(JSON.stringify(element("why").children), /why_source_llm/);
  explanation = { ...explanation, status: "incorrect_facts", source: "template", explanation: "Calculated text." };
  await context.requestExplanation();
  assert.match(JSON.stringify(element("why").children), /why_source_template/);
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
