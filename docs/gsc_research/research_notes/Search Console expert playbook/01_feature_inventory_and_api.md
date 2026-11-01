# Google Search Console: Full Feature Inventory and API Reachability (as of 1 Nov 2026)

Legend used throughout: **API** = reachable through the Search Console API (so an MCP server can reach it). **UI-only** = no API endpoint; only the web UI or a manual export. **Partial** = some of the data is reachable another way (another endpoint, BigQuery export, CrUX).

---

## 1. UI: Overview, Insights, Performance (Search / Discover / News / Generative AI / multimodal)

### Takeaway
The Performance reports (four metrics, six dimensions, hourly/daily/weekly/monthly views) are the only part of GSC whose data is fully reachable through the API (`searchanalytics.query`). Several 2025–2026 additions are UI-only as far as the docs say: Insights, query groups, the branded filter, annotations, AI-powered configuration, Generative AI reports and the multimodal search type.

### Cited Findings

**Performance report: core model**
- Search types in the Search results Performance report are Web (text-based), Web (multimodal), Image, Video and News. Multimodal covers searches that use images, such as Google Lens and uploaded images. — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- The four metrics are Clicks, Impressions, CTR and Average position. CTR is "The click count divided by the impression count." Average position is computed site-wide in the chart and per URL or grouping in the table. — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- The dimension tabs are Queries, Pages, Countries, Devices, Search appearance and Dates. — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- Chart data is aggregated by property. In the table, Queries, Countries, Devices and Dates are aggregated by property, while Pages and Search appearance are aggregated by page. — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- The default date range is the past three months, and a 24-hour view exists. Time granularity can be Hourly (only in the 24-hour view), or Daily, Weekly or Monthly (none of which are offered in the 24-hour view). — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- Preliminary data is shown as a dotted line on the chart, and the newest data may still change within a few hours. — [Performance report help](https://support.google.com/webmasters/answer/7576553)
- Export: values shown as "~" or "-" export as zeros. A share link covers only the current view. — [Performance report help](https://support.google.com/webmasters/answer/7576553)

**How the metrics are counted (incl. AI Overviews and AI Mode)**
- An impression counts when a link appears on the results page, even if it is not scrolled into view. In carousels and expandable sections the item usually has to be scrolled into view or expanded. — [About Performance data](https://support.google.com/webmasters/answer/7042828)
- Position is the average of the topmost position the link held. "Ads do not occupy a search position." — [About Performance data](https://support.google.com/webmasters/answer/7042828)
- Data for page variants is credited to Google's chosen canonical URL, and a redirect after the click doesn't change the URL credited. — [About Performance data](https://support.google.com/webmasters/answer/7042828)
- In AI Overviews, all links share the one position the Overview occupies. AI Mode uses standard position rules, and its follow-up questions count as new queries. Data from Search Labs experiments is excluded. — [About Performance data](https://support.google.com/webmasters/answer/7042828)
- AI Mode data has counted toward Search Console Performance totals since a doc update on 16 Jun 2025. — [Search docs changelog](https://developers.google.com/search/updates)
- In Discover, an impression counts once per result per session when the card is scrolled into view. Discover impressions are not aggregated by property, clicks count only when the card itself is tapped, and position is not recorded. — [About Performance data](https://support.google.com/webmasters/answer/7042828)
- In News, data from the News app and news.google.com appears in the News Performance report without a position. News-tab results in Search use normal position rules. — [About Performance data](https://support.google.com/webmasters/answer/7042828)

**Hourly / 24-hour view (2025)**
- The UI's "24 hours" view shows hourly data for the last 24 hours, delayed only a few hours. The API returns hourly data for up to 10 days (announced 9 Apr 2025). — [Blog: hourly data](https://developers.google.com/search/blog/2025/04/san-hourly-data)

**Weekly / monthly views (10 Dec 2025)**
- A granularity drop-down (default "Daily") lets you choose weekly or monthly in the Performance chart for Search results, Google News and Discover. It was available globally to all properties from 10 Dec 2025. When a coarser granularity is selected, exports change their file and tab names, some headers and the sort order. The post doesn't mention API support or how partial periods are handled. — [Blog: weekly/monthly](https://developers.google.com/search/blog/2025/12/weekly-monthly-views-search-console)

**Branded queries filter (announced 20 Nov 2025; available to all eligible sites by 11 Mar 2026)**
- It is "determined by an internal, AI-assisted system", not keyword matching. It recognizes brand names in every language, typos, and queries about the site's unique products. Misclassification is possible, and the filter has no effect on ranking. — [Blog: branded filter](https://developers.google.com/search/blog/2025/11/search-console-branded-filter)
- It appears in the Search results Performance report across web, image, video and news, and shows all four metrics for each segment. A new card in Insights shows the branded/non-branded split of clicks. — [Blog: branded filter](https://developers.google.com/search/blog/2025/11/search-console-branded-filter)
- Eligibility: "only available for top level properties (and not for URL path properties … or subdomain properties)". It also needs enough query volume. The post says nothing about the API. — [Blog: branded filter](https://developers.google.com/search/blog/2025/11/search-console-branded-filter)

**Custom annotations (17 Nov 2025)**
- To add one, right-click a Performance chart and choose "Add annotation". Each note can be up to 120 characters and is tied to a date you choose. Everyone with access to the property can see annotations. The post mentions no API and no limit on the number of annotations. — [Blog: annotations](https://developers.google.com/search/blog/2025/11/custom-chart-annotations)

**AI-powered configuration (experimental, 4 Dec 2025)**
- You describe the analysis in plain language, and the feature sets filters (query, page, country, device, search appearance, date range), comparisons and the visible metrics. It works only in the Search results Performance report, not Discover or News. It cannot sort the table or export, it may misread a request, and it is rolling out to a limited set of sites. — [Blog: AI-powered configuration](https://developers.google.com/search/blog/2025/12/ai-powered-configuration)

**Search Console Insights (integrated into the main UI, 30 Jun 2025)**
- The new Insights report replaces the standalone beta. Its cards show total clicks and impressions with trends, top pages and trending up/down pages, and top queries and trending up/down queries. It links deeper into the Performance report. Achievements (for example, click milestones over the last 28 days) continue by email and are planned for the sidebar. — [Blog: Insights](https://developers.google.com/search/blog/2025/06/search-console-insights)
- A secondary source says Google removed the Analytics integration from Search Console Insights in December 2024. — [ppc.land via search](https://ppc.land/google-launches-new-search-console-insights-report/) (secondary; unverified against a Google source)

**Query groups (27 Oct 2025)**
- AI clusters similar queries into groups shown on the "Queries leading to your site" card in Insights, with Top, Trending up and Trending down views. Each group shows clicks and its queries, which may be truncated, and links to the Performance report. Groups are only for properties with a large query volume and may change over time. "Don't affect ranking." No API is mentioned. — [Blog: query groups](https://developers.google.com/search/blog/2025/10/search-console-query-groups)

**Social channels (experiment, 8 Dec 2025) and platform properties (July 2026)**
- The Dec 2025 experiment added automatically detected social channels linked to a site (YouTube is shown) to Insights. Each channel shows reach (clicks and impressions), top and trending content and queries, countries, and other traffic sources (Image, Video, News, Discover). It was limited to a small set of sites. — [Blog: social channels](https://developers.google.com/search/blog/2025/12/social-channels-search-console)
- **Platform properties** are a new property type for Instagram, TikTok, X and YouTube accounts. They show how posts perform in Search, Discover and News, and became available globally by 29 Jul 2026. The post describes using Insights query groups, the 24-hour filter, export, annotations, and page filters or compare mode with them. It says nothing about the API. — [Blog: platform properties](https://developers.google.com/search/blog/2026/07/platform-properties-social-video-guide); [Blog: social/video platforms](https://developers.google.com/search/blog/2026/07/search-console-social-video-platforms)

**Search Generative AI performance reports (announced 3 Jun 2026; worldwide 31 Aug 2026)**
- Separate reports for Search and Discover show "how often URLs from your site appeared in generative AI features" (AI Overviews and AI Mode in Search, and generative AI features in Discover). Breakdowns are Pages, Countries, Devices (Search only) and Dates (hourly, daily, weekly or monthly). The same data is also included in the overall Performance report. "As of August 31, 2026, we've rolled out these insights to all websites worldwide." — [Blog: Gen AI reports](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
- Metric: **impressions only**, with no clicks at publication. Sites with too few AI impressions may see no report. A property-level **opt-out control** in Settings removes a site from AI Overviews, AI Mode and Discover generative AI features. It was added because of a UK CMA requirement, appeared outside the UK from July 2026, and is separate from Google-Extended. The CMA gave Google until March 2027 to introduce page-level controls. — [SEJ](https://www.searchenginejournal.com/google-search-console-ai-reports-rolled-out-worldwide/587836/)
- The API status is unconfirmed. One practitioner re-tested on 11 Aug 2026 and found that neither the Search Analytics API nor the BigQuery bulk export exposes the generative AI data. — [quattr / neilpatel results via search](https://www.quattr.com/blog/search-console-generative-ai-report) (secondary, single tester); the official post does not mention the API — [Blog](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
- Data anomalies in 2026: Generative AI in Search impressions dropped 13–17 Aug 2026 and were restored on 21 Aug. Generative AI in Discover impressions were reduced on 24 Jun and 13 Aug 2026. — [Data anomalies page](https://support.google.com/webmasters/answer/6211453)

**Web multimodal search reporting (24 Sep 2026)**
- A new **multimodal** option in the search-type filter of both the Performance (Search results) report and the Generative AI report. It covers Lens, Circle to Search on Android, image uploads to Google Search, and Chrome's "Search this image". Data can be exported, and metrics appear only if the site gets such traffic. The post mentions no API. — [Blog: multimodal](https://developers.google.com/search/blog/2026/09/web-multimodal-in-sc)

**Recommendations (5 Aug 2024, experimental)**
- Recommendations appear on the Overview page, are not shown for every site, and rolled out slowly. — [Blog: recommendations](https://developers.google.com/search/blog/2024/08/search-console-recommendations)
- Secondary sources list recommendation types such as adding sitemaps, adding structured data, fixing issues, and watching trending queries and pages. — [SEJ](https://searchenginejournal.com/googles-latest-tool-flags-seo-opportunities-youre-missing/523757) (secondary)

**Data-quality events that affect analysis (2026)**
- From 13 May 2025 to 27 Apr 2026, a logging error inflated impressions. Impressions, CTR and position were affected, but clicks were not; the fix was noted 3 Apr 2026. Bulk export is missing 28 Feb and 1 Mar 2026 for some properties, and that data won't be recovered. From 16–27 Apr 2026, Job listing and Job details appearances weren't reported. Discover logging errors occurred on 7–8 May, 21 May, 24 Jun and 13 Aug 2026. From 7 May 2026, FAQ impressions dropped because FAQ rich results were removed. — [Data anomalies page](https://support.google.com/webmasters/answer/6211453)

### Inferences
- An agent should treat the Performance data from the API as the source of truth for numbers. Insights, query groups, the branded split, annotations and Gen-AI/AI-feature impressions currently have to be rebuilt by the agent (for example, its own brand regex and clustering) or read manually from the UI.
- Because AI Mode and AI Overview impressions and clicks are already mixed into the totals (since June 2025), any year-over-year comparison crossing mid-2025 is distorted. So are impressions between May 2025 and April 2026, because of the logging bug.

### Gaps
- I couldn't fetch the support subpage on advanced filtering and comparison, so these are unverified here: the UI regex syntax (believed to be RE2) and its character limit, the date-range presets (7d/28d/3m/6m/12m/16m/custom), compare mode details, the 1,000-row UI table limit for Performance, and export formats (Google Sheets / Excel / CSV are commonly cited).
- The 16-month retention and roughly 2-day data lag are widely stated, but I didn't fetch an official page confirming them in this session.
- I found no source on whether annotations, the branded filter or query groups have API endpoints. None of the posts mention one, which suggests they are UI-only.
- I found no evidence of a Gemini or AI assistant chat inside GSC beyond the AI-powered configuration experiment. I also found no official Google "Search Console MCP server"; only community servers exist (mikusnuz/gsc-mcp, AminForou/mcp-gsc, ahonn/mcp-server-gsc, ncosentino). — [mcp.so listing](https://mcp.so/servers/mcp-gsc), [GitHub gsc-mcp](https://github.com/mikusnuz/gsc-mcp) (third-party)

---

## 2. UI: Indexing (Page indexing, Video indexing, Sitemaps, Removals) and URL Inspection

### Takeaway
URL Inspection is the only indexing feature with an API equivalent, and the API returns data from the index only (no live test, no request indexing). Sitemaps can be listed, submitted and deleted through the API. The Page indexing report, Video indexing report and Removals tool are UI-only.

### Cited Findings

**Page indexing report: the "why not indexed" reasons, verbatim**
- "Server error (5xx)", "Redirect error", "URL blocked by robots.txt", "URL marked 'noindex'", "Soft 404", "Blocked due to unauthorized request (401)", "Not found (404)", "Blocked due to access forbidden (403)", "URL blocked due to other 4xx issue", "Crawled - currently not indexed", "Discovered - currently not indexed", "Alternate page with proper canonical tag", "Duplicate without user-selected canonical", "Duplicate, Google chose different canonical than user", "Page with redirect". — [Page indexing help](https://support.google.com/webmasters/answer/7440203)
- Warnings (the page is indexed but has a problem): "Indexed, though blocked by robots.txt" and "Page indexed without content". The indexed status is "Page is indexed". — [Page indexing help](https://support.google.com/webmasters/answer/7440203)
- The Source column says whether Google or the Website is responsible. Generally you can fix only "Website" issues. — [Page indexing help](https://support.google.com/webmasters/answer/7440203)
- The sitemap filter offers All known pages (default), All submitted pages, Unsubmitted pages only, or a specific sitemap. — [Page indexing help](https://support.google.com/webmasters/answer/7440203)
- Example tables show at most 1,000 rows. Export includes the chart and table, with "~" and "-" exported as 0. — [Page indexing help](https://support.google.com/webmasters/answer/7440203)
- Validate fix: issue-level states are Not started, Started, Looking good, Passed, Failed and N/A. Instance-level states are Pending, Passed, Failed and Other (Other is treated as Passed). Validation usually takes up to about 2 weeks, and progress is emailed. Restarting a validation rechecks only Pending and Failed URLs. — [Page indexing help](https://support.google.com/webmasters/answer/7440203)

**Video indexing report**
- Shows how many videos are eligible for video features and why the others couldn't be indexed. — [Reports at a glance](https://support.google.com/webmasters/answer/9133276?hl=en)
- It does not validate video markup, so check the Videos structured-data report as well. — [SEJ video indexing](https://www.searchenginejournal.com/google-search-console-video-indexing-report/457261) (secondary)

**URL Inspection (UI)**
- Indexed result: page availability (on Google / on Google with issues / not on Google / alternate version), Discovery (sitemaps and referring page), Crawl (last crawl, crawled as, crawl allowed?, page fetch), Indexing (indexing allowed?, user-declared canonical, Google-selected canonical), Video indexing (only when a video is detected), the AMP and Rich results enhancement sections. — [URL Inspection help](https://support.google.com/webmasters/answer/9012289)
- Live test: reports availability, crawled as, crawl allowed, page fetch, indexing allowed and the user-declared canonical. It does not check sitemaps or referring pages, video indexing, canonical selection, manual actions, quality or security problems, removals, or temporary blocks. A pass doesn't guarantee indexing. — [URL Inspection help](https://support.google.com/webmasters/answer/9012289)
- "View crawled page" or "View tested page" shows the HTML, HTTP response and headers, JavaScript console output and page resources. A screenshot is available only for a successful live test. — [URL Inspection help](https://support.google.com/webmasters/answer/9012289)
- Each property has a daily inspection quota, a separate daily live-test quota and a daily indexing-request quota (numbers not published). Indexing can't be requested for a URL the live test marks non-indexable. For many URLs, submit a sitemap with `<lastmod>` instead. The Google-selected canonical can lag by a few hours. — [URL Inspection help](https://support.google.com/webmasters/answer/9012289)
- Restricted users can use URL Inspection only in "Fetch only" mode. — [Permissions help](https://support.google.com/webmasters/answer/7687615)

**Removals tool**
- It has three tabs: Temporary removals, Outdated content (requests filed by non-owners through the Refresh Outdated Content tool) and SafeSearch filtering (URLs that users reported as adult). — [Removals help](https://support.google.com/webmasters/answer/9689846)
- Request types: "Temporarily remove URL" hides the URL for about 6 months and clears its snippet; "Clear snippet in search" lasts until the page is reindexed. A prefix option covers www and non-www but not subdomains. — [Removals help](https://support.google.com/webmasters/answer/9689846)
- Statuses: Processing request, Request denied, Request canceled, Temporarily removed, Removal expired, Cleared. SafeSearch statuses include Filtered. History covers 6 months. Only owners can file temporary removals. — [Removals help](https://support.google.com/webmasters/answer/9689846)

**robots.txt report (under Settings)**
- Shows robots.txt files for the property's top 20 hosts (http and https for each), "Checked on" time, fetch status (Fetched / Not Fetched – Not found (404) / Not Fetched – Any other reason), size and issue count. Versions from the last 30 days are kept, but only when the file changed. Files returning 404 drop out after 30 days. "Request a recrawl" is available. The report needs a domain-level property (Domain, or a URL-prefix property with no path). — [robots.txt report help](https://support.google.com/webmasters/answer/6062598)

### Inferences
- An agent can rebuild part of the Page indexing view by running URL Inspection over sitemap URLs (2,000 per property per day, see section 4). `coverageState` returns the same verdict strings shown in the UI ("Crawled - currently not indexed" and so on), but the aggregated counts and trend chart are UI-only.
- Validation, Request indexing, removals and robots.txt recrawl are actions available only in the UI, so an agent needs a human to do them (or browser automation, which the brief rules out).

### Gaps
- Daily quotas for Request indexing and live tests are not published (the help page only says limits exist).
- I didn't find a current, verbatim list of Video indexing reasons (for example "No video found", "Video outside the viewport", "Video is too small") in this session.
- I didn't fetch the Sitemaps report UI fields (status: Success / Couldn't fetch / Has errors; discovered pages/videos) from a help page. The API side is described in section 4.

---

## 3. UI: Experience, Shopping, Enhancements, Security & Manual actions, Links, Settings

### Takeaway
None of these reports are in the API. Core Web Vitals can be approximated through CrUX/PSI. Links, Crawl stats, Manual actions, Security issues, HTTPS and the enhancement reports are UI-only, apart from per-URL rich-result and AMP verdicts in the URL Inspection API. Google has been removing reports steadily: Mobile usability in Dec 2023, Page experience in Nov 2024, 6 structured-data types in Sep 2025, practice problem in Jan 2026, and FAQ in Jun–Aug 2026.

### Cited Findings

**Core Web Vitals report**
- Uses CrUX field data, with mobile and desktop reported separately. Thresholds: LCP good ≤2.5 s, poor >4 s; INP good ≤200 ms, poor >500 ms; CLS good ≤0.1, poor >0.25. Statuses are Good, Need improvement and Poor, and a group takes the status of its worst metric. Pages are grouped into URL groups where 75% of visits must meet the status, falling back to an origin group when data is thin. Data covers the last 28 days. A group needs enough LCP and CLS data to appear, and only indexed URLs are included. — [CWV help](https://support.google.com/webmasters/answer/9205520)
- Validation: "Start Tracking" monitors CrUX for 28 days, with states Not started, Started, Looking good, Passed, N/A and Failed. No API is mentioned; Google points to CrUX on BigQuery, PSI and Lighthouse. — [CWV help](https://support.google.com/webmasters/answer/9205520)
- The Page Experience report (which combined CWV and HTTPS) was removed, reportedly in Nov 2024. The CWV and HTTPS reports remain under Experience. — [SEJ](https://www.searchenginejournal.com/google-retires-search-consoles-page-experience-report/532968/)
- The Mobile Usability report, Mobile-Friendly Test and Mobile-Friendly Test API were retired from 1 Dec 2023. — [Search Engine Land](https://searchengineland.com/google-officially-drops-mobile-usability-report-mobile-friendly-test-tool-and-mobile-friendly-test-api-435377)
- In the URL Inspection API, `mobileUsabilityResult` is marked "deprecated". — [UrlInspectionResult](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult)

**Shopping**
- A Shopping section appears only for sites Google identifies as merchants. It contains Product snippets, Merchant listings and Shopping tab listings. — [Shopping reports help](https://support.google.com/webmasters/answer/12660034); [Google blog 2022](https://developers.google.com/search/blog/2022/09/merchant-listings)
- Merchant listings and Product snippets are separate search appearances in Performance. — [Search Engine Land](https://searchengineland.com/google-search-console-breaks-out-merchant-listings-and-product-snippets-appearances-394865)

**Enhancements and structured data: deprecations with dates**
- On 12 Jun 2025, retirement banners went up for Book actions, Course info, Estimated salary, ClaimReview, Learning video, Special announcement and Vehicle listing. Their docs were removed on 9 Sep 2025. — [Search docs changelog](https://developers.google.com/search/updates)
- Reporting for 6 of the 7 types was dropped from GSC, the Rich Results Test and search-appearance filters (Sep 2025). Bulk-export fields for them have been NULL since 1 Oct 2025, and API data was removed in Dec 2025. — [Search Engine Journal](https://www.searchenginejournal.com/google-drops-search-console-reporting-for-six-structured-data-types/555560/); [Search Engine Land](https://searchengineland.com/google-drops-reporting-on-several-structured-data-types-461744)
- Practice problem and Dataset were phased out (announced 5 Nov 2025). Practice problem docs were removed on 6 Jan 2026, and its GSC support ended in January 2026. Dataset markup is used only by Dataset Search. — [Search docs changelog](https://developers.google.com/search/updates); [ppc.land](https://ppc.land/google-phases-out-practice-problem-and-dataset-structured-data/)
- FAQ rich results stopped appearing on 7 May 2026, with a deprecation notice on 8 May and docs removed on 15 Jun 2026. — [Search docs changelog](https://developers.google.com/search/updates); [Data anomalies](https://support.google.com/webmasters/answer/6211453)
- The FAQ search appearance filter, report and Rich Results Test support were removed in June 2026, and API support ends in August 2026. — [SEJ](https://www.searchenginejournal.com/google-drops-faq-rich-results-from-search/574429/) (secondary)
- The Sitelinks search box report was reportedly removed in Nov 2024. — [search result summary of changelog](https://ppc.land/google-launches-new-search-console-insights-report/) (secondary; verify)
- Rich-result types still detected in URL Inspection include breadcrumbs, recipes, products and videos (FAQ was listed on the help page at the time of fetch). — [URL Inspection help](https://support.google.com/webmasters/answer/9012289)

**Manual actions and Security issues**
- The Manual actions report lists actions against the site and the affected section. The Security issues report warns when a site may be hacked or harmful. — [Reports at a glance](https://support.google.com/webmasters/answer/9133276?hl=en)
- Reconsideration requests are a Full-user action. — [Permissions help](https://support.google.com/webmasters/answer/7687615)

**Links report**
- External links: Top linked pages, Top linking sites (root domain) and Top linking text, with drill-downs from site to page. Internal links: Top linked pages. Tables are capped at 1,000 rows. The report is a **sample**, gives no nofollow indication, and may include removed links. — [Links help](https://support.google.com/webmasters/answer/9049606)
- Export: tables up to 1,000 rows. The links export (CSV or Sheets) offers "Latest links" (sorted by discovery date) or "More sample links", up to 100,000 rows each. Links are grouped by canonical URL, sites by root domain with TLD kept, and duplicates are merged. No API exists. — [Links help](https://support.google.com/webmasters/answer/9049606)

**Settings: Crawl stats**
- Found under Settings > Crawl stats, for root-level properties only. Metrics are total crawl requests, total download size and average response time. — [Crawl stats help](https://support.google.com/webmasters/answer/9679690)
- Host status covers robots.txt fetching, DNS resolution and server connectivity, judged over 90 days (green / some issues not recent / recent issue in the last week). If robots.txt fetching fails (429 or 5xx), crawling stops for 12 h, then the last good copy is used for up to 30 days. — [Crawl stats help](https://support.google.com/webmasters/answer/9679690)
- By response: OK (200); Moved permanently (301/308); Moved temporarily (302/307); Moved (other); Not modified (304); Not found (404); robots.txt not available; Unauthorized (401/407); Server error (5XX); Other client error (4XX); DNS unresponsive; DNS error; Fetch error; Page could not be reached; Page timeout; Redirect error; Other error. — [Crawl stats help](https://support.google.com/webmasters/answer/9679690)
- By file type: HTML, Image, Video, JavaScript, CSS, PDF, Other XML, JSON, Syndication, Audio, Geographic data, Other file type, Unknown (Failed). By purpose: Discovery and Refresh. By Googlebot type: Smartphone, Desktop, Image, Video, Page resource load, AdsBot, StoreBot, Other agent type. Example URLs are a representative sample. Only the top 20 child hosts (over 90 days) are listed. — [Crawl stats help](https://support.google.com/webmasters/answer/9679690)

**Settings: users and permissions**
- Roles: Owner (verified or delegated), Full user, Restricted user, Associate (for example a Merchant Center or GA link; associates can't open GSC). Limits: 100 non-owner users, and 500 verified plus delegated owners combined. Verification methods: HTML file, meta tag, DNS, GA, GTM, Google Sites/Blogger. — [Permissions help](https://support.google.com/webmasters/answer/7687615)
- Full users can disavow links, file reconsideration requests, remove URLs, submit sitemaps and share links. Only owners can manage users. — [Permissions help](https://support.google.com/webmasters/answer/7687615)
- Settings also has the per-property **Generative AI opt-out control** (2026). — [SEJ](https://www.searchenginejournal.com/google-search-console-ai-reports-rolled-out-worldwide/587836/)

### Inferences
- Workarounds an agent can use instead of these reports: **CrUX API / CrUX BigQuery / PSI API** in place of the CWV report; **URL Inspection API** (`richResultsResult`, `ampResult`, `indexStatusResult`) per URL in place of the Enhancements, AMP and Page indexing reports; **server logs** in place of Crawl stats; a third-party backlink index, or a periodic manual Links CSV export the user uploads, in place of Links. Manual actions and Security issues can only be watched through email or UI notifications, or by a human checking.

### Gaps
- I didn't fetch details for the HTTPS report, AMP report, Change of address tool, Associations settings, the International targeting deprecation (believed Sept 2022), Disavow tool, Achievements UI, or email/notification settings. Their help pages weren't reached within the call budget.
- I couldn't confirm the exact removal date of the Sitelinks search box report from a Google source.
- The current list of enhancement reports (Breadcrumbs, Videos, Events, Recipes, Review snippets, Product snippets, Merchant listings, Organization, Profile page, Discussion forum, Q&A, Image metadata, etc.) wasn't verified one by one for Nov 2026.

---

## 4. Search Console API: every endpoint, parameter, response, quota

### Takeaway
The API has exactly four resources: Search Analytics, Sitemaps, Sites and URL Inspection. Everything else in GSC is UI-only. Each query returns at most 25,000 rows and you page through with `startRow`. Hourly data goes back 10 days. Quotas are 1,200 QPM per site/user for Search Analytics and 2,000 inspections per day (600 per minute) per site for URL Inspection.

### Cited Findings

**Endpoint list**
- Base `https://www.googleapis.com/webmasters/v3`: `searchanalytics.query` POST `/sites/{siteUrl}/searchAnalytics/query`; `sitemaps.delete` DELETE, `sitemaps.get` GET, `sitemaps.list` GET and `sitemaps.submit` PUT on `/sites/{siteUrl}/sitemaps[/{feedpath}]`; `sites.add` PUT, `sites.delete` DELETE, `sites.get` GET on `/sites/{siteUrl}` and `sites.list` GET `/sites`. Base `https://searchconsole.googleapis.com/v1`: `urlInspection.index.inspect` POST `/urlInspection/index:inspect`. — [API reference index](https://developers.google.com/webmaster-tools/v1/api_reference_index)

**searchanalytics.query: request**
- `startDate` and `endDate` (YYYY-MM-DD, Pacific Time, inclusive). `dimensions[]` can be any filter dimension plus `date` and `hour`, with no repeats. `type` is `web` (default; the "All" tab, excluding Discover and News), `image`, `video`, `news`, `discover` or `googleNews`. `searchType` is deprecated. — [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- `dimensionFilterGroups[]`: `groupType` supports only `and` ("or" is not yet supported). Filter dimensions are `country` (ISO 3166-1 alpha-3), `device` (DESKTOP/MOBILE/TABLET), `page`, `query` and `searchAppearance`. Operators are `equals` (default), `notEquals`, `contains`, `notContains`, `includingRegex` and `excludingRegex`, with regex in **RE2** syntax. Maximum length is **4096 characters**. — [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- `aggregationType`: `auto`, `byPage`, `byProperty` or `byNewsShowcasePanel`. You can't use byProperty when grouping or filtering by page, and byProperty isn't supported for discover or googleNews. byNewsShowcasePanel requires a NEWS_SHOWCASE searchAppearance filter and type discover or googleNews. An invalid value returns an error. — [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- `rowLimit` defaults to 1,000 (range 1–25,000). `startRow` is a zero-based offset; past the end you get success with 0 rows. `dataState` is `final` (default), `all` (includes fresh, incomplete data) or `hourly_all` (use with `hour`). — [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- Hourly: the `HOUR` dimension with `HOURLY_ALL` returns up to **10 days** of hourly data. Timestamps carry a PT offset, for example `2025-04-07T00:00:00-07:00`. Announced 9 Apr 2025. — [Blog: hourly data](https://developers.google.com/search/blog/2025/04/san-hourly-data)

**searchanalytics.query: response**
- `rows[]` with `keys[]`, `clicks`, `impressions`, `ctr` (0–1) and `position` (all doubles); `responseAggregationType`; `metadata.first_incomplete_date` (with dataState=all grouped by date) and `metadata.first_incomplete_hour` (with hourly_all grouped by hour), times in America/Los_Angeles. — [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)

**urlInspection.index.inspect**
- Request: `inspectionUrl` (required; must sit under the property), `siteUrl` (required; URL-prefix properties need a trailing slash, Domain properties use `sc-domain:example.com`), `languageCode` (BCP-47, default en-US). — [inspect method](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect)
- Response fields: `inspectionResultLink`; `indexStatusResult` {`verdict`, `coverageState` (UI string), `robotsTxtState`, `indexingState`, `lastCrawlTime`, `pageFetchState`, `googleCanonical`, `userCanonical`, `sitemap[]`, `referringUrls[]`, `crawledAs`}; `ampResult` {issues, verdict, ampUrl, robotsTxtState, indexingState, ampIndexStatusVerdict, lastCrawlTime, pageFetchState}; `mobileUsabilityResult` (**deprecated**); `richResultsResult` {detectedItems[] {richResultType, items[] {name, issues[] {issueMessage, severity}}}, verdict}. — [UrlInspectionResult](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult)
- Enums. Verdict: PASS, PARTIAL (reserved), FAIL, NEUTRAL. RobotsTxtState: ALLOWED, DISALLOWED. IndexingState: INDEXING_ALLOWED, BLOCKED_BY_META_TAG, BLOCKED_BY_HTTP_HEADER, BLOCKED_BY_ROBOTS_TXT (reserved). PageFetchState: SUCCESSFUL, SOFT_404, BLOCKED_ROBOTS_TXT, NOT_FOUND, ACCESS_DENIED, SERVER_ERROR, REDIRECT_ERROR, ACCESS_FORBIDDEN, BLOCKED_4XX, INTERNAL_CRAWL_ERROR, INVALID_URL. CrawlingUserAgent: DESKTOP, MOBILE. AmpIndexingState: AMP_INDEXING_ALLOWED, BLOCKED_DUE_TO_NOINDEX, BLOCKED_DUE_TO_EXPIRED_UNAVAILABLE_AFTER. Severity: WARNING, ERROR. — [UrlInspectionResult](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult)

**Quotas**
- Search Analytics: **1,200 QPM per site**, **1,200 QPM per user**, and per project 40,000 QPM and 30,000,000 QPD. Load quota is measured in 10-minute and 1-day windows; if you exceed the short-term limit, wait 15 minutes. Grouping or filtering by page and query together is the most expensive, so use shorter ranges and don't re-query. — [Usage limits](https://developers.google.com/webmaster-tools/limits)
- URL Inspection: **2,000 QPD and 600 QPM per site**; per project 10,000,000 QPD and 15,000 QPM. — [Usage limits](https://developers.google.com/webmaster-tools/limits)
- Other resources (sites, sitemaps): 20 QPS and 200 QPM per user, and 100,000,000 QPD per project. — [Usage limits](https://developers.google.com/webmaster-tools/limits)

**Bulk data export to BigQuery (the "API" for unsampled performance data)**
- Tables: `searchdata_site_impression` (by property), `searchdata_url_impression` (by URL) and `ExportLog`. The default dataset is `searchconsole`. — [Bulk export tables help](https://support.google.com/webmasters/answer/12917991)
- Site table: data_date (PT), site_url, query, is_anonymized_query, country, search_type (web/image/video/news/discover/googleNews), device, impressions, clicks, and sum_top_position (average = SUM(sum_top_position)/SUM(impressions)+1). — [Bulk export tables help](https://support.google.com/webmasters/answer/12917991)
- URL table: adds url, is_anonymized_discover, the `is_[search_appearance]` booleans (for example is_amp_top_stories, is_job_listing, is_job_details) and the zero-based sum_position. — [Bulk export tables help](https://support.google.com/webmasters/answer/12917991)
- ExportLog: agenda (SEARCHDATA), namespace, data_date, epoch_version (incremented when data is revised) and publish_time. — [Bulk export tables help](https://support.google.com/webmasters/answer/12917991)
- Rare queries are anonymized; the docs call the query value both "zero-length string" and null, which is inconsistent. Export runs daily. Failed days are retried for about a week and then lost (no later backfill). Tables are kept indefinitely unless you set partition expiration. Rows aren't compressed, so aggregate in SQL. — [Bulk export tables help](https://support.google.com/webmasters/answer/12917991)
- Bulk-export fields for the 6 deprecated structured-data types have been NULL since 1 Oct 2025. — [SEJ](https://www.searchenginejournal.com/google-drops-search-console-reporting-for-six-structured-data-types/555560/)

**What the API does not expose (UI-only)**
- Not in the API (based on the full method list above): Page indexing report aggregates, Video indexing, Crawl stats, robots.txt report, Links, CWV, HTTPS, Manual actions, Security issues, Removals, Enhancements and Shopping reports, Insights, query groups, recommendations, achievements, the branded filter, annotations, Generative AI reports, user management, change of address, Request indexing and live test. — [API reference index](https://developers.google.com/webmaster-tools/v1/api_reference_index)
- Generative AI report data is reportedly missing from both the API and bulk export (one practitioner's test, 11 Aug 2026). — [quattr](https://www.quattr.com/blog/search-console-generative-ai-report) (secondary)
- Multimodal search type: the Sep 2026 post doesn't mention the API, and the API's `type` enum has no multimodal value. — [Blog: multimodal](https://developers.google.com/search/blog/2026/09/web-multimodal-in-sc); [searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)

### Inferences
- An MCP server built on this API can offer about ten tools: list/get/add/delete site, list/get/submit/delete sitemap, query search analytics, and inspect URL. For high-volume query and URL data, an agent should prefer the BigQuery export, since API row totals are capped and queries are sampled or anonymized.
- `type=web` in the API corresponds to the UI's "Web" tab. Multimodal web data seems to have no separate API filter, so it is probably inside `web` or not exposed (unverified).
- The UI's branded filter and query groups have no API, so the agent should keep its own brand-term regex using `includingRegex`/`excludingRegex` (RE2, with the 4096-character filter limit) and its own query clustering.
- The Indexing API (`indexing.googleapis.com`) is a separate API, officially limited to JobPosting and BroadcastEvent pages. It is not part of the Search Console API, and I didn't verify it in this session.

### Gaps
- I didn't fetch the Sitemaps resource fields (path, lastSubmitted, isPending, isSitemapsIndex, type, lastDownloaded, warnings, errors, contents[]) or the Sites resource `permissionLevel` enum (siteOwner, siteFullUser, siteRestrictedUser, siteUnverifiedUser) in this session. They are believed correct from prior knowledge but are not cited.
- I didn't fetch the OAuth scopes (`webmasters` / `webmasters.readonly`).
- The share of anonymized queries and the exact UI data lag weren't confirmed from an official page this session.
- I found no official statement on whether a `searchAppearance` value or `type` exists for AI Overviews, AI Mode or generative AI features in the API as of Nov 2026.
