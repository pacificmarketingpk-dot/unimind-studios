#!/usr/bin/env python3
"""Unimind Studios site builder.

Writes every page as real HTML into dist/<page>/index.html, so the site works
without JavaScript, at a domain root and on a GitHub project address.

  python3 build.py                 # uses site.config.json
  python3 build.py --out other/    # different output folder
  python3 build.py --demo          # QA only: fills Work with labelled test data (never deploy)
"""
import json, os, re, shutil, sys, html, datetime
from content import SERVICES, HOME_FAQ, SERVICES_FAQ, CONTACT_FAQ, GLOSSARY, WORK_FAQ

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
OUT = os.path.join(HERE, args[args.index("--out") + 1] if "--out" in args else "dist")
DEMO = "--demo" in args

CFG = json.load(open(os.path.join(HERE, "site.config.json")))
WORK = json.load(open(os.path.join(HERE, "data/work.json")))
INS = json.load(open(os.path.join(HERE, "data/insights.json")))
if DEMO:
    WORK = json.load(open(os.path.join(HERE, "data/demo-work.json")))

SITE = (CFG.get("site_url") or "").rstrip("/")
NAME, LEGAL = "Unimind Studios", "Unimind Studios Pvt Ltd"
SV = {s["slug"]: s for s in SERVICES}
LEGAL_PAGES = {}
for slug, title in (("privacy-policy", "Privacy Policy"), ("terms-of-service", "Terms of Service")):
    p = os.path.join(HERE, "legal", slug + ".html")
    if os.path.exists(p) and open(p).read().strip():
        LEGAL_PAGES[slug] = (title, open(p).read())
ARTICLES = [a for a in INS.get("articles", []) if a.get("slug") and a.get("title")]
HAS_WORK = any(WORK.get(k) for k in ("case_studies", "portfolio", "testimonials"))
HAS_INS = bool(ARTICLES)

e = lambda s: html.escape(str(s), quote=True)
PAGES = []  # (path, title, desc) for sitemap and QA

ARROW = '<svg viewBox="0 0 16 16" width="16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'


def url(path):
    return (SITE + "/" + path) if SITE else None


def lab(n, text):
    return f'<span class="tag">{e(text)}</span>' if text else ""


def sec_head(n, label, h2, p="", hid=None):
    hid = hid or re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") + "-h"
    pp = f"<p>{p}</p>" if p else ""
    return hid, f'<div class="sec-head reveal">{lab(n, label)}<div><h2 id="{hid}">{h2}</h2>{pp}</div></div>'


def section(n, label, h2, p, inner, extra_cls=""):
    hid, head = sec_head(n, label, h2, p)
    return f'<section class="sec {extra_cls}" aria-labelledby="{hid}"><div class="wrap">{head}{inner}</div></section>'


def faq_html(items):
    return '<div class="faq reveal">' + "".join(
        f'<details><summary>{e(q)}<i aria-hidden="true"></i></summary><div class="a"><p>{e(a)}</p></div></details>' for q, a in items) + "</div>"


def faq_ld(items):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def cta(n, h, p, R):
    return f'''<section class="cta" aria-labelledby="cta-h"><div class="wrap"><div class="cta-box reveal">
<div>{lab(n, "Next step")}<h2 id="cta-h" style="margin-top:18px">{e(h)}</h2></div>
<div><p>{e(p)}</p><div class="btn-row"><a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a><a class="btn btn-ghost" href="{R}contact/">Send a message</a></div></div>
</div></div></section>'''


def crumbs(trail, R):
    li = []
    for i, (label, path) in enumerate(trail):
        if i == len(trail) - 1:
            li.append(f'<li aria-current="page">{e(label)}</li>')
        else:
            li.append(f'<li><a href="{R}{path}">{e(label)}</a></li>')
    return f'<nav class="crumbs" aria-label="Breadcrumb"><div class="wrap"><ol>{"".join(li)}</ol></div></nav>'


def svc_rows(R):
    return '<ul class="svc-list reveal">' + "".join(
        f'<li><a href="{R}services/{s["slug"]}/"><span class="n">{i+1:02d}</span><h3>{e(s["name"])}</h3><p>{e(s["line"])}</p><span class="go" aria-hidden="true">{ARROW}</span></a></li>'
        for i, s in enumerate(SERVICES)) + "</ul>"


def packages(R):
    P = [("Launch", "One-off", "Get online properly", "For new businesses that need a clear brand and a simple site that explains what they do.", ["Logo and basic brand kit", "Small website, designed and built", "Search basics set up", "Handover session"], False),
         ("Grow", "One-off", "Rebuild for growth", "For businesses whose current site is slow, confusing or hard to update.", ["Review of your current site", "New page plan and design", "Full build with an easy editor", "SEO setup and content help"], True),
         ("Partner", "Monthly", "Keep improving", "For teams who want a studio on hand for updates, new pages and search work.", ["A set number of studio hours", "Security updates and backups", "New pages and campaigns", "Monthly report in plain English"], False)]
    out = '<div class="pkgs reveal">'
    for k, t, h, p, items, feat in P:
        lis = "".join(f"<li>{e(x)}</li>" for x in items)
        cls = "btn-primary" if feat else "btn-ghost"
        out += f'<article class="pkg{" feature" if feat else ""}"><div class="pkg-top"><span class="label"><b>{k}</b></span><span class="label">{t}</span></div><h3>{h}</h3><p>{p}</p><ul>{lis}</ul><a class="btn {cls}" href="{R}contact/" data-book>Book Meeting</a></article>'
    return out + "</div>"


STEPS = [("Listen", "A meeting about your business, your customers and what isn't working today.", "A written brief"),
         ("Plan", "We map every page and write the key words before anything is designed.", "A page plan and quote"),
         ("Make", "Design, then build. You review clickable drafts and leave comments directly on them.", "A working preview"),
         ("Launch and look after", "We put the site live, check it on many devices and show your team how to edit it.", "The keys to your site")]


def steps_html(steps, with_get=True):
    out = '<ol class="steps reveal">'
    for i, st in enumerate(steps):
        get = f"<small>You get: {e(st[2])}</small>" if with_get and len(st) > 2 else ""
        out += f'<li><span class="big" aria-hidden="true">{i+1:02d}</span><h3>{e(st[0])}</h3><p>{e(st[1])}</p>{get}</li>'
    return out + "</ol>"


WHY = [("Plain words first", "We write the page before we design it. If a sentence would confuse your customer, it doesn't make the cut."),
       ("Speed is part of the design", "We test on ordinary phones and slow connections, not only on fast office laptops."),
       ("One team, start to finish", "The people who plan your site also design and build it. Nobody has to explain your business twice."),
       ("Honest reporting", "No promises about rankings. Each month you see what changed, what worked and what we'll try next.")]


def why_html():
    return '<div class="why reveal">' + "".join(f"<div><h3>{e(a)}</h3><p>{e(b)}</p></div>" for a, b in WHY) + "</div>"


# ---------- Work components (only render with real data) ----------
def img(src, alt, w, h, R, lazy=True):
    l = ' loading="lazy" decoding="async"' if lazy else ""
    return f'<img src="{R}{e(src)}" alt="{e(alt)}" width="{int(w)}" height="{int(h)}"{l}>'


