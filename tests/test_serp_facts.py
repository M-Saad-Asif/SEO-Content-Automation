"""Offline regressions for page-one facts (majority-resolved contradictions), coverage and information gain."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib import common as C  # noqa: E402
from seolib.lint import allowed_numbers  # noqa: E402

spec = importlib.util.spec_from_file_location("serp_facts_run", ROOT / "plugins" / "serp_facts" / "run.py")
serp_facts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serp_facts)


def page(position, domain, blocks):
    return {"position": position, "url": f"https://{domain}/guide", "domain": domain, "blocks": blocks,
            "outline": [[int(t[1]), x] for t, x in blocks if t in ("h2", "h3")], "source_role": "ranked"}


class FakeCtx(SimpleNamespace):
    def load(self, name):
        return self.data.get(name) or {}


class SerpFactsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rd = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        C.save_json(self.rd / "fact_sheet.json", {"brief": {}, "facts": []})

    def run_plugin(self, pages, extra_facts=(), serp=None):
        sheet = C.load_json(self.rd / "fact_sheet.json")
        sheet["facts"] += list(extra_facts)
        C.save_json(self.rd / "fact_sheet.json", sheet)
        ctx = FakeCtx(rd=self.rd, brief={"target_query": "how deep should a strawberry pot be", "locale": "en-GB"},
                      data={"competitor_scrape": {"pages": pages}, "semantic_graph": {}, "serp_intel": serp or {}})
        res = serp_facts.run(ctx)
        return res, [f for f in C.load_json(self.rd / "fact_sheet.json")["facts"] if f["id"].startswith("serp:")]

    def test_rank_breaks_a_tie(self):
        pages = [page(2, "a.example", [["h2", "Pot depth"], ["p", "A strawberry pot should be at least 20 cm deep for the roots."]]),
                 page(6, "b.example", [["h2", "Pot depth"], ["p", "A strawberry pot should be at least 30 cm deep for the roots."]])]
        res, facts = self.run_plugin(pages)
        self.assertEqual(res["conflicts"], 1)
        winner = next(f for f in facts if f.get("conflicts"))
        self.assertIn("20 cm", winner["value"])
        self.assertEqual(winner["rank"], 2)
        self.assertIn("30 cm", winner["conflicts"][0]["sentence"])
        sheet = C.load_json(self.rd / "fact_sheet.json")
        nums, *_ = allowed_numbers(sheet)
        self.assertIn(20.0, nums)
        self.assertNotIn(30.0, nums)  # the losing value is never usable

    def test_another_markets_units_are_not_facts(self):
        pages = [page(1, "a.example", [["p", "Strawberry pots do best between 60 F and 80 F, so move the pot into shade in a heatwave."]]),
                 page(2, "b.example", [["p", "A strawberry pot should be at least 20 cm deep so the roots have room to grow."]])]
        res, facts = self.run_plugin(pages)
        self.assertFalse(any("80 F" in f["value"] for f in facts))
        self.assertTrue(any("20 cm" in f["value"] for f in facts))

    def test_majority_of_sites_wins_over_a_higher_rank(self):
        say = lambda cm: [["h2", "Pot depth"], ["p", f"A strawberry pot should be at least {cm} cm deep for the roots."]]
        pages = [page(1, "a.example", say(20))] + [page(r, f"s{r}.example", say(30)) for r in (3, 5, 7)]
        res, facts = self.run_plugin(pages)
        winner = next(f for f in facts if f.get("conflicts"))
        self.assertIn("30 cm", winner["value"])  # 3 sites against 1, though the 20 cm page ranks first
        self.assertIn("20 cm", winner["conflicts"][0]["sentence"])
        self.assertIn("3 site(s) against 1", winner["claim"])
        nums, *_ = allowed_numbers(C.load_json(self.rd / "fact_sheet.json"))
        self.assertIn(30.0, nums)
        self.assertNotIn(20.0, nums)

    def test_different_measures_are_separate_points_not_a_conflict(self):
        pages = [page(1, "a.example", [["p", "Choose a strawberry pot at least 20 cm deep with good drainage holes."]]),
                 page(3, "b.example", [["p", "Strawberry pots 30 cm wide hold three plants comfortably in a sunny spot."]])]
        res, facts = self.run_plugin(pages)
        self.assertEqual(res["conflicts"], 0)
        self.assertEqual(len(facts), 2)

    def test_single_site_point_is_kept_and_consensus_counted(self):
        pages = [page(1, "a.example", [["p", "Water strawberry pots every day in hot weather because pots dry quickly."]]),
                 page(4, "b.example", [["p", "In hot weather water strawberry pots every day as pots dry out quickly."]]),
                 page(7, "c.example", [["p", "Feed strawberry plants in pots with a high-potash fertiliser every two weeks once flowers appear."]])]
        res, facts = self.run_plugin(pages)
        by_value = {f["value"][:20]: f for f in facts}
        self.assertEqual(max(f["consensus"] for f in facts), 2)
        self.assertTrue(any("potash" in f["value"] for f in facts), "a point only one page-one site makes is still kept")
        self.assertTrue(all(f["status"] == "serp" for f in facts))
        self.assertTrue(by_value)

    def test_authority_figure_overrides_a_competitor(self):
        official = {"id": "auto:gov:1", "status": "verified", "basis": "official_page_auto",
                    "value": "A strawberry pot should be at least 25 cm deep for the roots.", "source_url": "https://gov.example/x"}
        pages = [page(1, "a.example", [["p", "A strawberry pot should be at least 20 cm deep for the roots."]])]
        res, facts = self.run_plugin(pages, [official])
        self.assertEqual(res["overridden"], 1)
        self.assertEqual(facts[0]["status"], "serp_overridden")
        nums, *_ = allowed_numbers(C.load_json(self.rd / "fact_sheet.json"))
        self.assertNotIn(20.0, nums)

    def test_different_years_are_history_not_an_override(self):
        official = {"id": "auto:gov:7", "status": "verified", "basis": "official_page_auto",
                    "value": "Tax year | Amount (2015 to 2016 | annual allowance £40,000)", "source_url": "https://gov.example/r"}
        pages = [page(1, "a.example", [["trh", "Tax year | Amount"], ["tr", "2026 to 2027 | annual allowance £60,000"]])]
        res, facts = self.run_plugin(pages, [official])
        self.assertEqual(res["overridden"], 0)

    def test_promotions_and_self_claims_are_not_facts(self):
        pages = [page(1, "a.example", [["p", "Sign up to our newsletter for 10% off strawberry pots this week only."],
                                        ["p", "We have sold strawberry pots for 25 years to happy gardeners."]])]
        _, facts = self.run_plugin(pages)
        self.assertEqual(facts, [])

    def test_paa_answers_become_serp_facts(self):
        serp = {"paa_answers": {"How deep should a strawberry pot be?": {
            "snippet": "Strawberry roots are shallow, so a pot 15 to 20 cm deep is usually enough.", "link": "https://c.example/a"}}}
        _, facts = self.run_plugin([page(1, "a.example", [["p", "x"]])], serp=serp)
        paa = [f for f in facts if f["basis"] == "paa_answer"]
        self.assertEqual(len(paa), 1)
        self.assertEqual(paa[0]["question"], "How deep should a strawberry pot be?")


class CoverageTests(unittest.TestCase):
    def test_single_site_angles_and_paa_drift_are_required(self):
        from seolib import article_context
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp)
            (rd / "research").mkdir()
            C.save_json(rd / "fact_sheet.json", {"brief": {"target_query": "grow strawberries in pots", "locale": "en-GB"},
                                                 "facts": []})
            C.save_json(rd / "link_map.json", {})
            C.save_json(rd / "research" / "competitor_scrape.json", {"pages": [
                page(1, "a.example", [["h2", "Use a high-quality potting mix"], ["p", "text"]])]})
            C.save_json(rd / "research" / "topic_outline.json", {"sections": [], "single_site_angles": ["Use a high-quality potting mix"]})
            C.save_json(rd / "research" / "query_map.json", {"queries": [
                {"query": "How long do strawberry plants last in pots?", "source": "paa_expanded", "decision": "drop",
                 "reason": "a second-hop question that drifts from the topic"},
                {"query": "how to grow strawberries in pots australia", "source": "autocomplete", "decision": "drop",
                 "reason": "another market's question"}]})
            C.save_json(rd / "research" / "serp_intel.json", {"organic": []})
            C.save_json(rd / "research" / "semantic_graph.json", {})
            ctx = article_context.build(rd)
            req = {c["text"]: c for c in ctx["coverage_requirements"] if c["required"]}
            self.assertIn("Use a high-quality potting mix", req)
            self.assertIn("How long do strawberry plants last in pots?", req)
            self.assertTrue(req["How long do strawberry plants last in pots?"]["info_gain"])
            self.assertNotIn("how to grow strawberries in pots australia", req)


if __name__ == "__main__":
    unittest.main()
