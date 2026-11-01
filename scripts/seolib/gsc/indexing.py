"""Index state from the URL Inspection API: a replica of the Page indexing report (IX5) and the per-URL triage
(U-A, IX1-IX4, IX14), including the user's own "Crawled - currently not indexed" rescue.

The API returns the indexed view only (no live test, rendered HTML or Request indexing) and allows 2,000 inspections
a day per property, so URLs are chosen by value: pages with impressions first, then sitemap and inventory pages,
skipping anything inspected in the last 14 days.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from . import analyze as A

DAILY_BUDGET = 1900  # headroom under Google's 2,000/day per property [synth]

# coverageState (the same strings as the Page indexing report) -> (bucket, playbook, what to do)
ROUTES = [
    (r"submitted and indexed|indexed, not submitted", "indexed", "-", "indexed"),
    (r"indexed, though blocked by robots", "warning", "IX4",
     "remove the robots block and use noindex to keep it out, or unblock it to have it indexed properly"),
    (r"indexed without content", "warning", "IX4",
     "Google indexed an empty page: compare Googlebot's fetch with a browser's (WAF challenge, client-side rendering, "
     "non-HTML); run the render check"),
    (r"crawled.{1,4}currently not indexed", "ccni", "U-A", "Crawled - currently not indexed: triage below"),
    (r"discovered.{1,4}currently not indexed", "dcni", "IX2",
     "Discovered - currently not indexed: raise internal links from the homepage and hubs, cut URL bloat, check server "
     "response time; Mueller: it 'can be forever' for URLs Google sees no demand for"),
    (r"google chose different canonical", "canonical", "IX3",
     "Google picked another canonical: an internal URL -> merge, differentiate or 301 (a cannibalisation signal); "
     "another domain -> syndication, copy or hack; http/www variant -> site-wide redirect fix"),
    (r"duplicate without user-selected canonical", "canonical", "IX3",
     "add a self-referencing canonical on the version you want, and point duplicates at it"),
    (r"alternate page with proper canonical|page with redirect", "ok", "-", "expected: nothing to do"),
    (r"noindex", "technical", "IX1", "noindex on a URL you want indexed: remove the tag or header"),
    (r"blocked by robots", "technical", "IX1", "robots.txt blocks a URL you want: remove the rule (test it first)"),
    (r"soft 404", "technical", "IX1",
     "soft 404: return a real 404/410, or give the page real content (out-of-stock, empty filter and 'not found' "
     "pages answering 200 are the usual causes; on Next.js check deploy version skew)"),
    (r"not found \(404\)|\b404\b", "technical", "IX1", "404: fix only if it is linked internally or listed in a sitemap"),
    (r"server error|5xx", "technical", "IX1", "5xx: server capacity or errors; check Crawl Stats host status"),
    (r"redirect error", "technical", "IX1", "redirect loop or chain: one hop to the final URL"),
    (r"unauthorized|\(401\)|forbidden|\(403\)|other 4xx", "technical", "IX1",
     "access blocked: a WAF/bot rule or login is stopping Googlebot; allowlist verified Googlebot"),
    (r"removal tool", "technical", "IX9", "a Removals request hides it: cancel it if the page should show"),
    (r"unknown to google", "unknown", "IX2",
     "Google has never seen it: link it from indexed pages and list it in a sitemap"),
]


def norm_inspection(d: dict) -> dict:
    """Any server's inspection output as the API's indexStatusResult fields (camelCase)."""
    if not isinstance(d, dict):
        return {}
    for k in ("inspectionResult", "result", "data"):
        if isinstance(d.get(k), dict):
            d = d[k]
    isr = d.get("indexStatusResult") or d.get("index_status_result") or d
    out = {}
    names = {"verdict": ("verdict", "index_verdict"), "coverageState": ("coverageState", "coverage_state", "coverage"),
             "robotsTxtState": ("robotsTxtState", "robots_txt_state"), "indexingState": ("indexingState", "indexing_state"),
             "pageFetchState": ("pageFetchState", "page_fetch_state"), "lastCrawlTime": ("lastCrawlTime", "last_crawl_time"),
             "googleCanonical": ("googleCanonical", "google_canonical"), "userCanonical": ("userCanonical", "user_canonical"),
             "sitemap": ("sitemap", "sitemaps"), "referringUrls": ("referringUrls", "referring_urls"),
             "crawledAs": ("crawledAs", "crawled_as")}
    for key, alts in names.items():
        for a in alts:
            if a in isr and isr[a] not in (None, ""):
                out[key] = isr[a]
                break
    rr = d.get("richResultsResult") or d.get("rich_results_result")
    if rr:
        out["richResults"] = rr
    return out


def route(insp: dict) -> tuple[str, str, str]:
    cov = (insp.get("coverageState") or "").lower()
    for pat, bucket, pb, what in ROUTES:
        if re.search(pat, cov):
            return bucket, pb, what
    fetch = (insp.get("pageFetchState") or "").upper()
    if fetch and fetch != "SUCCESSFUL":
        return "technical", "IX1", f"page fetch {fetch}"
    return ("indexed" if (insp.get("verdict") or "").upper() == "PASS" else "unknown"), "-", cov or "no state"


def crawl_age_days(insp: dict) -> float | None:
    t = insp.get("lastCrawlTime")
    if not t:
        return None
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 86400
    except ValueError:
        return None


def flags(url: str, insp: dict, impressions: int = 0, in_sitemap: bool | None = None) -> list[str]:
    """IX5 flags on a URL that is wanted (in a sitemap or earning impressions)."""
    f = []
    gc, uc = A.norm(insp.get("googleCanonical") or ""), A.norm(insp.get("userCanonical") or "")
    if gc and uc and gc != uc:
        f.append(f"canonical mismatch: Google chose {insp['googleCanonical']} over {insp['userCanonical']}")
    elif gc and gc != A.norm(url) and not uc:
        f.append(f"Google's canonical is another URL: {insp['googleCanonical']}")
    if (insp.get("indexingState") or "").upper().startswith("BLOCKED") and (in_sitemap or insp.get("sitemap")):
        f.append(f"{insp['indexingState']} but listed in a sitemap: remove it from the sitemap or allow indexing")
    if (insp.get("robotsTxtState") or "").upper() == "DISALLOWED" and impressions:
        f.append("robots.txt disallows a URL that earns impressions")
    if (insp.get("pageFetchState") or "SUCCESSFUL").upper() != "SUCCESSFUL":
        f.append(f"fetch state {insp.get('pageFetchState')}")
    age = crawl_age_days(insp)
    if age is not None and age > 90 and impressions:
        f.append(f"last crawled {int(age)} days ago: a key page Google rarely revisits (internal links, lastmod)")
    if (insp.get("crawledAs") or "").upper() == "DESKTOP":
        f.append("crawled as desktop: check that mobile-first indexing sees the same content")
    if in_sitemap is False and impressions:
        f.append("earns impressions but no sitemap lists it")
    if "referringUrls" in insp and not insp.get("referringUrls") and not insp.get("sitemap"):
        f.append("no referring page and no sitemap known to Google: likely orphan")
    return f


def triage_ccni(url: str, insp: dict, impressions_16m: int, queries: list[dict], kind_hint: str = "") -> dict:
    """U-A: the user's rescue of 'Crawled - currently not indexed', with the research refinements.
    Branch A (the page earned impressions): its own queries are the rewrite seed -> H2s and main content.
    Branch B (never any impressions): no queries to use -> merge into a stronger page, differentiate with unique
    data/experience, or build authority with contextual links from trafficked pages."""
    steps = []
    path = urlparse(url).path.lower()
    if re.search(r"/(tag|tags|category|author|page|search|feed)/|[?&](s|q|sort|filter|page)=", path + "?" + urlparse(url).query):
        return {"url": url, "branch": "not-wanted", "action": "a URL type that shouldn't be indexed (tag, filter, search, "
                "pagination, feed): noindex, canonical, 404 or merge, and stop", "steps": []}
    gc = insp.get("googleCanonical")
    if gc and A.norm(gc) != A.norm(url):
        return {"url": url, "branch": "duplicate", "action": f"Google treats it as a duplicate of {gc}: IX3", "steps": []}
    age = crawl_age_days(insp)
    recent = age is not None and age <= 60
    steps.append(f"crawl activity: last crawled {int(age)} days ago" if age is not None else "crawl activity: no crawl date")
    steps.append("authority check (Quaid): count internal links from pages with clicks, and external links")
    steps.append("title check (Sturm): is the title generic or near-duplicate of another page's? Make it unique: keyword + benefit")
    steps.append("render check: are the main text, H1 and links in the raw HTML? (`seo.py gsc render <url>`)")
    if impressions_16m > 0 and queries:
        q = [r["query"] for r in sorted(queries, key=lambda r: -r.get("impressions", 0))[:12]]
        action = ("rewrite from its own queries (Branch A): put them in H2s and the main content, check what a stronger "
                  "page now competes for them, then /page-seo rewrite" + ("" if recent else
                  "; crawl is old, so add body links from trafficked pages too (demand/authority, like DCNI)"))
        return {"url": url, "branch": "A", "action": action, "queries": q, "steps": steps, "recent_crawl": recent}
    return {"url": url, "branch": "B", "steps": steps, "recent_crawl": recent,
            "action": "no impressions ever (Branch B): merge into a stronger page and 301, or differentiate with unique "
                      "data and first-hand experience, or build authority with 3-5 contextual links from indexed, "
                      "trafficked pages; seed any rewrite from keyword research and the SERP, not from Search Console"}


def template(url: str) -> str:
    """URL template for grouping ('one template usually has one cause', Onely)."""
    parts = [p for p in urlparse(url).path.split("/") if p]
    if not parts:
        return "/"
    if len(parts) == 1:
        return "/*"
    return f"/{parts[0]}/" + "*/" * (len(parts) - 2) + "*"


def select(candidates: list[tuple[str, int]], inspected: dict, limit: int, recheck_days: int = 14) -> list[str]:
    """URLs to inspect next: by value (impressions), skipping fresh inspections. candidates: [(url, impressions)]."""
    out, seen = [], set()
    for url, _ in sorted(candidates, key=lambda x: -x[1]):
        k = A.norm(url)
        if k in seen:
            continue
        seen.add(k)
        prev = inspected.get(url) or {}
        age = None
        if prev.get("_inspected_at"):
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(prev["_inspected_at"])).days
            except ValueError:
                pass
        if age is not None and age < recheck_days:
            continue
        out.append(url)
        if len(out) >= limit:
            break
    return out


def summary(items: dict, perf: dict[str, int], qp_rows: list[dict], sitemap_urls: set[str] | None = None) -> dict:
    """The replica of the Page indexing report: buckets, templates, flags, the site-level quality gate and the CCNI
    triage. items: {url: inspection}; perf: {norm(url): impressions over 16 months (or 90 days)}."""
    sm = {A.norm(u) for u in (sitemap_urls or set())}
    buckets, states, by_tpl = Counter(), Counter(), defaultdict(Counter)
    flagged, technical, ccni = [], [], []
    for url, raw in items.items():
        insp = norm_inspection(raw)
        if not insp:
            continue
        b, pb, what = route(insp)
        buckets[b] += 1
        states[insp.get("coverageState") or "?"] += 1
        by_tpl[template(url)][b] += 1
        imp = perf.get(A.norm(url), 0)
        f = flags(url, insp, imp, (A.norm(url) in sm) if sitemap_urls is not None else None)
        if f:
            flagged.append({"url": url, "flags": f, "impressions": imp})
        if b in ("technical", "warning", "canonical", "dcni", "unknown"):
            technical.append({"url": url, "state": insp.get("coverageState"), "playbook": pb, "fix": what, "impressions": imp})
        if b == "ccni":
            ccni.append(triage_ccni(url, insp, imp, A.page_rows_for(qp_rows, url)))
    wanted = sum(buckets.values()) - buckets["ok"]
    not_idx = buckets["ccni"] + buckets["dcni"]
    share = round(not_idx / wanted, 2) if wanted else 0
    tpl = []
    for t, c in by_tpl.items():
        n = sum(c.values())
        tpl.append({"template": t, "inspected": n, "indexed": c["indexed"], "index_rate": round(c["indexed"] / n, 2) if n else 0,
                    "ccni": c["ccni"], "dcni": c["dcni"], "technical": c["technical"]})
    tpl.sort(key=lambda r: -r["inspected"])
    rates = [r["index_rate"] for r in tpl if r["inspected"] >= 5]
    med = sorted(rates)[len(rates) // 2] if rates else None
    weak = [r for r in tpl if med is not None and r["inspected"] >= 5 and r["index_rate"] < 0.5 * med]
    gate = None
    if wanted >= 20 and share >= 0.3 and len({r["template"] for r in tpl if r["ccni"] + r["dcni"]}) >= 3:
        gate = (f"{int(share * 100)}% of inspected wanted URLs are crawled/discovered but not indexed, across many "
                "templates: Google calls this a site-quality signal (Mueller, Illyes). Run pruning and consolidation "
                "(merge thin pages, noindex/404 junk) before rewriting pages one by one. Google publishes no target ratio.")
    order = {"IX1": 0, "IX4": 1, "IX3": 2, "IX2": 3, "IX9": 4}
    technical.sort(key=lambda r: (order.get(r["playbook"], 9), -r["impressions"]))
    return {"inspected": sum(buckets.values()), "buckets": dict(buckets), "states": dict(states.most_common()),
            "not_indexed_share": share, "templates": tpl, "weak_templates": weak, "site_gate": gate,
            "technical": technical, "flags": sorted(flagged, key=lambda r: -r["impressions"]),
            "ccni": sorted(ccni, key=lambda r: (r["branch"] != "A", r["url"]))}
