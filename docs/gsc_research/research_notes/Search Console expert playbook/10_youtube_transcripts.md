# Search Console methods taught in YouTube videos (transcript-based where possible)

> **How this was gathered (read first).** We found video IDs by scripting YouTube's public search results page with Python's standard library. For each video we pulled the title, channel, date, chapters and description from its public watch page. **We could not get YouTube caption text.** Every caption track URL carried `exp=xpe`, which means YouTube wants a proof-of-origin token, and the URL returned an empty body. `youtubei/v1/get_transcript` returned HTTP 400 "Precondition check failed". The two public transcript sites we tried (youtubetotranscript.com and youtube-transcript.io) returned 403. Our next step would have queried YouTube's player API while posing as other apps. The permission system blocked it as bot-check circumvention, and we did not try to get around that.
> **Full official transcripts with timestamps WERE obtained** for four Google *Search Off the Record* (SOTR) episodes, which Google also publishes as YouTube videos. The transcripts are PDFs on libsyn, linked from goo.gle/sotrNNN-transcript. We parsed them with a stdlib PDF extractor. For SOTR 080 and 112 the transcript timestamps match the YouTube chapters to within about a minute. For SOTR 061 the YouTube cut runs roughly 1–1.5 minutes off the transcript times, so treat those timestamps as approximate.
> **For all creator videos** (Edward Sturm, David Quaid, Chris Long, Julian Goldie, Rank Math, Surfer, Caleb Ulku, Patrick Rice, Ahrefs and others), the tactics below come **only from the creator's own chapter list and description**, which is what the brief allowed as a fallback. Chapter timestamps are exact; any detail inside a chapter is unverified. Raw files (metadata, chapters, descriptions, SOTR transcripts) are in the scratchpad: `C:/Users/saadp/AppData/Local/Temp/claude/C--Users-saadp-OneDrive-Desktop-SEO-automation/7f4d23d1-d757-41c3-b2c3-43a2cdde0c43/scratchpad/yt/` (`meta/`, `sotr/`).

## Q1. Per-video GSC workflows (title, channel, URL, date, tactics with timestamps)

### Takeaway
The only verbatim, timestamped source material came from Google's own SOTR episodes. In them, Mueller, Splitt and Illyes say to read the Page Indexing report for **patterns and trend lines**, not as a fix-list. They add that there is **no meaningful indexed/non-indexed ratio**, that "Mark as fixed" triggers a sample check and a faster recrawl, and that URL Inspection plus the Pages report beat `site:`. Creator videos, known only from their chapters and descriptions, centre on regex segmentation (branded vs non-branded, questions), striking-distance positions (Quaid uses 8–17), cannibalization found through query→page drill-downs, and indexing fixes. Two newer threads run through the 2026 creator videos: the GSC AI/natural-language filter, the Generative AI report and the social "platform properties", and connecting GSC to LLMs via MCP or Sheets.

### Cited Findings

#### A. Google Search Central — "How to read the Indexing Report" (SOTR ep. 112), Martin Splitt & John Mueller, 2026-07-16 — https://www.youtube.com/watch?v=1-PcVLHplwc (official transcript: https://goo.gle/sotr112-transcript)
- **Tactic A1: read the Page Indexing report as a pattern detector, not an inventory or fix-list.** Splitt relays advice from Hillel on the Search Console team: look for patterns and unexpected changes, then dig deeper, rather than monitoring whether each URL is in or out (≈03:40). He frames the real question as whether the site in the index is doing what you expect (≈04:11). Link: https://www.youtube.com/watch?v=1-PcVLHplwc&t=105 — [SOTR 112 transcript](https://goo.gle/sotr112-transcript)
  - *When:* after any planned change (migration, redirects, removing a category) or when the trend line moves unexpectedly.
  - *Decision rule:* a planned change should show up as a matching rise, e.g. "Page with redirect" after a migration or 404s after deleting a section. If it does **not** show up, either Google hasn't processed it yet or something went wrong (≈04:11–06:25). [Transcript](https://goo.gle/sotr112-transcript); https://www.youtube.com/watch?v=1-PcVLHplwc&t=276
  - *Data delay:* the data isn't real-time. A new section can look "not indexed" because of a processing delay, and longer delays are announced in Search Console (≈05:35). [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A2: expected 404s are correct, not errors to drive to zero.** Mueller: pages you removed or that never existed should return an error, and pushing the error count down just to please management is the wrong goal (≈06:25–07:54). https://www.youtube.com/watch?v=1-PcVLHplwc&t=385 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A3: "Page with a different canonical" shifts. Sample a few examples and use a Domain property.** Click the reason to get example URLs, analyze one or two, and decide whether the shift was expected. Google picking another of your URLs as canonical is normal. Whether to adopt Google's choice is your call. A Domain property removes the www/non-www confusion (≈07:54–10:41). https://www.youtube.com/watch?v=1-PcVLHplwc&t=480 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A4: don't use `site:` as the source of truth.** Mueller calls `site:` an artificial query. Old domains can still appear in it 1–3 years after a correctly redirected move, and hreflang swapping makes it unreliable. Search Console is the source of truth (≈11:05–13:31). https://www.youtube.com/watch?v=1-PcVLHplwc&t=672 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A5: detect CDN or host bot protection through sudden systemic jumps.** *Signal:* a sudden rise in 404/403/410, URLs dropped, or many URLs canonicalized elsewhere. A worse case is a "are you a bot?" interstitial served with a **200**. Google may then index the interstitial, or pick another site's identical error page as the canonical. *Action:* find which provider (CDN or host) is responsible, get it fixed, **then** click "Mark as fixed". Mueller says overloaded servers should return 503, not 404/403 (≈13:38–17:49). https://www.youtube.com/watch?v=1-PcVLHplwc&t=818 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A6: how "Mark as fixed" works.** Google tests a **sample** of the URLs. If they pass, it usually triggers a **faster recrawl** of the rest. Use it after a real systemic fix, not for "crawled/discovered not indexed" (≈17:00–17:49). https://www.youtube.com/watch?v=1-PcVLHplwc&t=1069 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A7: tell template problems from infrastructure problems.** If errors cluster on one template, the cause is probably in your own code. If they span the whole site or the whole CDN-fronted section, suspect the CDN (≈17:49). [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A8: trend-line thresholds for 5xx and DNS blips.** A small blip means checking server logs and is usually fine. A **steep line up** means investigate. A flat, stable error level that hasn't hurt before is not new. Errors lasting **about a day** are treated as temporary. **Longer than a day**, Google's systems react (≈17:49–20:32; 28:31). https://www.youtube.com/watch?v=1-PcVLHplwc&t=1069 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A9: Discovered vs Crawled – currently not indexed.** "Discovered" means Google knows the URL but hasn't visited it. "Crawled" means it visited and chose not to index. Mueller says this is *sometimes* a quality signal. When Google is seriously concerned about site quality, it crawls and indexes less. *Action:* if a large pattern has no technical cause, step back and assess **overall site quality**, including the page experience (ads, interstitials, filler above the content), not only the text. Don't try to "fix" these technically. Mueller says sites that are mostly AI-generated may offer nothing unique (≈20:32–25:31). https://www.youtube.com/watch?v=1-PcVLHplwc&t=1232 — [Transcript](https://goo.gle/sotr112-transcript)
