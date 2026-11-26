// Hero scene: the "spread" of possible portfolio paths, drawn as threads of light, one colour per risk class.
// Riskier classes fan out wider. Threads above the risk ceiling chosen in the graph card dim,
// the pointer combs through them, and one white thread carries "your portfolio".
(() => {
  const COLORS = ["#5B9BE6", "#3CC6B4", "#8FCB6E", "#F2BE4A", "#F58C4E", "#E8674D", "#D0558A"];
  const DIM = [120, 138, 158];
  const PER_CLASS = 22;
  const stage = document.querySelector(".hero-stage");
  const canvas = document.getElementById("spread");
  if (!stage || !canvas || !canvas.getContext) return;
  const ctx = canvas.getContext("2d");
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let seed = 20261126;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const gauss = () => Math.sqrt(-2 * Math.log(1 - rnd())) * Math.cos(2 * Math.PI * rnd());
  const wave = (amp) => ({ a: amp * (0.4 + rnd() * 0.6), f: 0.6 + rnd() * 2.2, p: rnd() * 6.283, s: (rnd() - 0.5) * 0.5 });

  const threads = [];
  for (let k = 1; k <= 7; k += 1) {
    for (let j = 0; j < PER_CLASS; j += 1) {
      threads.push({
        k, z: Math.max(-2.4, Math.min(2.4, gauss())), alpha: 0.26 + rnd() * 0.4, width: 0.6 + rnd() * 1.1,
        waves: [wave(0.35), wave(0.2), wave(0.12)], fine: { f: 22 + rnd() * 30, p: rnd() * 6.283, s: 0.4 + rnd() * 0.6 },
      });
    }
  }
  const mine = { k: 0, z: 0.35, alpha: 0.95, width: 2, waves: [wave(0.25), wave(0.12)], fine: { f: 26, p: 1, s: 0.6 } };

  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const palette = COLORS.map(rgb);
  const lit = palette.map(() => 1);  // eased 0..1 per class: 1 inside the ceiling, low above it
  const pointer = { x: -1e4, y: -1e4, tx: -1e4, ty: -1e4, on: 0, ton: 0 };
  const view = { w: 0, h: 0, scroll: 0 };
  let running = false;
  let raf = 0;
  const t0 = performance.now();

  function ceiling() {
    const card = document.getElementById("graph-card");
    const slider = document.getElementById("ceiling");
    return !card || card.hidden || !slider ? 7 : Number(slider.value);
  }

  function resize() {
    const box = stage.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    view.w = box.width; view.h = box.height;
    canvas.width = Math.round(box.width * dpr); canvas.height = Math.round(box.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!running) draw(still ? 99 : (performance.now() - t0) / 1000);
  }

  const ease = (x) => 1 - Math.pow(1 - Math.max(0, Math.min(1, x)), 3);

  // y of a thread at u (0 = origin, 1 = right edge). Wider fan and higher drift for riskier classes.
  function trace(th, t, reveal, close) {
    const { w, h } = view;
    const ox = -0.04 * w, oy = 0.84 * h, ex = 1.04 * w;
    const k = th.k || Math.max(1, ceiling() * 0.6);
    const sigma = (0.03 + 0.03 * k) * h * close;
    const n = Math.max(48, Math.min(120, Math.round(w / 13)));
    const pts = [];
    const last = Math.round(n * reveal);
    for (let i = 0; i <= last; i += 1) {
      const u = i / n;
      let z = th.z;
      for (const wv of th.waves) z += wv.a * Math.sin(wv.f * u * 6.283 + wv.p + wv.s * t);
      const x = ox + u * (ex - ox);
      let y = oy - u * h * (0.26 + 0.035 * k) * close - u * u * h * 0.06
        + sigma * Math.sqrt(u) * z
        + u * h * 0.006 * Math.sqrt(k) * Math.sin(th.fine.f * u + th.fine.p + th.fine.s * t * 3);
      if (pointer.on > 0.01) {
        const dx = x - pointer.x, dy = y - pointer.y, r = Math.min(w, h) * 0.17;
        const f = Math.exp(-(dx * dx + dy * dy) / (r * r));
        y += pointer.on * r * 0.55 * f * (dy / (Math.abs(dy) + r * 0.2));
      }
      pts.push(x, y);
    }
    return pts;
  }

  function stroke(pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0], pts[1]);
    for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
    ctx.stroke();
  }

  function draw(t) {
    const { w, h } = view;
    if (!w || !h) return;
    const close = 1 - 0.55 * view.scroll;
    const cap = ceiling();
    pointer.x += (pointer.tx - pointer.x) * 0.12; pointer.y += (pointer.ty - pointer.y) * 0.12;
    pointer.on += (pointer.ton - pointer.on) * 0.06;

    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = "lighter";
    const glow = ctx.createRadialGradient(0, 0.84 * h, 0, 0, 0.84 * h, Math.max(w, h) * 0.55);
    glow.addColorStop(0, "rgba(91,155,230,.22)"); glow.addColorStop(1, "rgba(91,155,230,0)");
    ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h);
    ctx.lineCap = "round"; ctx.lineJoin = "round";

    for (let k = 1; k <= 7; k += 1) lit[k - 1] += ((k <= cap ? 1 : 0.12) - lit[k - 1]) * (still ? 1 : 0.08);
    for (const th of threads) {
      const reveal = still ? 1 : ease((t - 0.2 - th.k * 0.09) / 2.2);
      if (reveal <= 0) continue;
      const pts = trace(th, t, reveal, close);
      if (pts.length < 4) continue;
      const v = lit[th.k - 1];
      const [r, g, b] = palette[th.k - 1].map((c, i) => Math.round(DIM[i] + (c - DIM[i]) * v));
      ctx.strokeStyle = `rgb(${r},${g},${b})`;
      ctx.globalAlpha = th.alpha * (0.35 + 0.65 * v);
      ctx.lineWidth = th.width;
      stroke(pts);
    }

    const reveal = still ? 1 : ease((t - 1.1) / 2.4);
    if (reveal > 0) {
      const pts = trace(mine, t, reveal, close);
      if (pts.length >= 4) {
        ctx.globalAlpha = 0.18; ctx.lineWidth = 7; ctx.strokeStyle = "#FFFFFF"; stroke(pts);
        ctx.globalAlpha = mine.alpha; ctx.lineWidth = mine.width; stroke(pts);
        // A pulse travels along your portfolio's thread.
        const at = still ? pts.length - 2 : 2 * Math.floor(((t * 0.11) % 1) * (pts.length / 2 - 1));
        const px = pts[at], py = pts[at + 1];
        const halo = ctx.createRadialGradient(px, py, 0, px, py, 26);
        halo.addColorStop(0, "rgba(255,255,255,.9)"); halo.addColorStop(0.25, "rgba(233,180,76,.45)"); halo.addColorStop(1, "rgba(233,180,76,0)");
        ctx.globalAlpha = 1; ctx.fillStyle = halo; ctx.fillRect(px - 26, py - 26, 52, 52);
      }
    }

    if (pointer.on > 0.01) {
      const lamp = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, 180);
      lamp.addColorStop(0, `rgba(190,215,255,${0.09 * pointer.on})`); lamp.addColorStop(1, "rgba(190,215,255,0)");
      ctx.globalAlpha = 1; ctx.fillStyle = lamp; ctx.fillRect(pointer.x - 180, pointer.y - 180, 360, 360);
    }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
  }

  function frame(now) {
    draw((now - t0) / 1000);
    raf = running ? requestAnimationFrame(frame) : 0;
  }
  function setRunning(on) {
    running = on && !still && !document.hidden;
    if (running && !raf) raf = requestAnimationFrame(frame);
  }

  new ResizeObserver(resize).observe(stage);
  new IntersectionObserver(([entry]) => setRunning(entry.isIntersecting)).observe(stage);
  document.addEventListener("visibilitychange", () => setRunning(stage.getBoundingClientRect().bottom > 0));
  if (still) document.getElementById("ceiling")?.addEventListener("input", () => draw(99));

  stage.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch") return;
    const box = stage.getBoundingClientRect();
    pointer.tx = event.clientX - box.left; pointer.ty = event.clientY - box.top; pointer.ton = 1;
    if (pointer.x < -1e3) { pointer.x = pointer.tx; pointer.y = pointer.ty; }
  });
  stage.addEventListener("pointerleave", () => { pointer.ton = 0; });

  // The graph card drifts a few whole pixels against the pointer (parallax), unless a finger or a drag is on it.
  const card = document.getElementById("graph-card");
  stage.addEventListener("pointermove", (event) => {
    if (!card || still || event.pointerType === "touch" || event.buttons) return;
    card.style.setProperty("--tx", `${Math.round((0.5 - event.clientX / window.innerWidth) * 18)}px`);
    card.style.setProperty("--ty", `${Math.round((0.5 - event.clientY / window.innerHeight) * 12)}px`);
  });
  stage.addEventListener("pointerleave", () => { card?.style.setProperty("--tx", "0px"); card?.style.setProperty("--ty", "0px"); });

  // Scroll: the fan closes, the copy drifts, and the top bar switches from night to day past the stage.
  const top = document.querySelector(".top");
  function onScroll() {
    const box = stage.getBoundingClientRect();
    view.scroll = Math.max(0, Math.min(1, -box.top / Math.max(1, box.height)));
    stage.style.setProperty("--p", view.scroll.toFixed(3));
    top?.classList.toggle("on-dark", box.bottom > (top.offsetHeight || 72));
    if (!running && still) draw(99);
  }
  function measureTop() {
    if (top) document.documentElement.style.setProperty("--top-h", `${top.offsetHeight}px`);
  }
  if (top) new ResizeObserver(measureTop).observe(top);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Headline comes in word by word, from blur to sharp. Re-run after a language switch.
  function splitHeadline() {
    const h1 = stage.querySelector("h1");
    if (!h1) return;
    const words = h1.textContent.trim().split(/\s+/);
    h1.replaceChildren(...words.flatMap((word, i) => {
      const span = document.createElement("span");
      span.className = "word"; span.style.setProperty("--i", i); span.textContent = word;
      return i ? [" ", span] : [span];
    }));
  }
  document.addEventListener("DOMContentLoaded", splitHeadline);
  document.addEventListener("langchange", splitHeadline);

  // Static figures follow the page language (0,189 in French, 0.189 in English).
  function formatFigures() {
    document.querySelectorAll("[data-n]").forEach((node) => {
      if (!node.dataset.counting) node.textContent = fmt(Number(node.dataset.n), Number(node.dataset.d || 0));
    });
    document.querySelectorAll("[data-pct]").forEach((node) => { node.textContent = pct(Number(node.dataset.pct), 0, false); });
  }
  document.addEventListener("DOMContentLoaded", formatFigures);
  document.addEventListener("langchange", formatFigures);

  // Sections fade up once as they enter the viewport; the facts band counts up the first time.
  document.addEventListener("DOMContentLoaded", () => {
    if (still || !("IntersectionObserver" in window)) return;
    document.documentElement.classList.add("js-reveal");
    const groups = [".method .eyebrow, .method h2, .method .lede", ".steps li", ".evidence .eyebrow, .evidence h2, .evidence .lede",
      ".ev-grid > figure, .ev-side > .card", ".limits", ".ask-panel", ".team h2", ".team li"];
    const seen = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add("in"); seen.unobserve(entry.target); }
    }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });
    for (const selector of groups) {
      document.querySelectorAll(selector).forEach((node, i) => {
        node.classList.add("reveal"); node.style.setProperty("--d", `${(i * 0.08).toFixed(2)}s`); seen.observe(node);
      });
    }

    const band = document.querySelector(".facts");
    const cells = [...document.querySelectorAll(".facts-grid [data-n]")];
    if (!band) return;
    cells.forEach((cell) => { cell.dataset.counting = "1"; cell.textContent = fmt(0); });
    const watch = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      watch.disconnect();
      const begin = performance.now();
      const step = (now) => {
        const p = Math.min(1, (now - begin) / 1600);
        const e = p < 1 ? 1 - Math.pow(2, -10 * p) : 1;
        cells.forEach((cell) => { cell.textContent = fmt(Math.round(Number(cell.dataset.n) * e)); });
        if (p < 1) requestAnimationFrame(step);
        else cells.forEach((cell) => { delete cell.dataset.counting; });
      };
      requestAnimationFrame(step);
    }, { threshold: 0.4 });
    watch.observe(band);
  });
})();
