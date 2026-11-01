"""GSC insights: what Google already shows this page for, and what that means for the rewrite or the new page.

Data, in order of preference: rows the agent ingested through an MCP server for this run (`seo.py ingest <run>
gsc_insights`), the client's Search Console store (sites/<slug>/gsc, filled by `seo.py gsc pull` or the MCP fetch
plan), then a live API call for this page. Every analysis comes from seolib.gsc, the same code the site audit uses.
"""
import re

from seolib import connectors as K
from seolib.gsc import analyze as A, api, bus, caveats as CV, indexing as IX, store as S

STOP = set("a an the and or of to in on for with by from at is are be how what why when where which who can do does "
           "you your my i it me near best online".split())


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def rows_from_api(resp, keys):
    return api.rows(resp, keys)


def run(ctx):
    if not ctx.connector_on("gsc"):
        return {"skipped": "gsc not enabled in the brief's connectors"}
    b = ctx.brief
    url = b.get("page_url") or ""
    topic = b.get("target_query") or ""
    slug = S.slug_for(b)
    prop = S.property_for(slug, b) if slug else (b.get("gsc_property") or f"sc-domain:{(b.get('domain') or '').replace('www.', '')}")
    g = bus.for_brief(b)
    raw = ctx.raw("gsc_insights")
    head = sorted(toks(topic), key=len, reverse=True)
    window = None
    if raw:
        page_rows, site_rows, source, window = raw.get("page_rows", []), raw.get("site_rows", []), "mcp", raw.get("window")
    elif g and g.has("query_page"):
        page_rows = [{k: r.get(k, 0) for k in ("query", "clicks", "impressions", "ctr", "position")}
                     for r in A.page_rows_for(g.rows("query_page"), url)] if url else []
        site_rows = A.topic_rows(g.rows("query_page"), set(head[:1])) if head else []
        source, window = "store", g.meta("query_page").get("window")
    else:
        why = K.gsc_configured()
        if why:
            return {"not_configured": why,
                    "mcp_route": "fetch this page's query rows via a Search Console MCP server, then `seo.py ingest <run> "
                                 "gsc_insights <file>`; or fill the site store with `seo.py gsc plan <client>`"}
        start, end = K.gsc_window(90)
        window = [start, end]
        page_rows = []
        if url:
            r1 = K.gsc_query(prop, {"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": 1000,
                                    "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals",
                                                                            "expression": url}]}]})
            if r1.get("error") or r1.get("not_configured"):
                return {"error": r1.get("error") or r1.get("not_configured")}
            page_rows = rows_from_api(r1, ["query"])
        site_rows = []
        if head:
            r2 = K.gsc_query(prop, {"startDate": start, "endDate": end, "dimensions": ["query", "page"], "rowLimit": 5000,
                                    "dimensionFilterGroups": [{"filters": [{"dimension": "query", "operator": "contains",
                                                                            "expression": head[0]}]}]})
            site_rows = rows_from_api(r2, ["query", "page"]) if not r2.get("error") else []
        source = "api"
    caveat_lines = CV.lines(tuple(window)) if window and len(window) == 2 else []
    extra = _connections(g, url, topic, prop)
    if not page_rows:
        # New page (or a page with no impressions): which client pages already rank for the topic.
        others = {}
        for r in site_rows:
            if A.norm(r["page"]) != A.norm(url) and r["impressions"] >= 10:
                o = others.setdefault(r["page"], {"page": r["page"], "impressions": 0, "queries": []})
                o["impressions"] += r["impressions"]
                if len(o["queries"]) < 5:
                    o["queries"].append(r["query"])
        ranked = sorted(others.values(), key=lambda o: -o["impressions"])[:5] or [
            {k: p[k] for k in ("page", "impressions", "queries")} for p in extra.get("link_targets", [])[:5]]
        decisions = [f"{url or 'This page'} has no Search Console queries yet."]
        if url and b.get("task") == "rewrite":
            decisions.append("A live page with no impressions has no queries to rewrite from (Branch B of the indexing "
                             "playbook): seed it from the SERP and keyword research, make it distinct from the client's "
                             "stronger pages, and plan contextual links into it from trafficked pages.")
        if ranked:
            decisions.append("Client pages already showing for this topic: " + "; ".join(
                f"{o['page']} ({o['impressions']} impressions)" for o in ranked)
                + ". Give this page a distinct angle and link to them; don't duplicate.")
        return {"source": source, "rows": [], "existing_topic_pages": ranked, "decisions": decisions + extra.pop("decisions", []),
                "caveats": caveat_lines, **extra,
                "summary": f"no rows for this page; {len(ranked)} other client pages show for the topic"}
    page_rows.sort(key=lambda r: -r["impressions"])
    text = (ctx.load("current_page") or {}).get("text", "").lower()
    ptoks = toks(text)
    curve = g.curve if g else A.ctr_curve(page_rows + site_rows)
    striking = [r for r in page_rows if 4 <= r["position"] <= 20 and r["impressions"] >= 10][:25]
    low_ctr = A.ctr_deficit(page_rows, curve, min_impr=50)[:10]
    buckets = A.page_queries(page_rows, 20, min_impr=5)
    gaps = []
    for r in page_rows[:200]:
        qt = toks(r["query"])
        if r["impressions"] >= 5 and qt and not qt <= ptoks:
            gaps.append({**r, "missing_terms": sorted(qt - ptoks)})
    gaps = gaps[:25]
    top_q = {r["query"] for r in page_rows[:30]}
    cannibal = {}
    for r in site_rows:
        if r["query"] in top_q and A.norm(r["page"]) != A.norm(url) and r["impressions"] >= 10:
            cannibal.setdefault(r["query"], []).append({"page": r["page"], "position": r["position"],
                                                       "impressions": r["impressions"]})
    totals = {"queries": len(page_rows), "clicks": sum(r["clicks"] for r in page_rows),
              "impressions": sum(r["impressions"] for r in page_rows), "position": A.wpos(page_rows)}
    questions = [r for r in buckets["question"] if r["position"] > 3][:12]
    decisions = []
    if striking:
        decisions.append(f"{len(striking)} striking-distance queries (positions 4–20): cover them explicitly.")
    if questions:
        decisions.append(f"{len(questions)} question queries the page already shows for: answer each under its own "
                         "heading in the searcher's words (FAQ rich results ended May 2026; this is for ranking and AI answers).")
    if low_ctr:
        decisions.append(f"{len(low_ctr)} page-1 queries under the site's own CTR curve: the title and meta description "
                         "get rewritten for them.")
    if cannibal:
        decisions.append(f"{len(cannibal)} top queries also send impressions to other client pages (cannibalisation): "
                         "keep this page's angle distinct and link to the other page instead of duplicating it.")
    an = extra.get("anonymised_share")
    if an and an >= 0.6:
        decisions.append(f"{int(an * 100)}% of this page's clicks come from queries Search Console doesn't list: optimise "
                         "for the topic's coverage, not only the listed keywords.")
    return {"source": source, "window": window, "totals": totals, "rows": page_rows[:60], "striking": striking,
            "low_ctr": low_ctr, "gaps": gaps, "cannibalisation": cannibal, "questions": questions,
            "should_rank": buckets["should_rank"][:15], "ctr_curve": curve.get("curve"),
            "ctr_curve_source": f"{curve.get('site_points', 0)} of 10 positions from the site's own data",
            "caveats": caveat_lines, "decisions": decisions + extra.pop("decisions", []), **extra,
            "summary": f"{totals['queries']} queries, {totals['clicks']} clicks, {len(striking)} striking, "
                       f"{len(questions)} questions, {len(gaps)} gaps, {len(cannibal)} cannibalised"}


