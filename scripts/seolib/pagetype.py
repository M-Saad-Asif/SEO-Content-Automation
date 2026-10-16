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

TYPES = ("service", "product", "category", "home", "guide", "location", "company", "tool")
# A page whose main content is an interactive tool: the tool is the offer, the text explains it
TOOL_WORDS = re.compile(r"\b(calculators?|converters?|checkers?|estimators?|planners?|generators?|simulators?|"
                        r"trackers?|quiz(zes)?|finders?|counters?|timers?|tool)\b", re.I)

BLOG_PATH = re.compile(r"/(blog|news|guides?|insights?|articles?|learn|resources|knowledge(-base)?|advice|help|"
                       r"hub|academy|journal|stories|magazine|tips)(/|$)", re.I)
PRODUCT_PATH = re.compile(r"/(products?|p|item|shop/[^/]+/[^/]+)/[^/]+", re.I)
CATEGORY_PATH = re.compile(r"/(collections?|category|categories|shop|range|department)(/[^/]+)?/?$", re.I)
COMPANY_PATH = re.compile(r"/(about(-us)?|contact(-us)?|team|careers|our-story|reviews|testimonials)/?$", re.I)
OFFER = re.compile(r"\b(apply( now| online)?|get a (quote|call ?back)|request a (quote|call)|enquire|book (a|an|your)|"
                   r"speak to (an?|our)|call us|contact us|our (team|experts|advisers|brokers|engineers)|we (arrange|offer|"
                   r"provide|install|repair|deliver|lend|fund|help)|from £?\d|(per|a) month|rates? from|"
                   r"free (quote|consultation|valuation|survey))\b", re.I)
PRICE = re.compile(r"(?:[£$€₹]|\b(?:usd|gbp|eur|aed|inr|cad|aud)\s?)\d[\d,.]*", re.I)
CTA_WORDS = re.compile(r"\b(start (your|now|today|a free trial)|get started|order (now|today)|book (now|online|a "
                       r"(demo|call|consultation|survey|visit))|buy now|sign up|apply (now|online|today)|get (your|a|an) "
                       r"(quote|visa|e-?visa|loan|offer|estimate|valuation|price)|check (eligibility|prices?|availability)|"
                       r"request (a|your)|start your|(start|try) (it )?free|free trial|talk to (us|an?|our)|"
                       r"speak to (us|an?|our)|enquire( now)?|get in touch|contact (us|our team)|call ?back|"
                       r"shop (now|the)|see (prices|plans|pricing)|compare (plans|deals|quotes))\b", re.I)
CTA_WORDS = re.compile(CTA_WORDS.pattern + r"|\b(add to (cart|basket|bag)|browse (the |our )?(range|products|collection)|"
                       r"view (the |our )?(range|products|collection)|explore (the |our )?(range|products|collection))\b", re.I)
CART = re.compile(r"\b(add to (cart|basket|bag)|in stock|out of stock|sku|£\s?\d+(\.\d\d)?\s*(inc|ex)\.? vat|"
                  r"buy now|quantity)\b", re.I)
# a byline or reading time is a post; "last updated" alone is not (service pages in regulated fields show one)
BLOG_FURNITURE = re.compile(r"\b(\d+\s*min(ute)?s? read|posted (on|by)|published (on|by)|written by|by [A-Z][a-z]+ "
                            r"[A-Z][a-z]+|share this (post|article))\b")
QUESTION_H1 = re.compile(r"^(how|what|why|when|which|who|can|should|is|are|do|does|will)\b", re.I)
PLACE_WORDS = re.compile(r"\b(in|near|across)\s+[A-Z][a-z]+", re.M)


def _slug_words(url: str) -> list[str]:
    seg = [x for x in urlparse(url).path.split("/") if x]
    return re.sub(r"[-_]+", " ", seg[-1]).lower().split() if seg else []


