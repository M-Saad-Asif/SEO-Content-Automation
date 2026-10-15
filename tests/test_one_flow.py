"""Offline regressions for the one flow: the script-built page plan (complete coverage, one H2 per searcher question,
duplicates merged), parallel parts joined, fact notes that can't be copied, the lock leftover, the market filter."""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib import common as C  # noqa: E402
from seolib import plan as P  # noqa: E402
from seolib.writebrief import note  # noqa: E402


def q(text, source="paa", decision="cover_in_section", competitors=0):
    return {"q": text, "source": source, "decision": decision, "reason": "", "competitors": competitors,
            "variants": [], "lead": None}


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rd = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.rd / "research").mkdir()

    def make(self, page_type="guide", offer=None):
        brief = {"target_query": "how long does fence paint take to dry", "client": "Acme", "domain": "acme.co.uk",
                 "locale": "en-GB", "page_type": page_type, "word_range": [900, 1400]}
        C.save_json(self.rd / "fact_sheet.json", {"brief": brief, "facts": [
            {"id": "serp:1", "status": "serp", "value": "Most fence paints are touch dry in 1 to 2 hours in warm weather.",
             "consensus": 3},
            {"id": "serp:2", "status": "serp", "value": "Apply two coats of fence paint, waiting 4 hours between coats.",
             "consensus": 2},
        ], "client": {"offer": offer or {}}})
        C.save_json(self.rd / "link_map.json", {"client_related": {}, "client_titles": {}})
        C.save_json(self.rd / "research" / "query_map.json", {"queries": [
            {"query": "How long does it take paint to dry outside in 90 degree weather?", "decision": "h2"},
            {"query": "Fence paint drying time in Australia", "decision": "drop"}]})
        C.save_json(self.rd / "research" / "topic_outline.json", {
            "sections": [
                {"id": "S1", "title": "Drying times", "covered_by": ["a.example", "b.example"], "subsections": [],
                 "questions": [q("How long should fence paint dry before it rains?", decision="h2"),
                               q("Is 2 hours enough for paint to dry?", decision="h2"),
                               q("How long before rain can I paint my fence?", source="related")]},
                {"id": "S2", "title": "How Many Coats Of Paint Should You Put On A Fence?", "covered_by": ["a.example"],
                 "subsections": [], "questions": [q("How many coats of paint should you put on a fence?", decision="h2")]},
                {"id": "S3", "title": "Painting new pressure-treated panels", "covered_by": ["c.example", "d.example"],
                 "subsections": [{"id": "S3.1", "title": "Weathering new panels", "covered_by": ["c.example"],
                                  "questions": []}], "questions": []},
                {"id": "S4", "title": "How long does it take paint to dry outside in 90 degree weather?",
                 "covered_by": [], "subsections": [],
                 "questions": [q("How long does it take paint to dry outside in 90 degree weather?", decision="h2")]},
            ],
            "single_site_angles": ["Fence painting tools", "Brush or roller for fence panels"],
            "single_site_questions": [{"q": "how long does water based fence paint take to dry", "source": "autocomplete"},
                                      {"q": "What happens if you paint a wet fence?", "source": "competitor"}],
            "other_searches": [], "not_here": [], "mention_only": []})
        return P.build(self.rd)

    def titles(self, plan):
        return [h["title"] for h in plan["headings"]] + [s["title"] for h in plan["headings"] for s in h["subs"]]

    def test_every_searcher_question_gets_a_heading(self):
        t = self.titles(self.make())
        for want in ("How long should fence paint dry before it rains?", "Is 2 hours enough for paint to dry?",
                     "How many coats of paint should you put on a fence?", "Painting new pressure-treated panels",
                     "Weathering new panels", "Fence painting tools", "What happens if you paint a wet fence?"):
            self.assertIn(want, t)

    def test_duplicates_merge_and_title_case_is_fixed(self):
        t = self.titles(self.make())
        self.assertEqual(sum(1 for x in t if "coats" in x.lower()), 1)  # section title and its PAA are one heading
        self.assertNotIn("How Many Coats Of Paint Should You Put On A Fence?", t)

    def test_another_markets_question_is_left_out(self):
        t = " ".join(self.titles(self.make())).lower()
        self.assertNotIn("90 degree", t)  # Fahrenheit weather on a UK page
        self.assertNotIn("australia", t)

    def test_main_query_variants_are_one_block_not_headings(self):
        plan = self.make()
        self.assertIn("how long does water based fence paint take to dry", plan["variants"])
        self.assertNotIn("water based", " ".join(self.titles(plan)).lower())

    def test_commercial_page_gets_the_clients_offer_and_next_step(self):
        plan = self.make("service", {"offers": [{"text": "We paint fences across London.", "url": "https://acme.co.uk/"}],
                                     "ctas": [{"text": "Book a quote", "url": "https://acme.co.uk/quote"}]})
        kinds = [h["kind"] for h in plan["headings"]]
        self.assertEqual(kinds[0], "offer")
        self.assertEqual(kinds[-1], "cta")
        self.assertIn("Book a quote", plan["headings"][-1]["note"])

    def test_facts_are_assigned_and_check_finds_missing_headings(self):
        plan = self.make()
        self.assertTrue(any(h.get("facts") for h in plan["headings"]))
        md = "# How long does fence paint take to dry\n\nText.\n\n## Is 2 hours enough for paint to dry?\n\nYes.\n"
        missing = P.check(self.rd, md)
        self.assertTrue(any("coats" in m.lower() for m in missing))
        self.assertFalse(any("2 hours" in m for m in missing))

    def test_parts_split_the_plan_for_parallel_writers(self):
        plan = self.make()
        names = [h for part in plan["parts"] for h in part["headings"]]
        self.assertEqual(names, [h["title"] for h in plan["headings"]])
        self.assertTrue(plan["parts"][0]["with_intro"])


