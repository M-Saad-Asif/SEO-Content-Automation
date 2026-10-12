"""Offline regressions. All writes use temporary directories; no SEO run or API is started."""
from __future__ import annotations

import contextlib
import asyncio
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from seolib import common as C, briefgen, driver, offer, pack, pagetype, prep, spider, timing
from seolib.lint import Linter
from seolib.pagejob import is_client_url, lines, next_steps


def sheet(page_type="service"):
    return {"brief": {"client": "Acme", "domain": "acme.example", "page_type": page_type,
                      "page_url": "https://acme.example/visa-help", "target_query": "visa help",
                      "locale": "en-GB", "word_range": [800, 1400]}, "facts": [], "decisions": [],
            "client": {"approved_claims": [], "offer": {
                "offers": [{"text": "Our team reviews visa application documents.", "url": "https://acme.example/visa-help"}],
                "ctas": [{"text": "Get started", "url": "https://acme.example/start"}]}}}


class OfflineCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix=".seo-regression-", dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)
        self.assertTrue(self.root.resolve().is_relative_to(Path(__file__).resolve().parent))
        for attr, value in (("ROOT", self.root), ("CACHE", self.root / "cache"), ("RUNS", self.root / "runs")):
            p = patch.object(C, attr, value)
            p.start()
            self.addCleanup(p.stop)
        # Any accidentally unmocked HTTP request fails locally.
        for target in ("httpx.Client.request", "httpx.AsyncClient.request"):
            p = patch(target, side_effect=AssertionError("Network forbidden in offline regressions"))
            p.start()
            self.addCleanup(p.stop)
        def finish_stub(coro):
            # Fake fetches return immediately; avoid opening even asyncio's Windows loopback socket.
            try:
                coro.send(None)
            except StopIteration as done:
                return done.value
            finally:
                coro.close()
            raise AssertionError("Unexpected asynchronous I/O in an offline regression")
        p = patch.object(C, "run_async", finish_stub)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)


class LockTests(OfflineCase):
    def test_nested_lock_is_fast_and_outer_owner_stays_locked(self):
        target = self.root / "facts.json"
        begin = time.monotonic()
        with C.file_lock(target):
            with C.file_lock(target):
                self.assertTrue(Path(str(target) + ".lock").exists())
            self.assertTrue(Path(str(target) + ".lock").exists())
        self.assertLess(time.monotonic() - begin, 1.0)
        self.assertFalse(Path(str(target) + ".lock").exists())

    def test_threads_do_not_bypass_the_process_lock(self):
        target = self.root / "facts.json"
        entered = threading.Event()
        def contender():
            with C.file_lock(target, timeout=2):
                entered.set()
        with C.file_lock(target):
            thread = threading.Thread(target=contender)
            thread.start()
            self.assertFalse(entered.wait(0.1))
        thread.join(2)
        self.assertTrue(entered.is_set())

    def test_active_process_lock_times_out_without_being_stolen(self):
        target = self.root / "facts.json"
        code = ("import sys; from pathlib import Path; from seolib.common import file_lock; "
                "lock=file_lock(Path(sys.argv[1])); lock.__enter__(); print('ready',flush=True); "
                "sys.stdin.readline(); lock.__exit__()")
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "scripts"))
        process = subprocess.Popen([sys.executable, "-c", code, str(target)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        try:
            self.assertEqual(process.stdout.readline().strip(), "ready")
            with self.assertRaises(TimeoutError):
                with C.file_lock(target, timeout=0.1):
                    self.fail("entered another process's lock")
            self.assertTrue(Path(str(target) + ".lock").exists())
        finally:
            process.communicate("release\n", timeout=5)

    def test_dead_process_lock_is_recovered(self):
        target = self.root / "facts.json"
        Path(str(target) + ".lock").write_text("999999999", encoding="utf-8")
        with patch.object(C, "_pid_alive", return_value=False):
            with C.file_lock(target, timeout=0.2):
                pass

    def test_parallel_json_writers_have_unique_temporary_files(self):
        target = self.root / "cache.json"
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda n: C.save_json(target, {"n": n, "data": "x" * 1000}), range(40)))
        self.assertIn(C.load_json(target)["n"], range(40))
        self.assertEqual(list(self.root.glob("*.tmp")), [])