# path segments that name a section of a site, not a topic
SECTION_WORDS = {"blog", "blogs", "news", "guide", "guides", "insight", "insights", "article", "articles", "learn",
                 "resources", "resource", "help", "hub", "products", "product", "p", "item", "shop", "collections",
                 "collection", "category", "categories", "services", "service", "en", "gb", "us", "uk", "pages",
                 "page", "c", "s", "info", "tools", "tool", "landing", "lp", "www"}


def _path_segments(url: str) -> list[list[str]]:
    segs = [x for x in urlparse(url).path.split("/") if x]
    out = []
    for x in segs:
        ws = [w for w in re.sub(r"[-_.]+", " ", x).lower().split()
              if not re.fullmatch(r"\d+|html?|php|aspx?|index", w)]
        if ws and not (len(ws) == 1 and ws[0] in SECTION_WORDS):
            out.append(ws)
    return out


def _match_set(text: str) -> set:
    """Words and places of a text: "UK" and "united kingdom" meet as the same place."""
    from .nlp import places
    ws = {w[:5] for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1}
    return ws | places(text)


# headings that greet or label the site instead of naming the page's subject
GENERIC_H1 = re.compile(r"(?i)^(welcome( to)?|home( page)?|hello|hi there|about( us)?|our story|menu|search)\b")
PADDING = re.compile(r"\b(your |the |a |an )?(complete|ultimate|definitive|full|quick|simple|beginner'?s?|expert)?\s*"
                     r"(guide|explained|overview|tips|faqs?|checklist)( for \d{4}| \d{4})?\s*$", re.I)


def keyword_from(h1: str, title: str, url: str) -> str:
    """The page's main keyword, from what the page says it is about.

    The H1's head phrase (before ":", "|", " - "), or else the title's, when it agrees with the address: it shares
    a word or a place with ANY path segment (a hub page's leaf is often only an entity: /visa-status-check/
    united-kingdom is headed "UK Visa Status Check"). Without the site's name and padding ("your complete guide").
    When neither agrees, the address itself, with the parent section's words added when the leaf alone is a name
    of two words or fewer ("visa status check united kingdom", not "united kingdom")."""
    slug = _slug_words(url)
    slug = [w for w in slug if not re.fullmatch(r"\d+|html?|php|aspx?|index", w)]
    brand = (urlparse(url).netloc.lower().removeprefix("www.").split(".")[0])
    segs = _path_segments(url)
    path_set = _match_set(" ".join(w for sg in segs for w in sg))

    def clean(s):
        s = re.sub(rf"\b{re.escape(brand)}\b", " ", s.lower()) if brand else s.lower()
        s = re.sub(r"[^\w£%' ]+", " ", s)
        prev = None
        while prev != s:
            prev, s = s, PADDING.sub("", " ".join(s.split())).strip()
        return " ".join(s.split())
    # the title part that names the page, not the site: "Acme Plumbing | Emergency plumber London" -> the second
    parts = [x for x in re.split(r"\s[|–—-]\s", title or "") if x.strip()]
    named = [x for x in parts if brand and brand not in re.sub(r"[^a-z0-9]", "", x.lower())] or parts[:1]
    heads = []
    for cand in ("" if GENERIC_H1.match((h1 or "").strip()) else h1 or "", named[0] if named else ""):
        head = clean(re.split(r"\s*[:|–—]\s*|\s+-\s+", cand.strip())[0])
        if head and len(head.split()) <= 10 and head.replace(" ", "") != brand:
            heads.append(head)
    for head in heads:
        if not segs or _match_set(head) & path_set:
            return head
    if len(heads) == 2 and _match_set(heads[0]) & _match_set(heads[1]) and not segs:
        return heads[0]
    leaf = clean(" ".join(slug))
    if segs and len(segs) >= 2 and len(leaf.split()) <= 2:
        parent = clean(" ".join(segs[-2]))
        if parent and parent != leaf:
            return f"{parent} {leaf}"
    return leaf


