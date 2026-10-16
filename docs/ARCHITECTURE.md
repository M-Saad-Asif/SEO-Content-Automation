# Architecture: a senior SEO as a plugin pipeline

Every stage of the work a senior SEO does is a plugin in `plugins/<name>/`, run by a small harness (`scripts/seolib/harness.py`). The idea comes from DeepSeek Harness, where every capability is a plugin that can be swapped. The pipeline stays tool-agnostic, so it runs in Claude Code, Cursor, Codex and Antigravity with no extra model API keys.

## The run, end to end

`python scripts/seo.py start <request>` performs intake; `site` prepares reusable website context/queues, and `batch` resumes queues. `python scripts/seo.py next <brief>` drives an individual page (`scripts/seolib/driver.py`). It runs every script step itself and prints one agent task at a time; the agent confirms judgement tasks with `seo.py done`. State lives in `runs/<run>/state.json`.

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

## The flow (one mode, every run)

`next`: research scripts (≤ 45 s) → the page plan (`seolib/plan.py`) and `write_brief.md` (`seolib/writebrief.py`) → one DRAFT task, the plan's parts written at the same time by parallel writers and joined by `next` → one combined FIX task (planned headings missing, lint blocks, claims no fact carries; warnings go to the report, not back to the writer) → validate → eval → DONE. Target: under five minutes. At most two fix rounds. The stage table above is the older agent sequence; its expert, fact-check and internal-link work now lives in the plan (page job, facts and links per heading) and in the scripted checks.