def _connections(g, url: str, topic: str, prop: str) -> dict:
    """What the rest of the suite knows about this page and topic: index state, decay, device gap, anonymised share,
    link targets (client pages ranking for the topic) and link sources (trafficked pages that should link here)."""
    out, decisions = {}, []
    if g:
        out["link_targets"] = g.topic(topic, exclude=url or None)
        if url:
            out["link_sources"] = g.link_sources(url, topic)
            p = g.page(url)
            for k in ("index", "decay", "device_gap", "anonymised_share", "changes"):
                if p.get(k):
                    out[k] = p[k]
    if url and "index" not in out and not api.configured():
        r = api.inspect(prop, url)  # one call, cached a week; quota 2,000/day
        if not r.get("error") and not r.get("not_configured"):
            n = IX.norm_inspection(r)
            bucket, pb, what = IX.route(n)
            out["index"] = {**{k: n.get(k) for k in ("coverageState", "googleCanonical", "userCanonical", "lastCrawlTime",
                                                      "pageFetchState", "indexingState")}, "bucket": bucket, "playbook": pb,
                            "what_to_do": what, "flags": IX.flags(url, n)}
    ix = out.get("index") or {}
    if ix.get("bucket") in ("ccni", "dcni", "technical", "canonical", "warning"):
        decisions.append(f"URL Inspection: {ix.get('coverageState')} → {ix.get('what_to_do')}")
    for f in ix.get("flags") or []:
        decisions.append(f"URL Inspection flag: {f}")
    if out.get("decay"):
        decisions.append(f"Decaying page ({out['decay']['prev_clicks']} → {out['decay']['clicks']} clicks): {out['decay']['cause']}")
    if out.get("device_gap"):
        d = out["device_gap"]
        decisions.append(f"Mobile ranks {d['mobile_position']} vs desktop {d['desktop_position']}: check mobile content parity and speed.")
    if out.get("link_sources"):
        decisions.append("After publishing, add contextual links into this page from: "
                         + "; ".join(f"{p['page']} ({p['clicks']} clicks)" for p in out["link_sources"][:4]))
    out["decisions"] = decisions
    return out
