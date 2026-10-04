#!/usr/bin/env python3
"""Device audit across phones, tablets, laptops, desktops and TVs.
Usage: python3 devices.py [dist] [--shots]"""
import sys, os, json, threading, http.server, socketserver, random, functools
from playwright.sync_api import sync_playwright

DIST = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "dist")
SHOTS = "--shots" in sys.argv
PAGES = [p for p, _, _ in json.load(open(os.path.join(DIST, ".pages.json")))]
# name, width, height, touch, dpr
DEVICES = [
    ("Galaxy Fold (folded)", 280, 653, True, 3), ("iPhone SE", 320, 568, True, 2), ("Galaxy S8", 360, 740, True, 3),
    ("iPhone 13 mini", 375, 812, True, 3), ("iPhone 15", 393, 852, True, 3), ("iPhone 15 Pro Max", 430, 932, True, 3),
    ("Phone landscape", 667, 375, True, 2), ("iPhone landscape", 852, 393, True, 3),
    ("iPad mini", 768, 1024, True, 2), ("iPad Air", 820, 1180, True, 2), ("Surface Pro", 912, 1368, True, 2),
    ("iPad landscape", 1024, 768, True, 2), ("iPad Pro landscape", 1366, 1024, True, 2),
    ("Small laptop", 1280, 720, False, 1), ("Laptop", 1366, 768, False, 1), ("MacBook Air", 1440, 900, False, 2),
    ("Desktop FHD", 1920, 1080, False, 1), ("TV / QHD", 2560, 1440, False, 1), ("Ultrawide", 3440, 1440, False, 1), ("4K TV", 3840, 2160, False, 1),
]
PORT = random.randint(41000, 49000)
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("", PORT), functools.partial(type('Q',(http.server.SimpleHTTPRequestHandler,),{'log_message':lambda *a:None}), directory=DIST))

threading.Thread(target=srv.serve_forever, daemon=True).start()

PROBE = """(touch)=>{
 const W=document.documentElement.clientWidth, H=innerHeight, out={};
 out.overflow=document.documentElement.scrollWidth-W;
 const h=document.querySelector('.hdr'); out.header=h.scrollWidth<=h.clientWidth+1;
 const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&!e.closest('[hidden],.hp,.floatrow,.logos,.marquee,.mega:not(.open),.mobile-menu:not(.open),.modal:not(.open),.float-cta:not(.show)')};
 const tgt=[...document.querySelectorAll('a,button,summary,input,select,textarea')].filter(vis);
 out.small_targets=touch?[...new Set(tgt.filter(e=>{const r=e.getBoundingClientRect();return (r.height<40||r.width<40)&&!e.closest('.prose,.faq .a,p')}).map(e=>(e.textContent||e.getAttribute('aria-label')||e.tagName).trim().slice(0,28)))].slice(0,8):[];
 out.small_text=[...new Set([...document.querySelectorAll('p,li,a,span,small,label,dd,figcaption,summary,button')].filter(vis).filter(e=>e.childNodes.length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<12).map(e=>e.textContent.trim().slice(0,24)))].slice(0,6);
 out.input_zoom=touch?[...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(vis).filter(e=>parseFloat(getComputedStyle(e).fontSize)<16).length:0;
 const lede=document.querySelector('main p'); out.line_ch=lede?Math.round(lede.getBoundingClientRect().width/ (parseFloat(getComputedStyle(lede).fontSize)*0.5)):0;
 const wrap=document.querySelector('main .wrap'); out.content_w=wrap?Math.round(wrap.getBoundingClientRect().width):0;
 out.content_ratio=Math.round(out.content_w/W*100);
 const h1=document.querySelector('h1'); out.h1_px=Math.round(parseFloat(getComputedStyle(h1).fontSize));
 out.body_px=Math.round(parseFloat(getComputedStyle(document.body).fontSize));
 out.header_h=Math.round(document.querySelector('.site-header').getBoundingClientRect().height);
 return out}"""

issues, table = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, w, h, touch, dpr in DEVICES:
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, is_mobile=touch and w < 1100, has_touch=touch)
        worst = {}
        for path in PAGES:
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://localhost:{PORT}/{path}", wait_until="networkidle")
            r = pg.evaluate(PROBE, touch)
            tag = f"{name} {w}x{h} /{path}"
            if r["overflow"] > 0: issues.append(f"{tag}: sideways scroll {r['overflow']}px")
            if not r["header"]: issues.append(f"{tag}: header doesn't fit")
            if r["small_targets"]: issues.append(f"{tag}: small tap targets {r['small_targets']}")
            if r["small_text"]: issues.append(f"{tag}: text under 12px {r['small_text']}")
            if r["input_zoom"]: issues.append(f"{tag}: {r['input_zoom']} form fields under 16px (iPhone zooms in)")
            if errs: issues.append(f"{tag}: JS errors {errs[:1]}")
            if path == "":
                worst = r
                # pop-up + menu fit
                if w < 1101:
                    pg.click("[data-burger]"); pg.wait_for_timeout(150)
                    mm = pg.evaluate("(()=>{const m=document.getElementById('mobile-menu').getBoundingClientRect();return {bottom:m.bottom,h:innerHeight,scroll:document.getElementById('mobile-menu').scrollHeight>document.getElementById('mobile-menu').clientHeight}})()")
                    if mm["bottom"] > mm["h"] + 1: issues.append(f"{tag}: mobile menu runs off screen")
                    pg.keyboard.press("Escape")
                pg.click(".hero [data-book]"); pg.wait_for_timeout(200)
                md = pg.evaluate("(()=>{const c=document.querySelector('#booking .modal-card').getBoundingClientRect();const btn=document.querySelector('#booking [data-booking-link]');return {fits:c.top>=0&&c.bottom<=innerHeight+1, scrollable:document.querySelector('#booking .modal-card').scrollHeight>document.querySelector('#booking .modal-card').clientHeight}})()")
                if not md["fits"]: issues.append(f"{tag}: booking pop-up doesn't fit")
                pg.keyboard.press("Escape")
                if SHOTS:
                    pg.wait_for_timeout(300)
                    pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))"); pg.wait_for_timeout(700)
                    pg.screenshot(path=f"/home/claude/dev-{w}x{h}.png")
            pg.close()
        table.append((name, w, h, worst))
        ctx.close()
    b.close()
srv.shutdown()
print(f"{'Device':24} {'size':>10} {'H1':>4} {'body':>4} {'header':>6} {'content%':>8}")
for name, w, h, r in table:
    print(f"{name:24} {str(w)+'x'+str(h):>10} {r['h1_px']:>4} {r['body_px']:>4} {r['header_h']:>6} {r['content_ratio']:>7}%")
print(f"\n{len(PAGES)} pages x {len(DEVICES)} devices = {len(PAGES)*len(DEVICES)} page loads")
print("\nISSUES:" if issues else "\nNO ISSUES")
seen = set()
for i in issues:
    key = i.split(" /")[0].split(" ")[0] + i.split(":")[-1][:60]
    print("  -", i)
