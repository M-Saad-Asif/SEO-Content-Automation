"""`seo.py next <brief>`: the pipeline as a state machine.

The coding agent (Claude Code, Codex, Cursor, Antigravity, any other) does not decide what to do. It runs
`python scripts/seo.py next <brief>`, does exactly the one task printed, and runs `next` again, until it prints
DONE. Every deterministic step (research, outline check, lint, editor's review sheet, validate, eval) is run here,
by code; the agent only researches, judges and writes when the printed task says so.

Agent-side tasks are confirmed with `python scripts/seo.py done <brief> <step>` where the task says so, so the
driver never has to guess whether a judgement task was finished.
"""
from __future__ import annotations

import contextlib
import io
from collections import Counter
from pathlib import Path

from . import common as C

SEP = "-" * 72


def _in_repo() -> bool:
    return Path.cwd().resolve() == C.ROOT.resolve()


def PY() -> str:
    """The interpreter running this, in the shortest form that reaches the same one: "python3" on macOS, "python"
    on Windows, the full path when a bare name would find another Python (an inactive virtual environment)."""
    import os
    import shutil
    import sys
    exe = Path(sys.executable)
    name = exe.stem if exe.suffix.lower() == ".exe" else exe.name
    found = shutil.which(name)
    try:
        if found and os.path.samefile(found, exe):
            return name
    except OSError:
        pass
    return f'"{exe.as_posix()}"'


def CMD() -> str:
    """How to call the CLI from the folder the agent is in."""
    return f"{PY()} scripts/seo.py" if _in_repo() else f'{PY()} "{(C.ROOT / "scripts" / "seo.py").as_posix()}"'


def ARG(value: str) -> str:
    """Quote printed CLI arguments, including absolute batch brief paths on Windows."""
    import os
    import shlex
    import subprocess
    return subprocess.list2cmdline([str(value)]) if os.name == "nt" else shlex.quote(str(value))


def _state(rd: Path) -> dict:
    return C.load_json(rd / "state.json") or {"done": {}}


def _save_state(rd: Path, st: dict) -> None:
    C.save_json(rd / "state.json", st)


def _end_agent_stage(rd: Path, st: dict) -> None:
    active = st.pop("active_stage", None)
    if active:
        from .timing import mark
        mark(rd, "agent:" + active, "end")
        _save_state(rd, st)


def _content_sig(path: Path, sheet: dict) -> str:
    """Linker may add internal links; changed facts, wording or external citations need a fresh check."""
    import hashlib
    import json
    import re
    from .lint import parse_md
    from .pagejob import is_client_url
    md = path.read_text(encoding="utf-8")
    meta, blocks = parse_md(md)
    meta.pop("updated", None)
    text = [(b["type"], C.collapse(b["text"])) for b in blocks]
    sources = sorted(u for u in re.findall(r"\]\((https?://[^)\s]+)\)", md) if not is_client_url(u, sheet))
    return hashlib.sha256(json.dumps([meta, text, sources], sort_keys=True).encode()).hexdigest()


def mark_done(brief_path: str, step: str) -> None:
    from .prep import load_brief
    rd = _current_run(load_brief(brief_path))
    if rd is None:
        raise SystemExit(f"No run yet. Run: {CMD()} next {ARG(brief_path)}")
    st = _state(rd)
    if step == "retry":
        st["rounds"], st["round_sig"] = {}, {}
        _save_state(rd, st)
        print(f"OK: fix-round counters reset for {rd.name}. Now run: {CMD()} next {ARG(brief_path)}")
        return
    need = {"research": rd / "research" / "dossier.md", "expert": rd / "expert_notes.md",
            "review": rd / "review.md", "expert_read": rd / "expert_read.md", "editor": rd / "editor.md",
            "verify": rd / "verify.md", "internal_links": rd / "internal_links.md"}
    if step not in need:
        raise SystemExit(f"Unknown step '{step}'. Steps you confirm: {', '.join(need)}")
    if not need[step].exists():
        raise SystemExit(f"NOT DONE: {need[step].as_posix()} does not exist yet. Finish the task first.")
    text = need[step].read_text(encoding="utf-8")
    if step == "verify":
        from .verify import check
        problems = check(rd, text)
    elif step == "internal_links":
        from .links import check as link_check
        problems = link_check(rd, text)
    else:
        problems = _gate(step, rd, text)
    if problems:
        print(f"NOT DONE: {need[step].name} is incomplete. Fix these, then run `done` again:")
        for p in problems:
            print(f"- {p}")
        raise SystemExit(1)
    st["done"][step] = C.now_iso()
    if step == "verify":
        st["verified_content"] = _content_sig(rd / "draft.md", C.load_json(rd / "fact_sheet.json") or {})
    _end_agent_stage(rd, st)
    _save_state(rd, st)
    print(f"OK: '{step}' recorded for {rd.name}. Now run: {CMD()} next {ARG(brief_path)}")


GATES = {  # headings each agent output must have (the formats in the skills); matched case-insensitively
    "research": ["main answer", "answers by question", "do not say", "gaps"],
    "expert": ["answer a professional would give", "decisions the reader faces", "mistakes people make",
               "what a professional would warn about", "experience the client can genuinely claim"],
    "expert_read": ["verdict", "what i would change", "current news", "business fit", "risk"],
    "editor": ["claim ledger", "expert read"],
}


def _gate(step: str, rd: Path, text: str) -> list[str]:
    """Structural checks on an agent's output, so `done` cannot confirm an empty or invented file."""
    import re
    heads = [h.strip().lower() for h in re.findall(r"^#{1,4}\s+(.+)$", text, re.M)]
    need = [g for g in GATES.get(step, []) if not (g == "expert read" and not (rd / "expert_read.md").exists())]
    out = [f"missing section \"{g}\" (see the skill's format)" for g in need if not any(g in h for h in heads)]
    from .pagejob import COMMERCIAL
    commercial = (C.load_json(rd / "fact_sheet.json") or {}).get("brief", {}).get("page_type") in COMMERCIAL
    if commercial and step in ("expert", "editor") and not any("offer" in h or "page job" in h for h in heads):
        out.append("missing Page job / client offer section: state the scoped offer, appropriate structure and verified next step")
    if step == "research":
        if not re.search(r"^###\s+\S", text, re.M):
            out.append("\"Answers by question\" has no ### question entries")
        ids = {f.get("id") for f in (C.load_json(rd / "fact_sheet.json") or {}).get("facts", [])}
        cited = set(re.findall(r"`([a-z0-9]+(?:[-:_.][a-z0-9]+)+)`", text, re.I))
        unknown = sorted(c for c in cited if c not in ids)
        if unknown:
            out.append("cites fact ids that are not in the fact sheet (add them with --add-fact or correct the id): "
                       + ", ".join(unknown[:15]))
        plan = (rd / "research_plan.md").read_text(encoding="utf-8") if (rd / "research_plan.md").exists() else ""
        need_t = re.findall(r"^- (T\d+): (.+?) \(", plan, re.M)
        sec = re.search(r"^##\s+topics[^\n]*$(.*?)(?=^##\s|\Z)", text, re.M | re.I | re.S)
        have = set(re.findall(r"\b(T\d+)\b", sec.group(1))) if sec else set()
        missing = [f"{t} ({name})" for t, name in need_t if t not in have]
        if missing:
            out.append("the topics section has no line for: " + "; ".join(missing[:12])
                       + " (cover each with fact ids, or say why it is left out)")
        main = re.search(r"^##\s+main answer\s*$(.*?)(?=^##\s)", text, re.M | re.I | re.S)
        if main and not re.search(r"`[^`]+`", main.group(1)):
            out.append("the main answer cites no fact id")
    if step == "editor":
        context = C.load_json(rd / "article_context.json") or {}
        if context:
            coverage = re.search(r"^#{1,4}[^\n]*coverage[^\n]*$(.*?)(?=^#{1,4}\s|\Z)", text, re.M | re.I | re.S)
            resolved = set(re.findall(r"\b(?:S\d+|Q\d+)\b", coverage.group(1))) if coverage else set()
            missing = [i["id"] for i in context.get("coverage_requirements", []) if i.get("required") and i["id"] not in resolved]
            if not coverage or missing:
                out.append("Coverage section must resolve required context ids with final-page placements or specific exclusions: " + ", ".join(missing[:20]))
        ledger = re.search(r"^#{1,4}[^\n]*claim ledger[^\n]*$(.*?)(?=^#{1,4}\s|\Z)", text, re.M | re.I | re.S)
        if ledger and len([l for l in ledger.group(1).splitlines() if l.strip()]) < 3:
            out.append("the claim ledger lists fewer than three factual sentences")
    return out


