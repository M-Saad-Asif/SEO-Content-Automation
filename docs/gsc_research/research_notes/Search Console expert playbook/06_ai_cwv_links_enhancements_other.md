# GSC Expert Playbook — AI features, CWV/HTTPS, Links, Enhancements, Video, Manual actions/Security, Discover/News, Search appearance/Shopping, Settings & ops, Migrations/traffic drops

Research date: 2026-11-01. Tags: **[API/MCP-automatable]** = Search Analytics API / URL Inspection API / Sites API / BigQuery bulk export; **[external API]** = CrUX API, PSI API, Rich Results Test, schema validator, SERP APIs, third-party tools; **[UI-only]** = no programmatic access, an agent must ask a human or use browser automation.

Note on method: ~27 tool calls. Items marked "(prior knowledge, not re-verified this session)" come from the researcher's background knowledge and are placed under Inferences or Gaps, never as cited facts.

---

## 1. AI Overviews & AI Mode in Search Console

### Takeaway
Since June 16, 2025 AI Mode data counts inside the normal Performance report (Web search type), blended with blue links, and AI Overview links all share the AI Overview's single position. On June 3, 2026 Google launched a separate, **UI-only, impressions-only** "Search generative AI performance" report (AI Overviews + AI Mode, plus a Discover gen-AI report). It went worldwide on Aug 31, 2026, has Pages/Countries/Dates/Devices, no queries, no clicks, no position, and is not in the API or BigQuery export. Query-level AI estimation still relies on practitioner inference: regex for long or conversational queries, impression-up/CTR-down decoupling, and SERP-API joins.