def _cats(items):
    cats = []
    for c in items:
        if c.get("category") and c["category"] not in cats:
            cats.append(c["category"])
    return cats


def _filters(cats, label):
    return f'<div class="filters" role="group" aria-label="{label}">' + "".join(
        f'<button type="button" data-f="{e(c)}" aria-pressed="{"true" if c == "All" else "false"}">{e(c)}</button>' for c in ["All"] + cats) + "</div>"


def case_cards(R, items, limit=None):
    if not items:
        return ""
    cards = ""
    for i, c in enumerate(items[:limit] if limit else items):
        imgs = c.get("images") or ([{"src": c["image"], "w": c.get("image_w", 1600), "h": c.get("image_h", 1000), "alt": c["title"]}] if c.get("image") else [])
        thumb = f'<div class="frame"><div class="frame-bar" aria-hidden="true"><i></i><i></i><i></i></div>{img(imgs[0]["src"], imgs[0]["alt"], imgs[0]["w"], imgs[0]["h"], R)}</div>' if imgs else ""
        mets = "".join(f"<span><b>{e(v)}</b> {e(l)}</span>" for v, l in c.get("results", [])[:3])
        mets = f'<div class="metrics">{mets}</div>' if mets else ""
        visit = f'<a class="btn btn-ghost" href="{e(c["url"])}" target="_blank" rel="noopener noreferrer" aria-label="Visit site: {e(c["title"])} (opens in a new tab)">Visit site ↗</a>' if c.get("url") else ""
        res = "".join(f'<div class="kpi"><b>{e(v)}</b><span>{e(l)}</span></div>' for v, l in c.get("results", []))
        shots = "".join(f'<figure class="shot">{img(m["src"], m["alt"], m["w"], m["h"], R)}<figcaption>{e(m["alt"])}</figcaption></figure>' for m in imgs)
        uid = f"cs-{i}-{re.sub(r'[^a-z0-9]+', '-', c['title'].lower())}"
        detail = f'''<div id="{uid}" hidden><span class="tag">{e(c.get("category",""))}</span><h2 id="dlg-h">{e(c["title"])}</h2><p class="muted">{e(c.get("industry",""))}</p>
{"<div class='kpis'>"+res+"</div>" if res else ""}{"<p>"+e(c["detail"])+"</p>" if c.get("detail") else ""}{"<h3>The challenge</h3><p>"+e(c["challenge"])+"</p>" if c.get("challenge") else ""}{"<h3>What we did</h3><p>"+e(c["approach"])+"</p>" if c.get("approach") else ""}
<div class="shots">{shots}</div>{"<p class='fine'>"+e(c["source_note"])+"</p>" if c.get("source_note") else ""}{"<p>"+visit+"</p>" if visit else ""}</div>'''
        cards += f'''<article class="ccard" data-cat="{e(c.get("category",""))}">{thumb}<div class="cbody"><span class="label"><b>{e(c.get("category",""))}</b> · {e(c.get("industry",""))}</span><h3>{e(c["title"])}</h3><p>{e(c.get("summary",""))}</p>{mets}
<div class="cact"><button type="button" class="btn btn-primary" data-open="{uid}">View details</button>{visit}</div></div>{detail}</article>'''
    n = len(items)
    cats = _cats(items)
    filt = _filters(cats, "Filter case studies") + f'<p class="count" aria-live="polite">{n} {"case study" if n == 1 else "case studies"}</p>' if len(cats) > 1 and not limit else ""
    return f'<div data-filter-group data-one="case study" data-many="case studies">{filt}<div class="cgrid">{cards}</div></div>'


def portfolio(R, items):
    if not items:
        return ""
    figs = ""
    for i, g in enumerate(items):
        uid = f"gal-{i}"
        visit = f'<a class="gvisit" href="{e(g["url"])}" target="_blank" rel="noopener noreferrer" aria-label="Visit site: {e(g["title"])} (opens in a new tab)">Visit site ↗</a>' if g.get("url") else ""
        big = f'<div id="{uid}" hidden><span class="tag">{e(g.get("category",""))}</span><h2 id="dlg-h">{e(g["title"])}</h2><figure class="shot">{img(g["image"], g["title"], g.get("image_w",1600), g.get("image_h",1000), R)}</figure>{"<p>"+visit.replace("gvisit","btn btn-ghost")+"</p>" if visit else ""}</div>'
        figs += f'<figure class="gw" data-cat="{e(g.get("category",""))}"><button type="button" class="gi" data-open="{uid}" aria-label="Open {e(g["title"])}">{img(g["image"], g["title"], g.get("image_w",1600), g.get("image_h",1000), R)}</button><figcaption><span>{e(g["title"])}</span>{visit}</figcaption>{big}</figure>'
    n = len(items)
    cats = _cats(items)
    filt = _filters(cats, "Filter portfolio") + f'<p class="count" aria-live="polite">{n} {"piece" if n == 1 else "pieces"}</p>' if len(cats) > 1 else ""
    return f'<div data-filter-group data-one="piece" data-many="pieces">{filt}<div class="gal">{figs}</div></div>'


def testimonials(R, items, uid="tfloat"):
    if not items:
        return ""
    def card(t, i, hide=False):
        long = len(t["quote"]) > 280
        q = t["quote"][:260].rsplit(" ", 1)[0] + "…" if long else t["quote"]
        more = f'<button type="button" class="btn btn-ghost" data-open="tq-{i}"{" tabindex=-1" if hide else ""}>Read full quote</button>' if long else ""
        ph = img(t["photo"], t["name"], 48, 48, R) if t.get("photo") else ""
        ah = ' aria-hidden="true"' if hide else ""
        return f'<figure class="tcard"{ah}><blockquote>“{e(q)}”</blockquote>{more}<figcaption>{ph}<span><b>{e(t["name"])}</b>{"<small>"+e(t["role"])+"</small>" if t.get("role") else ""}</span></figcaption></figure>'
    row = "".join(card(t, i) for i, t in enumerate(items)) + "".join(card(t, i, True) for i, t in enumerate(items))
    full = "".join(f'<div id="tq-{i}" hidden><span class="label">Testimonial</span><h2 id="dlg-h">{e(t["name"])}</h2><p>“{e(t["quote"])}”</p><p class="muted">{e(t.get("role",""))}</p></div>' for i, t in enumerate(items) if len(t["quote"]) > 280)
    return f'<div class="floatrow" id="{uid}"><div class="track">{row}</div></div><div class="wrap"><button type="button" class="pause" data-pause="{uid}" aria-pressed="false">Pause</button></div>{full}'


def logo_strip(R, items, uid="logos"):
    if not items:
        return ""
    one = lambda l, hide: f'<span class="cli" style="--h:{int(l.get("display_h", 56))}px"{" aria-hidden=\"true\"" if hide else ""}>{img(l["image"], "" if hide else l["name"] + " logo", l.get("w",160), l.get("h",48), R)}</span>'
    row = "".join(one(l, False) for l in items) + "".join(one(l, True) for l in items)
    return f'<div class="logos" id="{uid}" role="region" aria-label="Businesses we have worked with"><div class="track">{row}</div></div><div class="wrap"><button type="button" class="pause" data-pause="{uid}" aria-pressed="false">Pause</button></div>'


