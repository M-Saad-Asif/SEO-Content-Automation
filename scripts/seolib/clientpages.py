"""The client's own site as a source: which of its pages to link, what it says about itself, what it already
publishes on this topic. Niche-free: everything is decided from URLs, the query's words and the page text.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from . import common as C
from .nlp import tokens

# URL paths that are never content: tests, tools, accounts, carts, feeds, legal boilerplate
JUNK = re.compile(r"(test|dummy|staging|preview|sample|data-entry|split-url|tmp|temp|draft|sandbox|/cart|/checkout|"
                  r"deal-of-the-day|deals?/|/offers?/|/sale/|voucher|promo|discount-code|competition|giveaway|"
                  r"/account|/login|/register|/search|/wishlist|/feed|/rss|/tag/|/author/|/page/\d|\.xml$|\.json$)", re.I)
LOCALE_SEG = re.compile(r"^([a-z]{2})([-_][a-z]{2})?$", re.I)
COMMERCIAL = re.compile(r"/(collections?|products?|shop|store|services?|pricing|plans|book|booking|categories?|c|p|dp|item)/|"
                        r"/p[a-z]{0,2}\d{3,}/|"  # a product id as the last segment: Toolstation's /…-drain-unblocker/pAJ964
                        r"(calculator|quiz|checker|finder|planner|estimator|tool|quote|booking|book-a|sign-up)", re.I)


def _same_word(a: str, b: str) -> bool:
    """One word, another form of it: "unblock" and "unblocker", "drain" and "drains" (4+ letters shared at the start)."""
    return a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))


def _shared(q: set[str], s: set[str]) -> set[str]:
    return {w for w in q if any(_same_word(w, x) for x in s)}
STOP = {"how", "to", "what", "is", "the", "a", "an", "my", "your", "for", "of", "in", "on", "do", "i", "can", "you",
        "are", "with", "and", "or", "be", "does", "should", "much", "many", "best", "when", "why", "which", "it", "get"}


def locale_ok(url: str, locale: str) -> bool:
    """Keep pages in the brief's language and region: drop /da-dk/, /de/ etc. when the page is en-GB."""
    segs = [s for s in urlparse(url).path.split("/") if s]
    if not segs:
        return True
    first = segs[0].lower()
    region = (locale.split("-") + [""])[1].lower()
    # bare region folders (/uk/, /us/, /eu/, /au/ …) must match the page's region
    if first in ("uk", "gb", "us", "eu", "au", "ca", "nz", "ie", "in", "za", "sg", "int", "row", "intl"):
        return first == region or (first, region) in (("uk", "gb"), ("gb", "gb"))
    m = LOCALE_SEG.match(first)
    if not m:
        return True
    lang, reg = m.group(1).lower(), (m.group(2) or "")[1:].lower()
    want_lang, _, want_reg = locale.lower().partition("-")
    if lang != want_lang:
        return False
    return not reg or not want_reg or reg == want_reg or (reg, want_reg) in (("uk", "gb"), ("gb", "uk"))


def clean_internal(urls: list[str], locale: str) -> list[str]:
    return [u for u in urls if locale_ok(u, locale) and not JUNK.search(urlparse(u).path)]


def content(text: str, syn: dict | None = None) -> set[str]:
    return {w for w in tokens(text, syn) if w not in STOP and len(w) > 2 and not w.startswith("geo:")}


ID_SEG = re.compile(r"^(?:[a-z]{0,3}\d{3,}[a-z0-9]*|\d+)$", re.I)


def slug(url: str) -> str:
    """The URL's descriptive part: its last segment, or the one before when the last is an id
    ("/zep-drain-unblocker/p99444")."""
    segs = [s for s in urlparse(url).path.rstrip("/").split("/") if s]
    if len(segs) >= 2 and ID_SEG.match(segs[-1]):
        return segs[-2]
    return segs[-1] if segs else ""


def slug_words(url: str, syn: dict | None = None) -> set[str]:
    return content(re.sub(r"[-_]+", " ", slug(url)), syn)


def template_families(urls: list[str], syn: dict | None = None) -> set[str]:
    """Folders whose pages repeat one template with a single changing word ("tyres-exeter", "tyres-leeds"; one page per
    town or per model). They are location or catalogue pages, not guides."""
    by_dir = {}
    for u in urls:
        by_dir.setdefault(urlparse(u).path.rstrip("/").rsplit("/", 1)[0], []).append(u)
    fams = set()
    for d, us in by_dir.items():
        if len(us) < 8:
            continue
        slugs = [re.findall(r"[a-z]+", urlparse(u).path.rstrip("/").rsplit("/", 1)[-1].lower()) for u in us]
        cnt = {}
        for s in slugs:
            for w in set(s):
                cnt[w] = cnt.get(w, 0) + 1
        shared = {w for w, c in cnt.items() if c >= 0.6 * len(us)}
        short = sum(1 for s in slugs if len(set(s) - shared) <= 2)
        if short >= 0.7 * len(us) and (shared or sum(1 for s in slugs if len(s) <= 2) >= 0.7 * len(us)):
            fams.add(d)
    return fams


