"""GSC insights: what Google already shows this page for, and what that means for the rewrite."""
import re

from seolib import connectors as K

# Rough organic CTR by position, used only to flag titles that under-perform their rank.
EXPECTED_CTR = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018}
STOP = set("a an the and or of to in on for with by from at is are be how what why when where which who can do does "
           "you your my i it me near best online".split())


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def rows_from_api(resp, keys):
    out = []
    for r in resp.get("rows", []):
        rec = dict(zip(keys, r.get("keys", [])))
        rec.update(clicks=r.get("clicks", 0), impressions=r.get("impressions", 0),
                   ctr=r.get("ctr", 0.0), position=round(r.get("position", 0.0), 1))
        out.append(rec)
    return out


def run(ctx):
    if not ctx.connector_on("gsc"):
        return {"skipped": "gsc not enabled in the brief's connectors"}
    b = ctx.brief
    url = b["page_url"]
    site = b.get("gsc_property") or f"sc-domain:{b['domain'].replace('www.', '')}"
    raw = ctx.raw("gsc_insights")
    if raw:
        page_rows, site_rows, source = raw.get("page_rows", []), raw.get("site_rows", []), "mcp"
        window = raw.get("window")
    else:
        why = K.gsc_configured()
        if why:
            return {"not_configured": why,
                    "mcp_route": "fetch query rows for this page via a GSC MCP server, then `seo.py ingest <run> gsc_insights <file>`"}
        start, end = K.gsc_window(90)
        window = [start, end]
        r1 = K.gsc_query(site, {"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": 1000,
                                "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals",
                                                                        "expression": url}]}]})
        if r1.get("error") or r1.get("not_configured"):
            return {"error": r1.get("error") or r1.get("not_configured")}
        page_rows = rows_from_api(r1, ["query"])
        head = sorted(toks(b["target_query"]), key=len, reverse=True)
        site_rows = []
        if head:
            r2 = K.gsc_query(site, {"startDate": start, "endDate": end, "dimensions": ["query", "page"], "rowLimit": 5000,
                                    "dimensionFilterGroups": [{"filters": [{"dimension": "query", "operator": "contains",
                                                                            "expression": head[0]}]}]})
            site_rows = rows_from_api(r2, ["query", "page"]) if not r2.get("error") else []
        source = "api"
    if not page_rows:
        # New page (or a page with no impressions): still check which client pages already rank for the topic.
        others = {}
        for r in site_rows:
            if r["page"].rstrip("/") != url.rstrip("/") and r["impressions"] >= 10:
                o = others.setdefault(r["page"], {"page": r["page"], "impressions": 0, "queries": []})
                o["impressions"] += r["impressions"]
                if len(o["queries"]) < 5:
                    o["queries"].append(r["query"])
        ranked = sorted(others.values(), key=lambda o: -o["impressions"])[:5]
        decisions = [f"{url} has no Search Console queries yet."]
        if ranked:
            decisions.append("Client pages already showing for this topic: " + "; ".join(
                f"{o['page']} ({o['impressions']} impressions)" for o in ranked)
                + ". Give this page a distinct angle and link to them; don't duplicate.")
        return {"source": source, "rows": [], "existing_topic_pages": ranked, "decisions": decisions,
                "summary": f"no rows for this page; {len(ranked)} other client pages show for the topic"}
    page_rows.sort(key=lambda r: -r["impressions"])
    text = (ctx.load("current_page") or {}).get("text", "").lower()
    ptoks = toks(text)
    striking = [r for r in page_rows if 4 <= r["position"] <= 20 and r["impressions"] >= 10][:25]
    low_ctr = [r for r in page_rows if r["position"] <= 10 and r["impressions"] >= 50
               and r["ctr"] < 0.6 * EXPECTED_CTR.get(max(1, round(r["position"])), 0.02)][:10]
    gaps = []
    for r in page_rows[:200]:
        qt = toks(r["query"])
        if r["impressions"] >= 5 and qt and not qt <= ptoks:
            gaps.append({**r, "missing_terms": sorted(qt - ptoks)})
    gaps = gaps[:25]
    top_q = {r["query"] for r in page_rows[:30]}
    cannibal = {}
    for r in site_rows:
        if r["query"] in top_q and r["page"].rstrip("/") != url.rstrip("/") and r["impressions"] >= 10:
            cannibal.setdefault(r["query"], []).append({"page": r["page"], "position": r["position"],
                                                       "impressions": r["impressions"]})
    totals = {"queries": len(page_rows), "clicks": sum(r["clicks"] for r in page_rows),
              "impressions": sum(r["impressions"] for r in page_rows)}
    decisions = []
    if striking:
        decisions.append(f"{len(striking)} striking-distance queries (positions 4–20): cover them explicitly.")
    if low_ctr:
        decisions.append(f"{len(low_ctr)} queries rank on page 1 with weak CTR: the title and meta description get rewritten for them.")
    if cannibal:
        decisions.append(f"{len(cannibal)} top queries also send impressions to other client pages (cannibalisation): "
                         "keep this page's angle distinct and link to the other page instead of duplicating it.")
    return {"source": source, "window": window, "totals": totals, "rows": page_rows[:60], "striking": striking,
            "low_ctr": low_ctr, "gaps": gaps, "cannibalisation": cannibal, "decisions": decisions,
            "summary": f"{totals['queries']} queries, {totals['clicks']} clicks, {len(striking)} striking, "
                       f"{len(gaps)} gaps, {len(cannibal)} cannibalised"}