def brand_names(url: str, title: str = "") -> list[str]:
    """The site's name as the page writes it: the domain's root and title parts that spell it ("Master Fast Visas",
    "MasterFastVisas" for masterfastvisas.com)."""
    root = urlparse(url if "//" in url else "https://" + url).netloc.lower().removeprefix("www.").split(".")[0]
    names = {root}
    for part in re.split(r"\s[|–—-]\s", title or ""):
        if re.sub(r"[^a-z0-9]", "", part.lower()) == root:
            names.add(part.strip())
    return sorted(n for n in names if len(n) > 2)


def commerce(text: str, url: str, title: str = "") -> dict:
    """What a page or site does commercially: prices in any currency, calls to action, and the brand offering
    something in its own name ("Apply for your UK visa with MasterFastVisas", "filed by our team")."""
    brands = brand_names(url, title)
    flat = re.sub(r"\s+", " ", text)
    own = 0
    for b in brands:
        bb = re.escape(b)
        own += len(re.findall(rf"(?i)\b(with|from|by|at|choose|contact)\s+{bb}\b|\b{bb}\s+(can|will|offers?|provides?|"
                              rf"helps?|handles?|files?|processes|arranges?|delivers?)\b", flat))
    own += len(re.findall(r"(?i)\b(our (team|experts?|service|specialists?|advisers?|agents?)|we (file|handle|process|"
                          r"arrange|offer|provide|deliver|install|repair|lend|fund|help you))\b", flat))
    return {"prices": len(PRICE.findall(flat)), "ctas": len(CTA_WORDS.findall(flat)), "own_offer": own,
            "offers": len(OFFER.findall(flat[:8000]))}


SAID_TYPE = [("tool", r"\b(calculator|converter|checker|estimator|tool) page\b"),
             ("product-guide", r"\b(product|buying|buyer'?s?) guide\b"),
             ("hub", r"\b(hub|pillar) page\b"),
             ("spoke", r"\bspoke page\b"),
             ("location", r"\b(location|local|city|area) (landing )?page\b"),
             ("service", r"\b(service|landing|sales|money|conversion) page\b|\bservices? page\b"),
             ("product", r"\bproduct (page|listing|description)\b|\bpdp\b"),
             ("category", r"\b(category|collection|range|plp) page\b"),
             ("home", r"\bhome ?page\b"),
             ("company", r"\babout( us)? page\b|\bcompany page\b"),
             ("guide", r"\b(blog post|blog article|article|guide|how-?to|explainer|informational page)\b")]
COMMERCIAL_Q = re.compile(r"\b(services?|agenc(y|ies)|compan(y|ies)|providers?|specialists?|consultants?|brokers?|"
                          r"near me|hire|for hire|cost|costs|price|prices|pricing|quote|quotes|buy|for sale|order|"
                          r"shop|deals?|apply for|application service|online application|book|booking|installers?|"
                          r"repairs?|fitting|delivery|rental|subscription|software|app|tool|platform|"
                          # trades and professions people hire
                          r"plumbers?|electricians?|builders?|roofers?|locksmiths?|solicitors?|lawyers?|attorneys?|"
                          r"accountants?|dentists?|clinics?|architects?|designers?|developers?|cleaners?|cleaning|"
                          r"removals?|movers?|mechanics?|garages?|tutors?|photographers?|caterers?|vets?|agents?|"
                          # products people take out or buy into
                          r"loans?|mortgages?|insurance|isas?|pensions?|credit cards?|savings accounts?|"
                          r"current accounts?|bonds?|bridging|finance|leasing|hosting|courses?|visas?|e-?visas?)\b", re.I)


def explicit_type(request: str) -> str | None:
    """Only operator instructions establish an explicit type; query words are intent signals."""
    typed = re.search(r"\bpage[_ -]type\s*[:=]\s*(product-guide|service|product|category|location|home|company|guide|hub|spoke|tool)\b",
                      request or "", re.I)
    if typed:
        return typed.group(1).lower()
    for t, rx in SAID_TYPE:
        for m in re.finditer(rx, request or "", re.I):
            if not re.search(r"\b(not|no|avoid|without)\s+(?:a |an |another )?$", (request or "")[:m.start()], re.I):
                return t
    return None