def _length_line(rd: Path) -> str:
    b = (C.load_json(rd / "fact_sheet.json") or {}).get("brief", {})
    eff, raw = b.get("word_range_effective"), b.get("word_range")
    if eff:
        return (f"Length: about {eff[0]}–{eff[1]} words in all (set by the plan: every heading the ranking pages cover, "
                f"answered; each heading's share is in the plan). Verified material only: a shorter section beats an "
                f"invented sentence.")
    if raw:
        return f"Length: aim for {raw[0]}–{raw[1]} words, with verified material only."
    return "Length: as long as the verified material needs, no padding."


def _quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = fn(*a, **k)
    return res, buf.getvalue()


LINT_ROUNDS = 5       # fix rounds before the run stops instead of looping (WORKFLOW: stop after three validate rounds)
VALIDATE_ROUNDS = 3


def _finding_lines(fs: list[dict], limit: int = 40) -> list[str]:
    out = []
    for f in fs[:limit]:
        out.append(f"- [{f['rule']}] line {f.get('line')}: \"{(f.get('text') or '')[:160]}\"")
        out.append(f"    why: {f.get('reason')}" + (f"  fix: {f['fix']}" if f.get("fix") else ""))
    if len(fs) > limit:
        out.append(f"- …and {len(fs) - limit} more; run `next` again after these to see them.")
    return out


def _rounds(rd: Path, st: dict, key: str, cap: int, R: str, brief_path: str, left) -> bool:
    """Count fix rounds; after `cap` rounds stop the run with a clear verdict instead of looping."""
    import hashlib
    sig = hashlib.sha1((rd / "draft.md").read_bytes()).hexdigest()
    st.setdefault("rounds", {})
    seen = st.setdefault("round_sig", {})
    if seen.get(key) != sig:  # a round is one edited draft that still fails, not one call of `next`
        st["rounds"][key] = st["rounds"].get(key, 0) + 1
        seen[key] = sig
        _save_state(rd, st)
    if st["rounds"][key] <= cap:
        return False
    print(SEP)
    print(f"STOPPED: {key} still fails after {cap} fix rounds")
    print(SEP)
    print(f"Draft:  {R}/draft.md")
    print(f"Report: {R}/report.md")
    print("Still blocking:")
    print("\n".join(_finding_lines(left)) if isinstance(left, list) else left)
    print("\nStop here. Reply with STOPPED, the two paths and the blocking lines above, and nothing else.")
    print(f"(An operator can reset the counter with: {CMD()} done {ARG(brief_path)} retry)")
    return True


def _task(title: str, lines: list[str], brief_path: str, confirm: str | None = None) -> None:
    from .prep import load_brief
    from .timing import mark
    rd = _current_run(load_brief(brief_path))
    if rd:
        st = _state(rd)
        stage = confirm or ("outline" if "OUTLINE" in title else "draft" if title.startswith("DRAFT") else "fix")
        if st.get("active_stage") != stage:
            _end_agent_stage(rd, st)
            mark(rd, "agent:" + stage, "start")
            st["active_stage"] = stage
            _save_state(rd, st)
    print(SEP)
    print(f"NEXT TASK: {title}")
    print(SEP)
    if not _in_repo():
        print(f"Repository: {C.ROOT.as_posix()} (every relative path below is inside it)")
    if ("role: writer" in title or "role: hostile senior editor" in title) and "in parallel" not in title:
        print("Claude Code: give this task to the `seo-writer` agent (it runs on Sonnet). Other tools: do it yourself.")
    for ln in lines:
        print(ln)
    print()
    print("Checks (lint, claims against facts, planned headings, validate, eval) are run by `next`; do not run them yourself.")
    if confirm:
        print(f"When the task is complete, run: {CMD()} done {ARG(brief_path)} {confirm}")
    print(f"Then run: {CMD()} next {ARG(brief_path)}")
    print("Do only this task. Do not start the next one until `next` prints it.")