# ---------- Page shell ----------
def org_node():
    n = {"@type": ["ProfessionalService", "Organization"], "@id": (SITE + "/#organization") if SITE else "#organization",
         "name": NAME, "legalName": LEGAL, "description": "A studio that designs and builds brands, websites and digital products.",
         "knowsAbout": [s["name"] for s in SERVICES]}
    if SITE:
        n.update({"url": SITE + "/", "logo": {"@type": "ImageObject", "url": SITE + "/assets/img/logo-512.png", "width": 512, "height": 512}, "image": SITE + "/assets/img/og-image.jpg"})
    if CFG.get("public_email"):
        n["email"] = CFG["public_email"]
    if CFG.get("show_phones") and CFG.get("phones"):
        n["telephone"] = CFG["phones"][0]
    offs = [o for o in CFG.get("offices", []) if o.get("city")]
    if offs:
        n["address"] = [{"@type": "PostalAddress", "streetAddress": o.get("street"), "addressLocality": o["city"], "addressRegion": o.get("region") or None, "postalCode": o.get("postal") or None, "addressCountry": o.get("country")} for o in offs]
    if CFG.get("socials"):
        n["sameAs"] = CFG["socials"]
    n["makesOffer"] = [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["name"], **({"url": SITE + "/services/" + s["slug"] + "/"} if SITE else {})}} for s in SERVICES]
    return n


def analytics_head():
    out = ""
    if CFG.get("cookieyes_src"):
        out += f'<script id="cookieyes" type="text/javascript" src="{e(CFG["cookieyes_src"])}"></script>\n'
    if CFG.get("gtm_id"):
        g = e(CFG["gtm_id"])
        out += f"<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','{g}');</script>\n"
    if CFG.get("ga4_id") and CFG.get("gtm_already_fires_ga4") is not True:
        g = e(CFG["ga4_id"])
        out += f'<script async src="https://www.googletagmanager.com/gtag/js?id={g}"></script>\n<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{g}");</script>\n'
    return out


def nav_html(R, current):
    cur = lambda k: ' aria-current="page"' if current == k else ""
    mega = "".join(f'<a href="{R}services/{s["slug"]}/"><strong>{e(s["name"])}</strong><small>{e(s["menu"])}</small></a>' for s in SERVICES)
    items = [("work", "Work")] if HAS_WORK else []
    items += [("about", "About")] + ([("insights", "Insights")] if HAS_INS else []) + [("contact", "Contact")]
    links = "".join(f'<a href="{R}{k}/"{cur(k)}><span>{t}</span></a>' for k, t in items)
    home_link = f'<a href="{R}"{" aria-current=\"page\"" if current == "home" else ""}><span>Home</span></a>'
    mob_sub = "".join(f'<a href="{R}services/{s["slug"]}/">{e(s["name"])}</a>' for s in SERVICES)
    mob = f'<a href="{R}">Home</a>' + "".join(f'<a href="{R}{k}/">{t}</a>' for k, t in items)
    svc_cur = " current" if current == "services" else ""
    return f'''<header class="site-header">
  <div class="wrap hdr">
    <a class="logo" href="{R}" aria-label="{NAME} home"><img class="mark" src="{R}assets/img/logo-mark-88.webp" width="44" height="44" alt="" decoding="async"><span class="long">Unimind Studios</span></a>
    <nav class="nav" aria-label="Main">
      {home_link}
      <div class="has-mega">
        <button type="button" class="{svc_cur.strip()}" data-mega-btn aria-expanded="false" aria-controls="mega"><span>Services</span>
          <svg class="chev" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></button>
        <div class="mega" id="mega"><div class="wrap mega-grid">
          <div class="mega-intro"><p class="mega-title">Six ways we can help</p><p>From the first sketch of your logo to the site that keeps working years later.</p><a class="btn btn-ghost" href="{R}services/">See all services</a></div>
          <div class="mega-list">{mega}</div>
        </div></div>
      </div>
      {links}
    </nav>
    <a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a>
    <button class="burger" type="button" data-burger aria-expanded="false" aria-controls="mobile-menu" aria-label="Open menu"><svg viewBox="0 0 20 14" aria-hidden="true"><path d="M0 1h20M0 7h20M0 13h20" stroke="currentColor" stroke-width="1.8"/></svg></button>
  </div>
</header>
<nav class="mobile-menu" id="mobile-menu" aria-label="Mobile">{mob.split("</a>",1)[0]}</a><a href="{R}services/">Services</a><div class="sub">{mob_sub}</div>{mob.split("</a>",1)[1]}<a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a></nav>'''


def footer_html(R):
    svc = "".join(f'<li><a class="ul" href="{R}services/{s["slug"]}/">{e(s["name"])}</a></li>' for s in SERVICES)
    studio = ([("work", "Work")] if HAS_WORK else []) + [("about", "About")] + ([("insights", "Insights")] if HAS_INS else []) + [("glossary", "Glossary")]
    studio = "".join(f'<li><a class="ul" href="{R}{k}/">{t}</a></li>' for k, t in studio)
    contact = f'<li><a class="ul" href="{R}contact/">Contact</a></li><li><a class="ul" href="{R}contact/" data-book>Book Meeting</a></li>'
    if CFG.get("public_email"):
        contact += f'<li><a class="ul" href="mailto:{e(CFG["public_email"])}">{e(CFG["public_email"])}</a></li>'
    if CFG.get("show_phones"):
        contact += "".join(f'<li><a class="ul" href="tel:{re.sub(r"[^0-9+]", "", p)}">{e(p)}</a></li>' for p in CFG.get("phones", []))
    legal = "".join(f'<a class="ul" href="{R}{k}/">{t}</a>' for k, (t, _) in LEGAL_PAGES.items())
    privacy_note = f' See our <a class="ul" href="{R}privacy-policy/">Privacy Policy</a>.' if "privacy-policy" in LEGAL_PAGES else ""
    return f'''<footer class="site-footer"><div class="wrap">
<div class="foot-brand"><a class="foot-logo" href="{R}" aria-label="{NAME} home"><img src="{R}assets/img/logo-mark-160.webp" width="80" height="80" alt="" loading="lazy" decoding="async"><span>Unimind Studios</span></a><p>Brands, websites and digital products, designed and built in plain English.</p></div>
<div class="foot-grid">
  <div class="news"><h2>Newsletter</h2><p>Occasional notes on clear websites and better search results. No spam.{privacy_note}</p>
    <form data-form data-ok="Thanks. You're on the list." novalidate>
      <input type="hidden" name="form" value="newsletter">
      <div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
      <label class="vh" for="nl-email">Email address</label>
      <input class="field" id="nl-email" type="email" name="email" placeholder="you@company.com" autocomplete="email" required>
      <button class="btn btn-primary" type="submit">Subscribe</button>
    </form><p class="form-msg" role="status" aria-live="polite"></p></div>
  <div><h2>Services</h2><ul>{svc}</ul></div>
  <div><h2>Studio</h2><ul>{studio}</ul></div>
  <div><h2>Get in touch</h2><ul>{contact}</ul></div>
</div>
<p class="wordmark" aria-hidden="true">Unimind<i></i></p>
<div class="foot-base"><span>© {datetime.date.today().year} {LEGAL}</span><nav aria-label="Legal">{legal}</nav></div>
</div></footer>'''


