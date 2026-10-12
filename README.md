# SEO Content Automation

Pages researched and written the way a senior SEO works, from one command in the coding agent you already use (Claude Code, Cursor, Codex, Antigravity, Gemini CLI, Windsurf, GitHub Copilot).

It reads Google for the right country (intent, format, who ranks, People Also Ask, related searches), renders every ranking page, and builds two things the writer works from: a **knowledge graph** of the topic in that market (entities, definitions, attribute values with their sources, relationships, verified facts) and a **topic outline** (the sections the ranking pages share, macro to micro, with every searcher and competitor question placed in the section that answers it). Then it researches and verifies facts, gets an expert's notes, writes in the client's voice, lints, fact-checks with a separate agent, adds internal links, and scores the result. Every stage is a plugin ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

## Start in two steps

**1. Clone and install** (Python 3.10+ needed: [python.org/downloads](https://www.python.org/downloads/); on Windows tick "Add python.exe to PATH")

```bash
git clone https://github.com/M-Saad-Asif/SEO-Content-Automation.git
cd SEO-Content-Automation
python install.py
```

On macOS or Linux use `python3 install.py` (or `./install.sh`); on Windows you can also double-click `install.cmd`.

The installer installs the packages and the spaCy model, asks for two API keys (input hidden, saved only in `.env` in this folder, never committed), installs the `/page-seo` command into every coding agent on your machine pointing at this folder, and runs a setup check that should end with `DOCTOR PASS`.

| Key | What it is for | Where |
|---|---|---|
| `SERPER_API_KEY` | Google results for the right country | [serper.dev](https://serper.dev) (free credits on sign-up) |
| `SPIDER_API_KEY` | renders competitor pages that block plain fetching | [spider.cloud](https://spider.cloud) |

**2. Restart your agent and run a page**

```
/page-seo <client name or domain>: <keyword> | <optional instructions>
```

For example `/page-seo example.com: how to grow tomatoes in pots | for beginners, UK`. In Codex the command is `$page-seo …`. A new domain is profiled automatically; the market (country and language) comes from your words, the page or the client's site. To improve an existing page, give its address: `/page-seo https://example.com/some-page/`.

The agent then runs the pipeline step by step until it prints `DONE` with the paths to `final.md` (the page), `report.md` (decisions, questions answered, links) and `eval.md`, in `runs/`. Use Sonnet or a stronger model for the writing steps.

## Commands

For repeated work on one website, save its context and discover its pages once:

```bash
python scripts/seo.py site example.com
python scripts/seo.py site example.com --keywords keywords.csv
python scripts/seo.py site example.com --pages pages.txt
python scripts/seo.py site example.com --all-pages
```

`site` only reads the website and prepares briefs/queue; it does not research or write articles. It follows same-site sitemaps and content links, reads up to 250 pages per pass (change with `--max-pages`), and saves `sites/<client>/inventory.json`. Repeat it to resume a larger site; use `--refresh` to read it afresh. Thin successful HTML can be rendered with Spider. Robots exclusions, unavailable pages and unfinished frontiers are reported. A bounded crawl cannot promise every page on a website was found.

The generated `seo-context.yaml` binds this project to that website. Keyword-only requests reuse it; a single saved client is also an implicit default. Multiple clients without a binding require a website. A domain alone means its homepage; a full page URL derives its page type and query from live content (H1/title/address). An explicit keyword remains the target when matching it to an existing page. Ambiguous existing-page matches require a page URL.

Lists accept TXT (one keyword/URL per line), CSV (`keyword,url,page_type,instructions`), JSON or YAML lists. A keyword already matching one known page is a rewrite; a new keyword creates a brief with inferred type. Explicit page types win. Multiple keywords for the same URL share one page as secondary queries. `--all-pages` queues known content pages only and reports incomplete discovery. Prepared plans live in `batches/`; resume one with `python scripts/seo.py batch <printed-plan-path>`. The existing driver completes, validates and fact-checks each page before advancing the queue. These local files and client context are git-ignored.

Through an installed agent adapter, use `/page-seo example.com | keywords: keywords.csv` or `/page-seo example.com | pages: https://example.com/services/help; https://example.com/blog/guide`. To prepare and start directly from the CLI: `python scripts/seo.py start --site example.com --keywords keywords.csv`. Re-run the installer after pulling updates to refresh installed adapters.

Writers now use `article_context.json`: page purpose, website catalog, scoped facts, entities/attributes/values, semantic triplets, relationships, definitions, all search demand, evidence references, section priorities and coverage ids. This replaces repeated Markdown graph/outline exports by default; there was never a graph database to remove. Raw source blocks remain indexed in `research/competitor_scrape.json` without duplicating them into the writer's context. The extractor caches identical inputs and reports limits; neither exhaustive knowledge nor ranking guarantees are claimed. Legacy Markdown exports are available only with `research_format: markdown` in a brief.

```bash
python install.py --keys                                            # change the API keys
python install.py                                                   # again after moving the folder or pulling updates
python scripts/seo.py doctor                                        # setup check (Python, packages, keys, plugins)
python scripts/seo.py start "<client>: <keyword> | <instructions>"  # the same run, from a terminal
python scripts/seo.py client <slug> <domain>                        # a client profile ahead of time (start does this for a new domain)
python scripts/seo.py test --offline                                # synthetic regressions, no API calls/content runs
python scripts/seo.py test                                          # full fixture preparation; fetches sources/creates runs
```

Your briefs, client profiles, runs and cache stay on your machine (`briefs/`, `clients/`, `runs/`, `cache/` are git-ignored).

**Rewrites and connectors:** a rewrite can pull Search Console, Clarity and DataForSEO data for the existing page, through API keys in `.env` or MCP servers attached to your agent ([mcp/README.md](mcp/README.md)). Every plugin's `plugins/<name>/SKILL.md` documents its rules and edge cases.

| File | What it holds |
|---|---|
| `AGENTS.md` | What an agent does when you type `/page-seo` |
| `WORKFLOW.md` | The procedure |
| `RULES.md` | The writing rules |
| `BRIEF_TEMPLATE.yaml` | Every brief field |
| `docs/ARCHITECTURE.md` | The run end to end and every plugin |