class IntakeTests(OfflineCase):
    def test_keyword_keeps_parent_task_and_country(self):
        self.assertEqual(pagetype.keyword_from("UK Visa Status Check", "UK Visa Status Check | MasterFastVisas",
                                             "https://masterfastvisas.com/visa-status-check/united-kingdom"),
                         "uk visa status check")

    def test_address_only_keeps_parent_task(self):
        self.assertEqual(pagetype.keyword_from("", "", "https://example.com/visa-status-check/united-kingdom"),
                         "visa status check united kingdom")

    def test_all_explicit_types_are_supported(self):
        for page_type in prep.PAGE_TYPES:
            with self.subTest(page_type=page_type):
                self.assertEqual(pagetype.infer_type("page_type: " + page_type, "how to apply")[0], page_type)

    def test_specific_instructions_win(self):
        self.assertEqual(pagetype.infer_type("location landing page", "boiler service")[0], "location")
        self.assertEqual(pagetype.infer_type("product guide", "laptop bags")[0], "product-guide")
        self.assertEqual(pagetype.infer_type("not a guide; service page", "how to apply")[0], "service")

    def test_informational_queries_stay_guides(self):
        for query in ("what is a mortgage", "visa status check", "boiler repair cost", "best running shoes",
                      "how to use an app", "ISA eligibility"):
            with self.subTest(query=query):
                self.assertEqual(pagetype.infer_type("", query)[0], "guide")

    def test_near_me_is_a_location(self):
        self.assertEqual(pagetype.infer_type("", "plumber near me")[0], "location")

    def test_structural_types_survive_shared_sales_navigation(self):
        doc = {"title": "Acme", "blocks": [["h1", "Our range"], ["p", "Our team can help. Apply now. " * 20]]}
        for url, expected in (("https://acme.example/", "home"),
                              ("https://acme.example/products/red-bag", "product"),
                              ("https://acme.example/collections/bags", "category"),
                              ("https://acme.example/about", "company"),
                              ("https://acme.example/blog/how-to-apply", "guide")):
            with self.subTest(url=url):
                self.assertEqual(pagetype.classify(url, doc)[0], expected)

    def test_short_url_alone_does_not_establish_commercial_purpose(self):
        doc = {"blocks": [["h1", "Visa status check"], ["p", "Check application decisions here."]]}
        self.assertEqual(pagetype.classify("https://example.com/visa-status", doc)[0], "guide")

    def test_retail_blog_product_markup_does_not_make_it_a_product_page(self):
        doc = {"blocks": [["h1", "How to choose bags"], ["p", "Written by Jane Doe. Our team can help."]]}
        self.assertEqual(pagetype.classify("https://acme.example/blog/bag-guide", doc,
                                         '{"@type":"Product"}')[0], "guide")

    def test_brief_defaults_and_validation_cover_all_types(self):
        (self.root / "clients").mkdir()
        (self.root / "clients" / "acme.yaml").write_text(yaml.safe_dump({"client": "Acme", "domain": "acme.example",
                                                                      "locale": "en-GB", "blog_path": "/blog/"}))
        for page_type in prep.PAGE_TYPES:
            with self.subTest(page_type=page_type), contextlib.redirect_stdout(io.StringIO()):
                p = briefgen.make_brief("acme", "visa help", page_type=page_type, slug=page_type)
                data = prep.load_brief(p)
                self.assertEqual(data["page_type"], page_type)
                if page_type in ("service", "product", "category", "location", "home", "company"):
                    self.assertNotIn("/blog/", data["page_url"])

    def test_intake_fetches_page_and_home_in_one_wave(self):
        url = "https://acme.example/services/visa-help"
        markup = "<title>Visa help | Acme</title><main><h1>Visa help</h1><p>Our team provides visa help. " + "word " * 90 + "</p></main>"
        calls = []
        async def fetch(reqs, *args, **kwargs):
            calls.append(reqs)
            return {r["url"]: {"raw": markup, "status": 200, "state": "ok", "final_url": r["url"]} for r in reqs}
        with patch.object(C, "fetch_many", fetch):
            result = pagetype.intake(url)
        self.assertTrue(result["exists"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 2)
        for address in (url, "https://acme.example/"):
            self.assertEqual(C.cache_get(C._fetch_key("doc", address), "page")["status"], 200)
            self.assertEqual(C.cache_get(C._fetch_key("html", address), "page")["links"], [])

    def test_intake_does_not_render_a_refused_page(self):
        url = "https://acme.example/visa-help"
        async def fetch(reqs, *args, **kwargs):
            return {r["url"]: {"status": 200, "state": "blocked", "raw": "<p>Access denied</p>"} for r in reqs}
        with patch.object(C, "fetch_many", fetch), patch.object(spider, "scrape_many") as render:
            result = pagetype.intake(url)
        self.assertFalse(result["exists"])
        render.assert_not_called()


    def test_type_change_updates_only_generated_defaults(self):
        data = {"page_type": "guide", "page_url": "https://acme.example/blog/visa-help", "domain": "acme.example",
                "target_query": "visa help", "task": "new", "word_range_source": "type",
                "page_url_source": "generated", "word_range_effective": [1200, 2000]}
        briefgen.set_page_type(data, "service", "explicit")
        self.assertEqual(data["page_url"], "https://acme.example/visa-help")
        self.assertEqual(data["word_range"], briefgen.WORDS["service"])
        self.assertNotIn("word_range_effective", data)
        data.update(page_url_source="explicit", word_range_source="explicit", word_range=[300, 400])
        briefgen.set_page_type(data, "product", "explicit")
        self.assertEqual(data["page_url"], "https://acme.example/visa-help")
        self.assertEqual(data["word_range"], [300, 400])

    def test_saved_keyword_brief_accepts_type_instructions_without_repeating_the_client(self):
        (self.root / "briefs").mkdir()
        path = self.root / "briefs" / "visa-help.yaml"
        path.write_text(yaml.safe_dump({"client": "Acme", "domain": "acme.example", "target_query": "visa help",
                                       "page_type": "guide", "page_url": "https://acme.example/blog/visa-help",
                                       "page_url_source": "generated", "word_range_source": "type"}))
        with patch.object(driver, "next_step"), contextlib.redirect_stdout(io.StringIO()):
            driver.start("visa help | service page")
        result = C.load_yaml(path)
        self.assertEqual(result["page_type"], "service")
        self.assertEqual(result["page_url"], "https://acme.example/visa-help")

    def page_start_fixture(self, query="united kingdom", source="page", url=None):
        url = url or "https://acme.example/visa-status-check/united-kingdom"
        (self.root / "clients").mkdir(exist_ok=True)
        (self.root / "briefs").mkdir(exist_ok=True)
        (self.root / "clients" / "acme.yaml").write_text(yaml.safe_dump({"client": "Acme", "domain": "acme.example", "locale": "en-GB"}))
        brief = {"client": "Acme", "domain": "acme.example", "page_url": url, "target_query": query,
                 "page_type": "guide", "page_type_source": source, "locale": "en-GB", "word_range_source": "type",
                 "page_intake": {"keyword_from": "address", "inferred_query": "united kingdom"}}
        path = self.root / "briefs" / "united-kingdom.yaml"
        path.write_text(yaml.safe_dump(brief))
        info = {"page_url": url, "target_query": "uk visa status check", "page_type": "service", "exists": True,
                "evidence": ["own offer"], "h1": "UK visa status check", "locale": "en-GB"}
        return path, info

    def test_url_intake_refreshes_old_inferred_query_and_honours_saved_type(self):
        path, info = self.page_start_fixture(source="explicit")
        with patch.object(pagetype, "intake", return_value=info), patch.object(driver, "next_step") as next_step, \
             contextlib.redirect_stdout(io.StringIO()):
            driver.start_from_page(info["page_url"], "")
        result = C.load_yaml(path)
        self.assertEqual(result["target_query"], "uk visa status check")
        self.assertEqual(result["page_type"], "guide")
        next_step.assert_called_once()
        self.assertFalse((self.root / "runs").exists())

    def test_url_intake_preserves_manually_changed_keyword(self):
        path, info = self.page_start_fixture(query="manual target keyword")
        with patch.object(pagetype, "intake", return_value=info), patch.object(driver, "next_step"), \
             contextlib.redirect_stdout(io.StringIO()):
            driver.start_from_page(info["page_url"], "service page")
        result = C.load_yaml(path)
        self.assertEqual(result["target_query"], "manual target keyword")
        self.assertEqual(result["page_type"], "service")
        self.assertEqual(result["word_range"], briefgen.WORDS["service"])

    def test_url_intake_does_not_overwrite_another_page_with_the_same_leaf(self):
        path, info = self.page_start_fixture(url="https://acme.example/other/united-kingdom")
        original = path.read_text()
        info["page_url"] = "https://acme.example/visa-status-check/united-kingdom"
        with patch.object(pagetype, "intake", return_value=info), patch.object(driver, "next_step"), \
             contextlib.redirect_stdout(io.StringIO()):
            driver.start_from_page(info["page_url"], "")
        self.assertEqual(path.read_text(), original)
        self.assertEqual(C.load_yaml(self.root / "briefs" / "united-kingdom-acme.yaml")["page_url"], info["page_url"])


class IntentTests(OfflineCase):
    def settle(self, data, rows, primary="transactional"):
        C.save_json(self.root / "fact_sheet.json", data)
        pack._settle_page_type(self.root, data, {"organic": rows, "intent": {"primary": primary}})
        return C.load_json(self.root / "fact_sheet.json")

    def test_business_blogs_are_not_sales_page_evidence(self):
        data = sheet("guide")
        data["brief"].update(page_type_source="keyword", target_query="visa options")
        rows = [{"kind": "business_site", "shape": "guide"}] * 8
        self.assertEqual(self.settle(data, rows)["brief"]["page_type"], "guide")

    def test_unrelated_client_offer_cannot_establish_fit(self):
        data = sheet("guide")
        data["brief"].update(page_type_source="keyword", target_query="roof insulation")
        rows = [{"kind": "business_site", "shape": "tool_or_service"}] * 8
        self.assertEqual(self.settle(data, rows)["brief"]["page_type"], "guide")

    def test_explicit_guide_is_never_overridden(self):
        data = sheet("guide")
        data["brief"].update(page_type_source="explicit", target_query="visa application")
        rows = [{"kind": "business_site", "shape": "tool_or_service"}] * 8
        self.assertEqual(self.settle(data, rows)["brief"]["page_type"], "guide")

    def test_relevant_offer_and_page_shapes_can_settle_ambiguous_query(self):
        data = sheet("guide")
        data["brief"].update(page_type_source="keyword", target_query="visa application", word_range_source="type",
                             word_range_effective=[1500, 2500])
        rows = [{"kind": "business_site", "shape": "tool_or_service"}] * 8
        result = self.settle(data, rows)
        self.assertEqual(result["brief"]["page_type"], "service")
        self.assertEqual(result["brief"]["word_range"], briefgen.WORDS["service"])
        self.assertNotIn("word_range_effective", result["brief"])

    def test_status_task_stays_informational_despite_business_serp(self):
        data = sheet("guide")
        data["brief"].update(page_type_source="keyword", target_query="visa status check")
        rows = [{"kind": "business_site", "shape": "tool_or_service"}] * 8
        self.assertEqual(self.settle(data, rows)["brief"]["page_type"], "guide")


class PageJobTests(OfflineCase):
    def findings(self, md, data=None):
        with patch.object(C, "lexicon", return_value={}):
            linter = Linter(md, data or sheet(), {})
            linter.r_page_job()
        return linter.findings

    def test_phishing_hostname_and_query_parameter_are_not_client_links(self):
        for url in ("https://acme.example.evil.test/start", "https://evil.test/?next=acme.example",
                    "https://acme.example@evil.test/start"):
            self.assertFalse(is_client_url(url, sheet()))

    def test_relative_action_and_root_conversion_targets_are_valid(self):
        for url in ("/start", "https://acme.example/start", "https://www.acme.example/start"):
            self.assertTrue(is_client_url(url, sheet()))
        data = sheet()
        data["client"]["offer"]["ctas"] = [{"text": "Get started", "url": "https://acme.example/"}]
        self.assertTrue(next_steps([{"raw": "[Get started](https://acme.example/)", "text": "Get started"}], data))

    def test_blog_link_does_not_count_as_next_step(self):
        fs = self.findings("# Visa help\n\nAcme reviews your documents.\n\nRead our [visa guide](https://acme.example/blog/visas).")
        self.assertTrue(any(f["rule"] == "P02-no-client-next-step" and f["severity"] == "block" for f in fs))

    def test_valid_service_opening_and_action_pass_page_job(self):
        fs = self.findings("# Visa help\n\nAcme reviews application documents. [Get started](/start).\n\n"
                           "## Our process\n\nOur team checks the documents you provide.\n\n[Get started](/start).")
        self.assertFalse([f for f in fs if f["severity"] == "block"])

    def test_official_checking_instructions_and_disclosures_remain_allowed(self):
        fs = self.findings("# Visa help\n\nAcme reviews documents. [Get started](/start).\n\n"
                           "Sign in to your [UKVI account](https://gov.uk/account) to view granted status.\n\n"
                           "You can apply directly on [GOV.UK](https://gov.uk/apply). Our assistance is optional.\n\n"
                           "We cannot influence an authority's decision. [Get started](/start).")
        self.assertFalse([f for f in fs if f["severity"] == "block"])

    def test_repeated_official_application_ctas_block_commercial_drift(self):
        fs = self.findings("# Visa help\n\nAcme reviews documents. [Get started](/start).\n\n"
                           "Apply on [GOV.UK](https://gov.uk/apply).\n\n"
                           "Book through [GOV.UK](https://gov.uk/book).\n\n[Get started](/start).")
        self.assertTrue(any(f["rule"] == "P03-steers-elsewhere" and f["severity"] == "block" for f in fs))

    def test_distinct_mandatory_official_actions_are_not_competing_sales_ctas(self):
        fs = self.findings("# Visa help\n\nAcme reviews documents. [Get started](/start).\n\n"
                           "You must pay the application fee on [GOV.UK](https://gov.uk/pay).\n\n"
                           "Book the mandatory biometrics appointment through [GOV.UK](https://gov.uk/book).\n\n"
                           "You can apply directly on [GOV.UK](https://gov.uk/apply). Assistance is optional.")
        self.assertFalse([f for f in fs if f["rule"] == "P03-steers-elsewhere"])

    def test_guides_can_explain_official_workflows_without_sales_blocks(self):
        md = "# Track your visa\n\nApply on [GOV.UK](https://gov.uk/apply).\n\nBook on [GOV.UK](https://gov.uk/book)."
        self.assertEqual(self.findings(md, sheet("guide")), [])

    def test_unverified_offer_is_not_equated_with_a_non_selling_business(self):
        data = sheet("guide")
        data["client"]["offer"] = {}
        self.assertIn("No relevant client offer has been verified", "\n".join(lines(data)))

    def test_anti_service_warning_never_requires_hiding_a_material_limit(self):
        fs = self.findings("# Visa help\n\nAcme reviews documents. [Get started](/start).\n\n"
                           "No agency can get a faster authority decision, ours included.")
        self.assertFalse([f for f in fs if f["rule"] == "P04-warns-off-client" and f["severity"] == "block"])


class OfferTests(OfflineCase):
    def profile(self, pages, results, **kwargs):
        async def fetch(*args, **kw):
            return results
        with patch.object(C, "fetch_many", fetch):
            return offer.offer_profile("Acme", "acme.example", pages, **kwargs)

    def test_external_redirect_does_not_supply_client_claims(self):
        url = "https://acme.example/"
        result = self.profile([url], {url: {"state": "ok", "final_url": "https://other.example/",
                                          "text": "Our team provides instant approvals.", "links": []}})
        self.assertEqual(result["offers"], [])
        self.assertEqual(result["pages_read"], [])

    def test_banned_claim_and_external_cta_are_rejected(self):
        url = "https://acme.example/"
        result = self.profile([url], {url: {"state": "ok", "text": "Our team provides a fast-track service.",
                                          "links": [("https://other.example/", "Get started")]}}, banned=["fast-track"])
        self.assertEqual(result["offers"], [])
        self.assertEqual(result["ctas"], [])

    def test_service_fee_alone_does_not_invent_an_intermediary_role(self):
        self.assertFalse(offer._intermediary("Our service fee covers the repair.", ["Acme"]))
        self.assertTrue(offer._intermediary("We submit applications on your behalf.", ["Acme"]))

    def test_cta_from_current_page_beats_unrelated_homepage_cta(self):
        home, page = "https://acme.example/", "https://acme.example/uk-visas"
        result = self.profile([page, home], {
            page: {"state": "ok", "text": "Our team reviews UK visa documents.", "links": [("/uk-start", "Get started")]},
            home: {"state": "ok", "text": "Our team reviews all travel documents.", "links": [("/canada-start", "Apply now")]}},
            page_url=page, target_query="UK visa")
        self.assertEqual(result["ctas"][0]["url"], "https://acme.example/uk-start")
        self.assertIn("scope", result["offers"][0])

    def test_offer_keeps_the_route_heading_with_an_ambiguous_promise(self):
        url = "https://acme.example/uk-visas"
        result = self.profile([url], {url: {"state": "ok", "links": [], "text":
            "UK visa status check\nUK to Pakistan e-visa in 24 hours\nA priority e-visa filed by our team.\nTerms apply."}},
            page_url=url, target_query="UK visa status check")
        promise = next(x for x in result["offers"] if "filed by our team" in x["text"])
        self.assertIn("UK to Pakistan", promise["scope"])
        self.assertIn("24 hours", promise["scope"])


class FactBatchTests(OfflineCase):
    def test_batch_uses_one_source_fetch_commit_and_pack_rebuild(self):
        rd = self.root / "scratch"
        rd.mkdir()
        brief_path = self.root / "brief.yaml"
        brief_path.write_text("client: Acme\nextra_facts: []\n", encoding="utf-8")
        data = sheet()
        C.save_json(rd / "fact_sheet.json", data)
        C.save_json(rd / "link_map.json", {"official": []})
        items = [{"id": "f" + str(i), "claim": "The authority checks documents before a decision.",
                  "value": "The authority checks documents before a decision.", "url": "https://authority.example/rules",
                  "scope": "UK applications"} for i in range(12)]
        source = self.root / "facts.yaml"
        source.write_text(yaml.safe_dump(items), encoding="utf-8")
        calls, rebuilds = [], []
        async def fetch(reqs, *args, **kwargs):
            calls.append(reqs)
            return {r["url"]: {"state": "ok", "status": 200, "text": items[0]["value"], "fetched_at": C.now_iso()} for r in reqs}
        def rebuild(*args):
            with C.file_lock(rd / "fact_sheet.json"):
                rebuilds.append(True)
        with patch.object(prep, "load_brief", return_value={"_path": str(brief_path)}), \
             patch.object(prep, "latest_run", return_value=rd), patch.object(C, "fetch_many", fetch), \
             patch.object(prep, "run_checks", return_value={}), patch.object(prep, "gaps", return_value=[]), \
             patch.object(prep, "decisions", return_value=[]), patch.object(prep, "writer_pack", rebuild), \
             contextlib.redirect_stdout(io.StringIO()):
            start = time.monotonic()
            out = prep.add_facts(str(brief_path), str(source))
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(len(out), 12)
        self.assertTrue(all(f["status"] == "verified" for f in out))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(len(rebuilds), 1)
        self.assertEqual(len(C.load_json(rd / "fact_sheet.json")["facts"]), 12)
        self.assertEqual(len(C.load_yaml(brief_path)["extra_facts"]), 12)

    def test_malformed_batch_is_rejected_before_any_network(self):
        source = self.root / "facts.yaml"
        source.write_text("wrong: shape", encoding="utf-8")
        with self.assertRaises(ValueError):
            prep.add_facts("unused.yaml", str(source))

    def test_invalid_entries_count_as_rejections(self):
        source = self.root / "facts.yaml"
        source.write_text("- id: broken\n- a string\n", encoding="utf-8")
        with patch.object(prep, "load_brief", return_value={}), patch.object(prep, "latest_run", return_value=self.root), \
             contextlib.redirect_stdout(io.StringIO()):
            out = prep.add_facts("unused.yaml", str(source))
        self.assertEqual([f["status"] for f in out], ["invalid", "invalid"])

    def test_rejected_number_remains_rejected_in_batch_verification(self):
        f, _ = prep._verify_fact("f1", "Processing takes 10 days.", "Processing takes five working days.",
                                "https://authority.example/rules", res={"state": "ok", "text": "Processing takes five working days.", "fetched_at": C.now_iso()})
        self.assertEqual(f["status"], "not_found")

    def test_corrected_persistent_fact_replaces_stale_evidence_safely(self):
        source = self.root / "brief.yaml"
        source.write_text(yaml.safe_dump({"extra_facts": [{"id": "f1", "value": "old"}]}), encoding="utf-8")
        f = {"id": "f1", "claim": "A Windows path", "value": 'C:\\docs\\file says "yes"\nnext line',
             "scope": "new scope", "source_url": "https://authority.example/rules"}
        prep._persist_extras({"_path": str(source)}, [f])
        self.assertEqual(C.load_yaml(source)["extra_facts"], [f])


class TimingTests(OfflineCase):
    def test_measured_phases_do_not_call_research_drafting(self):
        raw = [("prep", "start", 100), ("prep", "end", 110), ("agent:research", "start", 110),
               ("facts", "start", 120), ("facts", "end", 121), ("agent:research", "end", 140),
               ("agent:draft", "start", 140), ("agent:draft", "end", 150),
               ("lint", "start", 150), ("lint", "end", 151),
               ("agent:verify", "start", 151), ("agent:verify", "end", 200)]
        result = timing.summarise([{"step": s, "ev": e, "t": t} for s, e, t in raw])
        self.assertEqual(result["research"], 30)
        self.assertEqual(result["draft"], 10)
        self.assertEqual(result["facts"], 1)
        self.assertEqual(result["verify"], 49)
        self.assertEqual(result["total"], 100)
        self.assertNotIn("precheck_work", result)

    def test_legacy_logs_expose_unclassified_work(self):
        raw = [("prep", "start", 100), ("prep", "end", 110), ("validate", "start", 200), ("validate", "end", 201)]
        result = timing.summarise([{"step": s, "ev": e, "t": t} for s, e, t in raw])
        self.assertEqual(result["precheck_work"], 90)
        self.assertNotIn("draft", result)

    def test_concurrent_timing_events_are_not_lost(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda n: timing.mark(self.root, str(n), "event"), range(30)))
        events = C.load_json(self.root / "timing.json")["events"]
        self.assertEqual(len(events), 30)
        self.assertEqual({e["step"] for e in events}, {str(n) for n in range(30)})


