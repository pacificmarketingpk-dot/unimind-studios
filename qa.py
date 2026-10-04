#!/usr/bin/env python3
"""QA for the built site. Usage: python3 qa.py [dist_dir] [base_path]
Serves dist under base_path (e.g. /my-repo) to mimic a GitHub project address."""
import sys, os, json, re, threading, http.server, socketserver, functools, urllib.parse
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright

DIST = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "dist")
BASE = (sys.argv[2] if len(sys.argv) > 2 else "").rstrip("/")
PORT = 8790 + (7 if BASE else 0)
WIDTHS = [320, 390, 768, 1024, 1440, 1920]
PAGES = json.load(open(os.path.join(DIST, ".pages.json")))
fails, notes = [], []


class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = urllib.parse.urlparse(path).path
        if BASE and p.startswith(BASE):
            p = p[len(BASE):] or "/"
        return os.path.join(DIST, p.lstrip("/"))
    def log_message(self, *a): pass

socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("", PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
ROOT = f"http://localhost:{PORT}{BASE}/"

# ---- static checks (no JavaScript) ----
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.h = []; s.links = []; s.imgs = []; s.ld = []; s._ld = False; s.title = ""; s._t = False; s.desc = ""; s.canon = None; s.text = []; s._skip = 0
    def handle_starttag(s, t, a):
        a = dict(a)
        if re.fullmatch(r"h[1-6]", t): s.h.append(int(t[1]))
        if t == "a" and a.get("href"): s.links.append(a["href"])
        if t in ("link",) and a.get("rel") in ("stylesheet", "icon", "manifest", "apple-touch-icon"): s.links.append(a["href"])
        if t == "script" and a.get("src"): s.links.append(a["src"])
        if t == "img": s.imgs.append(a)
        if t == "script" and a.get("type") == "application/ld+json": s._ld = True
        if t in ("script", "style"): s._skip += 1
        if t == "title": s._t = True
        if t == "meta" and a.get("name") == "description": s.desc = a.get("content", "")
        if t == "link" and a.get("rel") == "canonical": s.canon = a.get("href")
    def handle_endtag(s, t):
        if t == "title": s._t = False
        if t == "script": s._ld = False
        if t in ("script", "style"): s._skip -= 1
    def handle_data(s, d):
        if s._ld: s.ld.append(d)
        if s._t: s.title += d
        if not s._skip: s.text.append(d)

titles, descs = {}, {}
for path, _, _ in PAGES:
    f = os.path.join(DIST, path, "index.html")
    src = open(f).read(); p = P(); p.feed(src)
    tag = "/" + path
    t, d = p.title.strip(), p.desc.strip()
    if not 50 <= len(t) <= 60: fails.append(f"{tag}: title length {len(t)} ({t})")
    if not 120 <= len(d) <= 158: fails.append(f"{tag}: description length {len(d)}")
    if t in titles: fails.append(f"{tag}: duplicate title with {titles[t]}")
    if d in descs: fails.append(f"{tag}: duplicate description with {descs[d]}")
    titles[t] = tag; descs[d] = tag
    if p.h.count(1) != 1: fails.append(f"{tag}: {p.h.count(1)} H1 tags")
    prev = 0
    for lv in p.h:
        if lv > prev + 1 and prev: fails.append(f"{tag}: heading jumps h{prev} -> h{lv}"); break
        prev = lv
    if p.h and p.h[0] != 1 and 1 in p.h and p.h.index(1) > 0: fails.append(f"{tag}: heading before H1")
    for block in p.ld:
        try:
            g = json.loads(block)["@graph"]
            types = [n["@type"] if isinstance(n["@type"], str) else "/".join(n["@type"]) for n in g]
            for n in g:
                if n["@type"] == "FAQPage":
                    import html as _h; vis = set(_h.unescape(re.sub(r"\s+", " ", x).strip()) for x in re.findall(r"<summary>(.*?)<i", src))
                    vis |= set(_h.unescape(x) for x in re.findall(r'<h2 id="ans-h">(.*?)</h2>', src))
                    for q in n["mainEntity"]:
                        if q["name"] not in vis: fails.append(f"{tag}: FAQ schema question not visible: {q['name']}")
            notes.append(f"{tag}: JSON-LD ok [{', '.join(types)}]")
        except Exception as ex:
            fails.append(f"{tag}: invalid JSON-LD {ex}")
    for href in p.links:
        if href.startswith(("http", "mailto:", "tel:", "#", "data:")): continue
        target = os.path.normpath(os.path.join(DIST, path, href.split("#")[0]))
        if os.path.isdir(target): target = os.path.join(target, "index.html")
        if not os.path.exists(target): fails.append(f"{tag}: broken link {href}")
    for im in p.imgs:
        if not (im.get("width") and im.get("height")): fails.append(f"{tag}: image without width/height {im.get('src')}")
        if im.get("src", "").startswith("data:"): fails.append(f"{tag}: base64 image")
    body = " ".join(p.text)
    for bad in [r"lorem", r"\bTODO\b", r"\[\s*_+", r"_{3,}", r"placeholder text", r"\bTBD\b", r"example\.com"]:
        if re.search(bad, body, re.I): fails.append(f"{tag}: placeholder-like text /{bad}/")
    words = len(re.findall(r"\w+", body))
    notes.append(f"{tag}: {words} words of real text in raw HTML (no JS needed)")

# ---- browser checks ----
results = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for path, _, _ in PAGES:
        for w in WIDTHS:
            pg = b.new_page(viewport={"width": w, "height": 900})
            errs, bad_req = [], []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda ex: errs.append(str(ex)))
            pg.on("response", lambda r: bad_req.append(f"{r.status} {r.url}") if r.status >= 400 else None)
            pg.goto(ROOT + path, wait_until="networkidle")
            ov = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            hdr = pg.evaluate("(()=>{const h=document.querySelector('.hdr');return h.scrollWidth<=h.clientWidth})()")
            broken_img = pg.evaluate("[...document.images].filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.src)")
            if ov > 0: fails.append(f"/{path} @{w}: horizontal overflow {ov}px")
            if not hdr: fails.append(f"/{path} @{w}: header does not fit")
            if errs: fails.append(f"/{path} @{w}: console errors {errs[:2]}")
            if bad_req: fails.append(f"/{path} @{w}: failed requests {bad_req[:2]}")
            if broken_img: fails.append(f"/{path} @{w}: broken images {broken_img[:2]}")
            pg.close()
        results.append(path)
    # interaction checks on home, a service page and contact
    for w in (390, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.goto(ROOT, wait_until="networkidle")
        if w > 1100:
            pg.click("[data-mega-btn]"); ok = pg.is_visible("#mega .mega-list"); pg.keyboard.press("Escape")
            if not ok: fails.append("mega menu did not open")
            pg.click(".hdr [data-book]")
        else:
            pg.click("[data-burger]")
            if not pg.is_visible("#mobile-menu"): fails.append("mobile menu did not open")
            pg.click("#mobile-menu [data-book]")
        if not pg.is_visible("#booking .modal-card"): fails.append(f"booking pop-up failed @{w}")
        pg.keyboard.press("Escape")
        if pg.is_visible("#booking .modal-card"): fails.append(f"booking pop-up did not close @{w}")
        # every button-like element visible fits viewport
        off = pg.evaluate("[...document.querySelectorAll('.btn')].filter(b=>{const r=b.getBoundingClientRect();return r.width&&!b.closest('.floatrow,.logos,.marquee')&&(r.left<0||r.right>innerWidth)}).length")
        if off: fails.append(f"{off} buttons off-screen @{w}")
        pg.goto(ROOT + "contact/", wait_until="networkidle")
        pg.click(".form-card button[type=submit]")
        msg = pg.inner_text(".form-card .form-msg")
        if "Fill in" not in msg and "email" not in msg.lower(): fails.append(f"contact validation message missing @{w}: {msg}")
        pg.close()
    # without JavaScript: direct links still render content
    ctx = b.new_context(java_script_enabled=False)
    for path, _, _ in PAGES:
        pg = ctx.new_page(); pg.goto(ROOT + path)
        h1 = pg.inner_text("h1")
        if not h1.strip(): fails.append(f"/{path}: no H1 without JavaScript")
        pg.close()
    b.close()
srv.shutdown()

print(f"Served at {ROOT}  |  {len(PAGES)} pages x {len(WIDTHS)} widths = {len(PAGES)*len(WIDTHS)} renders")
for n in notes: print("  ok  ", n)
print("\nFAILURES:" if fails else "\nALL CHECKS PASSED")
for f in fails: print("  FAIL", f)
sys.exit(1 if fails else 0)
