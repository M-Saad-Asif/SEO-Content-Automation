"""The gaming niche (owner's rules of 17 Oct 2026, first client gta6coverage.com): leaks, rumors, insider reports and
what players say are all used, each labelled, and the article opens with its status; Discover-style titles that
don't oversell; press may be credited and linked, GTA fan and coverage sites are never named or linked; the views
are the editorial desk's ("we"); the site's own records are verified facts; finished pages are written into the
site as its own Markdown."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seolib import common as C  # noqa: E402
from seolib import gaming  # noqa: E402
from seolib.lint import lint_text  # noqa: E402

B = {"target_query": "gta 6 trailer 3 leak", "client": "GTA 6 Coverage", "domain": "gta6coverage.com",
     "locale": "en-US", "page_type": "news", "page_url": "https://gta6coverage.com/news/gta-6-trailer-3-leak",
     "niche": "gaming", "voice": "we", "scope": "global", "word_range": [10, 9000]}
LEAK = {"id": "serp:1", "claim": "x", "value": "Leaked footage shows Lucia driving a convertible through Vice City at night.",
        "status": "serp", "label": "leak", "source_kind": "rival", "source_url": "https://gtabase.com/news/leak"}


def rules(md, sheet_extra=None, research=None):
    sheet = {"brief": dict(B), "facts": [LEAK], "client": {}, "products": [], **(sheet_extra or {})}
    return [f for f in lint_text(md, sheet, {}, research or {})["findings"] if f["severity"] == "block"]


PAGE = """---
title: "GTA 6 Trailer 3 Leak: What the Footage Appears to Show"
meta_description: "A leaked clip appears to show Lucia in Vice City. Here is what is confirmed, what is not, and what Rockstar has said about the next trailer."
quick_answer: "A clip shared online appears to show new GTA 6 footage. Rockstar has not confirmed it. The game is listed for November 19, 2026."
tags: [trailer, leaks]
---

# GTA 6 Trailer 3 Leak: What the Footage Appears to Show

**Leak:** a clip shared online appears to show new footage of Lucia. Rockstar has not confirmed it.

## What does the leaked clip show?