class LateStageTests(OfflineCase):
    def test_late_edits_are_linted_after_editor_checker_and_linker(self):
        from seolib import lint
        data = sheet()
        C.save_json(self.root / "fact_sheet.json", data)
        C.save_json(self.root / "link_map.json", {})
        (self.root / "research_plan.md").write_text("synthetic fixture")
        (self.root / "writer_pack.md").write_text("synthetic fixture")
        md = ("# Visa help\n\nAcme reviews documents. [Get started](/start).\n\n"
              "Apply on [GOV.UK](https://gov.uk/apply).\n\nBook on [GOV.UK](https://gov.uk/book).")
        (self.root / "draft.md").write_text(md, encoding="utf-8")
        def real_page_job(md, data, *args):
            with patch.object(C, "lexicon", return_value={}):
                linter = Linter(md, data, {})
                linter.r_page_job()
            return {"findings": linter.findings, "summary": {}}
        for stage in ("editor", "verify", "internal_links"):
            with self.subTest(stage=stage):
                done = {key: "done" for key in ("research", "outline", "expert", "review", "expert_read", "editor", "verify", "internal_links")}
                C.save_json(self.root / "state.json", {"done": done, "mode": "deep"})
                with patch.object(prep, "load_brief", return_value={"target_query": "visa help"}), \
                     patch.object(driver, "_current_run", return_value=self.root), \
                     patch.object(lint, "lint_text", real_page_job), patch.object(driver, "_task") as task:
                    driver.next_step("synthetic.yaml")
                self.assertEqual(task.call_args.args[0], "FIX LINT BLOCKS (role: writer)")

    def test_content_signature_allows_internal_links_but_not_changed_claims_or_sources(self):
        p = self.root / "draft.md"
        original = "# Visa help\n\nAcme reviews documents. See the [official rules](https://authority.example/rules)."
        p.write_text(original)
        baseline = driver._content_sig(p, sheet())
        p.write_text(original.replace("reviews documents", "reviews [documents](/documents)"))
        self.assertEqual(driver._content_sig(p, sheet()), baseline)
        p.write_text(original.replace("reviews", "approves"))
        self.assertNotEqual(driver._content_sig(p, sheet()), baseline)
        p.write_text(original.replace("authority.example", "another.example"))
        self.assertNotEqual(driver._content_sig(p, sheet()), baseline)

    def test_final_validation_uses_content_hash_even_when_mtimes_match(self):
        from seolib import lint, validate
        data = sheet()
        data["brief"].update(page_type="guide")
        C.save_json(self.root / "fact_sheet.json", data)
        C.save_json(self.root / "link_map.json", {})
        for name in ("research_plan.md", "writer_pack.md", "draft.md", "final.md"):
            (self.root / name).write_text("# Changed content\n\nA synthetic test page.")
        stamp = time.time() - 60
        for name in ("draft.md", "final.md"):
            os.utime(self.root / name, (stamp, stamp))
        C.save_json(self.root / "state.json", {"done": {"research": "done", "outline": "done", "review": "done"},
                                                "mode": "quick", "validated_draft": "old content hash"})
        with patch.object(prep, "load_brief", return_value={"target_query": "test page"}), \
             patch.object(driver, "_current_run", return_value=self.root), \
             patch.object(lint, "lint_text", return_value={"findings": [], "summary": {}}), \
             patch.object(validate, "validate", return_value=False) as check, patch.object(driver, "_task"):
            driver.next_step("synthetic.yaml")
        check.assert_called_once()


