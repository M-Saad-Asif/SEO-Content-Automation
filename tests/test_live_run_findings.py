"""Regressions for what the live run on "how to unblock a sink" (Toolstation, 16 Oct 2026) found: research that never
reached the writer, wrong client pages, junk and contradictory headings, steps written as headings, dates flagged as
invented, one source linked by every parallel writer."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class PlanHeadingTests(unittest.TestCase):
    def test_competitor_furniture_is_never_a_heading(self):
        from seolib.plan import boiler
        for t in ("Special offers", "Recent posts", "Related sinks & taps articles", "Video", "FAQs"):
            self.assertTrue(boiler(t), t)
        for t in ("Reviews of drain unblockers", "Check the sink trap", "How to prevent sink blockages"):
            self.assertFalse(boiler(t), t)

    def test_instructions_become_numbered_steps_and_topics_stay_headings(self):
        from seolib.plan import is_step
        for t in ("Seal the overflow", "Plunge the sink", "Clear water from the sink", "Leave the mixture to work"):
            self.assertTrue(is_step(t), t)
        for t in ("Wire hanger", "Hot water", "Enzymatic drain cleaners", "Common causes of bathroom sink clogs",
                  "Painting new pressure-treated panels"):
            self.assertFalse(is_step(t), t)


class ClientPageTests(unittest.TestCase):
    URLS = ["https://www.toolstation.com/andris-lux-15l-under-sink-water-heater/pAL832",
            "https://www.toolstation.com/andris-lux-10l-under-sink-water-heater/pAL835",
            "https://www.toolstation.com/belfast-ceramic-sink/p12345",
            "https://www.toolstation.com/kitchen-sink-mixer-tap/p23456",
            "https://www.toolstation.com/scrubb-drain-unblocker/pAC006",
            "https://www.toolstation.com/kilrockpro-rhino-kitchen-drain-unblocker/pAJ960",
            "https://www.toolstation.com/help-and-advice/how-to-guides/how-to-unblock-toilet"] + [
            f"https://www.toolstation.com/stainless-steel-sink-model-{i}/p9{i:04d}" for i in range(20)]  # a shop's many sinks

    def test_product_ids_are_read_past_and_rare_query_words_win(self):
        from seolib.clientpages import related, slug
        self.assertEqual(slug("https://www.toolstation.com/scrubb-drain-unblocker/pAC006"), "scrubb-drain-unblocker")
        rel = related(self.URLS, "how to unblock a sink")
        self.assertTrue(rel["commercial"])
        self.assertTrue(all("unblocker" in u for u in rel["commercial"]), rel["commercial"])
        self.assertIn("https://www.toolstation.com/help-and-advice/how-to-guides/how-to-unblock-toilet", rel["guides"])

    def test_content_sitemaps_are_read_first(self):
        from seolib.prep import pick_child_sitemaps
        locs = [f"https://x.com/sitemap/category/{i}.xml" for i in range(45)] + ["https://x.com/sitemap/information.xml"]
        got = pick_child_sitemaps(locs, {"page_url": "", "target_query": "how to unblock a sink"})
        self.assertEqual(got[0], "https://x.com/sitemap/information.xml")
        self.assertEqual(len(got), 40)


class GainDateTests(unittest.TestCase):
    def test_a_sources_date_is_a_citable_figure(self):
        import tempfile
        from seolib import common as C
        from seolib.gain import register
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            (rd / "research").mkdir()
            C.save_json(rd / "fact_sheet.json", {"brief": {"domain": "acme.co.uk"}, "facts": []})
            C.save_json(rd / "research" / "gain.json", {"items": [{
                "kind": "data", "point": "Which? timed a kitchen unblocker at 15 minutes", "who": "Which?",
                "quote": "It only took 15 minutes for this plughole unblocker", "source": "https://which.co.uk/x",
                "date": "May 2021", "quote_found": True}]})
            f = register(rd)[0]
            self.assertIn("2021", f["condition"])
            self.assertIn("2021", f["claim"])


class OneLinkPerSourceTests(unittest.TestCase):
    def test_the_plan_names_one_heading_to_link_each_source(self):
        from seolib.plan import render
        plan = {"h1": "x", "intro_words": 90, "parts": [{"id": "A", "headings": ["First"], "with_intro": True},
                                                       {"id": "B", "headings": ["Second"], "with_intro": False}],
                "headings": [{"title": "First", "kind": "topic", "subs": [], "questions": [], "words": 100,
                              "facts": ["gain:1"], "gain": ["gain:1"]},
                             {"title": "Second", "kind": "topic", "subs": [], "questions": [], "words": 100,
                              "facts": ["gain:2"], "gain": ["gain:2"]}]}
        facts = {"gain:1": {"source_url": "https://which.co.uk/x"}, "gain:2": {"source_url": "https://which.co.uk/x"}}
        text = "\n".join(render(plan, facts))
        self.assertIn("`gain:2` (name the source only: it is linked under \"First\")", text)
        self.assertNotIn("`gain:1` (name the source only", text)


class CopyAllowanceTests(unittest.TestCase):
    def test_a_long_copied_run_always_goes_back(self):
        from seolib.lint import Linter
        self.assertIn("C03-copied-text", Linter.ALLOWANCE)


if __name__ == "__main__":
    unittest.main()