### Cited Findings
**What Google counts (main Performance report)**
- AI Mode data counts toward Search Console performance totals from **Jun 16, 2025** (Search Central documentation changelog). — [Google Search Central updates](https://developers.google.com/search/updates)
- AI Overviews and AI Mode traffic "is included in overall search data" and appears in Performance under the **Web** search type. — [Google: AI features and your website (updated 2025-12-10)](https://developers.google.com/search/docs/appearance/ai-features)
- Counting rules (Performance report help): an AI Overview "occupies a single position in search results… all links in the AI Overview are assigned that same position". A click on an external link in AIO or AI Mode counts as a click. "Standard impression rules apply". Position in AI Mode "follows the same methodology as a Google Search results page". An AI Mode follow-up question is "essentially performing a new query", so all its data is attributed to the new query. Search Labs experiments are excluded. Carousel items must be scrolled into view. Expanding an FAQ/PAA item is not a click, but links inside the expanded section get impressions. — [Search Console Help: Performance report metrics](https://support.google.com/webmasters/answer/7042828)
- John Mueller (reported): Search Console counts links, and a hidden link counts only after the user expands it. — [CrawlRaven summary citing Mueller](https://crawlraven.com/blog/gsc-ai-performance-reports)
- Eligibility to be a supporting link: the page must be "indexed and eligible to be shown in Google Search with a snippet". There are no extra technical requirements, and no special schema, AI text files or llms.txt are needed. Controls are nosnippet, data-nosnippet, max-snippet and noindex. Google-Extended governs training/grounding in other Google systems. — [Google: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)

**New dedicated reports (2026)**
- **Jun 3, 2026:** Google announced "Search Generative AI performance reports" in Search Console: separate Search (AI Overviews + AI Mode) and Discover (generative AI features) reports, first tested with UK site owners, alongside a "Search generative AI control" opt-out. — [Search Central blog, Jun 2026](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports); [Google blog announcement](https://blog.google/products-and-platforms/products/search/new-controls-website-owners/)
- **Aug 31, 2026:** "we've rolled out these insights to all websites worldwide." Sites with too few AI impressions may see no report. — [SEJ, Matt G. Southern, 2026-08-31](https://www.searchenginejournal.com/google-search-console-ai-reports-rolled-out-worldwide/587836/)
- Search gen-AI report spec: the only metric is **impressions** ("how many times links to your site were shown in a generative AI feature"). Tabs are Pages (final URL after redirects, assigned to canonical), Countries, Dates (day/week/month, Pacific Time) and Devices. Filters are Web text-based / Web multimodal plus URL filters. The chart aggregates by property, so two results from the same site in one AI feature count as one impression. With a URL filter it aggregates by URL, and the Pages table aggregates by page, so chart and table totals can differ. Fresh data is preliminary (dotted line). Export has a 1,000-row table limit. The data is **included** in the Web Performance report (a companion report, not additive). Search Labs is excluded. — [Search Console Help: Search generative AI performance report](https://support.google.com/webmasters/answer/16984139); Discover counterpart: [help 16983858](https://support.google.com/webmasters/answer/16983858)
- The report sits at the `/performance/search-analytics/ai` path, is labelled Beta, and offers hourly/daily/weekly/monthly granularity per one summary. **No clicks, CTR, position or query data.** Google "may add metrics over time". — [CrawlRaven](https://crawlraven.com/blog/gsc-ai-performance-reports) (conflicts slightly with the Google help page, which lists day/week/month; trust the help page)
- One source says data begins **May 18, 2026** with no backfill. — [Search result summary of 2026 coverage, e.g. pikaseo](https://pikaseo.com/articles/google-search-console-ai-performance-reports-2026) (not confirmed by Google, so treat as unverified)
- **API/BigQuery:** Suganthan Mohanadasan re-verified on Aug 11, 2026 that neither the Search Analytics API nor the BigQuery bulk export exposes generative-AI data. The report is UI-only. — [SEJ, Suganthan Mohanadasan, 2026-08-19](https://www.searchenginejournal.com/how-to-track-google-ai-mode-traffic-in-search-console/586194/)
- **Opt-out control** ("Search generative AI control") is property-level under Settings. It excludes the site from AIO, AI Mode and Discover AI features, is not a ranking signal elsewhere, and does not affect AI training (that is Google-Extended). The UK CMA conduct requirement (Jun 3, 2026) gives Google until **March 2027** for page-level controls and expects click-through data. — [SEJ](https://www.searchenginejournal.com/google-search-console-ai-reports-rolled-out-worldwide/587836/); [Help: control](https://support.google.com/webmasters/answer/16908024). The "Control what you share" docs were updated Oct 21, 2026 to include it. — [Search Central updates](https://developers.google.com/search/updates)
- **Sep 24, 2026: Multimodal search type.** Under Web, the Search type filter now splits into "Text-based" and "Multimodal" (Lens, Circle to Search, image uploads, Chrome "Search this image"). It applies in both the Performance and gen-AI reports. Multimodal has no query data. — [Search Engine Roundtable](https://www.seroundtable.com/google-search-console-multimodal-search-type-filter-42156.html); [PPC Land](https://ppc.land/google-search-console-gains-lens-and-circle-to-search-data-without-queries/)
- Other 2026 AI-related docs: "Optimizing your website for generative AI features on Google Search" guide (**May 15, 2026**) says AI optimisation "is still SEO". Features are rooted in core ranking systems using RAG and query fan-out, with no special markup or chunking. — [Search Central blog May 2026](https://developers.google.com/search/blog/2026/05/a-new-resource-for-optimizing); [Semrush coverage](https://www.semrush.com/blog/google-publishes-generative-ai-search-guide/). Preferred sources extended to AIO/AI Mode (May 27, 2026). Llms.txt non-use clarified (Jun 15, 2026). Spam policies apply to gen-AI responses (May 15, 2026). — [Search Central updates](https://developers.google.com/search/updates)

**Practitioner estimation methods (query level, since the gen-AI report has no queries)**
- **Chris Long regex** (Search Engine Land, Feb 2026): Performance → Query → Custom regex flagging queries of 10+ words as proxies for AI-style prompts. Earlier June 2025 variants flagged very long (e.g. 32+ word) strings. — [Pixis summary](https://pixis.ai/blog/how-to-find-ai-queries-in-google-search-console/) / [SEJ AI Mode tracking](https://www.searchenginejournal.com/how-to-track-google-ai-mode-traffic-in-search-console/586194/). Typical word-count regex form (prior knowledge, verify before use): `^(\S+\s){9,}\S+$` [API/MCP-automatable: Search Analytics API supports `includingRegex`/`excludingRegex` (RE2) on query]
- **Jean-Christophe Chouinard regex** (LinkedIn, Aug 14, 2026): matches prompt verbs (write, draft, generate, summarize, explain, act as), greetings, acknowledgements ("yes", "ok", "sounds good"), refusals and follow-ups ("more", "continue", "show me more"), i.e. AI Mode conversation strings leaking into GSC. It is English-only. — [SEJ, Suganthan](https://www.searchenginejournal.com/how-to-track-google-ai-mode-traffic-in-search-console/586194/) [API/MCP-automatable]
- **Glenn Gabe:** pulls the full query set via the API (Analytics Edge in Excel), then has an LLM (Claude) classify likely AI Mode queries. — [same SEJ article](https://www.searchenginejournal.com/how-to-track-google-ai-mode-traffic-in-search-console/586194/) [API/MCP-automatable]
- **Suganthan Mohanadasan:** browser classifier plus GSC MCP tool `genai_conversation_queries` and a BigQuery MCP running the same detector on the bulk export. Caveat: 57.7% of impressions sat in the anonymized pool for one site (59 days to Aug 11, 2026), so any regex result is an undercount. — [same SEJ article](https://www.searchenginejournal.com/how-to-track-google-ai-mode-traffic-in-search-console/586194/) [API/MCP-automatable]
- **"Great Decoupling":** impressions up while clicks/CTR fall, attributed to AI Overviews. An Ahrefs study (300k keywords) found an average CTR drop of 34.5% on AIO-enabled queries. One theory is that AIO citations "share" position-1 impressions. — [Ahrefs: The Great Decoupling](https://ahrefs.com/blog/the-great-decoupling); [SEJ: explaining to C-level](https://www.searchenginejournal.com/explaining-the-great-decoupling-to-c-level/549902/)
- **SERP-API join:** pull query-level GSC data, join to a SERP API flagging AIO presence, and compare CTR with vs. without AIO. Sample figures in that guide are illustrative, not measured. — [apiserpent](https://apiserpent.com/blog/great-decoupling-measure-ai-overview-traffic-loss) [external API]
- Suggested uses for the new report: baseline-export AI impressions, sort Pages by AI impressions to find most-cited URLs, trend over weeks rather than absolutes, compare AI impressions with classic organic clicks per page for "cited but not visited" pages, use Countries for target markets, and make sure crawlers aren't blocked and nosnippet isn't overused. — [CrawlRaven](https://crawlraven.com/blog/gsc-ai-performance-reports)
- Lily Ray (Amsive) criticised the impressions-only scope. — [CrawlRaven](https://crawlraven.com/blog/gsc-ai-performance-reports)
- Don't add gen-AI report figures to Search results totals, because they are already included. — [SEO Kreativ](https://www.seo-kreativ.de/en/blog/search-console-multimodal-en/); [Google help](https://support.google.com/webmasters/answer/16984139)

### Inferences
- Agent workflow: (a) [API] weekly regex pulls (long-query + conversational) with impressions/clicks/CTR/position trends. (b) [API] per-page decoupling score = Δimpressions vs Δclicks over 28d YoY. Pages with impressions ↑, CTR ↓ and position stable or improving in the 1–3 band are likely AIO-cited. (c) [UI-only] monthly human/browser export of the gen-AI report Pages tab, joined with the API page data to get an "AI impression share" per URL. (d) [external API] AIO presence and citation checks via SERP APIs or third-party AI-visibility tools (Semrush, Ahrefs Brand Radar, Profound, etc.) for queries, which GSC cannot supply.
- Citation optimisation signals from GSC: pages with high AI impressions but low organic clicks need a stronger "click reason" (original data, tools, visuals). Long-query clusters with impressions but no clicks show sub-questions that query fan-out pulls in. Answer them explicitly in indexable text, keep pages snippet-eligible (no blanket nosnippet / max-snippet:0) and make sure structured data matches visible text.
- Because the position of every AIO link equals the AIO's position, a sudden average-position *improvement* to ~1–2 on a long-tail query with collapsing CTR is a classic AIO-citation fingerprint.

### Gaps
- No Google statement on whether the gen-AI report will reach the API/bulk export. The CMA requirement implies click data may come; no date was found.
- The verbatim regexes of Chris Long and Chouinard were not retrieved (the articles describe them without reproducing them).
- No direct primary sources were found this session from Kevin Indig, Mike King/iPullRank or Aleyda Solis on GSC-based AI measurement.
- Data start date (May 18, 2026) comes from a single secondary source.

---

## 2. Core Web Vitals report, Page experience, HTTPS report

### Takeaway
The CWV report is CrUX field data (p75, 28-day rolling), grouped into similar-URL groups, separate for mobile and desktop, with group status equal to the worst metric. Validation is passive 28-day monitoring. The report is UI-only, so agents automate with the CrUX API / CrUX History API / PSI API.

### Cited Findings
- Thresholds (Good / Needs improvement / Poor): LCP ≤2.5s / ≤4s / >4s. INP ≤200ms / ≤500ms / >500ms. CLS ≤0.1 / ≤0.25 / >0.25. The value shown is the one 75% of visits meet. — [Search Console Help: Core Web Vitals report](https://support.google.com/webmasters/answer/9205520)
- Data source is CrUX field data from real users, including URLs outside any GSC property. A group's status equals its worst metric. A group needs enough LCP **and** CLS data to show. With too little data it falls back to an origin group (protocol://host:port). Mobile and desktop are reported separately. The report is a *sample* of indexed pages. Data is assigned to the actual URL, not the canonical. — [same](https://support.google.com/webmasters/answer/9205520)
- Validation: "Start Tracking" begins a **28-day** monitoring period and doesn't trigger recrawl. An issue is fixed if absent from all URLs for the full window. States are Not started → Started → Looking good → Passed / Failed (then "Start new validation"). URL states are Pending / Passed / Failed. — [same](https://support.google.com/webmasters/answer/9205520)
- Prioritisation (Google): fix Poor first, then by number of URLs affected or importance. Groups list URLs by impressions, so the top URLs drive group status. PSI single-URL results can differ because a URL may be an outlier in its group. — [same](https://support.google.com/webmasters/answer/9205520)
- No CWV-related documentation changes appear in the Jan 2025–Oct 2026 Search Central changelog. — [Search Central updates](https://developers.google.com/search/updates)
- Google's AI features doc lists "provide a strong page experience" as a best practice for AI-feature eligibility. — [AI features doc](https://developers.google.com/search/docs/appearance/ai-features)

### Inferences
- Expert reading: work at template level (group example URLs map to templates such as PDP, PLP, article), weight by impressions/clicks from the Performance API per template path, and fix Poor groups on money templates first. Mobile usually matters most.
- Automation [external API]: CrUX API (`queryRecord` by origin/URL, formFactor PHONE/DESKTOP; prior knowledge: developer.chrome.com/docs/crux/api), CrUX History API for weekly trend (validates fixes faster than GSC's 28-day pass/fail), and PSI API v5 for lab + field per URL with Lighthouse diagnostics (developers.google.com/speed/docs/insights/v5/get-started). The GSC CWV report itself is [UI-only].
- Page experience report and Mobile usability report: (prior knowledge, not re-verified this session) Google retired the standalone Page Experience report in late 2023 and the Mobile Usability report / Mobile-Friendly Test in Dec 2023. The HTTPS report (Experience section) still lists non-HTTPS indexed URLs and reasons (e.g. HTTP URL indexed, invalid cert, HTTPS redirects to HTTP). It is [UI-only]; workaround: URL Inspection API + crawler.

### Gaps
- The HTTPS report help page was not fetched, so its exact issue list is unverified.
- The retirement dates of the Page experience / Mobile usability reports were not re-verified this session.

---

## 3. Links report

### Takeaway
A sampled, canonicalised link view: top linked pages (external), top linking sites, top linking text, and internal links. It is UI/export only (no API), capped at 1,000 rows on screen and 100k rows in the landing-page export. It is useful for internal-link audits and anchor sanity checks, and weak as a complete backlink source.

### Cited Findings
- Tables: Top linked pages (external), Top linking sites (root domain; protocol/subdomains/subdirs stripped, TLDs not), Top linking text (image links shown as "(empty)"), drill-down "Top linking pages" with target URL when redirected or canonicalised, and Internal links (most internally linked pages, with drill-down to linking pages). — [Search Console Help: Links report](https://support.google.com/webmasters/answer/9049606)
- Counting: grouped by canonical URL. Same source→target duplicates are merged. Anchor text matching is case-insensitive. **Nofollow status is not shown.** — [same](https://support.google.com/webmasters/answer/9049606)
- Limits: 1,000 rows on screen. The landing-page export allows up to **100,000 rows** in two slices ("Latest links" by discovery date, and "More sample links"). Single tables export 1,000 rows. It is a sample, may include links that no longer exist, and omits non-indexed pages. — [same](https://support.google.com/webmasters/answer/9049606)
- Disavow: for unknown or spammy sites, request removal or, "as a last resort", disavow. For known spam sites "Google typically ignores the links". — [same](https://support.google.com/webmasters/answer/9049606)
- The unnatural links manual action fix is a good-faith removal effort, disavow what can't be removed, and a reconsideration request with documentation. — [Manual actions report help](https://support.google.com/webmasters/answer/9044175)

### Inferences
- Internal linking audit [UI-only export, then join with API data]: export Internal links, join with Performance API page clicks/impressions and the sitemap URL list. Money pages with high impressions but low internal-link counts are under-linked. Sitemap URLs absent from the internal list are possible orphans; confirm with a crawler since the report is sampled.
- Link reclamation: "Latest links" + "More sample links" export → crawl target URLs → targets returning 404/410 are reclamation candidates (redirect or restore).
- Anchor spam: a top linking text list dominated by exact-match commercial anchors or foreign-language spam, especially newly discovered in "Latest links", is a negative-SEO or legacy-link-building signal. Default to ignoring it per Google's stance. Disavow only with a manual action or a clear paid-link history. Disavow tool (prior knowledge): support.google.com/webmasters/answer/2648487, URL-prefix properties only.
- No Links data in the Search Console API, so an agent needs browser export or third-party backlink APIs (Ahrefs/Semrush/Majestic) [external API].

### Gaps
- Links report refresh cadence is undocumented.

---

## 4. Enhancements / structured data reports and URL Inspection rich results

### Takeaway
The Enhancements section shows a per-type rich-result report (valid / invalid items, issues, validate fix) plus "Unparsable structured data". Google has aggressively removed types during 2025–2026, most notably **FAQ rich results (ended May 7, 2026; GSC report/filter removed June 2026; API support removed Aug 2026)**. The agent should treat the report list as dynamic.

### Cited Findings
- 2025 deprecations: Special announcement notice (Apr 23, 2025). Deprecation banners for book actions, course info, estimated salary, ClaimReview, learning video, special announcement, vehicle listing (Jun 12, 2025). Docs removed for course info, estimated salary, learning video, special announcement, vehicle listing (Sep 9, 2025). — [Search Central updates](https://developers.google.com/search/updates)
- Search Console stopped reporting on six deprecated types. For Bulk Data Export, deprecated Search appearance fields return NULL (from ~Oct 2025). Rankings are unaffected and the markup can stay. — [SEJ: Google drops Search Console reporting for six structured data types](https://www.searchenginejournal.com/google-drops-search-console-reporting-for-six-structured-data-types/555560/)
- Practice problem: deprecation notice Nov 5, 2025, GSC support discontinued from Jan 2026, docs removed Jan 6, 2026. Dataset markup is used only by Dataset Search, not Google Search. Book actions deprecation banner removed Nov 5, 2025 (i.e. kept). — [Search Central updates](https://developers.google.com/search/updates); [PPC Land](https://ppc.land/google-phases-out-practice-problem-and-dataset-structured-data/)
- **FAQ:** rich results stopped showing for all sites (including gov/health) on **May 7, 2026**. The deprecation notice was added May 8, 2026 and docs removed Jun 15, 2026. The FAQ search appearance filter, FAQ report and Rich Results Test support were slated for removal in June 2026, and Search Console API support in **August 2026**. The markup remains valid schema. — [Search Central updates](https://developers.google.com/search/updates); [Search Engine Roundtable](https://www.seroundtable.com/google-drops-faq-rich-results-41298.html); [SEJ](https://www.searchenginejournal.com/google-drops-faq-rich-results/574429/)
- Q&A page: properties were *added* (Mar 24, 2026), not deprecated. — [Search Central updates](https://developers.google.com/search/updates)
- Structured data issue is a manual action type (invisible, misleading or non-compliant markup). Fix the markup, then request review. — [Manual actions help](https://support.google.com/webmasters/answer/9044175)
- Google: structured data must match visible page text. No special schema is needed for AI features. — [AI features doc](https://developers.google.com/search/docs/appearance/ai-features); [SEJ: Google not diminishing structured data in 2026](https://www.searchenginejournal.com/google-is-not-diminishing-the-use-of-structured-data-in-2026/560516/)

### Inferences
- Reports likely still present as of Nov 2026 (prior knowledge, verify in the property): Breadcrumbs, Product snippets, Merchant listings, (Shopping) Review snippets, Videos, Events, Recipes, Organization? (the Organization report is uncertain), Profile page, Discussion forum, Q&A, Image metadata, Job postings, Logos, Sitelinks searchbox (removed Nov 2024 per the changelog mention), Unparsable structured data. HowTo rich results were dropped in Sept 2023 (prior knowledge).
- Fix playbook: open the issue → sample URLs → Rich Results Test (search.google.com/test/rich-results) [external/UI; no public API] and Schema Markup Validator (validator.schema.org) → fix the template → "Validate fix" (Google recrawls affected URLs; can take up to ~2 weeks+) [UI-only]. Per URL, URL Inspection API returns `richResultsResult` (detected types, items, issues) [API/MCP-automatable], so an agent can run its own validation sweep across template samples.
- Red flags: sudden drop in valid items, which usually means a template or JS rendering change or a CMS plugin update. Spikes in "Unparsable structured data" come from JSON-LD syntax errors. Merchant listing "missing field" warnings (shippingDetails, hasMerchantReturnPolicy) cap Shopping-tab eligibility.

### Gaps
- No authoritative list was retrieved of exactly which Enhancements reports exist in Nov 2026 (Organization, Profile page, Discussion forum reports not verified this session).

---

## 5. Video page indexing report

### Takeaway
Not researched in depth this session. Core facts below are prior knowledge.

### Cited Findings
- (None retrieved this session.)

### Inferences
- (Prior knowledge, not re-verified) The Video indexing report (Indexing → Video pages) shows pages where Google found a video and whether it was indexed. Common reasons: "Video isn't on a watch page", "Video outside the viewport", "Video too small", "Cannot determine video position/size", "Invalid thumbnail URL", "No video thumbnail". Validate fix is UI-only. Per-URL video indexing status is in the URL Inspection API response? (Uncertain; the API exposes `richResultsResult`, which may include Videos when VideoObject markup exists.) The fix playbook is a dedicated watch page with the video as the main content, above the fold, VideoObject markup with a crawlable thumbnail/contentUrl, and a video sitemap.

### Gaps
- Exact current issue names and API exposure were not verified. A follow-up should fetch the Video page indexing report help page.

---

## 6. Manual actions & Security issues

### Takeaway
Google's manual actions help page now lists 18 action categories, including the 2026-added **back button hijacking** and **site reputation abuse** (affected pages only, not applied in the EEA). Scaled content abuse falls under "Major spam problems". Reconsideration requests must fix all issues on all pages and document the work. The reports are [UI-only] (email alerts are the main automated signal).

### Cited Findings
- Types and fixes (Google): back button hijacking, site abused with third-party spam, user-generated spam, spammy free host, structured data issue, unnatural links to your site, unnatural links from your site, thin content with little/no added value (thin affiliate, scraped, doorway), **site reputation abuse** (move to a separate domain without redirects, noindex, rewrite as first-party or remove; moving to a subdomain/subdirectory "may not resolve"), "Major spam problems" (pure spam, scaled content abuse, cloaking, repeated violations), cloaking/sneaky redirects, cloaked images, hidden text/keyword stuffing, AMP content mismatch, sneaky mobile redirects, **News and Discover policy violations** (dangerous, deceptive practices, harassing, hateful, manipulated media, medical, misleading, sexually explicit, terrorist, transparency, violence/gore, vulgar language). — [Search Console Help: Manual actions report](https://support.google.com/webmasters/answer/9044175)
- Reconsideration: explain the exact issue, the fixes and documented results (link removal logs, examples of removed/added content). Fix all issues on all pages, and resolve all actions if there are several. Pages must be accessible (no login/paywall/robots/noindex). Reviews take "several days to a few weeks" (links longer). Don't resubmit while pending. For purchased sites, say you recently acquired it. — [same](https://support.google.com/webmasters/answer/9044175)
- Policy timeline: site reputation abuse clarified Jan 21, 2025. Back-button hijacking added Apr 13, 2026. Spam reports may be used for manual actions (Apr 14/23, 2026). Spam policies apply to gen-AI responses (May 15, 2026). Site reputation enforcement adjusted within the EEA (Aug 28, 2026). UGC spam guide updated with Search Console abuse monitoring (Oct 26, 2026). — [Search Central updates](https://developers.google.com/search/updates)
- Site reputation abuse/expired domain/scaled content policies date from March 2024. Manual actions for site reputation abuse began May 6, 2024. The March 2025 documentation expansion says redirecting old to new may reintroduce the issue. — [Search Engine Roundtable](https://www.seroundtable.com/google-expands-site-reputation-abuse-policy-manual-actions-steps-39027.html)
- Glenn Gabe argues for algorithmic over manual enforcement of site reputation abuse. — [GSQI](https://www.gsqi.com/marketing-blog/google-site-reputation-abuse-spam-policy-algorithmic-approach/)
- If no manual action is shown, the drop is algorithmic and a reconsideration request does nothing. — [summary of practitioner sources incl. SEO Juice](https://seojuice.com/blog/how-to-recover-from-google-penalty/)
- Security issues are one of Google's listed traffic-drop causes (malware/phishing warnings reduce clicks). Check the Security Issues report. — [Google: Debugging search traffic drops](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)

### Inferences
- Expired domain abuse has no standalone manual-action entry. It is enforced under "Major spam problems"/scaled content or algorithmically.
- Security issues (prior knowledge): hacked content (code injection, content injection, URL injection), malware/unwanted software, social engineering (deceptive pages), harmful downloads, uncommon downloads. Fix, then "Request review". [UI-only]; workaround: Safe Browsing / Web Risk API status checks [external API] and alerts from GSC email.

### Gaps
- Typical review turnaround numbers are anecdotal (one blog claims 2–6 weeks).

---

## 7. Discover and Google News reports

### Takeaway
Discover has its own Performance report (impressions, clicks, CTR, 16 months, threshold-gated, includes Chrome) plus, since June 2026, a Discover generative-AI impressions report. February 2026 saw the first Discover-only core update.

### Cited Findings
- Eligibility: indexed + compliant with Discover content policies, no special tags. Recommendations: images ≥1200px wide, >300k pixels, 16:9, `max-image-preview:large`, preferred image via schema or og:image (no logos/text-heavy images), titles that capture the content, timely/unique content. Avoid clickbait and sensationalism. Report covers 16 months above a minimum impression threshold and includes Chrome traffic. Discover policy violations appear as manual actions. Traffic is volatile; "treat as supplement". Page last updated 2026-03-09. — [Google: Discover](https://developers.google.com/search/docs/appearance/google-discover)
- Follow-feature guidance removed Nov 19, 2025. Guidance expanded for the **February 2026 Discover Core Update** (Feb 5, 2026). Preferred image best practices added Mar 2, 2026. — [Search Central updates](https://developers.google.com/search/updates); [Google blog: Feb 2026 Discover core update](https://developers.google.com/search/blog/2026/02/discover-core-update)
- The Feb 2026 Discover core update started Feb 5 and completed ~Feb 27, 2026 (sources conflict; one says Feb 19). Barry Schwartz noted it was the first core update isolated to Discover. — [SEJ](https://www.searchenginejournal.com/google-releases-discover-focused-core-update/566647); [TripleDart tracker](https://www.tripledart.com/google-algorithm-update-tracker/february-2026-discover-core-update)
- Discover generative-AI impressions report (Jun 2026). — [Help 16983858](https://support.google.com/webmasters/answer/16983858)

### Inferences
- Discover and Google News data are available in the Search Analytics API via `type=discover` and `type=googleNews` (prior knowledge: these data types exist in the API; Discover data has no query dimension). [API/MCP-automatable]. The gen-AI Discover report is [UI-only].
- Reading: track page-level clicks per publish date; Discover lifespans are short (24–72h). Compare Discover vs. Search clicks by page to separate a Discover update from a core update.

### Gaps
- No Barry Adams primary source was retrieved this session. The Google News report specifics (news.google.com app/web traffic) were not re-verified.

---

## 8. Search appearance dimension and Shopping/merchant reports

### Takeaway
Search appearance is a dimension that is volatile with Google's deprecations. Deprecated appearance fields go NULL in bulk export, and FAQ was removed in 2026.

### Cited Findings
- Deprecated Search appearance fields return NULL in Bulk Data Export, and Search Console stopped reporting six deprecated types (2025). — [SEJ](https://www.searchenginejournal.com/google-drops-search-console-reporting-for-six-structured-data-types/555560/)
- The FAQ search appearance filter was removed (June 2026). — [Search Engine Roundtable](https://www.seroundtable.com/google-drops-faq-rich-results-41298.html)
- Google tells sites to keep Merchant Center and Business Profile information current for AI features. — [AI features doc](https://developers.google.com/search/docs/appearance/ai-features)
- One guide claims the Performance report has Search Appearance filters for AI Mode and AIO. — [apiserpent](https://apiserpent.com/blog/great-decoupling-measure-ai-overview-traffic-loss). **Contradicted** by Google's help, which says AIO/AI Mode are folded into Web and gets a separate gen-AI report. — [Google help 16984139](https://support.google.com/webmasters/answer/16984139). Treat the claim as false or unverified.

### Inferences
- Search appearance is available in the API (`searchAppearance` dimension, which cannot be combined with other dimensions in the same request; prior knowledge) [API/MCP-automatable]. Typical values include product snippets, merchant listings, review snippet, video, rich results, AMP, translated results, etc.
- Shopping (prior knowledge): Merchant listings and Product snippets reports, Shopping tab listings, and the Merchant Center association that powers the "Shopping" section in GSC. Free-listing performance is not in GSC Performance; see Merchant Center. [UI-only] for Shopping reports.

### Gaps
- The current list of searchAppearance values and the state of the GSC "Shopping" section were not verified this session.

---

## 9. Settings & ops

### Takeaway
The key ops levers: domain property plus extra URL-prefix/subfolder properties (more row headroom), BigQuery bulk export (owner-only, daily, no 1k/50k row caps, anonymized queries not text-exposed), Looker Studio, and 2025–2026 additions (custom annotations, branded-queries filter, query groups, AI-powered configuration).

### Cited Findings
- **Bulk data export** (Feb 2023): daily dump to the user's BigQuery project, set up by property owners only. Exports all performance data except anonymized query text. Later expanded to let multiple properties export to one Cloud project. — [Search Central blog: Bulk data export](https://developers.google.com/search/blog/2023/02/bulk-data-export); [Help 12918484](https://support.google.com/webmasters/answer/12918484)
- Anonymized queries are those not issued by more than a few dozen users over 2–3 months. Search Console also stores only "top data rows", so not all non-anonymized queries are shown either. — [Search Engine Roundtable](https://www.seroundtable.com/google-search-console-anonymizes-tons-of-queries-33735.html); Advanced Web Ranking shows BigQuery exposes metrics for anonymized rows (query NULL) — [AWR](https://www.advancedwebranking.com/blog/access-more-anonymized-google-search-console-data)
- **Custom annotations** (Nov 2025): up to 200 per property, deletable not editable, visible to all users. **Branded queries filter** (AI-assisted brand/non-brand split; domain properties only; broad rollout Mar–Apr 2026, dates conflict; accuracy mixed, with competitor names misclassified). **Query groups** (Oct or Dec 2025, conflicting). **AI-powered configuration** (natural-language Performance-report setup; GA status unverified). — [Stan Ventures](https://www.stanventures.com/news/google-search-console-to-get-ai-branded-query-filter-5869/); [The Keyword](https://www.thekeyword.co/news/google-search-console-branded-queries-filter); [Search Engine Land GSC guide](https://searchengineland.com/google-search-console-seo-guide-443942)
- Search generative AI control lives under Settings (property-level). — [SEJ](https://www.searchenginejournal.com/google-search-console-ai-reports-rolled-out-worldwide/587836/)
- The UGC spam guide (Oct 26, 2026) adds monitoring abuse via Search Console. — [Search Central updates](https://developers.google.com/search/updates)

### Inferences
- Subfolder-property trick (prior knowledge; widely used by Glenn Gabe and others, not re-verified this session): the UI shows 1k rows and the API returns up to 50k rows/day per property per search type. Adding URL-prefix properties for key subfolders (/blog/, /products/, country folders) gives each its own row budget, increasing surfaced long-tail queries. Bulk export removes the per-request cap but not anonymization.
- BigQuery SQL use cases [API/MCP-automatable]: tables `searchdata_site_impression` (property-aggregated) and `searchdata_url_impression` (URL-level, with boolean search-appearance columns such as `is_amp_*`, `is_product_snippets`, `is_merchant_listings`, `is_video`, etc.; prior knowledge). Typical queries: anonymized share = SUM(impressions WHERE is_anonymized_query)/SUM(impressions); brand vs non-brand regex; long-query (AI-style) regex counts over time; page × query cannibalisation (≥2 URLs with impressions for the same query); decoupling trend (impressions vs clicks weekly); CTR by position bucket. Note `sum_top_position` is zero-based, so avg position = sum_top_position/impressions + 1.
- Users/permissions hygiene [UI-only; Sites API only lists/adds sites]: quarterly review of Owners (verified vs delegated), removal of departed staff and agencies, unused verification tokens (DNS/HTML file) cleanup, since a lingering verification token re-grants ownership.
- Property types: Domain property (DNS verification, all protocols and subdomains) is the default. Add URL-prefix properties for disavow (URL-prefix only), subfolder data and team scoping.
- Change of Address [UI-only] (prior knowledge: support.google.com/webmasters/answer/9370220): domain-level moves only, requires 301s from the old homepage, both properties verified by the same owner, and stays effective for 180 days.
- Associations: GA4 (Search Console linking in GA4 admin; enables Search Console reports in GA4), Merchant Center (Shopping section). Email alerts for new manual actions, security issues, indexing spikes and validation results. These are the only "push" triggers; an agent should parse them from the inbox if available.
- Search Console Insights (merged into the main GSC UI in 2025 per prior knowledge; not verified), recommendations (2024), and Achievements (2025) are [UI-only] and low-value for experts.

### Gaps
- Exact current API row limits and whether Search Console Insights / Recommendations / Achievements still exist in Nov 2026 were not verified this session.
- No primary Glenn Gabe source on the subfolder-property trick was retrieved.

---

## 10. Site migrations & traffic-drop diagnosis

### Takeaway
Google's traffic-drop guide (updated 2025-12-10) gives the canonical sequence: impressions vs clicks → 16-month view → period and YoY comparisons across all tabs → search type → position → Pages sorted by Clicks Difference → Google Trends → wait weeks. Causes are algorithmic updates, technical, security, spam/manual, seasonality, site moves, and reporting glitches (Data anomalies page).

### Cited Findings
- Causes: algorithmic/core updates (check the ranking-updates list), technical issues (server, robots.txt fetch, 404s, stray noindex; check Crawl stats and Page indexing), security issues, spam/manual actions, seasonality and interest shifts, site moves ("medium sites a few weeks, larger longer"), reporting glitches (Data Anomalies page). — [Google: Debugging drops in Google Search traffic](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
- Steps: if both impressions and clicks dropped, check causes. If only clicks dropped, review titles/snippets and competitor rich results. Use Last 16 months. Compare last 3 months vs previous and YoY across queries/pages/countries/devices/search appearance. Filter search type (Web/Image/Video/News). Use average position as secondary. Sort Pages by Clicks Difference. Page indexing for site-wide drops, URL Inspection for single pages. Google Trends on top queries. Wait a few weeks after changes. — [same](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
- February 2026 Discover-only core update: separate the Discover report from Search when diagnosing. — [SEJ](https://www.searchenginejournal.com/google-releases-discover-focused-core-update/566647)
- AI Overviews decouple impressions from clicks (clicks-only drop pattern). — [Ahrefs](https://ahrefs.com/blog/the-great-decoupling)

### Inferences
- Agent decision tree [mostly API/MCP-automatable]: (1) Pull 16-month daily clicks and impressions. (2) Classify the shape: step-change both metrics on a date matching an update → algorithmic; clicks-only decline with impressions flat/up → SERP feature/AIO (check long-query regex share and position ~1 anomalies); gradual decline matching Trends → demand; drop confined to a directory/template → technical (URL Inspection API sample + Page indexing UI). (3) Check manual actions/security [UI-only, email alerts]. (4) Check the Data Anomalies page. (5) Annotate in GSC custom annotations [UI-only].
- Migration playbook (prior knowledge; Google site-move doc developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes): pre-move benchmark export (API/BigQuery), 1:1 301 map, verify both properties, submit new sitemaps (+ keep old sitemap temporarily to speed discovery of redirects), Change of Address tool for domain moves, then monitor via API: old-property clicks ↓ mirrored by new-property clicks ↑, Page indexing "Page with redirect" growth on old, crawl-stats spike, and the URL Inspection API on the top 500 URLs for canonical = new URL.

### Gaps
- Glenn Gabe / Marie Haynes / Lily Ray core-update diagnosis methods were not retrieved as primary sources this session.
