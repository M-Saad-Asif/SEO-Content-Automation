"""Clarity UX: how real visitors behave on the page, as rewrite instructions."""
import re

from seolib import connectors as K


def norm(u):
    return re.sub(r"^https?://(www\.)?", "", (u or "").lower()).split("?")[0].split("#")[0].rstrip("/")


def num(v):
    try:
        return float(str(v).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def run(ctx):
    if not ctx.connector_on("clarity"):
        return {"skipped": "clarity not enabled in the brief's connectors"}
    raw = ctx.raw("clarity_ux")
    token_env = ctx.brief.get("clarity_token_env", "CLARITY_API_TOKEN")
    if raw:
        metrics, source = raw.get("metrics", raw), "mcp"
    else:
        r = K.clarity_insights(3, ("URL",), token_env)
        if r.get("not_configured"):
            return {"not_configured": r["not_configured"],
                    "mcp_route": "use Microsoft's Clarity MCP (dimension URL, last 3 days), then `seo.py ingest <run> clarity_ux <file>`"}
        if r.get("error"):
            return {"error": r["error"]}
        metrics, source = r["metrics"], "api"
    target = norm(ctx.brief["page_url"])
    found = {}
    for m in metrics if isinstance(metrics, list) else []:
        name = m.get("metricName") or m.get("name")
        for row in m.get("information") or []:
            u = row.get("URL") or row.get("Url") or row.get("url")
            if u and norm(u) == target:
                found[name] = row
    if not found:
        ctx.decide("Clarity has no sessions for this URL in the last 3 days; no behaviour-based changes.")
        return {"source": source, "page": None, "summary": "no Clarity data for this URL"}
    recs, facts = [], {}
    for name, row in found.items():
        vals = {k: num(v) for k, v in row.items() if num(v) is not None}
        facts[name] = vals
    sd = next((v for k, v in (facts.get("ScrollDepth") or {}).items() if "scroll" in k.lower() or "average" in k.lower()), None)
    if sd is not None and sd < 50:
        recs.append(f"Average scroll depth is {sd:.0f}%: most visitors never reach the lower sections. Answer the "
                    "query in the first screen and move the most-searched answers higher.")
    for metric, advice in (("DeadClickCount", "Visitors click things that aren't links (bold text, table cells, icons). "
                                              "Link the obvious targets or stop styling plain text like a link."),
                           ("RageClickCount", "Rage clicks show frustration with an element: check broken links, slow "
                                              "selectors or tables that look interactive."),
                           ("QuickbackClick", "Quickbacks (leaving then returning fast) suggest the page or a link didn't "
                                              "match what people expected: tighten the opening to the exact intent."),
                           ("ExcessiveScroll", "Excessive scrolling means people hunt for something: add a clear route "
                                               "(short contents list or the answer earlier).")):
        v = facts.get(metric) or {}
        pct = next((x for k, x in v.items() if "percentage" in k.lower()), None)
        cnt = next((x for k, x in v.items() if "count" in k.lower() or "session" in k.lower()), None)
        if (pct is not None and pct >= 5) or (pct is None and cnt and cnt >= 5):
            recs.append(advice)
    return {"source": source, "page": ctx.brief["page_url"], "metrics": facts, "recommendations": recs,
            "decisions": [f"Clarity: {len(recs)} behaviour-based structural fix(es) apply."] if recs else [],
            "summary": f"{len(facts)} metrics, {len(recs)} recommendations"}
