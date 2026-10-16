"""Regressions from the Cursor run on calculatorssite.com's compound interest calculator (17 Oct 2026): US results for
a UK brief, a calculator read as a service page, a rewrite that dropped the live page, menu links as sections, a
formula section without the formula, and checks that misread quotes and calendar arithmetic."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib.lint import lint_text  # noqa: E402

SHEET = {"brief": {"target_query": "compound interest calculator", "client": "Acme", "domain": "acme.com",
                   "locale": "en-GB", "page_type": "tool", "word_range": [50, 5000]}, "facts": [], "client": {},
         "products": []}


def blocks(md: str, facts=()) -> set[str]:
    sheet = json.loads(json.dumps(SHEET))
    sheet["facts"] = list(facts)
    return {f["rule"] for f in lint_text(md, sheet, {}, {})["findings"] if f["severity"] == "block"}


class MarketTests(unittest.TestCase):
    def test_the_uk_is_searched_as_gb(self):
        from seolib.serper import locale_params
        self.assertEqual(locale_params("en-GB"), ("gb", "en"))
        self.assertEqual(locale_params("en-UK"), ("gb", "en"))
        self.assertEqual(locale_params("en-AU"), ("au", "en"))


class ToolPageTests(unittest.TestCase):
    def test_a_calculator_is_a_tool_page_not_a_service(self):
        from seolib.pagetype import classify, infer_type
        doc = {"title": "Compound interest calculator", "blocks": [["h1", "Compound interest calculator"],
               ["p", "Enter a starting balance from £1,000 and a rate. Rates from 4%. £36,904.12 after 10 years."]]}
        html = '<form><input type="number"><input type="number"><select></select></form>'
        self.assertEqual(classify("https://acme.com/finance/compound-interest-calculator", doc, html)[0], "tool")
        self.assertEqual(infer_type("", "bmi calculator")[0], "tool")
        self.assertEqual(infer_type("", "how does a mortgage calculator work")[0], "guide")

    def test_a_formula_section_shows_the_formula_and_an_example_shows_figures(self):
        md = ("---\ntitle: x\nmeta_description: x\n---\n\n# Compound interest calculator\n\nIt adds interest.\n\n"
              "## What is the compound interest formula?\n\nThe formula links the balance to the rate and the term.\n\n"
              "## Worked example\n\nPut in your balance and read the result.\n")
        got = blocks(md)
        self.assertIn("F01-formula-missing", got)
        self.assertIn("F02-example-without-figures", got)
        md2 = md.replace("The formula links the balance to the rate and the term.",
                         "A = P(1 + r/n)^(nt), where P is the balance.").replace(
            "Put in your balance and read the result.", "£1,000 at 5% for 10 years gives £1,628.89.")
        self.assertFalse({"F01-formula-missing", "F02-example-without-figures"} & blocks(md2))

    def test_a_table_never_talks_about_the_search(self):
        md = ("---\ntitle: x\nmeta_description: x\n---\n\n# Compound interest calculator\n\nIt adds interest.\n\n"
              "| What you searched | What it covers |\n|---|---|\n| Monthly | Interest each month |\n")
        self.assertIn("H05-meta-commentary", blocks(md))


class CheckMisreadTests(unittest.TestCase):
    def test_a_quote_holding_a_full_stop_is_not_copied_text(self):
        q = "You are using an annual rate, but compounding by a number of months. Change the rate to a monthly one"
        fact = {"id": "gain:1", "status": "verified", "basis": "gain_mistake", "value": q,
                "source_url": "https://forum.example.org/t/1"}
        md = ("---\ntitle: x\nmeta_description: x\n---\n\n# Compound interest calculator\n\nIt adds interest.\n\n"
              f"## Why do results differ?\n\nA forum poster wrote, \"{q}\", after a spreadsheet gave a different answer.\n")
        self.assertNotIn("C03-copied-text", blocks(md, [fact]))

    def test_months_in_a_term_are_worked_arithmetic(self):
        fact = {"id": "live:1", "status": "verified", "basis": "client_page", "source_url": "https://acme.com/x",
                "value": "Starting with £5,000 and adding £200 a month at 4% for 10 years gives £36,904.12."}
        md = ("---\ntitle: x\nmeta_description: x\n---\n\n# Compound interest calculator\n\nIt adds interest.\n\n"
              "## Worked example\n\nAdd £200 a month for 10 years, which is 120 monthly payments, on top of "
              "£5,000 at 4%: the balance reaches £36,904.12.\n")
        self.assertNotIn("N01-untraced-number", blocks(md, [fact]))


class RewritePlanTests(unittest.TestCase):
    def test_a_rewrite_keeps_the_live_pages_sections_and_drops_menu_links(self):
        from seolib import common as C
        from seolib.plan import build
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            (rd / "research").mkdir()
            sheet = json.loads(json.dumps(SHEET))
            sheet["brief"].update(task="rewrite", page_url="https://acme.com/finance/compound-interest-calculator")
            C.save_json(rd / "fact_sheet.json", sheet)
            C.save_json(rd / "research" / "current_page.json", {"exists": True, "blocks": [
                ["h2", "The compound interest formula"], ["p", "The balance after t years is P × (1 + r/n)^(n × t) for a deposit."],
                ["h2", "Worked example with monthly contributions"],
                ["p", "Starting with £5,000 and adding £200 a month at 4% for 10 years gives £36,904.12."],
                ["h2", "Inputs for the compound interest calculator"], ["h3", "Starting balance"],
                ["p", "The amount you have saved already, or 0 if you are starting from nothing."]]})
            C.save_json(rd / "research" / "competitor_scrape.json", {"pages": [{"blocks": [
                ["h2", "Pension calculator"], ["li", "Pension calculator"], ["h2", "Discover more savings tools"],
                ["li", "ISA calculator"]]}]})
            C.save_json(rd / "research" / "topic_outline.json", {"sections": [], "single_site_angles": [
                "Pension calculator", "Discover more savings tools"], "single_site_questions": [], "other_searches": []})
            plan = build(rd)
            titles = [h["title"] for h in plan["headings"]]
            self.assertEqual(titles[:3], ["The compound interest formula", "Worked example with monthly contributions",
                                          "Inputs for the compound interest calculator"])
            self.assertFalse({"Pension calculator", "Discover more savings tools"} & set(titles))
            self.assertTrue(any(i.startswith("live:") for i in plan["headings"][0]["facts"]))
            self.assertIn("write the formula itself", plan["headings"][0].get("note", ""))
            self.assertNotIn("Worked example", titles)  # the live page's own worked example is the one


if __name__ == "__main__":
    unittest.main()
