# Primary-source GSC methods: Koray Tuğberk GÜBÜR, Chris Long, plus crawl-efficiency material from Jes Scholz, Barry Adams and Aleyda Solis

Research date: 2026-11-01. Access log, for the report writer:
- **Fetched OK (primary):** holisticseo.digital (3 Koray articles), nectivdigital.com blog index and 3 posts, seoforjournalism.com (Barry Adams guest post), learningseo.io GSC page.
- **Blocked (HTTP 403 or not reachable by the fetcher):** searchengineland.com (Chris Long's AI-prompts article and the "7 ways AI + GSC" article; Koray's SEL author page), medium.com/@ktgubur (two Koray case studies), webtan.impress.co.jp (Japanese write-up of a Jes Scholz Moz post), moz.com (the domain is refused outright), app.thejuicehq.com (DNS failure). x.com was not fetched. Koray's X posts below come from search-result snippets only and are marked as such.
- No block was worked around. Where a page was blocked, I looked for the same author's material on other sites.
- Long holisticseo pages were read only up to about 100k characters (they run 127k–205k characters). Later sections may hold more GSC detail.

## 1. Koray Tuğberk GÜBÜR: how he uses GSC (topical coverage, query-network growth, initial ranking vs re-ranking, crawl efficiency, cadence, what to publish next, historical data, quality thresholds)

### Takeaway
Koray's own articles use GSC as a scoreboard, not a documented step-by-step method. His recurring measure of topical coverage and query-network growth is the number of ranking queries in GSC, split into position bands (top 1–3 / 4–10 / 11–20 / 20–100) and counted as new queries, alongside clicks and impressions over YoY, 3-month and 6-month windows. Crawl Stats (total crawled, the By Purpose discovery/refresh split) and the Coverage report are his crawl and index evidence. I found **no primary source in which Koray gives numeric crawl-efficiency targets** (response time in ms, % canonical HTML hits, % 200/304). His publishing-momentum cadence, however, is documented with specific figures.

### Cited Findings