def modals(R):
    return f'''<div class="modal" id="booking" role="dialog" aria-modal="true" aria-labelledby="book-h" aria-hidden="true">
  <div class="modal-scrim" data-close></div>
  <div class="modal-card">
    <button class="modal-close" type="button" aria-label="Close"><svg viewBox="0 0 14 14" width="14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button>
    <span class="tag"><span class="dot" aria-hidden="true"></span>Free first meeting</span>
    <h2 id="book-h">Book a meeting with us.</h2>
    <p>You'll choose a time on our Google Calendar. In the meeting we'll cover:</p>
    <ul><li>What your business does and who it serves</li><li>What isn't working with your site today</li><li>What we'd fix first, and roughly how</li></ul>
    <a class="btn btn-primary" href="{BOOK or R + 'contact/'}"{' target="_blank" rel="noopener"' if BOOK else ''} data-booking-link>Book Meeting</a>
  </div>
</div>
<div class="modal" id="dlg" role="dialog" aria-modal="true" aria-labelledby="dlg-h" aria-hidden="true">
  <div class="modal-scrim" data-close></div>
  <div class="modal-card wide"><button class="modal-close" type="button" aria-label="Close"><svg viewBox="0 0 14 14" width="14" aria-hidden="true"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.8"/></svg></button><div class="dlg-body"></div></div>
</div>
<div class="float-cta" id="float-cta" aria-hidden="true">
  <span class="float-cta-text"><span class="dot" aria-hidden="true"></span>Have a project in mind?</span>
  <a class="btn btn-primary" href="{R}contact/" data-book tabindex="-1"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>Book Meeting</a>
</div>'''


BOOK = CFG.get("booking_url") or ""


def book_links(html_text, R):
    """Point every booking button straight at the calendar (falls back to Contact if no link is set)."""
    if not BOOK:
        return html_text
    return re.sub(r'href="[^"]*contact/"( class="[^"]*")? data-book', lambda m: f'href="{BOOK}" target="_blank" rel="noopener"{m.group(1) or ""} data-book', html_text)