- **Tactic A10: no index-ratio target.** Splitt has seen healthy sites with about 1M non-indexed and about 500k indexed pages. Mueller says only about **5%** of the Google developer-docs site's pages are indexed, mostly because of noindex, 404s and canonicals, and its important content is still indexed and visible in the Performance report. *Rule:* make sure everything you care about is indexed under *some* URL (≈25:31–28:31). https://www.youtube.com/watch?v=1-PcVLHplwc&t=1531 — [Transcript](https://goo.gle/sotr112-transcript)

#### B. Google Search Central — "Why is my site not indexed?" (SOTR ep. 61), Martin Splitt, John Mueller, Gary Illyes, 2023-06-22 — https://www.youtube.com/watch?v=T2RwEr4bkBw (official transcript PDF via http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed). The YouTube cut runs about 1–1.5 minutes off the transcript times.
- **B1: first, rule out "it's a ranking problem, not an indexing problem".** Mueller (≈01:49). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=88 — [Transcript page](http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed)
- **B2: use the Page indexing report for the overview and URL Inspection for individual cases.** Mueller usually sends people to inspect individual pages, because the site-level view can mislead. Illyes uses URL Inspection almost exclusively (≈04:04–05:42). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=217
- **B3: if a new site's homepage isn't crawled or indexed, it's almost always technical.** Illyes: homepages are crawled and indexed first. If the homepage hasn't even been crawled (check GSC or server logs), suspect a technical block. Google can't judge quality before it has crawled anything (≈06:33–08:49). Non-quality causes listed: server unreachable from Googlebot, robots.txt, the site not linked anywhere (undiscoverable), a whole-site URL **Removal** request, a past webspam action, checking the www version while the non-www one is indexed, hreflang variants (DE/AT/CH) canonicalized into one with GSC reporting on the canonical, a CMS "discourage search engines" noindex, and parked or "under construction" pages caught by soft-error detection (≈09:01–14:42). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=345
- **B4: indexing speed is anywhere from seconds to never.** It depends on links and demand. Illyes: the web is too big to index everything, so lower your expectations or raise quality (≈15:17–19:17). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=904
- **B5: deleting old content doesn't free "index quota".** Illyes says there is no per-site indexing quota. Ongoing natural links make Google more inclined to keep your content (≈19:49–20:54). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=1047
- **B6: Request Indexing is not a lever for normal sites.** Illyes would use it only for urgent, unique content such as an exclusive breaking story. It is useful for *testing* whether a page can be indexed, e.g. to catch an accidental "content not available" message (≈20:54–23:40). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=1167
- **B7: `site:` shows only *some* indexed pages, while GSC gives the count.** Illyes uses `site:` only to spot spammy keywords that shouldn't be on the site (or uses Google Alerts), to find localized doc versions, and to check indexed images on UGC sites (≈23:59–26:05). https://www.youtube.com/watch?v=T2RwEr4bkBw&t=1347

#### C. Google Search Central — "Working with the Search Console API" (SOTR ep. 80), guest Mihai Aperghis with Mueller and Splitt, 2024-08-22 — https://www.youtube.com/watch?v=ZFEYYmJjJ94 (transcript: https://goo.gle/sotr080-transcript)
- **C1: forum triage order for traffic or ranking complaints:** (1) eliminate technical blockers, (2) line up the change dates with recent algorithm updates, (3) only then look at subjective content quality (Aperghis ≈07:04). https://www.youtube.com/watch?v=ZFEYYmJjJ94&t=346 — [Transcript](https://goo.gle/sotr080-transcript)
- **C2: many GSC "issues" are just notifications.** Canonicalized pages, WordPress noindex pages and 404s after removing products are expected. "Crawled/Discovered not indexed" is the one area worth case-by-case review, and some pages will never be indexed (≈11:10–14:32). https://www.youtube.com/watch?v=ZFEYYmJjJ94&t=614
- **C3: use the API, not the UI, for scale and history.** In the API you can pull query and page together in one request, which the UI only shows by clicking one query at a time. Aperghis reports hundreds of thousands of rows, including "a million pages" for big sites. He schedules a **monthly automated export to Google Sheets** to keep data beyond the 16-month window, and runs thousands of URL Inspection API calls in minutes. He wishes indexing reports were in the API, since the UI caps each indexing report at about 1,000 example rows (≈14:45–28:29). https://www.youtube.com/watch?v=ZFEYYmJjJ94&t=873 — [Transcript](https://goo.gle/sotr080-transcript)
- **C4: LLM access to GSC data.** Aperghis built "Search Analytics for GPT" for natural-language questions but expects big sites to stay in Sheets. Mueller notes the monthly Search Console Insights emails as a light alternative (≈19:00–24:38). https://www.youtube.com/watch?v=ZFEYYmJjJ94&t=1141