def next_step(brief_path: str, mode: str | None = None) -> None:
    from .prep import load_brief
    brief = load_brief(brief_path)  # exits with BRIEF NOT FOUND / BRIEF INVALID
    rel = lambda p: Path(p).resolve().relative_to(C.ROOT.resolve()).as_posix()

    # 1. research (scripts) -------------------------------------------------------------------------------------
    rd = _current_run(brief)
    if rd is None or not (rd / "research_plan.md").exists() or not (rd / "writer_pack.md").exists():
        print(f"RUNNING: research for \"{brief['target_query']}\" (scripts, about a minute)…")
        from .harness import run_research
        # the scripts' own console notes ("next: write outline.md…") are for manual runs; here `next` decides
        rd, log = _quiet(run_research, brief_path, "deep")  # one mode: every research plugin, every run
        (rd / "research_log.txt").write_text(log, encoding="utf-8")
        print(f"Research scripts finished (log: {rel(rd)}/research_log.txt).")
        st = _state(rd)
        st["mode"] = "full"
        _save_state(rd, st)
    st = _state(rd)
    _end_agent_stage(rd, st)
    deep = st.get("mode", "deep") == "deep"
    R = rel(rd)
    if st.get("mode") in ("full", "fast") or not st["done"].get("research"):
        return _next_flow(brief, brief_path, rd, st, R, mode)

    # 2. research (agent) ----------------------------------------------------------------------------------------
    if "research" not in st["done"]:
        _task("RESEARCH (role: researcher)", [
            f"Run folder: {R}",
            "If your tool can start a separate agent, give this task to one (Claude Code: the `seo-researcher` agent).",
            "Otherwise do it yourself as a separate pass, before you think about the article.",
            "",
            "1. Read plugins/deep_research/SKILL.md fully. It is your complete instruction for this task.",
            f"2. Work {R}/research_plan.md as the skill says, using your own web search and fetch tools. If you have",
            f"   no tool that opens a URL, read pages with: {CMD()} read <url>",
            f"3. Write your findings to {R}/research/facts.yaml (a list of: id, claim, value = the page's exact words, url,",
            f"   scope) and record them all in one call: {CMD()} prep {ARG(brief_path)} --add-facts {R}/research/facts.yaml",
            "   Fix and re-run only the rejected ones (the reason is printed). One call for the batch, not one per fact.",
            f"4. Write {R}/research/dossier.md in the format the skill gives.",
            "Do not write the article.",
        ], brief_path, confirm="research")
        return

    # 3. expert review (agent, deep) ------------------------------------------------------------------------------
    if deep and "expert" not in st["done"]:
        _task("EXPERT REVIEW (role: expert reviewer)", [
            f"Run folder: {R}",
            "If your tool can start a separate agent, give this task to one (Claude Code: the `seo-expert` agent).",
            "",
            "1. Read plugins/expert_review/SKILL.md, pass 1 (everything above \"Pass 2\"). It is your complete instruction.",
            f"2. Read the brief ({brief_path}), the client profile in clients/, {R}/research/dossier.md and {R}/writer_pack.md"
            " (its Page job and decisions sections first).",
            f"3. Write {R}/expert_notes.md in the format the skill gives. Never invent experience, statistics or credentials.",
        ], brief_path, confirm="expert")
        return

    # 4. outline (agent writes, script checks; deep) --------------------------------------------------------------
    outline = rd / "outline.md"
    draft = rd / "draft.md"
    if not draft.exists():  # the facts the researcher verified since the scripts ran belong in both documents
        from .kgdoc import write_docs
        write_docs(rd)
    docs = [f"{R}/article_context.json"] if (rd / "article_context.json").exists() else []
    if deep and not st["done"].get("outline"):
        if not outline.exists():
            _task("OUTLINE (role: writer)", [
                f"Run folder: {R}",
                "1. Read RULES.md (section 0 first) and WORKFLOW.md section 3 (Outline).",
                f"2. Read {R}/writer_pack.md, " + (", ".join(docs) + ", " if docs else "")
                + f"{R}/research/dossier.md and {R}/expert_notes.md.",
                f"3. Write {R}/outline.md exactly as WORKFLOW.md section 3 describes (H1, H2/H3s, Skip:/Linked: lines,",
                "   one line under each heading naming the facts it uses)"
                + (", using article_context.json's sections, coverage requirements and page purpose." if docs else "."),
            ], brief_path)
            return
        from .outline import check_outline
        ok, out = _quiet(check_outline, rd)
        if not ok:
            _task("FIX THE OUTLINE (role: writer)", [
                f"The outline check failed. Edit {R}/outline.md so that every line starting with B below is resolved:",
                "", out.strip()[-3000:], "",
                "Change only what these lines ask for.",
            ], brief_path)
            return
        st["done"]["outline"] = C.now_iso()
        _save_state(rd, st)

    # 5. draft (agent) ---------------------------------------------------------------------------------------------
    if not draft.exists():
        _task("DRAFT (role: writer)", [
            f"Run folder: {R}",
            "1. Read RULES.md fully (section 0, the page's job, first) and WORKFLOW.md section 4 (Draft).",
            f"2. Read {R}/writer_pack.md, " + (", ".join(docs) + ", " if docs else "") + f"{R}/research/dossier.md"
            + (f", {R}/expert_notes.md and {R}/outline.md." if deep else "."),
            f"3. Write {R}/draft.md in one pass, as WORKFLOW.md section 4 describes (front matter, one H1, Markdown only).",
            "4. Reread it once as the reader (contradictions, repeated numbers or rules, sentences that only announce",
            "   the next one) and fix those in the same pass.",
            "",
            _length_line(rd),
        ], brief_path)
        return

    # 6. lint (script) ------------------------------------------------------------------------------------------------
    from .lint import lint_text, load_research
    sheet = C.load_json(rd / "fact_sheet.json")
    lm = C.load_json(rd / "link_map.json") or {}
    from .timing import mark
    mark(rd, "lint", "start")
    try:
        res = lint_text(draft.read_text(encoding="utf-8"), sheet, lm, load_research(rd))
    finally:
        mark(rd, "lint", "end")
    C.save_json(rd / "lint.json", res)
    blocks = [f for f in res["findings"] if f["severity"] == "block"]
    if blocks:
        if _rounds(rd, st, "lint", LINT_ROUNDS, R, brief_path, blocks):
            return
        lines = [f"Lint found {len(blocks)} blocking problem(s) in {R}/draft.md. Fix each one in place, one edit per",
                 "item, and change nothing else (WORKFLOW.md section 6):", ""]
        lines += _finding_lines(blocks)
        _task("FIX LINT BLOCKS (role: writer)", lines, brief_path)
        return
    st.setdefault("rounds", {})["lint"] = 0
    if st.get("verified_content") and "verify" in st["done"] and _content_sig(draft, sheet) != st["verified_content"]:
        for step in ("verify", "internal_links", "complete"):
            st["done"].pop(step, None)
        st.pop("verify_draft", None)
    _save_state(rd, st)

    # 7. editor's review sheet (script builds it, agent resolves it) --------------------------------------------------
    if "review" not in st["done"]:
        from .review import review
        _quiet(review, rd)
        warns = [f for f in res["findings"] if f["severity"] == "warn"]
        lines = [
            f"The review sheet is {R}/review.md (claims beside their facts, client lines, section shapes, gaps).",
            "Follow WORKFLOW.md section 6b: for every CHECK line make the sentence say what its fact says, add the",
            f"fact with --add-fact, or cut the claim; fix repeated section shapes; edit {R}/draft.md in place.",
        ]
        if warns:
            lines += ["", f"Also judge these {len(warns)} lint warning(s) (WORKFLOW.md section 5): fix a sentence when the rule",
                      "really applies to it; leave it when the sentence is already clear.", ""]
            lines += _finding_lines(warns)
        _task("RESOLVE THE REVIEW SHEET (role: writer)", lines, brief_path, confirm="review")
        return

    # 8. validate (script) ---------------------------------------------------------------------------------------------
    final = rd / "final.md"
    import hashlib
    draft_sig = hashlib.sha256(draft.read_bytes()).hexdigest()
    if not final.exists() or st.get("validated_draft") != draft_sig or \
            st.get("validated_final") != hashlib.sha256(final.read_bytes()).hexdigest():
        from .validate import validate
        ok, out = _quiet(validate, str(rd))
        if not ok:
            if _rounds(rd, st, "validate", VALIDATE_ROUNDS, R, brief_path, out.strip()[-3500:]):
                return
            _task("FIX VALIDATION (role: writer)", [
                f"Validation failed. Fix each blocking line below in {R}/draft.md and change nothing else:", "",
                out.strip()[-3500:],
            ], brief_path)
            return
        st.setdefault("rounds", {})["validate"] = 0
        st["validated_draft"] = draft_sig
        st["validated_final"] = hashlib.sha256(final.read_bytes()).hexdigest()
        _save_state(rd, st)

    # 8b. the expert read: an independent practitioner's opinion on the finished page, with today's news (deep) -----------
    if deep and "expert_read" not in st["done"]:
        _task("EXPERT READ OF THE FINISHED PAGE (role: independent senior practitioner)", [
            "Give this to a fresh agent that has not drafted the page (Claude Code: the `seo-expert` agent).",
            "",
            "1. Read plugins/expert_review/SKILL.md, section \"Pass 2: the expert read of the finished article\". It is",
            "   your complete instruction for this task.",
            f"2. Read {R}/final.md, {R}/page_context.md, the brief ({brief_path}) and the client profile in clients/. Search today's news on",
            "   the topic (last 18 months) with your own search tools; record any fact the page needs with --add-fact.",
            f"3. Write {R}/expert_read.md in the format the skill gives. Do not edit the draft: the editor applies it next.",
        ], brief_path, confirm="expert_read")
        return

    # 9. editor's pass (agent) -------------------------------------------------------------------------------------------
    if "editor" not in st["done"]:
        from .review import review
        _quiet(review, rd)  # the sheet beside the editor must describe the page as it is now, not an earlier draft
        _task("EDITOR'S PASS (role: hostile senior editor)", [
            f"`next` has just validated the draft: {R}/final.md is current. Follow WORKFLOW.md section 7b exactly:",
            f"1. Read docs/EVAL_RUBRIC.md and {R}/final.md, with {R}/review.md beside it"
            + (f", and the expert's opinion in {R}/expert_read.md." if (rd / "expert_read.md").exists() else "."),
            f"2. Write {R}/editor.md: deductions per rubric criterion with quoted lines; generic, link-only and",
            "   announcing sentences; repeated section endings; the claim ledger (every factual sentence → fact id →",
            "   same case yes/no); limits written with or less/or more checked against their facts; missing shared topics."
            "\n   Add a section \"## Page job\": the page type, scoped client offer, verified next step, structure and necessary disclosures; fix any drift."
            "\n   Add a section Coverage: resolve every required article_context.json coverage id against the final page,"
            " including body/table/FAQ placements or a specific evidence-based exclusion. Check the main task comes before supporting context."
            + ("" if not (rd / "expert_read.md").exists() else
               "\n   Add a section \"## Expert read\": every item of expert_read.md with what you changed, or why not."),
            f"3. Fix {R}/draft.md in place for each item (cut, rewrite, or add a verified fact)"
            + (", including every expert-read change you accept and every current-news change." if (rd / "expert_read.md").exists() else "."),
        ], brief_path, confirm="editor")
        return

    # 9b. independent fact-check (agent) ----------------------------------------------------------------------------
    if "verify" not in st["done"]:
        if not (rd / "verify_claims.json").exists() or st.get("verify_draft") != draft_sig:
            from .verify import build
            build(rd)
            st["verify_draft"] = draft_sig
            _save_state(rd, st)
        _task("FACT-CHECK (role: independent fact-checker)", [
            "Give this task to a fresh agent that has not written or researched the page (Claude Code: the",
            "`seo-fact-checker` agent; Cursor/Codex/Antigravity: a new chat with this task, or if you cannot, do it",
            "yourself without opening the dossier, writer pack or outline).",
            "",
            "1. Read plugins/fact_check/SKILL.md fully. It is your complete instruction for this task.",
            f"2. Check every sentence in {R}/verify_sheet.md against the page it credits; open pages with your own",
            f"   fetch tool or: {CMD()} read <url>",
            f"3. Fix or cut unsupported sentences in {R}/draft.md, and write {R}/verify.md (one line per C-number).",
        ], brief_path, confirm="verify")
        return

    # 9c. internal links: the last writing stage, on the finished and fact-checked page -----------------------------
    if "internal_links" not in st["done"]:
        from .links import build
        cands = build(rd)
        _task("INTERNAL LINKS (role: internal linker)", [
            "Claude Code: give this to the `seo-writer` agent. Other tools: do it yourself.",
            "",
            "1. Read plugins/internal_links/SKILL.md fully (Koray Tuğberk Gübür's interlinking rules). It is your complete",
            "   instruction for this task.",
            f"2. Read {R}/internal_links_plan.md: {len(cands)} client pages ranked against the paragraphs they fit.",
            f"3. Add 3 to 6 contextual links in {R}/draft.md (each target's main term as the anchor, in a sentence about it,",
            "   never in the first sentence under a heading), and change nothing else.",
            f"4. Write {R}/internal_links.md: Links added, Not linked, Anchors waiting.",
        ], brief_path, confirm="internal_links")
        return

    # the page says when it was last checked (a trust signal for readers and raters, and for answer engines)
    ft = final.read_text(encoding="utf-8")
    if ft.startswith("---\n") and "\nupdated:" not in ft.split("\n---", 1)[0]:
        from datetime import date
        final.write_text(ft.replace("---\n", f"---\nupdated: {date.today().isoformat()}\n", 1), encoding="utf-8")
    st["validated_final"] = hashlib.sha256(final.read_bytes()).hexdigest()

    # 10. eval (final.md is current: step 8 re-validates after every edit, the editor's included) ---------------------
    if not (rd / "eval.md").exists() or (rd / "eval.md").stat().st_mtime < final.stat().st_mtime:
        from .evaluate import evaluate
        _quiet(evaluate, rd)
    st["done"]["complete"] = C.now_iso()
    _save_state(rd, st)
    if brief.get("batch_plan"):
        from .batch import next_page
        print(f"PAGE COMPLETE: {R}/final.md")
        return next_page(brief["batch_plan"], mode, {"id": brief["batch_item"], "result": str(rd / "final.md")})
    print(SEP)
    print("DONE")
    print(SEP)
    print(f"Page:   {R}/final.md")
    print(f"Report: {R}/report.md")
    print(f"Scores sheet (for a reviewer): {R}/eval.md")
    print("Stop here. Reply with these three paths and nothing else.")


