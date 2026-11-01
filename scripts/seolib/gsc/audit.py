"""Site-level Search Console work: pull every dataset, inspect URLs within quota, run every playbook, write the
audit (sites/<slug>/gsc/audit.md + audit.json), and turn findings into actions the page pipeline can run.

Actions are typed: `rewrite` and `new` go to the /page-seo batch queue (`queue()`), with the Search Console reason
and target queries as the page's instructions; `fix` (technical), `merge` and `ask` (UI-only data) are for the
user or developer and are never applied automatically. Every robots.txt, removal, sitemap or Request indexing
step stays a proposal that needs the user's approval.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .. import common as C
from . import analyze as A, api, bus, crawl as CR, indexing as IX, mcp, store as S

AUDIT_DATASETS = ["pages", "pages_prev", "pages_yoy", "query_page", "query_page_prev", "queries", "page_device",
                  "page_country", "appearance", "dates", "discover", "news", "image", "video", "hourly"]
QUEUE_KINDS = ("optimizer", "questions", "new", "decay", "ctr", "ccni")


def pull(slug: str, names: list[str] | None = None, refresh: bool = False) -> dict:
    """API route: fill the store. A dataset fresher than 7 days is kept unless `refresh`."""
    why = api.configured()
    if why:
        return {"not_configured": why}
    prop, done = S.property_for(slug), {}
    for n in names or AUDIT_DATASETS:
        if not refresh and S.fresh(slug, n):
            done[n] = "fresh"
            continue
        spec, body = S.DATASETS[n], mcp.request(n)
        resp = api.query_all(prop, body, spec.get("max_rows", 25000), ttl=0 if refresh else 6 * 3600)
        if resp.get("not_configured"):
            return {"not_configured": resp["not_configured"]}
        if resp.get("error"):
            done[n] = resp["error"][:160]
            if "403" in resp["error"] or "404" in resp["error"]:
                break  # property access problem: every other call would fail the same way
            continue
        rows = mcp.norm_rows(resp.get("rows") or [], spec["dims"])
        S.save(slug, n, rows=rows, meta={"source": "api", "dims": spec["dims"], "window": [body["startDate"], body["endDate"]],
                                         "type": body["type"], "property": prop, "truncated": resp.get("truncated", False),
                                         "first_incomplete_date": (resp.get("metadata") or {}).get("first_incomplete_date")})
        done[n] = f"{len(rows)} rows"
    sm = api.sitemaps(prop)
    if not sm.get("error") and not sm.get("not_configured"):
        S.save(slug, "sitemaps", rows=sm.get("sitemap") or [], meta={"source": "api"})
        done["sitemaps"] = f"{len(sm.get('sitemap') or [])} sitemaps"
    return done


def candidates(slug: str) -> list[tuple[str, int]]:
    """URLs worth inspecting: pages with impressions, then sitemap/inventory pages (impressions 0)."""
    out = [(r["page"], r["impressions"]) for r in S.rows(slug, "pages")]
    from ..sitecontext import inventory
    out += [(p["url"], 0) for p in (inventory(slug).get("pages") or [])]
    return out


def inspect(slug: str, limit: int = 200) -> dict:
    """URL Inspection over the most valuable URLs not inspected in 14 days (quota 2,000/day/property)."""
    why = api.configured()
    if why:
        return {"not_configured": why}
    prop = S.property_for(slug)
    prev = (S.load(slug, "inspections") or {}).get("items") or {}
    urls = IX.select(candidates(slug), prev, min(limit, IX.DAILY_BUDGET))
    got, errors = {}, 0
    for u in urls:
        r = api.inspect(prop, u)
        if r.get("error") or r.get("not_configured"):
            errors += 1
            if "429" in str(r.get("error")) or errors >= 5:
                break
            continue
        got[u] = {**r, "_inspected_at": C.now_iso()}
    if got:
        S.save(slug, "inspections", items={**prev, **got}, meta={"source": "api", "property": prop})
    return {"inspected": len(got), "errors": errors, "asked": len(urls)}


def _headings(urls: list[str]) -> dict:
    res = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "html"} for u in urls], concurrency=8)) if urls else {}
    return {u: " ".join([r.get("title", "")] + (r.get("h1") or []) + (r.get("h2") or [])).lower()
            for u, r in res.items() if r and r.get("state") == "ok"}


def _missing(queries: list[str], heads: str) -> list[str]:
    hw = bus.words(heads)
    return [q for q in queries if bus.words(q) and not bus.words(q) <= hw]


def run(slug: str, check_headings: int = 20) -> dict:
    g = bus.Console(slug)
    if not g.available():
        raise ValueError(f"no Search Console data stored for {slug}: run `seo.py gsc pull {slug}` (API) or the MCP fetch "
                         f"plan (`seo.py gsc plan {slug}`) first")
    V = {n: g.view(n) for n in ("optimizer", "striking", "ctr", "questions", "conversational", "site_operator", "zero_click",
                                "emerging", "alignment", "intent", "brand", "cannibalisation", "decay", "decoupling",
                                "device", "country", "appearance", "coverage", "trend", "curve", "index")}
    heads = _headings([p["page"] for p in V["optimizer"][:check_headings]])
    for p in V["optimizer"]:
        if p["page"] in heads:
            p["missing_from_headings"] = _missing(p["top_queries"], heads[p["page"]])
    crawl_rec = (S.load(slug, "ui_crawl_stats") or {}).get("items")
    if crawl_rec:
        imp = {r["page"]: r["impressions"] for r in g.rows("pages")}
        important = [r["page"] for r in sorted(g.rows("pages"), key=lambda r: -r["impressions"])[:200]]
        robots = CR.fetch_robots(g.domain) if g.domain else {}
        V["crawl"] = CR.analyse(crawl_rec, imp, important, robots.get("text"))
        V["robots"] = {k: v for k, v in robots.items() if k != "text"}
    out = {"client": slug, "property": g.property, "generated_at": C.now_iso(), "summary": g.summary(), "views": V,
           "actions": actions(V), "missing_ui": [k for k in S.UI_DATASETS if not S.load(slug, k)]}
    C.save_json(S.site_dir(slug) / "audit.json", out)
    C.save_json(S.site_dir(slug) / "actions.json", {"generated_at": out["generated_at"], "actions": out["actions"]})
    (S.site_dir(slug) / "audit.md").write_text(render(out), encoding="utf-8")
    return out


def actions(V: dict) -> list[dict]:
    acts, seen = [], set()

    def add(kind, playbook, reason, url="", keyword="", queries=None, priority=0.0, approval=False):
        key = (kind, url or keyword)
        if key in seen:
            return
        seen.add(key)
        acts.append({"id": f"{playbook}:{len(acts) + 1}", "kind": kind, "playbook": playbook, "url": url, "keyword": keyword,
                     "queries": (queries or [])[:12], "reason": reason, "priority": round(priority), "approval": approval})
    for c in (V.get("index") or {}).get("ccni") or []:
        if c["branch"] == "A":
            add("rewrite", "U-A", "Crawled - currently not indexed, with past impressions: rewrite from its own queries "
                "(H2s and main content)", c["url"], (c.get("queries") or [""])[0], c.get("queries"), 5000)
        elif c["branch"] == "B":
            add("merge", "U-A", c["action"], c["url"], priority=1000)
    for t in (V.get("index") or {}).get("technical") or []:
        add("fix", t["playbook"], f"{t['state']}: {t['fix']}", t["url"], priority=3000 + t["impressions"])
    for p in V.get("optimizer") or []:
        qs = [r["query"] for r in p["ranking"] + p["should_rank"] + p["questions"]]
        miss = p.get("missing_from_headings")
        add("rewrite", "U-B", f"position {p['position']} with {p['impressions']} impressions: cover its ranking and "
            "should-rank queries in headings and sections, then beat the same-country competitors"
            + (f"; missing from title/H1/H2s: {', '.join(miss[:5])}" if miss else ""),
            p["page"], p["top_queries"][0] if p["top_queries"] else "", qs, p["score"])
    for d in V.get("decay") or []:
        add("rewrite", "PF10", f"clicks {int(d['change'] * 100)}% vs the previous 90 days: {d['cause']}", d["page"],
            priority=abs(d["clicks"] - d["prev_clicks"]) * 10)
    for r in (V.get("ctr") or [])[:30]:
        add("rewrite", "PF2", f"\"{r['query']}\" at position {r['position']} gets {r['ctr']:.1%} CTR vs the site's "
            f"{r['expected_ctr']:.1%}: rewrite the title and meta description for it (keep the sections that rank)",
            r.get("page", ""), r["query"], [r["query"]], r["missed_clicks"] * 10)
    for q in (V.get("questions") or {}).get("update", [])[:40]:
        add("rewrite", "U-C", f"question \"{q['query']}\" at position {q['position']}: add an H2 with the exact "
            "question and a direct answer", q["page"], q["query"], [q["query"]], q["impressions"])
    for q in (V.get("questions") or {}).get("new", [])[:25]:
        add("new", "U-C", f"question \"{q['query']}\" has no fitting page (position {q['position']})", "", q["query"],
            [q["query"]], q["impressions"] / 2)
    for c in (V.get("cannibalisation") or [])[:20]:
        if c["money_query"] or c["impressions"] >= 500:
            add("merge", "PF9", f"\"{c['query']}\" split across {len(c['pages'])} pages: {c['action']}; keep {c['keep']}",
                c["keep"], c["query"], [c["query"]], c["impressions"], approval=True)
    for a in (V.get("alignment") or [])[:20]:
        add("fix", "PF7", f"\"{a['query']}\": {a['issue']}; point internal anchors to the right page and strengthen it",
            a["page"], a["query"], [a["query"]], a["impressions"] / 2)
    for d in (V.get("decoupling") or [])[:15]:
        add("rewrite", "AI2", "impressions up and CTR down at a stable position: likely cited in AI Overviews; add a "
            "click reason (original data, tools, visuals)", d["page"], priority=500)
    for f in ((V.get("crawl") or {}).get("clusters") or []):
        if f.get("robots_rules"):
            add("fix", "U-D", f"crawl waste: {f['label']} ({f['count']} example URLs): {f['action']}", "", "",
                f["robots_rules"], 2000, approval=True)
    return sorted(acts, key=lambda a: -a["priority"])


def queue(slug: str, kinds: list[str] | None = None, limit: int = 10, run_now: bool = False):
    """The audit's rewrite/new actions as a /page-seo batch: each page gets the Search Console reason and queries
    as instructions, so the writers cover exactly those queries in headings and sections."""
    data = C.load_json(S.site_dir(slug) / "actions.json") or {}
    acts = data.get("actions") or run(slug)["actions"]
    want = set(kinds or QUEUE_KINDS)
    pb = {"optimizer": "U-B", "questions": "U-C", "new": "U-C", "decay": "PF10", "ctr": "PF2", "ccni": "U-A"}
    rows, seen = [], set()
    for a in acts:
        if a["kind"] not in ("rewrite", "new") or not any(pb[k] == a["playbook"] for k in want):
            continue
        if a["kind"] == "new" and "new" not in want:
            continue
        key = a["url"] or a["keyword"]
        if key in seen:
            continue
        seen.add(key)
        instr = f"Search Console ({a['playbook']}): {a['reason']}"
        if a["queries"]:
            instr += "; target queries: " + "; ".join(a["queries"][:10])
        row = {"instructions": instr}
        if a["url"]:
            row["url"] = a["url"]
        if a["keyword"]:
            row["keyword"] = a["keyword"]
        rows.append(row)
        if len(rows) >= limit:
            break
    if not rows:
        return None
    from ..batch import setup
    return setup(slug, rows=rows, run=run_now, bind=False)


def render(o: dict) -> str:
    V, s = o["views"], o["summary"]
    W = [f"# Search Console audit: {o['client']} ({o['property']})", "", f"Generated {o['generated_at']}. "
         f"90 days: {s['totals_90d']['clicks']} clicks, {s['totals_90d']['impressions']} impressions, "
         f"{s['totals_90d']['pages']} pages, {s['totals_90d']['queries']} listed queries.", "", "## Data and caveats"]
    W += [f"- {d['dataset']}: {d['rows']} rows, {d['source']}, {d['age_days']} days old" + (" (truncated)" if d["truncated"] else "")
          for d in s["datasets"]]
    W += [f"- {c}" for c in s["caveats"]]
    t = V.get("trend") or {}
    if t:
        change = "n/a" if t["clicks_change"] is None else f"{int(t['clicks_change'] * 100)}%"
        W += ["", "## Trend", f"- Last 28 days {t['last_28']['clicks']} clicks vs {t['prev_28']['clicks']} the 28 before "
              f"({change}); median "
              f"{t['median_daily_impressions']} impressions a day (Koray: re-ranking momentum from ~10,000/day)."]
    b = V.get("brand") or {}
    if b:
        W += ["", "## Brand vs non-brand (regex: " + str(b.get("regex")) + ")",
              f"- Brand {b['brand']['clicks']} clicks / {b['brand']['impressions']} impressions; non-brand "
              f"{b['nonbrand']['clicks']} / {b['nonbrand']['impressions']}. All opportunity work below is non-brand."]

    def sect(title, items, fmt, n=15):
        W.extend(["", f"## {title} ({len(items)})"] + [f"- {fmt(x)}" for x in items[:n]] if items else ["", f"## {title}", "- none"])
    sect("Page optimiser (U-B): pages at position <=20 that can climb", V.get("optimizer") or [],
         lambda p: f"{p['page']}: pos {p['position']}, {p['impressions']} impr.; ranking: "
                   f"{', '.join(r['query'] for r in p['ranking'][:4])}; should rank: {', '.join(r['query'] for r in p['should_rank'][:4])}"
                   + (f"; NOT in headings: {', '.join(p['missing_from_headings'][:4])}" if p.get("missing_from_headings") else ""))
    sect("Striking distance (PF1)", V.get("striking") or [],
         lambda r: f"\"{r['query']}\" pos {r['position']}, {r['impressions']} impr. → {r['page']} ({r['route']})")
    sect(f"CTR under the site's own curve (PF2; curve from {(V.get('curve') or {}).get('site_points')} site positions)",
         V.get("ctr") or [], lambda r: f"\"{r['query']}\" pos {r['position']}: CTR {r['ctr']:.1%} vs {r['expected_ctr']:.1%}, "
                                       f"~{r['missed_clicks']} clicks missed → {r.get('page')}")
    q = V.get("questions") or {}
    sect("Questions to add as H2s (U-C)", q.get("update") or [], lambda r: f"\"{r['query']}\" pos {r['position']} → {r['page']}")
    sect("Questions needing a new article (U-C)", q.get("new") or [], lambda r: f"\"{r['query']}\" ({r['impressions']} impr.)")
    sect("Conversational 10+ word queries (PF4)", V.get("conversational") or [], lambda r: f"\"{r['query']}\" → {r['page']}", 10)
    sect("Emerging queries (PF6)", V.get("emerging") or [], lambda r: f"\"{r['query']}\" {r['impressions']} impr., pos {r['position']}", 10)
    sect("Cannibalisation (PF9)", V.get("cannibalisation") or [],
         lambda c: f"\"{c['query']}\" ({c['impressions']} impr.): " + " vs ".join(f"{p['page']} (pos {p['position']})" for p in c["pages"])
                   + f" → {c['action']}")
    sect("Decay (PF10)", V.get("decay") or [], lambda d: f"{d['page']}: {d['prev_clicks']} → {d['clicks']} clicks; {d['cause']}")
    sect("Likely AI Overview citations (AI2)", V.get("decoupling") or [],
         lambda d: f"{d['page']}: impressions {int(d['impressions_change'] * 100)}%, CTR {int(d['ctr_change'] * 100)}%")
    sect("Zero-click queries (PF3)", V.get("zero_click") or [], lambda r: f"\"{r['query']}\" {r['impressions']} impr., {r['kind']}", 10)
    sect("Query on the wrong kind of page (PF7)", V.get("alignment") or [], lambda r: f"\"{r['query']}\" on {r['page']}: {r['issue']}", 10)
    sect("Mobile gaps (PF15)", V.get("device") or [], lambda r: f"{r['page']}: mobile pos {r['mobile_position']} vs desktop {r['desktop_position']}", 10)
    sect("Target-country gaps (PF16)", V.get("country") or [], lambda r: f"{r['page']}: pos {r['position']} in {r['country']} vs {r['elsewhere']}", 10)
    sect("Topical coverage by folder (PF27)", V.get("coverage") or [],
         lambda r: f"{r['folder']}: {r['queries']} queries {r['bands']}" + (f", +{r['new_queries']} new / -{r['lost_queries']} lost" if r.get("new_queries") is not None else ""), 12)
    ix = V.get("index") or {}
    if ix:
        W += ["", f"## Index state (URL Inspection replica, {ix['inspected']} URLs)", f"- Buckets: {ix['buckets']}"]
        if ix.get("site_gate"):
            W.append(f"- SITE-LEVEL: {ix['site_gate']}")
        W += [f"- weak template {t['template']}: index rate {t['index_rate']}" for t in ix.get("weak_templates", [])]
        W += [f"- {t['url']}: {t['state']} → {t['fix']}" for t in ix.get("technical", [])[:20]]
        W += [f"- CCNI {c['url']}: branch {c['branch']}: {c['action']}" for c in ix.get("ccni", [])[:20]]
        W += [f"- {f['url']}: {'; '.join(f['flags'])}" for f in ix.get("flags", [])[:15]]
    cr = V.get("crawl")
    if cr:
        W += ["", "## Crawl Stats (from your export)"] + [f"- {n}" for n in cr["notes"]]
        W += [f"- {c['label']}: {c['count']} examples, {'needed for rendering' if c['needed_for_render'] else 'not needed' if c['needed_for_render'] is False else 'test first'}"
              f"; {c['action']}" for c in cr["clusters"]]
        if cr.get("robots_proposal"):
            W += [f"- robots.txt PROPOSAL (needs your approval): {', '.join(cr['robots_proposal'])}; test: {cr['robots_test']['verdict']}"]
    W += ["", f"## Actions ({len(o['actions'])})", "Rewrite/new actions can be queued for the page pipeline; fix/merge "
          "actions are for you or a developer; anything marked APPROVAL is never done without your yes."]
    W += [f"- [{a['kind']}{' APPROVAL' if a['approval'] else ''}] {a['playbook']} {a['url'] or a['keyword']}: {a['reason']}" for a in o["actions"][:60]]
    if o.get("missing_ui"):
        W += ["", "## Not reachable through the API (export from Search Console, then `seo.py gsc ingest`)"]
        W += [f"- {k}: {S.UI_DATASETS[k]}" for k in o["missing_ui"]]
    return "\n".join(W) + "\n"


def age_label(slug: str) -> str:
    a = [d["age_days"] for d in S.manifest(slug) if d["dataset"] in AUDIT_DATASETS]
    return f"{min(a)}-{max(a)} days old" if a else "none stored"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
