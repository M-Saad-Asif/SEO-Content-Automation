"""Page intake: what kind of page is this, and what is its main keyword? Decided first, before any research,
because a service page, a product page, a category, a blog post and a home page answer different searches and are
built differently.

`intake(url)` reads the live page (or, for a page that doesn't exist yet, only its address) and scores the signals a
senior SEO looks at: the URL path, the offer on the page (rates, prices, "apply", "get a quote", forms), product and
article markup, blog furniture (author, date, "min read"), and the H1. The main keyword comes from the page itself:
the H1's head phrase when it contains the URL slug's words, otherwise the slug. Every signal is returned as evidence
and logged as a decision; the operator can override `page_type` or `target_query` in the brief.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from . import common as C

TYPES = ("service", "product", "category", "home", "guide", "location", "company")

BLOG_PATH = re.compile(r"/(blog|news|guides?|insights?|articles?|learn|resources|knowledge(-base)?|advice|help|"
                       r"hub|academy|journal|stories|magazine|tips)/", re.I)
PRODUCT_PATH = re.compile(r"/(products?|p|item|shop/[^/]+/[^/]+)/[^/]+", re.I)
CATEGORY_PATH = re.compile(r"/(collections?|category|categories|shop|range|department)(/[^/]+)?/?$", re.I)
COMPANY_PATH = re.compile(r"/(about(-us)?|contact(-us)?|team|careers|our-story|reviews|testimonials)/?$", re.I)
OFFER = re.compile(r"\b(apply( now| online)?|get a (quote|call ?back)|request a (quote|call)|enquire|book (a|an|your)|"
                   r"speak to (an?|our)|call us|contact us|our (team|experts|advisers|brokers|engineers)|we (arrange|offer|"
                   r"provide|install|repair|deliver|lend|fund|help)|from £?\d|(per|a) month|rates? from|"
                   r"free (quote|consultation|valuation|survey))\b", re.I)
CART = re.compile(r"\b(add to (cart|basket|bag)|in stock|out of stock|sku|£\s?\d+(\.\d\d)?\s*(inc|ex)\.? vat|"
                  r"buy now|quantity)\b", re.I)
BLOG_FURNITURE = re.compile(r"\b(\d+\s*min(ute)?s? read|posted (on|by)|published (on|by)|written by|by [A-Z][a-z]+ "
                            r"[A-Z][a-z]+|last updated|share this (post|article))\b")
QUESTION_H1 = re.compile(r"^(how|what|why|when|which|who|can|should|is|are|do|does|will)\b", re.I)
PLACE_WORDS = re.compile(r"\b(in|near|across)\s+[A-Z][a-z]+", re.M)


def _slug_words(url: str) -> list[str]:
    seg = [x for x in urlparse(url).path.split("/") if x]
    return re.sub(r"[-_]+", " ", seg[-1]).lower().split() if seg else []


PADDING = re.compile(r"\b(your |the |a |an )?(complete|ultimate|definitive|full|quick|simple|beginner'?s?|expert)?\s*"
                     r"(guide|explained|overview|tips|faqs?|checklist)( for \d{4}| \d{4})?\s*$", re.I)


def keyword_from(h1: str, title: str, url: str) -> str:
    """The page's main keyword: the H1's head phrase (before ":", "|", " - ") when it carries the slug's words,
    else the slug itself; without the site's name and padding ("your complete guide")."""
    slug = _slug_words(url)
    slug = [w for w in slug if not re.fullmatch(r"\d+|html?|php|aspx?|index", w)]
    brand = (urlparse(url).netloc.lower().removeprefix("www.").split(".")[0])

    def clean(s):
        s = re.sub(rf"\b{re.escape(brand)}\b", " ", s.lower()) if brand else s.lower()
        s = re.sub(r"[^\w£%' ]+", " ", s)
        prev = None
        while prev != s:
            prev, s = s, PADDING.sub("", " ".join(s.split())).strip()
        return " ".join(s.split())
    for cand in (h1 or "", re.split(r"\s[|–-]\s", title or "")[0]):
        head = clean(re.split(r"\s*[:|–—]\s*|\s+-\s+", cand.strip())[0])
        hw = head.split()
        sl = [w for w in clean(" ".join(slug)).split()]
        if sl and hw and sum(any(w.startswith(s[:5]) for w in hw) for s in sl) >= max(1, len(sl) - 1) and len(hw) <= 8:
            return head
    return clean(" ".join(slug))