FIX_ROUNDS = 2  # fix rounds after the combined first check, before the run stops instead of looping


def _review_checks(rd: Path, limit: int = 25) -> list[str]:
    """The CHECK items of review.md (a claim with no fact behind it, or a number its fact doesn't carry), with the
    closest-fact lines under each, ready to print in the fix task."""
    from .review import review
    _quiet(review, rd)
    lines = (rd / "review.md").read_text(encoding="utf-8").splitlines()
    out, n, keep = [], 0, False
    for ln in lines:
        if ln.startswith("- **CHECK**"):
            n += 1
            keep = n <= limit
            if keep:
                out.append(ln.replace("- **CHECK** ", "- CHECK "))
        elif keep and ln.startswith("  - "):
            out.append(ln)
        elif not ln.startswith("  "):
            keep = False
    if n > limit:
        out.append(f"- …and {n - limit} more CHECK items in {rd.name}/review.md")
    return out


def _coverage_gaps(rd: Path, md: str) -> list[dict]:
    """Required coverage items the page shows no sign of answering. Lexical, so the writer judges each one: a
    paraphrase can answer an item without its words."""
    from .article_context import content_words
    ctx = C.load_json(rd / "article_context.json") or {}
    page = ctx.get("page") or {}
    syn = page.get("synonyms")
    body = content_words(md, syn)
    main = content_words(page.get("target_query", ""), syn)
    out, seen = [], set()
    for c in ctx.get("coverage_requirements", []):
        if not c.get("required"):
            continue
        words = content_words(c["text"], syn) - main
        key = frozenset(words)
        if not words or key in seen:
            continue
        seen.add(key)
        if len(words & body) < max(1, round(0.6 * len(words))):
            out.append(c)
    return out


