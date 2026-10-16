#!/usr/bin/env python3
"""Install the single /page-seo command into every coding agent on this machine, at user level, so it works in any
folder: Claude Code, Cursor, Codex, Antigravity, Gemini CLI, Windsurf and GitHub Copilot (VS Code).

  python scripts/install_adapters.py            # show what it would write
  python scripts/install_adapters.py --apply    # write it (replaced files are backed up first)
  python scripts/install_adapters.py --apply --only claude cursor

Every adapter is the same instruction with this repository's absolute path in it: run
`seo.py start "<what the user typed>"`, then do the one task `seo.py next` prints, until DONE. Backups of replaced
files go to '<working folder> backups/_backup/install-<timestamp>/'.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
# the interpreter that ran this installer (it has the packages): "python" may be missing or another Python on
# a friend's machine (macOS has only python3; a virtual environment has its own)
PY = Path(sys.executable).as_posix() if sys.executable else "python"
SEO = f'"{PY}" "{(ROOT / "scripts" / "seo.py").as_posix()}"'
DESC = ("Write SEO pages with the ASDivigitals pipeline from keywords, domains, page URLs or a website keyword list, "
        "step by step, exactly as the program prints it.")


def body(args: str) -> str:
    """The one contract every tool gets. `args` is how that tool passes the text typed after the command."""
    return f"""You are the operator of a program. The program decides every step; you carry out the one task it prints, then ask it for the next. Do not plan the article, skip steps, reorder them or add your own.

The pipeline lives in `{ROOT.as_posix()}`. The commands below work from any folder.

The request is {args}: a keyword with optional client/instructions, a domain or a page URL. Page URLs are read for type and main query. A configured website context (seo-context.yaml) or a single saved client is reused; ask for the website only when none is unambiguous. A website list works as `example.com | keywords: keywords.csv` or `example.com | pages: pages.txt` (semicolon-separated values also work). The program discovers the website, prepares a resumable queue and prints one page task at a time.

1. Run `{SEO} start "<the request, exactly as typed>"`.
   - If it prints `NEED A CLIENT`, `NEED A KEYWORD` or `NEED A PAGE`, ask the missing-context question and run `start` again with their answer added.
   - Otherwise follow the printed task and brief path. In a batch, the next page may have a different brief; use the path in that task's commands. Website discovery does not claim unread pages were read.
2. If the output contains `NEXT TASK`, do exactly that task and nothing more, then run exactly the command(s) printed at its end: `done <brief> <step>` only when the task prints it, then `{SEO} next <brief>`.
3. If it prints `DONE` or `STOPPED`, reply exactly as it says and stop.
4. If a command fails (error, traceback, missing package or key), run `{SEO} doctor`, apply the `fix:` line it prints once, and run `next` again. If it still fails, stop and show the error.
5. Read the output of every `next` and go back to 2.

When a task says writers work in parallel, start the `seo-writer` sub-agent once per part, all at the same time, in one turn (Claude Code: the Agent tool; Cursor: its subagents; Codex: spawn one `seo_writer` agent per part and wait for all; Antigravity and Gemini CLI: invoke the `seo-writer` subagent once per part; Copilot: the agent tool with `seo-writer`). A tool that cannot run sub-agents writes the parts itself, one after another. When a task says researchers work at the same time, start the `seo-gain-researcher` sub-agent (Codex: `seo_gain_researcher`) once per letter in the same way; a tool without sub-agents does each in turn with its own web search. Any other task naming a role: give it to a sub-agent if your tool can start one, otherwise do it yourself as a separate pass.

