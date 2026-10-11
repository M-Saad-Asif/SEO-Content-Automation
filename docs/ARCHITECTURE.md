# Architecture: a senior SEO as a plugin pipeline

Every stage of the work a senior SEO does is a plugin in `plugins/<name>/`, run by a small harness (`scripts/seolib/harness.py`). The idea comes from DeepSeek Harness, where every capability is a plugin that can be swapped. The pipeline stays tool-agnostic, so it runs in Claude Code, Cursor, Codex and Antigravity with no extra model API keys.

## The run, end to end

`python scripts/seo.py next <brief>` is the only entry point (`scripts/seolib/driver.py`). It runs every script step itself and prints one agent task at a time; the agent confirms judgement tasks with `seo.py done`. State lives in `runs/<run>/state.json`.

| # | Stage | Who | Output |
|---|---|---|---|
| 0 | Page intake (a page address in the request): page type and main keyword from the page itself | script | brief `page_type`, `target_query`, `page_intake` |
| 1 | Research scripts: the plugins below, in dependency waves | script | `writer_pack.md`, `research_plan.md`, `fact_sheet.json`, `link_map.json` |
| 2 | Research (`plugins/deep_research`) | researcher agent | facts via `--add-fact`, `research/dossier.md` (gated: every shared topic T1..Tn accounted for, every cited fact id real) |
| 3 | Expert notes, pass 1 (`plugins/expert_review`, deep) | expert agent | `expert_notes.md` |
| 4 | Outline (WORKFLOW 3, deep) + outline check | writer + script | `outline.md` |
| 5 | Draft (WORKFLOW 4) | writer | `draft.md` |
| 6 | Lint (60+ rules) → fix rounds (max 5) | script → writer | `lint.json` |
| 7 | Review sheet + lint warnings (WORKFLOW 6b) | script → writer | `review.md` |
| 8 | Validate: re-lint, live links (max 3 rounds) | script | `final.md`, `report.md` |
| 8b | Expert read, pass 2: independent opinion on the finished page with today's news and business fit (deep) | expert agent | `expert_read.md` |
| 9 | Editor's pass (WORKFLOW 7b): rubric, claim ledger, every expert-read item applied | writer as hostile editor | `editor.md`, `draft.md` |
| 9b | Fact-check (`plugins/fact_check`): every factual sentence against the page it credits | fresh fact-checker agent | `verify.md`, `draft.md` |
| 9c | Internal links (`plugins/internal_links`): 3–6 contextual links on each target's main term (Koray's rules) | script ranks, linker places | `internal_links_plan.md`, `internal_links.md` |
| 10 | Re-validate, date stamp, eval | script | `final.md` (`updated:`), `eval.md` |

## The research plugins (stage 1)

Run in waves by `scripts/seolib/harness.py`; plugins in one wave run in parallel. Observed order on a deep run: **foundation, serp_intel** → **competitor_scrape, site_profile, reddit_voice, gsc_insights, current_page** → **info_gain, keyword_research, official_facts** → **query_map** → **semantic_graph** → **topic_outline, research_plan**.

| Plugin | What a senior SEO would do | Output |
|---|---|---|
| `foundation` | Read the client page, sitemap and products; verify official facts; find the client's related pages | `fact_sheet.json`, `link_map.json` |
| `serp_intel` | Read the SERP for the right country: intent, format, who ranks, PAA, related searches; decide YMYL (authorities ranking, or a money/health/legal/safety topic) | `research/serp_intel.json` |
| `competitor_scrape` | Read the top pages' outlines and content (rendered via Spider when configured; other-language pages and scraped clones skipped) | `research/competitor_scrape.json` |
| `site_profile` | Read the client's own pages for its voice | `research/site_profile.json` |
| `official_facts` | Pull verbatim facts from the authorities for the topic, with scope | facts in `fact_sheet.json` |
| `info_gain` | Find what the top pages lack: forums, reviews, first-hand experience | `research/info_gain.json` |
| `query_map` | Decide for each related query: H2 here, inside a section, link to an existing page, separate page, or drop | `research/query_map.json` |
| `semantic_graph` | The knowledge graph of the topic in this market (`seolib/graph.py`, plain rules, spaCy sharpens types): typed entities with aliases and definitions, attribute values with the sites that state them, relationships; plus consensus figures and heading topics | `research/semantic_graph.json` → `knowledge_graph.md` |
| `topic_outline` | Every PAA, related, Search Console and competitor question placed in the sections the ranking pages share, macro to micro, each with its entities, figures and facts | `research/topic_outline.json` → `topic_outline.md` |
| `research_plan` | Turn all of it into the researcher's brief: questions, five reader perspectives, shared topics T1..Tn, figures to trace, client pages, where to look | `research_plan.md` |

