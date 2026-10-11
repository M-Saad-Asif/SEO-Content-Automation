# MCP servers for the connector plugins

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
| Google Search Console | `mcp-server-gsc` (community; check its README for the credential variable) | Service-account JSON added as a user on the property | `search_analytics` | `gsc_insights` |
| DataForSEO (official) | `dataforseo-mcp-server` | API login and password (not the dashboard login) | Related keywords, keyword overview, SERP organic with PAA click depth | `keyword_research` |
| Microsoft Clarity (official) | `@microsoft/clarity-mcp-server` | Project API token (Settings → Data Export) | `get-clarity-data` (numOfDays 1–3, dimension URL) | `clarity_ux` |
| Reddit | Any Reddit MCP that uses Reddit's official API | Reddit app credentials | Search and comments | `reddit_voice` |

Use read-only tools only. For example, never call `submit_sitemap` or anything that changes a property.

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
