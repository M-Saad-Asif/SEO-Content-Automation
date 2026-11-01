# Indexing diagnosis with GSC: Page indexing report, URL Inspection (UI + API), Sitemaps, Removals (status-by-status playbook, Nov 2026)

Tag legend used throughout:
- **[API/MCP-automatable]**: doable with Search Analytics / Sitemaps API calls or with the site's own code/crawler. No Page indexing report is needed.
- **[URL-Inspection-API]**: needs `urlInspection.index.inspect`, which has a quota of 2,000/day and 600/min per property.
- **[UI-only/manual]**: needs the GSC web UI. That covers the Page indexing report, Validate fix, Request indexing, the live test, screenshots, rendered HTML, page resources, the JS console, and Removals.

Important framing for the automation: the agent's MCP has **no Page indexing report**. Its stand-in for "list all issues" is: (a) pull the sitemap URLs plus the pages that get impressions from Search Analytics, (b) run every candidate URL through the URL Inspection API and bucket the results by `coverageState` (the same verbatim strings the report uses), and (c) group the results by URL pattern or template. Everything below is mapped onto that loop.

---

## Q1. Status-by-status playbook: technical "Not indexed" errors (5xx, Redirect error, robots.txt, noindex, Soft 404, 401, 404, 403, other 4xx, Page removal tool)

### Takeaway
Google's official position is that "Not indexed is not necessarily bad." Only issues whose **Source = Website** are usually fixable, and you should only fix them when the affected URLs are ones you *want* indexed: URLs you link to internally or list in sitemaps. Of these errors, 5xx, redirect errors and 403/401 on wanted URLs are urgent. 404s on removed pages and deliberate noindex or robots blocks are normal.

### Cited Findings
**Google's definitions and fixes (verbatim status names)**: [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)
- **Server error (5xx)**: the server returned a 500-level error. Diagnose host status in the **Crawl Stats report** and fix server connectivity. [UI-only/manual for Crawl Stats; URL-Inspection-API `pageFetchState=SERVER_ERROR`]
- **Redirect error**: the redirect chain was too long, there was a redirect loop, the redirect URL was over-long, or the chain contained a bad or empty URL. Google suggests debugging with a tool such as Lighthouse. [URL-Inspection-API `pageFetchState=REDIRECT_ERROR`; API/MCP-automatable via your own crawler following the hops]
- **URL blocked by robots.txt**: per Google, a robots.txt block "does not guarantee that the page won't be indexed through some other means". To keep a page out of the index, *remove* the block and use noindex. [URL-Inspection-API `robotsTxtState=DISALLOWED`, `pageFetchState=BLOCKED_ROBOTS_TXT`]
- **URL marked 'noindex'**: if the page should be indexed, remove the directive and confirm with a live test. [URL-Inspection-API `indexingState=BLOCKED_BY_META_TAG` / `BLOCKED_BY_HTTP_HEADER`; live test is UI-only]
- **Soft 404**: the page says "not found" (or is effectively empty) but returns a non-404 code. Return a real 404 for missing pages, or add content. [URL-Inspection-API `pageFetchState=SOFT_404`]
- **Blocked due to unauthorized request (401)**: remove the authorization requirement, or allow Googlebot after verifying its identity. [URL-Inspection-API `ACCESS_DENIED`]
- **Not found (404)**: only fix 404s that you link to or list in a sitemap. 301 moved pages. Removed pages with no replacement can stay 404. [URL-Inspection-API `NOT_FOUND`]
- **Blocked due to access forbidden (403)**: Googlebot never sends credentials, so a 403 means server misconfiguration (WAF/CDN bot blocking is the usual culprit; see Inferences). Admit non-signed-in users or explicitly allow Googlebot. [URL-Inspection-API `ACCESS_FORBIDDEN`]
- **URL blocked due to other 4xx issue**: debug it with URL Inspection. [URL-Inspection-API `BLOCKED_4XX`]
- The API also returns `INTERNAL_CRAWL_ERROR` and `INVALID_URL` page-fetch states, which have no direct report-row equivalent. [Google: UrlInspectionResult reference](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult)