def page(path, title, desc, body, current="", trail=None, ldtype="WebPage", extra_ld=(), og_type="website"):
    depth = path.count("/")
    R = "../" * depth if depth else "./"
    canon = url(path)
    graph = [org_node(), {"@type": "WebSite", "@id": (SITE + "/#website") if SITE else "#website", "name": NAME, "publisher": {"@id": org_node()["@id"]}, "inLanguage": "en", **({"url": SITE + "/"} if SITE else {})}]
    wp = {"@type": ldtype, "@id": (canon or "") + "#webpage", "name": title, "description": desc, "inLanguage": "en", "isPartOf": {"@id": graph[1]["@id"]}, "about": {"@id": graph[0]["@id"]}}
    if canon:
        wp["url"] = canon
    if trail:
        bl = {"@type": "BreadcrumbList", "@id": (canon or "") + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": lbl, **({"item": url(p)} if SITE else {})} for i, (lbl, p) in enumerate(trail)]}
        graph.append(bl)
        wp["breadcrumb"] = {"@id": bl["@id"]}
    graph.append(wp)
    graph += list(extra_ld)
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    seo = ""
    if canon:
        seo += f'<link rel="canonical" href="{canon}">\n<meta property="og:url" content="{canon}">\n<meta property="og:image" content="{SITE}/assets/img/og-image.jpg">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta name="twitter:image" content="{SITE}/assets/img/og-image.jpg">\n'
    if CFG.get("search_console_meta") and path == "":
        seo += f'<meta name="google-site-verification" content="{e(CFG["search_console_meta"])}">\n'
    gtm_ns = f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={e(CFG["gtm_id"])}" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n' if CFG.get("gtm_id") else ""
    crumb_html = crumbs(trail, R) if trail else ""
    doc = f'''<!doctype html>
<html lang="en" data-root="{R}" data-booking="{e(CFG.get("booking_url",""))}" data-endpoint="{e(CFG.get("form_endpoint",""))}">
<head>
{analytics_head()}<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0A1024">
{seo}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:locale" content="en">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<link rel="icon" href="{R}favicon.ico" sizes="48x48">
<link rel="icon" href="{R}assets/img/icon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="{R}assets/img/icon-16.png" type="image/png" sizes="16x16">
<link rel="apple-touch-icon" href="{R}assets/img/apple-touch-icon.png">
<link rel="manifest" href="{R}site.webmanifest">
<link rel="preload" href="{R}assets/fonts/plus-jakarta-sans-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{R}assets/css/style.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
{gtm_ns}<div class="bgfx" aria-hidden="true"><i></i></div>
<a class="skip" href="#main">Skip to content</a>
{nav_html(R, current)}
{crumb_html}
<main id="main">
{body(R)}
</main>
{footer_html(R)}
{modals(R)}
<script src="{R}assets/js/main.js" defer></script>
</body>
</html>
'''
    doc = book_links(doc, R)
    d = os.path.join(OUT, path)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(doc)
    PAGES.append((path, title, desc))


# ---------- Pages ----------
def home(R):
    tools_strip = ["Figma", "WordPress", "Shopify", "Webflow", "Google Analytics", "Search Console", "Adobe Illustrator"]
    strip = "".join(f"<span>{t}</span>" for t in tools_strip) + "".join(f'<span aria-hidden="true">{t}</span>' for t in tools_strip)
    contents = "".join(f'<li><a href="{R}services/{s["slug"]}/"><span>{i+1:02d}</span><span>{e(s["name"])}</span><span aria-hidden="true">↗</span></a></li>' for i, s in enumerate(SERVICES))
    caps = [("Brand", "How your business looks and sounds: logo, colours, fonts and the way you talk to customers.", '<rect x="4" y="4" width="32" height="32" rx="3"/><circle cx="20" cy="20" r="8"/><path d="M20 4v8M20 28v8"/>'),
            ("Websites", "Pages planned around what your customer needs to know, then built to load fast.", '<rect x="3" y="7" width="34" height="26" rx="3"/><path d="M3 14h34"/><circle cx="8" cy="10.5" r="1"/><circle cx="12" cy="10.5" r="1"/><path d="M9 21h14M9 26h9"/>'),
            ("Product design", "Screens for apps and online tools that people can use without reading a manual.", '<rect x="11" y="3" width="18" height="34" rx="3"/><path d="M17 32h6M15 10h10M15 15h10M15 20h6"/>'),
            ("Search", "SEO, short for search engine optimisation: the work that helps Google understand and show your pages.", '<circle cx="17" cy="17" r="11"/><path d="M25 25l11 11M12 17h10"/>')]
    caps_html = '<div class="caps reveal">' + "".join(f'<div class="cap"><svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">{ic}</svg><h3>{t}</h3><p>{p}</p></div>' for t, p, ic in caps) + "</div>"
    problems = [("Visitors can't tell what you do", "The first screen talks about vision and values. A new visitor leaves before they find your actual service."),
                ("Pages load slowly on phones", "Large images and heavy code make people wait. Many give up before the page appears."),
                ("Search engines miss you", "Without clear headings and page descriptions, Google struggles to understand who the page is for."),
                ("Every small change needs a developer", "Updating a price or a phone number turns into a ticket, an invoice and a week of waiting.")]
    prob = "".join(f"<li><strong>{a}</strong><span>{b}</span></li>" for a, b in problems)
    inds = "".join(f"<li>{x}</li>" for x in ["Professional services", "Online shops", "Education", "Clinics and healthcare", "Real estate", "Software companies", "Hospitality", "Non-profits"])
    tools = [("Design", [("Figma", "Layouts and prototypes"), ("Adobe Illustrator", "Logos and icons"), ("Adobe Photoshop", "Image editing")]),
             ("Build", [("WordPress", "Easy page editing"), ("Shopify", "Online shops"), ("HTML, CSS, JavaScript", "Custom, fast sites")]),
             ("Measure", [("Google Analytics", "Who visits and what they do"), ("Search Console", "How Google sees you"), ("Lighthouse", "Speed and accessibility checks")])]
    tools_html = '<div class="tools reveal">' + "".join(f'<div><h3>{g}</h3><ul>' + "".join(f"<li>{a}<span>{b}</span></li>" for a, b in items) + "</ul></div>" for g, items in tools) + "</div>"
    n = iter(range(1, 20))
    out = f'''<section class="hero"><div class="wrap hero-grid">
<div><span class="tag"><span class="dot" aria-hidden="true"></span>Brand, web and search studio</span><h1>Websites that make sense to <em>the people using them.</em></h1>
<p class="lede">We design and build brands, websites and digital products for growing businesses. Plain words, clear layouts and pages that load quickly on any phone.</p>
<div class="btn-row"><a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a><a class="btn btn-ghost" href="#services">See our services</a></div></div>
<aside class="contents" aria-label="What we do"><span class="chip c1" aria-hidden="true"><span class="dot"></span>Design and build</span><div class="contents-head"><span class="label"><b>What we do</b></span><span class="label">6 services</span></div><ol>{contents}</ol><span class="chip c2" aria-hidden="true"><span class="dot"></span>One team, start to finish</span></aside>
</div></section>
{('<section class="tstrip" aria-label="What clients say about us">' + testimonials(R, WORK["testimonials"], "tfloat-home") + '</section>') if WORK.get("testimonials") else ""}
<div class="strip" aria-label="Platforms we work with"><div class="strip-inner"><span class="strip-label label">We work in</span><div class="marquee" id="platforms"><div class="marquee-track">{strip}</div></div><button type="button" class="pause" data-pause="platforms" aria-pressed="false">Pause</button></div></div>
{section(f"{next(n):02d}", "What we do", "Four skills under one roof.", "Most businesses hire a designer, a developer and an SEO person separately, then spend weeks getting them to agree. We do all four, so nothing gets lost between handovers.", caps_html)}
<section class="sec" aria-labelledby="prob-h"><div class="wrap problem-grid"><div class="reveal">{lab(f"{next(n):02d}", "The problem")}<h2 id="prob-h" class="problem-quote" style="margin-top:22px">Most business websites describe the company. Few answer the customer's question.</h2></div><ul class="problem-list reveal">{prob}</ul></div></section>
<div id="services">{section(f"{next(n):02d}", "Services", "Pick one, or the whole set.", "Each service stands on its own. Most clients start with one and add others as the business grows.", svc_rows(R))}</div>
{section(f"{next(n):02d}", "Packages", "Three ways to work with us.", "Every project is quoted after a first meeting, because a five-page site and a fifty-page shop are very different jobs.", packages(R))}
{section(f"{next(n):02d}", "Why Unimind", "How we're different.", "Four habits we keep on every project, large or small.", why_html(), "dark")}
{section(f"{next(n):02d}", "Process", "Four steps, in order.", "You approve each step before the next one starts, so there are no surprises at the end.", steps_html(STEPS))}
'''
    if WORK.get("case_studies"):
        out += section(f"{next(n):02d}", "Selected work", "Recent projects.", "", case_cards(R, WORK["case_studies"], limit=3) + f'<p style="margin-top:28px"><a class="btn btn-ghost" href="{R}work/">See all work</a></p>')
    out += section(f"{next(n):02d}", "Industries", "Who we design for.", "Different fields, the same goal: help a visitor understand you quickly and take the next step.", f'<ul class="inds reveal">{inds}</ul>')
    out += section(f"{next(n):02d}", "Tools", "What we use, and why.", "We pick tools your team can keep using after we've finished, not ones that lock you in.", tools_html)
    out += section(f"{next(n):02d}", "Questions", "Questions we hear often.", "Short answers. If yours isn't here, ask us in a meeting.", faq_html(HOME_FAQ))
    out += cta(f"{next(n):02d}", "Tell us what isn't working.", "A short meeting, no slides. You'll leave with a clearer idea of what to fix first, whether or not we work together.", R)
    return out


def services_page(R):
    return f'''<section class="pg-hero"><div class="wrap">{lab("", "Services")}<h1>Six services, one studio.</h1><p class="lede">Brand, design, build and search, done by one team. Choose a single service or combine them. Every project starts with a free meeting.</p></div></section>
{section("01", "All services", "What we can do for you.", "Each page explains the service in plain English: what it is, what you get and how it works.", svc_rows(R))}
{section("02", "Packages", "Three ways to work with us.", "Every project is quoted after a first meeting, so you only pay for what you need.", packages(R))}
{section("03", "Process", "How every project runs.", "The same four steps, whatever the service.", steps_html(STEPS))}
{section("04", "Questions", "About our services.", "", faq_html(SERVICES_FAQ))}
{cta("05", "Not sure which service you need?", "Tell us what isn't working. We'll point you to the right starting place.", R)}'''


def service_page(s):
    def body(R):
        ch = "".join(f'<li><i aria-hidden="true">×</i>{e(x)}</li>' for x in s["ch"])
        ben = "".join(f"<li>{e(x)}</li>" for x in s["benefits"])
        dl = "".join(f"<div>{e(x)}</div>" for x in s["deliver"])
        uses = "".join(f"<li>{e(x)}</li>" for x in s["uses"])
        tg = "".join(f'<div class="card"><h3>{e(g)}</h3><ul>' + "".join(f"<li>{e(t)}</li>" for t in ts) + "</ul></div>" for g, ts in s["tools"])
        rel = "".join(f'<a href="{R}services/{k}/"><span class="label">Service</span><h3>{e(SV[k]["name"])}</h3><p>{e(SV[k]["line"])}</p><span class="more">Explore {e(SV[k]["name"].lower())} {ARROW}</span></a>' for k in s["related"])
        return f'''<section class="pg-hero"><div class="wrap hero-grid">
<div>{lab("", s["name"])}<h1>{e(s["h1"])}</h1><p class="lede">{e(s["lede"])}</p>
<div class="btn-row"><a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a><a class="btn btn-ghost" href="#included">What's included</a></div></div>
<aside class="answer" aria-labelledby="ans-h"><span class="label"><b>Short answer</b></span><h2 id="ans-h">{e(s["q"])}</h2><p>{e(s["a"])}</p></aside>
</div></section>
{section("02", "The challenge", e(s["ch_h"]), e(s["ch_p"]), f'<ul class="xlist reveal">{ch}</ul>')}
{section("03", "Overview", e(s["ov_h"]), "", f'<div class="ov reveal"><div><p class="big-p">{e(s["ov_p"])}</p><p class="note">{e(s["ov_note"])}</p></div><div class="card"><h3>What it does for you</h3><ul class="tick">{ben}</ul></div></div>')}
<div id="included">{section("04", "Deliverables", "What's included.", "The exact list is agreed in your quote and fitted to your project.", f'<div class="dgrid reveal">{dl}</div>')}</div>
{section("05", "Use cases", "When this helps.", "", f'<ul class="uses reveal">{uses}</ul>')}
{section("06", "Process", "How it works, step by step.", "You approve each step before the next one starts.", steps_html(s["steps"], False))}
{section("07", "Tools", "What we use.", "Tool names show what we work with. They don't suggest any partnership.", f'<div class="tgroups reveal">{tg}</div>')}
{section("08", "Questions", f"{e(s['name'])} questions.", "", faq_html(s["faq"]))}
{section("09", "Related services", "Pairs well with.", "", f'<div class="rel reveal">{rel}</div>')}
{cta("10", s["cta_h"], s["cta_p"], R)}'''
    path = f"services/{s['slug']}/"
    svc_ld = {"@type": "Service", "@id": (url(path) or "") + "#service", "name": s["name"], "serviceType": s["name"], "description": s["desc"], "provider": {"@id": org_node()["@id"]}}
    if SITE:
        svc_ld["url"] = url(path)
    faqs = [[s["q"], s["a"]]] + s["faq"]
    page(path, s["title"], s["desc"], body, "services", [("Home", ""), ("Services", "services/"), (s["name"], path)], extra_ld=[svc_ld, faq_ld(faqs)])


def about_page(R):
    services = "".join(f'<li><a href="{R}services/{s["slug"]}/"><span class="n">{i+1:02d}</span><h3>{e(s["name"])}</h3><p>{e(s["line"])}</p><span class="go" aria-hidden="true">{ARROW}</span></a></li>' for i, s in enumerate(SERVICES))
    team = ""
    if WORK.get("team"):
        team = section("", "Team", "The people you'll work with.", "", '<div class="team reveal">' + "".join(f'<figure>{img(t["photo"], t["name"], 800, 1000, R) if t.get("photo") else ""}<figcaption><b>{e(t["name"])}</b><span>{e(t.get("role",""))}</span></figcaption></figure>' for t in WORK["team"]) + "</div>")
    clients = ""
    if WORK.get("client_logos"):
        hid, head = sec_head("", "Clients", "Businesses we've worked with.")
        clients = f'<section class="sec" aria-labelledby="{hid}"><div class="wrap">{head}</div>{logo_strip(R, WORK["client_logos"], "logos-about")}</section>'
    tst = ""
    if WORK.get("testimonials"):
        hid, head = sec_head("", "Testimonials", "What clients say.")
        tst = f'<section class="sec" aria-labelledby="{hid}"><div class="wrap">{head}</div>{testimonials(R, WORK["testimonials"], "tfloat-about")}</section>'
    return f'''<section class="pg-hero"><div class="wrap">{lab("", "About")}<h1>A studio for brands and websites people understand.</h1><p class="lede">{LEGAL} designs and builds brands, websites and digital products. We care most about one thing: that your customer understands you quickly.</p></div></section>
{section("01", "Who we are", "Designers, writers and developers in one team.", "", '<div class="two-col reveal"><div></div><div class="prose"><p>Most businesses end up managing several freelancers or agencies: one for the logo, one for the website, another for search. Each hands over to the next, and something gets lost every time.</p><p>We put those skills in one studio. The people who plan your site also write it, design it and build it. That makes projects calmer, faster to agree and easier to look after later.</p><p>We work in plain English. If we use a technical word, we explain it.</p></div></div>')}
{section("02", "What we believe", "Four habits we keep.", "", why_html(), "dark")}
{section("03", "How we work", "Four steps, in order.", "", steps_html(STEPS))}
{team}{clients}{tst}
{section("04", "What we do", "Our services.", "", f'<ul class="svc-list reveal">{services}</ul>')}
{cta("05", "Let's talk about your project.", "A short meeting to understand your business and what you need. No slides, no pressure.", R)}'''


def work_page(R):
    out = f'<section class="pg-hero"><div class="wrap">{lab("", "Work")}<h1>Projects and results.</h1><p class="lede">Case studies, campaign dashboards and portfolio pieces from work we have delivered.</p></div></section>'
    if WORK.get("case_studies"):
        out += section("", "Case studies", "Results from real campaigns and websites.", "Figures come from the client's own Google Search Console or ads dashboard. Open a case study to see the screenshots.", case_cards(R, WORK["case_studies"]))
    if WORK.get("portfolio"):
        out += section("", "Portfolio", "Websites and designs we have made.", "", portfolio(R, WORK["portfolio"]))
    if WORK.get("testimonials"):
        hid, head = sec_head("", "Testimonials", "What people say about working with us.")
        out += f'<section class="sec" aria-labelledby="{hid}"><div class="wrap">{head}</div>{testimonials(R, WORK["testimonials"])}</section>'
    if WORK.get("client_logos"):
        hid, head = sec_head("", "Our clients", "Businesses we've worked with.")
        out += f'<section class="sec" aria-labelledby="{hid}"><div class="wrap">{head}</div>{logo_strip(R, WORK["client_logos"], "logos-work")}</section>'
    out += section("", "Questions", "About our work.", "", faq_html(WORK_FAQ))
    return out + cta("", "Want results like these?", "Tell us about your project and what you'd like to change. Every business is different, so we'll be honest about what's realistic for you.", R)


def contact_page(R):
    opts = "".join(f"<option>{e(s['name'])}</option>" for s in SERVICES) + "<option>Not sure yet</option>"
    email = f'<div class="card"><h3>Email</h3><p><a class="ul" href="mailto:{e(CFG["public_email"])}">{e(CFG["public_email"])}</a></p></div>' if CFG.get("public_email") else ""
    phones = ""
    if CFG.get("show_phones") and CFG.get("phones"):
        phones = '<div class="card"><h3>Phone</h3>' + "".join(f'<p><a class="ul" href="tel:{re.sub(r"[^0-9+]", "", p)}">{e(p)}</a></p>' for p in CFG["phones"]) + "</div>"
    offs = [o for o in CFG.get("offices", []) if o.get("city")]
    off_html, map_html = "", ""
    if offs:
        off_html = '<div class="card"><h3>Offices</h3>' + "".join(f'<div class="office"><b>{e(o.get("name") or o["city"])}</b><span>{e(", ".join(x for x in [o.get("street"), o.get("city"), o.get("region"), o.get("postal"), o.get("country")] if x))}</span></div>' for o in offs) + "</div>"
        q = ", ".join(x for x in [offs[0].get("street"), offs[0].get("city"), offs[0].get("country")] if x)
        map_html = f'<div class="map"><iframe title="Map of our {e(offs[0]["city"])} office" src="https://www.google.com/maps?q={html.escape(q.replace(" ", "+"))}&amp;output=embed" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe></div>'
    privacy = f' Read our <a class="ul" href="{R}privacy-policy/">Privacy Policy</a> to see how we use your details.' if "privacy-policy" in LEGAL_PAGES else ""
    return f'''<section class="pg-hero"><div class="wrap">{lab("", "Contact")}<h1>Tell us about your project.</h1><p class="lede">Send a message or book a meeting. Tell us what your business does and what isn't working, and we'll reply with a suggested next step.</p></div></section>
<section class="sec" aria-labelledby="form-h"><div class="wrap"><div class="contact-grid">
<div class="form-card reveal"><h2 id="form-h" style="font-size:clamp(30px,3.4vw,44px);margin-bottom:24px">Send a message</h2>
<form data-form data-ok="Thanks. Your message has been sent. We'll reply by email." novalidate>
<input type="hidden" name="form" value="contact">
<div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
<div class="frow"><div class="fgroup"><label for="c-name">Your name</label><input class="field" id="c-name" name="name" autocomplete="name" required></div>
<div class="fgroup"><label for="c-email">Email</label><input class="field" id="c-email" type="email" name="email" autocomplete="email" required></div></div>
<div class="frow"><div class="fgroup"><label for="c-co">Company <small>(optional)</small></label><input class="field" id="c-co" name="company" autocomplete="organization"></div>
<div class="fgroup"><label for="c-svc">What do you need?</label><select class="field" id="c-svc" name="service">{opts}</select></div></div>
<div class="fgroup"><label for="c-msg">Your message</label><textarea class="field" id="c-msg" name="message" required placeholder="What does your business do, and what would you like to change?"></textarea></div>
<p class="fine">We only use your details to reply to you.{privacy}</p>
<button class="btn btn-primary" type="submit">Send message</button>
</form><p class="form-msg" role="status" aria-live="polite"></p></div>
<div class="aside-stack reveal">
<div class="card"><h3>Book a meeting</h3><p>Prefer to talk? Pick a time on our Google Calendar for a free first meeting.</p><a class="btn btn-primary" href="{R}contact/" data-book>Book Meeting</a></div>
{email}{phones}{off_html}
</div></div>{map_html}</div></section>
{section("", "Questions", "Before you get in touch.", "", faq_html(CONTACT_FAQ))}'''


def glossary_page(R):
    nav = "".join(f'<a href="#{re.sub(r"[^a-z]+", "-", g.lower())}">{e(g)}</a>' for g, _ in GLOSSARY)
    groups = ""
    for g, terms in GLOSSARY:
        gid = re.sub(r"[^a-z]+", "-", g.lower())
        dl = "".join(f'<dt id="{re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")}">{e(t)}</dt><dd>{e(d)}</dd>' for t, d in terms)
        groups += f'<div class="gl-group" id="{gid}"><h2>{e(g)}</h2><dl>{dl}</dl></div>'
    return f'''<section class="pg-hero"><div class="wrap">{lab("", "Glossary")}<h1>Design and website terms, explained.</h1><p class="lede">Plain-English meanings for the words you'll hear when building a brand or website. One or two sentences each.</p></div></section>
<section class="sec" aria-label="Terms"><div class="wrap"><nav class="gl-nav" aria-label="Glossary sections">{nav}</nav>{groups}</div></section>
{cta("", "Still have a question?", "Ask us in a meeting. We're happy to explain anything in plain English.", R)}'''


def legal_page(title, content):
    return lambda R: f'<section class="pg-hero"><div class="wrap">{lab("", "Legal")}<h1>{e(title)}</h1></div></section><section class="sec"><div class="wrap"><div class="prose">{content}</div></div></section>'


def insights_page(R):
    li = "".join(f'<li><a href="{R}insights/{a["slug"]}/"><span class="label">{e(a.get("category",""))}<br>{e(a.get("date",""))}</span><div><h2>{e(a["title"])}</h2><p>{e(a.get("summary",""))}</p></div></a></li>' for a in ARTICLES)
    return f'<section class="pg-hero"><div class="wrap">{lab("", "Insights")}<h1>Notes from our work.</h1><p class="lede">What we learned on real projects, written in plain English.</p></div></section><section class="sec" aria-label="Articles"><div class="wrap"><ul class="alist">{li}</ul></div></section>'


def article(a):
    path = f"insights/{a['slug']}/"
    body = lambda R: f'<section class="pg-hero"><div class="wrap">{lab(a.get("category",""), a.get("date",""))}<h1>{e(a["title"])}</h1><p class="lede">{e(a.get("summary",""))}</p></div></section><section class="sec"><div class="wrap"><article class="prose">{a["body_html"]}</article></div></section>' + cta("", "Want help with something similar?", "Tell us about your project.", R)
    art = {"@type": "Article", "@id": (url(path) or "") + "#article", "headline": a["title"], "description": a.get("desc", ""), "datePublished": a.get("date"), "author": {"@id": org_node()["@id"]}, "publisher": {"@id": org_node()["@id"]}, "articleSection": a.get("category"), "inLanguage": "en"}
    page(path, a.get("seo_title") or (a["title"] + " | Unimind Studios"), a.get("desc", ""), body, "insights", [("Home", ""), ("Insights", "insights/"), (a["title"], path)], extra_ld=[art], og_type="article")


# ---------- Build ----------
def minify_assets():
    """Shrink CSS and JS in dist/ if terser and csso are installed (npm i -g terser csso-cli). Source files stay readable."""
    import subprocess
    bin_dir = os.path.expanduser("~/.npm-global/bin")
    for tool, path, args in (("csso", "assets/css/style.css", ["-i"]), ("terser", "assets/js/main.js", ["-c", "-m", "--"])):
        exe = shutil.which(tool) or (os.path.join(bin_dir, tool) if os.path.exists(os.path.join(bin_dir, tool)) else None)
        if not exe:
            continue
        f = os.path.join(OUT, path)
        try:
            if tool == "csso":
                out = subprocess.run([exe, "-i", f], capture_output=True, text=True, check=True).stdout
            else:
                out = subprocess.run([exe, f, "-c", "-m"], capture_output=True, text=True, check=True).stdout
            if out.strip():
                before = os.path.getsize(f); open(f, "w").write(out)
                print(f"  minified {path}: {before//1024} KB -> {os.path.getsize(f)//1024} KB")
        except Exception as ex:
            print(f"  (skipped minifying {path}: {ex})")



def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(OUT, "assets"))
    minify_assets()

    page("", "Unimind Studios | Brand, Web Design and Development Studio",
         "Unimind Studios designs brands, websites and digital products in plain language, with clear layouts and fast pages. See our services and book a meeting.",
         home, "home", None, extra_ld=[faq_ld(HOME_FAQ)])
    page("services/", "Services | Brand, Website, UX and SEO | Unimind Studios",
         "All Unimind Studios services in one place: brand identity, website design and development, UX and product design, SEO and content, and website care.",
         services_page, "services", [("Home", ""), ("Services", "services/")], "CollectionPage", [faq_ld(SERVICES_FAQ)])
    for s in SERVICES:
        service_page(s)
    page("about/", "About Unimind Studios | A Brand and Web Design Studio",
         "Meet Unimind Studios: one team of designers, writers and developers building brands and websites in plain English. See how we work and what we believe.",
         about_page, "about", [("Home", ""), ("About", "about/")], "AboutPage")
    if HAS_WORK:
        page("work/", "Our Work | Case Studies and Portfolio | Unimind Studios",
             "Case studies, websites and design work from Unimind Studios, with the challenge, what we did and the results for each real project we have delivered.",
             work_page, "work", [("Home", ""), ("Work", "work/")], "CollectionPage", [faq_ld(WORK_FAQ)])
    if HAS_INS:
        page("insights/", "Insights | Notes on Brands, Websites and SEO | Unimind",
             "Articles from Unimind Studios on brands, website design, development and SEO, written from our real project work in plain, practical English.",
             insights_page, "insights", [("Home", ""), ("Insights", "insights/")], "CollectionPage")
        for a in ARTICLES:
            article(a)
    terms = [{"@type": "DefinedTerm", "name": t, "description": d} for _, ts in GLOSSARY for t, d in ts]
    page("glossary/", "Glossary | Brand, Design and SEO Terms Explained | Unimind",
         "A plain-English glossary of brand, website design, development and SEO terms, from wireframes and CMS to AEO and GEO, explained in one or two sentences.",
         glossary_page, "", [("Home", ""), ("Glossary", "glossary/")], extra_ld=[{"@type": "DefinedTermSet", "@id": (url("glossary/") or "") + "#terms", "name": "Brand, design and website terms", "hasDefinedTerm": terms}])
    page("contact/", "Contact Unimind Studios | Book a Meeting or Send a Message",
         "Contact Unimind Studios to talk about a brand, website or SEO project. Send a short message or book a free meeting, and we will suggest a next step.",
         contact_page, "contact", [("Home", ""), ("Contact", "contact/")], "ContactPage", [faq_ld(CONTACT_FAQ)])
    for slug, (title, content) in LEGAL_PAGES.items():
        page(slug + "/", f"{title} | Unimind Studios", f"Read the {title} for the Unimind Studios website, covering how the site works and how information you share with us is handled.", legal_page(title, content), "", [("Home", ""), (title, slug + "/")])

    # 404 (served at any depth, so it finds the site root itself)
    known = ["services", "work", "about", "insights", "contact", "glossary", "privacy-policy", "terms-of-service"]
    n404 = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Page not found | Unimind Studios</title><meta name="robots" content="noindex"><meta name="theme-color" content="#0A1024">
