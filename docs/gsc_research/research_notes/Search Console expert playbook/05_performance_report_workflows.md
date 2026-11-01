# Search Console Performance Report Workflows: an Automation Catalogue (as of Nov 2026)

Scope: how results-driven SEOs use the GSC Performance report and the Search Analytics API to find and act on ranking, CTR and content opportunities, written so an AI agent with a GSC MCP/API can run each workflow and pass rewrites to a content pipeline.

Conventions used below:
- **[API/MCP]** means the workflow can be fully automated with `searchanalytics.query`. **[UI-only]** means it depends on a UI-only feature (Insights cards, the annotations display, the branded toggle where no API field is documented, etc.).
- "Source-stated" thresholds are attributed. Where a threshold is my own synthesis for automation, it is marked *(synth)*. These are starting defaults to tune, not published rules.
- Research budget note: several practitioner pages (Search Engine Land, aleydasolis.com) returned HTTP 403, and Google blog pages returned only navigation. Some attributions therefore rest on search-result summaries and are marked *(summary-level)*.

---

## Q1. Data model, API parameters and caveats an agent must respect

### Takeaway
The API is the right engine: it allows up to 25,000 rows per request with paging, RE2 regex include/exclude on any dimension, an `hour` dimension, fresh or hourly data via `dataState`, and search types web/image/video/news/discover/googleNews. It has three big traps. Filter groups are AND-only, so you build OR logic inside a single regex. Property-level and page-level aggregation give different totals and positions. About 46–47% of clicks belong to anonymised queries that never appear as query rows.

