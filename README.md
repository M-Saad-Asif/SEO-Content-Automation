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

```bash
python install.py --keys                                            # change the API keys
python install.py                                                   # again after moving the folder or pulling updates
python scripts/seo.py doctor                                        # setup check (Python, packages, keys, plugins)
python scripts/seo.py start "<client>: <keyword> | <instructions>"  # the same run, from a terminal
python scripts/seo.py client <slug> <domain>                        # a client profile ahead of time (start does this for a new domain)
python scripts/seo.py test                                          # regression fixtures
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
