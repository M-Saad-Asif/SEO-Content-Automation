---
name: seo-foundation
description: Analyse a client website for one page brief. The live page (exists or new, H1, title, meta), the sitemap and internal link map, child pages for hubs, Shopify products and specs, official-source facts verified against their text, and vertical checks. Use before writing any SEO page, or alone to audit what a site offers for a topic.
---

# Foundation: client site, sitemap and facts

**Script:** `run.py` calls the foundation step (`seo.py prep <brief>` when run alone).

**Outputs:**
- `fact_sheet.json`: page, products, facts, checks, gaps, decisions
- `link_map.json`: products, children, internal pages, official sources
- the foundation part of `writer_pack.md`

## What it analyses

| Area | What is collected | Why it matters |
|---|---|---|
| Live page (`page_url`) | HTTP status, title, H1, H2s, meta description, opening text | Keep the live H1. Match the existing angle. Know whether this is a rewrite or a new page |
| Sitemap index | Child sitemaps chosen by path tokens (max 12), page and post sitemaps | Every internal link must come from here. Never guess a URL |
| Hub children (`page_type: hub`) | Links under the page's path prefix, from the live page and the sitemap, with their anchor names | The hub links to child pages instead of repeating them |
| Products (`platform: shopify`) | `/collections/<h>/products.json` and `/products/<h>.json`, then each product page's `<dl>` spec block: dimensions, weight, material, colours, laptop size, internal codes | Real product URLs and specs; fit checks; no SKUs in copy |
| Official facts (`official_sources`) | Each declared value searched for in the fetched page text, after normalising case, spaces, ×/x and quotes, plus every `also` string | A fact is usable only when its source says it |
| Client facts and claims | `client_facts`; `approved_claims` checked against the client's own fetched pages | Positioning and service claims come only from here |
| Vertical checks (`checks/<name>.py`) | Computed comparisons such as `luggage_fit` | The writer copies results; it never reasons about fit |

## Fact status rules

| Situation | Status | Usable? |
|---|---|---|
| Source fetched and every value and `also` string found | `verified` | yes |
| Source blocks scripts or is JS-only, but captured agent text contains the value | `captured` | yes (capture expires after 7 days) |
| Source fetched but value not found | `not_found` | no; logged as a decision; written around |
| Source blocked, no capture | `pending` | no, until step 2 verifies it in the agent's browser or on another official source |
| `absence_of` fact: page loads, states the `also` alternative and has none of the listed phrases | `verified` (`absence_check`) | yes |
| Client facts from the brief | `operator` | yes, for positioning only |

**Approved claims:** a claim not found on the client's pages is dropped automatically and logged. Don't publish a service promise the site doesn't make.

## Scenario rules

| Scenario | What to do |
|---|---|
| Page returns 404 or isn't live | Treat it as a new page. Write a sentence-case H1 that matches the query. Logged as a decision |
| Page exists, `task: new` | Keep the live H1 exactly unless `brief.h1` is set. Support what is on the page (selector, product grid) rather than replacing it |
| Page exists, `task: rewrite` | `current_page` and `gsc_insights` decide what stays. Never drop a section that earns impressions |
| Hub page | Child pages come from the live selector first, then the sitemap. Link the relevant ones and keep the hub short. Never rebuild children's content in tables or bullets (lint R02) |
| Product guide or e-commerce | Products come only from store JSON. A handle that redirects (301) is replaced by its final URL. Prices are left out unless `hardcode_prices: true` |
| Product has no listed dimensions | No fit statement for it. Logged |
| Product dimension under 5 cm, or another implausible spec | Treated as doubtful: no fit claim. Logged |
| Irregular or expandable shape | Fit uses the widest point. The copy says it is measured unexpanded |
| Sitemap is huge (100+ child sitemaps) | Only child sitemaps matching the page path, plus page sitemaps, are read. Set `brief.sitemaps` to override |
| Sitemap missing or blocked | Links come only from the live page's own links and the official sources. Logged |
| JS-only official page (`needs_js`) | Capture it in the agent's browser (`seo.py capture`) or find the same fact on a script-readable official page |
| Source has moved (404) | Find the current official URL in step 2 (search, then fetch) and add the fact with `--add-fact`. Never keep a dead source |
| Two official sources disagree | Use the more specific and more recent one for the same entity, market and version. Never average. Log the conflict |

## What never happens here
- Guessing handles, slugs or child URLs.
- Taking a number from a page title, URL or navigation as a fact.
- Treating a third party (reseller, forum, competitor) as an official source for rules, fees or specs.

## Run it alone
`python scripts/seo.py prep briefs/<page>.yaml` prints the summary. Read the generated `writer_pack.md` foundation sections.
