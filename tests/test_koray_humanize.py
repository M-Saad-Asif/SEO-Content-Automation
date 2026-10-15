"""Offline regressions for Koray's rules (RULES.md section 7), the humanization checks from the University of Maryland
/ Google DeepMind research (seolib/humanize.py), the mechanical auto-fixes, and the writer sub-agent in every tool."""
from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib.autofix import fix_text  # noqa: E402
from seolib.lint import lint_text  # noqa: E402

SHEET = {"brief": {"target_query": "how long does fence paint take to dry", "client": "Acme", "domain": "acme.co.uk",
                   "locale": "en-GB", "page_type": "guide", "word_range": [50, 5000]},
         "facts": [], "client": {}, "products": []}


def rules(body: str) -> set[str]:
    md = "---\ntitle: How long does fence paint take to dry\nmeta_description: x\n---\n\n# How long does fence paint " \
         "take to dry\n\n" + body
    return {f["rule"] for f in lint_text(md, SHEET, {}, {})["findings"] if f["severity"] == "block"}


class KorayTests(unittest.TestCase):
    def test_hedging_and_opinion_are_blocked_and_the_declaration_passes(self):
        self.assertIn("K10-hedge", rules("Older fences should be treated before painting.\n"))
        self.assertIn("K10-hedge", rules("You should check the tin first.\n"))
        self.assertIn("K11-opinion", rules("We'd recommend a water-based paint for most fences.\n"))
        got = rules("Treat older fences before painting.\n")
        self.assertFalse({"K10-hedge", "K11-opinion"} & got)

    def test_need_to_inside_a_clause_is_not_a_hedge(self):
        self.assertNotIn("K10-hedge", rules("The leak's position decides which part you need to replace.\n"))

    def test_vague_quantities_need_a_number_or_examples(self):
        self.assertIn("K12-vague-quantity", rules("There are several ways to speed up drying.\n"))
        self.assertNotIn("K12-vague-quantity", rules("There are several ways to speed up drying, such as warm air and thin coats.\n"))
        self.assertNotIn("K12-vague-quantity", rules("There are 3 ways to speed up drying.\n"))

    def test_if_goes_second(self):
        self.assertIn("K04-if-opener", rules("If rain is due, wait for a dry day.\n"))
        self.assertNotIn("K04-if-opener", rules("Wait for a dry day if rain is due.\n"))

    def test_bold_the_answer_not_the_search_term(self):
        self.assertIn("K05-bold-search-term", rules("**Fence paint** dries in about 2 hours.\n"))
        self.assertNotIn("K05-bold-search-term", rules("Fence paint dries in about **2 hours**.\n"))

    def test_list_items_start_with_the_same_part_of_speech(self):
        mixed = "- Clean the fence.\n- Sanding of rough patches.\n- Apply two thin coats.\n- Wait for a dry day.\n"
        same = "- Clean the fence.\n- Sand rough patches.\n- Apply two thin coats.\n- Wait for a dry day.\n"
        self.assertIn("K14-list-mixed", rules(mixed))
        self.assertNotIn("K14-list-mixed", rules(same))

    def test_no_skipped_heading_levels(self):
        self.assertIn("K16-skipped-level", rules("### How long fence paint takes in rain\n\nIt takes 4 hours.\n"))
        self.assertNotIn("K16-skipped-level", rules("## Drying times\n\nFence paint dries in 2 hours.\n\n"
                                                     "### Drying in rain\n\nRain adds 2 hours.\n"))

    def test_answering_in_the_headings_terms_is_not_an_echo(self):
        body = "".join(f"## How long does {w} fence paint take to dry\n\n{w.capitalize()} fence paint takes {n} hours "
                       f"to dry at 20 °C on dry, planed timber.\n\n" for w, n in
                       (("oil", 6), ("water", 2), ("spray", 1), ("stain", 4)))
        md = "---\ntitle: x\nmeta_description: x\n---\n\n# How long does fence paint take to dry\n\n" + body
        found = {f["rule"] for f in lint_text(md, SHEET, {}, {})["findings"]}
        self.assertNotIn("H08-heading-echo", found)


