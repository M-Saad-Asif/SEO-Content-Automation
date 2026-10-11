"""Reddit voice: first-hand experience through the official Reddit Data API."""
import re

from seolib import connectors as K

FIRST_HAND = re.compile(r"\b(I|I'm|I've|my|we|our|took|waited|got|received|had|tried|applied|paid|bought|used)\b")


def run(ctx):
    if not ctx.connector_on("reddit"):
        return {"skipped": "reddit not enabled in the brief's connectors"}
    q = ctx.brief["target_query"]
    raw = ctx.raw("reddit_voice")
    threads = []
    if raw:
        threads, source = raw.get("threads", []), "mcp"
    else:
        why = K.reddit_configured()
        if why:
            return {"not_configured": why}
        res = K.reddit_get("/search", {"q": q, "sort": "relevance", "t": "year", "limit": 8, "type": "link"})
        if res.get("error"):
            return {"error": res["error"]}
        posts = [c["data"] for c in (res.get("data") or {}).get("children", []) if c.get("data")]
        posts = [p for p in posts if not p.get("over_18") and p.get("num_comments", 0) >= 2][:5]
        for p in posts:
            com = K.reddit_get(f"/comments/{p['id']}", {"limit": 20, "sort": "top", "depth": 1})
            listing = com.get("listing") or []
            comments = []
            if len(listing) > 1:
                for c in listing[1].get("data", {}).get("children", []):
                    d = c.get("data") or {}
                    if d.get("body") and d.get("score", 0) >= 2 and d.get("author") not in ("AutoModerator", "[deleted]"):
                        comments.append({"text": d["body"], "score": d.get("score", 0)})
            threads.append({"url": "https://www.reddit.com" + p.get("permalink", ""), "subreddit": p.get("subreddit"),
                            "title": p.get("title"), "selftext": p.get("selftext", "")[:800], "comments": comments})
        source = "api"
    items = []
    for t in threads:
        ex = []
        for c in sorted(t.get("comments", []), key=lambda c: -(c.get("score") or 0) if isinstance(c, dict) else 0):
            text = c["text"] if isinstance(c, dict) else c
            text = " ".join(text.split())
            if 12 <= len(text.split()) <= 120 and FIRST_HAND.search(text) and "http" not in text:
                ex.append(text)
            if len(ex) >= 3:
                break
        if ex:
            items.append({"url": t["url"], "domain": "reddit.com", "kind": "forum_ugc",
                          "title": f"r/{t.get('subreddit')}: {t.get('title')}", "excerpts": ex, "read": True,
                          "via": "Reddit Data API" if source == "api" else "MCP"})
    return {"source": source, "items": items,
            "summary": f"{len(threads)} threads, {sum(len(i['excerpts']) for i in items)} first-hand excerpts"}
