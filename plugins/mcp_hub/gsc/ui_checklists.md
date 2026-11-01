# UI-only reports: what to ask the user for, exactly

The API can't reach these reports. Ask the user to open each screen, set the filter, and export or paste. Store each one with `seo.py gsc ingest <client> <dataset> <file>`. Then the audit uses it on its next run (`/page-seo <site> | gsc`).

| Dataset | Screen and steps | Feeds |
|---|---|---|
| `ui_crawl_stats` | **Settings → Crawl stats → Open report** (root Domain property). Copy the summary (total requests, download size, average response time) and Host status. Then open each breakdown — **By response, By file type, By purpose, By Googlebot type** — and for each row, its example URLs (export each table, or paste). For "Other file type", **always** include the examples. A folder of CSVs works: `gsc crawl <client> <folder>` | `crawl.md` U-D, CR1–CR12 |
| `ui_page_indexing` | **Indexing → Pages.** Note the "last updated" date. Copy the chart's indexed/not-indexed totals and every "Why pages aren't indexed" row (reason, source, count). Switch the filter to **All submitted pages** and copy again. Export the examples of each reason you want fixed | `indexing.md` U-A, IX12 |
| `ui_links` | **Links → Export external links** ("Latest links" + "More sample links") and the **Internal links** "Top linked pages" table | `experience_links.md` LK1–LK3 |
| `ui_cwv` | **Experience → Core Web Vitals → Mobile** and **Desktop**: each issue's URL groups and status | EX1 |
| `ui_genai` | **Performance → Search generative AI** (and Discover generative AI): **Pages** tab, last 3 months, export | `ai_visibility.md` AI1 |
| `ui_manual_actions` | **Security & manual actions → Manual actions** and **Security issues**: paste what each says ("No issues detected" counts) | `diagnostics.md` SM1, SM2 |
| `ui_enhancements` | **Enhancements** and **Shopping**: each report's valid/invalid counts and its issues | EN2, EN4 |
| `ui_robots` | **Settings → robots.txt**: each host, its fetch status, last fetched | CR2, CR7 |
| `ui_branded` | **Performance → Search results → filter "Brand: Branded"**, then "Non-branded": the two click and impression totals (top-level properties only) | PF22 check against the regex |
| View crawled page HTML | **URL Inspection → <url> → View crawled page → HTML** (or **Test live URL → View tested page**): paste into a file | `render.md` U-E |
| Multimodal | **Performance → Search type: Web → Multimodal**: export pages | PF30 |
| Query groups | **Insights → Queries → Query groups**: copy the group names | PF23 |

Never ask for passwords or tokens. Never log into Search Console on the user's behalf. The user exports; the agent ingests.