**Quality gates, cheapest first.** The writer card prevents (Koray's rules, humanization, page job); `seolib/autofix.py` rewrites the mechanical cases by script before the check ("if" second, fluff words), so they never cost a round; lint blocks go back in the one fix task; warnings stay in the report. Koray Tuğberk Gübür's rules win any conflict (`docs/RULES_MAP.md` maps all 128 lint rules and every RULES section to his). Humanization (`plugins/humanize`, lint HU01–HU08) applies the University of Maryland / Google DeepMind findings (StoryScope, IdeaLens). At DONE, `seolib/schema.py` writes `schema.json` (JSON-LD naming the page's central entity and the entities it covers).

**Parallel writers in every tool.** `install.py` installs the same `seo-writer` sub-agent into each tool in its own format: Claude Code (`~/.claude/agents/seo-writer.md`), Cursor (`~/.cursor/agents/seo-writer.md`), Codex (`~/.codex/agents/seo_writer.toml`), Antigravity (`~/.gemini/config/agents/seo-writer.md`), Gemini CLI (`~/.gemini/agents/seo-writer.md`) and Copilot (`~/.copilot/agents/seo-writer.agent.md`), with identical instructions (a test checks this). Windsurf has no sub-agents, so it writes the parts in turn. The DRAFT task names the spawn call for each tool.

**Search cost.** At most 3 paid Serper searches a run (`seolib/serper.py`, `CAP_PER_RUN`; cached answers are free, refused searches are logged as decisions): the main search (top 10, People Also Ask, related searches and answer box in one response); one People Also Ask expansion (or, where Google shows no PAA for the market, the closest English market's SERP); then one search across the authorities on money, health, legal and safety topics, or else Google's site search of the client (`prep.client_site_search`, after the waves, only when a credit is left: it finds client pages no sitemap lists). Autocomplete, including the question-word variants, comes from Google's free suggestion service (`seolib/suggest.py`; unofficial, so any failure means no suggestions, never a retry around a block). PAA answer lookups, per-question SERP-overlap checks and name lookups are gone; the top 10 pages, read in full, and the researchers cover them. Runs used 33-51 credits before.

**Information gain and the author's view.** The first `next` starts the research scripts as a background process (`seo.py research --background`; `research_bg.json` records its state) and prints the researchers' task: two `seo-gain-researcher` sub-agents use the coding tool's own web search (no Serper credit) to find what page one lacks, A from people (forums, Q&A, communities; Reddit skipped) and B from evidence (studies, tests, official statistics, recent changes, mistakes, costs), each writing `gain_<X>.yaml` with exact quotes. The next `next` checks each quote against its page (`seolib/gain.py`: a direct fetch, Spider where pages block scripts), waits for the scripts (or runs them itself if the background process could not start or died), drops what page one already says, the client's own pages and competitors, and registers the rest as `gain:N` facts. The plan places them under their headings, picks 1-2 exact-quote slots and marks 2-3 "your view" headings in the first 70% of the page; `seolib/voice.py` checks the views (count, placement, no claimed experience), the gain items, citations and quotes. `info_gain` and `reddit_voice` are off (`modes: [manual]`).

**The plan** turns `topic_outline` into the page's headings before anyone writes: every shared section, every section only one ranking page has, and every People Also Ask, related and competitor question, merged by meaning; a searcher question routed as H2 gets its own H2, the rest become H3s under the H2 they belong to; variants of the main query ("… water based fence paint …") become one comparison block; another market's questions (other currencies, Fahrenheit, other countries) are left out; commercial page types get the client's offer section first and its next step last. Each heading carries its facts, its internal links and a word budget, and the length range follows the plan. The plan is split into two or three parts for parallel writers, and `plan.check` tells the combined check which planned headings the draft lacks.

**Facts** come from four places, in this order of authority: the client site's own rates data when its profile names it (`site_rates_dir`: the figures its calculators run on, kept from official sources; `seolib/siterates.py` reads the modules with Node and registers the ones the page is about as `rates:` facts), verified authority pages (`official_facts`), the client's own pages, and `serp_facts`: the points the page-one results state, clustered by meaning and counted by how many ranking sites make them. Where sites disagree, the figure most ranking sites state wins (rank only breaks a tie; losing figures are blocked by lint). Sentences in another market's currency or units are left out. The writer sees other sites' facts as notes (figures, qualifiers, content words), never their sentences, so nothing is copied.

Coverage (`article_context.json` `coverage_requirements`) is the union of what page one covers (every outline section, every point a single ranking site makes under its own heading) plus the searcher questions page one leaves unanswered (`info_gain: true`). PAA questions survive the "drifts from the topic" heuristic; only another market's, another brand's or shopping questions are dropped.

Speed work (October 2026): spaCy lemmatisation is batched (`nlp.prime`) and cached, URL slugs are prefiltered by shared stems before tagging (the sitemap of a big site was ~7,000 model calls), every fetch has a wall-clock deadline, Spider renders all competitor pages at once with an 18 s budget; the client-page reads of foundation share one 6 s round, and plugins start as soon as their own dependencies finish (no wave barrier).

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
| `semantic_graph` | The knowledge graph of the topic in this market (`seolib/graph.py`, plain rules, spaCy sharpens types): typed entities with aliases and definitions, attribute values with the sites that state them, relationships; plus consensus figures and heading topics | `research/semantic_graph.json` → `article_context.json` |
| `topic_outline` | Every PAA, related, Search Console and competitor question placed in the sections the ranking pages share, macro to micro, each with its entities, figures and facts | `research/topic_outline.json` → `article_context.json` |
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

## Website context and JSON writing handoff (October 2026)

`seolib/sitecontext.py` resolves an explicit project binding before a single-profile fallback, matches hosts exactly, and builds a resumable same-site inventory from robots/sitemaps/internal links. Parsed documents share versioned fetch cache keys with foundation/intake. The inventory records H1/title/query/type, purpose excerpts, read states and gaps. Thin successful pages may use Spider; refused/error pages stay gaps. A page cap or an inaccessible page cannot become a claim that the whole website was read.

`seolib/batch.py` normalises TXT/CSV/JSON/YAML requests, matches existing pages, blocks ambiguous mappings, merges queries targeting one URL, and prepares briefs before starting the first page. Plans retain pending/running/complete/blocked states and mode. The normal page completion branch advances the plan only after validation, editorial review and fact-checking. New plans include their fingerprint in brief names so changed instructions cannot silently reuse a completed run from another plan.

`seolib/article_context.py` builds one cached JSON handoff: page job, website catalog, scoped usable facts, entities/attributes/values, semantic triplets/relationships, definitions, search demand, source metadata/passages, sections and coverage requirements. Full parser blocks are retained once in competitor_scrape.json and indexed by source/block id. The focused semantic inventory is heuristic: per-page processing, extraction limits, market exclusions and unread sources are visible. Nothing here establishes an exhaustive knowledge graph or perfect rankings. `kgdoc.write_docs` keeps its compatibility entry point but renders Markdown only for explicit `research_format: markdown`.

Deep research sends up to ten eligible organic URLs plus four PAA source URLs and two related/expanded-search sources to Spider in one bounded wave; quick mode uses five organic plus two PAA sources. Related queries are looked up in the same SERP expansion wave to obtain real URLs. All PAA/related/autocomplete/expansion text remains in search demand regardless of source budgets. Extraction is cached by source, demand, locale, market strictness and code. New facts refresh the article context without re-extracting unchanged competitor text.

Section priorities use main-task relevance and source support before observed competitor order. Coverage is enforced through explicit placements/exclusions, including paragraphs, tables and FAQs on all page types. Lexical routing/coverage checks are advisory because paraphrases and page purpose can invalidate a keyword-only inference; factual verification remains enforced. The editor must account for every required coverage id in the final page.
