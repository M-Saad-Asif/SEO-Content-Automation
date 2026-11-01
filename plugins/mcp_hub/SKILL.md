---
name: seo-mcp-hub
description: The MCP hub of the page-SEO pipeline. Hosts the MCP servers the pipeline uses (Google Search Console first, plus DataForSEO, Microsoft Clarity and Reddit) and the skills that say when, why and how to use each tool. Use when connecting an MCP server, fetching data through one, or when a task names an MCP route.
---

# MCP hub

The hub has three parts per server:

1. **A registry entry** in `servers.yaml`: what the server is for, the recommended package and version, how it authenticates, the tools allowed, the tools never used without the user's yes, and where its data enters the pipeline.
2. **A skill folder** that says when, why and how to use each tool the way an experienced practitioner would. Search Console's is `gsc/SKILL.md`, with its playbooks, UI checklists and references.
3. **A data route.** MCP output is stored by a script, never pasted into prose. After that, every plugin reads the same data. For Search Console that is the per-site store `sites/<client>/gsc/` and the bus `seolib.gsc.bus.Console`.

## Rules for every MCP server

| Rule | Why |
|---|---|
| Run the server's tool list first and match tools by capability, not by name | Community servers rename tools between versions |
| Read-only by default. Writes (sitemap submit/delete, site add/delete, request indexing, anything that changes an account) only on the user's explicit yes, one action at a time | One wrong write can hide a site or waste a quota that can't be undone |
| Every number comes from tool output and is saved with the ingest command | Models invent plausible numbers; the store is the single source |
| An empty answer is a setup problem until proven otherwise (wrong property format, account without access, API disabled) | "No data" almost never means "no traffic" |
| Respect quotas: Search Console URL Inspection 2,000/day per property; Clarity 10 requests/day; DataForSEO is paid | A loop burns a day's quota in minutes |
| Pin server versions; never expose a server's remote HTTP mode without its auth token | Supply-chain and open-endpoint risk |

## Where each server's data goes

| Server | Command | What reads it |
|---|---|---|
| Google Search Console | `seo.py gsc plan <client>` → tools → `seo.py gsc ingest <client> <dataset> <file>`; in a page run, `research/raw/gsc_insights.json` | The audit, `gsc_insights`, `query_map`, the plan, internal links, the write brief, the batch queue, `seo.py gsc data` |
| DataForSEO | `seo.py ingest <run> keyword_research <file>` | `keyword_research`, `query_map` |
| Microsoft Clarity | `seo.py ingest <run> clarity_ux <file>` | `clarity_ux`, the writer pack |
| Reddit | `seo.py ingest <run> reddit_voice <file>` | `reddit_voice` |

## Adding a server

1. Add its entry to `servers.yaml`.
2. Write `<server>/SKILL.md`: what each tool is for, when to use it, its thresholds, and its never-list.
3. Give it a route into a store or a plugin's `research/raw/<plugin>.json`.
4. Make the plugins that need it read that store, so its data reaches every stage that can use it.
