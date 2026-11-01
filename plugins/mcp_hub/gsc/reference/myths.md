# Myths and mistakes to refuse

| Myth or mistake | Correction |
|---|---|
| Spam Request indexing to fix indexing | It doesn't scale and doesn't change canonicals; fix quality, links and sitemaps (Mueller 2026; Search Engine Roundtable 2024) |
| robots.txt removes indexed pages | It blocks crawling, not indexing; the noindex on a blocked page is never seen |
| The Removals tool deindexes permanently | It lasts about 6 months; pair it with 404/410/noindex |
| Validate fix makes Google index CCNI pages | It samples URLs for technical issue classes; it is not for CCNI/DCNI (SOTR 112) |
| Drive 404s and non-indexed counts to zero | Expected 404s are correct; there is no target index ratio (Google's own docs site is about 5% indexed) |
| A higher average position after September 2025 means rankings improved | The `num=100` removal took out deep scraper impressions |
| Impressions up = visibility up | AI Overview impressions are shared, and CTR falls (Ahrefs, the Great Decoupling) |
| "Other" file type means client-side rendering | Other includes redirects, fonts and RSC payloads; read the examples |
| Block `/_next/static`, `*.js`, `*.json` to save crawl budget | It breaks rendering; Google warns against blocking resources |
| A query-only noindex on `_rsc` | It also noindexes the HTML; condition it on the `RSC: 1` header |
| noindex saves crawl budget | Google still requests the page; use robots.txt for URL spaces with no value |
| Use robots.txt or 503/429 to reshuffle budget | "Don't use robots.txt to temporarily reallocate"; 503/429 beyond 2–3 days reduces crawling |
| Mass-redirect 404s to the homepage | It creates soft 404s that keep being crawled |
| `site:` shows index coverage | It's an artificial query; Search Console is the source of truth |
| Add the Gen-AI report to Performance totals | It is already included |
| Performance has AI Overview / AI Mode appearance filters | Google says no: they are folded into Web |
| An empty MCP result means no traffic | Usually the wrong property format or an account without access |
| A fixed industry CTR curve | Build the site's own curve, segmented for AI Overviews |
| Disavow routinely | Google typically ignores spam links; disavow is a last resort |
| Reconsideration fixes algorithmic drops | Without a manual action there is nothing to reconsider |
| Prune pages "to free index quota" | There is no per-site index quota (Illyes); prune only to consolidate quality |
