"""Competitor scrape: outlines and main content of what already ranks."""
import re
import statistics

from seolib import common as C
from seolib.domains import domain, kind

SKIP_KINDS = {"video", "app_store", "image"}


def _shingles(blocks, n=6):
    import re
    ws = re.findall(r"[a-z0-9']+", " ".join(x for t, x in blocks if t in ("p", "li")).lower())
    return {" ".join(ws[i:i + n]) for i in range(0, max(0, len(ws) - n + 1), 2)}


FUNCTION_WORDS = {
    "en": {"the", "and", "of", "to", "a", "in", "is", "for", "that", "you", "it", "with", "on", "are", "your", "can",
           "or", "be", "as", "this", "an", "by", "if", "not", "from", "at", "will", "have", "more", "how", "what"},
}


def other_language(blocks, locale: str) -> bool:
    """A ranking page in another language (a German page in an en-US SERP) teaches nothing about this reader's
    page. Checked by how often the locale's commonest function words appear; languages without a list pass."""
    words_ = FUNCTION_WORDS.get((locale or "en").split("-")[0].lower())
    if not words_:
        return False
    toks = [w for _, x in blocks for w in re.findall(r"[a-zà-ÿ']+", x.lower())][:800]
    return len(toks) >= 80 and sum(w in words_ for w in toks) / len(toks) < 0.12


def clone_of(blocks, kept):
    """Scraper sites re-publish a ranking page word for word on another domain. A copy says nothing new about what
    readers expect and doubles one page's weight in every "shared by N pages" count."""
    sh = _shingles(blocks)
    if len(sh) < 40:
        return None
    for p in kept:
        other = p.get("_sh") or set()
        if other and len(sh & other) / min(len(sh), len(other)) > 0.5:
            return p["url"]
    return None


def run(ctx):
    serp = ctx.load("serp_intel")
    if not serp or serp.get("error"):
        return {"error": "no SERP data"}
    client = ctx.brief["domain"].replace("https://", "").replace("www.", "").strip("/")
    n = 10 if ctx.deep() else 5
    targets, skipped = [], []
    for o in serp.get("organic", []):
        if domain(o["link"]).endswith(client):
            skipped.append({"url": o["link"], "why": "client's own page"})
        elif o["kind"] in SKIP_KINDS or o["link"].lower().endswith(".pdf"):
            skipped.append({"url": o["link"], "why": f"{o['kind']} result (no article text)"})
        else:
            targets.append(o)
    # Fetch every eligible result in parallel and keep the first n that are readable, in ranking order.
    from seolib import spider
    rendered = spider.scrape_many([o["link"] for o in targets]) if spider.api_key() else {}
    need = [o for o in targets if (rendered.get(o["link"]) or {}).get("state") != "ok"]
    res = C.run_async(C.fetch_many([{"url": o["link"], "kind": "page", "parse": "doc"} for o in need],
                                   ctx.refresh, timeout=8, attempts=1)) if need else {}
    res.update({u: r for u, r in rendered.items() if r.get("state") == "ok"})
    pages = []
    for o in targets:
        r = res.get(o["link"]) or {}
        if r.get("state") != "ok":
            skipped.append({"url": o["link"], "why": f"{r.get('state') or 'error'} ({r.get('status')})"})
            continue
        if len(pages) >= n:
            continue
        blocks = r.get("blocks", [])
        if other_language(blocks, ctx.brief.get("locale") or "en-GB"):
            skipped.append({"url": o["link"], "why": "written in another language than the page's locale"})
            continue
        dup = clone_of(blocks, pages)
        if dup:
            skipped.append({"url": o["link"], "why": f"copy of {dup} (scraped clone)"})
            continue
        outline = [[int(t[1]), x] for t, x in blocks if t in ("h1", "h2", "h3", "h4")]
        pages.append({"position": o["position"], "url": o["link"], "domain": o["domain"], "kind": o["kind"],
                      "title": r.get("title") or o.get("title"), "outline": outline, "words": r.get("words", 0),
                      "tables": r.get("tables", 0), "blocks": blocks, "_sh": _shingles(blocks),
                      "via": r.get("via") or "direct"})
    # Too few readable pages to learn from (blocked sites, scripts-only pages): read more pages that rank for the
    # same intent, from the near-identical searches serp_intel already ran and from Google's PAA answer sources.
    want = 6 if ctx.deep() else 3
    if len(pages) < want:
        seen = {o["link"] for o in serp.get("organic", [])} | {s["url"] for s in skipped}
        extra = []
        for x in serp.get("expansions", {}).values():
            extra += [u for u in x.get("organic", []) if u]
        extra += [a.get("link") for a in (serp.get("paa_answers") or {}).values() if a.get("link")]
        extra = [u for u in dict.fromkeys(extra) if u not in seen and not domain(u).endswith(client)
                 and kind(u) not in SKIP_KINDS and not u.lower().endswith(".pdf")
                 and domain(u) not in {p["domain"] for p in pages}][:12]
        more = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in extra],
                                        ctx.refresh, timeout=8, attempts=1)) if extra else {}
        for u in extra:
            r = more.get(u) or {}
            if r.get("state") != "ok" or len(pages) >= want + 2 or domain(u) in {p["domain"] for p in pages}:
                continue
            blocks = r.get("blocks", [])
            if clone_of(blocks, pages) or other_language(blocks, ctx.brief.get("locale") or "en-GB"):
                continue
            pages.append({"position": None, "url": u, "domain": domain(u), "kind": kind(u),
                          "title": r.get("title"), "outline": [[int(t[1]), x] for t, x in blocks if t in ("h1", "h2", "h3", "h4")],
                          "words": r.get("words", 0), "tables": r.get("tables", 0), "blocks": blocks, "backfill": True})
    for p in pages:
        p.pop("_sh", None)
    words = [p["words"] for p in pages if p["words"]]
    return {"pages": pages, "skipped": skipped,
            "median_words": int(statistics.median(words)) if words else None,
            "summary": f"{len(pages)} pages read, {len(skipped)} skipped, median {int(statistics.median(words)) if words else 0} words"}
