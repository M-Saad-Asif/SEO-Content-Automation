"""Style rules are an allowance per page, not a ban per sentence; Serper is capped at 3 paid searches a run and
autocomplete comes from Google's free suggestion service."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib.autofix import fix_text  # noqa: E402
from seolib.lint import lint_text  # noqa: E402

SHEET = {"brief": {"target_query": "how long does fence paint take to dry", "client": "Acme", "domain": "acme.co.uk",
                   "locale": "en-GB", "page_type": "guide", "word_range": [50, 5000]},
         "facts": [], "client": {}, "products": []}
FILL = ("Fence paint dries to the touch in 2 hours at 20 degrees on planed timber. Rough sawn boards hold more water "
        "and take longer. ")
IF = "If the boards feel damp, wait another day before the second coat. "
PASSIVE = "The boards are treated by the factory before delivery. "


def page(sections: list[str], headings: list[str] | None = None) -> str:
    heads = headings or [f"How long does section {i + 1} take to dry?" for i in range(len(sections))]
    body = "".join(f"## {h}\n\n{s}\n\n" for h, s in zip(heads, sections))
    return ("---\ntitle: Fence paint\nmeta_description: x\n---\n\n# How long does fence paint take to dry\n\n"
            "Fence paint dries in about 2 hours at 20 degrees.\n\n" + body)


def blocks(md: str) -> set[str]:
    return {f["rule"] for f in lint_text(md, SHEET, {}, {})["findings"] if f["severity"] == "block"}


def count(md: str, rule: str) -> int:
    return sum(1 for f in lint_text(md, SHEET, {}, {})["findings"] if f["severity"] == "block" and f["rule"] == rule)


class AllowanceTests(unittest.TestCase):
    def test_a_few_if_sentences_read_naturally_and_many_go_back(self):
        secs = [FILL * 5 for _ in range(10)]
        for i in (1, 4, 7):
            secs[i] = FILL * 3 + IF + FILL
        self.assertNotIn("K04-if-opener", blocks(page(secs)))
        many = [FILL * 3 + IF + FILL for _ in range(10)]
        self.assertGreaterEqual(count(page(many), "K04-if-opener"), 5)

    def test_an_if_sentence_that_opens_a_section_always_goes_back(self):
        secs = [FILL * 5 for _ in range(10)]
        secs[2] = IF + FILL * 4
        self.assertIn("K04-if-opener", blocks(page(secs)))

    def test_two_passive_sentences_are_fine_and_more_go_back(self):
        secs = [FILL * 5 for _ in range(8)]
        secs[2], secs[5] = FILL * 3 + PASSIVE, FILL * 3 + PASSIVE
        self.assertNotIn("S08-passive", blocks(page(secs)))
        secs = [FILL * 3 + PASSIVE for _ in range(8)]
        self.assertIn("S08-passive", blocks(page(secs)))

    def test_statement_headings_must_be_built_from_the_topics_entities(self):
        secs = [FILL * 5 for _ in range(8)]
        heads = [f"How long does part {i} take?" for i in range(8)]
        heads[2], heads[5] = "Drying times by paint type", "Fence paint drying in cold weather"
        self.assertFalse({"H03-question-heading", "H12-vague-heading"} & blocks(page(secs, heads)))
        heads[5] = "Tools for the job"  # names no entity of the topic
        self.assertIn("H03-question-heading", blocks(page(secs, heads)))

    def test_hype_headings_are_never_allowed(self):
        secs = [FILL * 5 for _ in range(8)]
        for h in ("The ultimate guide to fence paint", "Navigating fence paint drying", "A new era of quick-dry paint",
                  "Everything you need to know about drying"):
            with self.subTest(h=h):
                heads = [f"How long does part {i} take?" for i in range(8)]
                heads[3] = h
                self.assertIn("H12-vague-heading", blocks(page(secs, heads)))

    def test_varied_human_pages_pass_the_style_allowances(self):
        style = {"K04-if-opener", "K10-hedge", "K12-vague-quantity", "S08-passive", "H03-question-heading",
                 "K14-list-mixed", "S01-long-sentence"}
        variants = [
            [FILL * 3 + IF + FILL, FILL * 5, FILL * 3 + PASSIVE, FILL * 5, FILL * 3 + IF, FILL * 5, FILL * 4, FILL * 5],
            [FILL * 5, FILL * 3 + "Rain might delay the second coat by a day. " + FILL, FILL * 5, FILL * 3 + IF + FILL,
             FILL * 5, "- Sand the boards.\n- Brushing the dust off.\n- Apply the first coat.", FILL * 5, FILL * 5],
            [FILL * 4 + PASSIVE, FILL * 5, FILL * 5, FILL * 3 + IF, FILL * 3 + "Several brands sell quick-dry "
             "formulas. " + FILL, FILL * 5, FILL * 5, FILL * 5],
        ]
        for n, secs in enumerate(variants):
            with self.subTest(variant=n):
                self.assertFalse(style & blocks(page(secs)))

    def test_autofix_keeps_a_few_if_sentences_and_turns_the_section_opener(self):
        secs = [FILL * 4 + IF for _ in range(4)]
        secs[0] = IF + FILL * 4
        md, _ = fix_text(page(secs))
        self.assertIn("Wait another day before the second coat if the boards feel damp.", md)
        self.assertEqual(md.count("If the boards feel damp"), 3)  # the allowance stays as written


class SerperCapTests(unittest.TestCase):
    def test_at_most_three_paid_searches_a_run(self):
        from seolib import serper
        serper.start_run(3)
        got = [serper._take("search", f"q{i}") for i in range(5)]
        self.assertEqual(got, [True, True, True, False, False])
        self.assertEqual(len(serper.spent()["refused"]), 2)
        serper.start_run(None)

    def test_a_capped_search_returns_an_error_without_calling(self):
        import asyncio
        from seolib import serper
        serper.start_run(0)

        class NoCall:
            async def post(self, *a, **k):
                raise AssertionError("a capped search must not reach Serper")
        with patch("seolib.common.load_json", return_value=None):
            r = asyncio.run(serper._call_once(NoCall(), "search", "fence paint", "uk", "en", []))
        self.assertTrue(r.get("capped"))
        serper.start_run(None)


class SuggestTests(unittest.TestCase):
    def test_suggestions_take_the_shape_the_pipeline_reads(self):
        from seolib import suggest
        self.assertEqual(suggest.as_serper(["a", "b"]), {"suggestions": [{"value": "a"}, {"value": "b"}]})
        self.assertEqual(suggest.many([], "en-GB"), {})

    def test_a_blocked_or_broken_response_gives_no_suggestions(self):
        import asyncio
        from seolib import suggest

        class Resp:
            status_code, content, encoding = 429, b"", "utf-8"

        class Client:
            async def get(self, *a, **k):
                return Resp()
        with patch("seolib.common.load_json", return_value=None):
            self.assertEqual(asyncio.run(suggest._one(Client(), "fence paint", "en-GB")), [])


if __name__ == "__main__":
    unittest.main()
