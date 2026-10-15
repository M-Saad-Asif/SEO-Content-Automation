"""Does the research reach the writer? For each kind of research output, how much of it appears in write_brief.md.

Run on any run folder (`python -c "from seolib.flow_audit import report; report('runs/<run>')"`). A research output
that never reaches the writer costs time (and sometimes credits) for nothing: the forum plugin did that for weeks.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w£$€%.]+", " ", str(s or "").lower()).split())


def _in(text: str, item: str, share: float = 0.6) -> bool:
    """The item's content words are in the brief (questions are rephrased into headings, so most of them, not all)."""
    w = [x for x in _norm(item).split() if len(x) > 3]
    return bool(w) and sum(x in text for x in w) / len(w) >= share


def audit(rd: Path) -> list[tuple[str, int, int, list[str]]]:
    rd = Path(rd)
    brief = (rd / "write_brief.md").read_text(encoding="utf-8") if (rd / "write_brief.md").exists() else ""
    text = _norm(brief)
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    facts = sheet.get("facts") or []
    serp = C.load_json(rd / "research" / "serp_intel.json") or {}
    kg = C.load_json(rd / "research" / "semantic_graph.json") or {}
    lm = C.load_json(rd / "link_map.json") or {}
    plan = C.load_json(rd / "plan.json") or {}
    out = []

    def row(name, items, check):
        items = [i for i in items if i]
        miss = [i for i in items if not check(i)]
        out.append((name, len(items) - len(miss), len(items), [str(m)[:90] for m in miss[:6]]))

    row("People Also Ask questions", serp.get("paa") or [], lambda q: _in(text, q))
    row("related searches", serp.get("related") or [], lambda q: _in(text, q))
    row("autocomplete questions", serp.get("question_autocomplete") or [], lambda q: _in(text, q))
    row("must-cover entities", [e if isinstance(e, str) else e.get("entity") for e in kg.get("must_cover_entities") or []],
        lambda e: _norm(e) in text)
    row("questions page one leaves open (KG gaps)", kg.get("paa_gaps") or [], lambda q: _in(text, q))
    ids = set(re.findall(r"`([^`]+)`", brief))
    by = lambda pred: [f["id"] for f in facts if pred(f)]
    row("page-one points (serp facts)", by(lambda f: f.get("status") == "serp"), lambda i: i in ids)
    row("page-one points made by 2+ sites", by(lambda f: f.get("status") == "serp" and (f.get("consensus") or 1) >= 2),
        lambda i: i in ids)
    row("authority facts", by(lambda f: f.get("status") in ("verified", "captured", "operator")
                              and f.get("basis") not in ("client_page",) and not str(f["id"]).startswith(("offer:", "client", "gain:"))),
        lambda i: i in ids)
    row("client facts and offer", by(lambda f: f.get("basis") == "client_page" or str(f["id"]).startswith(("offer:", "client"))),
        lambda i: i in ids)
    row("items beyond page one (gain)", by(lambda f: str(f["id"]).startswith("gain:")), lambda i: i in ids)
    rel = lm.get("client_related") or {}
    row("client pages to link", list(dict.fromkeys((rel.get("commercial") or [])[:4] + (rel.get("guides") or [])[:5])),
        lambda u: u in brief)
    row("planned headings", [h["title"] for h in plan.get("headings", [])], lambda t: t in brief)
    row("author's view slots", [h["title"] for h in plan.get("headings", []) if h.get("view")], lambda t: True)
    row("quote slots", [h["quote"] for h in plan.get("headings", []) if h.get("quote")], lambda i: i in ids)
    return out


def report(rd) -> None:
    for name, got, total, miss in audit(Path(rd)):
        flag = "OK  " if got == total else ("LOST" if got == 0 and total else "PART")
        print(f"{flag} {name:42s} {got}/{total}" + (f"   missing: {miss}" if miss else ""))
