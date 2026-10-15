"""The writer's single handoff: everything needed for one pass, in one compact file.

It holds the page job, the finished page plan (every heading, in order, split into parts that writers can draft at
the same time), the facts as short notes with their ids, and the links. The writer reads this and RULES_CARD.md,
nothing else. Evidence policy (RULES.md section 1): page-one points are validated; where ranking sites disagree
the value most of them state is the fact (rank breaks a tie); a verified authority fact beats any competitor.

Facts from other sites are given as notes (their content words and figures), not their sentences: a writer handed
a competitor's sentence reuses its wording, lint blocks the copy, and the fix round costs minutes.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C

NOTE_STOP = set("a an the and or but so of to in on at by for with from into is are was were be been being this that "
                "these those it its there here which who whom whose what when where why how your you we our they their "
                "can could will would should may might must do does did have has had just also very really then than "
                "as if because while whether".split())
KEEP = re.compile(r"(?i)^(not|no|never|only|up|least|most|more|less|than|before|after|until|within|over|under|"
                  r"between|per|each|every|without|minimum|maximum)$")


def _cut(s, n=260) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def note(sentence: str, n: int = 24) -> str:
    """A fact as a note: its figures, qualifiers and content words, in order ("full curing · up to week · most
    paints"), so the writer states it in its own sentence."""
    out, clause = [], []
    for tok in re.findall(r"[£$€]?\d[\d,.]*\s?(?:%|cm|mm|m|kg|g|ml|l|°C|hours?|hrs?|days?|weeks?|months?|years?|"
                          r"minutes?|mins?)?|[A-Za-z][\w'-]*|[,;:()]", sentence or ""):
        if tok in ",;:()":
            if clause:
                out.append(" ".join(clause))
                clause = []
            continue
        if tok.lower() in NOTE_STOP and not KEEP.match(tok):
            continue
        clause.append(tok if (tok[:1].isdigit() or tok.isupper() or tok[:1] in "£$€") else tok.lower()
                      if not (tok[:1].isupper() and clause) else tok)
    if clause:
        out.append(" ".join(clause))
    text = " · ".join(x for x in out if x)
    ws = text.split()
    return " ".join(ws[:n]) + (" …" if len(ws) > n else "")


def build(rd: Path) -> Path:
    rd = Path(rd)
    from .plan import build as plan_build, render
    plan = plan_build(rd)
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    serp = C.load_json(rd / "research" / "serp_intel.json") or {}
    b = sheet.get("brief") or {}
    facts = sheet.get("facts") or []
    lo, hi = b.get("word_range_effective") or b.get("word_range") or plan.get("words") or [900, 1400]
    W = [f"# Write brief: {b.get('target_query')}", "",
         f"- Page: **{b.get('page_type') or 'guide'}** for {b.get('client')} ({b.get('domain')}), market {b.get('locale')}, "
         f"task {b.get('task') or 'new'}" + (f" (live page: {b.get('page_url')})" if b.get("task") == "rewrite" else ""),
         f"- Search intent: {(serp.get('intent') or {}).get('primary')}"
         + ("; YMYL topic: money/health/legal/safety cautions where the decision is made" if b.get("ymyl") is True
            or serp.get("ymyl") else ""),
         f"- Length: {lo}–{hi} words in all (each heading's share is in the plan); every heading answered, no padding."]
    if b.get("instructions"):
        W.append(f"- Operator's instructions: {b['instructions']}")
    from .pagejob import lines as page_job
    job = [x for x in page_job(sheet) if x.strip() and not x.startswith("## ")]
    W += ["", "## 1. Page job"] + [_cut(x, 380) for x in job[:12]]

    W += ["", "## 2. The plan: write every heading below, in this order (rephrase a heading only to read naturally; "
          "keep its key words)",
          "Each H2 answers its question in its first one or two sentences, then the detail. H3s sit under their H2. "
          "\"also answer\" lines are answered inside that section in those words. A fact id listed under a heading is "
          "the material for it; any fact below may be used where it fits.", ""]
    W += render(plan, {f["id"]: f for f in facts})

    gain = [f for f in facts if str(f.get("id", "")).startswith("gain:")]
    auth = [f for f in facts if f.get("status") in ("verified", "captured", "operator") and f not in gain
            and f.get("basis") != "client_page" and not str(f.get("id", "")).startswith(("offer:", "client"))]
    client = [f for f in facts if f.get("status") in ("verified", "captured", "operator")
              and (f.get("basis") == "client_page" or str(f.get("id", "")).startswith(("offer:", "client")))]
    quoted = {h["quote"] for h in plan["headings"] if h.get("quote")}
    planned = {i for h in plan["headings"] for i in h.get("facts", [])}
    serpf = [f for f in facts if f.get("status") == "serp"]
    serpf.sort(key=lambda f: (f["id"] not in planned, -(f.get("consensus") or 1)))
    W += ["", "## 3. Facts (notes: write your own sentences; figures exactly as given; no figure that isn't here)"]
    if gain:
        W += ["", "### Beyond page one (information gain: what no ranking page says; use every one under its heading, "
              "credit who says it in the sentence and link the source on those words)"]
        W += [f"- `{f['id']}` [{f.get('kind')}] {f.get('who')}{' (' + str(f['date']) + ')' if f.get('date') else ''}: "
              f"{_cut(f.get('point'), 220)} — {f.get('source_url')}"
              + ("" if f.get("status") == "verified" else " [an experience, quoted by the researcher: attribute it, no figures]")
              for f in gain]
    if quoted:
        W += ["", "### Quotable, word for word (the plan's quote slots: these exact words in quotation marks, the "
              "source named and linked in the same sentence)"]
        W += [f"- `{f['id']}` \"{' '.join(str(f.get('value')).split())}\" — {f.get('source_url')}"
              for f in facts if f["id"] in quoted]
    if auth:
        W += ["", "### Authorities (they win any disagreement; link the source on the words a reader would check)"]
        W += [f"- `{f['id']}` {note(f.get('value'), 30)} — {f.get('source_url')}"
              + (f" [applies to: {_cut(f['scope'], 80)}]" if f.get("scope") else "") for f in auth[:25]]
    if serpf:
        W += ["", "### Page one (validated: state as fact, never link a competitor; disagreements already settled by "
              "the majority of ranking sites)"]
        for f in serpf[:70]:
            q = f" (answers: {f['question']})" if f.get("question") else ""
            W.append(f"- `{f['id']}` [{f.get('consensus') or 1} site{'s' if (f.get('consensus') or 1) != 1 else ''}]"
                     f" {note(f.get('value'))}{q}")
    conf = [f for f in serpf if f.get("conflicts")]
    if conf:
        W += ["", "### Settled disagreements (never use the losing figure)"]
        W += [f"- `{f['id']}` use: {note(f.get('value'), 14)}; not: "
              + "; ".join(note(a["sentence"], 10) for a in f["conflicts"][:2]) for f in conf]
    if client:
        W += ["", f"### {b.get('client')}'s own words (usable as they are, in its voice; never stretch them)"]
        W += [f"- `{f['id']}` \"{_cut(f.get('value'), 200)}\"" for f in client[:12]]
    W += ["", "## 4. Never",
          "- Mention the research (\"top results\", \"other guides\", \"according to competitors\").",
          "- A figure no fact above carries (arithmetic you show from facts is fine), or a losing figure.",
          "- A competitor's link, invented experience, statistics or credentials, HTML, or an FAQ block (questions are "
          "headings in the plan).",
          "- \"I\" claiming you used, tried, tested, bought or saw something, \"in my experience\", \"my clients\", years "
          "of experience" + (" (only the client's experience notes below may be told in the first person)"
                             if b.get("experience") else "") + "."]
    if b.get("experience"):
        W += ["", "## 5. First-hand experience you may tell (the client's own notes; nothing beyond them)"]
        W += [f"- {_cut(x, 300)}" for x in (b["experience"] if isinstance(b["experience"], list) else [b["experience"]])]
    out = rd / "write_brief.md"
    out.write_text("\n".join(W) + "\n", encoding="utf-8")
    return out
