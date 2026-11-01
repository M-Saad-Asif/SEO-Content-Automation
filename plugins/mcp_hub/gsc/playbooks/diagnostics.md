# Traffic drops, core updates, migrations, manual actions, security (PF11, PF12, OP4, SM1, SM2)

## PF11. Traffic-drop diagnosis (Google's sequence)

1. **Data anomalies first.** Check Google's Data anomalies page and `reference/caveats.md`. Known distortions:
   - the `num=100` change, September 2025;
   - the impression-logging bug, 13 May 2025 to 27 Apr 2026 (it affects impressions, not clicks);
   - Discover logging errors.
2. **Clicks vs impressions.**
   - A clicks-only drop points to titles or AI Overviews.
   - Both falling points to rankings or demand.
3. **Look at 16 months** (`data trend`) to see the drop's shape:
   - sharp → an algorithm update, security or spam;
   - yearly → seasonal;
   - gradual → page-level or demand.
4. **Compare the last 3 months** with the previous 3 and with the same period last year, on every tab (`data decay`, `data coverage`, `data device`, `data country`).
5. **Check each search type:** Web, Image, Video, Discover, News. A Discover-only drop needs a different fix.
6. **Sort pages by the clicks difference.**
   - A site-wide drop → the Page indexing report (ask the user) and URL Inspection on a sample.
   - A section → the URL group.
7. **Ask the user for the UI-only reports:** Crawl Stats (host status, response codes), Security issues and Manual actions (`../ui_checklists.md`).
8. **Rebuild or retarget the losing pages** (Quaid): `/page-seo <site> | gsc queue decay`.
9. **Wait "a few weeks"** after changes before judging (Google).

## PF12. Update delta report (Glenn Gabe)

1. **Windows.** 14–28 days before the update vs from completion + 7 days, with the same weekday mix [synth]. Google says wait at least a week after completion.
2. **Segment** by folder regex, query class (`data intent`), device, country and appearance. Sort by the click change.
3. **Find the onset** with `hourly` data over 10 days.
4. **Decide:**
   - a section losing ≥20% of clicks with a worse position → a quality self-assessment of that section [synth];
   - small slips → no action (Google).

## OP4. Migrations

**Before the move:**
- Benchmark everything in the store: `gsc pull` and keep a monthly archive.
- Build a 1:1 301 map.
- Verify both properties.
- Prepare new sitemaps.

**At the move:**
- Change of address for **both www and non-www** (Mueller). It needs the user's approval.

**Weekly for 6 months [synth]:**
- old property down and new up;
- "Page with redirect" growing on the old property;
- URL Inspection canonicals on the top URLs.

**Warning:** migrations can unravel months later. In an r/SEO case from October 2026, the new domain's pages fell to "Crawled – currently not indexed" four months after the move.

## SM1. Manual actions (UI-only, plus email)

- **18 categories,** including:
  - site reputation abuse;
  - scaled content abuse (under major spam);
  - back-button hijacking (added April 2026).
- **Fix every issue on every page,** and document the fixes.
- **Reconsideration** takes several days to a few weeks. It needs the user's approval.
- **No manual action shown** means the drop is algorithmic, so a reconsideration request does nothing.

## SM2. Security issues

Hacked content, malware or social engineering: clean up, then request a review (approval). Safe Browsing / Web Risk can confirm externally.

Sources: Google's traffic-drop debugging guide (updated 10 Dec 2025); Daniel Waisberg; Glenn Gabe's delta reports; Search Engine Roundtable on migrations; Google's Manual actions help. Links are in the research report §4.4 and §4.6.
