"""Website intake, queue and JSON handoff regressions. Synthetic sources only; never start content runs."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from test_pipeline_regressions import OfflineCase, sheet
from seolib import common as C, article_context as AC, batch, driver, kgdoc, outline, pagetype, sitecontext as SC

REPO = Path(__file__).resolve().parents[1]


def plugin(name):
    spec = importlib.util.spec_from_file_location("test_plugin_" + name, REPO / "plugins" / name / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextOfflineCase(OfflineCase):
    def setUp(self):
        super().setUp()
        async def forbidden(*args, **kwargs):
            raise AssertionError("Unexpected fetch in context regression; stub sources explicitly")
        p = patch.object(C, "fetch_many", forbidden)
        p.start()
        self.addCleanup(p.stop)


class ContextTests(ContextOfflineCase):
    def profile(self, slug="acme", domain="acme.example"):
        p = self.root / "clients" / (slug + ".yaml")
        p.parent.mkdir(exist_ok=True)
        p.write_text(yaml.safe_dump({"client": slug.title(), "domain": domain, "locale": "en-GB", "blog_path": "/blog/"}))
        return p

    def test_single_saved_client_is_a_default(self):
        self.profile()
        self.assertEqual(SC.resolve_client()[0], "acme")

    def test_no_client_or_multiple_clients_requires_a_website(self):
        self.assertIsNone(SC.resolve_client())
        self.profile()
        self.profile("other", "other.example")
        self.assertIsNone(SC.resolve_client())

    def test_bound_context_wins_and_checks_domain(self):
        self.profile()
        self.profile("other", "other.example")
        path = SC.bind_client("other")
        self.assertEqual(SC.resolve_client()[0], "other")
        path.write_text("client_slug: other\ndomain: acme.example\n")
        with self.assertRaisesRegex(ValueError, "disagree"):
            SC.resolve_client()

    def test_host_matching_is_exact_and_full_host_slugs_do_not_collide(self):
        self.profile("acme", "acme.com")
        self.assertEqual(SC.client_for_website("https://www.acme.com/help")[0], "acme")
        self.assertFalse(SC.client_for_website("acme.com.evil.example")[1])
        self.assertNotEqual(SC.client_for_website("acme.org")[0], SC.client_for_website("acme.com")[0])

    def test_keyword_only_and_single_word_use_configured_site(self):
        self.profile()
        with patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()):
            driver.start("tax")
        brief = C.load_yaml(self.root / nxt.call_args.args[0])
        self.assertEqual(brief["target_query"], "tax")
        self.assertEqual(brief["domain"], "acme.example")

    def test_missing_site_stops_before_any_run(self):
        with patch.object(driver, "next_step") as nxt, self.assertRaisesRegex(SystemExit, "NEED A CLIENT"):
            driver.start("tax advice")
        nxt.assert_not_called()

    def test_url_and_bare_domain_route_to_intake(self):
        for request in ("acme.example", "https://acme.example/", "acme.example/services/help", "rewrite https://acme.example/blog/help"):
            with self.subTest(request=request), patch.object(driver, "start_from_page") as intake:
                driver.start(request)
                intake.assert_called_once()

    def test_domain_plus_keyword_preserves_keyword_and_instructions(self):
        self.profile()
        with patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()):
            driver.start("https://acme.example/: visa help | service page")
        brief = C.load_yaml(self.root / nxt.call_args.args[0])
        self.assertEqual(brief["target_query"], "visa help")
        self.assertEqual(brief["page_type"], "service")

    def test_keyword_match_routes_existing_page_and_preserves_operator_query(self):
        self.profile()
        C.save_json(SC.inventory_path("acme"), {"pages": [{"url": "https://acme.example/help", "target_query": "visa help"}]})
        with patch.object(driver, "start_from_page") as intake:
            driver.start("visa help")
        self.assertEqual(intake.call_args.kwargs["target_query"], "visa help")

    def test_project_binding_wins_over_a_keyword_brief_for_another_client(self):
        self.profile()
        self.profile("other", "other.example")
        SC.bind_client("other")
        from seolib.briefgen import make_brief
        with contextlib.redirect_stdout(io.StringIO()):
            make_brief("acme", "visa help")
        with patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()):
            driver.start("visa help")
        self.assertEqual(C.load_yaml(self.root / nxt.call_args.args[0])["domain"], "other.example")

    def test_ambiguous_page_matches_stop_intake_and_block_batch(self):
        self.profile()
        C.save_json(SC.inventory_path("acme"), {"pages": [{"target_query": "visa help", "url": "https://acme.example/" + p} for p in ("a", "b")]})
        with self.assertRaisesRegex(SystemExit, "NEED A PAGE"), contextlib.redirect_stdout(io.StringIO()):
            driver.start("visa help")
        path = batch.prepare("acme", [{"keyword": "visa help"}])
        self.assertEqual(C.load_json(path)["items"][0]["status"], "blocked")

    def test_batch_remembers_quick_mode_when_advancing_pages(self):
        self.profile()
        with contextlib.redirect_stdout(io.StringIO()):
            path = batch.prepare("acme", [{"keyword": "visa help"}, {"keyword": "visa cost"}])
        with patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()):
            batch.next_page(str(path), "quick")
            item = C.load_json(path)["items"][0]
            batch.next_page(str(path), completed={"id": item["id"], "result": "result.md"})
        self.assertEqual(nxt.call_args.args[1], "quick")

    def test_printed_batch_task_commands_quote_brief_paths_with_spaces(self):
        path = str(self.root / "briefs" / "visa-help.yaml")
        output = io.StringIO()
        with patch("seolib.prep.load_brief", return_value={}), patch.object(driver, "_current_run", return_value=None), contextlib.redirect_stdout(output):
            driver._task("EDITOR", ["Edit the draft"], path, confirm="editor")
        self.assertIn(f"done {driver.ARG(path)} editor", output.getvalue())
        self.assertIn(f"next {driver.ARG(path)}", output.getvalue())
        self.assertNotIn(f"next {path}\n", output.getvalue())

    def test_ambiguous_keyword_mapping_does_not_choose_arbitrarily(self):
        pages = [{"target_query": "visa help", "url": "https://acme.example/" + p} for p in ("a", "b")]
        self.assertIsNone(SC.match_keyword("visa help", {"pages": pages}))

    def test_discovery_resumes_cap_reads_links_and_respects_robots(self):
        self.profile()
        home = "https://acme.example/"
        a, b, blocked = home + "services/help", home + "blog/news", home + "private"
        markup = lambda title, links="": "<main><h1>" + title + "</h1><p>" + "We provide help for your application and explain the process. " * 12 + "</p>" + links + "</main>"
        bodies = {home: markup("Acme", f'<a href="{a}">Help</a><a href="{blocked}">Private</a>'), a: markup("Visa help"), b: markup("How applications work")}
        calls = []
        async def fetch(reqs, *args, **kwargs):
            calls.extend(r["url"] for r in reqs)
            results = {}
            for r in reqs:
                u = r["url"]
                if u.endswith("robots.txt"):
                    results[u] = {"status": 200, "state": "ok", "raw": "User-agent: *\nDisallow: /private\n"}
                elif u.endswith("sitemap.xml"):
                    results[u] = {"status": 200, "is_index": False, "locs": [a, b, blocked]}
                elif u in bodies:
                    results[u] = {"status": 200, "state": "ok", "raw": bodies[u], "final_url": u}
                else:
                    results[u] = {"status": 404, "state": "error"}
            return results
        with patch.object(C, "fetch_many", fetch), patch("seolib.spider.api_key", return_value=None):
            first = SC.discover("acme", max_pages=1)
            self.assertFalse(first["discovery_complete"])
            second = SC.discover("acme", max_pages=10)
        self.assertEqual({p["url"] for p in second["pages"]}, {home, a, b})
        self.assertNotIn(blocked, calls)
        self.assertTrue(second["discovery_complete"])
        self.assertTrue(any(g["reason"] == "robots_disallowed" for g in second["gaps"]))

    def test_thin_pages_render_once_and_unavailable_pages_remain_gaps(self):
        self.profile()
        home = "https://acme.example/"
        async def fetch(reqs, *args, **kwargs):
            return {r["url"]: ({"status": 200, "state": "ok", "raw": "<main><h1>Acme</h1></main>"}
                               if r["url"] == home else {"status": 404, "state": "error"}) for r in reqs}
        render = {home: {"state": "ok", "status": 200, "blocks": [["h1", "Visa service"], ["p", "help " * 90]], "words": 90,
                         "text": "We review visa documents.", "title": "Visa service", "via": "spider"}}
        with patch.object(C, "fetch_many", fetch), patch("seolib.spider.api_key", return_value="fake"), patch("seolib.spider.scrape_many", return_value=render) as scrape:
            good = SC.discover("acme", 1)
        scrape.assert_called_once()
        self.assertFalse(good["gaps"])
        self.assertIn("review visa", good["source_context"]["published_purpose_excerpt"])
        with patch.object(C, "fetch_many", fetch), patch("seolib.spider.api_key", return_value=None):
            bad = SC.discover("acme", 1, refresh=True)
        self.assertFalse(bad["discovery_complete"])
        self.assertEqual(bad["gaps"][0]["reason"], "thin_or_js_page")

    def test_failed_child_sitemap_remains_retryable_and_recovers(self):
        self.profile()
        home = "https://acme.example/"
        child, page = home + "pages-sitemap.xml", home + "visa-help"
        failed = True
        async def fetch(reqs, *args, **kwargs):
            out = {}
            for r in reqs:
                u = r["url"]
                if u == home + "sitemap.xml":
                    out[u] = {"status": 200, "is_index": True, "locs": [child]}
                elif u == child:
                    out[u] = {"status": 503, "state": "error"} if failed else {"status": 200, "is_index": False, "locs": [page]}
                elif u in (home, page):
                    out[u] = {"status": 200, "state": "ok", "raw": "<main><h1>Visa help</h1><p>" + "word " * 100 + "</p></main>"}
                else:
                    out[u] = {"status": 404, "state": "error"}
            return out
        with patch.object(C, "fetch_many", fetch):
            first = SC.discover("acme")
            self.assertFalse(first["discovery_complete"])
            self.assertIn(child, first["sitemap_frontier"])
            failed = False
            second = SC.discover("acme")
        self.assertTrue(second["discovery_complete"])
        self.assertIn(page, [p["url"] for p in second["pages"]])
        self.assertFalse(second["gaps"])

    def test_blocked_pages_are_never_rendered(self):
        self.profile()
        async def fetch(reqs, *args, **kwargs):
            return {r["url"]: {"status": 403, "state": "blocked", "raw": "Access denied"} for r in reqs}
        with patch.object(C, "fetch_many", fetch), patch("seolib.spider.scrape_many") as scrape:
            data = SC.discover("acme", 1)
        scrape.assert_not_called()
        self.assertFalse(data["discovery_complete"])
        self.assertFalse(data["pages"])

    def test_unreadable_live_url_does_not_become_a_new_page(self):
        self.profile()
        url = "https://acme.example/services/help"
        info = {"exists": False, "status": 403, "read_state": "blocked", "page_url": url,
                "target_query": "visa help", "page_type": "guide", "evidence": []}
        with patch.object(pagetype, "intake", return_value=info), patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit, "NEED A PAGE"):
            driver.start_from_page(url, "")
        nxt.assert_not_called()
        with patch.object(pagetype, "intake", return_value=info):
            path = batch.prepare("acme", [{"url": url, "keyword": "visa help"}])
        self.assertEqual(C.load_json(path)["items"][0]["status"], "blocked")
        with patch.object(pagetype, "intake", return_value=info), contextlib.redirect_stdout(io.StringIO()):
            path = batch.prepare("acme", [{"url": url, "keyword": "visa help", "page_type": "service"}])
        self.assertEqual(C.load_json(path)["items"][0]["task"], "rewrite")

    def test_batch_deduplicates_url_queries_preserves_types_and_resumes(self):
        self.profile()
        url = "https://acme.example/help"
        C.save_json(SC.inventory_path("acme"), {"discovery_complete": True, "source_context": {"purpose": "visa help"},
            "pages": [{"url": url, "target_query": "visa help", "page_type": "service", "words": 100}]})
        rows = [{"url": url, "keyword": "visa help"}, {"url": url, "keyword": "visa assistance"},
                {"keyword": "visa rules", "page_type": "hub"}]
        with contextlib.redirect_stdout(io.StringIO()):
            path = batch.prepare("acme", rows)
        plan = C.load_json(path)
        self.assertEqual(len(plan["items"]), 2)
        self.assertEqual(plan["items"][0]["secondary_queries"], ["visa assistance"])
        self.assertEqual(plan["items"][1]["page_type"], "hub")
        with patch.object(driver, "next_step") as nxt, contextlib.redirect_stdout(io.StringIO()):
            batch.next_page(str(path))
            batch.next_page(str(path))
            self.assertEqual(nxt.call_args_list[0], nxt.call_args_list[1])
            batch.next_page(str(path), completed={"id": plan["items"][0]["id"], "result": "result.md"})
        self.assertEqual(C.load_json(path)["items"][0]["status"], "complete")
        self.assertEqual(batch.prepare("acme", rows), path)
        brief = C.load_yaml(plan["items"][0]["brief"])
        self.assertEqual(brief["source_context"]["purpose"], "visa help")

    def test_batch_rejects_foreign_pages_and_conflicting_types(self):
        self.profile()
        with self.assertRaisesRegex(ValueError, "outside"):
            batch.prepare("acme", [{"url": "https://other.example/page"}])
        url = "https://acme.example/help"
        C.save_json(SC.inventory_path("acme"), {"pages": [{"url": url, "target_query": "visa help", "page_type": "service"}]})
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            batch.prepare("acme", [{"url": url, "type": "service"}, {"url": url, "type": "guide"}])

    def test_list_formats_and_adapter_inline_syntax(self):
        for filename, text in (("k.txt", "visa help\nvisa cost"), ("k.csv", "keyword,page_type\nvisa help,service\nvisa cost,guide"),
                               ("k.json", '["visa help", "visa cost"]'), ("k.yaml", "keywords:\n- visa help\n- visa cost")):
            p = self.root / filename
            p.write_text(text)
            self.assertEqual(len(batch.read_list(str(p))), 2)
        with patch.object(batch, "setup") as setup:
            self.assertTrue(batch.route_request("acme.example | keywords: visa help; visa cost"))
        self.assertEqual(setup.call_args.args[0], "acme.example")
        self.assertEqual(len(setup.call_args.kwargs["rows"]), 2)

    def test_missing_list_file_is_not_treated_as_a_keyword(self):
        with patch.object(batch, "setup") as setup, self.assertRaises(FileNotFoundError):
            batch.route_request("acme.example | keywords: missing.csv")
        setup.assert_not_called()

    def test_a_url_in_a_keyword_list_still_gets_page_intake(self):
        self.profile()
        url = "https://acme.example/services/help"
        page = {"page_url": url, "target_query": "visa help", "page_type": "service", "exists": True}
        with patch.object(pagetype, "intake", return_value=page) as intake, contextlib.redirect_stdout(io.StringIO()):
            path = batch.prepare("acme", [{"keyword": url}])
        intake.assert_called_once_with(url)
        self.assertEqual(C.load_json(path)["items"][0]["page_type"], "service")


class HandoffTests(ContextOfflineCase):
    def research(self):
        rd = self.root / "synthetic"
        data = sheet("service")
        data["brief"]["target_query"] = "visa service cost"
        data["facts"] = [{"id": "fee:1", "claim": "Visa service cost", "value": "40", "status": "verified", "source_url": "https://source.example/fees"}]
        C.save_json(rd / "fact_sheet.json", data)
        C.save_json(rd / "research" / "serp_intel.json", {"organic": [{"link": "https://source.example/fees", "position": 1}, {"link": "https://unread.example/", "position": 2}],
            "paa": ["Can a child apply?"], "paa_answers": {"Can a child apply?": {"link": "https://source.example/fees"}}, "related": ["visa processing times"]})
        C.save_json(rd / "research" / "competitor_scrape.json", {"pages": [{"url": "https://source.example/fees", "domain": "source.example", "blocks": [["p", "Visa assistance costs 40 pounds."]]}]})
        C.save_json(rd / "research" / "semantic_graph.json", {"graph": {"entities": [{"name": "Visa", "domains": ["source.example"]}], "relations": [
            {"example": {"sentence": "Visa assistance costs 40 pounds.", "source": "https://source.example/fees"}}],
            "attributes": [{"values": [{"value": "40", "example": {"sentence": "Visa assistance costs 40 pounds.", "source": "source.example"}}]}]}})
        C.save_json(rd / "research" / "topic_outline.json", {"sections": [
            {"id": "S1", "title": "What is a visa", "pos": 0, "covered_by": ["a", "b"]},
            {"id": "S2", "title": "Visa service costs and fees", "pos": .9, "covered_by": ["a", "b"], "questions": []}]})
        C.save_json(rd / "research" / "query_map.json", {"h2_questions": ["Which documents are needed?"], "queries": []})
        return rd

    def test_context_retains_eav_relations_provenance_demand_and_gaps(self):
        rd = self.research()
        context = AC.build(rd)
        self.assertEqual(context["sections"][0]["id"], "S2")
        self.assertEqual(context["source_coverage"]["organic_results_read"], 1)
        self.assertEqual(context["source_coverage"]["organic_results_unread"][0]["reason"], "not_read")
        self.assertEqual(len(context["semantic_inventory"]["relations"][0]["evidence_refs"]), 1)
        self.assertEqual(len(context["semantic_inventory"]["attributes"][0]["values"][0]["evidence_refs"]), 1)
        self.assertEqual(context["semantic_inventory"]["entities"][0]["source_urls"], ["https://source.example/fees"])
        self.assertIn("Can a child apply?", [q["text"] for q in context["coverage_requirements"]])
        self.assertIn("Which documents are needed?", [q["text"] for q in context["coverage_requirements"] if q["required"]])
        self.assertNotIn("blocks", context["source_pages"][0])
        self.assertEqual(context["source_pages"][0]["block_count"], 1)

    def test_handoff_cache_and_default_do_not_rebuild_markdown(self):
        rd = self.research()
        kgdoc.write_docs(rd)
        self.assertTrue((rd / "article_context.json").exists())
        self.assertFalse((rd / "knowledge_graph.md").exists())
        with patch.object(C, "save_json", wraps=C.save_json) as save:
            kgdoc.write_docs(rd)
        save.assert_not_called()
        data = C.load_json(rd / "fact_sheet.json")
        data["facts"][0]["value"] = "45"
        C.save_json(rd / "fact_sheet.json", data)
        self.assertEqual(AC.build(rd)["usable_facts"][0]["value"], "45")

    def test_json_handoff_preserves_derived_signals_and_search_features(self):
        rd = self.research()
        semantic = C.load_json(rd / "research" / "semantic_graph.json")
        semantic["consensus_figures"] = [{"value": "40 pounds", "domains": ["a", "b"]}]
        semantic["paa_gaps"] = ["Can a child apply?"]
        C.save_json(rd / "research" / "semantic_graph.json", semantic)
        serp = C.load_json(rd / "research" / "serp_intel.json")
        serp["features"] = {"places": True}
        C.save_json(rd / "research" / "serp_intel.json", serp)
        context = AC.build(rd)
        self.assertEqual(context["research_signals"]["consensus_figures"], semantic["consensus_figures"])
        self.assertEqual(context["research_signals"]["paa_gaps"], semantic["paa_gaps"])
        self.assertTrue(context["search_demand"]["features"]["places"])

    def test_required_coverage_accepts_body_placement_and_explicit_exclusion(self):
        rd = self.research()
        context = AC.build(rd)
        text = "# Visa service cost\nPage job: service; offer:1; next step not verified\n## Costs and eligibility\n"
        p = rd / "outline.md"
        p.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(outline.check_outline(rd))
        text += "\n".join(f"Coverage: {item['id']} — body under Costs and eligibility; {item['text']}" for item in context["coverage_requirements"] if item["required"])
        p.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(outline.check_outline(rd))
        self.assertTrue(C.load_json(rd / "research" / "coverage_plan.json")["items"])

    def test_editor_cannot_omit_required_coverage_records(self):
        rd = self.research()
        context = AC.build(rd)
        text = "## Claim ledger\nOne factual line\nTwo factual lines\nThree factual lines\n## Page job\nService offer\n"
        self.assertTrue(any("Coverage" in e for e in driver._gate("editor", rd, text)))
        text += "## Coverage\n" + "\n".join(f"{c['id']}: body under Costs and eligibility; checked" for c in context["coverage_requirements"] if c["required"])
        self.assertFalse(driver._gate("editor", rd, text))

    def test_main_task_order_is_not_competitor_median_order(self):
        sections = [{"id": "S1", "title": "Definition", "pos": 0}, {"id": "S2", "title": "Refusal risks", "pos": 1}]
        result = AC.prioritise(sections, {"target_query": "visa rejection risks", "page_type": "guide"})
        self.assertEqual(result[0]["id"], "S2")
        self.assertEqual(sections[0]["title"], "Definition")

    def test_top_ten_and_paa_related_sources_share_one_render_wave(self):
        mod = plugin("competitor_scrape")
        organic = [{"link": f"https://s{i}.example/page", "domain": f"s{i}.example", "kind": "publisher", "position": i, "title": str(i)} for i in range(1, 11)]
        serp = {"organic": organic, "paa_answers": {"Question?": {"link": "https://paa.example/answer"}},
                "expansions": {"related query": {"source": "related", "organic": ["https://related.example/page"]}}}
        ctx = SimpleNamespace(brief={"domain": "acme.example", "locale": "en-GB"}, refresh=True, deep=lambda: True, load=lambda n: serp)
        def render(urls, **kwargs):
            return {u: {"state": "ok", "status": 200, "words": 100, "blocks": [["h2", "Costs"], ["p", "The fee is listed for your application."]], "via": "spider"} for u in urls}
        with patch("seolib.spider.api_key", return_value="fake"), patch("seolib.spider.scrape_many", side_effect=render) as scrape:
            result = mod.run(ctx)
        self.assertEqual(len(scrape.call_args.args[0]), 12)
        self.assertTrue(scrape.call_args.kwargs["refresh"])
        self.assertEqual(len([p for p in result["pages"] if p["source_role"] == "ranked"]), 10)
        self.assertEqual({p["source_role"] for p in result["pages"]}, {"ranked", "paa_source", "related_search_source"})

    def test_quick_mode_limits_render_work_and_reports_other_organic_pages(self):
        mod = plugin("competitor_scrape")
        serp = {"organic": [{"link": f"https://s{i}.example/", "domain": f"s{i}.example", "kind": "publisher", "position": i} for i in range(10)]}
        ctx = SimpleNamespace(brief={"domain": "acme.example"}, refresh=False, deep=lambda: False, load=lambda n: serp)
        with patch("seolib.spider.api_key", return_value="fake"), patch("seolib.spider.scrape_many", side_effect=lambda urls, **kw: {u: {"state": "ok", "words": 100, "blocks": []} for u in urls}) as scrape:
            result = mod.run(ctx)
        self.assertEqual(len(scrape.call_args.args[0]), 5)
        self.assertEqual(len(result["skipped"]), 5)

    def test_semantic_extraction_is_reused_only_for_identical_inputs(self):
        mod = plugin("semantic_graph")
        sources = {"competitor_scrape": {"pages": [{"url": "https://a.example/", "domain": "a.example", "blocks": [], "outline": []}]}, "serp_intel": {}, "query_map": {}}
        ctx = SimpleNamespace(brief={"target_query": "visa", "locale": "en-GB"}, refresh=False, decisions=[], load=lambda n: sources.get(n, {}))
        graph = {"entities": [], "attributes": [], "relations": [], "central": "visa", "foreign_pages": [], "spacy": False}
        with patch("seolib.graph.build", return_value=graph) as build:
            sources["semantic_graph"] = mod.run(ctx)
            mod.run(ctx)
            self.assertEqual(build.call_count, 1)
            sources["serp_intel"]["paa"] = ["How much does a visa cost?"]
            mod.run(ctx)
            self.assertEqual(build.call_count, 2)

    def test_semantic_budget_is_bounded_and_reports_partial_extraction(self):
        from seolib import graph
        page = {"url": "https://source.example/", "domain": "source.example", "blocks": [
            ["h1", "Visa service"], ["p", "Visa service application documents require careful review before processing. " * 600]]}
        before = copy.deepcopy(page)
        result = graph.build([page], "visa service", "en-GB", use_spacy=False)
        report = result["source_processing"][0]
        self.assertEqual(report["state"], "partial")
        self.assertLessEqual(report["analysed_words"], graph.MAX_WORDS_PER_PAGE)
        self.assertGreater(report["sentences_omitted_by_budget"], 0)
        self.assertEqual(before, page)
