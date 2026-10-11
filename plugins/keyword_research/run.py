"""Keyword research (DataForSEO): volumes, intent, related keywords, deep PAA."""
from seolib import connectors as K


def run(ctx):
    if not ctx.connector_on("dataforseo"):
        return {"skipped": "dataforseo not enabled in the brief's connectors"}
    b = ctx.brief
    raw = ctx.raw("keyword_research")
    if raw:
        kws = raw.get("keywords", [])
        paa = raw.get("paa", [])
        source = "mcp"
    else:
        why = K.dfs_configured()
        if why:
            return {"not_configured": why,
                    "mcp_route": "use the DataForSEO MCP (related keywords, keyword overview, SERP with PAA), then `seo.py ingest <run> keyword_research <file>`"}
        loc = K.dfs_location(b["locale"], b.get("dataforseo_location"))
        lang = (b["locale"] or "en-GB").split("-")[0]
        gsc = ctx.load("gsc_insights") or {}
        seeds = [b["target_query"]] + [r["query"] for r in (gsc.get("rows") or [])[:2]]
        kws, paa = [], []
        rel = K.dfs_post("dataforseo_labs/google/related_keywords/live",
                         [{"keyword": s, "location_name": loc, "language_code": lang, "depth": 1, "limit": 40} for s in seeds[:2]])
        if rel.get("error"):
            return {"error": rel["error"]}
        for it in K.dfs_items(rel):
            kd = it.get("keyword_data") or {}
            info = kd.get("keyword_info") or {}
            kws.append({"keyword": kd.get("keyword"), "search_volume": info.get("search_volume"),
                        "intent": ((kd.get("search_intent_info") or {}).get("main_intent")),
                        "competition": info.get("competition_level"), "source": "related"})
        ov = K.dfs_post("dataforseo_labs/google/keyword_overview/live",
                        [{"keywords": list(dict.fromkeys(seeds + [r["query"] for r in (gsc.get("striking") or [])[:20]])),
                          "location_name": loc, "language_code": lang}])
        for it in K.dfs_items(ov):
            info = it.get("keyword_info") or {}
            kws.append({"keyword": it.get("keyword"), "search_volume": info.get("search_volume"),
                        "intent": (it.get("search_intent_info") or {}).get("main_intent"), "source": "overview"})
        if ctx.deep():
            serp = K.dfs_post("serp/google/organic/live/advanced",
                              [{"keyword": b["target_query"], "location_name": loc, "language_code": lang, "depth": 10,
                                "people_also_ask_click_depth": 2}])
            for it in K.dfs_items(serp):
                if it.get("type") == "people_also_ask":
                    for q in it.get("items") or []:
                        if q.get("title"):
                            paa.append(q["title"])
        source = "api"
    seen, uniq = set(), []
    for k in kws:
        key = (k.get("keyword") or "").lower()
        if key and key not in seen:
            seen.add(key)
            uniq.append(k)
    uniq.sort(key=lambda k: -(k.get("search_volume") or 0))
    main = next((k for k in uniq if k["keyword"].lower() == b["target_query"].lower()), None)
    decisions = []
    if main and main.get("intent"):
        decisions.append(f"DataForSEO labels \"{b['target_query']}\" as {main['intent']} intent "
                         f"({main.get('search_volume') or 0} searches a month).")
    return {"source": source, "keywords": uniq[:80], "paa": list(dict.fromkeys(paa))[:20], "main": main,
            "decisions": decisions,
            "summary": f"{len(uniq)} keywords, {len(paa)} PAA (click depth 2)"}
