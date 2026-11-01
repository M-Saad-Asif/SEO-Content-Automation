"""Google Search Console suite: the data layer behind the MCP hub's Search Console skills.

One store per website (sites/<slug>/gsc/), filled by either route:
  - API route: a read-only service account or OAuth user file (`api.py`), paged past 25k rows;
  - MCP route: the agent calls a Search Console MCP server and runs `seo.py gsc ingest` (`mcp.py`);
  - UI route: reports the API cannot reach (Crawl Stats, Page indexing, Links, CWV, the Gen-AI report) are pasted
    or exported by the user and ingested the same way.

Every pipeline plugin and every agent reads the same data through the bus (`bus.Console`): `gsc_insights`,
`query_map`, the plan, internal links, the write brief, the batch queue and `seo.py gsc data` all ask it.
Analyses (`analyze.py`, `indexing.py`, `crawl.py`) are pure functions over rows, so the API, MCP and UI routes
give the same answers. Nothing here changes a Search Console property: writes are proposals for the user.
"""
