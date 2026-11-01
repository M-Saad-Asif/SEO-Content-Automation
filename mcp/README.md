# MCP servers for the connector plugins

**The MCP hub is `plugins/mcp_hub/`.** It holds the registry of servers (`servers.yaml`) and the skills that say when, why and how to use each tool. Google Search Console has its own skill, playbooks and data suite (`plugins/mcp_hub/gsc/SKILL.md`, `seo.py gsc ...`, `/page-seo <website> | gsc`). This file covers installing servers.

The connector plugins have two routes:

- **Script:** they call the APIs themselves with keys in `.env`.
- **MCP:** your agent calls an MCP server and stores the result with `seo.py ingest`.

Use whichever you have. Both feed the same analysis (see each plugin's `SKILL.md`).

## Install

1. Copy `mcp.example.json` and fill in your credentials. Never commit the filled copy.
   - **Cursor:** save it as `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` in a project.
   - **Claude Code:** save it as `.mcp.json` in the project, or run `claude mcp add <name> -- npx -y <package> ...`.
2. Node.js must be installed (`npx`).

| Server | Package | Credentials | Tool used | Plugin |
|---|---|---|---|---|
| Google Search Console | `open-gsc-mcp` pinned (`uvx open-gsc-mcp@1.4.0`, `GSC_ENABLE_WRITES=0`), or `mcp-search-console` (AminForou). `mcp-server-gsc` (ahonn) works, but it has no paging past 25k rows and no hourly data | OAuth read-only login, or a service account added as a user on the property | Search analytics, URL inspection, sitemaps (read-only): `seo.py gsc plan <client>` prints every call | The Search Console suite (`sites/<client>/gsc/`), `gsc_insights` and everything downstream |
| DataForSEO (official) | `dataforseo-mcp-server` | API login and password (not the dashboard login) | Related keywords, keyword overview, SERP organic with PAA click depth | `keyword_research` |
| Microsoft Clarity (official) | `@microsoft/clarity-mcp-server` | Project API token (Settings → Data Export) | `get-clarity-data` (numOfDays 1–3, dimension URL) | `clarity_ux` |
| Reddit | Any Reddit MCP that uses Reddit's official API | Reddit app credentials | Search and comments | `reddit_voice` |

Use read-only tools only. For example, never call `submit_sitemap` or anything that changes a property. The full never-list and the approval rules are in `plugins/mcp_hub/gsc/reference/approvals.md`.

Search Console without an MCP server: put `GSC_SERVICE_ACCOUNT_JSON` (or `GSC_OAUTH_JSON`) in `.env` and `pip install google-auth`. Then `seo.py gsc pull <client>` fills the same store directly from the API.

## From MCP output to the pipeline

1. Run `seo.py research <brief>`. The pack's "Connectors not used this run" lists what is missing.
2. Call the MCP tool. Save the result in the raw format given in the plugin's `SKILL.md`:

   | Plugin | Required top-level key |
   |---|---|
   | `gsc_insights` | `page_rows` |
   | `keyword_research` | `keywords` |
   | `clarity_ux` | `metrics` |
   | `reddit_voice` | `threads` |

3. Run `python scripts/seo.py ingest <run> <plugin> <file.json>`. This re-runs that plugin and everything downstream (query_map, semantic_graph) and rebuilds `writer_pack.md`.

## Rate limits and costs

| Server | Limit or cost |
|---|---|
| Clarity | 10 Data Export requests per day per project; last 1–3 days only |
| DataForSEO | Paid per task. The script route caches responses for 7 days |
| Search Console | Data lags about 2–3 days. The plugins use the last 90 days ending 3 days ago |
