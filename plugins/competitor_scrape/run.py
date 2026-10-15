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
    client = C.host("https://" + ctx.brief["domain"].removeprefix("https://").removeprefix("http://"))
    n = 10 if ctx.deep() else 5
    targets, skipped = [], []
    for o in serp.get("organic", [])[:10]:
        if C.host(o["link"]) == client:
            skipped.append({"url": o["link"], "why": "client's own page"})
        elif o["kind"] in SKIP_KINDS or o["link"].lower().endswith(".pdf"):
            skipped.append({"url": o["link"], "why": f"{o['kind']} result (no article text)"})
        else:
            targets.append({**o, "source_role": "ranked"})
    for o in targets[n:]:
        skipped.append({"url": o["link"], "why": "quick-mode organic page limit"})
    targets = targets[:n]
    # Questions are search demand; only their actual source URLs can be scraped. Read selected PAA and
    # related-search sources in the same bounded wave even when all ten ranked pages are readable.
    seen = {o["link"] for o in targets} | {s["url"] for s in skipped}
    supplements = [(a.get("link"), "paa_source") for a in (serp.get("paa_answers") or {}).values() if a.get("link")]
    supplements += [(u, "related_search_source" if x.get("source") == "related" else "expanded_search_source")
                    for x in sorted((serp.get("expansions") or {}).values(), key=lambda x: x.get("source") != "related")
                    for u in x.get("organic", [])[:1] if u]
    counts, limits = {}, {"paa_source": 4 if ctx.deep() else 2, "related_search_source": 2 if ctx.deep() else 0,
                         "expanded_search_source": 2 if ctx.deep() else 0}
    for u, role in supplements:
        if u in seen:
            continue
        seen.add(u)
        if C.host(u) == client or kind(u) in SKIP_KINDS or u.lower().endswith(".pdf"):
            skipped.append({"url": u, "why": "supplement is own site or non-text source"})
            continue
        if counts.get(role, 0) >= limits[role] or (role != "paa_source" and
                sum(counts.get(r, 0) for r in ("related_search_source", "expanded_search_source")) >= limits[role]):
            skipped.append({"url": u, "why": "supplement source budget; query retained in article context"})
            continue
        counts[role] = counts.get(role, 0) + 1
        targets.append({"link": u, "position": None, "domain": domain(u), "kind": kind(u), "source_role": role})
    from seolib import spider
    rendered = spider.scrape_many([o["link"] for o in targets], concurrency=max(1, min(16, len(targets))), timeout_s=25,
                                 attempts=1, refresh=ctx.refresh) if spider.api_key() else {}
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
                      "via": r.get("via") or "direct", "final_url": r.get("final_url") or o["link"],
                      "source_role": o["source_role"]})
    # Too few readable pages to learn from (blocked sites, scripts-only pages): read more pages that rank for the
    # same intent, from the near-identical searches serp_intel already ran and from Google's PAA answer sources.
    want = 6 if ctx.deep() else 3
    backfill_requested = []
    if len(pages) < want:
        seen = {o["link"] for o in serp.get("organic", [])} | {s["url"] for s in skipped}
        extra = []
        for x in serp.get("expansions", {}).values():
            extra += [u for u in x.get("organic", []) if u]
        extra += [a.get("link") for a in (serp.get("paa_answers") or {}).values() if a.get("link")]
        extra = [u for u in dict.fromkeys(extra) if u not in seen and C.host(u) != client
                 and kind(u) not in SKIP_KINDS and not u.lower().endswith(".pdf")
                 and domain(u) not in {p["domain"] for p in pages}][:12]
        more = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in extra],
                                        ctx.refresh, timeout=8, attempts=1)) if extra else {}
        backfill_requested = extra
        for u in extra:
            r = more.get(u) or {}
            if r.get("state") != "ok" or len(pages) >= want + 2 or domain(u) in {p["domain"] for p in pages}:
                skipped.append({"url": u, "why": "backfill unavailable, redundant or sufficient readable sources retained"})
                continue
            blocks = r.get("blocks", [])
            if clone_of(blocks, pages) or other_language(blocks, ctx.brief.get("locale") or "en-GB"):
                continue
            pages.append({"position": None, "url": u, "domain": domain(u), "kind": kind(u),
                          "title": r.get("title"), "outline": [[int(t[1]), x] for t, x in blocks if t in ("h1", "h2", "h3", "h4")],
                          "words": r.get("words", 0), "tables": r.get("tables", 0), "blocks": blocks, "backfill": True,
                          "final_url": r.get("final_url") or u, "source_role": "backfill", "via": r.get("via") or "direct"})
    for p in pages:
        p.pop("_sh", None)
    words = [p["words"] for p in pages if p["words"]]
    return {"pages": pages, "skipped": skipped,
            "acquisition": {"mode": "deep" if ctx.deep() else "quick", "requested_urls": [o["link"] for o in targets] + backfill_requested,
                            "renderer": "spider" if spider.api_key() else "unavailable; direct HTTP fallback",
                            "question_sources": counts, "note": "All PAA/related text is retained; source pages use a bounded supplement budget"},
            "median_words": int(statistics.median(words)) if words else None,
            "summary": f"{len(pages)} pages read, {len(skipped)} skipped, median {int(statistics.median(words)) if words else 0} words"}