#### D. Google Search Central — Daniel Waisberg "Search Console Training" videos (chapters only; content supplemented by the matching official docs)
- **"Analyzing drops in Google Search traffic", 2023-03-29**, https://www.youtube.com/watch?v=IIvIRgpCOqc. Chapters: main reasons for drops (https://www.youtube.com/watch?v=IIvIRgpCOqc&t=70), analyze the drop pattern (…&t=195), check industry trends with Google Trends (…&t=268). The matching Google doc gives the workflow:
  1. Check the Data Anomalies page.
  2. See whether both impressions and clicks fell; if only clicks fell, look at titles, snippets and rich results.
  3. Set the range to the last 16 months to spot seasonality.
  4. Compare the last 3 months with the previous period or the same period last year, across every tab.
  5. Segment by search type.
  6. Treat average position as a supporting signal only.
  7. Sort the Pages table by Clicks Difference. For a site-wide loss, check Page indexing; for a group of pages, run URL Inspection on samples.
  8. Check Crawl Stats, Security Issues and Manual Actions.
  9. Use Google Trends to see whether demand itself fell.

  The doc also maps drop *shapes* to causes: a sharp drop suggests an update, security issue or spam action; a yearly curve suggests seasonality; a gradual decline suggests a page-level technical issue or shifting interest. — [Google: Debugging drops in Search traffic](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
- **"Crawl Budget and the Crawl Stats report", 2021-03-03**, https://www.youtube.com/watch?v=x_GoMrl6_u0. Chapters: crawl demand (…&t=91), Crawl Stats report (…&t=183). Help-doc rules: the report is for advanced users, and sites under ~1,000 pages usually don't need it. Host status is green if there were no issues in 90 days, an amber-type warning if the issue was more than a week ago, and red if it was within the last week. The DNS-failure threshold example is **>5% of requests in a day**. A robots.txt fetch failure pauses crawling for 12 hours; from 12 hours to 30 days Google uses the last good copy. Don't keep 503/429 or robots.txt crawl-blocking for more than 2–3 days. Breakdowns are by response, file type, purpose (Discovery vs Refresh) and Googlebot type. — [Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- **"Analyzing performance on Google Search", 2025-12-04**, https://www.youtube.com/watch?v=5LF6SwB5jZ0. Chapters: data controls and filters (…&t=122), refining analysis (…&t=166), **branded query analysis** (…&t=289), chart visualizations (…&t=342), **custom chart annotations** (…&t=406), performance tables (…&t=470). — [YouTube chapters](https://www.youtube.com/watch?v=5LF6SwB5jZ0)
- **"Demystifying Google Analytics and Search Console data", Cherry Prommawin & Waisberg, 2025-01-29**, https://www.youtube.com/watch?v=ViwW9D-brTQ. Chapters: GSC clicks vs GA sessions (…&t=297) and why the numbers differ (…&t=391). — [YouTube chapters](https://www.youtube.com/watch?v=ViwW9D-brTQ)
- Also available: "Getting started with Search Console Insights" (https://www.youtube.com/watch?v=BKtQ5tVAwSo), "Intro to Search Console bulk data export" (https://www.youtube.com/watch?v=YBpYB9c-uGQ) and "Intro to Search Console APIs" (https://www.youtube.com/watch?v=KkvI0X-w6dE). We did not analyze them.

#### E. Edward Sturm (The Edward Show) — chapters and descriptions only; no transcript available
- **"You're Reading Google Search Console WRONG (Here's Why)", guest David Quaid, 2026-08-04 (E1126, 1:16:26)**, https://www.youtube.com/watch?v=YRN9xDKoQhk. Per the description and chapters:
  - **E1 Macro stats mislead. Work at page × query level.** Site-wide clicks, impressions, CTR and average position rarely explain why a page wins or fails (…&t=154; keywords and SERP reports …&t=235).
  - **E2 "Click zone" and titles.** The description says page titles beyond page 1 rarely improve CTR (…&t=390).
  - **E3 Build a query filter or regex** (…&t=472, …&t=654).
  - **E4 Hidden queries.** Google withholds part of the query data (…&t=1030).
  - **E5 Google as a "CTR engine".** It tests pages before rankings stabilize, so expect fluid rankings during testing (…&t=1169, …&t=1322).
  - **E6 GSC data lags** (…&t=1524).
  - **E7 Find cannibalization in GSC, and decide whether it matters.** Fix it only when it matters, and use a SERP tracker to diagnose (…&t=1650, …&t=1896, …&t=2137, …&t=2150).
  - **E8 When traffic drops, look at page-level deltas, then rebuild or retarget the page** (…&t=2363, …&t=2515). The description lists the options as republish, retarget or rewrite.
  - **E9 Newbie starting points** (…&t=2584).
  - **E10 Build a "keyword universe".** Leaders should know their most valuable keywords (…&t=2989).
  - **E11 Treat SERP fluctuations and alerts calmly; tag historical trends** (…&t=3158, …&t=3917).
  - **E12 Use GSC to spot intent mismatches and pages ranking for untargeted keywords** (description).
  - Source: [video page](https://www.youtube.com/watch?v=YRN9xDKoQhk)
- **"Stop Guessing SEO: How to Let Google Tell You What to Rank For", guest David Quaid, 2026-01-03 (E913, 37:49)**, https://www.youtube.com/watch?v=88alcdGtwAE.
  - **Regex branded vs non-branded split** (…&t=49, …&t=94).
  - **Privacy-withheld data.** Work with wider query sets to get more accurate insights (…&t=390).
  - **Expand topical authority with regex.** Find **question queries** Google already associates with the site, and find **page-two keywords as a signal of "topical readiness"** (…&t=668).
  - **Turn PAA-style queries into FAQ and content structures.** Hub pages, internal links and subfolders pass topical authority (…&t=1221, …&t=1259).
  - **Low-risk test: publish many small pages to test ranking potential, then improve the pages Google shows it will rank** (description; …&t=1901).
  - **Content decay** (…&t=1568).
  - Source: [video page](https://www.youtube.com/watch?v=88alcdGtwAE)
- **"Why Google Crawls Your Page but Refuses to Index It (And How to Fix It)", 2026-02-10 (E951, 9:38, 22.6k views)**, https://www.youtube.com/watch?v=ahNhcLDa1LQ. Sturm's thesis is that Google asks whether the page **adds distinct value** compared with what it already has. He calls the page title a strong, overlooked signal: generic or near-duplicate titles can prevent indexing. *Action:* use a title formula of **target keyword + clear benefit or searcher goal + brand name**, cleanly separated (…&t=128, examples …&t=182). He uses ChatGPT to draft titles (…&t=455). He rules out 404s, noindex, blocked resources and server errors as causes of this status (description). Source: [video page](https://www.youtube.com/watch?v=ahNhcLDa1LQ). The companion Reddit post (r/SEO 1qzt59k) could not be fetched.
- **"Google Just Dropped an AI Update for Search Console (And It's Huge)", 2026-03-08 (E977)**, https://www.youtube.com/watch?v=xFjRMvI-a7g. Covers the natural-language/AI configuration in the Performance report (…&t=36). *Workflow:* prompt it for **transactional or buyer-intent queries** (…&t=97). Find **low-hanging fruit**, meaning high-intent queries where the site ranks but is not yet in the top positions, using a **position filter** (…&t=142). Limits are covered at …&t=187. Source: [video page](https://www.youtube.com/watch?v=xFjRMvI-a7g)
- **"Google Just Added Instagram, TikTok, X & YouTube to Search Console", 2026-07-12 (E1103)**, https://www.youtube.com/watch?v=EqyK0ToKepo. Covers the new **platform properties**, which show the queries leading to your social posts and videos in Search and Discover. Enable them at …&t=379. *Tactics:* put the target keyword in a LinkedIn post's **first words**, because LinkedIn uses them for the page title and URL (…&t=80). Write detailed video descriptions plus transcripts rather than hashtags (…&t=298). Sturm got a LinkedIn post indexed with an indexer in about **30 minutes**, but says being indexed is not the same as ranking on page 1, and running indexers across all posts carries risks (…&t=459). Source: [video page](https://www.youtube.com/watch?v=EqyK0ToKepo)
- **"Position #1 On Google Is Dead (8.1 Million Searches Prove It)", guest Joy Hawkins (Sterling Sky), 2026-09-12 (E1165)**, https://www.youtube.com/watch?v=jIh1xEDAqZQ. Per the description, a study of 8.1M results found rankings **48.7% more volatile** after the May 2026 core update, with 97% of tracking reports shuffling. *GSC-relevant rules:*
  - Measure leads and calls, not ranking spots (…&t=518).
  - Hawkins trusts **Search Console and call tracking** more than a single rank-tracker snapshot, and wants multiple checks before trusting rank data (…&t=621).
  - Google's "go-to" redirects could make rank trackers contaminate GSC click data (…&t=977).
  - Pruning experiments: deleting **1,000 not-visited pages**, and pruning more than half the content on sites hit by domain-wide losses (…&t=3073).

  Source: [video page](https://www.youtube.com/watch?v=jIh1xEDAqZQ)
- **"Inside the Search Engine Black Box…", guest David Quaid, 2025-12-14 (E893)**, https://www.youtube.com/watch?v=0oxz_mSy3pQ. Per the description, Quaid explains why pages aren't indexed on Google or Bing, discusses CTR vs dwell time and freshness myths, and says indexing APIs and manual indexing are "a red flag" (…&t=1977 "How to Index a Link Instantly"; …&t=3570 new page vs update). Source: [video page](https://www.youtube.com/watch?v=0oxz_mSy3pQ)

#### F. David Quaid (own channel) — "Understanding SEO Performance with GSC", 2026-09-25 (56:55) — https://www.youtube.com/watch?v=unlR3iHAmGE (chapters and description only)
- **F1 GSC vs GA4.** GSC explains why you got the traffic; GA4 shows what visitors did afterwards (…&t=70).
- **F2 Striking-distance keywords.** Find queries in **positions 8–17** and push them higher (…&t=170).
- **F3 High-impression, low-CTR keywords** (…&t=400).
- **F4 Period-on-period comparison**, not just week over week, to spot declining pages, tied to authority (…&t=744).
- **F5 Backlinks, Bing Webmaster Tools and internal links** (…&t=1170).
- **F6 Indexing issues are "almost always" authority problems, not technical ones** (…&t=1966).
- **F7 Brand vs non-brand traffic split** (…&t=2664).
- **F8 Live GSC walkthrough** (…&t=2780).
- Source: [video page](https://www.youtube.com/watch?v=unlR3iHAmGE). The description misspells the host's name in places; the channel is David G Quaid.

#### G. Other high-signal GSC tutorials (chapters and descriptions only)
- **Surfer Academy, "Google Search Console Tutorial (2026): The Complete Guide", 2026-08-12 (23.9k views)**, https://www.youtube.com/watch?v=93uhFZ_9IzY. Built around 12 scenarios:
  - Domain vs URL-prefix setup (…&t=106).
  - Page not showing, i.e. diagnosing Discovered vs Crawled not indexed (…&t=334).
  - Tracking a single page's or keyword's rank history without a paid tracker (…&t=531).
  - **Proving non-branded growth with regex** (…&t=639).
  - Traffic-drop diagnosis (…&t=812).
  - **Finding the best keyword for an existing page from its own click data** (…&t=898).
  - **Mining question queries for FAQs** (…&t=1028).
  - Links report as free backlink data (…&t=1104).
  - Video indexing and platform properties (…&t=1235, …&t=1336).
  - **"Rankings held, clicks fell" → the Generative AI report**, and finding "AI magnets" (…&t=1433, …&t=1561).
  - Deciding what content to create next (…&t=1672).

  Surfer's own tool blurb in the description mentions flagging pages "slipping to page 6–8" for a refresh. That is a vendor claim and the unit is ambiguous. — [video page](https://www.youtube.com/watch?v=93uhFZ_9IzY)
- **Caleb Ulku, "You Didn't Know THIS About Google Search Console" (local SEO), 2026-01-27 (16.7k views)**, https://www.youtube.com/watch?v=CUceqWoibYo.
  - **Page–query alignment check:** for each service page, confirm in the Performance report that its queries match the service. His examples are a plumber's water-heater page and finish carpentry vs deck designs (…&t=116, …&t=167).
  - Native export limits → **Search Analytics for Sheets with a 90-day query+page pull** (…&t=284, …&t=304).
  - An AI prompt to prioritize misaligned pages (…&t=415).
  - Indexing check in the Pages report; fix discovered/crawled-not-indexed with **content improvements plus Request Indexing** (…&t=451, …&t=573).
  - **Modifier mining:** materials, variations and urgency terms already earning impressions, added to the page with a rewrite prompt that avoids stuffing (…&t=656, …&t=736, …&t=810).
  - The description claims the process has been used with 200+ local businesses (vendor claim). — [video page](https://www.youtube.com/watch?v=CUceqWoibYo)
- **Rank Math SEO, "8 Hidden Google Search Console Tricks Revealed", 2024-05-15 (30k views)**, https://www.youtube.com/watch?v=G3OQ2YIjiJw.
  - Long-tail keywords with regex (…&t=39).
  - **Identify infrequently crawled pages** (…&t=279).
  - Schema issues (…&t=366).
  - Removals tool (…&t=424).
  - **Remove unused verification tokens** (a security-hygiene step) (…&t=477).
  - Underperforming pages (…&t=669).
  - Link profile (…&t=714).
  - "Keyword gems" (…&t=802).

  Patterns and thresholds were not available. — [video page](https://www.youtube.com/watch?v=G3OQ2YIjiJw)
- **Rank Math SEO, "Claude + Search Console MCP for FREE SEO Superpowers", 2026-07-09 (19.3k views)**, https://www.youtube.com/watch?v=wb7Ya_z9lMk. Covers setup: Node.js, Claude Desktop, a Google Cloud service account (…&t=277), and the MCP config (…&t=624). Analysis at …&t=982 covers period comparisons, top growing and declining content, striking-distance keywords, and **update-vs-create-new decisions**. — [video page](https://www.youtube.com/watch?v=wb7Ya_z9lMk)
- **Patrick Rice, "Google Search Console Tutorial 2025 – How To Scale Traffic with GSC SEO", 2025-02-06 (49k views)**, https://www.youtube.com/watch?v=iB7_i4giItw. Chapters: filters (…&t=294); **page report and opportunity finding** (…&t=456); individual page report to find top content (…&t=536); GSC for on-page SEO (…&t=902); Page Indexing (…&t=1323); Request indexing (…&t=1487); **viewing the HTML as Google sees it in URL Inspection** (…&t=1518); **regex** (…&t=1767); sitemaps and crawl stats (…&t=1913); links (…&t=2113); keyword research (…&t=2195); **getting full data from GSC** (…&t=2238). The description adds finding low-CTR opportunities and fixing 404s and soft 404s. — [video page](https://www.youtube.com/watch?v=iB7_i4giItw)
- **Ahrefs (Sam Oh), "How to use Google Search Console to Improve Your SEO", 2019-10-16 (194k views; older)**, https://www.youtube.com/watch?v=FXVEb_eklhk.
  - (1) Improve CTR for "underperforming" keywords, defined as **any keyword where the page isn't in positions 1–2** (…&t=50).
  - (2) Find high-ranking but low-CTR pages and analyze why (…&t=187).
  - (3) Check sitemap errors, warnings and exclusions (…&t=328).
  - (4) Find pages that need internal links or pruning (…&t=402).
  - GSC limitations (…&t=542).
  - Source: [video page/description](https://www.youtube.com/watch?v=FXVEb_eklhk)
- **Julian Goldie SEO, "NEW Google Search Console Update is INSANE!", 2026-07-31**, https://www.youtube.com/watch?v=uvJduj-pfAI. Add social profiles to GSC; the description says data takes about **48 hours** to appear (…&t=144). Find the keywords a profile already ranks for (…&t=194), then make platform-native versions to rank **multiple times** for one keyword (…&t=106, …&t=279). He stresses quality over reposting (…&t=427). The rest promotes his agent/"Parasite SEO" products. — [video page](https://www.youtube.com/watch?v=uvJduj-pfAI)
- **Julian Goldie SEO, "5 FREE AI SEO Workflows with ChatGPT & Google Search Console", 2023-08-24**, https://www.youtube.com/watch?v=2ou71rliNfQ. Covers: queries with **impressions but no clicks** for keyword research (…&t=65); improving indexing (…&t=132); internal linking for orphaned pages (…&t=249); money pages (…&t=314); a content-quality and core-update audit (…&t=493). The description also mentions a **"best" query filter**. — [video page](https://www.youtube.com/watch?v=2ou71rliNfQ)
- **Nectiv (Chris Long), "How To Set Up A Search Console MCP With Claude Code", 2026-02-12 (2:18, no description)**, https://www.youtube.com/watch?v=VceXE_9st48; and **Agital, "GSC Training Video From SEO Expert Chris Long", 2025-01-07 (12:34; the description says the full training is on demand)**, https://www.youtube.com/watch?v=BsoDMIsteT8. Neither had chapters or a substantive description, so no tactics could be extracted. — [Nectiv video](https://www.youtube.com/watch?v=VceXE_9st48); [Agital video](https://www.youtube.com/watch?v=BsoDMIsteT8)

### Inferences
- The SOTR transcripts give a Google-endorsed **triage order**:
  1. Is it ranking or indexing?
  2. Is it site-level or URL-level? Use Pages for patterns and URL Inspection for examples.
  3. Is the change expected given what you deployed?
  4. Is it template-level (your code) or site-wide (CDN or host)?
  5. If it's a systemic fix, use "Mark as fixed". If it's a crawled/discovered-not-indexed pattern with no technical cause, it is a quality question.

  This maps cleanly onto an automated monitoring rule set: alert on slope changes, not on absolute counts.
- Creator workflows converge on **page × query** analysis, which the UI does poorly. That explains the repeated pull toward the API, Search Analytics for Sheets, MCP connectors and the new in-product AI filter. Aperghis (C3) gives the Google-hosted justification: the API returns combined query+page rows at far larger volume than the UI.
- The 2026 GSC features (the AI-configured Performance filters, the Generative AI report, platform properties) are already being taught as standard workflow steps by Sturm, Surfer, Goldie and Rank Math within months of launch.

### Gaps
- **No YouTube caption text was retrieved for any creator video.** Tactic details inside chapters (exact regex strings, thresholds, before/after numbers) for Sturm/Quaid, Surfer, Ulku, Rank Math, Patrick Rice, Ahrefs and Goldie are unverified. Only the chapter titles and timestamps are reliable. Fixing this needs either a permitted transcript route or manual viewing.
- **Koray Tuğberk GÜBÜR:** no GSC-focused video found. The nearest is "Recovering From Google Updates…" (2024-11-16, https://www.youtube.com/watch?v=oOEpvuntvVE), which covers query connection, branded search management and engagement. It is not a GSC workflow, so it is not analyzed.
- **Neil Patel:** only old GSC videos (2017 "How to Increase Your Search Traffic Using GSC", https://www.youtube.com/watch?v=df3bnPfiNkA; SEO Unlocked setup, 6 years old). His 2024–26 videos aren't GSC-specific.
- **Matt Diggity:** only a 2018 3-minute Search Analytics walkthrough (https://www.youtube.com/watch?v=_L8CL3Zlh5w).
- **Nathan Gotch:** no GSC-focused video in search results.
- **Income School:** no GSC-focused video. "This strategy SAVED my website's traffic" (2024-06-25, https://www.youtube.com/watch?v=132nBINEX_g) is about Pinterest diversification after the March 2024 update.
- **Ahrefs:** only the 2019 video and Patrick Stox's 2025 demo of *Ahrefs'* GSC reports (https://www.youtube.com/watch?v=jyRXahPu-yw, no chapters).
- **Chris Long:** the gated Agital training and a 2-minute MCP video had no extractable content.
- We could not fetch Edward Sturm's companion Reddit post on crawled-not-indexed, and Podscan transcripts require registration.

## Q2. De-duplicated list of the most distinctive tactics across videos

### Takeaway
After de-duplication, the distinctive, reusable GSC tactics are: pattern- and slope-based reading of the Pages and Crawl Stats reports (Google); a regex branded/non-branded split and question mining (Quaid/Sturm, Surfer, Waisberg); striking-distance and page-two queries as "topical readiness" (Quaid); page–query alignment and modifier mining (Ulku); query→page cannibalization drill-downs (Quaid); API, Sheets and MCP exports for page × query at scale (Aperghis, Ulku, Rank Math, Nectiv); and the new 2026 surfaces: the AI filter, the Generative AI report and platform properties (Sturm, Surfer, Goldie).

### Cited Findings
1. **Read Page Indexing as trend lines and patterns. Confirm that expected changes show up; investigate steep unexpected slopes; ignore flat chronic levels.** — [SOTR 112](https://goo.gle/sotr112-transcript); https://www.youtube.com/watch?v=1-PcVLHplwc&t=105
2. **CDN/bot-protection detection.** A sudden spike in 403/404/410, or mass canonicalization to a foreign URL, points to bot protection. A 200-status interstitial is the worst case. Fix it with the provider, then click Mark as fixed, which tests a sample and speeds up the recrawl. — [SOTR 112](https://goo.gle/sotr112-transcript); https://www.youtube.com/watch?v=1-PcVLHplwc&t=818
3. **Treat Discovered/Crawled-not-indexed patterns with no technical cause as a site-quality review, including page experience and ads, not a URL fix-list.** — [SOTR 112](https://goo.gle/sotr112-transcript), https://www.youtube.com/watch?v=1-PcVLHplwc&t=1232
4. **A new site whose homepage isn't crawled is a technical problem. Use URL Inspection on samples, not site-level ratios.** — [SOTR 061 transcript page](http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed); https://www.youtube.com/watch?v=T2RwEr4bkBw&t=345
5. **Unique, benefit-led page titles as an indexing lever for crawled-not-indexed pages** (keyword + benefit + brand). — [Sturm](https://www.youtube.com/watch?v=ahNhcLDa1LQ&t=128)
6. **Regex branded vs non-branded split** to prove SEO growth and analyze demand. — [Sturm/Quaid](https://www.youtube.com/watch?v=88alcdGtwAE&t=94); [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=639); [Google/Waisberg "Branded query analysis" chapter](https://www.youtube.com/watch?v=5LF6SwB5jZ0&t=289); [Quaid own channel](https://www.youtube.com/watch?v=unlR3iHAmGE&t=2664)
7. **Question-query regex → FAQ, PAA and hub content; page-two queries as a sign of topical readiness to expand.** — [Sturm/Quaid](https://www.youtube.com/watch?v=88alcdGtwAE&t=668); [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=1028)
8. **Striking distance at positions 8–17** (Quaid). By comparison, Ahrefs 2019 calls anything outside positions 1–2 "underperforming", and Sturm uses a position filter on buyer-intent queries in the AI filter. — [Quaid](https://www.youtube.com/watch?v=unlR3iHAmGE&t=170); [Ahrefs](https://www.youtube.com/watch?v=FXVEb_eklhk&t=50); [Sturm](https://www.youtube.com/watch?v=xFjRMvI-a7g&t=142)
9. **High impressions with low or zero clicks as a source of keywords and CTR work.** — [Quaid](https://www.youtube.com/watch?v=unlR3iHAmGE&t=400); [Ahrefs](https://www.youtube.com/watch?v=FXVEb_eklhk&t=187); [Goldie 2023](https://www.youtube.com/watch?v=2ou71rliNfQ&t=65)
10. **Cannibalization from the query→pages drill-down, fixed only when it matters, with a SERP tracker to confirm.** — [Sturm/Quaid](https://www.youtube.com/watch?v=YRN9xDKoQhk&t=1650)
11. **Page–query alignment audit for service pages, plus modifier mining** (materials, variants, urgency terms already getting impressions). — [Ulku](https://www.youtube.com/watch?v=CUceqWoibYo&t=167); [Ulku modifiers](https://www.youtube.com/watch?v=CUceqWoibYo&t=656)
12. **Find the best target keyword for an existing page from its own click data.** — [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=898)
13. **Drop diagnosis:**
    1. Check data anomalies.
    2. Check impressions vs clicks.
    3. Look at 16 months for seasonality.
    4. Compare periods across all tabs.
    5. Sort pages by Clicks Difference.
    6. Use Pages vs URL Inspection depending on scope.
    7. Check Crawl Stats, Security and Manual Actions.
    8. Check Google Trends.

    Then rebuild or retarget the pages that lost clicks.
    — [Google doc](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops); [Waisberg](https://www.youtube.com/watch?v=IIvIRgpCOqc&t=195); [Sturm/Quaid page deltas](https://www.youtube.com/watch?v=YRN9xDKoQhk&t=2363)
14. **"Rankings held, clicks fell" → check the Generative AI report and find "AI magnet" pages.** — [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=1433)
15. **AI/natural-language Performance filter prompts for transactional queries.** — [Sturm](https://www.youtube.com/watch?v=xFjRMvI-a7g&t=97)
16. **Platform properties for Instagram, TikTok, X and YouTube.** Find the queries that already reach social posts; front-load keywords in LinkedIn posts; write full video descriptions and transcripts. — [Sturm](https://www.youtube.com/watch?v=EqyK0ToKepo&t=379); [Goldie](https://www.youtube.com/watch?v=uvJduj-pfAI&t=144); [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=1336)
17. **Scale and history:** API query+page pulls, monthly automated Sheets exports past 16 months, bulk URL Inspection API; Search Analytics for Sheets with 90-day pulls; Claude MCP. — [Aperghis](https://goo.gle/sotr080-transcript); [Ulku](https://www.youtube.com/watch?v=CUceqWoibYo&t=304); [Rank Math MCP](https://www.youtube.com/watch?v=wb7Ya_z9lMk&t=982)
18. **Smaller hygiene tactics:** remove unused verification tokens; find infrequently crawled pages; view the rendered HTML in URL Inspection; custom chart annotations. — [Rank Math](https://www.youtube.com/watch?v=G3OQ2YIjiJw&t=477); [Rank Math crawl](https://www.youtube.com/watch?v=G3OQ2YIjiJw&t=279); [Patrick Rice](https://www.youtube.com/watch?v=iB7_i4giItw&t=1518); [Waisberg](https://www.youtube.com/watch?v=5LF6SwB5jZ0&t=406)
19. **Crawl Stats thresholds:** host status colour windows (7 and 90 days); DNS failures >5% of requests in a day counts as an issue; a robots.txt failure pauses crawling for 12 hours; don't keep 503/429 or a crawl block for more than 2–3 days. — [Crawl Stats help](https://support.google.com/webmasters/answer/9679690); [Waisberg video](https://www.youtube.com/watch?v=x_GoMrl6_u0&t=183)

### Inferences
- Tactics 1–4 and 19 are Google-sourced and safe to encode as automated rules. Tactics 5–18 are practitioner heuristics, and their thresholds (e.g., 8–17) should be configurable, not hard-coded.
- Several creators ship the same "page × query" idea under different names (Quaid's "keyword universe", Ulku's "alignment", Surfer's "best keyword for a page"). A single page×query dataset, pulled from the API, can serve all of them.

### Gaps
- The exact regex strings Quaid/Sturm, Surfer and Rank Math demonstrate, and the before/after results, are unknown without transcripts.
- No creator video gave measured outcomes for the GSC-specific tactics in its metadata, apart from Hawkins' volatility study (8.1M searches, +48.7% volatility).

## Q3. Disagreements between creators (and with Google)

### Takeaway
The biggest split is over **what causes "crawled/discovered – currently not indexed" and what to do about it**. Google calls it sometimes quality and says not to fix it technically. Quaid calls it almost always authority. Sturm points to unique titles. Ulku and Surfer improve the content and request indexing. A second split is over **Request Indexing and indexers**. Smaller disagreements concern rank and position metrics, `site:`, and what counts as underperforming.

### Cited Findings
- **Cause of crawled/discovered-not-indexed:**
  - Mueller says it is *sometimes* a quality signal. With no technical cause, step back and reassess the overall site and page experience; it is not a technical fix. — [SOTR 112](https://goo.gle/sotr112-transcript)
  - **Quaid**: indexing issues are "almost always authority problems, not technical ones". — [Quaid video description](https://www.youtube.com/watch?v=unlR3iHAmGE)
  - **Sturm**: an overlooked cause is generic or near-duplicate page titles; fix the title. — [Sturm](https://www.youtube.com/watch?v=ahNhcLDa1LQ)
  - **Ulku**: improve the content, then Request Indexing. — [Ulku](https://www.youtube.com/watch?v=CUceqWoibYo&t=573)
  - **Surfer**: says you can "diagnose… and fix both". — [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY)
  - Aperghis (a Google Product Expert) says some pages will simply never be indexed, and users should be told so. — [SOTR 080](https://goo.gle/sotr080-transcript)
- **Request Indexing and indexers:**
  - Illyes: a good site doesn't need Request Indexing. Use it only for urgent, unique content or to test indexability. — [SOTR 061](http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed)
  - Quaid: indexing APIs and manual indexing are a red flag. — [Sturm/Quaid E893 description](https://www.youtube.com/watch?v=0oxz_mSy3pQ)
  - Ulku and Patrick Rice teach Request Indexing as a routine fix. — [Ulku](https://www.youtube.com/watch?v=CUceqWoibYo&t=573); [Rice](https://www.youtube.com/watch?v=iB7_i4giItw&t=1487)
  - Sturm demonstrates a third-party indexer (about 30 minutes for a LinkedIn post) but warns about the risks and that indexing ≠ ranking. — [Sturm](https://www.youtube.com/watch?v=EqyK0ToKepo&t=459)
- **Index coverage targets:** Google says there is no meaningful indexed/non-indexed ratio; only about 5% of its own docs site is indexed and that's fine. Tutorials that frame the report as errors to fix (Rice on 404s and soft 404s) imply a clean-up target, while Mueller says expected 404s are correct. — [SOTR 112](https://goo.gle/sotr112-transcript); [Rice description](https://www.youtube.com/watch?v=iB7_i4giItw)
- **Positions and rank metrics:**
  - Hawkins says a single recorded position is no longer trustworthy after the volatility increase; trust GSC plus call tracking and look at top-3 visibility across many checks. — [Sturm/Hawkins](https://www.youtube.com/watch?v=jIh1xEDAqZQ&t=621)
  - Quaid says site-level averages mislead; work keyword by keyword. — [Sturm/Quaid](https://www.youtube.com/watch?v=YRN9xDKoQhk&t=154)
  - Google's drop guide treats average position as a supporting signal only. — [Google doc](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
  - Surfer, by contrast, teaches tracking a single keyword's ranking history in GSC as a substitute for a paid tracker. — [Surfer](https://www.youtube.com/watch?v=93uhFZ_9IzY&t=531)
- **Where the opportunity band sits:** Ahrefs (2019) treats anything outside positions 1–2 as underperforming. Quaid targets positions 8–17. Surfer's tool blurb flags pages "slipping to page 6–8". The thresholds aren't reconciled. — [Ahrefs](https://www.youtube.com/watch?v=FXVEb_eklhk&t=50); [Quaid](https://www.youtube.com/watch?v=unlR3iHAmGE&t=170); [Surfer description](https://www.youtube.com/watch?v=93uhFZ_9IzY)
- **Title/CTR work:** Quaid (per the Sturm episode description) says titles past page 1 rarely improve CTR. Ahrefs teaches CTR optimization for any keyword outside positions 1–2. — [Sturm/Quaid](https://www.youtube.com/watch?v=YRN9xDKoQhk&t=390); [Ahrefs](https://www.youtube.com/watch?v=FXVEb_eklhk&t=50)
- **Ranking multiple times through social:** Goldie promotes platform-native versions of the same keyword content to rank multiple times. Sturm also supports cross-posting the same text across LinkedIn, X, Threads and Facebook, but keeps the website as the "foundation". — [Goldie](https://www.youtube.com/watch?v=uvJduj-pfAI&t=106); [Sturm](https://www.youtube.com/watch?v=EqyK0ToKepo&t=170)
- **`site:`:** Google (Mueller, Illyes) says don't use `site:` to verify indexing; Search Console is the source of truth. None of the creator chapter lists contradicted this explicitly. — [SOTR 112](https://goo.gle/sotr112-transcript); [SOTR 061](http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed)
- **Pruning:** Hawkins reports experiments deleting 1,000 not-visited pages and pruning more than half the content on hit sites. Illyes says deleting old content doesn't free per-site indexing quota, because no such quota exists. These address different goals: quality vs index capacity. — [Sturm/Hawkins](https://www.youtube.com/watch?v=jIh1xEDAqZQ&t=3073); [SOTR 061](http://search-off-the-record.libsyn.com/transcript-for-why-is-my-site-not-indexed)

### Inferences
- For an automated playbook, the defensible default is Google's: no technical "fix" for non-indexed patterns. Add Sturm's title-uniqueness check and Quaid's authority check (internal and external links) as diagnostic steps, not as competing rules. Treat Request Indexing as a single-URL test or urgent tool, not a bulk remedy.
- The disagreement over position thresholds suggests storing striking-distance bands as parameters, defaulting to 8–17 per Quaid and offering 4–20 or page 2 as alternatives.

### Gaps
- Without transcripts we cannot confirm the nuance behind creator claims stated only in descriptions. For example, Quaid may qualify "almost always authority" on air, and Surfer's "fix both" may mean content rather than technical fixes.