TASK_VERBS = {"make", "do", "get", "use", "choose", "find", "check", "build", "create", "start", "fix", "clean", "plan",
              "work", "know", "tell", "need", "set", "pick", "buy", "learn"}


def related(urls: list[str], query: str, syn: dict | None = None, exclude: str = "") -> dict:
    """Score the client's pages against the query: same-topic pages (possible cannibalisation), related guides,
    and commercial pages (the natural next step)."""
    from .nlp import prime, _rule_lemma
    q = content(query, syn) - TASK_VERBS or content(query, syn)
    raw_slug = {u: re.sub(r"[-_]+", " ", slug(u)).lower() for u in urls}
    # words most of the site's URLs share ("dog" on a dog-food site) say nothing about relevance; counted with the
    # cheap rule lemmas over every URL, so the tagger only runs on slugs that can match the query at all
    df = {}
    for text in raw_slug.values():
        for w in {_rule_lemma(x) for x in re.findall(r"[a-z0-9]{3,}", text)}:
            df[w] = df.get(w, 0) + 1
    common = {w for w, c in df.items() if len(urls) >= 20 and c / len(urls) > 0.15}
    # a slug sharing no 4-letter stem with the query cannot share a lemma with it (the match needs `specific`)
    stems = {w[:4] for w in q | set(re.findall(r"[a-z]{3,}", (query or "").lower()))}
    for k, v in (syn or {}).items():
        stems |= {w[:4] for w in re.findall(r"[a-z]{3,}", f"{k} {v}".lower())}
    cand = [u for u in urls if any(x[:4] in stems for x in re.findall(r"[a-z0-9]{3,}", raw_slug[u]))]
    prime([query] + [raw_slug[u] for u in cand], syn)
    slugs = {u: slug_words(u, syn) for u in cand}
    qs = q - common or q
    same, guides, commercial = [], [], []
    # a query word rare on this site says more than a common one: "unblock" (a few drain unblockers) over "sink"
    # (hundreds of sinks, sink heaters and taps), so pages rank by the rarity of the words they share
    dfq = {w: max(1, sum(1 for s in slugs.values() if any(_same_word(w, x) for x in s))) for w in q}
    weight = lambda s: sum(1 / dfq[w] for w in _shared(q, s))
    fams = template_families(urls, syn)
    ex_path = urlparse(exclude).path.rstrip("/")
    for u, s in slugs.items():
        if u.rstrip("/") == exclude.rstrip("/") or urlparse(u).path.rstrip("/") == ex_path or not s or not q:
            continue
        if urlparse(u).path.rstrip("/").rsplit("/", 1)[0] in fams and not COMMERCIAL.search(urlparse(u).path + "/"):
            continue
        hit = len(_shared(q, s)) / len(q)
        specific = _shared(qs, s)  # matches on the query's distinctive words, in any form ("unblocker")
        if COMMERCIAL.search(urlparse(u).path + "/"):
            if specific:
                commercial.append((hit + weight(s), u))
        elif (hit >= 0.75 and len(s - q) <= 1 and specific) or (s <= q and len(s) >= max(1, len(q) - 1) and specific):
            same.append((hit, u))
        elif specific and len(specific) / len(qs) >= 0.5:
            guides.append((hit + weight(s), u))
    pick = lambda xs, n: [u for _, u in sorted(xs, key=lambda x: -x[0])[:n]]
    pool = pick(commercial + guides, 60)  # the plan re-ranks these by the topic's entities (plan.py, step 5)
    top = max((x for x, _ in commercial), default=0)
    commercial = [(x, u) for x, u in commercial if x >= 0.6 * top]  # only the pages close to the best match
    return {"same_topic": pick(same, 3), "guides": pick(guides, 8), "commercial": pick(commercial, 6),
            "candidates": pool}


PROMO = re.compile(r"(\bsave\b|% off|\boff\b.*\bprice|free (delivery|shipping)|sign up|subscribe|newsletter|cookie|"
                   r"terms and conditions|registered in|company (no|number)|©|all rights reserved|shop now|buy now|"
                   r"apply now|enrol|limited time|discount|voucher|promo code)", re.I)