Never: edit anything in the pipeline's `scripts/`, `plugins/`, `RULES.md`, `WORKFLOW.md`, `clients/` or the brief; open other runs or backup folders; run `seo.py` commands the task did not print; run `done` for a task you have not finished; ask the user anything mid-run.
"""


WRITER_DESC = ("Writer of the page-SEO pipeline: drafts one part of a page plan (or the whole page, or one fix pass) "
               "exactly as the task from `seo.py next` says. Several run at once, one per part of the plan.")


RESEARCHER_DESC = ("Information-gain researcher of the page-SEO pipeline: while the research scripts run, finds what page "
                   "one doesn't have with the tool's own web search and writes gain_<X>.yaml. Two run at once (A, B).")


def agent_prompt(name: str = "seo-writer") -> str:
    """A role's instructions, the same in every tool (from .claude/agents/<name>.md, the source of truth)."""
    src = (ROOT / ".claude" / "agents" / f"{name}.md").read_text(encoding="utf-8")
    body_ = src.split("---", 2)[2].strip() if src.startswith("---") else src.strip()
    return body_ + f"\n\nThe pipeline lives in `{ROOT.as_posix()}`; paths in the task are relative to it.\n"


def writer_prompt() -> str:
    return agent_prompt("seo-writer")


def _agents(name: str, desc: str, ag_tools: list | None, copilot_tools: list) -> dict[str, list[tuple[Path, str]]]:
    """One role as a sub-agent in each tool's own format, with identical instructions."""
    prompt = agent_prompt(name)
    md = lambda front: "---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in front.items()) + "\n---\n\n" + prompt
    snake = name.replace("-", "_")
    ag = {"name": name, "description": desc, **({"tools": ag_tools} if ag_tools else {}),
          "mainAgent": False, "subagent": True, "model": "inherit"}
    return {
        "cursor": [(HOME / ".cursor" / "agents" / f"{name}.md", md({"name": name, "description": desc}))],
        "codex": [(HOME / ".codex" / "agents" / f"{snake}.toml",
                   f'name = "{snake}"\ndescription = {json.dumps(desc)}\ndeveloper_instructions = """\n{prompt}"""\n')],
        "antigravity": [(HOME / ".gemini" / "config" / "agents" / f"{name}.md", md(ag))],
        "gemini": [(HOME / ".gemini" / "agents" / f"{name}.md", md({"name": name, "description": desc, "kind": "local"}))],
        "copilot": [(HOME / ".copilot" / "agents" / f"{name}.agent.md",
                     md({"name": name, "description": desc, "tools": copilot_tools}))],
    }


def writer_agents(appdata: Path) -> dict[str, list[tuple[Path, str]]]:
    """The writer as a sub-agent in each tool that can run sub-agents in parallel."""
    return _agents("seo-writer", WRITER_DESC, ["view_file", "write_to_file", "replace_file_content", "list_dir"],
                   ["read", "edit", "search"])


CHECKER_DESC = ("Fact-check pass of the page-SEO pipeline: checks only the lines where a mistake would hurt (formulas, "
                "sums, money, rates, health, legal, safety), leaves correct lines alone and fixes only real errors.")


def checker_agents(appdata: Path) -> dict[str, list[tuple[Path, str]]]:
    """The fact-checker in each tool, the same calm instructions everywhere."""
    return _agents("seo-fact-checker", CHECKER_DESC, None, ["read", "edit", "web"])


def researcher_agents(appdata: Path) -> dict[str, list[tuple[Path, str]]]:
    """The information-gain researcher (web search + one file write) in each tool; tools left to each tool's
    defaults where a tool names its web tools differently."""
    return _agents("seo-gain-researcher", RESEARCHER_DESC, None, ["read", "edit", "web"])


def md_with_front(front: dict, args: str) -> str:
    lines = ["---"] + [f"{k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}" for k, v in front.items()] + ["---", ""]
    return "\n".join(lines) + body(args)


