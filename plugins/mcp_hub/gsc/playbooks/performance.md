# Performance: site-level playbooks (PF8–PF31)

The datasets behind these playbooks:

| Dataset | What it is |
|---|---|
| `pages` | byPage totals, 90 days |
| `pages_prev` | the previous 90 days |
| `pages_yoy` | the same 90 days last year |
| `query_page` | query × page, up to 100k rows |
| `query_page_prev` | query × page for the previous 90 days |
| `queries` | byProperty totals |
| `page_device` | page × device |
| `page_country` | page × country |
| `appearance` | search appearance |
| `dates` | 16 months by date |
| `discover`, `news`, `image`, `video` | page data for each search type |
| `hourly` | the last 10 days by hour |

**API rules:**
- Page past 25k rows with `startRow`.
- Filter groups are AND-only, so OR logic goes inside one RE2 regex.
- `searchAppearance` can't be combined with other dimensions.
- Discover and Google News have no query dimension and no `byProperty`.
- Discover has no device dimension.
- Hourly data uses `dataState: hourly_all` and covers 10 days.
- Use `final` data for comparisons.

| ID | When | How (view) | Decision → action |
|---|---|---|---|
| PF8 Intent segments | Every report | `data intent` (regex classes: R-TRANS, R-SERVICE, R-COMP, R-INFO, R-NAV, R-SAAS, R-PROBLEM, R-LOCAL, questions, brand). Regex, not the UI's AI filter (deterministic, API-safe; Mark Williams-Cook) | Report KPIs per segment; Sturm's funnel prompts map to R-TRANS/R-SERVICE/R-COMP |
| PF9 Cannibalisation | Monthly | `data cannibalisation`: ≥100 impressions with ≥2 pages each ≥15% [synth]; brand, homepage and pagination excluded; money queries first | Blog vs money page → de-optimise the blog, link it to the money page. Same intent → merge + 301 or differentiate and remove the shared query from the weaker page's title/H1/H2s. Act only on money queries or flip-flopping (Quaid/Sturm); merges and redirects need approval |
| PF10 Decay | Monthly | `data decay`: clicks −20% vs the previous 90 days **and** year on year [synth], prior ≥100 clicks | Position loss → competitors/intent, refresh through the pipeline (`queue decay`). CTR loss at a stable position → SERP feature or AI Overview (PF2/AI2). Impression loss → demand or indexing (URL Inspection) |
| PF13 Seasonality | Planning | `data trend` (16 months), year on year per folder | Refresh 6–8 weeks before the seasonal ramp [synth] |
| PF14 Intent shift | Stable position, falling CTR | CTR −30% with impressions up, or the intent mix moving >15 points [synth] | Check the live SERP; reformat the page to the dominant intent |
| PF15 Device gap (mobile-first) | Monthly | `data device`: mobile ≥3 positions worse, or mobile CTR <70% of desktop [synth] | Mobile parity of content, links and schema; CWV; above-the-fold content |
| PF16 Country gap | Multi-market | `data country`: the target country (from the client locale) ≥20% of impressions but ≥5 positions worse [synth] | Compare the SERP in that country (the pipeline's `serp_intel`), hreflang, local links |
| PF17 Search appearance | Rich-result pages | `data appearance`; filter appearance × page | Peers have a feature you don't → schema work. FAQ ended May 2026: don't chase it |
| PF18 Image search | Image-led sites | dataset `image` | Filenames, alt text, captions, image sitemaps; Web multimodal (Lens) is UI-only (PF30) |
| PF19 Video search | Video sites | dataset `video` | VideoObject, indexable watch pages (`indexing.md` IX10) |
| PF20 Discover | Publishers | dataset `discover` (page × date; no position, no query) | Winning patterns: images ≥1,200 px with `max-image-preview:large`, titles that capture the content, timeliness. Separate Discover drops from Search drops (Feb 2026 Discover core update); skip the logging-error dates |
| PF21 Google News | News sites | dataset `news` | Iterate headlines within hours (PF25) |
| PF22 Brand vs non-brand | Every report | `data brand`; the regex comes from the client profile (add misspellings as `client_aliases`) | Opportunity work is non-brand. Koray: branded demand rising with non-brand is the strongest pattern. Check the UI branded filter now and then (`ui_branded`) |
| PF23 Query groups | Topic discovery | UI-only (Insights) | Feed the group names into PF6; the API substitute is clustering the query rows |
| PF24 Change log | Every publish | `data changes`; finished pipeline pages are logged automatically; `gsc log` adds manual changes | Mirror key items as Search Console annotations (≤120 characters; hidden in compare mode) |
| PF25 Hourly | First 72 hours after publishing; update onset | dataset `hourly` (`hour` × `page`, 10 days; open-gsc-mcp or the API) | Confirm first impressions; news headline tests |
| PF26 Impact | After every change | `data impact` (direction); the controlled version is 28 days before vs 28 days starting 7 days after, `final`, against a control group from the same folder | Win = treated Δclicks − control Δclicks ≥ +10% with position improved [synth]; iterate or revert titles |
| PF27 Topical coverage (Koray) | Monthly per folder | `data coverage`: distinct ranking queries by band (1–3, 4–10, 11–20, 21–100), new and lost queries | Folders with many queries at 11–30 → more supporting articles. Impressions growing with a flat position = the query network expanding. Refresh pages according to their initial ranking |
| PF28 Momentum (Koray) | New sites | `data trend` median daily impressions; ~10,000/day = re-ranking begins (interview-reported) | Scale coverage at the milestone; keep the cadence controlled |
| PF29 Anonymised gap | Monthly | (page clicks − listed query clicks) ÷ page clicks, per page in `data page` | A rising gap = long-tail wins; never prune "query-less" pages |
| PF30 Multimodal (Sep 2026) | Image-heavy, ecommerce | UI-only (Web → Multimodal; no queries) | Image quality and product imagery; ask for an export |
| PF31 Platform properties | Brands with social video | UI-only (Instagram, TikTok, X, YouTube properties) | Front-load keywords in post and video descriptions (Sturm) |

Sources: Google Performance help and the traffic-drop guide; Mark Williams-Cook; Glenn Gabe; Koray Tuğberk Gübür; Ahrefs; SEOTesting. Links are in the research report §4.4.