### Cited Findings
- **API request body** (`searchanalytics.query`): `dimensions[]` can be country, device, page, query, searchAppearance, date and **hour**. You can't group by the same dimension twice, and results are grouped in the order listed. `type` is one of `web` (default), `discover`, `googleNews`, `news`, `image` or `video`. `googleNews` excludes the News tab in Google Search. — [Google Search Analytics API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- **Filters**: in `dimensionFilterGroups[]`, `groupType` supports **only "and"** ("or" is not yet supported). Operators are `equals`, `contains`, `notContains`, `notEquals`, `includingRegex` and `excludingRegex`. **Regex is RE2 syntax**. The expression can be **at most 4096 characters**. Country takes ISO 3166-1 alpha-3 codes and device takes DESKTOP/MOBILE/TABLET. — [API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- **aggregationType** is `auto`, `byPage`, `byProperty` or `byNewsShowcasePanel`. `byProperty` is not supported for discover/googleNews. If you group or filter by page, you can't aggregate by property. — [API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- **Paging**: `rowLimit` runs from 1 to 25,000 (default 1,000) and `startRow` is a zero-based offset. The API "does not guarantee all rows", returning top rows subject to internal limits. — [API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- **dataState**: `final` is the default (finalised data only). `all` includes fresh data. `hourly_all` includes the hourly breakdown with partial data and should be used when grouping by hour. — [API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- **Hourly data**: the API returns up to **10 days** of hourly breakdown through the HOUR dimension and HOURLY_ALL dataState, launched around **9 April 2025**. Google had first promised 8 days. The UI's 24-hour view is the only hourly view in the product. — [Search Engine Land](https://searchengineland.com/google-search-analytics-api-gains-hourly-break-down-for-past-10-days-454167); [SEL pre-announcement](https://searchengineland.com/google-search-console-api-gains-24-hour-hourly-data-for-past-8-days-coming-soon-453475); [PPC Land](https://ppc.land/google-adds-hourly-data-support-to-search-analytics-api/)
- **Average position** is "the average position of the topmost result from your site". In the chart it is site-wide; in the table it is per row. — [GSC Help: Performance report](https://support.google.com/webmasters/answer/7576553?hl=en)
- **Aggregation mismatch**: the chart aggregates by property, so two results from one site for one query count as one impression. In the table, Queries, Countries, Devices and Dates aggregate by property, while **Pages and Search appearance aggregate by page**. Chart and table totals can therefore disagree. — [GSC Help](https://support.google.com/webmasters/answer/7576553?hl=en)
- **Fresh data and UI quirks**: the newest data may be preliminary (shown as a dotted line). Hourly granularity exists only in the 24-hour view. The default view is 3 months. "~" or "-" values export as zeros. The **Web: multimodal** search type covers Lens, Circle to Search and image uploads. — [GSC Help](https://support.google.com/webmasters/answer/7576553?hl=en)
- **Anonymised queries**: Ahrefs found **46.08% of clicks** went to anonymised queries across 146,741 sites (2022). An update across 887,534 properties and 22B clicks found **46.77% in April 2025**. Some sites lose more than 90%. Anonymised queries are those not issued by more than a few dozen users over 2–3 months. — [Ahrefs: Anonymized queries](https://ahrefs.com/blog/gsc-anonymized-queries/); [Ahrefs hidden-terms study](https://ahrefs.com/blog/gsc-hidden-terms-study); Google removed "very rare" wording from its help doc afterwards — [Search Engine Land](https://searchengineland.com/google-removes-language-in-help-doc-calling-hidden-search-console-query-data-very-rare-386328)
- **Query+page rows drop data**: totals from a query+page export are smaller than page-only totals. For page totals, pull a page-only dataset. When filtering striking distance on API output, aggregate first and filter on impression-weighted position (a HAVING-style filter) rather than on individual rows. *(summary-level)* — [SEOTesting (Nick Swan): striking distance via GSC API](https://seotesting.com/blog/striking-distance-keywords-gsc-api/); [ContextBolt](https://contextbolt.com/blog/striking-distance-keywords-with-claude/)
- **Discover retention**: the Discover report appears only once a minimum impression threshold is reached. Data is kept for 16 months, so export regularly to keep YoY comparisons. — [TripleDart](https://tripledart.com/marketing-tutorials/how-to-check-your-google-discover-traffic-in-google-search-console)

### Inferences
- **The 1,000-row UI limit**: the UI tables display and export at most 1,000 rows (standard practitioner knowledge, consistent with the API's default rowLimit of 1,000). Every workflow below should run via the API with `rowLimit=25000` and `startRow` paging, or via BigQuery bulk export, never via UI export.
- **OR logic must live inside one regex**, because groups are AND-only. Use for example `includingRegex: "who|what|why|how"` rather than four filters. Negation of a set uses `excludingRegex`.
- **Position rule for the agent**: compute an **impression-weighted average position** when rolling up rows, `sum(position*impressions)/sum(impressions)`. Never use a simple mean of row positions. Use `byPage` for page-level work and `byProperty` (query dimension only) for site-level query work.
- Use `dataState=all` for monitoring the last 2–3 days and `final` for any before/after measurement, so partial data doesn't bias the "after" window.
- Anonymised-query gap metric *(synth)*: `gap = page_total_clicks(page-only query) - sum(clicks over query rows for that page)`. Pages with a gap above 60% are long-tail heavy. Optimise them for topic coverage rather than individual keywords.

### Gaps
- I couldn't fetch a Google page stating the UI 1,000-row limit or the UI regex length limit verbatim. The API's 4096-character limit is confirmed.
- I couldn't confirm whether the 2025 branded filter and query groups are exposed in the Search Analytics API. No API field for them appears in the API reference fetched, so treat them as [UI-only] until verified.
- I couldn't retrieve the BigQuery bulk export documentation in this session. Practitioners widely recommend it to escape row sampling and keep history beyond 16 months, but this isn't re-verified here.

---

## Q2. Regex library (RE2-safe) for GSC/API

### Takeaway
GSC regex is RE2. It has **no lookahead/lookbehind and no backreferences**, so "does not contain X" is done with `excludingRegex` or the UI's "Doesn't match regex" (added June 2021). Matching is case-sensitive unless you prefix `(?i)`. Query data is lowercase anyway, so write patterns in lowercase. Use `\b` boundaries and anchors deliberately, because over-anchoring with `$` often returns nothing.

### Cited Findings
- Google added the **negative-match regex** option and published beginner tips in June 2021, pointing to the RE2 syntax reference. — [Google Search Central blog: regex filters update and quick tips (June 2021)](https://developers.google.com/search/blog/2021/06/regex-negative-match); RE2 syntax: [github.com/google/re2/wiki/Syntax](https://github.com/google/re2/wiki/Syntax)
- Regex filtering and comparison in Performance reports launched in April 2021. — [Google Search Central blog: better data filtering and comparison (April 2021)](https://developers.google.com/search/blog/2021/04/performance-report-data-filtering)
- The question pattern `^(who|what|when|where|why|how)\b`, extendable with is/can/should. Use the same pattern with "Doesn't match" for exclusions such as non-brand. Query data is lowercase. Anchoring with `$` too tightly returns nothing. Four or more words: `\S+(\s+\S+){3,}`. — [SEOcrawl: GSC regex](https://seocrawl.ai/blog/google-search-console-regex)
- Single-word queries: `^\b\w+\b` (Rank Math lists it as one-word; anchor with `$` to make it strict). Two to three words: `^\b\w+(?:\s+\w+){1,2}\b`. Rank Math's char-count example is internally inconsistent, so test before use. — [Rank Math KB](https://rankmath.com/kb/regex-in-google-search-console/)
- Ends-with and starts-with examples: `seo$` and `^buy`. — [Sitechecker](https://sitechecker.pro/google-search-console/regex-in-google-search-console/)
- **AI-Mode / conversational prompts**: filter Query > Custom (regex) with `([^" "]*\s){10,}?` to surface queries of 10+ words that look like LLM-style prompts (2026). — [Practical Ecommerce: Filter AI Mode prompts in Search Console](https://www.practicalecommerce.com/filter-ai-mode-prompts-in-search-console). A Nectiv-attributed regex pulling 10+ word "conversational" queries is referenced on LinkedIn *(attribution to Chris Long unconfirmed)* — [LinkedIn mention](https://bd.linkedin.com/in/rexaul)
- Brand-misspelling regex examples, and using regex101 to test patterns. — [Getbutterfly](https://getbutterfly.com/regular-expressions-regex-in-google-search-console/)
- Local SEO uses of GSC regex ("near me", city modifiers). — [BrightLocal: advanced GSC for local](https://www.brightlocal.com/learn/advanced-google-search-console-local/)

### Inferences: the library *(synth; all RE2-valid; prefix `(?i)` if unsure of case)*

| Class | Pattern (query dimension unless noted) | Notes |
|---|---|---|
| Questions (start) | `^(who\|what\|when\|where\|why\|how\|which\|whose\|whom\|is\|are\|can\|could\|should\|would\|will\|do\|does\|did\|was\|were)\b` | Start-anchored = true question intent |
| Questions (anywhere) | `\b(who\|what\|when\|where\|why\|how\|which)\b` | Catches "best way how to …", noisier |
| Question-ish non-wh | `\b(guide\|tutorial\|tips\|ideas\|examples\|meaning\|definition\|explained\|steps)\b` | Informational modifiers |
| Long-tail 6+ words | `^(\S+\s){5,}\S+$` | 6+ words |
| Long-tail 4+ words | `^\S+(\s+\S+){3,}$` | |
| Conversational 10+ | `^(\S+\s){9,}\S+$` | Equivalent to Practical Ecommerce's 10+ |
| Short head 1–2 words | `^\S+(\s\S+)?$` | |
| Comparisons | `\b(vs\|versus\|or\|compared?\|comparison\|alternatives?\|competitors?\|like)\b` | "or"/"like" are noisy, so drop them for precision |
| Commercial | `\b(best\|top\|review(s)?\|rated\|cheap(est)?\|affordable\|price(s\|d)?\|pricing\|cost(s)?\|deal(s)?\|discount\|coupon\|buy\|for sale\|hire\|quote)\b` | |
| Transactional/service | `\b(near me\|nearby\|services?\|company\|agency\|consultant\|contractor\|book(ing)?\|appointment)\b` | |
| Local | `\b(near me\|nearby\|in [a-z]+\|open now)\b` or `\b(london\|manchester\|leeds)\b` | Fill city list |
| Year modifiers | `\b20(2[4-9]\|3[0-9])\b` | Freshness intent. Update yearly titles |
| Problem/fix | `\b(error\|not working\|fix\|issue\|problem\|broken\|won't\|can't)\b` | Troubleshooting content |
| Brand (example) | `(?i)\b(asdi\|asdivigital(s)?\|asdi digital)\b` | Add misspellings. Run as includingRegex vs excludingRegex for brand/non-brand |
| URL folder (page dim) | `^https://example\.com/blog/` ; `/(services\|locations)/` | Escape dots. Topic clusters per folder |
| URL with parameters | `\?` or `[?&](utm_\|gclid\|sort\|filter)=` | Parameter leakage into Search |
| URL depth | `^https://[^/]+(/[^/]+){3,}/?$` | Deep pages |
| Exact multi-page check | `^keyword phrase$` | Cannibalisation drill-down |

- **RE2 limits to tell the agent**: no `(?!…)`, `(?<=…)` or `\1`. Possessive quantifiers aren't supported. Make "contains A but not B" by using two filters in the same AND group (`includingRegex A` + `excludingRegex B`), which works because groups AND together.

### Gaps
- I couldn't fetch the Google June 2021 post body to quote its exact example patterns, such as the `(?i)` tip, so the (?i) recommendation rests on RE2 docs and general practitioner use.
- I couldn't verify a Chris Long (Nectiv) original post URL for his regex or GSC tips.

---

## Q3. Opportunity workflows: striking distance, CTR, question/long-tail mining, new keywords

### Takeaway
The core repeatable loops are these. Pull query×page rows with the API (90 days, `final`), aggregate with impression-weighted position, then bucket: **positions 4/8–20** become content/on-page upgrades, and **positions 1–5 with CTR well below the site's own CTR curve** become title/meta rewrites. Since 2025 the CTR curve has to be segmented by whether a query triggers AI Overviews, because Ahrefs measured top-position CTR **58% lower** on AIO keywords (Dec 2025).

### Cited Findings
- **Striking-distance band definitions vary.** Most use 8–20 ("below 8 is often already earning; above 20 rarely moves with a single edit"). Others use 11–20 or 5–20, and one GSC MCP tool defaults to 8–25. — [ContextBolt](https://contextbolt.com/blog/striking-distance-keywords-with-claude/); [Clearscope](https://www.clearscope.io/blog/what-are-striking-distance-keywords); [gsc-mcp `gsc_striking_distance` tool](https://glama.ai/mcp/servers/conorbronsdon/gsc-mcp/tools/gsc_striking_distance); [SEOTesting (Nick Swan)](https://seotesting.com/blog/striking-distance-keywords-gsc-api/)
- **AI Overviews and CTR**: Ahrefs (300k keywords, 150k with AIO vs 150k informational without) found an AIO correlates with **58% lower CTR for position 1**. Position-1 CTR on AIO keywords went from 0.073 (Dec 2023) to **0.016 (Dec 2025)**. The earlier 2025 study found **34.5%** lower (0.073 → 0.026, Mar 2024 to Mar 2025). — [Ahrefs: AI Overviews reduce clicks by 58%](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update/); [eMarketer on 34.5%](https://www.emarketer.com/content/google-ai-overviews-decrease-ctrs-by-34-5-per-new-study). Seer Interactive reported organic CTR declines of roughly 49–65% on AIO queries *(secondary, unverified)* — [PPC Land](https://ppc.land/googles-ai-summaries-now-swallow-58-of-clicks-that-once-went-to-websites/); Amsive found −15.49% average across 700k keywords *(secondary)* — [Search Engine Land](https://searchengineland.com/google-ai-overviews-hurt-click-through-rates-454428)
- **CTR curves**: Advanced Web Ranking publishes a monthly CTR curve for the top 20 results, split by desktop/mobile and by SERP-feature combination. Its Q4 2025 changes report exists. — [AWR CTR study](https://www.advancedwebranking.com/ctrstudy/); [AWR Q4 2025](https://www.advancedwebranking.com/blog/ctr-google-2025-q4). Third-party 2025 figures put position 1 at roughly 28–40% without AIO and roughly 11–19% with AIO *(secondary, variable)* — [We Are TG](https://wearetg.com/?p=9426). Building a **site-specific CTR curve from your own GSC data** is the recommended method — [Botify: how to calculate SEO CTR curves](https://botify.com/blog/how-to-calculate-seo-ctr-or-organic-click-through-rate-curves)
- **Google's own rule**: if impressions held steady but clicks fell, review titles and snippets ("users don't understand the content of your page", or another site has a more appealing rich result). — [Google: Debugging drops in Search traffic](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
- Question and long-tail regexes (see Q2) are used to find FAQ/blog ideas. — [SEOcrawl](https://seocrawl.ai/blog/google-search-console-regex); conversational prompts — [Practical Ecommerce](https://www.practicalecommerce.com/filter-ai-mode-prompts-in-search-console)

### Inferences: workflow catalogue *(thresholds synth unless attributed)*

**W1. Page-level striking distance and query-to-H2 mapping (formalises the user's workflow 1)** [API/MCP]
- Goal: move pages ranking 4–20 or 0–30 into the top 3.
- Pull A: `dimensions=[page]`, last 90 days, `aggregationType=byPage`, `type=web`, `dataState=final`, rowLimit 25000. Keep pages with position 4–20 (or 0–30 as the user does) and at least 500 impressions/90d (scale to site size).
- Pull B per page: `dimensions=[query]`, filter `page equals <url>`. Classify queries as: **ranking** (position ≤ 20 and impressions ≥ 20), **should-rank** (impressions ≥ 20 and position 20–50, or semantically related queries from other pages), and **question queries** (Q2 regex).
- Decision: a page qualifies if the sum of impressions on queries at positions 4–20 is at least X, and its top-5 queries aren't already in title/H1/H2 (check with an on-page crawl).
- Action: hand the content pipeline the query list grouped into H2 topics, an exact-match SERP check per head query in the target country (`country` filter + geo-localised SERP fetch), and a competitor gap list (content sections, author/E-E-A-T signals, internal/external links, schema). Then add an annotation and start W15 measurement.
- Source basis: user's own practice. Band rationale from [ContextBolt](https://contextbolt.com/blog/striking-distance-keywords-with-claude/) and [SEOTesting](https://seotesting.com/blog/striking-distance-keywords-gsc-api/).

**W2. Query-level striking distance (quick wins)** [API/MCP]
- `dimensions=[query,page]`, 90 days. Aggregate per query (weighted position), keep 8–20 (or 11–20 for page-2 only), impressions ≥ 100/90d, and exclude brand (excludingRegex).
- Decision: one dominant page (≥ 80% of the query's impressions) means on-page optimisation. Multiple pages means route to W6 (cannibalisation).
- Action: add or strengthen an H2 or section, put the query in title/H1 if it's the primary, add 2–5 internal links from relevant high-authority pages using the query as anchor-variant.
- Source: [SEOTesting (Nick Swan)](https://seotesting.com/blog/striking-distance-keywords-gsc-api/); [Clearscope](https://www.clearscope.io/blog/what-are-striking-distance-keywords).

**W3. Low-CTR / high-impression title and meta rewrite (expected-CTR gap)** [API/MCP]
- Build the site curve: `dimensions=[query]`, 90 days, non-brand only, device-split. Per rounded position bucket (1, 2, …, 10), compute the impression-weighted median CTR.
- Decision: candidate if position ≤ 10, impressions ≥ 1,000/90d, and `actual CTR < 0.6 × expected CTR(bucket, device)`. Rank by `missed clicks = impressions × (expected − actual)`.
- AIO adjustment (2025–26): flag queries known to trigger AIO (external SERP check). For those, compare to an AIO-specific curve, or treat low CTR as structural. Ahrefs shows position-1 CTR around 1.6% on AIO keywords, so don't rewrite a title expecting a 28% CTR.
- Also check the SERP for a competitor rich result, as Google advises.
- Action: the pipeline rewrites the title (primary query front-loaded, specific benefit or number, year if Q2 year-regex queries show freshness intent) and meta description. Measure with W15 (28 days before vs after, same weekdays).
- Sources: [Botify CTR curves](https://botify.com/blog/how-to-calculate-seo-ctr-or-organic-click-through-rate-curves); [AWR](https://www.advancedwebranking.com/ctrstudy/); [Ahrefs AIO](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update/); [Google debugging guide](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops).

**W4. Zero-click / high-impression queries** [API/MCP]
- Queries with impressions ≥ 1,000, clicks ≤ 5 and position ≤ 5.
- Decision: if the query is definitional or quick-answer, or triggers AIO, accept it as zero-click. Target AIO citation instead (concise answer block, clear definitions) and track impressions as the KPI. If it's commercial, treat it as W3.
- Source basis: the Ahrefs AIO data above. Thresholds *(synth)*.

**W5. Question-query mining (formalises the user's workflow 2)** [API/MCP]
- `dimensions=[query,page]`, `includingRegex ^(who|what|why|how|when|where|which|is|are|can|does|do|should)\b`, 3–6 months.
- Decision: a question with an existing ranking page at position 5–30 is a **content-update** candidate (add an H2 with the exact question plus a 40–60 word direct answer). A question with no page, or whose page is off-topic (see W7), is a **new FAQ/blog** candidate. Group questions sharing nouns into one article.
- Source: [SEOcrawl](https://seocrawl.ai/blog/google-search-console-regex); user's practice.

**W6. Long-tail and conversational mining** [API/MCP]
- `includingRegex ^(\S+\s){5,}\S+$` (6+ words) and `^(\S+\s){9,}\S+$` (10+ words, AI-Mode-style prompts).
- Action: cluster by shared entities, map clusters to existing pages as new H2/H3 sections, and write net-new pages only for clusters with no host page.
- Source: [Practical Ecommerce](https://www.practicalecommerce.com/filter-ai-mode-prompts-in-search-console).

**W7. New keyword discovery ("queries you rank for but never targeted")** [API/MCP]
- Pull all queries with impressions ≥ 50/90d. Compare against the target-keyword list from the site's briefs, titles and H1s (crawl).
- Decision: an untargeted query with meaningful impressions and position ≤ 30 goes to existing-page expansion. Untargeted queries that are intent-distinct from the ranking page (see W8) get a new page.
- Also compare the first-seen date: queries with zero impressions in the prior 90 days but impressions now are **emerging queries** (YoY or period diff).

**W8. Query–page mismatch** [API/MCP]
- `dimensions=[query,page]`. A query's top page is semantically or intent-distant from the query, for example a commercial query landing on a blog post, a question landing on a category page, or a homepage ranking for deep topics.
- Decision: if the query's intent class (Q2 regex: commercial or question) differs from the page type (URL folder regex), redirect internal links and anchors toward the correct page, strengthen that page, and de-optimise the wrong one.

### Gaps
- I found no authoritative published "expected CTR multiplier" threshold (such as 0.5 or 0.6 of expected). It's a practitioner convention, so tune it per site.
- I couldn't extract AWR's exact 2025/2026 position-by-position numbers, because the page tables didn't render in fetch.

---

## Q4. Decay, traffic drops, algorithm updates, seasonality, intent shifts

### Takeaway
Google's own drop-analysis method is the backbone. Use the last 16 months to spot seasonality. Compare the last 3 months to the previous period and YoY. Click every dimension tab, split by search type, and sort Pages by **Clicks Difference**. Then classify the drop as site-wide, section or single page, and as algorithmic, technical, spam/security, seasonal or site-move. Practitioners such as Glenn Gabe run "delta reports" (before/after an update, by query and page) and segment by query class and folder (Aleyda Solis's segmented Looker Studio template).

### Cited Findings
- Google workflow: (1) both impressions and clicks fell means investigate causes, while steady impressions with fewer clicks means fix titles/snippets; (2) use the **Last 16 months** to check whether the drop recurs yearly; (3) "Compare last 3 months to previous period" or "year over year"; (4) click every tab (queries, pages, countries, devices, search appearance); (5) filter by search type; (6) position isn't the main success measure, but self-assess if there's "a dramatic, persistent drop in position"; (7) sort the Pages table by **Clicks Difference**; (8) site-wide means the Page indexing report, a page group means URL Inspection; (9) for algorithm updates, a small position drop needs no fix and a large drop calls for whole-site self-assessment. Check Crawl stats, Security, Manual actions, Google Trends for seasonality, and site moves. Wait "a few weeks" after changes before re-analysing. — [Google Search Central: Debugging drops in Google Search traffic](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)
- Google's guidance video on interpreting traffic across Search, Discover and News was published on **4 Dec 2024** by Daniel Waisberg. — [PPC Land summary](https://ppc.land/google-updates-search-console-performance-analysis-guidance/)
- Google's revised core-update guidance says to wait at least a week after an update completes before analysing. — [Search Engine Journal](https://www.searchenginejournal.com/google-revises-core-update-guidance-whats-changed/524584/)
- **Glenn Gabe delta analysis** compares rankings and queries before and after a core update to isolate impacted pages and queries. He also compares hourly GSC data via Analytics Edge and the GSC API to see update impact quickly *(summary-level)*. — [Knowledge Bomb podcast recap](https://knowledgebomb.buzzsprout.com/2247897/episodes/13664821-glenn-gabe-major-algorithm-updates-2023); [GSQi](https://www.gsqi.com/?p=20)
- **Aleyda Solis**: a segmented Looker Studio report for analysing an update via GSC data by segments, plus "7 key questions" for ranking drops *(page 403, title-level only)*. — [Aleyda Solis: Google update analysis Looker Studio template](https://www.aleydasolis.com/en/search-engine-optimization/google-update-analysis-search-console-data-studio-report-template/); [Aleyda: rankings drop analysis](https://www.aleydasolis.com/en/search-engine-optimization/seo-rankings-drops-analysis/)
- Heuristic: several top-10 queries dropping on the same date suggests an algorithm update. A single query dropping alone suggests a competitor move or page decay *(vendor, summary-level)*. — [Texta](https://www.texta.ai/api/md/blog/ranking-drops-algorithm-updates-vs-tracking-no)

### Inferences: workflows

**W9. Content decay detector** [API/MCP]
- Pull `dimensions=[page]` for the last 3 months vs the prior 3 months, and the same 3 months YoY, using `final` data.
- Decision: decaying if clicks fall ≥ 20% vs both prior period and YoY (which rules out seasonality), prior-period clicks ≥ 100, and the weighted position worsened by ≥ 1.5 *or* impressions fell ≥ 20%.
- Diagnose by drilling into the page's queries: lost queries mean competitor or intent shift; stable position with lower CTR means a SERP feature or AIO appeared (route to W3/W4); position drop across many queries means refresh content.
- Action: the pipeline refreshes the page (W1 steps, update facts and year, add missing subtopics from the SERP comparison). Monthly cadence.

**W10. Algorithm-update impact by segment (delta report)** [API/MCP]
- Windows: 14–28 days before the update start vs 14–28 days after completion plus 7 days, same weekday mix.
- Segment by folder (page regex), query class (Q2 regex: brand/non-brand, question, commercial, local, long-tail), device, country and search appearance.
- Decision: identify segments with Δclicks ≤ −20% where Δposition is negative (not just CTR). Per Google, small position slips need no action, while large, persistent drops mean a quality self-assessment of that section.
- Hourly variant: `dimensions=[hour]`, `dataState=hourly_all`, last 10 days to timestamp the onset.

**W11. Seasonality check** [API/MCP + external Trends]
- Use 16 months of data (or BigQuery for longer). Compare the same months YoY per query cluster. Schedule refreshes 6–8 weeks before the seasonal impressions ramp *(synth)*.
- Source: [Google debugging guide](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops).

**W12. Search-intent shift detector** [API/MCP + SERP]
- Same query, stable or better position, but CTR falls ≥ 30% with impressions up. Or the page's query mix moves from commercial-regex to question-regex share (or the reverse) by more than 15 percentage points period-over-period.
- Action: run a live SERP check for result types (AIO, video, forums, product grids) and reformat the page to the dominant intent.

### Gaps
- I couldn't access Glenn Gabe's own posts (method only at summary level). Kevin Indig, Lily Ray and Mark Williams-Cook specific GSC workflows weren't retrieved in this session.

---

## Q5. Cannibalisation, device/country gaps, search appearance, Discover, News, image/video

### Takeaway
Cannibalisation can only be detected with query×page data, not query-only exports. Flag queries where 2 or more pages each take a meaningful impression share and the ranking URL alternates over time. Device, country and search-appearance tabs reveal sub-segment gaps. Discover and Google News have separate `type`s in the API, with no `byProperty` aggregation.

### Cited Findings
- Cannibalisation detection requires the query-page split. Find queries in the striking band with more than one page with impressions, then **consolidate, differentiate or internally link** *(summary-level)*. — [ContextBolt](https://contextbolt.com/blog/striking-distance-keywords-with-claude/); [Coupler.io GSC opportunity skill](https://www.coupler.io/ai-agent-skills/gsc-search-opportunity-finder)
- Search types: `image`, `video`, `news`, `discover` and `googleNews` are available. `googleNews` excludes the News tab. `byProperty` isn't supported for discover/googleNews. `byNewsShowcasePanel` is for News Showcase. — [API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- The Discover report needs a minimum impression threshold and keeps 16 months. — [TripleDart](https://tripledart.com/marketing-tutorials/how-to-check-your-google-discover-traffic-in-google-search-console); [Google 2019 Discover report launch](https://developers.google.com/search/blog/2019/04/search-console-reporting-for-your-sites)
- The search appearance tab aggregates by page, and differences there can explain drops (for example a competitor's rich result). — [GSC Help](https://support.google.com/webmasters/answer/7576553?hl=en); [Google debugging guide](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops)

### Inferences: workflows

**W13. Cannibalisation detection and resolution** [API/MCP]
- Pull `dimensions=[query,page]` (90d), plus `dimensions=[date,query,page]` for flip detection.
- Flag a query when it has impressions ≥ 100, at least 2 pages each with ≥ 15% of impressions, and the top page changes on at least 3 days in 28 or the weighted position SD is above 3.
- Exclude intended pairs: brand queries, homepage + service pages, and pagination.
- Resolution rules: (a) same intent with one weaker page (fewer clicks/backlinks) means **merge + 301**; (b) a near-duplicate that's needed for users (filters/params) means **canonical**; (c) different intents means **differentiate** (retitle/re-angle the weaker page and remove the shared query from its title/H1/H2), plus internal links with exact anchor to the chosen winner; (d) a blog page competing with a money page means de-optimise the blog and link it to the money page.

**W14. Device and country gap** [API/MCP]
- `dimensions=[page,device]` and `[query,country]`.
- Device gap: mobile weighted position ≥ 3 worse than desktop, or mobile CTR < 70% of desktop at similar position. Check mobile UX, CWV and above-the-fold content.
- Country gap: a target country with impressions ≥ 20% of the total but position ≥ 5 worse than the home market. Do localised SERP comparison (the user's same-country step), consider hreflang or localised content, and local links.

**W15-SA. Search appearance audit** [API/MCP]
- `dimensions=[searchAppearance]` then filter `searchAppearance equals <type>` × page.
- Compare CTR of pages with vs without a given appearance (review snippet, video, FAQ, product). Pages without the rich result whose peers have it get schema work.
- Note: Google cut FAQ and HowTo rich-result visibility in 2023, so don't expect FAQ appearance gains *(general knowledge; not re-verified this session)*.

**W16. Image and video search** [API/MCP]
- `type=image` with `dimensions=[page,query]`: pages with image impressions but CTR < 1% need better filenames, alt text, surrounding captions and image sitemaps. Image-intent queries ranking for pages with weak imagery need better images.
- `type=video` and the web `searchAppearance` video: pages with video impressions but no video appearance on web need VideoObject schema and indexable watch pages.

**W17. Discover and Google News** [API/MCP]
- `type=discover`, `dimensions=[page,date]`: identify hit pages and Discover's short lifespan curve. Extract patterns from winners (topic, image presence/size, headline length, freshness).
- `type=googleNews` similarly. Export monthly because of the 16-month limit.

### Gaps
- No verified Brodie Clark or Lily Ray Discover workflow was retrieved in this session.
- Exact thresholds for cannibalisation "share" aren't published by Google. All are *(synth)*.

---

## Q6. 2025–2026 features: branded filter, query groups, annotations, hourly; impact measurement; topical authority

### Takeaway
New UI features shipped in late 2025. The **branded queries filter** (announced 20 Nov 2025, AI-classified, not regex-based, top-level properties only) splits brand from non-brand across web/image/video/news. **Query groups** (27 Oct 2025, in Search Console Insights) use AI to cluster queries for high-volume properties. **Annotations** allow up to 200 per property with 120 characters each. Hourly API data covers 10 days. For automation, replicate the branded split with a brand regex and query groups with the agent's own clustering, because API exposure for both is unconfirmed.

### Cited Findings
- **Branded queries filter**: introduced 20 Nov 2025 with a gradual rollout. It splits Performance data into branded and non-branded across web, image, video and news. Google says it is **not** regex-based, and a separate regex option remains under "Filter by query". It's reported as available only for top-level properties, not URL-path or subdomain properties, and later reported as fully rolled out to eligible properties. — [Google Search Central blog](https://developers.google.com/search/blog/2025/11/search-console-branded-filter); [Search Engine Land](https://searchengineland.com/google-search-console-adds-branded-queries-filter-464928); [ALM Corp](https://almcorp.com/blog/google-search-console-branded-queries-filter/); [SER pre-announcement](https://www.seroundtable.com/google-search-console-brand-query-filters-40474.html)
- **Query groups**: launched 27 Oct 2025 in Search Console Insights. AI clusters similar queries and is available only to properties with a large volume of queries. — [Google Search Central blog](https://developers.google.com/search/blog/2025/10/search-console-query-groups)
- **Annotations**: up to **200 per property**, up to **120 characters**, attached to a date and visible to all users with property access. System annotations flag data-processing issues. Restricted users can't add or delete them. Annotations are site-level only *(third-party, Nov 2025 coverage)*. — [WTF is SEO? Nov 2025 roundup](https://www.seoforjournalism.com/p/google-news-updates-november-2025); [SEOTesting: GSC annotations](https://seotesting.com/blog/google-search-console-annotations/)
- **Hourly**: 10 days via API with `hour` + `hourly_all`. — [Search Engine Land](https://searchengineland.com/google-search-analytics-api-gains-hourly-break-down-for-past-10-days-454167)

### Inferences: workflows

**W18. Brand vs non-brand split** [UI-only for the native filter; API/MCP via regex]
- The agent maintains a brand regex (brand, misspellings, product names, founder names). Every opportunity workflow defaults to **non-brand** (`excludingRegex`) so brand CTR doesn't inflate the CTR curve. Report non-brand clicks as the core SEO KPI.
- Cross-check the native filter's totals in the UI periodically to catch missed brand variants.

**W19. Query groups → topic opportunity** [UI-only]
- Use Insights query-group cards (top and trending groups) to spot rising topics, then feed group names into W7 as seeds.
- API substitute: cluster query rows by embeddings.

**W20. Change log and annotations** [UI-only display; agent keeps its own log]
- On every pipeline publish, the agent writes a dated change log (URL, change type, target queries). The human mirrors key items as GSC annotations (≤ 120 characters).
- Use system annotations to exclude data-incident windows from comparisons.

**W21. Hourly monitoring for new or news content** [API/MCP]
- `dimensions=[hour,page]`, filter page = new URL, `dataState=hourly_all`, `type=web` / `googleNews` / `discover`, for the first 72h after publish.
- Use it to confirm indexing and first impressions, and to iterate the headline within hours for news.
- Also detect update onset (W10).

**W15. Impact measurement (content refresh, title test, internal links)** [API/MCP]
- Use `dataState=final`. Before window = 28 days before the change. After window = 28 days starting 7 days after the change (indexing lag). Keep equal length and the same weekday mix.
- Measure clicks, impressions, CTR and weighted position on (a) the changed page with page filter `equals`, (b) its target queries, and (c) a control group of similar unchanged pages (same folder regex) to net out seasonality and updates.
- Decision: a win if treated Δclicks − control Δclicks ≥ +10% and position improved. Otherwise iterate or revert titles.
- For internal-link tests, the treated pages are link *targets*.
- Google advises waiting "a few weeks" before judging. — [Google debugging guide](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops). SEOTesting builds before/after tests on this model — [SEOTesting](https://seotesting.com/blog/google-search-console-annotations/).

**W22. Topical authority by folder or cluster** [API/MCP]
- Map each topic cluster to a page regex (for example `^https://site\.com/(blog/)?(seo-audit|technical-seo)[^/]*`). Monthly, track per cluster: non-brand impressions, number of distinct queries with impressions, share of queries at position ≤ 10, and weighted position.
- Topical authority is growing when distinct-query count and top-10 share rise across the cluster, including on pages not recently edited (a spill-over effect).
- Clusters with high impressions but many queries at 11–30 need more supporting articles (a Koray-style topical-map gap). Feed them into W7.

**W23. Anonymised-gap watch** [API/MCP]
- Per page, `(page-only clicks − Σ query-row clicks)/page-only clicks`. A rising share means the page is winning ever-longer tail queries. Don't prune pages that look "query-less".
- Source: [Ahrefs](https://ahrefs.com/blog/gsc-anonymized-queries/).

### Gaps
- API availability of the branded filter, query groups and annotations is unverified. The API reference fetched lists no such parameters, so assume UI-only.
- I couldn't fetch the full Google posts for the branded filter and query groups (pages returned navigation only), so details such as Insights card names come from third-party coverage.
- Practitioner-specific workflows from Chris Long, Kevin Indig, Lily Ray, Brodie Clark, Mark Williams-Cook and Andrew Charlton weren't retrieved within the research budget. Attributions to them are deliberately omitted rather than guessed.
