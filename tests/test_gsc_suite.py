"""Offline regressions for the Search Console suite (seolib/gsc) and its wiring into the pipeline. No network."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from seolib.gsc import analyze as A, caveats as CV, crawl as CR, indexing as IX, regexlib as RX  # noqa: E402


def row(query, page, clicks, impressions, position):
    return {"query": query, "page": page, "clicks": clicks, "impressions": impressions,
            "ctr": round(clicks / impressions, 4) if impressions else 0, "position": position}


SITE = "https://shop.test"
QP = [
    row("how to paint a fence", f"{SITE}/blog/paint-fence", 40, 2000, 7.0),
    row("how to paint a fence", f"{SITE}/services/fence-painting", 10, 900, 12.0),
    row("fence paint drying time", f"{SITE}/blog/paint-fence", 5, 400, 14.0),
    row("best fence paint", f"{SITE}/blog/paint-fence", 2, 300, 28.0),
    row("what is the best fence paint for wood", f"{SITE}/blog/paint-fence", 1, 120, 9.0),
    row("fence painting service near me", f"{SITE}/blog/paint-fence", 0, 150, 18.0),
    row("shoptest fence paint", f"{SITE}/", 50, 200, 1.0),
    row("can you paint a fence in winter when it is cold and wet outside", f"{SITE}/blog/winter", 0, 15, 22.0),
]
PAGES = [
    {"page": f"{SITE}/blog/paint-fence", "clicks": 120, "impressions": 4000, "ctr": 0.03, "position": 9.0},
    {"page": f"{SITE}/services/fence-painting", "clicks": 15, "impressions": 1000, "ctr": 0.015, "position": 12.0},
    {"page": f"{SITE}/blog/old-post", "clicks": 60, "impressions": 3000, "ctr": 0.02, "position": 8.0},
]
PAGES_PREV = [
    {"page": f"{SITE}/blog/paint-fence", "clicks": 110, "impressions": 3800, "ctr": 0.029, "position": 9.2},
    {"page": f"{SITE}/blog/old-post", "clicks": 300, "impressions": 3500, "ctr": 0.085, "position": 4.0},
]


class RegexAndCaveats(unittest.TestCase):
    def test_re2_validation(self):
        self.assertIsNone(RX.validate(RX.get("R-CONV")))
        self.assertIn("lookahead", RX.validate("^(?!brand).*"))
        self.assertIn("backreferences", RX.validate(r"(a)\1"))
        for pid, (_, pat, _) in RX.PATTERNS.items():
            self.assertIsNone(RX.validate(pat), pid)

    def test_brand_intent_page_kind(self):
        br = RX.brand_regex({"client": "Shop Test", "client_aliases": ["shoptest"]}, "shop.test")
        self.assertTrue(RX.is_brand("shoptest fence paint", br))
        self.assertTrue(RX.is_brand("shop test reviews", br))
        self.assertFalse(RX.is_brand("fence paint", br))
        self.assertEqual(RX.intent("buy fence paint"), "R-TRANS")
        self.assertEqual(RX.page_kind(f"{SITE}/blog/x"), "blog")
        self.assertEqual(RX.page_kind(f"{SITE}/services/x"), "money")

    def test_caveats_switch_to_clicks_across_the_bug(self):
        self.assertEqual(CV.metric_for(("2025-10-01", "2025-12-31"), ("2025-07-01", "2025-09-30")), "clicks")
        self.assertEqual(CV.metric_for(("2026-08-01", "2026-10-30"), ("2026-05-01", "2026-07-31")), "impressions")


class Analyses(unittest.TestCase):
    br = r"\b(shoptest)\b"

    def test_curve_is_monotonic_with_fallback(self):
        c = A.ctr_curve(QP)
        vals = [c["curve"][p] for p in range(1, 11)]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertEqual(c["site_points"], 0)  # too little data: fallback, never a fixed old industry table

    def test_striking_routes_and_brand_excluded(self):
        s = A.striking(QP, (4, 20), 100, self.br)
        q = {r["query"]: r for r in s}
        self.assertEqual(q["how to paint a fence"]["route"], "cannibalisation")
        self.assertEqual(q["fence paint drying time"]["route"], "on_page")
        self.assertNotIn("shoptest fence paint", q)

    def test_page_optimizer_user_workflow(self):
        opt = A.page_optimizer(PAGES, QP, 20, 500, self.br)
        top = next(p for p in opt if p["page"].endswith("/blog/paint-fence"))
        self.assertIn("best fence paint", [r["query"] for r in top["should_rank"]])
        self.assertIn("what is the best fence paint for wood", [r["query"] for r in top["questions"]])
        self.assertIsNotNone(top["anonymised_share"])

    def test_questions_update_vs_new(self):
        q = A.questions(QP)
        self.assertIn("how to paint a fence", [r["query"] for r in q["update"]])
        self.assertIn("can you paint a fence in winter when it is cold and wet outside", [r["query"] for r in q["update"] + q["new"]])

    def test_cannibalisation_blog_vs_money_action(self):
        c = A.cannibalisation(QP, 100, 0.15, self.br, home=f"{SITE}/")
        self.assertEqual(c[0]["query"], "how to paint a fence")
        self.assertIn("de-optimise the informational page", c[0]["action"])

    def test_decay_and_cause(self):
        d = A.decay(PAGES, PAGES_PREV)
        self.assertEqual(len(d), 1)
        self.assertTrue(d[0]["page"].endswith("/old-post"))
        self.assertIn("position loss", d[0]["cause"])

    def test_decoupling(self):
        cur = [{"page": "p", "clicks": 20, "impressions": 4000, "ctr": 0.005, "position": 2.0}]
        yoy = [{"page": "p", "clicks": 40, "impressions": 2000, "ctr": 0.02, "position": 2.2}]
        self.assertEqual(len(A.decoupling(cur, yoy)), 1)

    def test_coverage_conversational_alignment(self):
        cov = A.topical_coverage(QP, QP[:2])
        blog = next(r for r in cov if r["folder"] == "/blog/")
        self.assertGreater(blog["new_queries"], 0)
        self.assertEqual(len(A.conversational(QP)), 1)
        self.assertIn("commercial query on an informational page", [a["issue"] for a in A.alignment(QP, 50)])


class Indexing(unittest.TestCase):
    def insp(self, state, gc=None, uc=None, days=10, fetch="SUCCESSFUL"):
        t = (date.today() - timedelta(days=days)).isoformat() + "T00:00:00Z"
        return {"inspectionResult": {"indexStatusResult": {"coverageState": state, "googleCanonical": gc, "userCanonical": uc,
                                                           "lastCrawlTime": t, "pageFetchState": fetch, "verdict": "NEUTRAL"}}}

    def test_routes(self):
        n = IX.norm_inspection(self.insp("Crawled - currently not indexed"))
        self.assertEqual(IX.route(n)[0], "ccni")
        self.assertEqual(IX.route(IX.norm_inspection(self.insp("Soft 404")))[1], "IX1")
        self.assertEqual(IX.route(IX.norm_inspection(self.insp("Duplicate, Google chose different canonical than user")))[1], "IX3")
        self.assertEqual(IX.route({"coverage_state": "x", "pageFetchState": "SERVER_ERROR"} | {})[0], "technical")

    def test_ccni_branches(self):
        n = IX.norm_inspection(self.insp("Crawled - currently not indexed"))
        a = IX.triage_ccni(f"{SITE}/blog/a", n, 500, [row("q one", "", 1, 100, 12)])
        self.assertEqual(a["branch"], "A")
        self.assertEqual(a["queries"], ["q one"])
        self.assertEqual(IX.triage_ccni(f"{SITE}/blog/b", n, 0, [])["branch"], "B")
        self.assertEqual(IX.triage_ccni(f"{SITE}/tag/x", n, 0, [])["branch"], "not-wanted")
        dup = IX.norm_inspection(self.insp("Crawled - currently not indexed", gc=f"{SITE}/other"))
        self.assertEqual(IX.triage_ccni(f"{SITE}/blog/c", dup, 0, [])["branch"], "duplicate")

    def test_snake_case_server_output(self):
        n = IX.norm_inspection({"index_verdict": "PASS", "coverage_state": "Submitted and indexed", "google_canonical": "x"})
        self.assertEqual(n["coverageState"], "Submitted and indexed")
        self.assertEqual(IX.route(n)[0], "indexed")

    def test_site_gate(self):
        items = {}
        for i, tpl in enumerate(["a", "b", "c", "d"] * 6):
            items[f"{SITE}/{tpl}/p{i}"] = self.insp("Crawled - currently not indexed" if i % 3 else "Submitted and indexed")
        s = IX.summary(items, {}, [])
        self.assertIsNotNone(s["site_gate"])
        self.assertEqual(s["inspected"], 24)


class CrawlAndRobots(unittest.TestCase):
    def test_classifier(self):
        self.assertEqual(CR.classify("https://x.test/a?_rsc=1x2"), "rsc")
        self.assertEqual(CR.classify("https://x.test/_next/static/chunks/a.js"), "next_static")
        self.assertEqual(CR.classify("https://x.test/blog/opengraph-image?abc"), "og_image")
        self.assertEqual(CR.classify("https://x.test/search?q=paint"), "search")
        self.assertEqual(CR.classify("https://x.test/fonts/a.woff2"), "font")
        self.assertEqual(CR.classify("https://x.test/blog/post"), "page")

    def test_google_robots_semantics(self):
        p = CR.parse_robots("User-agent: *\nDisallow: /private\n\nUser-agent: Googlebot\nDisallow: /search\nAllow: /search/help$\n")
        self.assertTrue(CR.allowed(p, "https://x.test/private/a")[0])  # the Googlebot group replaces *
        self.assertFalse(CR.allowed(p, "https://x.test/search?q=1")[0])
        self.assertTrue(CR.allowed(p, "https://x.test/search/help")[0])
        self.assertFalse(CR.allowed(p, "https://x.test/search/help/more")[0])
        p2 = CR.parse_robots("User-agent: *\nDisallow: /a\nAllow: /a\n")
        self.assertTrue(CR.allowed(p2, "https://x.test/a")[0])  # tie: Allow wins

    def test_export_analysis_never_blocks_rendering_or_important_urls(self):
        text = ("Total crawl requests 18.1K\nAverage response time 840 ms\nHTML 8%\nOther file type 87%\nDiscovery 22%\n"
                "https://x.test/?_rsc=a1\nhttps://x.test/shop?_rsc=b2\nhttps://x.test/_next/static/chunks/main.js\n"
                "https://x.test/search?q=x\n")
        ex = CR.parse_export(text)
        self.assertEqual(ex["summary"]["requests"], 18100)
        res = CR.analyse(ex, {}, ["https://x.test/", "https://x.test/shop", "https://x.test/_next/static/chunks/main.js"], "")
        self.assertTrue(any("Other file type" in n for n in res["notes"]))
        self.assertTrue(any("600 ms" in n for n in res["notes"]))
        self.assertIn("Disallow: /*?_rsc=", res["robots_proposal"])
        self.assertFalse(any("_next/static" in r for r in res["robots_proposal"]))
        self.assertEqual(res["robots_test"]["would_block"], [])

    def test_bad_rule_rejected(self):
        t = CR.test_rules("User-agent: *\n", ["Disallow: /shop"], ["https://x.test/shop/fence-paint"])
        self.assertTrue(t["verdict"].startswith("REJECTED"))


class StoreBusIngestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gsc-test-")
        os.environ["SEO_SITES_DIR"] = self.tmp
        from seolib.gsc import store as S
        self.S = S
        S.save("t1", "query_page", rows=QP, meta={"source": "test", "window": ["2026-08-01", "2026-10-29"]})
        S.save("t1", "pages", rows=PAGES, meta={"source": "test"})
        S.save("t1", "pages_prev", rows=PAGES_PREV, meta={"source": "test"})

    def tearDown(self):
        os.environ.pop("SEO_SITES_DIR", None)

    def test_ingest_shapes(self):
        from seolib.gsc import mcp
        d = Path(self.tmp)
        (d / "api.json").write_text(json.dumps({"rows": [{"keys": ["q a", "https://s.test/a"], "clicks": 3, "impressions": 30,
                                                          "ctr": 0.1, "position": 4.2}]}), encoding="utf-8")
        self.assertEqual(mcp.ingest("t2", "query_page", str(d / "api.json"))["rows"], 1)
        (d / "list.json").write_text(json.dumps({"content": [{"type": "text", "text": "x"}], "data": [
            {"Query": "Q B", "Page": "https://s.test/b", "Clicks": "5", "Impressions": "50", "CTR": "10%", "Position": "3.1"}]}),
            encoding="utf-8")
        mcp.ingest("t2", "query_page", str(d / "list.json"))
        r = self.S.rows("t2", "query_page")[0]
        self.assertEqual((r["query"], r["clicks"], r["ctr"]), ("q b", 5, 0.1))
        (d / "ui.csv").write_text("Top queries,Clicks,Impressions,CTR,Position\nfence paint,12,400,3%,6.5\n", encoding="utf-8")
        self.assertEqual(mcp.ingest("t2", "queries", str(d / "ui.csv"))["source"], "csv")
        (d / "empty.json").write_text(json.dumps({"rows": [{"keys": ["x"]}]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            mcp.ingest("t2", "queries", str(d / "empty.json"))
        (d / "insp.json").write_text(json.dumps([{"url": "https://s.test/a", "coverage_state": "Soft 404"}]), encoding="utf-8")
        mcp.ingest("t2", "inspections", str(d / "insp.json"))
        self.assertIn("https://s.test/a", self.S.load("t2", "inspections")["items"])

    def test_fetch_plan_has_every_dataset(self):
        from seolib.gsc import mcp
        plan = mcp.fetch_plan("t1")
        self.assertEqual({p["dataset"] for p in plan}, set(self.S.DATASETS))
        disc = next(p for p in plan if p["dataset"] == "discover")
        self.assertNotIn("query", disc["params"]["dimensions"])  # Discover has no query dimension

    def test_bus_views_and_page(self):
        from seolib.gsc.bus import Console, VIEWS
        g = Console("t1", {"domain": "shop.test"})
        p = g.page(f"{SITE}/blog/paint-fence")
        self.assertEqual(p["queries"], 5)
        self.assertTrue(p["cannibalisation"])
        self.assertTrue(g.topic("fence paint", exclude=f"{SITE}/blog/paint-fence"))
        for v in VIEWS:
            if v not in ("page", "query", "topic"):
                g.view(v)  # every view runs on partial data without raising

    def test_audit_actions_and_queue_rows(self):
        from seolib.gsc import audit
        audit._headings = lambda urls: {u: "how to paint a fence" for u in urls}
        o = audit.run("t1")
        kinds = {a["playbook"] for a in o["actions"]}
        self.assertIn("U-B", kinds)
        self.assertIn("PF10", kinds)
        self.assertTrue((Path(self.tmp) / "t1" / "gsc" / "audit.md").exists())
        captured = {}
        import seolib.batch as B
        orig = B.setup
        B.setup = lambda slug, **kw: captured.update(kw) or "plan.json"
        try:
            self.assertEqual(audit.queue("t1", ["optimizer"], 5), "plan.json")
        finally:
            B.setup = orig
        self.assertTrue(all(r["instructions"].startswith("Search Console (U-B)") for r in captured["rows"]))

    def test_change_log_and_impact(self):
        from seolib.gsc.bus import Console
        old = (date.today() - timedelta(days=60)).isoformat()
        p = self.S.site_dir("t1") / "changelog.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"entries": [{"date": old, "url": f"{SITE}/blog/old-post", "kind": "rewrite written",
                                              "baseline": {"clicks": 300, "position": 4.0}}]}), encoding="utf-8")
        imp = Console("t1").view("impact")
        self.assertEqual(imp[0]["clicks_now"], 60)

    def test_gsc_insights_reads_the_store_and_passes_links(self):
        from seolib.harness import Ctx
        rd = Path(tempfile.mkdtemp(prefix="gsc-run-"))
        brief = {"page_url": f"{SITE}/blog/paint-fence", "target_query": "how to paint a fence", "domain": "shop.test",
                 "task": "rewrite", "connectors": "auto", "site_inventory": str(Path(self.tmp) / "t1" / "inventory.json")}
        ctx = Ctx(brief, rd, "deep")
        spec = importlib.util.spec_from_file_location("t_gsc", ROOT / "plugins" / "gsc_insights" / "run.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = mod.run(ctx)
        self.assertEqual(out["source"], "store")
        self.assertIn("what is the best fence paint for wood", [r["query"] for r in out["questions"]])
        self.assertTrue(out["link_targets"])
        self.assertIn("how to paint a fence", out["cannibalisation"])


class Routing(unittest.TestCase):
    def test_only_explicit_requests_route(self):
        from seolib.gsc.cli import ROUTE
        import re

        def routed(t):
            m = ROUTE.match(t)
            if not m:
                return False
            rest = (m.group("rest") or "").strip().lower()
            return bool(re.match(r"(audit|queue|crawl|page|inspect)\b", rest) or (m.group("site") and not rest))
        self.assertTrue(routed("example.com | gsc"))
        self.assertTrue(routed("example.com | gsc queue optimizer 10"))
        self.assertTrue(routed("gsc: audit"))
        self.assertFalse(routed("google search console tutorial"))
        self.assertFalse(routed("nutmeg: what is a lifetime isa"))


if __name__ == "__main__":
    unittest.main()