<script>(function(){{var k={json.dumps(known)},s=location.pathname.split("/").filter(Boolean),b=(/\\.github\\.io$/i.test(location.hostname)&&s.length&&k.indexOf(s[0])<0)?"/"+s[0]+"/":"/";document.write('<base href="'+b+'">')}})();</script>
<link rel="stylesheet" href="assets/css/style.css"><link rel="icon" href="favicon.ico"></head><body>
<div class="bgfx" aria-hidden="true"><i></i></div><header class="site-header"><div class="wrap hdr"><a class="logo" href="./"><img class="mark" src="assets/img/logo-mark-88.webp" width="44" height="44" alt=""><span class="long">Unimind Studios</span></a></div></header>
<main id="main" class="e404"><div class="wrap"><span class="tag">404 / Page not found</span><h1 style="margin:20px 0 24px">This page doesn't exist.</h1><p class="lede">The link may be old or mistyped. Try the home page or our services.</p><div class="btn-row"><a class="btn btn-primary" href="./">Go to the home page</a><a class="btn btn-ghost" href="services/">See services</a></div></div></main></body></html>'''
    open(os.path.join(OUT, "404.html"), "w").write(n404)

    # Crawler files
    today = datetime.date.today().isoformat()
    if SITE:
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{url(p)}</loc><lastmod>{today}</lastmod></url>\n" for p, _, _ in PAGES) + "</urlset>\n"
        open(os.path.join(OUT, "sitemap.xml"), "w").write(sm)
    bots = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Google-Extended", "Applebot", "Applebot-Extended", "CCBot", "DuckDuckBot"]
    rb = "# Search engines and AI assistants are welcome.\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + "User-agent: *\nAllow: /\n"
    if SITE:
        rb += f"\nSitemap: {SITE}/sitemap.xml\n"
    open(os.path.join(OUT, "robots.txt"), "w").write(rb)
    base = SITE or ""
    llms = f"# {NAME}\n\n> {LEGAL} is a studio that designs and builds brands, websites and digital products, written in plain English with fast, accessible pages.\n\n## Services\n" + "".join(f"- [{s['name']}]({base}/services/{s['slug']}/): {s['line']}\n" for s in SERVICES)
    llms += f"\n## Key pages\n- [Home]({base}/)\n- [Services]({base}/services/)\n- [About]({base}/about/)\n" + (f"- [Work]({base}/work/)\n" if HAS_WORK else "") + (f"- [Insights]({base}/insights/)\n" if HAS_INS else "") + f"- [Glossary]({base}/glossary/): {sum(len(t) for _, t in GLOSSARY)} terms explained\n- [Contact]({base}/contact/)\n"
    llms += "\n## Short answers\n" + "".join(f"- {s['q']} {s['a']}\n" for s in SERVICES)
    open(os.path.join(OUT, "llms.txt"), "w").write(llms)
    man = {"name": NAME, "short_name": "Unimind", "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#0A1024", "theme_color": "#0A1024",
           "icons": [{"src": "assets/img/logo-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "assets/img/logo-512.png", "sizes": "512x512", "type": "image/png"}, {"src": "assets/img/logo-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
    open(os.path.join(OUT, "site.webmanifest"), "w").write(json.dumps(man, indent=2))
    if os.path.exists(os.path.join(HERE, "assets/img/favicon.ico")):
        shutil.copy(os.path.join(HERE, "assets/img/favicon.ico"), os.path.join(OUT, "favicon.ico"))
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    json.dump(PAGES, open(os.path.join(OUT, ".pages.json"), "w"))
    print(f"Built {len(PAGES)} pages into {OUT}" + ("  (DEMO DATA — do not deploy)" if DEMO else ""))
    if CFG.get("ga4_id") and CFG.get("gtm_id") and CFG.get("gtm_already_fires_ga4") is None:
        print("WARNING: GA4 and GTM are both set. If your GTM container already fires GA4, set gtm_already_fires_ga4 to true or visits will be counted twice.")


if __name__ == "__main__":
    build()
