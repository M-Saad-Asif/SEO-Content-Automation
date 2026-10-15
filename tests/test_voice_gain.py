"""Offline regressions for the author's view (first person, 2-3 times, top and middle, no invented experience),
information gain from the researchers (seolib/gain.py), and the GEO evidence checks (citations, exact quotes)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib.lint import lint_text  # noqa: E402

FILL = ("Fence paint dries to the touch in 2 hours at 20 degrees on planed timber, and rough sawn boards take longer "
        "because they hold more water. ")


def sheet(facts=()):
    return {"brief": {"target_query": "how long does fence paint take to dry", "client": "Acme", "domain": "acme.co.uk",
                      "locale": "en-GB", "page_type": "guide", "word_range": [50, 5000]},
            "facts": list(facts), "client": {}, "products": []}


def page(sections: list[str], opening: str = "Fence paint dries in about 2 hours at 20 degrees.") -> str:
    body = "".join(f"## Section {i + 1} about fence paint drying\n\n{s}\n\n" for i, s in enumerate(sections))
    return f"---\ntitle: Fence paint\nmeta_description: x\n---\n\n# How long does fence paint take to dry\n\n{opening}\n\n{body}"


def found(md: str, facts=()) -> set[str]:
    return {f["rule"] for f in lint_text(md, sheet(facts), {}, {})["findings"] if f["severity"] == "block"}


VIEW = "I'd pick a water-based paint for a fence you want to recoat the same day, because it dries in 1 hour. "


class AuthorViewTests(unittest.TestCase):
    def test_every_page_needs_two_to_three_views_in_the_top_and_middle(self):
        plain = [FILL * 8 for _ in range(8)]
        self.assertIn("V01-author-view-count", found(page(plain)))
        good = list(plain)
        good[1], good[3] = FILL * 6 + VIEW, FILL * 6 + VIEW
        got = found(page(good))
        self.assertFalse({"V01-author-view-count", "V02-view-placement"} & got)

    def test_a_view_in_the_opening_or_the_last_part_is_moved(self):
        late = [FILL * 8 for _ in range(8)]
        late[1], late[7] = FILL * 6 + VIEW, FILL * 6 + VIEW
        self.assertIn("V02-view-placement", found(page(late)))
        opening = [FILL * 8 for _ in range(8)]
        opening[2] = FILL * 6 + VIEW
        self.assertIn("V02-view-placement", found(page(opening, opening=VIEW)))

    def test_more_than_three_views_is_too_many(self):
        many = [FILL * 6 + VIEW for _ in range(6)] + [FILL * 8 for _ in range(6)]
        self.assertIn("V01-author-view-count", found(page(many)))

    def test_opinion_is_allowed_but_claimed_experience_is_not(self):
        secs = [FILL * 8 for _ in range(8)]
        secs[1] = FILL * 6 + "I think oil-based paint is the better buy, because it lasts 5 years."
        secs[3] = FILL * 6 + "I tested three paints on my own fence last summer."
        got = found(page(secs))
        self.assertNotIn("K11-opinion", got)
        self.assertIn("V03-claimed-experience", got)
        secs[3] = FILL * 6 + "In my experience, two coats last longer."
        self.assertIn("V03-claimed-experience", found(page(secs)))


class GainAndGeoTests(unittest.TestCase):
    GAIN = [{"id": f"gain:{i}", "status": "verified", "kind": "data", "basis": "gain_data", "who": f"Source {i}",
             "point": p, "value": p, "source_url": f"https://site{i}.org/page"} for i, p in enumerate(
        ["Cedar boards absorb twice as much paint as pine boards", "Spraying uses thirty percent more paint than "
         "brushing outdoors", "Painting below ten degrees doubles the drying time for most paints"], 1)]

    def test_items_beyond_page_one_must_be_used(self):
        secs = [FILL * 6 + VIEW, FILL * 8, FILL * 6 + VIEW] + [FILL * 8 for _ in range(5)]
        self.assertIn("IG01-no-information-gain", found(page(secs), self.GAIN))
        for i, f in enumerate(self.GAIN):
            secs[4 + i] = FILL * 6 + f"[{f['who']}]({f['source_url']}) found that {f['point'].lower()}."
        self.assertNotIn("IG01-no-information-gain", found(page(secs), self.GAIN))

    def test_the_page_cites_the_outside_sources_it_has(self):
        secs = [FILL * 6 + VIEW, FILL * 8, FILL * 6 + VIEW] + [FILL * 8 for _ in range(5)]
        self.assertIn("G02-few-citations", found(page(secs), self.GAIN))

    def test_quotes_are_required_and_exact(self):
        quote = "Paint should not be applied when rain is expected within 24 hours of application"
        fact = {"id": "auth:1", "status": "verified", "basis": "official_page", "value": quote,
                "source_url": "https://www.gov.uk/x"}
        secs = [FILL * 6 + VIEW, FILL * 8, FILL * 6 + VIEW] + [FILL * 8 for _ in range(5)]
        self.assertIn("G03-no-quotation", found(page(secs), [fact]))
        secs[4] = FILL * 6 + f"[GOV.UK](https://www.gov.uk/x) says \"{quote}\"."
        got = found(page(secs), [fact])
        self.assertFalse({"G03-no-quotation", "G04-misquote"} & got)
        secs[4] = FILL * 6 + "[GOV.UK](https://www.gov.uk/x) says \"Paint must never be applied when any rain " \
                             "is expected within a day\"."
        self.assertIn("G04-misquote", found(page(secs), [fact]))

    def test_two_short_quoted_words_are_not_one_long_quote(self):
        secs = [FILL * 6 + VIEW, FILL * 8, FILL * 6 + VIEW] + [FILL * 8 for _ in range(5)]
        secs[4] = "CEAC shows \"REFUSED\" while your case is still being processed and later shows \"ISSUED\"."
        self.assertNotIn("G04-misquote", found(page(secs)))


class GainModuleTests(unittest.TestCase):
    def test_parse_keeps_well_formed_items_and_checks_quotes(self):
        from seolib import gain
        text = ("```yaml\n- kind: experience\n  point: A forum member found two thin coats beat one thick coat\n"
                "  quote: two thin coats lasted far longer than one thick coat on my fence\n"
                "  source: https://www.diynot.com/forums/x\n  who: a member of the DIYnot forum\n  date: 2025\n"
                "- kind: data\n  point: too short\n  quote: x\n  source: nope\n```")
        items = gain.parse(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "experience")
        page_text = "Reply: Honestly, two thin coats lasted far longer than one thick coat on my fence. Cheers"
        self.assertTrue(gain.quote_on_page(items[0]["quote"], page_text))
        self.assertFalse(gain.quote_on_page("one coat is always enough for any fence anywhere", page_text))

    def test_register_drops_page_one_points_competitors_and_unchecked_figures(self):
        from seolib import gain
        from seolib import common as C
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            (rd / "research").mkdir()
            C.save_json(rd / "fact_sheet.json", sheet())
            C.save_json(rd / "research" / "serp_intel.json",
                        {"organic": [{"domain": "rivalpaints.co.uk", "kind": "ecommerce"}]})
            C.save_json(rd / "research" / "competitor_scrape.json", {"pages": [{"blocks": [
                ["p", "Most fence paints are touch dry in about two hours in warm weather."]]}]})
            base = {"who": "x", "date": ""}
            items = [
                {**base, "kind": "data", "point": "Cedar absorbs twice as much paint as pine", "quote": "cedar absorbs "
                 "twice as much paint as pine in our tests", "source": "https://lab.org/a", "quote_found": True},
                {**base, "kind": "data", "point": "Most fence paints are touch dry in about two hours",
                 "quote": "most fence paints are touch dry in about two hours in warm weather",
                 "source": "https://blog.org/b", "quote_found": True},
                {**base, "kind": "data", "point": "Rival paint lasts 9 years on fences", "quote": "our paint lasts 9 "
                 "years on any fence", "source": "https://rivalpaints.co.uk/c", "quote_found": True},
                {**base, "kind": "data", "point": "Sprayers waste 30 percent of the paint", "quote": "sprayers waste "
                 "30 percent of the paint you buy", "source": "https://forum.org/d", "quote_found": False},
                {**base, "kind": "experience", "point": "A member found the second coat went on much faster",
                 "quote": "the second coat went on much faster than the first one did", "source": "https://forum.org/e",
                 "quote_found": False},
            ]
            C.save_json(rd / "research" / "gain.json", {"items": items})
            kept = gain.register(rd)
            self.assertEqual([f["source_url"] for f in kept], ["https://lab.org/a", "https://forum.org/e"])
            self.assertEqual([f["status"] for f in kept], ["verified", "captured"])
            ids = [f["id"] for f in C.load_json(rd / "fact_sheet.json")["facts"]]
            self.assertEqual(ids, ["gain:1", "gain:2"])


class PlanViewTests(unittest.TestCase):
    def test_views_go_to_decision_headings_in_the_first_seventy_percent(self):
        from seolib.plan import mark_views
        heads = [{"title": t, "kind": "topic", "subs": [], "questions": [], "facts": []} for t in
                 ["What fence paint is", "Which fence paint is best", "How long it takes", "Oil vs water based paint",
                  "Drying in cold weather", "How to choose a sprayer", "Cleaning brushes", "Storing leftover paint",
                  "Disposing of paint", "Get started"]]
        mark_views(heads, {})
        idx = [i for i, h in enumerate(heads) if h.get("view")]
        self.assertEqual(len(idx), 3)
        self.assertTrue(all((i + 1) / len(heads) <= 0.7 for i in idx))
        self.assertIn(1, idx)
        self.assertIn(3, idx)


class ResearcherAgentTests(unittest.TestCase):
    def test_the_researcher_is_installed_in_every_tool_with_the_same_instructions(self):
        import install_adapters as I
        agents = I.researcher_agents(I.HOME)
        self.assertEqual(set(agents), {"cursor", "codex", "antigravity", "gemini", "copilot"})
        prompts = set()
        for tool, items in agents.items():
            path, text = items[0]
            if path.suffix == ".toml":
                import tomllib
                prompts.add(tomllib.loads(text)["developer_instructions"].strip())
            else:
                prompts.add(text.split("---", 2)[2].strip())
        self.assertEqual(len(prompts), 1)
        self.assertIn("gain_<X>.yaml", prompts.pop())

    def test_first_step_starts_research_in_background_and_prints_the_researchers_task(self):
        import contextlib
        import io
        from unittest.mock import patch
        from seolib import common as C, driver, prep
        C.RUNS.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=C.RUNS, prefix="zz-test-") as d:  # run folders live inside the repo
            rd = Path(d) / "2026-10-16-fence-paint"
            brief = {"target_query": "how long does fence paint take to dry", "client": "Acme", "domain": "acme.co.uk",
                     "locale": "en-GB", "page_type": "guide", "slug": "fence-paint", "_path": "briefs/x.yaml"}
            out = io.StringIO()
            with patch.object(prep, "load_brief", return_value=brief), patch.object(prep, "run_dir", return_value=rd), \
                    patch.object(driver, "_current_run", side_effect=lambda b: rd if rd.exists() else None), \
                    patch.object(driver, "_research_in_background", return_value=True) as bg, \
                    patch.object(driver, "_in_repo", return_value=True), contextlib.redirect_stdout(out):
                driver.next_step("briefs/x.yaml")
            text = out.getvalue()
            bg.assert_called_once()
            self.assertIn("RESEARCH BEYOND PAGE ONE", text)
            self.assertIn("seo-gain-researcher", text)
            self.assertIn("gain_X.yaml", text)
            self.assertTrue(json.loads((rd / "state.json").read_text(encoding="utf-8")).get("gain_asked"))

    def test_every_claude_agent_file_has_valid_frontmatter(self):
        # an unquoted ": " in a description once made Claude Code drop the seo-writer agent without a word
        import yaml
        for f in sorted((ROOT / ".claude" / "agents").glob("*.md")):
            with self.subTest(agent=f.name):
                front = yaml.safe_load(f.read_text(encoding="utf-8").split("---")[1])
                self.assertEqual(front["name"], f.stem)
                self.assertTrue(front["description"])

    def test_alive_tells_a_running_process_from_a_finished_one(self):
        from seolib.driver import _alive
        self.assertTrue(_alive(os.getpid()))
        self.assertFalse(_alive(0))
        self.assertFalse(_alive(2 ** 22 + 12345))


if __name__ == "__main__":
    unittest.main()