According to a leak shared online, the footage shows Lucia driving a convertible through Vice City at night.
"""


class SourceAndLabelTests(unittest.TestCase):
    def test_who_can_be_named(self):
        for d, k in (("rockstargames.com", "official"), ("www.ign.com", "press"), ("bloomberg.com", "press"),
                     ("reddit.com", "public"), ("gtabase.com", "rival"), ("gtaforums.com", "rival"),
                     ("rockstarintel.com", "rival"), ("someblog.net", "rival"), ("gta6coverage.com", "client")):
            self.assertEqual(gaming.kind(d, B), k, d)
        self.assertEqual(gaming.kind("ign.com", {**B, "competitor_sites": ["ign.com"]}), "rival")

    def test_every_claim_gets_its_label(self):
        for s, want in (("A leaked build shows a new map.", "leak"),
                        ("According to people familiar with the matter, the game slips again.", "insider"),
                        ("The game reportedly costs $80.", "rumor"),
                        ("Fans on Reddit think the map is bigger than Los Santos.", "community"),
                        ("Rockstar confirmed the November 19 date on its site.", "official"),
                        ("The studio is hiring more QA testers in Lincoln.", "report")):
            self.assertEqual(gaming.label(s, "press"), want, s)
        self.assertEqual(gaming.label("The studio is hiring more QA testers.", "rival"), "rumor")

    def test_section_and_page_type_follow_the_query(self):
        for q, cat, pt in (("gta 6 cheats", "cheats", "guide"), ("gta 6 pc requirements", "tech", "guide"),
                           ("gta 6 trailer 3 release date", "news", "news"), ("gta 6 map guide", "guides", "guide"),
                           ("gta 6 price leak", "news", "news")):
            self.assertEqual((gaming.category(q), gaming.page_type(q)), (cat, pt), q)
        self.assertEqual(gaming.page_type("gta 6 money tracker", "tool"), "guide")  # no tools on a gaming site

    def test_the_status_line_comes_from_the_query_then_the_facts(self):
        self.assertEqual(gaming.status_of([], "gta 6 trailer 3 leak"), "Leak")
        self.assertEqual(gaming.status_of([{"label": "official"}, {"label": "rumor"}], "gta 6 release date"), "Official")
        self.assertEqual(gaming.status_of([{"label": "rumor"}, {"label": "rumor"}, {"label": "report"}], "gta 6 price"), "Rumor")

    def test_the_writer_sees_each_facts_label_and_who_may_be_credited(self):
        self.assertEqual(gaming.tag(LEAK, B), "[Leak · unnamed site: never name it] ")
        self.assertIn("IGN", gaming.tag({"label": "report", "source_url": "https://www.ign.com/articles/x"}, B))
        text = "\n".join(gaming.brief_lines(B, [LEAK], today="October 17, 2026"))
        for want in ("**Leak:**", "Google Discover", "quick_answer", "never the site's name", "as of October 17, 2026"):
            self.assertIn(want, text)


class LintTests(unittest.TestCase):
    def test_a_labelled_page_passes_the_gaming_checks(self):
        got = {f["rule"] for f in rules(PAGE)}
        self.assertFalse({r for r in got if r.startswith(("G1", "C05", "V04", "K10", "H01-title"))}, got)

    def test_a_page_without_its_status_or_labels_is_sent_back(self):
        md = PAGE.replace("**Leak:** a clip", "A clip").replace(
            "According to a leak shared online, the footage shows", "The footage shows")
        got = {f["rule"] for f in rules(md)}
        self.assertIn("G10-status-label", got)
        self.assertIn("G11-unlabelled-claim", got)

    def test_titles_that_oversell_or_drop_the_label(self):
        md = PAGE.replace('title: "GTA 6 Trailer 3 Leak: What the Footage Appears to Show"',
                          'title: "GTA 6 Trailer 3 Is HERE and It Changes EVERYTHING!"')
        got = {f["rule"] for f in rules(md)}
        self.assertIn("G12-title-bait", got)
        self.assertIn("G13-title-label", got)

    def test_quick_answer_is_required(self):
        md = PAGE.replace('quick_answer: "A clip shared online appears to show new GTA 6 footage. Rockstar has not '
                          'confirmed it. The game is listed for November 19, 2026."\n', "")
        self.assertIn("G14-quick-answer", {f["rule"] for f in rules(md)})

    def test_fan_sites_are_never_named_or_linked_but_the_press_is(self):
        md = PAGE + ("\nGTABase first posted the clip, and [IGN reports](https://www.ign.com/articles/gta-6-leak) that "
                     "Rockstar has not commented. See [the post](https://gtabase.com/news/leak).\n")
        research = {"serp_intel": {"organic": [{"domain": "gtabase.com", "link": "https://gtabase.com/news/leak"},
                                               {"domain": "ign.com", "link": "https://www.ign.com/articles/gta-6-leak"}]}}
        hits = [f for f in rules(md, research=research) if f["rule"] == "C05-fan-site"]
        self.assertTrue(any("gtabase.com/news/leak" in f["text"] for f in hits))
        self.assertTrue(any("GTABase first posted" in f["text"] for f in hits))
        self.assertFalse(any("ign.com" in f["text"] and "gtabase" not in f["text"].lower() for f in hits))

    def test_the_desk_speaks_as_we_and_a_game_may_unlock_things(self):
        md = PAGE + ("\n## How do you unlock the convertible?\n\nYou unlock it after the second mission, according to a "
                     "leak. I think the footage is real.\n")
        got = {f["rule"] for f in rules(md)}
        self.assertIn("V04-desk-voice", got)
        self.assertNotIn("X01-banned-phrase", got)
        self.assertNotIn("H12-vague-heading", got)


class RecordAndExportTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        (self.repo / "content" / "database").mkdir(parents=True)
        (self.repo / "content" / "news").mkdir()
        (self.repo / "content" / "database" / "vehicles.json").write_text(json.dumps([
            {"id": "grotti-cheetah-1995", "type": "vehicles", "name": "'95 Grotti Cheetah", "manufacturer": "Grotti",
             "class": "Sports car", "topSpeedMph": None, "price": None, "verification": "official-name",
             "description": "Rockstar names this car in its media gallery.", "lastUpdated": "2026-09-26",
             "sourceUrl": "https://www.rockstargames.com/VI/media/screenshots"}]), encoding="utf-8")
        self.b = {**B, "site_repo": str(self.repo), "site_data_files": ["content/database/vehicles.json"],
                  "site_export": {"author": {"id": "editorial-desk", "name": "GTA 6 Coverage Editorial Desk",
                                             "role": "Editorial desk"}}}

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_records_are_verified_facts_with_their_blank_stats_not_announced(self):
        self.assertEqual(gaming.record_facts(self.b, "gta 6 map regions"), [])
        f = gaming.record_facts(self.b, "gta 6 cars list")[0]
        self.assertEqual((f["status"], f["basis"], f["label"]), ("verified", "site_rates", "official"))
        self.assertIn("named by Rockstar", f["value"])
        self.assertIn("Not announced: top speed mph, price", f["value"])
        self.assertEqual(f["record_page"], "https://gta6coverage.com/database/vehicles/grotti-cheetah-1995")

    def test_the_finished_page_is_written_into_the_site_as_its_own_markdown(self):
        rd = Path(tempfile.mkdtemp())
        (rd / "final.md").write_text(PAGE + (
            "\nThe [map guide](https://gta6coverage.com/map) lists the regions. The [Grotti Cheetah]"
            "(https://gta6coverage.com/database/vehicles/grotti-cheetah-1995) is named. "
            "[Rockstar lists the date](https://www.rockstargames.com/VI) and [IGN reports](https://www.ign.com/articles/x) "
            "more.\n"), encoding="utf-8")
        dest = gaming.export(rd, {**self.b, "slug": "gta-6-trailer-3-leak"}, today="2026-10-17")
        self.assertEqual(dest, self.repo / "content" / "news" / "gta-6-trailer-3-leak.md")
        text = dest.read_text(encoding="utf-8")
        meta, body = gaming._front(text)
        self.assertEqual(meta["title"], "GTA 6 Trailer 3 Leak: What the Footage Appears to Show")
        self.assertEqual(meta["publishedAt"], "2026-10-17")
        self.assertIn("quickAnswer", meta)
        self.assertEqual(meta["author"]["id"], "editorial-desk")
        self.assertEqual([s["url"] for s in meta["sources"]], ["https://www.rockstargames.com/VI", "https://www.ign.com/articles/x"])
        self.assertNotIn("# GTA 6 Trailer", body)  # the title is the H1 on the site
        self.assertIn("[map guide](/map)", body)
        self.assertIn("The Grotti Cheetah is named", body)  # the site links database items itself
        # a second export keeps the first date and adds the update date
        dest = gaming.export(rd, {**self.b, "slug": "gta-6-trailer-3-leak"}, today="2026-10-20")
        meta, _ = gaming._front(dest.read_text(encoding="utf-8"))
        self.assertEqual((meta["publishedAt"], meta["updated"]), ("2026-10-17", "2026-10-20"))


class ResearchTests(unittest.TestCase):
    def test_the_researchers_hunt_leaks_and_reactions_and_fan_sites_are_dropped(self):
        from seolib.gain import task_lines, register
        text = "\n".join(task_lines(B, "runs/x"))
        for want in ("A (players)", "kind: official | leak | rumor | insider | report | reaction", "Never quote or name GTA fan"):
            self.assertIn(want, text)
        rd = Path(tempfile.mkdtemp())
        (rd / "research").mkdir()
        C.save_json(rd / "fact_sheet.json", {"brief": B, "facts": []})
        item = lambda src, kind: {"kind": kind, "point": "Players think the new trailer shows a bigger Vice City map.",
                                  "quote": "the map looks way bigger than anything Rockstar has made before",
                                  "source": src, "who": "players", "date": "", "quote_found": True}
        C.save_json(rd / "research" / "gain.json", {"items": [item("https://www.reddit.com/r/GTA6/comments/x", "reaction"),
                                                              item("https://gtaforums.com/topic/1", "rumor")]})
        got = register(rd)
        self.assertEqual([f["source_url"] for f in got], ["https://www.reddit.com/r/GTA6/comments/x"])
        self.assertEqual(got[0]["label"], "community")

    def test_a_gaming_brief_gets_its_sites_section_in_its_address(self):
        from seolib.briefgen import default_page_url
        self.assertEqual(default_page_url({"domain": "gta6coverage.com", "niche": "gaming", "target_query": "gta 6 cheats"},
                                          "guide", "gta-6-cheats"), "https://gta6coverage.com/cheats/gta-6-cheats")


if __name__ == "__main__":
    unittest.main()
