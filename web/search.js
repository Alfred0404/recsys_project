// Asset search shared by the home page and the catalogue.
// Every typed word must appear somewhere in the name, ISIN or category, in any order.
const searchNormalize = (text) => String(text ?? "").toLowerCase().normalize("NFD")
  .replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();

// Lower score = better match. Returns null when the asset does not match every word.
function searchScore(asset, words, whole) {
  const name = searchNormalize(asset.name);
  const isin = asset.isin.toLowerCase();
  const nameWords = name.split(" ");
  const haystack = `${name} ${isin} ${searchNormalize(asset.category)}`;
  if (!words.every((w) => haystack.includes(w))) return null;
  if (isin === whole) return 0;
  if (isin.startsWith(whole)) return 1;
  if (name === whole) return 2;
  if (name.startsWith(whole)) return 3;
  if (words.every((w) => nameWords.some((nw) => nw.startsWith(w)))) return 4;
  return 5;
}

// searchAssets(catalog, "cac amundi", { limit: 8, exclude: Set, category: "MTF" }) -> assets, best first
function searchAssets(catalog, query, { limit = Infinity, exclude = null, category = null } = {}) {
  const whole = searchNormalize(query);
  const words = whole.split(" ").filter(Boolean);
  const pool = catalog.filter((a) => (!exclude || !exclude.has(a.isin)) && (!category || a.category === category));
  if (!words.length) return pool.slice(0, limit);
  const scored = [];
  for (const asset of pool) {
    const score = searchScore(asset, words, whole);
    if (score !== null) scored.push([score, asset]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name));
  return scored.slice(0, limit).map(([, asset]) => asset);
}

// Name split into plain and matched parts so the page can bold what the user typed (no innerHTML).
function highlightParts(text, query) {
  const words = [...new Set(searchNormalize(query).split(" ").filter(Boolean))];
  const lower = text.toLowerCase();
  const flags = new Array(text.length).fill(false);
  for (const word of words) {
    let at = lower.indexOf(word);
    while (at !== -1) {
      for (let i = at; i < at + word.length; i += 1) flags[i] = true;
      at = lower.indexOf(word, at + word.length);
    }
  }
  const parts = [];
  for (let i = 0; i < text.length; i += 1) {
    const last = parts[parts.length - 1];
    if (last && last.hit === flags[i]) last.text += text[i];
    else parts.push({ text: text[i], hit: flags[i] });
  }
  return parts;
}
