"""U-E: approximate URL Inspection's rendered HTML (UI-only) by diffing the raw server HTML with a rendered copy.

Raw = a plain fetch (normal and Googlebot user agents); rendered = Spider when configured. Content, H1 or links that
exist only after JavaScript are a rendering dependency; a bot-challenge page answered with 200 is the worst case.
The user can paste Search Console's 'View crawled page' HTML for the exact comparison.
"""
from __future__ import annotations

import re

from .. import common as C

GOOGLEBOT = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) " \
            "Chrome/129.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def _raw(url: str, ua: str) -> dict:
    import httpx
    try:
        r = httpx.get(url, headers={**C.HEADERS, "User-Agent": ua}, timeout=20, follow_redirects=True)
        d = C.parse_html(r.text, str(r.url))
        return {"status": r.status_code, "words": len(d["text"].split()), "h1": d["h1"], "links": len(d["links"]),
                "canonical": d["canonical"], "x_robots": r.headers.get("x-robots-tag", ""),
                "noindex_meta": bool(re.search(r"<meta[^>]+name=[\"']robots[\"'][^>]+noindex", r.text, re.I)),
                "challenge": any(m in r.text[:20000].lower() for m in C.BLOCK_MARKERS), "text": d["text"][:20000]}
    except Exception as e:
        return {"status": 0, "error": f"{type(e).__name__}: {e}"}


def check(url: str) -> dict:
    browser, bot = _raw(url, C.UA), _raw(url, GOOGLEBOT)
    findings = []
    if bot.get("status") != browser.get("status"):
        findings.append(f"Googlebot gets HTTP {bot.get('status')} but a browser gets {browser.get('status')}: a WAF/CDN rule")
    if bot.get("challenge") and bot.get("status") == 200:
        findings.append("Googlebot receives a bot-challenge page with status 200: Google may index or canonicalise the challenge")
    if bot.get("noindex_meta") or "noindex" in (bot.get("x_robots") or "").lower():
        findings.append("noindex is served to Googlebot")
    rendered = None
    from .. import spider
    if spider.api_key():
        rendered = (spider.scrape_many([url], 1, timeout_s=60) or {}).get(url)
    if rendered and rendered.get("state") == "ok":
        rw, bw = rendered.get("words", 0), bot.get("words", 0)
        if rw >= 150 and bw < 0.5 * rw:
            findings.append(f"the raw HTML has {bw} words, the rendered page {rw}: main content depends on JavaScript "
                            "(server-render or pre-render it)")
        if not bot.get("h1") and rendered.get("title"):
            findings.append("the H1 appears only after JavaScript")
    elif not rendered:
        findings.append("no renderer configured (SPIDER_API_KEY): compare with Search Console's View crawled page HTML instead")
    if bot.get("words", 0) < 100 and bot.get("status") == 200:
        findings.append(f"only {bot.get('words', 0)} words in the HTML Googlebot receives")
    return {"url": url, "googlebot": {k: v for k, v in bot.items() if k != "text"},
            "browser": {k: v for k, v in browser.items() if k != "text"},
            "rendered_words": (rendered or {}).get("words"), "findings": findings or ["no rendering problem detected"]}
