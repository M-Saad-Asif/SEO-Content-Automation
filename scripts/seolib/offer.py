"""What the client sells, from its own pages: the offer a commercial page exists to make.

A service, product, category, location or home page answers the searcher AND sells the client's offer. Without a
model of that offer the writer only has third-party facts (official guidance, competitors), and a visa agency's
page turns into a government guide that sends readers elsewhere. This module reads the client's own pages (the page
being rewritten, its home page, and its pages on the same topic) and returns:

- offers: sentences in which the brand states what it does or charges ("A priority e-visa filed by our team",
  "Apply for your UK visa with MasterFastVisas"), verbatim, with the page they are on. They are client claims the
  copy may use, because the client publishes them itself.
- ctas: the calls to action the site uses on its own links (text and target), so the page ends in the client's
  real next step, not an invented one.
- role: "provider" (the client does the thing) or "intermediary" (it does it on the reader's behalf with an
  authority or another provider deciding, e.g. a visa or licence filing service). An intermediary owes the reader
  one honest disclosure, never a page of directions to the authority.

Niche-free: the patterns are the ways any business writes about itself (we/our/with <brand>/prices/calls to act).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from . import common as C
from .pagetype import CTA_WORDS, PRICE, brand_names

OWN = [r"\b(our (team|experts?|service|services|specialists?|advisers?|agents?|engineers?|staff|platform|app))\b",
       r"\bwe('ll| will| can)? (file|handle|process|arrange|offer|provide|deliver|install|repair|lend|fund|help|check|"
       r"submit|prepare|review|manage|take care|do)\b",
       r"\b(get|start|apply for|order|book) (your|a|an)\b.{0,60}\b(with|from|through) {brand}\b",
       r"\b{brand}\b.{0,40}\b(offers?|provides?|helps?|handles?|files?|processes|arranges?|delivers?|can|will)\b",
       r"\b(with|from|through|choose|by) {brand}\b"]
SPEED = re.compile(r"\b(in|within|under|as little as)\s+\d+\s*(hours?|days?|working days|minutes?)\b", re.I)
JUNK = re.compile(r"(cookie|privacy|terms|©|all rights reserved|sign in|log ?in|newsletter|subscribe|follow us)", re.I)


def _sentences(text: str) -> list[str]:
    """Sentences of the page's own blocks: a line break ends a block (menus and buttons are lines of their own)."""
    from .graph import sentences
    out = []
    for line in re.split(r"\n+", text or ""):
        out += [s for s in sentences(line) if 4 <= len(s.split()) <= 45 and not JUNK.search(s)]
    return out


def _intermediary(text: str, brands: list[str]) -> bool:
    """The client acts for the reader before someone else who decides: "filed by our team", "we submit your
    application", "the decision is made by…", "not affiliated with…"."""
    return bool(re.search(r"(?i)\b(on your behalf|we (submit|file|lodge)|filed by our team|submitted (by|on)|"
                          r"not affiliated|independent (service|agency|company)|third[- ]party (service|agency)|"
                          r"decision (is|will be) made by)\b", text))


def offer_profile(client: str, domain: str, pages: list[str], title_hint: str = "", banned: list[str] | None = None,
                  refresh: bool = False, target_query: str = "", page_url: str = "") -> dict:
    """Read the client's own pages (first = the page this run writes, when it exists) and model its offer."""
    home = f"https://{C.host('https://' + domain.removeprefix('https://').removeprefix('http://').strip('/'))}/"
    pages = [u for u in dict.fromkeys(pages) if u and C.host(u) == C.host(home)]
    if not pages:
        return {}
    brands = sorted(set(brand_names(home, title_hint) + [client]), key=len, reverse=True)
    bre = "(" + "|".join(re.escape(b) for b in brands if b) + ")"
    own = [re.compile(p.replace("{brand}", bre), re.I) for p in OWN]
    res = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "html"} for u in pages], refresh)) or {}
    banned_l = [b.lower() for b in banned or []]
    offers, ctas, seen, seen_cta, texts = [], [], set(), set(), []
    for rank, u in enumerate(pages):
        r = res.get(u) or {}
        if r.get("state") not in ("ok", "needs_js"):
            continue
        if C.host(r.get("final_url") or u) != C.host(home):
            continue  # a redirect to an unrelated organisation proves no client offer
        text = r.get("text") or ""
        texts.append(text)
        source_lines = [x.strip() for x in text.splitlines() if x.strip()]
        passages = [(s, " / ".join(source_lines[max(0, i - 2):i + 2])[:600])
                    for i, line in enumerate(source_lines) for s in _sentences(line)]
        for s, context in passages:
            key = re.sub(r"\W+", " ", s.lower()).strip()
            if key in seen or any(b in s.lower() for b in banned_l) or s.rstrip().endswith("?"):
                continue  # a question ("Why choose us?") states no offer
            hits = sum(1 for rx in own if rx.search(s)) + (1 if PRICE.search(s) else 0) + (1 if SPEED.search(s) else 0)
            if hits and (any(rx.search(s) for rx in own) or re.search(bre, s, re.I)):
                seen.add(key)
                offers.append({"text": s, "url": C.clean_url(r.get("final_url") or u), "score": hits * 2 - rank,
                               "this_page": bool(page_url) and C.clean_url(u).rstrip('/') == C.clean_url(page_url).rstrip('/'),
                               "scope": f"Client claim published on {u}; retain its product, route, country and conditions. "
                                        f"Source context: {context}"})
        base = r.get("final_url") or u
        for href, label in r.get("links") or []:
            label = (label or "").strip()
            if not label or len(label) > 60 or not CTA_WORDS.search(label):
                continue
            target = C.clean_url(urljoin(base, href))
            if urlparse(target).scheme not in ("tel", "mailto") and C.host(target) != C.host(home):
                continue  # a button to another site is not the client's offer
            k = (label.lower(), target.rstrip("/"))
            if k in seen_cta:
                continue
            seen_cta.add(k)
            ctas.append({"text": label, "url": target,
                         "this_page": bool(page_url) and C.clean_url(u).rstrip('/') == C.clean_url(page_url).rstrip('/')})
    offers.sort(key=lambda o: -o["score"])
    generic = re.compile(r"(?i)\b(contact|get in touch|talk to|speak to|enquire)\b")
    query_terms = set(re.findall(r"[a-z]{3,}", target_query.lower())) - {"the", "for", "and", "with"}
    ctas.sort(key=lambda c: (not c["this_page"], -len(query_terms & set(re.findall(r"[a-z]{3,}", (c["text"] + ' ' + c["url"]).lower()))),
                             bool(generic.search(c["text"])), c["url"].rstrip("/") == home.rstrip("/")))
    joined = " ".join(texts)
    return {"brands": brands, "offers": [{k: v for k, v in o.items() if k != "score"} for o in offers[:10]],
            "ctas": ctas[:8], "role": "intermediary" if _intermediary(joined, brands) else "unknown",
            "pages_read": [u for u in pages if (res.get(u) or {}).get("state") in ("ok", "needs_js")
                           and C.host((res.get(u) or {}).get("final_url") or u) == C.host(home)]}