**Workflow K1: measuring query-network growth with GSC ranking-query bands (his core measurement pattern)**
- Trigger: a topical-map expansion project or case-study reporting. Read: GSC Performance, with ranking queries counted by position band (top 1–3, 4–10, 11–20, 20–100) plus "total new ranking queries", over YoY, 3-month, 6-month and multi-week comparison windows. Growth in ranking-query counts is used as the proxy for topical coverage; the article defines no separate GSC coverage metric. — [Koray, "How to Expand a Topical Map for Higher Topical Authority?", holisticseo.digital, 5/8 Jan 2023](https://www.holisticseo.digital/?p=15373)
- Results reported in that article (self-reported, from screenshots):
  - TeamColorcodes: 110%+ clicks, 7,000+ new top-1–3 queries, 17,000+ new queries.
  - Kanbanize: 245% clicks, 39,000+ new queries, 7,000+ top-1–3, 5,350 in 4–10.
  - Encazip: from about 10k to 500k+ monthly clicks, 38,000+ new queries (3,722 top-3; 6,005 in 4–10; 7,572 in 11–20; 20,000+ in 20–100).
  - BKMKitap: 750k → 3.9M clicks, 68,500+ queries.
  - Complaintsboard: 320%+ clicks, 413k+ queries.
  - The article says it draws on 26 SEO sample studies with open Search Console data. — [same source](https://www.holisticseo.digital/?p=15373)
- He reads impressions rising with a flat average position as expansion of the query network: one site's average position moved only from 32.1 to 31.9 while impressions rose about 2M. Inference: new low-position queries were entering the network. — [same source](https://www.holisticseo.digital/?p=15373)

**Workflow K2: deciding what to publish next (topical-map expansion)**
- Find topical gaps between topic centroids.
- Expand by adding more entities of the same type, more attributes of entities already covered, and deeper context.
- Add contextual bridges (one example recommends at least 3 per topical map).
- Check search demand before translating or publishing, because low-demand translations waste crawl resources.
- The article does **not** describe a GSC filter for choosing topics. Selection is driven by the topical map, and GSC is used afterwards to verify results. — [Koray, holisticseo.digital, Jan 2023](https://www.holisticseo.digital/?p=15373)

**Workflow K3: publishing momentum cadence and refresh (primary)**
- Reported ramp in the flagship 0→128k case:
  - one article every 3 days;
  - then one every 2 days;
  - then daily;
  - then several per day;
  - later 3 articles a day (1 canonical plus 2 alternate-language versions).
- The source's own timeline is internally inconsistent (the "20 days" milestones appear twice, in different orders). — [Koray, "Importance of Topical Authority for SEO", holisticseo.digital, pub. 11 Feb 2021, upd. 24 Nov 2022](https://www.holisticseo.digital/?p=4946)
- Refresh rules:
  - Authors update content according to the **initial ranking** it gets.
  - New articles are checked for pending anchor texts from existing pages that can now link to them.
  - Consistent publishing is said to earn more crawl resources. — [same source](https://www.holisticseo.digital/?p=4946)
- In the 2023 article, one project stresses "fast content production momentum". On one large site, stale or low-quality pages were removed or de-indexed. — [Koray, Jan 2023](https://www.holisticseo.digital/?p=15373)
- Reported results:
  - 0 → 128k organic traffic in 123 days, and about 12k clicks/day by day 162. The same article also cites 0→100k in 115 days; the two figures conflict.
  - Third site: +7k clicks/day over 6 months, then a drop tied to the Armenia–Azerbaijan war, read from GSC traffic plus average position. — [same source](https://www.holisticseo.digital/?p=4946)

**Workflow K4: GSC crawl and index evidence (Crawl Stats + Coverage)**
- Crawl Stats is used to show a crawl-budget increase after a dated change (after 28 Sep: 1,400+ pages crawled). He points to the "By Purpose" view (discovery vs refresh).
- The Coverage report showed 346 pages as "Crawled – currently not indexed" at project end.
- The hreflang report was used for before/after evidence.
- Crawl frequency and indexing speed are described as correlated with topical authority. — [Koray, holisticseo.digital, 2021/2022](https://www.holisticseo.digital/?p=4946)
- His crawl-budget guide treats Crawl Stats (90-day window, verified properties only) qualitatively:
  - Crawl frequency should be fairly constant and rise with site size.
  - Falling frequency can mean stale content or a robots.txt block.
  - Fast responses raise the crawl rate limit; slow responses and 5xx lower it.
  - **No numeric targets are given.** — [Koray, "Crawl Budget", holisticseo.digital, pub. 16 Jul 2020, upd. 20 Apr 2022](https://www.holisticseo.digital/technical-seo/crawl-budget/)
- Decision rules from the crawl-budget guide:
  - Return 410 rather than 404 for content removed for good.
  - 301 or merge content you keep.
  - Point internal links straight at 200 URLs to break redirect chains.
  - Fix soft-404s.
  - Consolidate faceted, session and duplicate URL spaces.
  - Use log analysis to confirm Googlebot has stopped requesting 410'd assets. — [same source](https://www.holisticseo.digital/technical-seo/crawl-budget/)
- In the Encazip case he used GSC YoY comparisons (via DataBox) and Authoritas' GSC module to track query and traffic productivity. Reported: +155% organic traffic in 6 months, +110% YoY. The crawl-efficiency work in that case is described only qualitatively (fewer requests, Brotli, HTTP/2). — [Koray, "Holistic SEO Case Study", holisticseo.digital, pub. 24 Nov 2022, upd. 29 May 2023](https://www.holisticseo.digital/seo-research-study/holistic-seo)

**Initial ranking vs re-ranking; historical data; quality thresholds**
- Initial ranking is the phase after indexing. It is influenced by social sharing, sitemap inclusion, site-wide linking, and avoiding canonicalization or cannibalization issues. Re-ranking is a set of algorithms that the initial ranking can affect. No GSC method is given for telling them apart. — [Koray, 2021/2022](https://www.holisticseo.digital/?p=4946)
- A source must hold a position with strong click satisfaction for a period before the position becomes stable. Rankings can survive the reversal of technical gains once a "positive ranking state" exists. — [Koray, Jan 2023](https://www.holisticseo.digital/?p=15373)
- Topical authority is tied to historical data, which is why new domains are preferred. Historical trust can be reset by sudden shifts in search behaviour. — [Koray, Jan 2023](https://www.holisticseo.digital/?p=15373); [Koray, 2021/2022](https://www.holisticseo.digital/?p=4946)
- Quality thresholds move with the competing documents: an article that was once strong can become relatively weaker without getting worse. — [Koray, Jan 2023](https://www.holisticseo.digital/?p=15373)
- The 2023 article mentions "cost of retrieval" only as a topic for future publications. — [same](https://www.holisticseo.digital/?p=15373)
- **Snippet-level only (x.com not fetched).** According to search-result snippets:
  - Initial rankings come from statistical semantics (entities, predicates, phrase-based term distributions), and re-ranking comes from sentential semantics. — [Koray on X, status 1918074533723988438](https://x.com/KorayGubur/status/1918074533723988438)
  - A search summary attributes to him the claim that a low-PageRank page can be ignored unless it reaches 10,000+ impressions. I could not open the post itself. Treat as **unverified**.
  - A search summary also attributes to him an extended formula in a 2026 Search Engine Land article: ((Historical Data × Topical Coverage) ÷ Cost of Retrieval) × Right Visual Annotations. SEL returned 403. — [SEL author page, blocked](https://searchengineland.com/author/koray-tugberk-gubur)
- **Secondary:** an interview reports that he read Googlebot crawl-delay and crawl-frequency changes as a sign of server fatigue and warned the client's CTO. — [Sitechecker interview (secondary)](https://sitechecker.pro/interview-koray-tugberk-gubur/)

### Inferences
- A practical "Koray-style" GSC loop that can be built from these sources:
  1. Publish to the topical map at a rising cadence.
  2. Watch new-query counts and position-band migration (20–100 → 11–20 → 4–10 → 1–3), plus impressions growing ahead of clicks.
  3. Refresh pages according to the initial position they receive.
  4. Use Crawl Stats By Purpose (discovery share) and "Crawled – currently not indexed" counts as signals of crawl priority and quality.
- The banding and the "update per initial ranking" rule are his. The specific numeric triggers in that loop would be our own construction.

### Gaps
- **No primary source found** for Koray's numeric crawl-efficiency targets (response-time ms, % canonical HTML hits, % 200/304). The holisticseo pages I could read contain none, and Medium, X and SEL were blocked. Do not attribute such numbers to him without a source.
- No primary statement of a fixed refresh interval (e.g., "every N days"). Refresh is tied to the initial ranking, not to a calendar.
- No documented GSC regex or filter workflow from Koray.
- The 10,000-impression threshold and the "visual annotations" formula are unverified (snippets only).
- The tails of the holisticseo pages were not read past about 100k characters.

## 2. Chris Long (Nectiv): GSC methods

### Takeaway
The one GSC workflow fully verified from a primary source is Nectiv's "conversation data" method. It uses a regex for queries of 10+ words in GSC, exports the results, analyses them in Claude, and turns the output into prompt-tracking candidates. Long's AI Overview gap method uses Ahrefs, not GSC. His Search Engine Land versions were blocked (403).

### Cited Findings

**Workflow C1: mining GSC for conversational / LLM-style queries**
- Steps:
  1. Open Performance → Queries.
  2. Add filter → Query → Custom (regex) `^(?:\S+\s+){9,}\S+$`. It matches queries of 10 or more words. The page renders it with doubled backslashes, which is likely markdown escaping; use single backslashes in GSC.
  3. No impression or click minimum is set.
  4. Export.
  5. Upload to Claude (or Claude Code) and ask, for example: what customers ask about the brand, how users phrase prompts, which product attributes matter, and what the data says about the customers.
  6. Read the output for themes, brand and competitor mentions, question framing, attributes and geographic qualifiers.
  7. Ask Claude for prompt-tracking recommendations. Hand-pick the ones the data supports before loading them into a tracker.
  — [Nectiv, "How To Mine Google Search Console For Conversation Data (Regex Included)", no date shown, ~early 2026](https://nectivdigital.com/blog/how-to-mine-google-search-console-for-conversation-data-regex-included.md)
- Reported findings are qualitative only:
  - A PR issue from 3+ years ago was still being queried.
  - More country-specific software searches than expected.
  - One competitor is used as the benchmark for comparisons.
  - Frequent "cheaper alternative" searches.
  - AI Mode–filtered impressions rose steadily over 3 months; no figures are given. — [same](https://nectivdigital.com/blog/how-to-mine-google-search-console-for-conversation-data-regex-included.md)
- Caveats the post states itself:
  - There is no proof that these queries come from LLMs.
  - Some queries contain personal data (PII).
  - Rand Fishkin's study found a 0.081 similarity across 142 respondents' prompts, so the method reveals themes, not exact prompts. — [same](https://nectivdigital.com/blog/how-to-mine-google-search-console-for-conversation-data-regex-included.md)
- A version is republished on SEL and attributed to Chris Long. It was blocked (403), so its date is not confirmed. — [SEL, blocked](https://searchengineland.com/see-ai-search-prompts-google-search-console-470358)
- **Secondary:** ContextBolt says the regex finds long queries, not confirmed AI queries. It also reports that Google shipped an AI report in GSC in June 2026 with impressions only and no queries. I did not verify that. — [ContextBolt (secondary)](https://contextbolt.com/blog/ai-search-prompts-search-console/)

**Workflow C2: finding AI Overviews where you already rank (Ahrefs, not GSC)**
- Steps:
  1. Open Ahrefs Organic Keywords.
  2. Filter SERP Features = AI Overview.
  3. Filter Position 2–10.
  4. Review keywords where your brand is not cited in the AI Overview.
  5. Rework those pages' content density and structure.
- No results are reported. — [Nectiv / Chris Long (video transcript), no date](https://nectivdigital.com/blog/how-to-find-ai-overviews-where-you-have-strong-rankings.md)

**Context**
- Nectiv's "stair-stepping into AI Mode" post (~early 2026, inferred from a 28 Jan 2026 timeline entry) describes the "Great Decoupling" (impressions up, clicks flat or down) qualitatively. It contains no GSC numbers. — [Nectiv](https://nectivdigital.com/blog/like-it-or-not-google-is-slowly-stair-stepping-us-into-ai-mode.md)

### Inferences
- C1 fits directly into an automated pipeline: a GSC API query with the 10+ word regex, then an LLM theme-clustering pass, then candidate prompts or FAQ topics. C2 can be approximated with GSC alone, using queries at position 2–10 together with a separate check for whether an AI Overview appears.

### Gaps
- I found nothing on the Nectiv blog about GSC + Looker Studio, GSC + MCP, or content decay. The SEL article "7 ways AI can turn GSC data into action" was blocked, and its author is unconfirmed.
- His guest posts on Moz and SEJ were not reachable (moz.com refused; SEJ not attempted for Long). No posts are dated on Nectiv.

## 3. Barry Adams, Jes Scholz, Aleyda Solis: crawl efficiency in GSC

### Takeaway
Barry Adams gives the only primary, numeric Crawl Stats playbook found. The thresholds are:
- average response ≤600 ms, with 200 ms ideal;
- HTML should be the top file type;
- for established publishers, a Discovery share above 10% (Refresh below 90%) is a red flag;
- Smartphone Googlebot should dominate;
- watch the AdsBot share.

I could not reach primary material from Jes Scholz or Aleyda Solis.

### Cited Findings

**Workflow B1: Barry Adams's Crawl Stats review for news publishers**
1. Average response time: aim for ≤600 ms; 200 ms is ideal. Above 600 ms needs work: server caching, more hosting capacity, a CDN. Googlebot crawls mainly from California, so server location matters.
2. By response: most responses should be 200. A large share of 301/302 or 5xx means a problem; drill into the example URLs.
3. By file type: HTML should be the most-requested type. Heavy crawling of JS, JSON or font files takes budget away from articles, so make pages lighter.
4. By purpose: for established publishers, Discovery above 10% (Refresh below 90%) means investigate crawl waste.
5. By Googlebot type: Smartphone should dominate. A large Page-resource-load share means pages need to be lighter. A large AdsBot share means asking the ads team to tighten campaigns.
6. Crawl the site with an SEO crawler (Sitebulb, Screaming Frog) to find duplicates and internal redirects.

Size rules:
- under 100k URLs: crawl budget is rarely an issue;
- 100k–1M URLs: some issues may be worth fixing;
- over 1M URLs: monitor regularly.

Actions:
- canonical or 301 for duplicates (fixes indexing, not the crawl waste);
- careful robots.txt disallows (the disallowed budget is not reallocated);
- link internally to final URLs;
- maintain sitemaps, while treating crawling as the main discovery route.

No before/after results are reported. — [Barry Adams, "Crawl optimization for news publishers", WTF is SEO? newsletter (seoforjournalism.com), 13 Mar 2023](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)

- **Secondary:** a DDMA interview reports Adams's view that news sites are crawled so heavily that log analysis is often impractical, and GSC Crawl Stats is usually enough. — [DDMA (secondary, not fetched)](https://ddma.nl/kennisbank/barry-adams-polemic-digital-news-publishers-really-need-to-double-down-on-what-makes-them-unique-in-terms-of-their-journalistic-output/)

**Aleyda Solis**
- LearningSEO.io's GSC section is a list of six external guides (Google, Backlinko, SEJ/Anna Crowe, SEOSLY/Olga Zarzeczna, Ahrefs/Joshua Hardwick, and Nick Brown, whose link points to Semrush although it is labelled Ahrefs). It contains no workflow of her own. — [LearningSEO.io GSC page](https://learningseo.io/seo_roadmap/deepen-knowledge/google-search-console/)

### Inferences
- Adams's thresholds give an automated Crawl Stats health check concrete pass/fail lines. Note that the >10% Discovery rule is scoped to *established publishers*; a growing site that publishes heavily will have a legitimately higher Discovery share.

### Gaps
- **Jes Scholz:** no primary text retrieved. Her "crawl efficacy" material (SEL and Moz, ~2023) could not be reached: SEL and webtan returned 403, moz.com is refused, and the JuiceHQ mirror would not resolve. From memory, which is **unverified**: she defines crawl efficacy as the time between publishing or updating a URL and Googlebot's next crawl, and prefers it over crawl volume. Do not cite this until it is verified.
- **Aleyda Solis:** no Crawling Mondays episode or checklist containing a GSC crawl workflow was retrieved; the search found only show listings.
- **Barry Adams on polemicdigital.com:** not fetched. The SEO for Google News newsletter archive was not searched directly.
