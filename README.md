# Unimind Studios website

Plain HTML, CSS and JavaScript. No framework. Every page is pre-built into its own folder
(`about/index.html`, `services/seo-content/index.html` …) so search engines and AI crawlers
that don't run JavaScript still see all the text, titles and structured data.

## What's in this zip
- `site/` – the finished website. Upload the **contents** of this folder.
- `source/` – where you edit things, then rebuild:
  - `site.config.json` – domain, email, booking link, form URL, offices, analytics IDs
  - `content.py` – all page copy (drafted, please review)
  - `data/work.json` – case studies, portfolio, testimonials, client logos, team
  - `data/insights.json` – articles
  - `legal/` – drop in `privacy-policy.html` and `terms-of-service.html`
  - `build.py` – builds the site; `qa.py` – runs all quality checks

## Rebuild after editing
```
cd source
pip install playwright && playwright install chromium   # once, for qa.py
python3 build.py            # writes source/dist/
python3 qa.py dist          # checks at a domain root
python3 qa.py dist /repo    # checks at a GitHub project address
```
Sections and pages with no real content stay hidden automatically:
Work appears once `work.json` has entries, Insights once an article exists,
legal pages once their files exist. Nothing placeholder is ever published.

## Publish on GitHub Pages
1. Create a repository and upload the contents of `site/` (keep the `.nojekyll` file).
2. Settings → Pages → Deploy from branch → `main` / root.
3. Works at `username.github.io/repo/` and on a custom domain (Settings → Pages → Custom domain).

## Analytics (exact order, once per page)
Fill `cookieyes_src`, `gtm_id`, `ga4_id` in `site.config.json`. The build writes, in the head:
CookieYes → Tag Manager → Google tag, and the Tag Manager noscript frame right after `<body>`.
**Double-counting warning:** if your Tag Manager container already has a GA4 tag with the same
G- ID, set `"gtm_already_fires_ga4": true` so the separate Google tag is skipped.

## Google Search Console
1. Set `site_url` (e.g. `https://www.yourdomain.com`) in `site.config.json` and rebuild.
   This adds canonical links, share-image tags and `sitemap.xml`.
2. Go to search.google.com/search-console → Add property → **Domain** (recommended, verify
   with a DNS TXT record at your domain provider) or **URL prefix** (paste the HTML-tag
   `content` value into `search_console_meta`, rebuild and upload).
3. Sitemaps → submit `sitemap.xml`.
4. URL inspection → test the home page and one service page → Request indexing.
5. Check Pages and Enhancements reports after a few days (FAQ, Breadcrumbs).

## Forms
Set `form_endpoint` to your Google Apps Script web-app URL (ends in `/exec`). Forms include
validation, a hidden honeypot field against spam bots, and success/error messages.
