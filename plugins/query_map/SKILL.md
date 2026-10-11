---
name: seo-query-map
description: Decide for every People Also Ask question, related search, autocomplete variant, keyword idea and Search Console query whether it becomes an H2 on this page, is covered inside a section, is linked to an existing client page, deserves its own separate page, or is dropped. Keyword clustering by SERP overlap, cannibalisation checks and topical boundaries. Use when planning a page, or alone to cluster keywords.
---

# Query map: what belongs on this page

**Script:** `run.py`. **Output:** `research/query_map.json`, containing `queries` (each with decision, reason, source, volume and GSC data), `h2_questions` and `counts`.

## Candidates, in priority order
1. **gsc:** striking-distance and gap queries the page already shows for (rewrite with Search Console data).
2. **paa:** Google PAA on the main SERP.
3. **paa_dfs:** DataForSEO PAA (click depth 2).
4. **paa_expanded:** PAA one level down.
5. **related / related_expanded:** Google related searches.
6. **paa_autocomplete:** question-prefixed autocomplete (the fallback when there is no PAA).
7. **autocomplete:** suggestions for the query.
8. **keyword:** DataForSEO related keywords with volume.

Near-duplicates (80%+ token overlap) are merged, keeping the higher-priority source.

## Decisions

| Decision | When | What the writer does |
|---|---|---|
| `h2` | A PAA or question query (or a GSC question the page shows for), up to 8 in deep mode or 5 in quick | Its own H2 in the reader's words, answered in the first 40–50 words |
| `cover_in_section` | Same intent as the main query (no distinct terms), a GSC non-question, 3+ shared top-10 URLs with the main query, PAA over the cap, or a question restating the main query | Use its words naturally inside the closest section |
| `existing_page` | Its distinct terms match a client page (child page, collection, guide), or another client page outranks this one for it in GSC | Link that page with a descriptive anchor; no section |
| `separate_page` | Fewer than 3 shared top-10 URLs (deep: SERP overlap check), or 2+ distinct terms (quick heuristic), or a question carrying a separate page's distinctive terms | No section. At most a one-line mention. Logged as a content-gap opportunity |
| `drop` | Shares under a third of the main query's content words (not PAA) | Ignore |

## Why SERP overlap decides it
When two queries share 3 or more of the same top-10 URLs, Google treats them as one topic, and one page can rank for both. With 0–2 shared URLs, Google wants different pages, and covering both on one page dilutes it. This is how senior SEOs cluster keywords. Deep mode checks up to 6 non-PAA candidates with real searches (cached).

## Cannibalisation rules
- A GSC query where another client page has a better position → `existing_page` (link it, don't compete).
- A `separate_page` topic the client already covers → `existing_page`.
- A rewrite must not drop the queries the page already earns (lint Q04 checks striking-distance queries).

## Edge cases

| Situation | What to do |
|---|---|
| Hub page and a country-specific query ("… uae") | `existing_page`: the child page owns it |
| Question about an error message ("your search did not return any data") | Usually a separate troubleshooting page |
| Brand or competitor names in queries | Separate or drop. Never write about a competitor's service |
| Off-topic autocomplete noise | `drop` (or harmless `cover_in_section` in quick mode; the writer ignores it) |
| Too many PAA (over the cap) | Keep the most specific and highest-volume ones as H2s; fold the rest |
| All candidates restate the main query | The page answers them as a whole. Use the SERP's expected topics for H2s instead |
| GSC shows the page ranking for an off-intent query | Don't chase it if it conflicts with the brief's intent. Log it |

## Agent review
The writer may phrase H2s naturally ("How do you check a UK visa application?" for "how to check uk visa application status"). The writer must not:
- turn `separate_page` items into sections
- ignore `h2` items, which lint Q01 blocks in deep mode