Agent stages ship a `SKILL.md` (`deep_research`, `expert_review`, `fact_check`); the writer follows `RULES.md` and the WORKFLOW section the task names.

### Connector plugins (data superpowers)

| Plugin | Source | When it runs | Output used for |
|---|---|---|---|
| `current_page` | The live page | `task: rewrite` | What exists today; what must be kept |
| `gsc_insights` | Google Search Console | Rewrite (and new pages: which client pages already rank for the topic) | Queries kept, striking distance, weak-CTR titles, gaps, cannibalisation |
| `keyword_research` | DataForSEO | When configured | Volumes, intent, related keywords, PAA at click depth 2 |
| `clarity_ux` | Microsoft Clarity | `task: rewrite` | Scroll, dead-click, rage-click and quickback fixes |
| `reddit_voice` | Reddit official Data API | Deep mode | First-hand experience for info_gain |

Each connector has two routes into one analysis:

- **Script:** the plugin calls the API with keys in `.env`.
- **MCP:** the agent calls an MCP server ([mcp/README.md](../mcp/README.md)) and stores the raw result with `seo.py ingest <run> <plugin> <file>`. That re-runs the plugin and everything downstream.

`connectors: auto` (the default) uses whatever is configured. A connector with neither route is logged as a decision, and the run continues without it.

Every plugin, script or agent, ships a full `SKILL.md`: what it analyses, rules per intent and page type, what it keeps and rejects, edge cases and what to do, and how to run it alone. `seo.py test` fails if a plugin lacks one.

`python scripts/seo.py plugins` lists them. The pack builder (`scripts/seolib/pack.py`) merges the results into `writer_pack.md`, the writer's data file.

## Plugin contract

Each `plugin.yaml` declares:

| Field | Meaning |
|---|---|
| `name` | The plugin's name |
| `kind` | `script` or `agent` |
| `description` | What it does |
| `needs` | The plugins it depends on |
| `modes` | `deep`, `quick` or both |
| `budget_s` | Its time budget in seconds |
| `outputs` | The files it writes |

A script plugin exposes `run(ctx) -> dict`. `ctx` gives:

- `brief`
- `rd`, the run folder
- `mode` and `deep()`
- `load(name)`, which returns another plugin's output
- `decide(text)`, which logs a decision
- `credits`, the Serper credit counter

An agent plugin ships a `SKILL.md`. To swap a stage, replace its folder. To add one, add a folder with a manifest and wire it in through `needs`.

## Data sources and limits

- **Google SERP** comes through Serper.dev under your key, kept in `.env` and git-ignored. Calls are cached for 3 days. A deep run costs about 10–15 credits on first fetch and 0 when cached; a quick run about 4.
- **Markets.** The market (locale) is decided without asking: the operator's words ("for Australian readers"), else the target page's own signals (og:locale, html lang, domain ending, currency), else the client profile. Every search uses Google's own country code for it (the UK is `uk`, not ISO `gb`).
- **Question data in every market.** The results API (Serper) returns People Also Ask and related searches only for the UK and the US. Each search self-checks: rankings with no questions are retried with the country's alternative code. For other English markets the questions are borrowed from the UK, then US, results and filtered for another market's currency and people; for every market, the market's own question searches (autocomplete with the language's question words) are collected in deep mode and lead when the PAA was borrowed. Competitors' questions come from their rendered pages. Google is never scraped around its own blocks.
- **Competitor pages** are rendered through Spider (one page per site, cached 3 days) and fall back to a direct fetch; `competitor_scrape.json` records `via` for each page, and every page feeds the knowledge graph.
- **Sites that block scripts** are recorded and skipped, never worked around.
- **Fact verification:** facts are verified on official pages by script, or captured by the agent's browser. Knowledge-graph claims are leads. Numbers on YMYL pages must be verified facts. Non-YMYL pages may use a competitor number only when 3+ domains agree.
- **Semantic analysis** uses spaCy (`en_core_web_sm`) when it loads. Where it can't (missing, or blocked by Windows Application Control), tokens fall back to plain rules and the entity graph is skipped; `seo.py doctor` says which.

## Modes

| | Deep (default) | Quick |
|---|---|---|
| Top pages read | 10 | 5 |
| PAA expansion | yes | no |
| SERP-overlap check for related queries | yes | no (heuristic) |
| Information-gain searches | yes | no |
| Outline gate | yes | no |
| Typical total | 3–6 min | 2–4 min |