def classify(url: str, doc: dict | None, html: str = "") -> tuple[str, list[str]]:
    """(page_type, evidence)."""
    path = urlparse(url).path or "/"
    ev, score = [], {t: 0 for t in TYPES}
    text = " ".join(x for _, x in (doc or {}).get("blocks", []))[:20000]
    h1 = next((x for t, x in (doc or {}).get("blocks", []) if t == "h1"), "")
    if path in ("", "/"):
        score["home"] += 10
        ev.append("the site's root address")
    if BLOG_PATH.search(path):
        score["guide"] += 4
        ev.append(f"blog-style path ({BLOG_PATH.search(path).group(1)})")
    if PRODUCT_PATH.search(path):
        score["product"] += 4
        ev.append("product-style path")
    if CATEGORY_PATH.search(path):
        score["category"] += 4
        ev.append("category-style path")
    if COMPANY_PATH.search(path):
        score["company"] += 6
        ev.append("about/contact path")
    if path.count("/") <= 2 and not BLOG_PATH.search(path) and path not in ("", "/"):
        score["service"] += 2
        ev.append("top-level path (where sites put their service pages)")
    if html:
        if re.search(r'"@type"\s*:\s*"Product"', html) or re.search(r'property="product:price', html):
            score["product"] += 5
            ev.append("Product markup")
        if re.search(r'"@type"\s*:\s*"(Service|FinancialProduct|LoanOrCredit|LocalBusiness)"', html):
            score["service"] += 4
            ev.append("Service/LocalBusiness markup")
        if re.search(r'"@type"\s*:\s*"(BlogPosting|NewsArticle)"', html):
            score["guide"] += 4
            ev.append("BlogPosting markup")
        forms = len(re.findall(r"<form\b", html, re.I))
        if forms:
            score["service"] += 1
            ev.append(f"{forms} form(s) on the page")
    offers = len(OFFER.findall(text[:6000]))
    if offers >= 2:
        score["service"] += min(6, offers)
        ev.append(f"{offers} offer signals near the top (rates, apply, quote, 'we arrange'…)")
    carts = len(CART.findall(text))
    if carts >= 2:
        score["product"] += 4
        ev.append("shopping signals (basket, stock, price)")
    if BLOG_FURNITURE.search(text[:3000]):
        score["guide"] += 3
        ev.append("blog furniture (author, date or reading time)")
    if h1 and QUESTION_H1.match(h1):
        score["guide"] += 3
        ev.append("the H1 is a question")
    slug = " ".join(_slug_words(url))
    if re.search(r"\b(guide|how to|what is|tips|ideas|explained|vs|versus|checklist|faq|questions)\b", slug + " " + h1.lower()):
        score["guide"] += 3
        ev.append("informational wording in the address or H1 (guide, how to, what is…)")
    if score["service"] and PLACE_WORDS.search(h1 or ""):
        score["location"] += score["service"] + 1
        ev.append("a service with a place in its H1")
    if doc is None:
        ev.append("the page doesn't exist yet: decided from its address only")
        if not any(score.values()):
            score["guide"] = 1
    if not any(score.values()):  # nothing points anywhere: an information page is the safe reading
        score["guide"] = 1
        ev.append("no commercial, product or blog signals: read as an information page")
    best = max(TYPES, key=lambda t: (score[t], -TYPES.index(t)))
    return best, ev


def intake(url: str) -> dict:
    """Read a page and decide its type and main keyword. {page_url, exists, page_type, target_query, h1, title,
    evidence}."""
    import httpx
    url = C.clean_url(url if url.startswith("http") else "https://" + url)
    res = C.run_async(C.fetch_many([{"url": url, "kind": "page", "parse": "doc"}])).get(url) or {}
    html = ""
    try:
        html = httpx.get(url, headers=C.HEADERS, follow_redirects=True, timeout=20).text[:400000]
    except Exception:
        pass
    exists = res.get("status") == 200 and res.get("state") in ("ok", "needs_js")
    if not exists:  # a script-built page: the rendering service reads it, when configured
        from . import spider
        r = spider.scrape_many([url]).get(url) or {}
        if r.get("state") == "ok":
            res, exists = r, True
    doc = res if exists else None
    h1 = next((x for t, x in (doc or {}).get("blocks", []) if t == "h1"), "") if doc else ""
    title = (doc or {}).get("title") or ""
    ptype, ev = classify(url, doc, html)
    kw = keyword_from(h1, title, url)
    from .market import from_page
    locale, mev = from_page(url, html)
    return {"page_url": C.clean_url(res.get("final_url") or url) if exists else url, "exists": exists,
            "page_type": ptype, "target_query": kw, "h1": h1, "title": title, "evidence": ev,
            "locale": locale, "locale_evidence": mev}
