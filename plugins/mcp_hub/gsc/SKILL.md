---
name: seo-gsc
description: Google Search Console through MCP or the API, used the way experienced, results-driven SEOs use it. Covers indexing, URL inspection and rendering, crawl stats and crawl budget, robots.txt, performance (queries, pages, positions, CTR, regex, devices, countries, appearance, Discover, News, image, video, hourly), AI Overviews/AI Mode visibility, Core Web Vitals, links, enhancements, manual actions and settings. Use for a site audit, a page's Search Console data, rewrite queues from Search Console, crawl-waste and indexing fixes, or whenever a task needs Search Console data.
---

# Google Search Console

Search Console has four API resources: Search Analytics, URL Inspection, Sitemaps and Sites. Everything else (Page indexing totals, Crawl Stats, robots.txt report, Links, Core Web Vitals, Enhancements, Manual actions, Removals, the live test and rendered HTML, Request indexing, the branded filter, query groups, annotations, the Generative AI report) is **UI-only**. This skill:

- uses the reachable part fully, through the store and its analyses;
- rebuilds the rest from other data (URL Inspection sampling, live fetches, CrUX) or asks the user for an export (`ui_checklists.md`);
- never invents a number it cannot get.

Full evidence and sources: `docs/gsc_research/reports/Search Console expert playbook.md`.

## Setup: two routes into one store

| Route | How | Gives |
|---|---|---|
| API (best) | `GSC_SERVICE_ACCOUNT_JSON` (service-account key; add its email under Settings > Users) or `GSC_OAUTH_JSON` (authorized-user file) in `.env`; `pip install google-auth` | `seo.py gsc pull` pages past 25k rows; `seo.py gsc inspect` runs URL Inspection on up to 1,900 URLs a day |
| MCP | A server from `../servers.yaml` (recommended: open-gsc-mcp pinned, or AminForou's mcp-search-console), read-only | `seo.py gsc plan <client>` prints every tool call; `seo.py gsc ingest <client> <dataset> <file>` stores each answer |

**Property format.**
- A Domain property is `sc-domain:example.com`.
- A URL-prefix property is `https://www.example.com/`, with the trailing slash.
- Set `gsc_property:` in the client profile when it isn't the Domain property.
- Wrong format, an account without access, or the API disabled gives an empty answer or a 403/404. That is not "no traffic".

## The one command (operator)

`/page-seo <website> | gsc` pulls (or prints the MCP fetch task), inspects, audits and writes:
- `sites/<client>/gsc/audit.md`, the readable audit;
- `sites/<client>/gsc/actions.json`, typed actions:
  - `rewrite` and `new` can go to the page pipeline;
  - `fix`, `merge` and `ask` are for the user or a developer;
  - `approval` actions never run without the user's yes.

Related requests:

| Request | What it does |
|---|---|
| `/page-seo <website> \| gsc queue optimizer 10` | Turns the actions into a `/page-seo` batch. Each page carries its Search Console reason and target queries as instructions. Kinds: `optimizer`, `questions`, `new`, `decay`, `ctr`, `ccni` |
| `/page-seo <website> \| gsc crawl <export file>` | Crawl Stats analysis |
| `/page-seo <website> \| gsc page <url>` | One page's full picture |

## Data for any agent or plugin (the bus)

`seo.py gsc data <client> <view> [--page URL] [--query Q] [--topic T] [--json]`.

Views: `summary`, `page`, `query`, `topic`, `optimizer`, `striking`, `ctr`, `questions`, `conversational`, `site_operator`, `zero_click`, `emerging`, `alignment`, `intent`, `brand`, `cannibalisation`, `decay`, `decoupling`, `device`, `country`, `appearance`, `coverage`, `trend`, `curve`, `index`, `changes`, `impact`.

In Python, `seolib.gsc.bus.for_brief(brief)` returns the same views. Inside a page run, `gsc_insights` gathers them for the page and passes them on:

- **To `query_map`:** questions, striking-distance and should-rank queries become headings or in-section answers.
- **To the plan and internal links:** client pages ranking for the topic become link targets.
- **To the write brief:** which wording to keep and which queries the title and meta description must answer.
- **To lint:** striking queries dropped, and weak-CTR titles.
- **To the report:** index state, decay, device gap, anonymised share, and link sources (trafficked pages that should link *into* the new page).

Finished pages are logged in `changelog.json` with their baseline, for `impact`.

## Which playbook, when

| Situation | Playbook | Command |
|---|---|---|
| Pages not indexed; any deploy, migration or section drop | `playbooks/indexing.md` (U-A, IX1–IX15) | `seo.py gsc inspect`, then `data index` |
| Pages on positions ≤20 (or ≤30) that could climb | `playbooks/page_optimizer.md` (U-B, PF1, PF2, PF3, PF6, PF7) | `data optimizer`, `data striking`, `data ctr` |
| Question and conversational queries | `playbooks/questions.md` (U-C, PF4, PF5) | `data questions`, `data conversational` |
| Crawl budget, crawl waste, robots.txt | `playbooks/crawl.md` (U-D, CR1–CR12) | `gsc crawl <export>`, `gsc robots` |
| Is Google seeing the content? (JS, CDN, soft 404) | `playbooks/render.md` (U-E) | `gsc render <url>` |
| Site trends, decay, cannibalisation, segments, Discover, News, image, video | `playbooks/performance.md` (PF8–PF31) | `data decay`, `data cannibalisation`, `data coverage`… |
| AI Overviews / AI Mode visibility | `playbooks/ai_visibility.md` (AI1–AI5) | `data decoupling`, `data zero_click`, plus the Gen-AI export |
| Traffic drop, core update, migration | `playbooks/diagnostics.md` (PF11, PF12, OP4, SM1, SM2) | `data trend`, `data decay` |
| CWV, mobile-first, links, structured data, shopping, settings | `playbooks/experience_links.md` (EX, LK, EN, OP) | CrUX/PSI, UI exports |
| Anything UI-only | `ui_checklists.md` | `gsc ingest <client> ui_<report> <file>` |

## Guardrails (always)

1. Quote every number from the store or tool output, never from memory. State the window and whether data is `final`.
2. State the caveats that apply (`reference/caveats.md`):
   - about half of clicks sit on anonymised queries;
   - the `num=100` change in September 2025;
   - the impression-logging bug from 13 May 2025 to 27 Apr 2026 (use clicks across it);
   - AI Mode is counted in Web, and AI Overview links share one position.
3. Use impression-weighted positions per page or query, never site averages. Opportunity work is non-brand. The brand regex comes from the client profile; add misspellings as `client_aliases`.
4. CTR expectations come from the site's own curve (`data curve`), never a fixed industry table.
5. Never do without the user's explicit yes (`reference/approvals.md`):
   - robots.txt changes;
   - Removals;
   - sitemap submit/delete;
   - Request indexing;
   - Validate fix;
   - site/user changes, disavow, Change of address;
   - the Generative-AI opt-out;
   - mass noindex/redirects.

   Propose each with its test and its diff.
6. Refuse the myths in `reference/myths.md`. For example:
   - spamming Request indexing;
   - robots.txt to deindex;
   - blocking `/_next/static`;
   - "Other file type means client-side rendering";
   - driving 404s to zero.
7. Where experts disagree, use the defaults in `reference/experts.md`.
