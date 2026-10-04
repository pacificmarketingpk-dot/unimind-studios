#!/usr/bin/env python3
"""Bundle dist/ into ONE self-contained HTML file with in-page navigation (preview only)."""
import os, re, json, base64, posixpath
D = "dist"
pages = json.load(open(f"{D}/.pages.json"))
css = open(f"{D}/assets/css/style.css").read()
css = re.sub(r'url\("\.\./fonts/([^"]+)"\)', lambda m: 'url("data:font/woff2;base64,' + base64.b64encode(open(f"{D}/assets/fonts/" + m.group(1), "rb").read()).decode() + '")', css)
js = open(f"{D}/assets/js/main.js").read()

def inline_imgs(html):
    """Preview only: embed images so the single-file preview shows them."""
    def rep(m):
        f = m.group(2).split("assets/img/")[1]
        mime = "image/webp" if f.endswith(".webp") else "image/png"
        return m.group(1) + '"data:' + mime + ';base64,' + base64.b64encode(open(f"{D}/assets/img/" + f, "rb").read()).decode() + '"'
    return re.sub(r'(src=)"((?:\.{1,2}/)*assets/img/[^"]+)"', rep, html)


def rewrite(html, path):
    def fix(m):
        h = m.group(2)
        if h.startswith(("http", "mailto:", "tel:", "#", "data:")):
            return m.group(0)
        frag = ""
        if "#" in h: h, frag = h.split("#", 1)
        r = posixpath.normpath(posixpath.join("/" + path, h)).strip("/")
        r = "" if r == "." else r
        return f'{m.group(1)}"#/{r}"'
    return inline_imgs(re.sub(r'(href=)"([^"]*)"', fix, html))

tpl, titles = [], {}
for path, title, desc in pages:
    src = open(f"{D}/{path}index.html").read()
    crumbs = re.search(r'(<nav class="crumbs".*?</nav>)', src, re.S)
    main = re.search(r'<main id="main">(.*)</main>', src, re.S).group(1)
    body = rewrite((crumbs.group(1) if crumbs else "") + main, path)
    r = path.strip("/")
    titles[r] = title
    tpl.append(f'<template data-route="{r}">{body}</template>')

home = open(f"{D}/index.html").read()
header = rewrite(home[home.index('<header class="site-header">'):home.index('<main id="main">')], "")
footer = rewrite(re.search(r'(<footer class="site-footer">.*?</footer>)', home, re.S).group(1), "")
mods = rewrite(re.search(r'(<div class="modal" id="booking".*?)<script src', home, re.S).group(1), "")
ld = re.search(r'<script type="application/ld\+json">.*?</script>', home, re.S).group(0)

router = """
(function(){
  var T={}, titles=%s, main=document.getElementById('main');
  document.querySelectorAll('template[data-route]').forEach(function(t){T[t.getAttribute('data-route')]=t});
  function show(){
    var h=location.hash;
    if(h && h.indexOf('#/')!==0){var el=document.getElementById(h.slice(1)); if(el) el.scrollIntoView(); return;}
    var r=h.replace(/^#\\/?/,'').replace(/\\/+$/,'');
    if(!T[r]) r='';
    main.innerHTML=T[r].innerHTML;
    document.title=titles[r];
    document.querySelectorAll('.nav a').forEach(function(a){a.removeAttribute('aria-current'); if(a.getAttribute('href')==='#/'+r||(r===''&&a.getAttribute('href')==='#/')) a.setAttribute('aria-current','page')});
    var sb=document.querySelector('[data-mega-btn]'); if(sb) sb.classList.toggle('current', r.indexOf('services')===0);
    var m=document.getElementById('mega'); if(m) m.classList.remove('open');
    var mb=document.querySelector('[data-mega-btn]'); if(mb) mb.setAttribute('aria-expanded','false');
    if(window.UnimindReveal) window.UnimindReveal(main);
    window.scrollTo({top:0,left:0,behavior:'instant'});
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest('a[href^="#"]'); if(!a) return;
    var h=a.getAttribute('href');
    if(h.indexOf('#/')!==0 && h.length>1){var el=document.getElementById(h.slice(1)); if(el){e.preventDefault(); el.scrollIntoView({behavior:'smooth'});}}
  });
  window.addEventListener('hashchange',show); show();
})();
""" % json.dumps(titles)

out = f'''<!doctype html>
<html lang="en" data-root="#/" data-booking="{json.load(open('site.config.json')).get('booking_url','')}" data-endpoint="">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Unimind Studios | Brand, Web Design and Development Studio</title>
<link rel="icon" href="data:image/png;base64,{base64.b64encode(open(D+'/assets/img/icon-32.png','rb').read()).decode()}"><meta name="description" content="{pages[0][2]}"><meta name="theme-color" content="#0A1024">
<style>{css}</style>{ld}</head>
<body><div class="bgfx" aria-hidden="true"><i></i></div><a class="skip" href="#main">Skip to content</a>
{header}
<main id="main"></main>
{footer}
{mods}
{"".join(tpl)}
<script>{js}</script>
<script>{router}</script>
</body></html>'''
os.makedirs("/mnt/user-data/outputs", exist_ok=True)
open("/mnt/user-data/outputs/unimind-site-preview.html", "w").write(out)
print(len(out)//1024, "KB,", len(tpl), "pages bundled")