def infer_type(request: str, keyword: str) -> tuple[str, str]:
    """Page type for a keyword request (no page address): what the operator says, else the keyword's intent.
    (type, why)."""
    said = explicit_type(request)
    if said:
        return said, f"the request says so ({said})"
    if TOOL_WORDS.search(keyword or "") and not QUESTION_H1.match(keyword or ""):
        return "tool", f"the query asks for a tool ({TOOL_WORDS.search(keyword).group(0)})"
    if QUESTION_H1.match(keyword or "") or re.search(r"\b(how|what|why|when|which|guide|tips|ideas|vs|versus)\b",
                                                     keyword or "", re.I):
        return "guide", "an informational query (a question, guide or comparison)"
    if re.search(r"\b(near me|nearby)\b", keyword or "", re.I):
        return "location", "a local search for a provider"
    if re.search(r"\b(costs?|prices?|fees?|requirements?|status|eligibility|reviews?|benefits?)\b", keyword or "", re.I):
        return "guide", "a task or information query; needs page and relevant offer evidence before changing its type"
    if COMMERCIAL_Q.search(keyword or ""):
        return "service", f"a commercial query ({COMMERCIAL_Q.search(keyword).group(0)})"
    return "guide", "no commercial wording in the query"


def classify(url: str, doc: dict | None, html: str = "", site: dict | None = None) -> tuple[str, list[str]]:
    """(page_type, evidence). `site` is commerce() of the home page: a page outside the blog on a site that sells
    something, carrying the brand's own offer, is a service (or product) page even when it explains a lot."""
    path = urlparse(url).path or "/"
    ev, score = [], {t: 0 for t in TYPES}
    text = " ".join(x for _, x in (doc or {}).get("blocks", []))[:20000]
    h1 = next((x for t, x in (doc or {}).get("blocks", []) if t == "h1"), "")
    title = (doc or {}).get("title") or ""
    com = commerce(text, url, title) if doc else {"prices": 0, "ctas": 0, "own_offer": 0, "offers": 0}
    selling_site = bool(site) and (site["prices"] + site["ctas"] + site["own_offer"] + site["offers"] >= 3)
    in_blog = bool(BLOG_PATH.search(path))
    if com["own_offer"]:
        score["service"] += 2 + min(4, com["own_offer"])
        ev.append(f"the brand offers something in its own name on the page ({com['own_offer']}x: 'with <brand>', 'our team'…)")
    if com["prices"] >= 2:
        score["service"] += 2
        ev.append(f"prices on the page ({com['prices']})")
    if com["ctas"]:
        score["service"] += min(3, com["ctas"])
        ev.append(f"calls to action ({com['ctas']}: start, apply, book, order…)")
    if selling_site and not in_blog and path not in ("", "/"):
        score["service"] += 3
        ev.append("a selling site (prices, calls to action or its own offer on the home page) and a page outside its blog")
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
    if path.count("/") <= 2 and not BLOG_PATH.search(path) and path not in ("", "/") and (selling_site or com["own_offer"]):
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
        score["guide"] += 3 if (in_blog or not selling_site) else 1
        ev.append("blog furniture (a byline or reading time)")
    if h1 and QUESTION_H1.match(h1):
        score["guide"] += 3
        ev.append("the H1 is a question")
    slug = " ".join(_slug_words(url))
    if re.search(r"\b(guide|how to|what is|tips|ideas|explained|vs|versus|checklist|faq|questions)\b", slug + " " + h1.lower()):
        score["guide"] += 3
        ev.append("informational wording in the address or H1 (guide, how to, what is…)")
    if score["service"] and PLACE_WORDS.search(h1 or "") and not QUESTION_H1.match(h1 or "") and not in_blog:
        score["location"] += score["service"] + 1
        ev.append("a service with a place in its H1")
    if doc is None:
        ev.append("the page doesn't exist yet: decided from its address only")
        if not any(score.values()):
            score["guide"] = 1
    if not any(score.values()):  # nothing points anywhere: an information page is the safe reading
        score["guide"] = 1
        ev.append("no commercial, product or blog signals: read as an information page")
    if path in ("", "/"):
        score["home"] = max(score["home"], max(score.values()) + 1)  # the root is the home page, offers and all
    if in_blog and score["product"] < 5:
        # the blog section outranks the banners and buttons the site repeats on every page
        score["guide"] = max(score["guide"], score["service"] + 1)
    # A tool page (a calculator, converter, checker…): its H1 or title names the tool and the page has the inputs
    # to use it. Its example results look like prices and its form like an enquiry form, so it is decided before
    # the commercial signals are weighed (a compound interest calculator was once read as a service page).
    inputs = len(re.findall(r"<input\b[^>]*type=[\"']?(number|range|text|date)|<select\b", html or "", re.I))
    if TOOL_WORDS.search(f"{h1} {title} {slug}") and (inputs >= 2 or not html) and not QUESTION_H1.match(h1 or ""):
        ev.append(f"a tool page: \"{TOOL_WORDS.search(f'{h1} {title} {slug}').group(0)}\" in its H1, title or "
                  f"address and {inputs} input(s) on the page")
        return "tool", ev
    # Navigation and shared banners supply commercial signals on every shop page.
    # Specific page evidence takes precedence over those generic signals.
    if path not in ("", "/") and not in_blog:
        if COMPANY_PATH.search(path):
            return "company", ev
        if CATEGORY_PATH.search(path):
            return "category", ev
        if PRODUCT_PATH.search(path) or re.search(r'"@type"\s*:\s*"Product"', html):
            return "product", ev
    best = max(TYPES, key=lambda t: (score[t], -TYPES.index(t)))
    return best, ev