def _stitch(rd: Path, plan: dict) -> list[str]:
    """Join the parts writers drafted at the same time into draft.md. Returns the parts still missing."""
    parts = plan.get("parts") or []
    files = {pt["id"]: rd / f"draft_part_{pt['id']}.md" for pt in parts}
    missing = [k for k, f in files.items() if not f.exists() or not f.read_text(encoding="utf-8").strip()]
    if missing:
        return missing
    import re
    out = []
    for k in [pt["id"] for pt in parts]:
        t = files[k].read_text(encoding="utf-8").strip()
        if out:  # only part A carries the front matter, the H1 and the opening
            t = re.sub(r"^---\n.*?\n---\s*", "", t, flags=re.S)
            t = re.sub(r"^#\s+[^\n]*\n+", "", t)
        out.append(t)
    (rd / "draft.md").write_text("\n\n".join(out).rstrip() + "\n", encoding="utf-8")
    return []


def _next_flow(brief: dict, brief_path: str, rd: Path, st: dict, R: str, mode: str | None) -> None:
    """The one flow, every run: research scripts and the page plan (seconds) → the writers draft the plan's parts
    at the same time → one combined check (lint blocks, claims no fact carries, planned headings missing) → at most
    two fix rounds → validate → done. The expert's, fact-checker's and internal linker's work is built into the plan
    (facts and links per heading, page job) and into the checks (every figure against a fact, every planned heading
    on the page), so no stage waits on another agent."""
    import hashlib
    draft, final = rd / "draft.md", rd / "final.md"
    plan = C.load_json(rd / "plan.json") or {}
    if not draft.exists():
        if not (rd / "write_brief.md").exists() or not plan:
            from .kgdoc import write_docs
            from .writebrief import build as write_brief
            write_docs(rd)
            write_brief(rd)
            plan = C.load_json(rd / "plan.json") or {}
        parts = plan.get("parts") or []
        if len(parts) > 1:
            missing = _stitch(rd, plan)
            if not missing:
                return next_step(brief_path, mode)
            each = [f"Run folder: {R}",
                    f"The plan in {R}/write_brief.md (section 2) is split into parts {', '.join(p['id'] for p in parts)}. "
                    "Write them at the same time:",
                    f"Start {len(parts)} `seo-writer` sub-agents in ONE turn (they run in parallel), one per part, each given "
                    "the instructions below with its part letter. How, in each tool (the installer set the writer up in all):",
                    "- Claude Code: the Agent tool with subagent_type `seo-writer`, all calls in one message.",
                    "- Cursor: the `seo-writer` subagent, once per part, in one message.",
                    "- Codex: \"spawn one `seo_writer` agent per part, wait for all of them\".",
                    "- Antigravity and Gemini CLI: invoke the `seo-writer` subagent once per part, concurrently.",
                    "- VS Code Copilot: the agent tool with `seo-writer`, once per part.",
                    "- A tool without sub-agents (e.g. Windsurf): write the parts yourself, one after another.",
                    "",
                    "Instructions for the writer of part X:",
                    f"1. Read RULES_CARD.md and {R}/write_brief.md: sections 1, 3 and 4, and part X of section 2. Nothing else.",
                    f"2. Write {R}/draft_part_X.md with a single write: only part X's headings, in the plan's order (H2s "
                    "and their H3s, Markdown only). Part A also starts with the front matter (title, meta_description), "
                    "the H1 and the opening.",
                    "3. Each heading answers its question in its first one or two sentences; facts in your own words, "
                    "figures exactly as their notes give them; the links listed under a heading go in that section.",
                    "4. Stop. No rereading, no research, no other files: the check that follows lists every problem.",
                    ""]
            if missing and len(missing) < len(parts):
                each.append("Still to write: part " + ", part ".join(missing) + " (the others are done).")
            each.append(_length_line(rd))
            _task("DRAFT THE PAGE (role: writers, in parallel)", each, brief_path)
            return
        _task("DRAFT THE PAGE (role: writer)", [
            f"Run folder: {R}",
            f"1. Read RULES_CARD.md and {R}/write_brief.md. Nothing else.",
            f"2. Write {R}/draft.md with a single write: front matter (title, meta_description), the H1, the opening, then "
            "every heading of the plan in its order. Markdown only.",
            "3. Each heading answers its question in its first one or two sentences; facts in your own words, figures "
            "exactly as their notes give them; the links listed under a heading go in that section.",
            "4. Stop. No rereading, no research, no other files: the check that follows lists every problem.",
            "",
            _length_line(rd),
        ], brief_path)
        return
    from .lint import lint_text, load_research
    from .timing import mark
    from .plan import check as plan_check
    sheet = C.load_json(rd / "fact_sheet.json")
    lm = C.load_json(rd / "link_map.json") or {}
    from .autofix import fix_text
    md, n_fixed = fix_text(draft.read_text(encoding="utf-8"))  # Koray's mechanical rules, fixed by script, not by a round
    if n_fixed:
        draft.write_text(md, encoding="utf-8")
    mark(rd, "lint", "start")
    try:
        res = lint_text(md, sheet, lm, load_research(rd))
    finally:
        mark(rd, "lint", "end")
    C.save_json(rd / "lint.json", res)
    blocks = [f for f in res["findings"] if f["severity"] == "block"]
    gaps = plan_check(rd, md)
    sig = hashlib.sha256(draft.read_bytes()).hexdigest()
    first = not st["done"].get("check")
    if blocks or gaps or first:
        checks = _review_checks(rd) if first else []
        st["done"]["check"] = st["done"].get("check") or C.now_iso()
        _save_state(rd, st)
        if blocks or gaps or checks:
            if not first and _rounds(rd, st, "check", FIX_ROUNDS, R, brief_path, blocks or gaps):
                return
            lines = [f"Fix {R}/draft.md in place, in one pass. Edit only what is named here; never rewrite the page.", ""]
            if gaps:
                lines += [f"A. {len(gaps)} planned heading(s) missing: add each with its answer (write_brief.md section 2 "
                          "lists its facts).", ""] + [f"- {g}" for g in gaps] + [""]
            if blocks:
                lines += [f"B. {len(blocks)} blocking line(s): fix each one.", ""] + _finding_lines(blocks) + [""]
            if checks:
                lines += ["C. Claims no fact carries: make the sentence say what its closest fact says (same figure, group, "
                          "condition and strength), or cut it. A figure you worked out from facts needs its inputs in the "
                          "same paragraph.", ""] + checks
            _task("FIX THE DRAFT (role: writer)", lines, brief_path)
            return
    draft_sig = hashlib.sha256(draft.read_bytes()).hexdigest()
    if not final.exists() or st.get("validated_draft") != draft_sig:
        from .validate import validate
        ok, out = _quiet(validate, str(rd))
        if not ok:
            if _rounds(rd, st, "validate", FIX_ROUNDS, R, brief_path, out.strip()[-3500:]):
                return
            _task("FIX VALIDATION (role: writer)", [
                f"Validation failed. Fix each blocking line below in {R}/draft.md and change nothing else:", "",
                out.strip()[-3500:],
            ], brief_path)
            return
        st["validated_draft"] = draft_sig
        _save_state(rd, st)
    ft = final.read_text(encoding="utf-8")
    if ft.startswith("---\n") and "\nupdated:" not in ft.split("\n---", 1)[0]:
        from datetime import date
        final.write_text(ft.replace("---\n", f"---\nupdated: {date.today().isoformat()}\n", 1), encoding="utf-8")
    if not (rd / "eval.md").exists() or (rd / "eval.md").stat().st_mtime < final.stat().st_mtime:
        from .evaluate import evaluate
        _quiet(evaluate, rd)
    try:
        from .schema import build as build_schema
        build_schema(rd)  # JSON-LD naming the page's central entity and the entities it covers
    except Exception as e:  # structured data is a bonus; never fail a finished page on it
        print(f"note: schema.json not written ({e})")
    st["done"]["complete"] = C.now_iso()
    _save_state(rd, st)
    if brief.get("batch_plan"):
        from .batch import next_page
        print(f"PAGE COMPLETE: {R}/final.md")
        return next_page(brief["batch_plan"], mode, {"id": brief["batch_item"], "result": str(rd / "final.md")})
    t =(C.load_json(rd / "timing.json") or {}).get("events") or []
    took = f" in {int(t[-1]['t'] - t[0]['t']) // 60} min {int(t[-1]['t'] - t[0]['t']) % 60} s" if len(t) > 1 else ""
    print(SEP)
    print("DONE" + took)
    print(SEP)
    print(f"Page:   {R}/final.md")
    print(f"Report: {R}/report.md")
    print(f"Scores sheet (for a reviewer): {R}/eval.md")
    print("Stop here. Reply with these three paths and nothing else.")