class StructureTests(OfflineCase):
    def test_service_questions_can_be_answered_in_body_and_faq_h3s(self):
        md = ("# Visa help\n\nAcme reviews documents.\n\n## Our process\n\n"
              "What documents do you need for a visa? You need a valid passport.\n\n"
              "## FAQs\n\n### Can I apply directly?\n\nYou can apply directly.")
        with patch.object(C, "lexicon", return_value={}):
            linter = Linter(md, sheet(), {}, {"query_map": {"h2_questions": ["What documents do you need for a visa?"]}})
            linter.r_research()
            linter.r_koray()
        self.assertFalse([f for f in linter.findings if f["rule"] in ("Q01-question-not-answered", "K03-contextless-heading")])

    def test_commercial_outline_requires_page_job_and_accepts_coverage_notes(self):
        from seolib.outline import check_outline
        C.save_json(self.root / "fact_sheet.json", sheet())
        C.save_json(self.root / "research" / "query_map.json", {"h2_questions": ["What visa documents do I need?"]})
        outline = ("# Visa help\n\n## Our process\nCovers: What visa documents do I need?\n\n"
                   "## FAQs\n### Can I apply directly?\n")
        (self.root / "outline.md").write_text(outline)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(check_outline(self.root))
        (self.root / "outline.md").write_text("Page job: service; offer facts: offer:1; next step: /start\n\n" + outline)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(check_outline(self.root))

    def test_opening_and_closing_conversion_cta_are_not_duplicate_link_warnings(self):
        md = "# Visa help\n\nAcme reviews documents. [Get started](https://acme.example/start).\n\n[Get started](https://acme.example/start)."
        with patch.object(C, "lexicon", return_value={}):
            linter = Linter(md, sheet(), {"internal": ["https://acme.example/start"]})
            linter.r_links()
        self.assertFalse([f for f in linter.findings if f["rule"] == "U07-url-linked-twice"])

    def test_published_contact_targets_are_usable_for_company_pages(self):
        data = sheet("company")
        data["client"]["offer"]["ctas"] = [{"text": "Contact us", "url": "mailto:hello@acme.example"}]
        self.assertTrue(next_steps([{"raw": "[Contact us](mailto:hello@acme.example)"}], data))


    def test_writer_pack_does_not_force_commercial_questions_into_h2s(self):
        from seolib import kgdoc
        for page_type in ("service", "location", "product", "category", "home", "company", "guide"):
            with self.subTest(page_type=page_type):
                data = sheet(page_type)
                C.save_json(self.root / "fact_sheet.json", data)
                C.save_json(self.root / "link_map.json", {})
                C.save_json(self.root / "research" / "query_map.json", {"h2_questions": ["Can I apply directly?"], "queries": []})
                def base_pack(rd, data, lm):
                    (rd / "writer_pack.md").write_text("\n".join(lines(data)), encoding="utf-8")
                with patch.object(pack, "writer_pack", base_pack), patch.object(kgdoc, "write_docs"):
                    pack.research_pack(self.root)
                content = (self.root / "writer_pack.md").read_text(encoding="utf-8")
                self.assertNotIn("Use each as an H2", content)
                if page_type != "guide":
                    self.assertIn("not a compulsory H2 structure", content)
                else:
                    self.assertIn("no compulsory opening or closing sales pitch", content)
                    self.assertNotIn("not a compulsory H2 structure", content)


