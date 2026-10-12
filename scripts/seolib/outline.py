"""Outline gate (deep mode): catch structural problems before a single
paragraph is written, when they are cheapest to fix."""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C
from .nlp import tokens

STOP = set("a an the and or of to in on for with by from at as is are be your my our their its this that how what "
           "why when where which who can do does you i it much many should would could say says".split())
FILLER_EXTRA = {"day", "daily", "per", "week", "weekly", "exactly", "really", "actually", "enough", "much", "many",
                "right", "amount", "ideal", "best", "typical", "average", "usually", "normally", "today"}
CONTEXTLESS = r"(introduction|overview|conclusion|final thoughts|about|miscellaneous|summary|wrap[- ]up|faqs?|" \
              r"frequently asked questions|key takeaways?|bottom line|verdict)"


def toks(s: str, synonyms: dict | None = None) -> set[str]:
    return {w for w in tokens(re.sub(r"[()]", "", s), synonyms) if w not in STOP and (len(w) > 2 or w.startswith("geo:"))}


def cover(q: str, heads: list[str]) -> float:
    qt = toks(q)
    return max((len(qt & toks(h)) / max(1, len(qt)) for h in heads), default=0.0)


def check_outline(rd: Path) -> bool:
    p = rd / "outline.md"
    if not p.exists():
        print(f"No outline yet: write {p.as_posix()} first.")
        return False
    heads, skips = [], []
    for ln in p.read_text(encoding="utf-8").splitlines():
        # "Skip: <question> — <reason>" records a PAA question deliberately left out (no verifiable answer, other intent)
        sm = re.match(r"^\s*[-*]?\s*(?:Skip|Linked):\s*(.+?)\s+[—–-]{1,2}\s+(.{8,})$", ln)
        if sm:
            if not re.search(r"own page|separate page|deserves (its|a) (own|separate)", sm.group(2), re.I) or \
                    not ln.lstrip(" -*").lower().startswith("skip"):
                skips.append((sm.group(1), sm.group(2)))
            # "Skip: … — deserves its own page" is the plan's call, not the writer's: a question the plan sends to
            # another page is never in h2_questions, and one the plan keeps here can't be skipped for that reason
        m = re.match(r"^(#{1,4})\s+(.*)$", ln.strip())
        if m:
            heads.append((len(m.group(1)), re.sub(r"[*_`]", "", m.group(2)).strip()))
    sheet = C.load_json(rd / "fact_sheet.json")
    from .pagejob import COMMERCIAL
    commercial = sheet["brief"].get("page_type") in COMMERCIAL
    outline_text = p.read_text(encoding="utf-8")
    if (rd / "research").exists():  # lint reads the deliberate skips from here
        C.save_json(rd / "research" / "outline.json", {"skips": [{"question": s, "reason": r} for s, r in skips]})
    qmap = C.load_json(rd / "research" / "query_map.json") or {}
    kg = C.load_json(rd / "research" / "semantic_graph.json") or {}
    F = []

    def add(sev, msg):
        F.append((sev, msg))
    h1 = [h for l, h in heads if l == 1]
    live = sheet["brief"].get("h1") or (sheet.get("page") or {}).get("h1")
    if len(h1) != 1:
        add("B", f"{len(h1)} H1 headings; use exactly one")
    elif live and C.norm_for_match(h1[0]) != C.norm_for_match(live):
        add("B", f"H1 must be the live H1 \"{live}\"")
    prev = 1
    for l, h in heads:
        if l > prev + 1:
            add("B", f"skipped heading level before \"{h}\"")
        prev = l
        if l >= 2 and re.fullmatch(CONTEXTLESS, h.lower().strip(" :?")) and not (
                commercial and re.fullmatch(r"faqs?|frequently asked questions", h.lower().strip(" :?"))):
            add("B", f"contextless heading \"{h}\": name the subject it covers; place questions according to the Page job")
        ws = re.findall(r"[A-Za-z][\w'’-]*", h)[1:]
        from .nlp import places as _pl
        geo = {w for i in range(len(ws)) for span in (ws[i:i + 1], ws[i:i + 2])
               if span and span[0][:1].isupper() and _pl(" ".join(span)) for w in span}
        caps = [w for w in ws if len(w) > 3 and w[0].isupper() and not w.isupper() and w not in geo]
        if l >= 2 and len(caps) >= 3 and len(caps) >= 0.6 * len([w for w in ws if len(w) > 3]):
            add("w", f"\"{h}\" looks like Title Case; use sentence case")
    sub = [h for l, h in heads if l >= 2]
    # an H2 that asks the H1's question again in other words is the query stuffed into a heading
    if h1:
        ht = toks(h1[0])
        for l, h in heads:
            st = toks(h)
            # "… per day?", "… exactly?" restate the H1; "… the Safari cache …" narrows it, which is fine
            if l == 2 and len(ht) >= 2 and len(ht & st) >= 0.8 * len(ht) and (st - ht) <= FILLER_EXTRA:
                add("B", f"\"{h}\" repeats the H1's question; merge it into the opening or make it specific")
    yous = [h for l, h in heads if l >= 2 and re.search(r"\b(you|your)\b", h, re.I)]
    mes = [h for l, h in heads if l >= 2 and re.search(r"\b(I|my|me)\b", h)]
    if yous and mes:
        add("w", f"headings switch between \"you\" and \"I\" (e.g. \"{mes[0]}\"); keep one person")
    for q in qmap.get("h2_questions", []):
        c = cover(q, sub + outline_text.splitlines())
        sk = next((r for s, r in skips if cover(q, [s]) >= 0.8), None)
        if c < 0.6 and sk:
            add("w", f"PAA question skipped on purpose: \"{q}\" ({sk})")
        elif c < 0.6:
            add("B", f"PAA question not placed in the outline: \"{q}\" (use a heading, a body/table/FAQ coverage note, or 'Skip: <question> — <reason>')")
    if commercial and not re.search(r"(?im)^\s*Page job:\s*\S.+", outline_text):
        add("B", "commercial outline needs a Page job: line identifying the type, scoped offer fact ids and verified next step (or next step not verified)")
    for r in qmap.get("queries", []):
        if r["decision"] == "separate_page" and cover(r["query"], sub) >= 0.85:
            add("w", f"\"{r['query']}\" was routed to a separate page; verify against the main task and document the coverage decision before removing relevant detail")
        if r["decision"] == "existing_page" and cover(r["query"], sub) >= 0.85 and sheet["brief"].get("page_type") == "hub":
            add("w", f"\"{r['query']}\" has its own page ({r.get('url')}); link it instead of a full section")
    topics = kg.get("heading_topics", [])[:10]
    if topics:
        hit = [t for t in topics if cover(t["topic"], sub + [h for h in h1]) >= 0.5 or
               any(cover(e, sub) >= 0.5 for e in t["examples"])]
        if len(hit) < 0.5 * len(topics):
            missing = [t["topic"] for t in topics if t not in hit][:6]
            add("w", f"outline covers {len(hit)}/{len(topics)} topics the top pages share; consider: " + "; ".join(missing))
        # a topic most of the top pages cover is what the reader expects: cover it, or say why not
        n_pages = len((C.load_json(rd / "research" / "competitor_scrape.json") or {}).get("pages", [])) or 1
        whole = sub + h1 + outline_text.splitlines() + [s for s, _ in skips]
        for tp in topics:
            if tp["domains"] >= max(3, 0.4 * n_pages) and tp not in hit and not any(
                    cover(e, whole) >= 0.5 for e in [tp["topic"]] + tp["examples"]):
                if len(toks(tp["topic"])) <= 1:
                    add("w", f"\"{tp['topic']}\" is a section most top pages have ({tp['domains']}/{n_pages}); make sure "
                             "the page covers it, under a heading in the reader's words")
                    continue
                add("B", f"\"{tp['topic']}\" is covered by {tp['domains']} of {n_pages} top pages but not by this outline "
                         "(add a section, or a `Skip: <topic> — <reason>` line)")
    context = C.load_json(rd / "article_context.json") or {}
    resolutions = {}
    for line in outline_text.splitlines():
        match = re.match(r"^\s*(?:[-*]\s*)?(Coverage|Exclude):\s*((?:S\d+|Q\d+)(?:\s*,\s*(?:S\d+|Q\d+))*)\s+[—–-]\s+(.{8,})$", line, re.I)
        if match:
            for cid in re.split(r"\s*,\s*", match[2].upper()):
                resolutions[cid] = {"decision": match[1].lower(), "placement_or_reason": match[3]}
    for item in context.get("coverage_requirements", []):
        if item.get("required") and item["id"] not in resolutions:
            add("B", f"coverage {item['id']} ({item['text']}) needs 'Coverage: {item['id']} — <heading/body/table/FAQ placement>' or 'Exclude: {item['id']} — <specific reason>'")
    if context:
        C.save_json(rd / "research" / "coverage_plan.json", {"input_digest": context.get("input_digest"), "items": resolutions})
    for sev, msg in F:
        print(f"{sev} {msg}")
    ok = not any(s == "B" for s, _ in F)
    print(f"OUTLINE {'PASS' if ok else 'FAIL'}: {len(heads)} headings, "
          f"{sum(1 for q in qmap.get('h2_questions', []) if cover(q, sub) >= 0.6)}/{len(qmap.get('h2_questions', []))} PAA covered")
    return ok