def parse_request(text: str) -> dict:
    """What the user typed after /page-seo, in their own words: a client, a keyword and, optionally, instructions.

    "nutmeg: what is a lifetime isa | first-time buyers, plain English"
    "what is a lifetime isa for nutmeg -- keep it short"
    "\"how to paint a fence\" ronseal, aimed at beginners"
    "best running shoes for example.com"      (a domain with no profile yet is onboarded)
    The client is found by its profile slug, name or domain; the keyword is a quoted phrase if there is one, else
    the text before "|", " -- " or a new line (or before the first comma or full stop when the rest is longer);
    everything else is the instructions."""
    import re
    raw = " ".join((text or "").split()) if "\n" not in (text or "") else text.strip()
    low = raw.lower()
    clients = []
    for p in sorted((C.ROOT / "clients").glob("*.yaml")):
        prof = C.load_yaml(p) or {}
        dom = (prof.get("domain") or "").lower().removeprefix("www.")
        names = {p.stem.lower(), (prof.get("client") or "").lower(), dom, dom.split(".")[0]}
        names |= {a.lower() for a in prof.get("client_aliases") or []}
        names |= {n.replace("-", " ") for n in names}  # "gardening-express" is typed "gardening express"
        first = ((prof.get("client") or "").lower().split() or [""])[0]
        clients.append((p.stem, {n for n in names if len(n) >= 3}, first))
    # people shorten a client to its first word ("tapton" for Tapton Capital): allowed when it is distinctive
    # (5+ letters) and no other client shares it
    firsts = Counter(f for _, _, f in clients if len(f) >= 5)
    clients = [(s, n | ({f} if firsts.get(f) == 1 else set())) for s, n, f in clients]
    found, span = None, None
    for slug, names in clients:
        for n in sorted(names, key=len, reverse=True):
            m = re.search(rf"(?<![\w.-]){re.escape(n)}(?![\w-])", low)
            if m and (span is None or len(n) > span[1] - span[0]):
                found, span = slug, (m.start(), m.end())
    new_domain = None
    if not found:
        m = re.search(r"(?<![\w@/.-])((?:https?://)?(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,})(?:/\S*)?", low)
        if m:
            new_domain = re.sub(r"^https?://(www\.)?|^www\.", "", m.group(1))
            span = (m.start(), m.end())
    rest = raw
    if span:  # take the client out, with the little words that attach it ("for", "client", ":")
        protocol = re.search(r"(?:https?://(?:www\.)?|www\.)$", raw[:span[0]], re.I)
        if protocol:
            span = (protocol.start(), span[1] + (1 if raw[span[1]:].startswith("/") else 0))
        rest = raw[:span[0]] + " " + raw[span[1]:]
        rest = re.sub(r"(?i)\b(for|client|on|at|by)\s*(?=\s*$|\s*[|:,.\-]|\s+--)", " ", rest)
        rest = re.sub(r"(?i)(^|\s)(for|client)\s*:?\s*$", " ", rest)
    rest = re.sub(r"^\s*[:,\-–|]+\s*", "", rest.strip())
    q = re.search(r"[\"“']([^\"”']{3,})[\"”']", rest)
    if q:
        keyword = q.group(1)
        instructions = (rest[:q.start()] + " " + rest[q.end():])
    else:
        parts = re.split(r"\s*(?:\||\s--\s|\n)\s*", rest, maxsplit=1)
        keyword, instructions = parts[0], (parts[1] if len(parts) > 1 else "")
        if not instructions:
            m = re.match(r"^([^,.;]{6,90}?)[,.;]\s+(.{12,})$", keyword)
            if m:
                keyword, instructions = m.group(1), m.group(2)
    keyword = re.sub(r"(?i)^\s*(keyword|query|topic|write( a page| an article)?( about| on)?)\s*:?\s*", "", keyword)
    keyword = re.sub(r"(?i)\s+(for|on|client)\s*$", "", keyword).strip(" :,.-–\"'“”").lower()
    instructions = re.sub(r"^\s*[:,\-–|]+\s*|\s*[:,\-–|]+\s*$", "", " ".join(instructions.split())).strip()
    return {"client": found, "new_domain": new_domain, "keyword": keyword, "instructions": instructions,
            "clients": [s for s, _ in clients]}


