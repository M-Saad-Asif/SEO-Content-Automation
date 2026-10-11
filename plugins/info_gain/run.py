"""Information gain: lived experience and independent views the top 10 lack.
Only excerpts actually read (or Google's own snippet) are kept, with sources."""
import re
from datetime import date

from seolib import common as C
from seolib import serper
from seolib.domains import domain, kind


def run(ctx):
    serp = ctx.load("serp_intel")
    if not serp or serp.get("error"):
        return {"error": "no SERP data"}
    q = serp["query"]
    intent = serp.get("intent", {}).get("primary")
    searches = [f"{q} reddit", f"{q} reviews" if intent in ("commercial", "transactional") else f"{q} experience forum"]
    res, cr = serper.batch([("search", s) for s in searches], ctx.brief["locale"])
    ctx.credits += cr
    top = {o["link"] for o in serp.get("organic", [])}
    client = ctx.brief["domain"].replace("www.", "")
    cands = []
    for (_, s), r in res.items():
        for o in r.get("organic", [])[:8]:
            link = o.get("link", "")
            if link in top or client in link:
                continue
            k = kind(link)
            yr = re.search(r"\b(20\d\d)\b", o.get("date") or "")
            if yr and int(yr.group(1)) < date.today().year - 2:
                continue  # stale experience for fast-changing topics
            if k in ("forum_ugc", "article", "business_site", "major_publisher"):
                cands.append({"url": link, "domain": domain(link), "kind": k, "title": o.get("title"),
                              "snippet": o.get("snippet"), "from_search": s})
    seen, items = set(), []
    for c in cands:
        if c["url"] not in seen:
            seen.add(c["url"])
            items.append(c)
    items = items[:8]
    pages = C.run_async(C.fetch_many([{"url": i["url"], "kind": "page", "parse": "doc"} for i in items[:5]],
                                     ctx.refresh, timeout=7, attempts=1))
    qt = {w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 3}
    for i in items:
        p = pages.get(i["url"]) or {}
        i["read"] = p.get("state") == "ok"
        ex = []
        if i["read"]:
            for t, x in p.get("blocks", []):
                if t in ("p", "li", "blockquote") and 12 <= len(x.split()) <= 90 and \
                        len(qt & set(re.findall(r"[a-z0-9]+", x.lower()))) >= 1 and \
                        re.search(r"\b(I|my|we|our|took|waited|got|received|had|tried|found)\b", x):
                    ex.append(x)
                if len(ex) >= 3:
                    break
        i["excerpts"] = ex
    usable = [i for i in items if i["excerpts"] or i.get("snippet")]
    rv = (ctx.load("reddit_voice") or {}).get("items") or []
    if rv:  # first-hand Reddit excerpts from the official API replace Reddit snippets
        usable = rv + [i for i in usable if i["domain"] != "reddit.com"]
    return {"searches": searches, "items": usable,
            "summary": f"{len(usable)} sources ({sum(1 for i in usable if i['excerpts'])} with first-hand excerpts)"}