**Redirects are reported under the destination's status (key diagnostic gotcha)**
- GSC often reports a redirecting URL with the status of its *final destination*, "even if that url is outside of your own site". So a 301 can show up as Blocked by robots.txt, Soft 404, Noindexed, Crawled – not indexed, or 404. John Mueller has explained this in hangouts (2019) and admitted it "can be a bit confusing". The fix is to inspect the destination and every hop, and to fix the destination rather than the redirect. A redirect through a robots-blocked hop gets reported as robots-blocked. Old-domain URLs redirecting to never-migrated pages report as 404. — Glenn Gabe, GSQi (Nov 3, 2022), [Demystifying the true destination URL](https://www.gsqi.com/marketing-blog/demystifying-true-destination-url-for-redirects-gsc/) [API/MCP-automatable: follow the hops with your own HTTP client; URL-Inspection-API on the final URL]

**Soft 404 root causes (practitioner)**: Glenn Gabe, GSQi (Feb 19, 2021), [Soft 404 analysis](https://www.gsqi.com/marketing-blog/google-search-console-soft-404s-analysis/)
- Most frequent: out-of-stock or discontinued product pages that return 200 with a "no longer available" message; thin pages (slideshows, job listings, image or video pages with little text); pages showing "not found" text with a 200 status; blank 200 pages.
- Google said on Jan 11, 2021 that "Soft 404 reporting is now more accurate", and soft-404 counts dropped sharply from Jan 5, 2021. Gabe re-inspected former soft 404s and found them as "URL is unknown to Google", Crawled/Discovered not indexed, still soft 404, or **indexed**. He calls indexed the most urgent case because thin pages then count toward site quality.
- Fixes: a hard 404 if the page is gone; improve the page if it should stay; for indexed low-quality pages, noindex, 301 to a newer version, or 404. Google's docs say soft 404s "can eat up crawl budget". [URL-Inspection-API to re-bucket; content fixes via the writing pipeline]
- In SPAs (JS apps), Google says soft 404s happen because the app returns 200 for missing content. Fix by redirecting to a URL that returns a real 404, or by adding `noindex` via JS when the content doesn't exist. — [Google: Fix Search-related JavaScript problems](https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript)
- Faceted ecommerce: Google says to return **404** for filter combinations with no results, duplicate or nonsensical filters, and nonexistent pagination URLs, and *not* to redirect them to a generic not-found page. (Doc last updated 2025-12-18.) — [Google: Faceted navigation](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation) [API/MCP-automatable in site code]

**What's normal vs urgent (Google + Gabe)**
- Expected non-indexing includes intentional robots.txt blocks, noindex pages you want hidden, duplicates, and removed pages with no replacement. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)
- Large clients with more than 1M daily Google clicks have "hundreds of thousands of 404s" and do fine. Noindexed, robots-blocked and 404 URLs are fine when they reflect intended behavior. — Glenn Gabe (Dec 10, 2018), [True size of your site](https://www.gsqi.com/marketing-blog/how-to-find-true-size-of-your-site-index-coverage-reporting/)
- 404/410 is "a strong signal not to crawl that URL again". Robots-blocked URLs stay in the crawl queue longer. Avoid long redirect chains. — [Google: Crawl budget management](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)

### Inferences
- **Urgency ranking for the agent:** (1) 5xx, 403, 401, robots, noindex or redirect errors on URLs that are **in the sitemap or get impressions**. These are always bugs, because the sitemap and those impressions both declare the URL as wanted. (2) Soft 404 on money or product pages. (3) 404s that are internally linked. (4) Everything else is informational.
- A 403/401 seen only by Googlebot, while browsers get 200, usually points to a CDN/WAF bot rule. The agent can check this by comparing `pageFetchState` with a plain HTTP fetch from its own client. That is my inference; Google only says "server misconfiguration".
- "Server error (5xx)" spikes are best cross-checked against the Crawl Stats host-status panel, which is UI-only. There is no API for Crawl Stats.

### Gaps
- Google's report doc (as fetched) does not describe the **"Blocked by page removal tool"** row. My recollection is that it means an active Removals request is hiding the URL, but I couldn't fetch the current wording, so verify it in the UI.
- I found no practitioner frequency ranking that quantifies how often each 5xx/4xx cause occurs.

---

## Q2. "Crawled – currently not indexed" and "Discovered – currently not indexed": causes, diagnosis, fixes, Google's quality statements

### Takeaway
Both statuses are mainly **priority and quality judgments**, not technical failures. Gary Illyes (2024) and John Mueller with Martin Splitt (Search Off the Record, July 2026) both tie high counts to site-wide quality. "Discovered" adds crawl capacity and server health as causes, plus internal linking. The senior-SEO workflow runs in four steps. Triage and exclude URL types that shouldn't be indexed. Group the remaining URLs by template. Rule out rendering, duplication and internal-linking causes. Then improve the content (or merge, noindex or 404 it) and resubmit *once*.

### Cited Findings
**Google's official meaning**
- Crawled – currently not indexed: "It may be indexed later", and you don't need to resubmit it for crawling. Discovered – currently not indexed: found but not yet crawled, usually because Google postponed the crawl to avoid overloading the site. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)
- Neither status can be tested in the **live test**. URL Inspection's live test can't reproduce "Crawled – currently not indexed", "Discovered – currently not indexed" or "Page indexed without content". — [Google: URL Inspection tool](https://support.google.com/webmasters/answer/9012289)

**Google statements on site quality (Illyes, Mueller, Splitt)**
- **Gary Illyes, SERP Conf (Bulgaria, May 2024):** overall site quality strongly affects how many URLs are crawled but not indexed: "If the number of these URLs is very high that could hint at general quality issues." A change in Google's "perception of the site" can suddenly lead it to index far more or far fewer URLs. Other causes he gave: "dupe elimination" (a very similar version is already indexed with stronger signals), and technical bugs such as a server that "served the same exact page to every single URL on the site". — Roger Montti, SEJ (Jul 3, 2024), [Google explains crawled not indexed](https://www.searchenginejournal.com/google-explains-crawled-not-indexed/521311/)
- **John Mueller and Martin Splitt, Search Off the Record, "How to read the indexing report" (covered Jul 16–17, 2026):** Mueller says that when "our systems are seriously worried about the quality of a website" they "will reduce the number of pages at the index". Both not-indexed statuses mean Google knows about the URL and will "take another look". When many pages are unindexed with no technical cause, "you almost need to take a step back and think about the quality overall". On AI content: "That's not to say that all AI-generated content is bad", but content that reads like "Anyone could have written this. This tells me nothing" may not be indexed. He also pointed to the whole page experience: content buried under ads or interstitials, filler such as long recipe intros, and slow pages. Splitt: if other sites cover the topic as well or better, the page may add little to the index. Asked whether non-indexing is often a quality sign, Mueller answered "Sometimes." — Barry Schwartz, [SER](https://seroundtable.com/google-crawled-not-indexed-quality-ai-content-41701.html); Roger Montti, [SEJ](https://www.searchenginejournal.com/google-explains-seo-connection-of-site-quality-to-non-indexed-pages/582683/)
- **Mueller on "Discovered" (2018–2023):** a high number of Discovered URLs "sounds like [Google is] seeing a high number of pages ... and they are not interested in indexing all of these". Poor internal linking is sometimes the cause, and a page that is only in the sitemap without internal links is less likely to be indexed. — [Marie Haynes hangout notes, Nov 16, 2018](https://mariehaynes.com/november-16-2018-google-help-hangout-notes). Crawling on large sites can be "limited by how your website can handle more crawling", but "in most cases ... it's more about overall website quality". Cutting a site from 8M to 2M pages won't help unless quality rises. Google can take "a couple of months, a half a year, sometimes even longer" to understand how a site fits on the web. — Roger Montti, SEJ (Jul 11, 2023), [Fixing Discovered – currently not indexed](https://www.searchenginejournal.com/fixing-discovered-currently-not-indexed/491432/)
- Mueller (per Glenn Gabe): Google considers **all indexed pages** when it evaluates site quality. Making Google crawl and process many unnecessary URLs is harmful even with correct canonicals, because Google has to crawl each one to see the canonical. — [Gabe, True size of your site](https://www.gsqi.com/marketing-blog/how-to-find-true-size-of-your-site-index-coverage-reporting/); Gabe also says both Crawled and Discovered can signal quality and/or crawl-budget issues, and gives a case where ~40–45% of indexed pages were low quality — [GSQi: estimate low-quality indexing by page type](https://www.gsqi.com/marketing-blog/how-to-estimate-low-quality-indexing-problem-by-page-type/)
- Google's crawl-budget guide is aimed at sites with 1M+ pages, sites with 10k+ pages changing daily, **or** sites with "many URLs ... classified as Discovered – currently not indexed". Crawl demand depends on "perceived inventory", popularity, staleness and page quality. Crawled pages are evaluated individually for index suitability. — [Google: Crawl budget management](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)

**Practitioner diagnosis and fix sequence**
- **Onely (Bartosz Góralewicz, article dated Oct 30, 2026)**: [How to fix Crawled – currently not indexed](https://www.onely.com/blog/how-to-fix-crawled-currently-not-indexed-in-google-search-console/)
  1. Triage. Tag, filter, internal-search, archive and paginated pages often belong outside the index. [API/MCP-automatable: URL-pattern classifier]
  2. In Page indexing, switch to **"All submitted pages"**, export, and group by URL pattern ("one template usually has one cause"). [UI-only; API equivalent: sitemap URLs → URL Inspection API → group by `coverageState`]
  3. Rendering: use View crawled page and Test live URL. If the main content is missing from the rendered HTML, put it in the HTML Google receives. [UI-only for rendered HTML]
  4. Thin or low-value content: add first-hand experience, original data and worked examples. Forum threads with no replies at crawl time get judged low-quality.
  5. Previously indexed pages that dropped: check for accidental content loss between versions, replacement by better content, or algorithm changes.
  6. Internal links: add a few **body-text links from already-indexed, trafficked pages**. These matter more than footer or sidebar links. [API/MCP-automatable: pick link sources by Search Analytics clicks]
  7. Duplicates: redirects are the strongest signal, then canonicals, then sitemap inclusion (weakest). Example: an RSS feed was chosen as canonical over the real page. Returning 404 for the feed URLs fixed it "within days".
  8. Request indexing **once** after the fix. Repeat requests don't speed things up. A requested crawl takes "a few days to a few weeks".
  9. A temporary sitemap helps for redirect-destination URLs that are crawled but not indexed.
  10. Exclude on purpose: noindex or canonicalize search, filter and parameter URLs; merge thin pages into a stronger page and 301 the old URL.
  - Onely also says "Crawled" rarely reflects crawl budget, while "Discovered" calls for checking site quality, crawl budget and server load.
- **Ahrefs (Patrick Stox, updated Jul 16, 2024)**: the status "typically points to some kind of quality issue". Causes: thin, duplicate or intent-mismatched content; misplaced noindex, robots or canonical directives; server errors; weak internal linking; new or low-authority sites. — [Ahrefs](https://ahrefs.com/blog/crawled-currently-not-indexed/)
- **Mueller (via SEJ, 2023), product and thin pages:** add unique, useful detail such as measurements, weight, colors, pairing suggestions, manuals, FAQs and ratings. Link popular sections from the main menu and homepage. Check server error logs and hosting limits (e.g., PHP memory) for "Discovered". — [SEJ](https://www.searchenginejournal.com/fixing-discovered-currently-not-indexed/491432/)
- **Koray Tuğberk Gübür (Holistic SEO):** his "quality threshold" model has Google scoring a source against a query or query network, and a source that passes the threshold moves from a supplemental index into the main index. Thresholds shift with ongoing "predictive ranking" tests, and queries and documents are grouped into topical clusters. — [OnCrawl: Importance of quality thresholds](https://www.oncrawl.com/technical-seo/importance-quality-thresholds-predictive-ranking/); [JDN](https://www.journaldunet.com/seo/1515659-connaissez-vous-le-seuil-de-qualite-en-seo-vous-devriez/). This is a practitioner model, not documented Google behavior.
- Szymon Słowik's case study frames non-indexing of a new portal as a cost-to-value calculation (crawl demand, information gain, authority, retrieval cost). This is the author's interpretation. — [Słowik case study](https://www.szymonslowik.com/case-study-why-google-wont-index-a-new-portal/)

**The user's own tactic (Performance tab → queries → H2s/content rewrite)**
- Consistent with Google's guidance: improve the content rather than resubmit unchanged pages; Onely says unchanged resubmitted pages usually don't move. — [Onely](https://www.onely.com/blog/how-to-fix-crawled-currently-not-indexed-in-google-search-console/)

### Inferences
- **Decision tree for the agent per URL with `coverageState` = "Crawled - currently not indexed":**
  1. Is the URL a type that shouldn't be indexed (tag, filter, search, paginated, feed, thin UGC)? If yes, noindex, canonicalize, 404 or merge, and stop. [API/MCP-automatable]
  2. Does the URL redirect? If so, the status belongs to the destination, so inspect that instead (Gabe). [URL-Inspection-API]
  3. Is `googleCanonical` ≠ the URL (when present)? Then it's a duplication problem, so go to Q3.
  4. Rendering check: fetch the raw HTML yourself and confirm the main content, H1 and internal links are in the server response. If they aren't, it's a CSR problem. URL Inspection has no rendered-HTML field in the API; that view is UI-only.
  5. Search Analytics with a page filter over 16 months. Impressions mean the page was indexed at some point and dropped (check for content loss or a stronger competing page), and the queries it got are the seed topics for the rewrite (the user's tactic). Zero impressions means it never earned a place, so do a full rewrite or merge. The query data only exists for pages that were *previously* indexed, or for the canonical of their duplicate cluster.
  6. Content rewrite via the existing pipeline. Then add 3–5 contextual body links from top-click indexed pages, update `<lastmod>`, and (UI) request indexing once. Re-inspect via the API after 2–4 weeks.
- **Site-level trigger:** if Crawled + Discovered make up a large share of submitted URLs across many templates, treat it as a site-quality issue (Illyes, Mueller), not a page issue. Pruning or consolidating low-value sections should come before rewriting individual pages. No Google-published ratio exists. A working heuristic: compare the index rate per sitemap segment and investigate the segments far below the site average.
- **"Discovered" specifically:** check server response time and 5xx/429 errors (Crawl Stats, UI-only), internal-link depth, and whether the URL appears only in the sitemap. On big sites, cut perceived inventory (faceted or parameter URLs) so demand concentrates on wanted URLs.

### Gaps
- I found no Tomek Rudzki/Onely statistics in the current Onely article (the 2026 version is under Bartosz Góralewicz's name with no figures). Older Onely indexing studies weren't retrieved.
- There's no verified Jes Scholz or Barry Adams source specifically on these two statuses; searches didn't surface one.
- Google publishes no percentage threshold for an "unhealthy" not-indexed ratio. Mueller declined to quantify it.
- There's no direct Koray Gübür quote on "Crawled/Discovered" specifically, only secondary summaries of his quality-threshold model.

---

## Q3. Canonical and duplicate statuses: Alternate page with proper canonical tag; Duplicate without user-selected canonical; Duplicate, Google chose different canonical than user; Page with redirect

### Takeaway
"Alternate page with proper canonical tag" and "Page with redirect" are normally fine. "Duplicate without user-selected canonical" is "working as intended" but shows that you haven't declared canonicals. "Google chose different canonical than user" is the actionable one. Compare `userCanonical` with `googleCanonical` in the URL Inspection API, then fix conflicting signals or make the pages genuinely different.

### Cited Findings
- Alternate page with proper canonical: "there is nothing you need to do." Duplicate without user-selected canonical: "This is not an error, but is working as intended". Inspect to see Google's choice. Google chose different canonical: compare Google-selected with user-declared, and if the pages aren't similar Google won't pick yours. Page with redirect: non-canonical redirect URLs aren't indexed, and the target may or may not be. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)
- Google's listed causes for choosing a different canonical: same-content language or region variants without `hreflang`; a CMS or plugin emitting a wrong `rel=canonical` or 3xx; a misconfigured server returning another domain's content or identical soft-404 pages; hacking that injects a cross-domain canonical or redirect; syndication (partners should block indexing instead); copycat sites; pages that aren't different enough. Fixes: add hreflang, fix the CMS, fix the server, make clustered pages clearly different ("clear, significant differences tend to split out faster"), file a DMCA for copycats, and **allow up to two weeks** for re-evaluation. Request indexing for the most important URLs only, because of quotas. — [Google: Canonicalization troubleshooting](https://developers.google.com/search/docs/crawling-indexing/canonicalization-troubleshooting)
- The URL Inspection UI shows the user-declared canonical (from link tag, HTTP header, sitemap and so on; "None" is fine for non-alternate pages) and the Google-selected canonical, which can be "a few hours out of date". — [Google: URL Inspection tool](https://support.google.com/webmasters/answer/9012289). The API equivalents are `userCanonical`, which is absent if none is declared, and `googleCanonical`, which is absent if the page isn't indexed. — [API reference](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult) [URL-Inspection-API]
- The live test does **not** check canonical selection or duplicate status. — [Google: URL Inspection tool](https://support.google.com/webmasters/answer/9012289)
- Signal strength: redirect > canonical tag > sitemap inclusion. — [Onely](https://www.onely.com/blog/how-to-fix-crawled-currently-not-indexed-in-google-search-console/)
- Gabe's red flags: parameterized duplicates with self-referencing canonicals, and Google overriding the user canonical at scale. — [GSQi](https://www.gsqi.com/marketing-blog/how-to-find-true-size-of-your-site-index-coverage-reporting/); [GSQi: NOT taking the canonical hint](https://www.gsqi.com/marketing-blog/how-to-estimate-low-quality-indexing-problem-by-page-type/)
- Faceted navigation: Google says `rel=canonical` on filtered URLs is a weaker, slower long-term signal than robots.txt for keeping facets from being crawled. Use the `&` separator and a consistent filter order when facets should be indexable. — [Google: Faceted navigation](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation)

### Inferences
- Automatable audit: for each sitemap URL, call the API and flag cases where `googleCanonical` ≠ `userCanonical` (normalize the trailing slash and protocol first). Classify the Google-chosen URL into one of these:
  - a different internal URL: a duplicate cluster, so merge, differentiate or 301;
  - another domain: syndication, a copycat, or a hack;
  - the http or non-www variant: a site-wide redirect or canonical misconfiguration. [URL-Inspection-API]
- A blog post that loses canonical selection to a category or tag page, or to another post on the same topic, is a **cannibalization signal**. Feed it to the content pipeline as a "merge or differentiate" task.

### Gaps
- Google doesn't say how long a "Duplicate, Google chose different" override persists after the fix beyond the "up to two weeks" re-evaluation note.

---

## Q4. Warnings: "Indexed, though blocked by robots.txt" and "Page indexed without content"

### Takeaway
Both are rarely huge, but they're diagnostic red flags. The first means robots.txt is being misused as a deindexing tool. The second usually means Googlebot got empty or unreadable content: cloaking, an unsupported format, or a rendering or bot-blocking failure.

### Cited Findings
- Indexed, though blocked by robots.txt: Google indexed the URL from links without crawling it. To keep it out, remove the robots block and use noindex. To include it, unblock it. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)
- Page indexed without content: Google couldn't read the content, "possibly due to cloaking or an unsupported format". It is not a robots.txt block. Check the Coverage section in URL Inspection. It can't be reproduced in the live test. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203); [URL Inspection](https://support.google.com/webmasters/answer/9012289)
- Gabe: indexed-but-blocked pages are generally not counted toward site quality because Google can't crawl their content. — [GSQi search result summary](https://www.gsqi.com/marketing-blog/how-to-estimate-low-quality-indexing-problem-by-page-type/)
- Removals guidance: don't use robots.txt for permanent removal. If a page was blocked first, unblock it so Google can see the noindex or 404. — [Google: Removals tool](https://support.google.com/webmasters/answer/9689846)

### Inferences
- For "Page indexed without content", the agent should fetch the URL with a Googlebot UA and a normal UA and compare body length and content. Check CDN or WAF challenges (JS challenge pages), lazy-loaded or CSR-only content, and non-HTML files. [API/MCP-automatable]

### Gaps
- No practitioner case study with quantified root-cause frequencies for "Page indexed without content" was retrieved.

---

## Q5. URL Inspection deep use (UI) and the URL Inspection API: fields, enums, quotas, batch audits, request-indexing practice

### Takeaway
The API returns the *indexed* state only: verdict, coverageState, robots, indexing, page fetch, canonicals, last crawl, crawledAs, sitemaps and referring URLs. The live test, rendered HTML, screenshot, page resources, JS console and Request indexing are **UI-only**. The quota is 2,000 inspections/day and 600/min **per property**, so adding more properties (URL-prefix properties per folder) multiplies the throughput.

### Cited Findings
**API fields (verbatim)**: [Google: UrlInspectionResult](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult) [URL-Inspection-API]
- `inspectionResult.inspectionResultLink`, `indexStatusResult`, `ampResult` (AMP pages only), `richResultsResult` (absent if none), and `mobileUsabilityResult`, which is **deprecated**.
- `indexStatusResult`: `sitemap[]`, `referringUrls[]`, `verdict` (PASS / PARTIAL [reserved, no longer used] / FAIL / NEUTRAL), `coverageState` (free-text string matching the report's status names), `robotsTxtState` (ALLOWED / DISALLOWED), `indexingState` (INDEXING_ALLOWED / BLOCKED_BY_META_TAG / BLOCKED_BY_HTTP_HEADER / BLOCKED_BY_ROBOTS_TXT [reserved]), `lastCrawlTime` (RFC3339; absent if never crawled successfully), `pageFetchState` (SUCCESSFUL, SOFT_404, BLOCKED_ROBOTS_TXT, NOT_FOUND, ACCESS_DENIED, SERVER_ERROR, REDIRECT_ERROR, ACCESS_FORBIDDEN, BLOCKED_4XX, INTERNAL_CRAWL_ERROR, INVALID_URL), `googleCanonical` (absent if not indexed), `userCanonical`, `crawledAs` (DESKTOP / MOBILE).
- `richResultsResult.detectedItems[].richResultType`, `items[].issues[].issueMessage` and `severity` (WARNING/ERROR).

**Quotas**
- URL Inspection: **2,000 queries/day and 600/min per site**; 10M/day and 15k/min per project. Search Analytics: 1,200 QPM per site and per user; 30M QPD per project. Sitemaps and other resources: 20 QPS and 200 QPM per user. — [Google: Usage limits](https://developers.google.com/webmaster-tools/limits)
- The UI "Request indexing" button has a per-property daily limit, but **no official number** is published. A 2020 community thread guessed about 50/day and a Product Expert said the docs show no number. — [Google community thread](https://support.google.com/webmasters/thread/76080485/indexing-request-results-in-quota-exceeded?hl=en)
- Screaming Frog (v16.6+) integrates the API: up to 2k URLs per property per day, applied to the first 2k crawled URLs (breadth-first), with an option to "Ignore Non-Indexable URLs for URL Inspection" to save quota. When over quota, wait 24h and re-run the next batch in List mode. The limit is per property, so setting up multiple properties gets you more than 2k. — [Screaming Frog: Automate the URL Inspection API](https://www.screamingfrog.co.uk/how-to-automate-the-url-inspection-api); [SEL: 8 tools using the API](https://searchengineland.com/seo-tools-google-search-console-url-inspection-api-379955) [API/MCP-automatable]

**UI fields and live test**: [Google: URL Inspection tool](https://support.google.com/webmasters/answer/9012289)
- Discovery shows the sitemaps pointing to the URL ("No referring sitemap" if none) and the referring page, which may be absent. Crawl shows the last crawl (all other indexed data comes from that crawl), crawled as (desktop or mobile), crawl allowed, page fetch, and indexing allowed. Indexing shows user-declared and Google-selected canonicals.
- The live test follows redirects silently and doesn't show the final URL. It doesn't check sitemaps, referring pages, canonical selection, duplicate status or video indexing. A pass ("URL is available to Google") doesn't guarantee indexing. Neither the indexed view nor the live test checks manual actions, security issues, removals or quality.
- View crawled page / View tested page shows raw HTML, HTTP headers, the JS console output and loaded resources. Crawled data is available only when the URL is on Google. **Screenshots appear only in a successful live test**, taken of the mobile version.
- Request indexing runs a quick check and queues the URL. It's refused if the live test says the page isn't indexable. Google gives inconsistent timing on the same page ("a day or so" vs "up to a week or two") and recommends sitemaps with `<lastmod>` for many URLs.

**Rendering and CSR diagnosis**: [Google: Fix Search-related JavaScript problems](https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript) [UI-only for rendered DOM; the agent can approximate with a headless render]
- Use the Rich Results Test or URL Inspection to see "loaded resources, JavaScript console output and exceptions, rendered DOM".
- Known failure modes, each with a fix:
  - SPA soft 404s;
  - content gated behind permission prompts;
  - `#/` fragment routing (use the History API);
  - reliance on localStorage, sessionStorage or cookies (WRS "does not retain state across page loads");
  - WRS ignoring caching headers (use fingerprinted filenames);
  - unsupported APIs such as WebGL (polyfill or SSR);
  - WebSockets or WebRTC (provide an HTTP fallback);
  - shadow-DOM components without `<slot>`;
  - JS paywalls.
- Retest after fixes.

**Mobile usability removal**
- Google retired the Mobile Usability report, the Mobile-Friendly Test tool and its API on **Dec 1, 2023**, and points to Lighthouse instead. — [SEL](https://searchengineland.com/google-officially-drops-mobile-usability-report-mobile-friendly-test-tool-and-mobile-friendly-test-api-435377). The API's `mobileUsabilityResult` is marked deprecated. — [API reference](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult). The brief says "2025 removal", but the sources date it to Dec 2023.

### Inferences
- **Batch audit design for the agent:**
  1. Seed list = every sitemap URL, plus every page with impressions in the last 16 months (Search Analytics `page` dimension), plus top internally linked URLs from the site crawl.
  2. Prioritize by business value and impressions, then inspect up to about 1,900 URLs/day per property, keeping headroom for ad-hoc checks. Cache results with a timestamp.
  3. Bucket by `coverageState`. That gives an API-built replica of the Page indexing report.
  4. Derive flags:
     - `sitemap[]` empty while the URL is wanted means it's missing from the sitemap;
     - `referringUrls[]` empty means it may be orphaned;
     - `lastCrawlTime` older than about 90 days on a key page means low crawl demand;
     - `crawledAs`=DESKTOP is worth noting, since mobile-first is the default;
     - `googleCanonical` ≠ `userCanonical` is a canonical conflict;
     - `indexingState` not ALLOWED on a sitemap URL is an accidental noindex;
     - `pageFetchState` not SUCCESSFUL is a technical error.
- **The rendered-HTML diff (CSR/hydration check) can't be done through the API.** The agent should approximate it by comparing raw server HTML (curl) against a headless-Chrome render. Text or links that appear only after JS mean a rendering dependency. The final confirmation through "View crawled page" or a live-test screenshot is a manual step for the user.
- Request indexing should be reserved for a few high-value URLs after a real change, once per URL (Onely). Bulk discovery should go through sitemaps with accurate lastmod. The Indexing API isn't covered here; Google restricts it to JobPosting and BroadcastEvent pages. That comes from my background knowledge and wasn't verified in this session.

### Gaps
- The exact UI live-test and Request indexing daily quotas are undocumented.
- I didn't verify whether `crawledAs`=DESKTOP still appears for any sites in 2026 now that mobile-first indexing is fully rolled out.

---

## Q6. Sitemaps report: segmentation for indexation-rate measurement, lastmod, sitemap index, errors

### Takeaway
Sitemaps are the main lever for both *discovery* and *measurement*. Segmenting sitemaps by section or template lets you filter the Page indexing report per sitemap and compute index rates per segment. Accurate `<lastmod>` is now Google's crawl-scheduling signal, since the ping endpoint is gone and changefreq and priority are ignored.

### Cited Findings
- The report's sitemap filter offers All known pages, All submitted pages, Unsubmitted pages only, and a specific sitemap URL or sitemap index. A URL counts as submitted even if Google also found it another way. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203) [UI-only]
- Validation tip: validate against a sitemap that contains only key pages, which finishes faster. Validation then applies only to those sitemap items as they were when you requested it. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203); [Google: Video indexing report](https://support.google.com/webmasters/answer/9495631)
- **Ping endpoint deprecated** (announced Jun 26, 2023; it now returns 404). Submit sitemaps through GSC or robots.txt. Google uses `lastmod` "as a signal for scheduling crawls". It has to reflect the "last significant modification" (main text, structured data or links changed, not footer tweaks) and "consistently match reality", or "eventually we're not going to believe you anymore". Pages whose dates are hard to pin down (home, category) can omit lastmod. `changefreq` and `priority` aren't used. — [Google Search Central blog](https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping); [SEL coverage](https://searchengineland.com/google-to-deprecate-sitemaps-ping-endpoint-later-this-year-428661)
- Keep sitemaps current, include lastmod, and support 304 Not Modified. — [Google: Crawl budget management](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Gabe's red flags: many indexed URLs missing from sitemaps (e.g., 200k indexed vs 4k in sitemaps), sitemap URLs that are soft 404s or robots-blocked, and a big gap between processed and indexed URLs (e.g., 1,000 indexed vs ~600k processed; 73k indexed vs 29.5M crawlable). He sets no fixed ratio. — [GSQi](https://www.gsqi.com/marketing-blog/how-to-find-true-size-of-your-site-index-coverage-reporting/)
- Onely: a temporary sitemap helps with redirect-destination URLs that are crawled but not indexed. — [Onely](https://www.onely.com/blog/how-to-fix-crawled-currently-not-indexed-in-google-search-console/)
- Google: sites under about 500 pages "probably don't need to use this report" and can use `site:` instead. Don't expect every URL to be indexed; indexed counts should rise gradually; the example list is capped at 1,000 URLs. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203)

### Inferences
- **Segmentation recipe** [API/MCP-automatable via the Sitemaps API plus site code]:
  - Use one sitemap per template or section (`/blog/`, `/services/`, `/locations/`, `/products/`, `/categories/`), each kept to 50k URLs or fewer, under one sitemap index.
  - Then compute the index rate per segment. It can be approximated with API-only data as (URLs with `verdict=PASS` from URL Inspection) ÷ (URLs in the segment).
  - A second proxy is the share of segment URLs with ≥1 impression in Search Analytics over 90 days.
  - Segments well below the site median get flagged for quality or template review.
- The Sitemaps API (`sitemaps.list/get/submit`) returns submitted, error and warning counts per sitemap. Per-sitemap *indexed* counts are no longer shown in the API, from memory. Verify that against the current API reference.
- Sitemap hygiene the agent should enforce: only canonical, 200, indexable URLs; no redirects, noindex or robots-blocked URLs; and lastmod changes only on meaningful edits. A content-pipeline rewrite *is* a meaningful edit, so bump lastmod.

### Gaps
- I didn't fetch the current Sitemaps report help page, so the exact sitemap error names ("Couldn't fetch", "Sitemap is HTML", etc.) aren't verified here.
- I'm not confident whether the Sitemaps API still returns an `indexed` count in `contents[]`; it needs checking against the API reference.

---

## Q7. Removals tool: when to use it and when never to

### Takeaway
Removals is an **emergency hide** for about six months. It doesn't remove anything from the index permanently, and using it for canonicalization or cleanup can backfire.

### Cited Findings
- Temporary removal hides a URL from results for "about six months". It doesn't stop crawling. It matches http/https and www/non-www variants, and a prefix can hide a whole directory or site. "Clear snippet" blanks the description until the page is recrawled. — [Google: Removals tool](https://support.google.com/webmasters/answer/9689846) [UI-only/manual]
- **Never use it for:**
  - canonicalization, since it "could remove all versions (http/https and www/non-www)";
  - site moves ("won't remove old content or URLs");
  - cleaning up crawl errors or old 404s, which drop out naturally;
  - whole-site blocking after a hack (block only the spam URLs and clean up the hack).
  - It's "only one step" toward permanent removal. — [Google: Removals tool](https://support.google.com/webmasters/answer/9689846)
- Permanent removal means a 404/410, password protection, or noindex (which Google calls less secure). Don't use robots.txt. — [Google: Removals tool](https://support.google.com/webmasters/answer/9689846)
- Outdated content belongs in the separate Refresh Outdated Content tool. SafeSearch filtering has its own statuses, and site owners can request review after 2–3 months. — [Google: Removals tool](https://support.google.com/webmasters/answer/9689846)

### Inferences
- The agent should never call Removals on its own (there is no API anyway). It should recommend it to the user only for legal, PII, leak or hacked-spam emergencies, always paired with a permanent fix (404/410 or noindex) inside the six-month window.
- If URL Inspection shows a wanted URL as blocked by the removal tool, the user should cancel the request in the UI.

### Gaps
- The wording of the "Blocked by page removal tool" row wasn't present in the fetched doc (see Q1 gaps).

---

## Q8. Validate fix: strategy and timing

### Takeaway
Validation is optional bookkeeping. Google recrawls fixed pages either way. If you use it, fix every instance first, validate once, scope it with a key-pages sitemap, and expect about two weeks or longer.

### Cited Findings
- Fix every instance; validation stops if one remains. Click Validate fix once and don't click again until it passes or fails. It "typically takes up to about two weeks, but in some cases can take much longer", with email updates. On failure, use See details, fix, and start a new validation. Validation states are Not started, Started, Looking good, Passed, N/A and Failed; instance states are Pending, Passed, Failed and Other. An issue stays in the table until 90 days after its last instance is gone. — [Google: Page indexing report](https://support.google.com/webmasters/answer/7440203) [UI-only]
- You don't have to validate, because Google updates counts as it recrawls. Only Pending or Failed URLs are rechecked after a failure. Use judgment, since some issues (e.g., robots blocks) are intentional. — [Google: Video indexing report](https://support.google.com/webmasters/answer/9495631)
- Onely: unchanged resubmitted pages usually don't move. Request indexing once. A requested crawl takes days to weeks. — [Onely](https://www.onely.com/blog/how-to-fix-crawled-currently-not-indexed-in-google-search-console/)
- Canonical clusters can take up to two weeks to be re-evaluated. — [Google canonical troubleshooting](https://developers.google.com/search/docs/crawling-indexing/canonicalization-troubleshooting). Site-level quality reassessment can take "a couple of months, a half a year, sometimes even longer" (Mueller). — [SEJ 2023](https://www.searchenginejournal.com/fixing-discovered-currently-not-indexed/491432/)

### Inferences
- **Wait-time heuristics for the agent's re-check scheduler:**
  - technical fixes (5xx, 4xx, noindex, robots): re-inspect via the API after 7–14 days;
  - canonical or duplicate fixes: after 14–21 days;
  - content-quality rewrites for Crawled/Discovered: after 3–6 weeks;
  - site-wide quality work: judge on a 2–6 month horizon.
- The agent's API-side "validation" is to re-inspect the fixed URL set and compare `coverageState` and `lastCrawlTime`. If `lastCrawlTime` hasn't moved, Google hasn't re-crawled yet, so don't judge the fix.

### Gaps
- There's no public data on how long validation takes by issue type beyond "about two weeks".

---

## Q9. Video indexing statuses

### Takeaway
The video report has two page statuses ("No video indexed", "Video indexed") and a set of reasons. Most of the reasons are about **watch-page focus**, **player position and size** and **thumbnails**.

### Cited Findings
All of the following are verbatim reasons with Google's fixes. — [Google: Video indexing report](https://support.google.com/webmasters/answer/9495631) [UI-only for the report; URL-Inspection-API/live test only says whether a video was detected]
- **Video isn't on a watch page**: make one video the page's main focus; confirm the video is in the rendered HTML and move the container higher; add paywalled-content structured data if relevant.
- **Cannot determine video position and size**: load the player at its real size on page load; don't use click-to-load placeholders.
- **MRSS failure; try using schema.org instead**.
- **No thumbnail URL provided**: provide one via structured data, a sitemap or MRSS, with a consistent title, thumbnail URL and video URL across sources.
- **Unsupported thumbnail format** and **Invalid thumbnail size**.
- **Thumbnail blocked by robots.txt**.
- **Thumbnail is transparent**: at least 80% of pixels need alpha >250.
- **Thumbnail could not be crawled due to hostload**: wait and see the crawl budget docs.
- **Thumbnail could not be reached** and **Invalid thumbnail** (catch-all).
- **Video not processed**: use stable video URLs. **Video not processed yet**: check back in a few days.
- **Video not found on host service**: verify the video ID and that it's public.
- The URL Inspection live test doesn't report video indexing status, only whether a video was detected. — [Google: URL Inspection](https://support.google.com/webmasters/answer/9012289)

### Inferences
- For a service-business site, a video is usually supporting content, so "Video isn't on a watch page" is expected and can be ignored unless the page is meant to rank in video results.

### Gaps
- Older reason names listed in the brief ("Video outside the viewport", "Video too small", "Video too tall", "Google could not determine the prominent video") aren't in the current doc. They appear to have been folded into "Video isn't on a watch page" and "Cannot determine video position and size", but I couldn't confirm a dated change.

---

## Q10. New sites, programmatic/large sites, ecommerce facets: practitioner heuristics and thresholds

### Takeaway
Small sites (under about 500 pages) should focus on the key URLs being indexed and on content quality. Large, programmatic or ecommerce sites mainly have a **perceived-inventory** problem. Cut URL bloat (facets, parameters, internal search, thin programmatic pages) so crawl demand and quality evaluation concentrate on valuable pages, and remember Google evaluates quality across *all indexed* pages.

### Cited Findings
- Sites under 500 pages "probably don't need" the report; don't expect every URL to be indexed. — [Google](https://support.google.com/webmasters/answer/7440203)
- Crawl-budget guidance applies to 1M+ pages, 10k+ pages changing daily, or sites with many Discovered URLs. Don't use noindex to save crawl budget, because Google still requests the page. Don't use robots.txt to temporarily reallocate budget. Consolidate duplicates and use robots.txt for unimportant URL spaces such as sort orders and infinite scroll. — [Google: Crawl budget](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Facets: block them with robots.txt if they aren't needed in Search; canonical and nofollow are weaker signals; 404 empty combinations. — [Google: Faceted navigation](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation)
- Mueller: cutting 8M product pages to 2M only helps if quality rises. Product pages need unique specs, FAQs, manuals and ratings. New sites can take months to "fit". — [SEJ 2023](https://www.searchenginejournal.com/fixing-discovered-currently-not-indexed/491432/)
- Gabe: the options for low-value pages are to boost them, 404/410 them, or noindex them if they must stay. An infinite-spaces case from on-site search created up to 10M URLs. — [GSQi: remove vs improve](https://www.gsqi.com/marketing-blog/remove-versus-improve-low-quality-thin-content/); [GSQi true size](https://www.gsqi.com/marketing-blog/how-to-find-true-size-of-your-site-index-coverage-reporting/)
- Gabe on indexing surges and drops: sudden swings in GSC indexing counts can be benign. — [GSQi: Scary surge and drop in indexing](https://www.gsqi.com/marketing-blog/scary-surge-drop-indexing-google-search-console/) (title only; not fetched in detail)

### Inferences
- For programmatic location or service pages, the content pipeline should ensure each page has unique entities and data. A page that differs only by a swapped city name is the textbook "Duplicate, Google chose different canonical" or "Crawled – not indexed" case (Google's "insufficiently different pages").
- New-site heuristic: expect weeks to months. Prioritize homepage-linked hub pages, keep the sitemap tiny and clean, and don't spam Request indexing.

### Gaps
- I didn't retrieve Reddit r/TechSEO or r/bigseo threads or YouTube transcripts, so community anecdotes are missing.
- I didn't fetch Aleyda Solis, Moz or Sitebulb guides, so their specific tactics aren't represented here.
