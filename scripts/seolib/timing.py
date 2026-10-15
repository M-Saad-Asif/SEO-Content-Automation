"""timing.json: every script call stamps itself, so the agent never has to.

The driver records agent task boundaries; fact registration is a nested span.
Legacy logs without those boundaries expose unclassified work before checks.
Interactive waits (`seo.py mark <run> wait start|end`) are subtracted.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import common as C

# one mode, one budget: research scripts and the plan in under a minute, the parts drafted at the same time, one
# combined fix pass, five minutes in all
BUDGET = {"prep": 45, "draft": 150, "lint": 5, "fix": 60, "validate": 15, "total": 300}


def mark(rd: Path, step: str, ev: str, fresh: bool = False) -> None:
    p = rd / "timing.json"
    with C.file_lock(p):
        _mark(p, step, ev, fresh)


def _mark(p: Path, step: str, ev: str, fresh: bool) -> None:
    if fresh and p.exists():  # keep the previous attempt's evidence
        n = len(list(p.parent.glob("timing.prev-*.json"))) + 1
        p.replace(p.parent / f"timing.prev-{n}.json")
    data = None if fresh else C.load_json(p)
    if not data or not isinstance(data, dict):
        data = {"events": []}
    data["events"].append({"step": step, "ev": ev, "t": round(time.time(), 2), "at": C.now_iso()})
    data["summary"] = summarise(data["events"])
    C.save_json(p, data)


def summarise(events: list[dict]) -> dict:
    def first(step, ev, after=0.0):
        return next((e["t"] for e in events if e["step"] == step and e["ev"] == ev and e["t"] >= after), None)

    def last(step, ev):
        xs = [e["t"] for e in events if e["step"] == step and e["ev"] == ev]
        return xs[-1] if xs else None

    waits, open_w = 0.0, None
    for e in events:
        if e["step"] == "wait" and e["ev"] == "start":
            open_w = e["t"]
        elif e["step"] == "wait" and e["ev"] == "end" and open_w:
            waits += e["t"] - open_w
            open_w = None

    s: dict = {}
    starts, measured = {}, {}
    for e in events:
        if not e["step"].startswith("agent:") and e["step"] != "facts":
            continue
        if e["ev"] == "start":
            starts.setdefault(e["step"], e["t"])
        elif e["ev"] == "end" and e["step"] in starts:
            key = e["step"].removeprefix("agent:")
            measured[key] = measured.get(key, 0) + max(0, e["t"] - starts.pop(e["step"]))
    p0, p1 = first("prep", "start"), first("prep", "end")
    if p0 is None:
        return s
    if p1:
        s["prep"] = p1 - p0
    research_end = last("research", "event")
    # every lint or validate call is a (start, end) pair; the gaps between them are fix time
    checks = []
    for e in events:
        if e["step"] in ("lint", "validate") and e["ev"] == "start":
            checks.append([e["step"], e["t"], None])
        elif e["step"] in ("lint", "validate") and e["ev"] == "end" and checks and checks[-1][2] is None:
            checks[-1][2] = e["t"]
    checks = [c for c in checks if c[2]]
    if p1 and research_end and research_end > p1:
        s["research"] = research_end - p1
    # fact checks (--add-fact) can happen before or between drafts: count them, don't let them shift the draft clock
    verify = [e["t"] for e in events if e["step"] == "verify" and e["ev"] == "event"]
    if verify:
        s["verify_calls"] = len(verify)
    draft_from = max(x for x in (p1, research_end) if x) if p1 else None
    if draft_from and checks:
        # Old logs have no agent boundaries: this includes research, expert and outline, not just drafting.
        s["precheck_work"] = max(0.0, checks[0][1] - draft_from)
    lints = [c for c in checks if c[0] == "lint"]
    vals = [c for c in checks if c[0] == "validate"]
    if lints:
        s["lint"] = sum(c[2] - c[1] for c in lints)
    if vals:
        s["validate"] = sum(c[2] - c[1] for c in vals)
    s["check_rounds"] = len(checks)
    fix = sum(max(0.0, b[1] - a[2]) for a, b in zip(checks, checks[1:]))
    if fix:
        s["fix"] = fix
    v1 = vals[-1][2] if vals else None
    end = max((e["t"] for e in events if e["step"] != "wait"), default=p1)
    if end:
        s["waits"] = waits
        s["total"] = end - p0 - waits
    if measured:
        if any(e["step"].startswith("agent:") for e in events):
            s.pop("precheck_work", None)
            s.pop("fix", None)
        s.update(measured)
    s = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items()}
    s["over_budget"] = [k for k, v in s.items() if k in BUDGET and isinstance(v, (int, float)) and v > BUDGET[k]]
    return s


def table(summary: dict, mode: str = "quick") -> str:
    budget = BUDGET
    over = [k for k, v in summary.items() if k in budget and isinstance(v, (int, float)) and v > budget[k]]
    summary = {**summary, "over_budget": over}
    rows = [f"| Step ({mode} mode) | Seconds | Budget |", "|---|---:|---:|"]
    for k in ("prep", "precheck_work", "research", "facts", "expert", "outline", "draft", "lint", "review",
              "expert_read", "editor", "verify", "internal_links", "fix", "validate", "waits", "total"):
        if k in summary:
            b = budget.get(k, "")
            flag = " ⚠" if k in summary.get("over_budget", []) else ""
            label = {"prep": "research (plugins)", "precheck_work": "work before first check (legacy log)",
                     "facts": "fact registration (included in agent stages)", "expert_read": "expert read",
                     "internal_links": "internal links"}.get(k, k)
            rows.append(f"| {label} | {summary[k]}{flag} | {b} |")
    return "\n".join(rows)
