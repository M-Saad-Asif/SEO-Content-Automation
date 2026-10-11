---
name: seo-gsc-insights
description: Use Google Search Console data to steer a page rewrite or a new page. Every query the page shows for (last 90 days) with clicks, impressions, CTR and position. Striking-distance queries, page-1 queries with weak CTR, query gaps the page doesn't cover, and cannibalisation with other client pages; for new pages, which client pages already rank for the topic. Use for rewrites and refreshes, or alone for a page performance review.
---

# Search Console insights

**Routes**, both producing the same analysis:
- **Script (default):** set `GSC_SERVICE_ACCOUNT_JSON` to a service-account key file, and add that account's email as a user on the Search Console property. The property comes from `brief.gsc_property`, defaulting to `sc-domain:<domain>`.
- **MCP:** with a GSC MCP server attached to your agent (several community servers exist), fetch the rows and save them as raw JSON, then run `seo.py ingest <run> gsc_insights <file>`.

**Raw format for ingest:**

```json
{"window": ["YYYY-MM-DD", "YYYY-MM-DD"],
 "page_rows": [{"query": "...", "clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}],
 "site_rows": [{"query": "...", "page": "https://...", "clicks": 0, "impressions": 0, "position": 0.0}]}
```

- `page_rows`: dimension `query`, filtered to `page = page_url`, last 90 days ending 3 days ago. CTR is 0–1.
- `site_rows` (optional, for cannibalisation): dimensions `query` and `page`, filtered to queries containing the main topic word.

## When it runs
- **`task: rewrite`:** always, if enabled (`connectors: auto` or listed).
- **`task: new`:** too. The page has no rows, but the site rows show which client pages already rank for the topic, so the new page gets a distinct angle and links to them.

## Analysis rules

| Bucket | Rule | What the rewrite does |
|---|---|---|
| Top queries | Sorted by impressions | Keep the sections and wording that earn them. Never drop a ranking section |
| Striking distance | Position 4–20, 10+ impressions | Cover each explicitly, ideally in a heading or opening sentence, in the searcher's words. Lint Q04 blocks when one with 100+ impressions is missing |
| Weak CTR | Position up to 10, 50+ impressions, CTR under 60% of the typical CTR for that position (pos 1 about 28%, 2 about 15%, 3 about 10%, 4 about 7%, 5 about 5%) | Rewrite the title and meta description to answer that query (lint Q05) |
| Query gaps | 5+ impressions, query words missing from the current page | Add the missing concept where it fits the intent; if it doesn't fit, leave it (log) |
| Cannibalisation | A top query also sends 10+ impressions to another client page | The better-positioned page keeps the query; this page links to it. Recommend merging if both are weak |

## Edge cases

| Situation | What to do |
|---|---|
| No rows (new page, or no impressions) | Use the SERP research; report other client pages ranking for the topic |
| Under 100 total impressions | Data is thin. Treat buckets as hints, not targets |
| Page shows for off-intent queries | Don't chase them. Note them for a separate page if valuable |
| Branded queries (client name) | Keep the brand phrasing; never optimise them away |
| URL changed recently (redirect) | Query the old URL too through the MCP route and merge the rows |
| Property not verified for the service account (403) | The plugin fails cleanly and the run continues. Logged |
| Data looks seasonal | Prefer the last 90 days; mention seasonality in decisions if obvious |

**Never** fabricate GSC numbers, and never quote GSC figures in the article copy. They steer the writing; they aren't content.