class StitchTests(unittest.TestCase):
    def test_parts_join_with_one_front_matter_and_h1(self):
        from seolib.driver import _stitch
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            plan = {"parts": [{"id": "A"}, {"id": "B"}]}
            (rd / "draft_part_A.md").write_text("---\ntitle: T\n---\n\n# H1\n\nOpening.\n\n## One\n\nA.\n", encoding="utf-8")
            self.assertEqual(_stitch(rd, plan), ["B"])
            (rd / "draft_part_B.md").write_text("---\ntitle: X\n---\n# H1\n\n## Two\n\nB.\n", encoding="utf-8")
            self.assertEqual(_stitch(rd, plan), [])
            md = (rd / "draft.md").read_text(encoding="utf-8")
            self.assertEqual(md.count("---\n"), 2)
            self.assertEqual(len(re.findall(r"(?m)^# ", md)), 1)
            self.assertIn("## Two", md)


class NoteTests(unittest.TestCase):
    def test_a_note_keeps_figures_and_qualifiers_but_not_six_words_of_wording(self):
        s = "Drying to the touch comes first, and full curing may take up to a week for most paints."
        n = note(s)
        self.assertIn("up", n)
        self.assertIn("week", n)
        src = re.findall(r"[a-z']+", s.lower())
        grams = {" ".join(src[i:i + 6]) for i in range(len(src) - 5)}
        got = re.findall(r"[a-z']+", n.lower())
        self.assertFalse(any(" ".join(got[i:i + 6]) in grams for i in range(len(got) - 5)))


class LockLeftoverTests(unittest.TestCase):
    def test_a_lock_file_left_by_this_process_is_not_a_live_owner(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "x.json"
            Path(str(target) + ".lock").write_text(str(os.getpid()), encoding="utf-8")
            lock = C.file_lock(target, timeout=2)
            with lock:
                pass  # acquires at once instead of waiting out the timeout
            self.assertFalse(Path(str(target) + ".lock").exists())


if __name__ == "__main__":
    unittest.main()
