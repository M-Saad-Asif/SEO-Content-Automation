"""The owner's rules of 17 Oct 2026: a page's scope (global or one country) decides its sources and market filters;
other online calculator websites are never named or linked; competitors' sentences about their own tools never
become facts; a query that mixes needs opens with a compact list linking the client's calculators."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib.lint import lint_text  # noqa: E402


class ScopeTests(unittest.TestCase):
    def test_scope_comes_from_the_query_then_the_client_then_the_market(self):
        from seolib.market import infer_scope, filter_locale
        site = {"locale": "en-GB", "default_scope": "global"}
        self.assertEqual(infer_scope({**site, "target_query": "compound interest calculator"}), "global")
        self.assertEqual(infer_scope({**site, "target_query": "salary calculator uk"}), "gb")
        self.assertEqual(infer_scope({**site, "target_query": "401k calculator"}), "us")
        self.assertEqual(infer_scope({"locale": "en-GB", "target_query": "fence paint drying"}), "gb")  # a UK shop
        self.assertEqual(infer_scope({**site, "target_query": "isa calculator", "scope": "global"}), "global")
        self.assertEqual(filter_locale({**site, "target_query": "bmi calculator"}), "en")  # no market filter
        self.assertEqual(filter_locale({**site, "target_query": "stamp duty calculator"}), "en-GB")

    def test_a_global_page_keeps_every_countrys_facts(self):
        from seolib.graph import foreign, market_of
        self.assertFalse(foreign("The IRS taxes interest at 22% for this bracket in the United States.",
                                 *market_of("en")))
        self.assertTrue(foreign("The IRS taxes interest at 22% for this bracket in the United States.",
                                *market_of("en-GB")))

    def test_the_page_job_states_the_scope_and_a_tool_page_has_no_contact_step(self):
        from seolib.pagejob import lines
        sheet = {"brief": {"page_type": "tool", "client": "Acme", "target_query": "compound interest calculator",
                           "scope": "global"},
                 "client": {"offer": {"ctas": [{"text": "Get in touch", "url": "https://acme.com/contact"}]}}}
        text = "\n".join(lines(sheet))
        self.assertIn("Scope: **global**", text)
        self.assertNotIn("acme.com/contact", text)


class CompetitorContentTests(unittest.TestCase):
    def test_a_pages_sentences_about_its_own_tool_are_not_facts(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("sf", ROOT / "plugins" / "serp_facts" / "run.py")
        sf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sf)
        for s in ("The tool is one of five calculators that together show whether a deal works.",
                  "An eligibility check takes about 10 minutes and won't affect your credit score.",
                  "Market introduces customers to Royal London Equity Release Advisers.",
                  "Use the calculator above to see your payment."):
            self.assertTrue(sf.TOOL_SELF.search(s), s)
        self.assertFalse(sf.TOOL_SELF.search("Lenders work out interest monthly at one twelfth of the annual rate."))

    def test_other_calculator_sites_are_never_named_or_linked_and_no_self_link(self):
        sheet = {"brief": {"target_query": "compound interest calculator", "client": "Acme", "domain": "acme.com",
                           "locale": "en-GB", "page_type": "tool", "page_url": "https://acme.com/compound",
                           "competitor_sites": ["omnicalculator.com"], "word_range": [10, 9000]},
                 "facts": [], "client": {}, "products": []}
        md = ("---\ntitle: x\nmeta_description: x\n---\n\n# Compound interest calculator\n\nIt adds interest.\n\n"
              "## How does it work?\n\nOmnicalculator shows the same result. See [this page](https://acme.com/compound).\n")
        rules = {f["rule"] for f in lint_text(md, sheet, {}, {})["findings"] if f["severity"] == "block"}
        self.assertIn("C04-calculator-site", rules)
        self.assertIn("U25-self-link", rules)

    def test_fact_notes_drop_buttons_and_links(self):
        from seolib.writebrief import note
        got = note("Check National Minimum Wage rates before March 2026. [ Start now ](https://www.gov.uk/am-i/y)")
        self.assertNotIn("gov.uk", got)
        self.assertNotIn("Start", got)


class PlanTests(unittest.TestCase):
    def _plan(self, outline, current=None, lm=None):
        from seolib import common as C
        from seolib.plan import build
        d = tempfile.mkdtemp()
        rd = Path(d)
        (rd / "research").mkdir()
        C.save_json(rd / "fact_sheet.json", {"brief": {"target_query": "equity loan interest calculator", "client": "Acme",
                                                       "domain": "acme.com", "locale": "en-GB", "page_type": "tool",
                                                       "task": "rewrite" if current else "new", "word_range": [10, 9000],
                                                       "page_url": "https://acme.com/property/equity-loan-interest-calculator"},
                                             "facts": []})
        C.save_json(rd / "research" / "topic_outline.json", outline)
        if current:
            C.save_json(rd / "research" / "current_page.json", current)
        if lm:
            C.save_json(rd / "link_map.json", lm)
        return build(rd)

    def test_a_question_asked_two_ways_is_one_heading(self):
        q = lambda x: {"q": x, "decision": "cover_in_section"}
        plan = self._plan({"sections": [
            {"id": "S1", "title": "Second home mortgages", "covered_by": ["a", "b"], "questions": [q("Can I get a mortgage on a second home?")]},
            {"id": "S2", "title": "Deposits for a second home", "covered_by": ["a", "b"], "questions": [q("Can I get a mortgage on a second home?"), q("Can I get a mortgage for a second home?")]}],
            "single_site_angles": [], "single_site_questions": [], "other_searches": []})
        subs = [x["title"] for h in plan["headings"] for x in h["subs"]]
        self.assertLessEqual(sum("second home" in s.lower() for s in subs), 1)  # never a heading per phrasing
        asked = [x for h in plan["headings"] for x in h["questions"]]
        self.assertIn("Can I get a mortgage for a second home?", asked)  # answered in the section that covers it

    def test_the_live_pages_form_labels_are_not_headings(self):
        plan = self._plan({"sections": [], "single_site_angles": [], "single_site_questions": [], "other_searches": []},
                          current={"exists": True, "blocks": [
                              ["h2", "I want to see the calculations for an hourly wage of £ and hours per week"],
                              ["p", "Enter your hourly wage and the hours you work each week to see the totals."],
                              ["h2", "How your pay is worked out"], ["p", "Weekly pay is the hourly rate times the hours."]]})
        titles = [h["title"] for h in plan["headings"]]
        self.assertIn("How your pay is worked out", titles)
        self.assertFalse(any(t.lower().startswith("i want to see") for t in titles))

    def test_a_query_that_mixes_needs_lists_the_clients_other_calculators(self):
        q = lambda x: {"q": x, "decision": "cover_in_section"}
        plan = self._plan({"sections": [
            {"id": "S1", "title": "Help to Buy equity loan interest", "headings": ["Help to Buy equity loan interest", "Help to Buy interest"], "covered_by": ["a"], "questions": []},
            {"id": "S2", "title": "Equity release interest", "headings": ["Equity release interest rates", "How equity release interest rolls up"], "covered_by": ["b"], "questions": []}],
            "single_site_angles": [], "single_site_questions": [],
            "other_searches": [{"q": "help to buy equity loan interest"}, {"q": "equity release interest calculator"}]},
            lm={"client_candidates": ["https://acme.com/property/equity-release-compound-interest-calculator",
                                      "https://acme.com/property/help-to-buy-equity-loan-calculator",
                                      "https://acme.com/finance/currency-converter"], "client_related": {}})
        urls = [m["url"] for m in plan.get("meanings", [])]
        self.assertIn("https://acme.com/property/equity-release-compound-interest-calculator", urls)
        self.assertIn("https://acme.com/property/help-to-buy-equity-loan-calculator", urls)
        self.assertNotIn("https://acme.com/finance/currency-converter", urls)


class FactCheckSelectionTests(unittest.TestCase):
    def test_a_tax_rule_without_a_number_is_checked(self):
        from seolib.verify import SENSITIVE
        self.assertTrue(SENSITIVE.search("Most salary sacrifice arrangements save National Insurance rather than income tax."))
        self.assertFalse(SENSITIVE.search("Seal the overflow with a damp cloth."))


if __name__ == "__main__":
    unittest.main()
