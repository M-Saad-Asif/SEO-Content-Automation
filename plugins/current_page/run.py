"""Current page (rewrite mode): what the page says today."""
from seolib import common as C


def run(ctx):
    url = ctx.brief["page_url"]
    r = C.run_async(C.fetch_many([{"url": url, "kind": "page", "parse": "doc"}], ctx.refresh)).get(url) or {}
    if r.get("state") != "ok":
        ctx.decide(f"Rewrite requested but {url} returned {r.get('status')} ({r.get('state')}); treated as a new page.")
        return {"exists": False, "status": r.get("status"), "summary": "page not readable"}
    page = ctx.load("foundation")["sheet"].get("page", {})
    blocks = r.get("blocks", [])
    outline = [[int(t[1]), x] for t, x in blocks if t in ("h1", "h2", "h3", "h4")]
    return {"exists": True, "url": url, "title": page.get("title"), "meta_description": page.get("meta_description"),
            "outline": outline, "words": r.get("words"), "tables": r.get("tables"),
            "text": r.get("text", "")[:60000],
            "blocks": [[t, x] for t, x in blocks if t in ("h2", "h3", "h4", "p", "li")][:400],  # the plan keeps its headings
            "summary": f"{r.get('words')} words, {len(outline)} headings"}