def intake(url: str) -> dict:
    """Read a page and decide its type and main keyword. {page_url, exists, page_type, target_query, h1, title,
    evidence}."""
    url = C.clean_url(url if url.startswith("http") else "https://" + url)
    home = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    pages = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "raw"} for u in dict.fromkeys([url, home])]))
    for address, raw_page in list(pages.items()):
        markup = raw_page.get("raw") or ""
        if not markup:
            continue
        parsed = {**raw_page, **C.parse_doc(markup)}
        pages[address] = parsed
        if parsed.get("status") == 200 and parsed.get("state") == "ok":
            if parsed.get("words", 0) < 80:
                parsed["state"] = "needs_js"
            C.cache_put(C._fetch_key("doc", address), parsed)
            C.cache_put(C._fetch_key("html", address),
                        {**parsed, **C.parse_html(markup, parsed.get("final_url") or address)})
    res = pages.get(url) or {}
    html = res.get("raw") or ""
    exists = res.get("status") == 200 and res.get("state") == "ok" and bool(res.get("text"))
    if res.get("status") == 200 and res.get("state") in ("ok", "needs_js") and (not exists or res.get("words", 0) < 80):
        from . import spider
        r = spider.scrape_many([url], timeout_s=20, attempts=1).get(url) or {}
        if r.get("state") == "ok":
            res, exists = r, True
            C.cache_put(C._fetch_key("doc", url), r)
    doc = res if exists else None
    h1 = next((x for t, x in (doc or {}).get("blocks", []) if t == "h1"), "") if doc else ""
    title = (doc or {}).get("title") or ""
    site = None
    if doc and home.rstrip("/") != url.rstrip("/"):
        hr = pages.get(home) or {}
        if hr.get("state") == "ok":
            site = commerce(" ".join(x for _, x in hr.get("blocks", [])), home, hr.get("title") or "")
    final = C.clean_url(res.get("final_url") or url) if exists else url  # a redirect: judge the page it lands on
    ptype, ev = classify(final, doc, html, site)
    kw = keyword_from(h1, title, final)
    from .market import from_page
    locale, mev = from_page(url, html)
    return {"page_url": C.clean_url(res.get("final_url") or url) if exists else url, "exists": exists,
            "status": res.get("status"), "read_state": res.get("state") or "unreadable",
            "page_type": ptype, "target_query": kw, "h1": h1, "title": title, "evidence": ev,
            "locale": locale, "locale_evidence": mev}