def site_says(home: dict) -> list[str]:
    """What the client publicly says it is and does: its homepage title and meta description, minus promotions."""
    import html as _html
    out = []
    for i, t in enumerate((home.get("meta_description"), home.get("title"))):
        t = _html.unescape(t or "").strip()
        if i == 1 and re.search(r"\s[|–—-]\s", t):  # "Fresh Dog Food Delivery | Brand" is a page title, not a claim
            continue
        if re.search(r"\b(no\.? ?1|number one|#1|best|leading|biggest|largest|top[- ]rated|award[- ]winning|"
                     r"cheapest|favourite|favorite)\b", t, re.I):
            continue  # a superlative the page can't verify (RULES 1.12)
        if 20 <= len(t) <= 300 and not PROMO.search(t):
            out.append(t)
    return list(dict.fromkeys(out))


META_TALK = re.compile(r"\b(in (the following|this) (guide|article|post|blog)|we('ll| will) (answer|look|explain|cover)|"
                       r"read on|below|above|this (guide|article|post))\b", re.I)


def client_passages(pages: dict, query: str, syn: dict | None = None, per_page: int = 4,
                    rich: tuple = ()) -> list[dict]:
    """Short passages from the client's own related guides: first-hand client advice the writer may use. The
    client's existing page on the same query (`rich`) is the page this one replaces: take more from it, and keep
    its figures (prices, durations), which the new page must not lose."""
    q = content(query, syn)
    out = []
    from .lint import _has_finite, sentences
    for url, page in pages.items():
        blocks = page.get("blocks") or []
        kept = 0
        per_page = 12 if url in rich else per_page
        for t, x in blocks:
            if t not in ("p", "li") or kept >= per_page:
                continue
            for s in sentences(x):
                n = len(s.split())
                # breadcrumbs, headings and questions are not passages: a full sentence with a verb, ending in a stop
                if not re.search(r"[.!]$", s.strip()) or s.strip().endswith("?") or not _has_finite(s):
                    continue
                if META_TALK.search(s) or re.search(r"(^|\s|\()_[a-z]+_?[a-z_]*|\{\{|\}\}|\[\[|%[a-z_]+%", s):
                    continue
                need = 1 if url in rich and re.search(r"\d", s) else min(len(q), max(2, len(q) // 2))
                if 8 <= n <= 40 and not PROMO.search(s) and len(content(s, syn) & q) >= need:
                    out.append({"url": url, "title": page.get("title") or "", "text": s})
                    kept += 1
                    if kept >= per_page:
                        break
    return out


MOJIBAKE = re.compile(r"Ã.|Â|â€")


def fix_text(s: str) -> str:
    """Repair UTF-8 read as Latin-1 ("again! Â", "donâ€™t")."""
    if s and MOJIBAKE.search(s):
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return MOJIBAKE.sub("", s)
    return s


PLACEHOLDER = re.compile(r"\b(dummy|test|sample|placeholder|do not (buy|use)|none)\b", re.I)


MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}


def _past(name: str) -> bool:
    """A dated product (a course, an event) whose date has gone."""
    from datetime import date
    today = date.today()
    for d, mon, yr in re.findall(r"(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?(january|february|march|april|may|june|july|august|"
                                 r"september|october|november|december)\s+(20\d\d)", name.lower()):
        try:
            when = date(int(yr), MONTHS[mon], int(d) if d else 28)
        except ValueError:
            continue
        if when < today:
            return True
    return False


def relevant_products(products: list[dict], query: str, syn: dict | None = None, cap: int = 15,
                      chosen: bool = False) -> list[dict]:
    """Products worth listing for this page: no placeholders, and sharing words with the query when there are many.
    Collections the brief names were chosen by the operator: keep them all (up to 60)."""
    if chosen:
        cap = 60
    good = [p for p in products if not PLACEHOLDER.search(p.get("display_name") or "") and not _past(p.get("display_name") or "")]
    for p in good:
        p["display_name"] = re.sub(r"\s*[-–|:]?\s*[£$€]\s?\d[\d,]*(\.\d\d)?\b", "", fix_text(p["display_name"])).strip()
        p["description"] = fix_text(p.get("description") or "")
    # in-stock products first; drop sold-out ones when enough others can be bought
    if sum(1 for p in good if p.get("in_stock") is not False) >= 3:
        good = [p for p in good if p.get("in_stock") is not False]
    if len(good) <= cap:
        return good
    q = content(query, syn)

    def words_of(p):
        return content(" ".join([p.get("display_name") or "", p.get("product_type") or "",
                                 (p.get("description") or "")[:300]]), syn)
    scored = sorted(good, key=lambda p: -len(q & words_of(p)))
    return [p for p in scored if q & words_of(p)][:cap]