def targets() -> dict[str, list[tuple[Path, str]]]:
    appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
    claude_tools = "Bash, Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent"
    out = {
        # Claude Code: user-level slash command, plus the four role agents so tasks can be delegated in any folder
        "claude": [(HOME / ".claude" / "commands" / "page-seo.md",
                    md_with_front({"description": DESC, "argument-hint": "<client>: <keyword> | <instructions>",
                                   "allowed-tools": claude_tools}, "`$ARGUMENTS`"))]
        + [(HOME / ".claude" / "agents" / p.name, p.read_text(encoding="utf-8"))
           for p in sorted((ROOT / ".claude" / "agents").glob("seo-*.md"))],
        # Cursor: user-level command (/page-seo in any workspace)
        "cursor": [(HOME / ".cursor" / "commands" / "page-seo.md",
                    "# page-seo\n\n" + body("the text the user typed after `/page-seo`"))],
        # Codex: one skill in Codex's own folder ($page-seo). Not ~/.agents/skills: Cursor reads that folder too.
        "codex": [(HOME / ".codex" / "skills" / "page-seo" / "SKILL.md",
                   md_with_front({"name": "page-seo", "description": DESC + " Use when the user invokes page-seo."},
                                 "the text the user gave with `$page-seo`"))],
        # Antigravity: global workflow (/page-seo)
        "antigravity": [(HOME / ".gemini" / "config" / "global_workflows" / "page-seo.md",
                         md_with_front({"description": DESC}, "the text the user typed after `/page-seo`"))],
        # Gemini CLI: user command (/page-seo), TOML with {{args}}
        "gemini": [(HOME / ".gemini" / "commands" / "page-seo.toml",
                    f'description = {json.dumps(DESC)}\nprompt = """\n{body("`{{args}}`")}"""\n')],
        # Windsurf: global workflow (/page-seo)
        "windsurf": [(HOME / ".codeium" / "windsurf" / "global_workflows" / "page-seo.md",
                      md_with_front({"description": DESC}, "the text the user typed after `/page-seo`"))],
        # GitHub Copilot in VS Code: user prompt file (/page-seo in Copilot Chat)
        "copilot": [(appdata / "Code" / "User" / "prompts" / "page-seo.prompt.md",
                     md_with_front({"description": DESC, "mode": "agent"}, "the text the user typed after `/page-seo`"))],
    }
    for agents in (writer_agents(appdata), researcher_agents(appdata), checker_agents(appdata)):
        for tool, items in agents.items():
            out[tool] = out.get(tool, []) + items
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", nargs="*", help="claude cursor codex antigravity gemini windsurf copilot")
    a = ap.parse_args()
    # replaced files are backed up: in '<working folder> backups' when that folder exists, else in the home folder
    side = ROOT.parent.parent / f"{ROOT.parent.name} backups"
    base = side if side.exists() else HOME / ".page-seo-backups"
    backup = base / "_backup" / ("install-" + time.strftime("%Y%m%d-%H%M%S"))
    appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
    present = {"claude": HOME / ".claude", "cursor": HOME / ".cursor", "codex": HOME / ".codex",
               "antigravity": HOME / ".gemini" / "config",
               "gemini": HOME / ".gemini" if shutil.which("gemini") else HOME / ".no-gemini-cli",
               "windsurf": HOME / ".codeium" / "windsurf", "copilot": appdata / "Code" / "User"}
    tools = a.only or [t for t, d in present.items() if d.exists()]
    skipped = [t for t in present if t not in tools]
    if skipped:
        print(f"not installed on this machine (skipped; add with --only): {', '.join(skipped)}")
    plan = [(tool, dest, text) for tool, items in targets().items() if tool in tools for dest, text in items]
    stale = [HOME / ".cursor" / "skills" / "page-seo", HOME / ".agents" / "skills" / "page-seo",
             HOME / ".codex" / "prompts" / "page-seo.md",
             HOME / ".gemini" / "config" / "plugins" / "Asdivigitals",
             HOME / ".gemini" / "config" / "global_workflows" / "workflow-page-seomd.md"]
    if "gemini" not in tools:
        stale.append(HOME / ".gemini" / "commands" / "page-seo.toml")
    for s in stale:
        if s.exists():
            print(f"RETIRE  {s}")
            if a.apply:
                b = backup / "retired" / s.relative_to(HOME)
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(s), str(b))
    for tool, dest, text in plan:
        exists = dest.exists()
        same = exists and dest.read_text(encoding="utf-8", errors="replace") == text
        print(f"{'SAME   ' if same else 'REPLACE' if exists else 'CREATE '} [{tool}] {dest}")
        if not a.apply or same:
            continue
        if exists:
            b = backup / dest.relative_to(HOME) if HOME in dest.parents else backup / dest.name
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, b)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    print("done" + (f"; backups (if any) in {backup}" if a.apply else " (dry run; add --apply)"))


if __name__ == "__main__":
    main()
