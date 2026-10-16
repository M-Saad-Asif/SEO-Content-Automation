"""The owner's rule of 17 Oct 2026: the rates a site's calculators run on (Calcsite's src/data/rates, kept from
official sources) are verified facts for the pages they apply to; anything the page says that isn't in them keeps
the pipeline's own verification."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib import common as C  # noqa: E402
from seolib.siterates import facts_for, registry, load, numbers  # noqa: E402

INCOME_TAX_TS = '''/**
 * UK income tax on employment income, by tax year (decision D7). Band limits
 * are of taxable income, i.e. after the Personal Allowance.
 * Check after every Budget and before each 6 April.
 */
export type TaxBand = { upTo: number; rate: number };

export type IncomeTaxYear = {
  personalAllowance: number;
  /** The allowance falls by £1 for every £2 of adjusted net income above this. */
  taperThreshold: number;
  /** England, Wales and Northern Ireland. The last band has upTo: Infinity. */
  rest: TaxBand[];
};

export const incomeTax: Record<string, IncomeTaxYear> = {
  "2026-27": { personalAllowance: 12_570, taperThreshold: 100_000,
               rest: [{ upTo: 37_700, rate: 20 }, { upTo: 125_140, rate: 40 }, { upTo: Infinity, rate: 45 }] },
};

export const currentTaxYear = "2026-27";

export const incomeTaxSource = {
  name: "GOV.UK: Income Tax rates and allowances for current and past years",
  url: "https://www.gov.uk/government/publications/rates-and-allowances-income-tax/income-tax-rates-and-allowances-current-and-past",
  lastChecked: "2026-10-14",
} as const;
'''

DATA = {
    "uk/income-tax.ts": {
        "currentTaxYear": "2026-27",
        "incomeTax": {"2026-27": {"personalAllowance": 12570, "taperThreshold": 100000,
                                  "rest": [{"upTo": 37700, "rate": 20}, {"upTo": 125140, "rate": 40},
                                           {"upTo": "Infinity", "rate": 45}]}},
        "incomeTaxSource": {"name": "GOV.UK: Income Tax rates and allowances for current and past years",
                            "url": "https://www.gov.uk/income-tax-rates", "lastChecked": "2026-10-14"}},
    "uk/student-loans.ts": {
        "studentLoanPlanNames": {"plan1": "Plan 1", "plan2": "Plan 2"},
        "studentLoanInterest": {"rates": {"plan1": 4.1, "plan2": 4.1}, "period": "September 2026"},
        "studentLoanWriteOffYears": {"plan1": 25, "plan2": 30},
        "studentLoanSources": [
            {"name": "GOV.UK: When your student loan gets written off or cancelled",
             "url": "https://www.gov.uk/repaying-your-student-loan/when-your-student-loan-gets-written-off-or-cancelled",
             "lastChecked": "2026-10-14"},
            {"name": "GOV.UK: Student loans interest rates and repayment threshold announcement (August 2026)",
             "url": "https://www.gov.uk/government/news/student-loans-interest-rates-and-repayment-threshold-announcement--7",
             "lastChecked": "2026-10-16"}]},
    "uk/vat.ts": {"vatRates": {"standard": 20, "reduced": 5, "zero": 0},
                  "vatSource": {"name": "GOV.UK: VAT rates", "url": "https://www.gov.uk/vat-rates", "lastChecked": "2026-10-14"}},
    "fx.ts": {"fxRates": {f"C{i:02d}": 1.0 + i for i in range(60)},
              "fxSource": {"name": "rates", "url": "https://example.org/fx", "lastChecked": "2026-10-01"}},
}


def brief(q, **kw):
    return {"client": "Calculators Site", "site_rates_dir": "unused", "target_query": q,
            "page_url": "https://www.calculatorssite.com/finance/" + q.replace(" ", "-"), "scope": "global", **kw}


class SiteRatesTests(unittest.TestCase):
    def test_the_rates_a_page_is_about_become_verified_facts_with_their_meaning(self):
        got = facts_for(brief("income tax calculator"), data=DATA, sources={"uk/income-tax.ts": INCOME_TAX_TS})
        self.assertEqual([f["id"] for f in got], ["rates:income-tax:incomeTax:2026-27"])
        f = got[0]
        self.assertEqual((f["status"], f["basis"], f["retrieved_at"], f["scope"]), ("verified", "site_rates", "2026-10-14", "UK"))
        self.assertIn("personal allowance: 12,570", f["value"])
        self.assertIn("20% up to 37,700, 40% up to 125,140, 45% above 125,140", f["value"])
        self.assertIn("falls by £1 for every £2", f["value"])  # the field's own comment gives the figure its meaning
        self.assertIn("(the current year)", f["value"])
        self.assertIn("after the Personal Allowance", f["meaning"])
        for upkeep in ("upTo", "Infinity", "Check after every Budget", "decision D7"):  # notes for the maintainer
            self.assertNotIn(upkeep, f["value"] + f["meaning"])

    def test_pages_the_data_is_not_about_get_none_and_a_us_page_never_gets_uk_rates(self):
        self.assertEqual(facts_for(brief("compound interest calculator"), data=DATA), [])
        self.assertEqual(facts_for(brief("income tax calculator", scope="us"), data=DATA), [])
        self.assertEqual(facts_for({"target_query": "income tax calculator"}), [])  # no rates folder in the profile

    def test_the_live_pages_own_text_can_make_a_module_apply(self):
        live = "Your take-home pay after income tax. Income tax is worked out on taxable income, and income tax bands..."
        got = facts_for(brief("salary calculator"), live_text=live, data=DATA)
        self.assertIn("rates:income-tax:incomeTax:2026-27", [f["id"] for f in got])

    def test_labels_and_lookup_tables_are_not_facts_and_each_value_names_its_own_source(self):
        got = {f["id"]: f for f in facts_for(brief("student loan calculator"), data=DATA)}
        self.assertNotIn("rates:student-loans:studentLoanPlanNames", got)
        self.assertIn("plan 1: 4.1%", got["rates:student-loans:studentLoanInterest"]["value"])
        self.assertIn("announcement", got["rates:student-loans:studentLoanInterest"]["source_url"])
        self.assertIn("written-off", got["rates:student-loans:studentLoanWriteOffYears"]["source_url"])
        self.assertEqual(facts_for(brief("currency converter", target_query="fx rates"), data=DATA), [])

    def test_the_register_names_pages_and_terms(self):
        d = Path(tempfile.mkdtemp())
        (d / "reg.md").write_text(
            "### income-tax\n- **Lives in:** `src/data/rates/uk/income-tax.ts`\n"
            "- **Find in articles:** \"Personal Allowance\", \"£12,570\", \"higher rate\", \"interest\"; pages salary-calculator.\n",
            encoding="utf-8")
        reg = registry(d / "reg.md")
        self.assertEqual(reg["uk/income-tax.ts"]["pages"], ["salary-calculator"])
        self.assertIn("Personal Allowance", reg["uk/income-tax.ts"]["terms"])
        b = brief("salary calculator", site_rates_registry=str(d / "reg.md"))
        self.assertTrue(facts_for(b, data=DATA))  # the register names this page
        b = brief("loan interest calculator", site_rates_registry=str(d / "reg.md"))
        b["page_url"] = "https://www.calculatorssite.com/finance/loan-interest-calculator"
        self.assertEqual(facts_for(b, data=DATA), [])  # a plain register word ("interest") doesn't name the topic

    def test_numbers_are_compared_without_their_formatting(self):
        self.assertEqual(numbers("The Personal Allowance is £12,570 and the basic rate 20%."), {"12570", "20"})

    @unittest.skipUnless(shutil.which("node"), "Node is not installed")
    def test_node_reads_the_typescript_modules(self):
        v = subprocess.run([shutil.which("node"), "--version"], capture_output=True, text=True).stdout
        major, minor = (int(x) for x in re.findall(r"\d+", v)[:2])
        if (major, minor) < (22, 6):
            self.skipTest("this Node can't load TypeScript")
        d = Path(tempfile.mkdtemp())
        (d / "uk").mkdir()
        (d / "uk" / "income-tax.ts").write_text(INCOME_TAX_TS, encoding="utf-8")
        data = load(d)
        if (major, minor) < (23, 6) and "__error" in data.get("uk/income-tax.ts", {}):
            self.skipTest("this Node needs --experimental-strip-types")
        self.assertEqual(data["uk/income-tax.ts"]["incomeTax"]["2026-27"]["rest"][2], {"upTo": "Infinity", "rate": 45})
        got = facts_for({**brief("income tax calculator"), "site_rates_dir": str(d)})
        self.assertIn("falls by £1", got[0]["value"])


class FactCheckTests(unittest.TestCase):
    def test_lines_the_rates_data_states_skip_the_fact_check_and_the_rest_keep_it(self):
        from seolib.verify import build_fast
        rd = Path(tempfile.mkdtemp())
        facts = facts_for(brief("income tax calculator"), data=DATA, sources={"uk/income-tax.ts": INCOME_TAX_TS})
        C.save_json(rd / "fact_sheet.json", {"brief": {"client": "Calculators Site", "target_query": "income tax calculator",
                                                       "page_type": "tool", "locale": "en-GB"}, "facts": facts})
        (rd / "draft.md").write_text(
            "# Income tax calculator\n\n"
            "In 2026-27 the Personal Allowance is £12,570 and the basic rate of income tax is 20%.\n\n"
            "## How is it worked out?\n\n"
            "The higher rate of income tax is 45% on taxable income above £37,700.\n\n"
            "In 2026-27 income tax is charged at 20% on taxable income up to £37,700.\n\n"
            "The basic rate of income tax in 2025-26 was 20% up to £37,700.\n\n"
            "On a salary of £30,000 the tax is (£30,000 − £12,570) × 20% = £3,486.\n", encoding="utf-8")
        n = build_fast(rd)
        sheet = (rd / "verify_sheet.md").read_text(encoding="utf-8")
        self.assertEqual(n, 4)
        self.assertNotIn("charged at 20% on taxable income up to £37,700", sheet)  # the data's own clause and year
        self.assertIn("Personal Allowance is £12,570", sheet)  # two clauses of the data: the pairing is checked
        self.assertIn("45% on taxable income above £37,700", sheet)  # 40% is the rate there: still checked
        self.assertIn("in 2025-26 was 20%", sheet)  # a year the data doesn't hold
        self.assertIn("1 more line(s)", sheet)
        self.assertIn("= £3,486", sheet)  # a worked sum is always checked
        self.assertIn("own rates data", sheet)


class BriefTests(unittest.TestCase):
    def test_rates_are_never_quote_slots(self):
        from seolib.plan import quote_candidates
        f = facts_for(brief("vat calculator"), data=DATA)
        self.assertTrue(f)
        self.assertEqual(quote_candidates(f), [])


if __name__ == "__main__":
    unittest.main()
