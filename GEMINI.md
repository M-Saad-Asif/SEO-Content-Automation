# GEMINI.md — ASDivigitals page-SEO pipeline (same as AGENTS.md)

## Trigger

When the user types `/page-seo …`, `$page-seo …`, `page-seo …`, or asks for an SEO page or article for a keyword, run the program below. You are its operator: the program decides every step; you carry out the one task it prints, then ask it for the next. Do not plan the article, skip steps, reorder them or add your own.

The request is what the user typed: a page address (the page is read first: its type and main keyword come from it), or a keyword, usually with the client (a name or a domain) and optional instructions, e.g. `nutmeg: what is a lifetime isa | for first-time buyers, plain English`. A brief path (`briefs/<page>.yaml`) works too.

1. Run `python scripts/seo.py start "<the request, exactly as typed>"` (from any other folder: `python "<this folder>/scripts/seo.py" …`).
   - If it prints `NEED A CLIENT` or `NEED A KEYWORD`, ask the user that one question and run `start` again with the answer added. That is the only question you may ask.
   - Otherwise it prints `BRIEF briefs/<page>.yaml` and the first task. Use that brief in every later command.
2. If the output contains `NEXT TASK`, do exactly that task and nothing more, then run exactly the command(s) printed at its end: `done <brief> <step>` only when the task prints it, then `python scripts/seo.py next <brief>`.
3. If it prints `DONE` or `STOPPED`, reply exactly as it says and stop.
4. If a command fails (error, traceback, missing package or key), run `python scripts/seo.py doctor`, apply the `fix:` line it prints once, and run `next` again. If it still fails, stop and show the error.
5. Read the output of every `next` and go back to 2.

Never: edit anything under `scripts/`, `plugins/`, `RULES.md`, `WORKFLOW.md`, `clients/` or the brief; open other runs or backup folders; run `seo.py` commands the task did not print; run `done` for a task you have not finished; ask the user anything mid-run.

Use `python3` where `python` is not on PATH. Add `--mode quick` to `start` or `next` only when the user asks for a quick run. First-time setup on a machine is one command, `python install.py` (packages, spaCy model, API keys into `.env`, and `/page-seo` installed into every coding agent: Claude Code, Cursor, Codex, Antigravity, Gemini CLI, Windsurf, Copilot). If `doctor` fails on packages or keys, that is the fix.

## Roles the tasks name

Where the host can start a separate agent, give each task to the agent the task names (Claude Code: `.claude/agents/`); otherwise do it as a separate pass. Pick Sonnet or a stronger model for runs in Cursor, Codex or Antigravity: the writer and fact-checker run on the model you select.
- researcher: `plugins/deep_research/SKILL.md` (verified, scoped facts and `research/dossier.md`)
- expert reviewer: `plugins/expert_review/SKILL.md`, two passes: `expert_notes.md` before the outline, and `expert_read.md` after validation (an independent opinion on the finished page, with today's news and the business fit, applied by the editor's pass); no invented experience
- writer: `RULES.md` + the `WORKFLOW.md` section the task names (Claude Code: `.claude/agents/seo-writer.md`, on Sonnet)
- fact-checker: `plugins/fact_check/SKILL.md` (`verify.md`; a fresh agent that did not write the page; Claude Code: `.claude/agents/seo-fact-checker.md`)
- internal linker: `plugins/internal_links/SKILL.md` (the last writing stage: 3–6 contextual links anchored on each target's main term; `internal_links.md`)

E-E-A-T inputs only a person can give go in the client profile: `author:` (a real name and credentials for the byline) and `experience:` (genuine first-hand notes, case data, what the client's staff see). The pipeline never invents either.

## New client or brief (operator, before a run)

- `python scripts/seo.py client <slug> <domain>` builds `clients/<slug>.yaml` from the live site.
- `python scripts/seo.py brief <client> "<query>"` writes `briefs/<slug>.yaml` (`start` does this for you).

## Repo notes for code changes (not for writing runs)

- Python 3.10+; `python install.py` sets everything up (packages, spaCy model, keys in the git-ignored `.env`: `SERPER_API_KEY`, `SPIDER_API_KEY`; adapters). Edit the `/page-seo` contract only in `scripts/install_adapters.py`, then run `python install.py` again.
- `python scripts/seo.py doctor` checks the setup; `python scripts/seo.py test` runs the regression fixtures; keep both passing.