def start(text: str, mode: str | None = None) -> None:
    """The single entry point behind /page-seo: a brief file, or a keyword with a client and instructions."""
    from .prep import load_brief
    try:  # an existing brief (path or name) runs as it is
        load_brief(text.strip())
        print(f"BRIEF {text.strip()}")
        return next_step(text.strip(), mode)
    except SystemExit:
        pass
    from .batch import route_request
    if route_request(text, mode):
        return
    import re
    # a page address in the request means "this page": decide its type and keyword from the page itself, first
    um = re.search(r"https?://[^\s\"'<>|]+|(?<![\w@./-])(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:/[^\s\"'<>|]*)?",
                   text, re.I)
    if um:
        from urllib.parse import urlparse
        from .sitecontext import website_url
        address = website_url(um.group(0).rstrip(".,;):"))
        rest = (text[:um.start()] + " " + text[um.end():]).strip(" :|,")
        remainder = parse_request(rest)["keyword"]
        meaningful = re.sub(r"(?i)\b(please|write|rewrite|create|make|content|copy|for|this|the|website|site|page|"
                            r"homepage|home|client|seo|on|of|and|a|an|can|you)\b", " ", remainder).strip(" :|,")
        if urlparse(address).path not in ("", "/") or not meaningful:
            return start_from_page(address, rest, mode)
    req = parse_request(text)
    if not req["client"] and req["new_domain"]:
        from .sitecontext import client_for_website
        req["client"] = client_for_website(req["new_domain"], create=True)[0]
    if not req["client"]:
        from .sitecontext import resolve_client
        context = resolve_client()
        if context:
            req["client"] = context[0]
            print(f"WEBSITE CONTEXT: {context[1].get('domain')} (from {context[2]})")
    if not req["client"]:
        if (C.ROOT / "briefs" / f"{C.slugify(req['keyword'])}.yaml").exists():
            req["client"] = "__brief__"  # fall back to a named brief only after resolving this project's website
    if not req["client"]:
        raise SystemExit("NEED A CLIENT: give the website domain or page link; no unambiguous website context was found. Known clients: "
                         + ", ".join(req["clients"]) + ". Then run the same command again with it, e.g. "
                         f"/page-seo <client>: {req['keyword']}")
    if not req["keyword"]:
        raise SystemExit("NEED A KEYWORD: give a search query or the page URL to derive its topic")
    if req["client"] != "__brief__":
        from .sitecontext import inventory, match_keyword, keyword_matches
        known_site = inventory(req["client"])
        matching_page = match_keyword(req["keyword"], known_site)
        if matching_page:
            return start_from_page(matching_page["url"], req["instructions"], mode, target_query=req["keyword"])
        if keyword_matches(req["keyword"], known_site):
            raise SystemExit("NEED A PAGE: multiple existing pages match this keyword; give the intended page URL. The website context is already known.")
    slug = C.slugify(req["keyword"])
    path = C.ROOT / "briefs" / f"{slug}.yaml"
    if path.exists() and req["client"] != "__brief__":
        b = C.load_yaml(path) or {}
        prof = C.load_yaml(C.ROOT / "clients" / f"{req['client']}.yaml") or {}
        if prof.get("client") and b.get("client") != prof.get("client"):
            slug = f"{slug}-{req['client']}"  # the same keyword for another client is another page
            path = C.ROOT / "briefs" / f"{slug}.yaml"
    if not path.exists():
        from .briefgen import make_brief
        from .pagetype import infer_type
        ptype, pwhy = infer_type(req["instructions"], req["keyword"])
        print(f"PAGE TYPE: {ptype} ({pwhy})")
        _quiet(make_brief, req["client"], req["keyword"], slug=slug, page_type=ptype,
               instructions=req["instructions"] or None,
               page_type_source="explicit" if pwhy.startswith("the request says") else "keyword")
    elif req["instructions"]:
        import yaml
        b = C.load_yaml(path) or {}
        if b.get("instructions") != req["instructions"]:
            b["instructions"] = req["instructions"]
            from .pagetype import explicit_type
            requested_type = explicit_type(req["instructions"])
            if requested_type:
                from .briefgen import set_page_type
                profile_path = C.ROOT / "clients" / f"{req['client']}.yaml"
                set_page_type(b, requested_type, "explicit", C.load_yaml(profile_path) if profile_path.exists() else b)
            path.write_text(yaml.safe_dump(b, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if req["client"] != "__brief__":
        from .sitecontext import inventory, inventory_path
        known_site = inventory(req["client"])
        if known_site:
            import yaml
            b = C.load_yaml(path)
            b.update(site_inventory=str(inventory_path(req["client"])), source_context=known_site.get("source_context") or {})
            path.write_text(yaml.safe_dump(b, sort_keys=False, allow_unicode=True), encoding="utf-8")
    from .market import from_text
    said = from_text(text)
    if said:
        import yaml as _y
        bb = C.load_yaml(path) or {}
        if bb.get("locale") != said:
            bb["locale"] = said
            path.write_text(_y.safe_dump(bb, sort_keys=False, allow_unicode=True), encoding="utf-8")
    brief_path = f"briefs/{slug}.yaml"
    who = (C.load_yaml(path) or {}).get("client") or req["client"]
    print(f"MARKET: {(C.load_yaml(path) or {}).get('locale')} (from {'your request' if said else 'the client profile'})")
    print(f"BRIEF {brief_path}  (client: {who}; keyword: \"{req['keyword']}\""
          + (f"; instructions: {req['instructions']}" if req["instructions"] else "") + ")")
    print(f"From here on, every command uses this brief: {brief_path}")
    next_step(brief_path, mode)


def start_from_page(url: str, rest: str, mode: str | None = None, target_query: str | None = None) -> None:
    """/page-seo with a page address: page type first, then the main keyword, then research (WORKFLOW 0)."""
    import re
    import yaml
    from .pagetype import intake, explicit_type
    from .sitecontext import client_for_website
    url = url if url.startswith("http") else "https://" + url
    client, profile = client_for_website(url, create=True)
    print(f"PAGE INTAKE: reading {url} …")
    info = intake(url)
    if target_query:
        info["target_query"] = target_query
    requested_type = explicit_type(rest)
    if info.get("status") is not None and not info["exists"] and info.get("status") not in (404, 410) and not (target_query and requested_type):
        raise SystemExit(f"NEED A PAGE: could not read {url} ({info.get('read_state')}, {info.get('status')}). "
                         "Give a readable page or a list row with the target keyword and page_type; the website is already known.")
    if requested_type:
        info["page_type"] = requested_type
        info["evidence"].insert(0, "explicit page type in the operator's instructions")
    if not info["target_query"]:
        info["target_query"] = (C.load_yaml(C.ROOT / "clients" / f"{client}.yaml") or {}).get("client", client).lower()
    # what's left of the request is the operator's instructions, without the words that only point at the page
    instr = re.sub(r"(?i)\b(please|kindly|can you|write|rewrite|re-write|create|make|optimi[sz]e|improve|update|do|"
                   r"the|this|that|some|new|seo|content|copy|page|article|blog|post|text|for|of|on|and|client|"
                   r"website|site|url|link|here|is|it)\b", " ", rest)
    instr = rest.strip(" :,.-–|") if re.search(r"[a-z]{3,}", instr, re.I) else ""
    instr = re.sub(r"(?i)^\s*(please\s+)?(write|rewrite|create|make|optimi[sz]e|improve|update)?\s*(the\s+)?"
                   r"(seo\s+)?(content|copy|page|article)?\s*(for\s+)?(this\s+)?(client\s+)?(and\s+)?(page\s*)?[:,.-]*\s*", "",
                   instr).strip(" :,.-–|")
    task = "rewrite" if info["exists"] or (info.get("status") is not None and info.get("status") not in (404, 410)) else "new"
    seg = [x for x in re.sub(r"https?://[^/]+", "", info["page_url"]).split("/") if x]
    slug = C.slugify(seg[-1] if seg else f"{client}-home")
    path = C.ROOT / "briefs" / f"{slug}.yaml"
    if path.exists() and C.clean_url((C.load_yaml(path) or {}).get("page_url") or "").rstrip("/") != C.clean_url(info["page_url"]).rstrip("/"):
        slug = f"{slug}-{client}"
        path = C.ROOT / "briefs" / f"{slug}.yaml"
        if path.exists() and C.clean_url((C.load_yaml(path) or {}).get("page_url") or "").rstrip("/") != C.clean_url(info["page_url"]).rstrip("/"):
            import hashlib
            slug += "-" + hashlib.sha256(info["page_url"].encode()).hexdigest()[:8]
            path = C.ROOT / "briefs" / f"{slug}.yaml"
    from .briefgen import make_brief
    if not path.exists():
        _quiet(make_brief, client, info["target_query"], url=info["page_url"], page_type=info["page_type"], task=task,
               slug=slug, instructions=instr or None, page_type_source="explicit" if requested_type else "page")
    b = C.load_yaml(path) or {}
    previous_intake = b.get("page_intake") or {}
    # A saved operator override wins over inference from the live page.
    chosen_type = requested_type or (b.get("page_type") if b.get("page_type_source") == "explicit" else None) or info["page_type"]
    from .briefgen import set_page_type
    set_page_type(b, chosen_type, "explicit" if requested_type or b.get("page_type_source") == "explicit" else "page")
    b.update({"page_url": info["page_url"], "task": task,
              "page_intake": {"type": info["page_type"], "keyword_from": "H1" if info["h1"] else "address",
                              "evidence": info["evidence"]}})
    old_leaf = " ".join(seg[-1].replace("-", " ").split()) if seg else ""
    legacy_leaf = previous_intake.get("keyword_from") == "address" and b.get("target_query") == old_leaf
    if not b.get("target_query") or b.get("target_query") == previous_intake.get("inferred_query") or legacy_leaf:
        b["target_query"] = info["target_query"]
    b["page_intake"]["inferred_query"] = info["target_query"]
    if target_query:
        b["target_query"] = target_query
    from .sitecontext import inventory, inventory_path
    known_site = inventory(client)
    if known_site:
        b.update(site_inventory=str(inventory_path(client)), source_context=known_site.get("source_context") or {})
    if instr:
        b["instructions"] = instr
    from .market import from_text
    said = from_text(rest)
    loc = said or info.get("locale")
    if loc and loc != b.get("locale"):
        b["locale"] = loc
    market_why = ("your request" if said else ("the page (" + ", ".join(info.get("locale_evidence") or []) + ")"
                                              if info.get("locale") else "the client profile"))
    path.write_text(yaml.safe_dump(b, sort_keys=False, allow_unicode=True), encoding="utf-8")
    brief_path = f"briefs/{slug}.yaml"
    print(f"PAGE TYPE: {chosen_type} ({'; '.join(info['evidence'][:4])})")
    print(f"MAIN KEYWORD: \"{b['target_query']}\" (from the page's {'H1' if info['h1'] else 'address'}; change "
          f"`target_query` in {brief_path} to override)")
    print(f"TASK: {task} ({'the page exists' if info['exists'] else 'no live page at that address'})")
    print(f"MARKET: {b.get('locale')} (from {market_why})")
    print(f"BRIEF {brief_path}  (client: {b.get('client')}" + (f"; instructions: {instr}" if instr else "") + ")")
    print(f"From here on, every command uses this brief: {brief_path}")
    next_step(brief_path, mode)


def read_page(url: str) -> bool:
    """Print a page's readable text, for agents whose host has no page-fetch tool. A plain request with the
    pipeline's normal headers: no rendering service, no stealth. A refusal is reported, never worked around."""
    res = C.run_async(C.fetch_many([{"url": url, "kind": "page", "parse": "doc"}], timeout=20.0)).get(url) or {}
    st, state = res.get("status"), res.get("state")
    if state == "not_html":
        import httpx
        try:
            from pypdf import PdfReader
            r = httpx.get(url, headers=C.HEADERS, follow_redirects=True, timeout=40)
            reader = PdfReader(io.BytesIO(r.content))
            print(f"URL: {r.url}\nSTATUS: {r.status_code}\nTYPE: pdf, {len(reader.pages)} pages\n")
            for i, pg in enumerate(reader.pages, 1):
                print(f"--- page {i}\n{(pg.extract_text() or '').strip()}")
            return True
        except Exception as e:
            print(f"UNREADABLE: {url} is not HTML and could not be read as a PDF ({type(e).__name__}).")
            return False
    if st in (404, 410):
        print(f"NOT FOUND: {url} returned {st}. Search for the page's current address; never cite this URL.")
        return False
    if st != 200 or state not in ("ok", "needs_js"):
        print(f"BLOCKED OR UNAVAILABLE: {url} returned {st or type(res.get('error')).__name__} ({state}).")
        print("Do not try to get round it. Use another route to the same fact (plugins/deep_research/SKILL.md section 8).")
        return False
    print(f"URL: {res.get('final_url') or url}\nSTATUS: {st}\nTITLE: {res.get('title', '')}\n")
    for tag, text in res.get("blocks", []):
        print(("#" * int(tag[1]) + " " if tag[0] == "h" and tag[1:].isdigit() else "- " if tag == "li" else "") + text)
    if state == "needs_js":
        print("\nNOTE: little text came back; the page may build its content with scripts. Prefer another source.")
    return True


def doctor() -> bool:
    """Check that this machine can run the pipeline. Never prints key values."""
    import importlib
    import sys
    ok = True

    def line(good: bool, msg: str, fix: str = "", hard: bool = True):
        nonlocal ok
        print(("OK   " if good else ("FAIL " if hard else "WARN ")) + msg + ("" if good or not fix else f"\n     fix: {fix}"))
        if not good and hard:
            ok = False
    line(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (3.10+ needed)", "install Python 3.10 or newer")
    for mod, pkg in (("httpx", "httpx"), ("yaml", "PyYAML"), ("pycountry", "pycountry"), ("pypdf", "pypdf")):
        try:
            importlib.import_module(mod)
            line(True, f"package {pkg}")
        except Exception:
            line(False, f"package {pkg} missing", f"{PY()} install.py   (in {C.ROOT.as_posix()})")
    # spaCy sharpens matching and the knowledge graph; without it the pipeline runs on plain-rules tokens
    try:
        from .nlp import import_spacy
        import_spacy().load("en_core_web_sm")
        line(True, "spaCy and en_core_web_sm")
    except Exception as e:
        blocked = "Application Control" in str(e) or "DLL load failed" in str(e)
        line(False, "spaCy unavailable" + (" (Windows Application Control is blocking its compiled library)" if blocked
                                          else "") + ": semantic extraction runs with plain rules; entity types are less precise",
             "allow Python packages in Windows Security (Smart App Control) if you want spaCy back" if blocked else
             f"{PY()} -m spacy download en_core_web_sm", hard=False)
    from . import serper, spider
    line(bool(serper.api_key() or spider.api_key()), "search key present (SERPER_API_KEY or SPIDER_API_KEY in .env)",
         f"{PY()} install.py --keys   (asks for the keys and writes .env; or add SERPER_API_KEY=... to "
         f"{(C.ROOT / '.env').as_posix()})")
    line(bool(spider.api_key()), "SPIDER_API_KEY present (rendered page content)",
         "add SPIDER_API_KEY=... to .env; without it pages are fetched directly", hard=False)
    gi = C.ROOT / ".gitignore"
    line(gi.exists() and ".env" in gi.read_text(encoding="utf-8").split(), ".env is git-ignored", "add .env to .gitignore")
    from .harness import manifests
    ms = manifests()
    bad = [f"{n} needs {d}" for n, m in ms.items() for d in m.get("needs", []) if d not in ms]
    bad += [f"{n} has no SKILL.md" for n, m in ms.items() if m.get("kind") == "agent"
            and not (C.ROOT / "plugins" / n / "SKILL.md").exists()]
    line(not bad, f"{len(ms)} plugins, dependencies resolve" + ("" if not bad else ": " + "; ".join(bad)))
    for f in ("WORKFLOW.md", "RULES.md", "AGENTS.md", "docs/EVAL_RUBRIC.md", "plugins/deep_research/SKILL.md",
              "plugins/expert_review/SKILL.md"):
        line((C.ROOT / f).exists(), f"{f} present")
    briefs = sorted(p.name for p in (C.ROOT / "briefs").glob("*.yaml"))
    print(f"INFO {len(briefs)} briefs in briefs/, {len(list((C.ROOT / 'clients').glob('*.yaml')))} client profiles in clients/")
    print("DOCTOR PASS" if ok else "DOCTOR FAIL")
    return ok


def _current_run(brief: dict) -> Path | None:
    from .prep import run_dir
    rd = run_dir(brief)
    return rd if rd.exists() else None