class FetchBudgetTests(OfflineCase):
    def test_single_attempt_respects_a_rate_limit_without_retrying(self):
        import httpx
        response = SimpleNamespace(status_code=429, url="https://authority.example/rules", text="", headers={})
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = response
        async def gather(*coros):
            return [await c for c in coros]
        with patch.object(httpx, "AsyncClient", return_value=client), patch.object(asyncio, "gather", gather), \
             patch.object(asyncio, "sleep", new_callable=AsyncMock) as sleep:
            result = C.run_async(C.fetch_many([{"url": str(response.url), "parse": "doc"}], attempts=1))
        self.assertEqual(result[str(response.url)]["status"], 429)
        self.assertEqual(client.get.await_count, 1)
        sleep.assert_not_awaited()

    def test_rendered_error_body_is_not_a_verified_source(self):
        url = "https://authority.example/rules"
        response = SimpleNamespace(status_code=200, json=lambda: [{"status": 403, "content": "blocked " * 100}])
        client = SimpleNamespace(post=AsyncMock(return_value=response))
        with patch.object(spider, "api_key", return_value="offline-test"), patch.object(C, "cache_put") as cache:
            result = C.run_async(spider._scrape_one(client, url, contextlib.nullcontext(), attempts=1))
        self.assertEqual(result["state"], "error")
        self.assertEqual(result["status"], 403)
        cache.assert_not_called()

    def test_render_timeout_becomes_an_explicit_research_gap(self):
        async def timed_out(coro, timeout):
            coro.close()
            raise asyncio.TimeoutError()
        with patch.object(asyncio, "wait_for", timed_out):
            result = C.run_async(spider._bounded_scrape(None, "https://authority.example/rules", None, 20, 1, False))
        self.assertEqual(result["state"], "timeout")
        self.assertEqual(result["error"], "render_budget_exceeded")
        self.assertEqual(result["budget_s"], 20)

    def test_render_batch_keeps_successes_beside_timed_out_pages_and_deduplicates_urls(self):
        import httpx
        ok, slow = "https://authority.example/ok", "https://authority.example/slow"
        client = AsyncMock()
        client.__aenter__.return_value = client
        async def bounded(client, url, sem, timeout_s, attempts, refresh):
            return {"url": url, "state": "ok" if url == ok else "timeout"}
        async def gather(*coros):
            return [await c for c in coros]
        with patch.object(spider, "api_key", return_value="offline-test"), \
             patch.object(httpx, "AsyncClient", return_value=client), \
             patch.object(spider, "_bounded_scrape", side_effect=bounded) as scrape, \
             patch.object(asyncio, "gather", gather):
            result = spider.scrape_many([ok, slow, ok], timeout_s=20, attempts=1, refresh=True)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[ok]["state"], "ok")
        self.assertEqual(result[slow]["state"], "timeout")
        self.assertEqual(scrape.call_count, 2)
        self.assertEqual(scrape.call_args.args[3:], (20, 1, True))


if __name__ == "__main__":
    unittest.main()
