---
name: seo-keyword-research
description: Use DataForSEO for search volumes, search intent, related keywords and deep People Also Ask (click depth 2) for a target query and the page's Search Console queries, in the brief's country and language. Use for new pages and rewrites, or alone for keyword research and prioritisation.
---

# Keyword research (DataForSEO)

**Routes:**
- **Script:** set `DATAFORSEO_USERNAME` and `DATAFORSEO_PASSWORD`. These are the same variable names the official DataForSEO MCP server uses, so one set of credentials serves both. Calls are paid per task and cached for 7 days.
- **MCP:** run the official DataForSEO MCP server (related keywords, keyword overview, SERP organic with `people_also_ask_click_depth`), save the result, then `seo.py ingest <run> keyword_research <file>`.

**Raw format for ingest:**

```json
{"keywords": [{"keyword": "...", "search_volume": 0, "intent": "informational", "competition": "LOW"}],
 "paa": ["question 1", "question 2"]}
```

## Calls (script route)

| Call | Input | Used for |
|---|---|---|
| `dataforseo_labs/google/related_keywords/live` | Target query plus top GSC query (depth 1, 40 each) | Related keywords with volume and intent |
| `dataforseo_labs/google/keyword_overview/live` | Target, GSC top and striking queries | Volume and intent of the queries that matter |
| `serp/google/organic/live/advanced` (deep only) | Target, depth 10, PAA click depth 2 | Deeper PAA than Serper |

The location comes from the locale (`en-GB` gives United Kingdom), or from `brief.dataforseo_location`. The language comes from the locale.

## Rules for using the data

| Situation | What to do |
|---|---|
| A related keyword with meaningful volume, same intent, 3+ shared top-10 URLs | Cover it here: use its wording in a heading or opening sentence |
| A related keyword with a different intent or entity | `separate_page` (query_map), logged as a content opportunity |
| DataForSEO intent disagrees with the SERP-based intent | The live SERP wins (it's what Google shows now). Log the disagreement |
| Several variants of the same keyword | Use the highest-volume natural variant in the H1 or title area. Others appear naturally once; never stuff |
| Zero or unknown volume | Not worthless (new or long-tail). Keep it if it's a real question with SERP evidence |
| Question keywords | Candidate H2s (query_map treats them like PAA) |
| PAA from click depth 2 | Second-level questions: H2 or H3 when they deepen the main intent; drop when they drift |

**Never** quote search volumes in the copy, chase volume against intent, or add keywords that don't belong to the page's one macro context.

## Edge cases

| Situation | What to do |
|---|---|
| Credentials missing | Plugin returns `not_configured` and the run continues on Serper data |
| API error or out of funds | Clean error, logged; continue |
| Country not in the location map | Set `dataforseo_location` in the brief |
| Very broad head term (huge volume) | Don't retarget the page to it; the brief's query stays the focus |