class HumanizeTests(unittest.TestCase):
    def test_ai_idea_patterns_are_blocked(self):
        cases = {
            "HU02-perfect-solution": "Our fence paint is the perfect solution for every garden.\n",
            "HU03-unconditional-forecast": "Water-based paints will always replace oil-based ones.\n",
            "HU04-vague-authority": "Experts say two coats of fence paint last longer.\n",
            "HU05-made-up-example": "Imagine a homeowner who paints a fence the day before a storm.\n",
            "HU06-stated-lesson": "The key takeaway is that fence paint needs dry weather.\n",
        }
        for rule, text in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, rules(text))

    def test_a_named_linked_source_is_not_a_vague_authority(self):
        self.assertNotIn("HU04-vague-authority", rules("The [RHS](https://www.rhs.org.uk/x) found that two coats last longer.\n"))

    def test_a_long_page_must_state_its_limits(self):
        filler = "Fence paint dries to the touch in about 2 hours in warm weather at 20 degrees. " * 60
        self.assertIn("HU08-no-limits", rules(filler + "\n"))
        self.assertNotIn("HU08-no-limits", rules(filler + "This does not apply to oil-based paint, which takes longer.\n"))


class AutofixTests(unittest.TestCase):
    def test_if_clause_moves_second_and_fluff_is_cut(self):
        md, n = fix_text("# H\n\nIf rain is due, wait for a dry day. Basically, paint dries fast.\n")
        self.assertIn("Wait for a dry day if rain is due.", md)
        self.assertIn("Paint dries fast.", md)
        self.assertEqual(n, 2)

    def test_links_quotes_and_headings_are_left_alone(self):
        src = "## If it rains\n\nIf [the guide](http://x) says so, do it.\n"
        self.assertEqual(fix_text(src)[0], src)


class SchemaTests(unittest.TestCase):
    def test_json_ld_names_the_central_entity_and_only_entities_on_the_page(self):
        import tempfile
        from seolib.schema import build
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            (rd / "research").mkdir()
            (rd / "final.md").write_text("---\ntitle: Fix a tap\nmeta_description: How to fix a tap.\nupdated: 2026-10-16\n"
                                         "---\n\n# How to fix a leaking tap\n\nReplace the washer.\n", encoding="utf-8")
            (rd / "fact_sheet.json").write_text(json.dumps({"brief": {"client": "Acme", "domain": "acme.co.uk",
                                                "page_type": "guide", "locale": "en-GB", "page_url": "https://acme.co.uk/t"}}),
                                                encoding="utf-8")
            (rd / "research" / "semantic_graph.json").write_text(json.dumps({
                "graph": {"entities": [{"name": "leaking taps", "type": "central"}]},
                "must_cover_entities": ["washer", "faucet"]}), encoding="utf-8")
            node = build(rd)["@graph"][1]
            self.assertEqual(node["@type"], "Article")
            self.assertEqual(node["about"]["name"], "leaking taps")
            self.assertEqual([m["name"] for m in node["mentions"]], ["washer"])
            self.assertEqual(node["dateModified"], "2026-10-16")


class WriterAgentTests(unittest.TestCase):
    def test_every_tool_gets_a_valid_writer_with_the_same_instructions(self):
        import install_adapters as I
        agents = I.writer_agents(I.HOME)
        self.assertEqual(set(agents), {"cursor", "codex", "antigravity", "gemini", "copilot"})
        prompts = set()
        for tool, items in agents.items():
            path, text = items[0]
            if path.suffix == ".toml":
                data = tomllib.loads(text)
                self.assertEqual(data["name"], "seo_writer")
                prompts.add(data["developer_instructions"].strip())
            else:
                front = yaml.safe_load(text.split("---")[1])
                self.assertEqual(front["name"], "seo-writer")
                self.assertTrue(front["description"])
                prompts.add(text.split("---", 2)[2].strip())
        self.assertEqual(len(prompts), 1)  # one writer, the same in every tool


if __name__ == "__main__":
    unittest.main()
