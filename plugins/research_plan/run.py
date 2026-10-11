"""Research plan: the question tree the deep_research agent works through.

Everything here is derived from this run's own data (the SERP, the ranking pages, the facts already gathered and
the client's site). No topic knowledge is written in: the plan is the same shape for any query, client or country.
"""
import re

from seolib import common as C
from seolib.domains import kind

# who reads a page like this, and what each of them would ask (multi-perspective questioning, as in STORM)
PERSPECTIVES = [
    ("Beginner", "doing this for the first time: what exactly do I do, in what order, and how do I know it worked?"),
    ("Practitioner", "does this every day: what do people get wrong, what shortcuts are unsafe, what do I check first?"),
    ("Authority", "sets or enforces the rules: what is required, for whom, from when, and what are the consequences?"),
    ("Skeptic", "doubts the common advice: which popular claims are myths, outdated or true only for some cases?"),
    ("Buyer", "is deciding what to buy or book: what does it cost, what are the options, when is it worth paying?"),
]


def run(ctx):
    serp = ctx.load("serp_intel") or {}
    qmap = ctx.load("query_map") or {}
    kg = ctx.load("semantic_graph") or {}
    comp = ctx.load("competitor_scrape") or {}
    found = ctx.load("foundation") or {}
    sheet = (found.get("sheet") or {}) or C.load_json(ctx.rd / "fact_sheet.json") or {}
    lm = (found.get("link_map") or {}) or C.load_json(ctx.rd / "link_map.json") or {}
    b = ctx.brief
    q = b.get("target_query", "")
    n_pages = len(comp.get("pages", [])) or 1

    questions = [q] + [x for x in qmap.get("h2_questions", []) if x.lower() != q.lower()]
    topics = [t for t in kg.get("heading_topics", []) if t.get("domains", 0) >= max(2, 0.3 * n_pages)][:12]
    figures = kg.get("consensus_figures", [])[:10]
    facts = [f for f in sheet.get("facts", []) if f.get("status") in ("verified", "captured", "operator")]
    by_kind = {}
    for f in facts:
        by_kind.setdefault(kind(f.get("source_url") or ""), []).append(f)
    client_pages = []
    for k in ("same_topic", "guides"):
        client_pages += (lm.get("client_related") or {}).get(k, [])
    authorities = sorted({o.get("domain") for o in serp.get("organic", []) if o.get("kind") in ("government", "international")})
    independents = sorted({o.get("domain") for o in serp.get("organic", []) if o.get("kind") in ("nonprofit", "education")})

    L = [f"# Research plan: {q}", "",
         f"Client: {b.get('client')} ({b.get('domain')}) · locale {b.get('locale')} · YMYL: {b.get('ymyl')} · "
         f"page type: {b.get('page_type')}", "",
         "Work through this with `plugins/deep_research/SKILL.md`. Every answer ends up as facts (`--add-fact`, with "
         "`--scope`) and a line in `research/dossier.md`.", "",
         "## 1. Questions the page must answer (search demand)"]
    L += [f"- Q{i}: {x}" for i, x in enumerate(questions, 1)]
    L += ["", "## 2. Questions from five readers (ask 2–3 for each; keep the ones the evidence can answer)"]
    L += [f"- **{name}** ({frame}) — about \"{q}\"" for name, frame in PERSPECTIVES]
    if topics:
        L += ["", f"## 3. Topics most ranking pages cover ({n_pages} read): cover each with evidence, or record why not",
              "Each needs a line in the dossier's \"Topics the ranking pages share\" that starts with its T-number."]
        L += [f"- T{i}: {t['topic']} ({t['domains']}/{n_pages} pages"
              + (f"; also headed \"" + "\", \"".join(t.get("examples", [])[1:3]) + "\"" if len(t.get("examples", [])) > 1 else "")
              + ")" for i, t in enumerate(topics, 1)]
    if figures:
        L += ["", "## 4. Figures several pages state: trace each to its original source (who measured or set it, when, for whom)"]
        L += [f"- {r['figure']} — e.g. \"{r['examples'][0]['sentence'][:140]}\" ({r['examples'][0]['source']})" for r in figures]
    if facts:
        L += ["", f"## 5. Facts already gathered ({len(facts)}): check scope before relying on them",
              "For each fact the answer depends on: who/what/when does it apply to, and does the full source sentence "
              "carry a condition the extract dropped?"]
        for k, fs in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
            L.append(f"- {k}: " + ", ".join(f"`{f['id']}`" for f in fs[:12]) + (" …" if len(fs) > 12 else ""))
    if client_pages:
        L += ["", "## 6. The client's own pages on this subject: read them first (the page must not contradict them, and "
                  "their method or figures lead when they are sound)"]
        L += [f"- {u}" for u in client_pages[:8]]
    L += ["", "## 7. Where to look first (this SERP)",
          f"- Authorities in the results: {', '.join(authorities) or 'none ranked: search the locale authority sites'}",
          f"- Independent organisations in the results: {', '.join(independents) or 'none ranked'}",
          "- Then the maker's own documentation for any product, app or standard the page names."]
    decisions = (sheet.get("decisions") or [])[:8]
    if decisions:
        L += ["", "## 8. Already decided or flagged by the scripts"] + [f"- {d[:220]}" for d in decisions]
    (ctx.rd / "research_plan.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return {"questions": len(questions), "topics": len(topics), "figures": len(figures), "facts": len(facts),
            "client_pages": len(client_pages),
            "summary": f"research plan: {len(questions)} questions, {len(topics)} shared topics, {len(figures)} figures to trace"}
