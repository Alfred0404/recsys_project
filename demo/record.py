"""Records the demo scenes to demo/raw/*.webm. The site must run on :8000 (uvicorn src.api.main:app)."""
import pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
RAW = HERE / "raw"
SIZE = {"width": 1280, "height": 720}
ACC = "<b style='color:#2f6bff;font-weight:600'>%s</b>"

INIT = """
addEventListener('DOMContentLoaded',()=>{
 const c=document.createElement('div');c.style.cssText='position:fixed;z-index:99999;width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,.9);border:3px solid #2f6bff;pointer-events:none;left:-50px;top:-50px;box-shadow:0 0 14px rgba(47,107,255,.7)';
 document.body.appendChild(c);addEventListener('mousemove',e=>{c.style.left=e.clientX-11+'px';c.style.top=e.clientY-11+'px'});
 const k=document.createElement('div');k.id='demo-cap';k.style.cssText='position:fixed;z-index:99998;left:50%;bottom:34px;transform:translateX(-50%);padding:14px 30px;border-radius:14px;background:rgba(10,10,12,.88);border:1px solid rgba(255,255,255,.16);backdrop-filter:blur(16px);color:#f4f4f5;font:500 27px Inter,Segoe UI,sans-serif;opacity:0;transition:opacity .5s;white-space:nowrap';
 document.body.appendChild(k);
 const s=sessionStorage.getItem('demo-cap');if(s){k.innerHTML=s;k.style.opacity=1}
});
"""


def record(browser, name, fn):
    ctx = browser.new_context(viewport=SIZE, record_video_dir=str(RAW / name), record_video_size=SIZE)
    ctx.add_init_script(INIT)
    pg = ctx.new_page()
    fn(pg)
    video = pg.video
    ctx.close()
    video.save_as(str(RAW / f"{name}.webm"))


def journey(pg):
    def cap(html):
        pg.evaluate("h=>{sessionStorage.setItem('demo-cap',h);const k=document.getElementById('demo-cap');k.style.opacity=0;setTimeout(()=>{k.innerHTML=h;k.style.opacity=1},500)}", html)

    def move(sel):
        b = pg.locator(sel).first.bounding_box()
        pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=25)

    pg.goto("http://127.0.0.1:8000/"); pg.wait_for_timeout(1500)
    cap("1 · Vous décrivez " + ACC % "votre portefeuille")
    pg.mouse.move(640, 400); pg.wait_for_timeout(2200)
    move("a.btn.primary"); pg.wait_for_timeout(400); pg.click("a.btn.primary"); pg.wait_for_timeout(1200)
    move("#query"); pg.click("#query")
    pg.keyboard.type("J’ai National Bank of Greece, je veux diversifier", delay=55); pg.wait_for_timeout(800)
    cap("2 · Vos préférences de " + ACC % "risque")
    move("#toggle"); pg.click("#toggle"); pg.wait_for_timeout(900)
    pg.select_option("#option-grid select >> nth=1", "1"); pg.wait_for_timeout(1400)
    pg.click("#toggle"); pg.wait_for_timeout(700)
    move("#go"); pg.click("#go"); pg.wait_for_selector(".rows .row"); pg.wait_for_timeout(2200)
    cap("3 · Des suggestions " + ACC % "classées" + ", avec risque et cours")
    pg.wait_for_timeout(3500)
    move(".rows .row"); pg.wait_for_timeout(700); pg.click(".rows .row")
    pg.wait_for_load_state(); pg.wait_for_timeout(1800)
    cap("4 · Et " + ACC % "pourquoi" + " chaque actif est suggéré")
    pg.mouse.wheel(0, 560); pg.wait_for_timeout(3500)


def scene(s, seconds):
    def run(pg):
        pg.goto((HERE / "scenes.html").as_uri() + f"?s={s}")
        pg.wait_for_timeout(seconds * 1000)
    return run


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch()
        record(b, "s1", scene(1, 13))
        record(b, "journey", journey)
        record(b, "s3", scene(3, 18))
        record(b, "s4", scene(4, 4))
        b.close()
