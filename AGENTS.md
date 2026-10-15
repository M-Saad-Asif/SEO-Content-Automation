# AGENTS.md — ASDivigitals page-SEO pipeline

## Trigger

When the user types `/page-seo …`, `$page-seo …`, `page-seo …`, or asks for an SEO page or article for a keyword, run the program below. You are its operator: the program decides every step; you carry out the one task it prints, then ask it for the next. Do not plan the article, skip steps, reorder them or add your own.

The request is what the user typed: a page address (the page is read first: its type and main keyword come from it), or a keyword, usually with the client (a name or a domain) and optional instructions, e.g. `nutmeg: what is a lifetime isa | for first-time buyers, plain English`. A brief path (`briefs/<page>.yaml`) works too.

1. Run `python scripts/seo.py start "<the request, exactly as typed>"` (from any other folder: `python "<this folder>/scripts/seo.py" …`).
   - If it prints `NEED A CLIENT`, `NEED A KEYWORD` or `NEED A PAGE`, ask the missing-context question and run `start` again with the answer added. Reuse known website context; do not ask for it again.
   - Otherwise follow the printed task and brief. For a batch, use the brief in each new task's commands as the driver advances pages.
2. If the output contains `NEXT TASK`, do exactly that task and nothing more, then run exactly the command(s) printed at its end: `done <brief> <step>` only when the task prints it, then `python scripts/seo.py next <brief>`.
3. If it prints `DONE` or `STOPPED`, reply exactly as it says and stop.
4. If a command fails (error, traceback, missing package or key), run `python scripts/seo.py doctor`, apply the `fix:` line it prints once, and run `next` again. If it still fails, stop and show the error.
5. Read the output of every `next` and go back to 2.

Never: edit anything under `scripts/`, `plugins/`, `RULES.md`, `WORKFLOW.md`, `clients/` or the brief; open other runs or backup folders; run `seo.py` commands the task did not print; run `done` for a task you have not finished; ask the user anything mid-run.

Use `python3` where `python` is not on PATH. There is one mode: every run does the whole pipeline (research scripts, the page plan, parallel writers, one combined check, validate) in about five minutes. First-time setup on a machine is one command, `python install.py` (packages, spaCy model, API keys into `.env`, and `/page-seo` installed into every coding agent: Claude Code, Cursor, Codex, Antigravity, Gemini CLI, Windsurf, Copilot). If `doctor` fails on packages or keys, that is the fix.

## Roles the tasks name

- writers: `RULES_CARD.md` + the run's `write_brief.md`, nothing else. The draft task splits the page plan into parts: start one writer per part at the same time where the host can run agents in parallel (Claude Code: several `seo-writer` agents in one message, on Sonnet); otherwise write the parts in turn. Pick Sonnet or a stronger model in Cursor, Codex or Antigravity.
- fixes: one combined fix task after the check (planned headings missing, blocking lines, claims no fact carries), edited in place.

E-E-A-T inputs only a person can give go in the client profile: `author:` (a real name and credentials for the byline) and `experience:` (genuine first-hand notes, case data, what the client's staff see). The pipeline never invents either.

## New client or brief (operator, before a run)

- `python scripts/seo.py site <website>` reads/discovers the website and saves reusable `seo-context.yaml` plus its inventory; no article run. Repeat to resume a capped discovery.
- Add `--keywords <file>`, `--pages <file>` or `--all-pages` to prepare a resumable queue; `python scripts/seo.py batch <plan>` starts/resumes writing. Through adapters use `<website> | keywords: <file or semicolon list>` or `<website> | pages: <file or URL list>`.
- `python scripts/seo.py client <slug> <domain>` builds `clients/<slug>.yaml` from the live site.
- `python scripts/seo.py brief <client> "<query>"` writes `briefs/<slug>.yaml` (`start` does this for you).

## Repo notes for code changes (not for writing runs)

- Python 3.10+; `python install.py` sets everything up (packages, spaCy model, keys in the git-ignored `.env`: `SERPER_API_KEY`, `SPIDER_API_KEY`; adapters). Edit the `/page-seo` contract only in `scripts/install_adapters.py`, then run `python install.py` again.
- `python scripts/seo.py doctor` checks the setup. `python scripts/seo.py test --offline` runs synthetic pipeline regressions without content runs, API calls or paid credits. `python scripts/seo.py test` runs the full fixture preparation and may fetch sources/create runs; use only when that scope is authorized.
