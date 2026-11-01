# Google Search Console MCP servers (as of 1 November 2026)

Research date: 2026-11-01. GitHub stars and last-push dates come from the GitHub REST API (`api.github.com/repos/<owner>/<repo>`, fields `stargazers_count` and `pushed_at`), queried on 2026-11-01. Package versions come from `npm view` and the PyPI JSON API on the same day. Where a figure comes only from a vendor blog, the vendor is named.

## Is there an official Google Search Console MCP server?

### Takeaway
No. As of November 2026 Google has not published a Search Console MCP server. Google's official MCP list includes Google Analytics (open source), BigQuery (managed remote plus the MCP Toolbox), Chrome DevTools and Google Workspace, but not Search Console, PageSpeed Insights or CrUX. Every GSC MCP server is third-party code calling the public Search Console API. The closest official route is Google's BigQuery MCP pointed at a GSC Bulk Data Export dataset.

### Cited Findings
- **Google's MCP list.** github.com/google/mcp lists these remote (Google-managed) servers: AlloyDB, BigQuery, Bigtable, Cloud Resource Manager, Cloud SQL, Compute Engine, Developer Knowledge API, Firestore, Maps Grounding Lite, SecOps, GKE, Spanner, Cloud Run, Cloud Storage. Its open-source servers are Workspace, Firebase, Cloud Run, Go, **Google Analytics** (github.com/googleanalytics/google-analytics-mcp), MCP Toolbox for Databases, GCS, Genmedia, GKE, Cloud Security, gcloud, Observability, Flutter/Dart, Angular, Maps Code Assist and **Chrome DevTools**. Search Console, PageSpeed and CrUX are not on it. The repo also carries the line "This is not an officially supported Google product." — [google/mcp](https://github.com/google/mcp)
- The official Google Analytics MCP had 3,603 stars and a last push on 2026-10-29. It is the "Analytics analog" that Search Console does not have. — [googleanalytics/google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) (GitHub API)
- Windsor.ai states that Google had not published a Search Console MCP server as of 1 October 2026, though it publishes one for Google Analytics. — [Windsor.ai](https://windsor.ai/google-search-console-mcp/)
- Enrich Labs says the same as of early October 2026 and notes that Google does ship an official Google Ads MCP. — [Enrich Labs](https://www.enrichlabs.ai/blog/google-search-console-mcp-2026)
- ContextBolt (updated 22 October 2026) also says no official GSC MCP exists. — [ContextBolt](https://contextbolt.com/blog/google-search-console-mcp/)
- Quattr said no official Google MCP for Search Console existed as of 2 August 2026. — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console)
- **Google's BigQuery MCP.** It exposes `execute_sql` and `execute_sql_readonly` against your own datasets, which can include the GSC bulk export. It comes as a managed remote endpoint or the open-source MCP Toolbox, uses IAM auth, caps results at 3,000 rows and 3 minutes per call, and bills BigQuery query costs. — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console); BigQuery remote MCP is listed at [google/mcp](https://github.com/google/mcp)

### Inferences
- An "official" GSC path today means one of two things: the Search Console API through a community wrapper, or the BigQuery bulk export through Google's BigQuery MCP. The plugin should not wait for a Google-built server.
- Google's Chrome DevTools MCP (official) can cover some lab-performance checks. It is not a CrUX field-data source.

### Gaps
- I found no Google announcement or roadmap item for a Search Console MCP. Absence of evidence is not proof that none is planned.

## Which community GSC MCP servers exist, and what tools does each expose?

### Takeaway
There are dozens of community servers. Eight matter for the decision:
- **AminForou/mcp-gsc:** the most popular (2,080 stars), Python, OAuth or service account, about 20 tools, destructive tools gated.
- **ahonn/mcp-server-gsc:** the server the project uses now. 282 stars, TypeScript, service account, 8 tools, strong `search_analytics` schema but no `startRow`/pagination and no hourly data.
- **saurabhsharma2u/search-console-mcp:** 319 stars, multi-engine (GSC, Bing, GA4, AdSense), many analyses, write scope opt-in, most actively released.
- **Suganthan-Mohanadasan/Suganthans-GSC-MCP:** 169 stars, 29 analysis-heavy tools including Indexing API submits.
- **FlorianBruniaux/google-search-console-mcp:** 96 tools across GSC, GA4, CrUX, Bing and IndexNow.
- **onlymoein/google-search-console-mcp:** small (9 stars) but the most API-faithful. It has hourly data, `final`/`all`, every search type, `next_start_row` paging, 50-URL batch inspection, regex validation and API-quirk guards.
- **thein-art/mcp-server-google-search-console:** read-only by default, 20-URL batch inspection.
- Plus several smaller ones.

### Cited Findings

#### Master comparison table

| Server | Repo / package | Maintainer | Runtime | Install | Auth | Stars / last push (GitHub API, 2026-11-01) | Latest release |
|---|---|---|---|---|---|---|---|
| mcp-gsc | [github.com/AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc), PyPI `mcp-search-console` | Amin Foroutan (AminForou) | Python ≥3.11 | `uvx mcp-search-console` | OAuth Desktop client (recommended) or service account (`GSC_SKIP_OAUTH=true`) | 2,080 / 2026-09-15 | 0.4.1, uploaded to PyPI 2026-09-15 |
| mcp-server-gsc | [github.com/ahonn/mcp-server-gsc](https://github.com/ahonn/mcp-server-gsc), npm `mcp-server-gsc` | ahonn | TypeScript/Node ≥18 | `npx -y mcp-server-gsc` | Service account via `GOOGLE_APPLICATION_CREDENTIALS`. Optional remote HTTP mode (Hono) | 282 / 2026-09-04 | npm 0.3.0 (registry modified 2026-02-13). No GitHub releases |
| search-console-mcp | [github.com/saurabhsharma2u/search-console-mcp](https://github.com/saurabhsharma2u/search-console-mcp), npm `search-console-mcp` | Saurabh Sharma (saurabhsharma2u) | TypeScript/Node | `npx search-console-mcp setup`, then `npx search-console-mcp` | OAuth (recommended) or service account. Bing API key, GA4 service account, AdSense OAuth | 319 / 2026-10-21 | v2.1.4 (npm modified 2026-10-21) |
| Suganthans-GSC-MCP | [github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP](https://github.com/Suganthan-Mohanadasan/Suganthans-GSC-MCP), npm `suganthan-gsc-mcp` | Suganthan Mohanadasan | Node | `npx -y suganthan-gsc-mcp` or `claude mcp add gsc -- npx -y suganthan-gsc-mcp` | OAuth (`GSC_AUTH_MODE=oauth`, `GSC_OAUTH_SECRETS_FILE`) or service account (`GSC_KEY_FILE`) | 169 / 2026-09-27 | npm 2.5.1 (modified 2026-08-27) |
| google-search-console-mcp (gsc-mcp-tools) | [github.com/FlorianBruniaux/google-search-console-mcp](https://github.com/FlorianBruniaux/google-search-console-mcp), PyPI `gsc-mcp-tools` | Florian Bruniaux | Python ≥3.11, FastMCP | `uvx gsc-mcp-tools` | Service account (`GSC_SERVICE_ACCOUNT_PATH`) or OAuth. `CRUX_API_KEY`, `BING_WEBMASTER_API_KEY`, `GA4_PROPERTY_ID` | 21 / 2026-10-18 | 1.6.0, uploaded to PyPI 2026-10-11 |
| open-gsc-mcp | [github.com/onlymoein/google-search-console-mcp](https://github.com/onlymoein/google-search-console-mcp), PyPI `open-gsc-mcp` | onlymoein | Python | `uvx open-gsc-mcp@latest` | OAuth Desktop client (`auth login --read-only`) or service account (`GSC_SERVICE_ACCOUNT_FILE`, takes precedence) | 9 / 2026-10-28 | 1.4.0, uploaded to PyPI 2026-10-15 |
| mcp-server-google-search-console | [github.com/thein-art/mcp-server-google-search-console](https://github.com/thein-art/mcp-server-google-search-console), npm same name | Tobias Hein / artaxo agency | Node ≥22 | `npx -y mcp-server-google-search-console` or Docker | Service account (file or inline) or OAuth. OAuth takes priority | 1 / 2026-05-04 | npm 1.0.1 (modified 2026-03-09) |
| google-search-console-mcp | [github.com/acamolese/google-search-console-mcp](https://github.com/acamolese/google-search-console-mcp) | acamolese | n/a | Claude Code plugin, .mcpb bundle, Docker | n/a | 9 / 2026-10-13 | n/a |
| mcp-google-search-console | [github.com/crunchtools/mcp-google-search-console](https://github.com/crunchtools/mcp-google-search-console) | crunchtools | n/a | n/a | n/a | 0 / 2026-10-31 | n/a |
| google-search-console-mcp | [github.com/ncosentino/google-search-console-mcp](https://github.com/ncosentino/google-search-console-mcp) | Nick Cosentino | Native binaries (Go/C#) per Enrich Labs | n/a | Service account | 17 / 2026-08-05 | n/a |

Sources for the table:
- Install, auth and README details: each repo URL above.
- Stars and dates: GitHub API.
- npm and PyPI versions: `npm view` and [pypi.org](https://pypi.org/project/mcp-search-console/).
- Runtime for ncosentino: [Enrich Labs](https://www.enrichlabs.ai/blog/google-search-console-mcp-2026).

#### AminForou/mcp-gsc (most popular; Python)

[Repo README](https://github.com/AminForou/mcp-gsc)

**Tools**

| Tool | Inputs (as documented) | Access |
|---|---|---|
| `get_capabilities` | none | read |
| `list_properties` | none | read |
| `get_site_details` | site URL | read |
| `get_search_analytics` | site URL, period | read |
| `get_performance_overview` | site URL, period | read |
| `compare_search_periods` | site URL, two date ranges | read |
| `get_search_by_page_query` | site URL, page | read |
| `get_advanced_search_analytics` | site URL; filters for country, device, query and page; `sort_by`, `sort_direction` | read |
| `inspect_url_enhanced` | site URL, page URL | read |
| `batch_url_inspection` | up to 10 URLs, run concurrently since v0.4.0 | read |
| `check_indexing_issues` | site URL, list of URLs; concurrent since v0.4.1 | read |
| `get_sitemaps` | site URL | read |
| `list_sitemaps_enhanced` | site URL | read |
| `manage_sitemaps` | submit or delete | write |
| `reauthenticate` | none | auth |
| `add_site`, `delete_site`, `delete_sitemap` | n/a | destructive, disabled unless `GSC_ALLOW_DESTRUCTIVE=true` |

- The README says "20 tools", but I could only identify 18 by name. Auspia measured 21 tools on v0.3.2 ([Auspia](https://auspia.ai/blog/google-search-console-mcp-seo-servers-2026)).
- I could not confirm whether the delete action inside `manage_sitemaps` is gated.

**Data settings**
- `GSC_DATA_STATE` defaults to `"all"`, which matches the GSC dashboard. `"final"` lags 2–3 days.
- A changelog note says `row_limit` goes "up to 500" (v0.2.0). That is far below the API's 25,000.
- v0.4.0 renamed `verdict` to `index_verdict` (breaking change).
- v0.4.0 fixed period ordering in `compare_search_periods`: Period 1 is the analysed period, Period 2 the baseline.

**Bundled Cursor skills**
- `seo-weekly-report`
- `cannibalization-check`
- `indexing-audit` (top 20 pages)
- `content-opportunities` (positions 11–20, high impressions, low CTR)

**Limitations**
- The README says it works locally in Claude Desktop, not claude.ai web.
- Python ≤3.10 fails silently under GUI clients.
- Config paths must be absolute.
- v0.3.3 pins `mcp[cli]<2.0.0` because MCP SDK 2.0.0 broke fresh installs.

**Security**
- Destructive tools are off by default.
- Tokens live in the platform user config directory (v0.3.0).
- Optional remote SSE mode binds to 127.0.0.1, but no endpoint authentication is described.

#### ahonn/mcp-server-gsc (what the project uses today)

**Tools.** The source file `src/server.ts` registers 8 tools: `list_sites`, `search_analytics`, `enhanced_search_analytics`, `detect_quick_wins`, `index_inspect`, `list_sitemaps`, `get_sitemap`, `submit_sitemap`. `src/schemas.ts` defines `inspectionUrl`, `sitemapIndex` and the sitemap `feedpath` schemas. The README documents mainly `search_analytics`. — [server.ts](https://github.com/ahonn/mcp-server-gsc/blob/master/src/server.ts), [README](https://github.com/ahonn/mcp-server-gsc)

**`search_analytics` parameters.** — [README](https://github.com/ahonn/mcp-server-gsc)
- Required: `siteUrl`, `startDate`, `endDate`.
- `dimensions`: query, page, country, device, searchAppearance, date. **No `hour`.**
- `type`: web, image, video, news, discover, googleNews.
- `aggregationType`: auto, byNewsShowcasePanel, byProperty, byPage.
- `rowLimit`: default 1,000, max 25,000.
- `dataState`: `all` or `final` (default `final`).
- Filters: `pageFilter` and `queryFilter` (regex via a `regex:` prefix), `countryFilter` (ISO alpha-3), `deviceFilter`, `searchAppearanceFilter`.
- `filterOperator`: equals, contains, notEquals, notContains, includingRegex, excludingRegex.
- Built-in quick wins: `detectQuickWins` with `quickWinsConfig` defaults `positionRange [4,20]`, `minImpressions 100`, `minCtr 1%`.

**Gaps in the API surface**
- A grep of `schemas.ts` found no `startRow` and no `hourly` parameter, so the server can't page past one 25k-row request and has no hourly data. — [schemas.ts](https://github.com/ahonn/mcp-server-gsc/blob/master/src/schemas.ts)
- The only write tool is `submit_sitemap`. There is no sitemap delete or site add/delete. There is no write gating flag.

**Security: remote HTTP mode** ([remote.ts](https://github.com/ahonn/mcp-server-gsc/blob/master/src/remote.ts))
- The remote mode is Hono with streamable HTTP and reads `GOOGLE_CREDENTIALS` from bindings.
- Bearer auth applies **only if** `MCP_API_TOKEN` is set. Otherwise `/mcp` is unauthenticated.
- `CORS_ORIGIN` defaults to `*`.

**Activity.** Last GitHub push 2026-09-04 (GitHub API). npm `mcp-server-gsc` is at 0.3.0, registry modified 2026-02-13 (`npm view`).

#### saurabhsharma2u/search-console-mcp (multi-engine)

[Repo README](https://github.com/saurabhsharma2u/search-console-mcp)

**Tools**

| Tool | Parameters |
|---|---|
| `sites_list` | `engine` (all/google/bing) |
| `sites_manage` | `action` add/delete, `siteUrl`, `engine` |
| `accounts_manage` | `action` list/add_site/remove |
| `sitemaps_list`, `sitemaps_submit`, `sitemaps_delete` | `siteUrl`, `feedUrl`, `engine` |
| `analytics_query` | `siteUrl`, `engine`, `dimensions`, `metrics`, `rowLimit` |
| `analytics_compare` | `mode`: period_over_period, trends, drop_attribution |
| `analytics_anomalies` | `siteUrl`, `threshold` |
| `inspection_inspect` | `siteUrl`, `urls`, `engine` |
| `pagespeed_analyze` | `url`, `strategy`, `cwvOnly` |
| `indexing_submit` | `urls`, `method`: standard, index_now, remove |
| `indexing_status` | `type`: quota/status |
| `seo_audit` | `type`: quick_wins, striking_distance, cannibalization, low_hanging_fruit, lost_queries, recommendations, brand_vs_nonbrand |
| `seo_keywords_research` | `keywords`, `type` |
| `site_health_check` | `level`: summary/full/crawl_issues |
| `compare_engines` | `siteUrl` |
| `genai_query_insights` | `siteUrl`, `days`, `engine`, `includePages`, `minImpressions`; custom heuristic, not an official API |

About 96 legacy tool names still route through a fallback.

**Write and security**
- Writes need an explicit write scope (v2.1.4). Setup is read-only by default.
- Tokens are stored in the OS keychain, with an AES-256-GCM file fallback.
- SSE binds to 127.0.0.1 and requires a bearer token. SSE is deprecated.

**Bugs fixed in v2.1.4**
- Analytics sometimes came from the wrong property when hostnames collided (#110).
- `find_quick_wins` rejected numeric `min_impressions` (#112).
- `analytics_query` previously ignored `rowLimit` and always returned up to 1,000 rows.

#### Suganthan-Mohanadasan/Suganthans-GSC-MCP (analysis-heavy)

Tool list from the author's blog, [Suganthan](https://suganthan.com/blog/google-search-console-mcp-server/) (published 2026-03-22, updated 2026-09-27; the author sells and promotes it).

**29 tools**
- **Analysis (11):** site snapshot, quick wins (positions 4–15), content gaps (position >20), traffic drops (ranking loss, CTR collapse or demand decline), CTR opportunities, cannibalisation, content decay (three consecutive monthly declines), URL inspection, topic clusters (path aggregation), CTR vs benchmarks, advanced search analytics.
- **Image SEO (8):** includes an image page audit that fetches pages.
- **GenAI (1):** AI Mode follow-up query fragments.
- **Monitoring (2):** `check_alerts` (position drop >20, CTR drop >50%, click loss >30%) and `verify_claim`, which re-queries the API before Claude presents a number. Responses carry a `_meta` provenance field.
- **Reporting (3):** content recommendations, a markdown report written to disk, a multi-site dashboard.
- **Indexing API (4):** submit URL, batch submit (up to 200 URLs), submit sitemap, list sitemaps.

**Gaps and caveats**
- Row limits and pagination are not documented.
- The page's changelog says "20 tools" in one place and 29 in another.
- Configs using the old npm name `gsc-mcp-server` run a different maintainer's package (sofianbettayeb/gsc-mcp-server, npm 1.1.0). — [npm](https://www.npmjs.com/package/gsc-mcp-server)

#### FlorianBruniaux/google-search-console-mcp (gsc-mcp-tools; broadest)

[Repo README](https://github.com/FlorianBruniaux/google-search-console-mcp)

**Scope.** Version 1.6.0 has 96 tools (98 on the source branch with two SerpApi tools). It covers GSC, GA4, CrUX, PageSpeed, Bing and IndexNow.

**Tools**
- **Performance:** `quick_wins`, `traffic_drops`, `seo_striking_distance`, `seo_cannibalization`, `seo_lost_queries`, `analytics_anomalies`, `compare_search_periods`.
- **Search types:** `search_type_breakdown` (web, Discover, News, image, video), `discover_performance`, `news_performance`.
- **Cross-source and technical:** `page_health_score`, `content_brief`, `schema_validate`, `hreflang_audit`, `internal_links_audit`, `pagespeed_audit`.
- **Inspection and indexing:** `batch_url_inspection` (max 10). `submit_batch` sends Indexing API HTTP batches of 100; quota 200 per day, warning at 180.

**Writes.** Nine tools change remote state. The documented workflow requires reading current state, naming the exact target, explicit confirmation and a same-origin check. `GSC_MCP_TOOL_FAMILIES` can hide whole tool families.

**Known limitations**
- dataState, hourly data and pagination past 25k rows are not documented.
- Bing keyword endpoints returned HTTP 400 in a live canary.
- Traffic-drop diagnoses are "candidates, not causal proof."
- Issue #53 proposes a GSC Bulk Export importer. It is not shipped. — [Issue #53](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/53)

#### onlymoein/google-search-console-mcp (open-gsc-mcp; most API-faithful)

[Repo README](https://github.com/onlymoein/google-search-console-mcp)

**Tools**

| Group | Tools |
|---|---|
| Sites | `list_sites`, `get_site` |
| Search analytics | `query_search_analytics` (any search type, filters, `final`/`all`, paging via `next_start_row`; default 100 rows, max 25,000 per request) |
| Hourly | `query_hourly_analytics` (about the last 10 days; sets `hourly_all` automatically) |
| Per search type | `query_discover_analytics`, `query_image_analytics`, `query_video_analytics`, `query_google_news_analytics`, `query_news_tab_analytics` |
| Search appearance | `list_search_appearances`, `query_search_appearance` |
| Analyses | `compare_periods` (equal-length periods), `explain_change` (attributes traffic shifts by page, query, country, device and appearance; separates impressions from CTR; cites Google updates) |
| Inspection | `inspect_url`, `batch_inspect_urls` (up to 50 URLs, 5 concurrent, stops cleanly at quota), `audit_indexing` (sitemap-based, resumable; plus a CLI `audit SITE`) |
| Sitemaps | `list_sitemaps`, `get_sitemap` |
| Writes | `submit_sitemap`, `delete_sitemap`, `add_site`, `delete_site`; disable all with `GSC_ENABLE_WRITES=0` |

`query_news_analytics` is deprecated.

**API-quirk guards (validated before the call)**
- Rejects regex that isn't valid RE2.
- Rejects `searchAppearance` combined with other dimensions, and `notEquals`/`notContains` on it.
- Rejects the query dimension for Discover and Google News, and device for Discover.
- Validates country codes, devices and dates, and rejects future end dates.
- Clamps start dates to 16 months. Uses Pacific Time.
- Reports `first_incomplete_date` and `first_incomplete_hour`. Comparisons default to `final`.

**Limitations**
- Audits run about 50 URLs per call.
- No request indexing, no URL removal, no user management.
- OAuth logins expire every 7 days unless the OAuth app is published.

#### thein-art/mcp-server-google-search-console (read-only by default)

[Repo README](https://github.com/thein-art/mcp-server-google-search-console)

**Tools (9)**
- `list_sites`, `get_site`
- `get_search_analytics` (with comparison mode)
- `get_performance_summary`
- `inspect_url`, `batch_inspect_urls` (up to 20 URLs concurrently)
- `list_sitemaps` (with aggregated health summary)
- `submit_sitemap`
- `delete_sitemap` (requires `confirm: true`)

**Prompts:** `seo_performance_analysis`, `index_coverage_check`, `content_opportunity_analysis`.
**Resources:** `sites://list`, `sitemaps://{site_url}`.

**Write gating.** Write tools are only registered when `GSC_SCOPES` holds the full write scope. The default scope is `webmasters.readonly`.

**Activity.** Last push 2026-05-04. 1 star.

#### Others (search-result descriptions, not verified in depth)

From the [GitHub search results](https://github.com/crunchtools/mcp-google-search-console):
- **crunchtools/mcp-google-search-console:** 10 tools (4 sites, 1 analytics, 4 sitemaps including submit and delete, 1 inspection).
- **kn00m1/google-search-console-mcp:** 5 read tools. Sitemap writes are gated by `GSC_WRITE_ACCESS`.
- **andrewjpyle/google_search_console_mcp:** includes `request_indexing` through the Indexing API. Writes are limited to properties listed in `GOOGLE_SEARCH_CONSOLE_SITE_URLS`.
- **ni-c/google-search-console-mcp:** restricts actions to a `GSC_ALLOWED_SITES` allowlist.
- **ricoarrigoni/gsc-mcp-server:** read-only; `inspect_url` takes 1–10 URLs; has CSV exports.
- **acamolese/google-search-console-mcp:** 17 read-only tools, including quick wins, CTR gaps, cannibalisation, traffic-drop diagnosis and indexing, plus a white-label HTML audit.
- **metehan777/google-search-console-mcp:** listing, inspection and sitemap tools.
- **PyPI `searchconsole-mcp` (harisnadeem):** version 0.1.0, uploaded 2026-04-01. — [PyPI](https://pypi.org/project/searchconsole-mcp/)

Elsewhere:
- **mamrrez/gsc-mcp-full** is listed on Glama with 37 tools. — [Glama](https://glama.ai/mcp/servers/mamrrez/gsc-mcp-full)
- **jcd3dr/google-search-console-mcp** and **nrvmodi/google-search-console-mcp-server** appear in registries. — [Glama](https://glama.ai/mcp/servers/jcd3dr/google-search-console-mcp), [mcpservers.org](https://mcpservers.org/ko/servers/nrvmodi/google-search-console-mcp-server)

### Inferences
- ahonn has a good `search_analytics` schema (regex, all six types, dataState) but lacks pagination and hourly data. Its remote mode is open by default. The project is using only 1 of its 8 tools.
- For a plugin that must teach an agent exact API semantics, onlymoein/open-gsc-mcp exposes the most faithful raw surface. However, it has 9 stars and a single maintainer.
- AminForou has the largest user base and safe defaults. Its documented 500-row analytics cap and absent hourly/type parameters make it weaker for bulk analysis.
- Analysis-heavy servers (Suganthan, saurabhsharma2u, Florian) bake in thresholds such as positions 4–15 or 4–20. That can conflict with the project's own definitions. Keep analyses in skills over raw data rather than relying on server-side heuristics.

### Gaps
- Parameter-level schemas for AminForou, Suganthan, saurabhsharma2u and Florian were not visible in their READMEs. Run `tools/list` against each installed server to confirm names and types.
- Whether AminForou supports `type` (discover/news/image/video) and regex operators is not stated in its README.
- I did not verify last-push dates for kn00m1, andrewjpyle, ni-c, ricoarrigoni or metehan777.

## Which commercial / hosted MCPs give GSC access?

### Takeaway
Several hosted options exist, but none is better than the self-hosted ones for raw API reach:
- **Ahrefs MCP:** has a `gsc` tool group, via data imported into Ahrefs.
- **Windsor.ai:** a remote MCP. Read-only, no URL inspection.
- **Composio and Pipedream:** hosted connectors, Pipedream with 25 actions.
- **Quattr:** 58 fixed analyses; Search Console including the bulk export.
- **ContextBolt:** read-only OAuth.

Similarweb, SE Ranking, Semrush and DataForSEO provide modelled third-party data rather than your GSC.

### Cited Findings
- **Ahrefs MCP.** Its docs list a `gsc` tool group (keywords, pages, positions, performance history), enabled through the connection URL's `tools` parameter. — [Ahrefs docs: Tool Categories](https://docs.ahrefs.com/en/mcp/docs/tool-categories)
  - The underlying Ahrefs GSC v3 endpoints include performance history, positions history, pages history, performance by device, metrics by country, CTR by position, keywords, pages and anonymous queries. — [Ahrefs API reference (zh)](https://docs.ahrefs.com/zh/api/reference/gsc)
  - The property must be verified and connected inside Ahrefs. Ahrefs imports up to 16 months of history, and a few weeks of lag is described as normal. Each plan sets a per-request row cap, and calls consume API units on Lite and higher plans. — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console)
  - Auspia measured Ahrefs MCP v0.0.11 at 42 tools and noted that every tool definition loads into context on each prompt. — [Auspia](https://auspia.ai/blog/google-search-console-mcp-seo-servers-2026)
- **Windsor.ai.** Remote MCP at `https://mcp.windsor.ai`. — [Windsor.ai](https://windsor.ai/google-search-console-mcp/)
  - Search Analytics only, plus derived fields: `words_in_query`, `position_page`, `pathlevel1`–`pathlevel4`, and `branded_vs_nonbranded` (which misses brand misspellings).
  - **No URL inspection.** Sitemaps are read-only. Access is read-only.
  - Pricing: free for one source; $19/month for 3 sources; $99/month for 7.
  - In Windsor's own test, splitting a request by device returned far more queries. Only about 68% of clicks in its sample carried a query.
- **Pipedream.** Its Google Search Console toolkit lists 25 actions and 6 triggers with managed auth, including a "Compare Search Analytics" action. It notes a 400 error when the query dimension is used with Discover. — [Pipedream](https://pipedream.com/apps/google-search-console/integrations/linear)
- **Composio.** Its GSC toolkit is read/write and includes Submit Sitemap. Users can restrict scopes and actions when connecting. — [Composio](https://composio.dev/toolkits/google_search_console/framework/vscode)
- **Zapier MCP.** A blog describes building a custom "Google Search Console Data" action. I found no authoritative Zapier GSC action list. — [Goodreads-hosted blog (Patrick Zandl)](https://www.goodreads.com/author_blog_posts/25624444-propojen-google-search-console-s-mcp---komplexn-pr-vodce?tab=book)
- **Quattr (vendor ranks itself first).** — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console)
  - 58 fixed analyses over Search Console data, including the bulk export, plus GA4 and Ads. No custom SQL.
  - Similarweb MCP returns modelled estimates for any domain and does not read your GSC.
- **ContextBolt SEO.** Read-only Google OAuth scope. Its GSC tools don't spend credits. $35/month for 1,000 credits. — [ContextBolt](https://contextbolt.com/blog/google-search-console-mcp/) (vendor)
- **Others.** Ertiqah (vendor of Murkuz) names OpenSEO, Coupler.io and Windsor as hosted options. It says DataForSEO, Ahrefs, Semrush and SE Ranking read Search Console "only indirectly or not at all." — [Ertiqah](https://ertiqah.com/blog/google-search-console-mcp-servers)
- **Auspia's four-server test (12 September 2026).** — [Auspia](https://auspia.ai/blog/google-search-console-mcp-seo-servers-2026)

  | Server | Version | Tools |
  |---|---|---|
  | Ahrefs MCP | 0.0.11 | 42 |
  | mcp-gsc | 0.3.2 | 21 |
  | DataForSEO MCP | 3.1.1 | 4 (gateway) |
  | seo-mcp-server | 3.0.5 | 1 |

  A fifth third-party GSC package failed the handshake within 50 seconds.

### Inferences
- Hosted connectors suit claude.ai and ChatGPT web users. They add a third party to the data path and usually drop URL inspection, hourly data and write operations.
- The project runs inside local agent CLIs (Claude Code, Cursor, Codex, Gemini CLI, Antigravity), so a local stdio server is the natural fit.

### Gaps
- I could not get an English tool-by-tool reference for Ahrefs' `gsc` group, nor Composio's full action list or exact tool names.
- No source gave SE Ranking or Semrush GSC-via-MCP specifics.

## Which servers support regex, all search types, dataState all/hourly, >25k pagination, batch inspection, BigQuery, CrUX/PageSpeed, Indexing API?

### Takeaway
- **Regex and all six search types:** ahonn and onlymoein, explicitly.
- **Hourly data:** only onlymoein.
- **Paging with `startRow`:** only onlymoein (`next_start_row`).
- **Batch URL inspection:** onlymoein (50), thein-art (20), AminForou (10), Florian (10), ricoarrigoni (10).
- **CrUX/PageSpeed:** Florian (CrUX + PageSpeed) and saurabhsharma2u (PageSpeed).
- **Indexing API:** Suganthan, Florian, saurabhsharma2u and andrewjpyle.
- **BigQuery bulk export:** a different MCP (Suganthan's BigQuery MCP or Google's BigQuery MCP).

No server gets past the API's own "top rows only" ceiling.

### Cited Findings

**What the API itself allows** ([Search Console API, searchanalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query))
- Dimensions: country, device, page, query, searchAppearance, date, hour.
- `type`: web (default), discover, googleNews, news, image, video.
- Filter operators: contains, equals, notContains, notEquals, includingRegex, excludingRegex (RE2, max 4096 characters). Groups support `and` only.
- `aggregationType`: auto, byPage, byProperty, byNewsShowcasePanel. `byProperty` is not supported for discover or googleNews.
- `rowLimit` 1–25,000 (default 1,000). `startRow` is a zero-based offset.
- `dataState`: final (default), all, hourly_all.
- The API "doesn't guarantee every row, and returns the top rows." Results sort by clicks descending, and response metadata flags the first incomplete date or hour.

**Feature matrix**

| Capability | ahonn | AminForou | saurabh | Suganthan | Florian | onlymoein | thein-art |
|---|---|---|---|---|---|---|---|
| Regex filters | Yes (`regex:` prefix, includingRegex/excludingRegex) | not documented | not documented | not documented | not documented | Yes (RE2 validated) | not documented |
| All search types | Yes (6) | not documented | not documented | image only documented | web/Discover/News/image/video | Yes, dedicated tools | not documented |
| dataState all | Yes (default final) | Yes (default all) | not documented | not documented | not documented | Yes (final/all) | not documented |
| Hourly | No | No | No | No | not documented | Yes | No |
| `startRow` pagination | No | No (500-row cap noted) | No (rowLimit fix only) | not documented | not documented | Yes (`next_start_row`) | not documented |
| Batch URL inspection | No (single) | 10 | `urls` param | single (batch not documented) | 10 | 50 | 20 |
| Sitemap writes | submit | submit/delete (gated) | submit/delete (write scope) | submit | submit/delete (confirm) | submit/delete/site add/delete (`GSC_ENABLE_WRITES`) | submit/delete (scope-gated) |
| PageSpeed/CrUX | No | No | PageSpeed | No | CrUX + PageSpeed | No | No |
| Indexing API | No | No | Yes (standard/IndexNow/remove) | Yes (200/run) | Yes (200/day quota) | No (explicitly) | No |
| Built-in analyses | quick wins | period compare, cannibalisation skill | striking distance, cannibalisation, quick wins, anomalies, brand vs non-brand | quick wins, decay, cannibalisation, CTR, alerts, verify_claim | striking distance, cannibalisation, drops, anomalies | compare_periods, explain_change | performance summary |

Sources for the matrix: the repo READMEs cited in the previous section, plus [ahonn schemas.ts](https://github.com/ahonn/mcp-server-gsc/blob/master/src/schemas.ts).

**Other notes**
- **URL Inspection quota:** about 2,000 inspections per day and 600 per minute per property. — [onlymoein README](https://github.com/onlymoein/google-search-console-mcp); [Enrich Labs](https://www.enrichlabs.ai/blog/google-search-console-mcp-2026)
- **Search Analytics rate:** 1,200 queries per minute per site, per Auspia. — [Auspia](https://auspia.ai/blog/google-search-console-mcp-seo-servers-2026)
- **Indexing API caveats:** Google limits it to JobPosting and BroadcastEvent pages. Suganthan says other pages get processed but priority is not guaranteed. It requires Owner permission and a separately enabled Web Search Indexing API. — [Suganthan](https://suganthan.com/blog/google-search-console-mcp-server/)
- **Suganthan's BigQuery MCP Server:** queries any BigQuery dataset in natural language and adds SEO tools for GSC bulk-export data (the blog title says 32 tools). It needs the BigQuery Data Editor, Data Viewer and Job User roles. 43 stars, last push 2026-08-27. — [GitHub](https://github.com/Suganthan-Mohanadasan/Suganthans-BigQuery-MCP-Server), [Suganthan blog](https://suganthan.com/blog/bigquery-mcp-server/)
- **Bulk export caveats:** no backfill, collection starts on the day it is enabled, and anonymised queries are omitted. — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console)
- **Google's BigQuery MCP:** capped at 3,000 rows per call, so aggregate in SQL. — [Quattr](https://www.quattr.com/ai-visibility/mcp/best-mcps/google-search-console)

### Inferences
- Paging with `startRow` is the only way to get more than 25k rows from the API, and only one server (onlymoein) exposes it. Even then, Google returns top rows only.
- Real "all rows" analysis (long tail, anonymised-query share) needs the BigQuery bulk export plus a BigQuery MCP.
- Splitting requests by date, device or country raises row coverage (consistent with Windsor's device-split observation). A skill should teach that technique regardless of server.

### Gaps
- I found no source documenting `startRow` support in AminForou, Suganthan, saurabh or Florian beyond the README text. Confirm with `tools/list`.
- I found no CrUX History API support confirmed in any GSC server beyond Florian's `CRUX_API_KEY` requirement.

## Can any MCP provide crawl stats, Page Indexing report or Links report data?

### Takeaway
No. These reports are not in the Search Console API, so no server exposes them. The others cited below (Core Web Vitals report, manual actions, AI Overviews/AI Mode report, branded-query filter) are also missing from the API. Partial substitutes:
- URL Inspection, per URL (index state, canonical, crawl time, robots).
- Sitemap-driven indexing audits (onlymoein's `audit_indexing`).
- Florian's `internal_links_audit`, which crawls your own pages rather than using GSC Links data.
- CrUX or PageSpeed for Core Web Vitals.

I found no MCP that scrapes the GSC UI. The BigQuery bulk export also does not contain crawl stats or links.

### Cited Findings
- onlymoein lists what Google's API does not provide, so no server can expose it: the AI Overviews/AI Mode report, platform properties, the branded query filter, Core Web Vitals, manual actions and links. The server also cannot request indexing, remove URLs, or manage users and settings. — [onlymoein README](https://github.com/onlymoein/google-search-console-mcp)
- URL Inspection is per URL and is not a bulk export of the Page Indexing report. Some hosted connectors omit inspection entirely. — [Enrich Labs](https://www.enrichlabs.ai/blog/google-search-console-mcp-2026)
- A targeted search found no GSC MCP server exposing Crawl Stats, and none of the results showed crawl stats in the bulk export. — WebSearch "GSC MCP BigQuery bulk export crawl stats indexing API MCP server" (no source returned; recorded as negative evidence)
- saurabhsharma2u's `site_health_check level=crawl_issues` is built from available API data (inspection and sitemaps), not the Crawl Stats report. Its README does not claim Crawl Stats access. — [saurabhsharma2u README](https://github.com/saurabhsharma2u/search-console-mcp)

### Inferences
- The plugin's skills should state plainly that crawl stats, page indexing totals, links and CWV-report numbers cannot be reached through the MCP. That prevents the agent from inventing them.
- Substitutes for those reports: sitemap plus batch inspection sampling, server logs for crawl, CrUX API for CWV, and a third-party link index for links.

### Gaps
- I did not find a public browser-automation MCP for GSC UI exports. Any such tool would raise terms-of-service and credential-handling concerns.

## Practitioner write-ups, workflows and pitfalls

### Takeaway
Practitioners use GSC MCP for weekly reports, striking-distance and quick-win lists, cannibalisation checks, decay and traffic-drop diagnosis, and indexing audits. The recurring pitfalls:
- Models invent or misread numbers.
- The 25k top-rows cap and anonymised queries mean rows don't sum to totals.
- `final` data lags while `all` data is partial.
- The property format is wrong (`sc-domain:` vs URL-prefix).
- The service account was never added to the property, so results come back silently empty.
- Tool-count context bloat.
- Write scopes are broader than needed.

Most write-ups are by vendors.

### Cited Findings
- **Suganthan's workflows:** "Check for any SEO alerts" then "Generate a performance report"; quick wins then content recommendations; traffic drops then decay; cannibalisation; multi-site dashboard.
  - Pitfalls he lists: `sc-domain:` vs full-URL property format "breaks everything silently", Owner permission needed for the Indexing API, and Claude can misread raw values. He recommends `verify_claim` and the `_meta` provenance field.
  - [Suganthan](https://suganthan.com/blog/google-search-console-mcp-server/)
- **Auspia's checklist:** read the OAuth scope (read-only is enough for reporting), check what data leaves the machine, run an empty-response test so the agent can't invent explanations for missing data, use one server per data source, keep reporting definitions in an instruction file outside the server, and verify the first week against the GSC UI. — [Auspia](https://auspia.ai/blog/google-search-console-mcp-seo-servers-2026)
- **Enrich Labs:** models can invent rankings, so ask for raw tool output. An empty property list usually means the wrong account or an unadded service account. A 403 usually means the API is not enabled or a scope is missing. Pin server versions. — [Enrich Labs](https://www.enrichlabs.ai/blog/google-search-console-mcp-2026)
- **ContextBolt:** the most common setup failure is not adding the service account as a user. Auth succeeds but every query returns empty. Averaged positions mislead, so check country splits. Low-volume queries are hidden, so query rows don't sum to totals. Suggested starter queries: positions 5–20 with more than 100 impressions, and CTR under 1%. — [ContextBolt](https://contextbolt.com/blog/google-search-console-mcp/) (vendor)
- **Ertiqah:** check whether a server requests `dataState: all`, since otherwise data lags the dashboard 2–3 days. Several early GSC servers have gone dormant. — [Ertiqah](https://ertiqah.com/blog/google-search-console-mcp-servers) (vendor)
- **Windsor.ai:** only about 68% of clicks in its sample had a query attached, and splitting by device surfaced far more queries. — [Windsor.ai](https://windsor.ai/google-search-console-mcp/) (vendor)
- **AminForou's bundled skills:** weekly report, cannibalisation check, indexing audit of the top 20 pages, and content opportunities (positions 11–20, high impressions, low CTR). This is the same server-plus-skills pattern the project is building. — [AminForou README](https://github.com/AminForou/mcp-gsc)
- **Other practitioner and vendor guides:**
  - [Trevor Lasn](https://trevorlasn.com/blog/google-search-console-mcp-claude-code)
  - [RightBlogger](https://rightblogger.com/blog/google-search-console-claude-2)
  - [alloq.digital](https://alloq.digital/en/blog/google-search-console-mcp/)
  - [SureVisible](https://surevisible.substack.com/p/the-game-is-inside-the-assistant)
  - [ContextBolt Claude SEO experiment](https://contextbolt.com/blog/claude-seo-experiment/)

  The search summary drew a general theme from these: GSC is treated as the one trusted first-party source, and humans still verify numbers. I did not open them individually.
- **Search Engine Land:** "How to use MCP to get more data from the tools you already use" returned HTTP 403 and was not read. — [Search Engine Land](https://searchengineland.com/mcp-data-tools-484650)

### Inferences
- The plugin's skills should require four things:
  1. Quote raw tool output for every number.
  2. Use `dataState=final` for comparisons and `all` only for "latest" views, stating the incomplete date.
  3. Split by date, device or country to beat the top-rows cap.
  4. Treat an empty result as a configuration or permission signal, not "no traffic."
- **Recommendation for the project:**
  - **Primary server.** Keep ahonn short-term for compatibility but plan a move.
    - The best raw-API surface is onlymoein/open-gsc-mcp: hourly data, paging, all types, 50-URL batch inspection, quirk guards, write kill-switch. Risk: 9 stars and one maintainer, so pin the version.
    - The safest mainstream choice is AminForou/mcp-gsc: 2,080 stars, gated destructive tools, OAuth. Its documented 500-row cap and missing hourly/pagination support make it weaker for bulk data.
  - **Add-ons.** If the plugin needs Indexing API, CrUX or PageSpeed, add Florian's gsc-mcp-tools or saurabhsharma2u, restricted with `GSC_MCP_TOOL_FAMILIES` or read-only scope to limit context bloat and write risk.
  - **Bulk export.** For long-tail and history work, add Google's BigQuery MCP over the GSC bulk export.
  - **Security.** Run read-only scope (`webmasters.readonly`) by default. Never expose ahonn's remote mode without `MCP_API_TOKEN` (its CORS defaults to `*`).
- **Gaps no server covers:** crawl stats, Page Indexing report totals, Links report, Core Web Vitals report (use CrUX instead), manual actions and security issues, AI Overviews/AI Mode report, branded-query filter, user/permission management, URL removals, and more than 25k rows beyond the API's top-rows ceiling. True completeness needs the BigQuery bulk export, which itself has no backfill and omits anonymised queries.

### Gaps
- I found no controlled study measuring hallucination rates for GSC MCP workflows. The evidence is anecdotal.
- I could not access Chris Long's or Aleyda Solis's GSC MCP posts in this pass. LinkedIn and YouTube content was not searched directly.
