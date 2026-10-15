"""The fast flow's single writer handoff: everything the writer needs for one pass, in one compact file.

It replaces reading the dossier, expert notes, outline and the full article_context.json in the fast flow. The
evidence policy is the one RULES.md section 1 states: page-one points (`serp` facts) are validated, the
higher-ranked page wins a contradiction, an authority beats any competitor, and every point page one covers is
covered here, plus the searcher questions page one leaves unanswered (the information gain).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C


def _cut(s, n=260) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def build(rd: Path) -> Path:
    rd = Path(rd)
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    ctx = C.load_json(rd / "article_context.json") or {}
    serp = C.load_json(rd / "research" / "serp_intel.json") or {}
    lm = C.load_json(rd / "link_map.json") or {}
    b = sheet.get("brief") or {}
    facts = sheet.get("facts") or []
    eff, raw = b.get("word_range_effective"), b.get("word_range")
    words = eff or raw
    W = [f"# Write brief: {b.get('target_query')}", "",
         f"- Page: **{b.get('page_type') or 'guide'}** for {b.get('client')} ({b.get('domain')}), market {b.get('locale')}, "
         f"task {b.get('task') or 'new'}" + (f" (live page: {b.get('page_url')})" if b.get("task") == "rewrite" else ""),
         f"- Search intent: {(serp.get('intent') or {}).get('primary')}; format Google shows: "
         f"{(serp.get('format') or {}).get('dominant')}"
         + (f"; YMYL topic (money/health/legal/safety rules apply)" if b.get("ymyl") is True or serp.get("ymyl") else ""),
         f"- Length: {words[0]}–{words[1]} words (set from the ranking pages); verified material only, no padding."
         if words else "- Length: as long as the verified material needs.",
         ]
    if b.get("instructions"):
        W.append(f"- Operator's instructions: {b['instructions']}")
    from .pagejob import lines as page_job
    W += [_cut(x, 420) for x in page_job(sheet) if x.strip()][:14]

    cov = ctx.get("coverage_requirements") or []
    req, seen = [], set()
    for c in cov:  # a section and its own question often carry the same words: list the point once
        key = " ".join(sorted(set(re.findall(r"[a-z0-9]+", c["text"].lower())) - {"the", "a", "to", "of", "in", "how", "what", "do", "does", "is", "can", "you"}))
        if c.get("required") and key not in seen:
            seen.add(key)
            req.append(c)
    base = [c for c in req if not c.get("info_gain")]
    gain = [c for c in req if c.get("info_gain")]
    W += ["", "## 1. Coverage: everything page one already covers (the baseline; leave nothing out)",
          "Each item gets a heading, a paragraph, a table row or an FAQ answer. Merge items that are the same point. "
          "Skip an item that is off this page's job without comment.", ""]
    for c in base:
        W.append(f"- [{c['id']}] {_cut(c['text'], 140)}" + (f" (page one: {c['covered_by']} sites)" if c.get("covered_by") else ""))
    answers = serp.get("paa_answers") or {}
    W += ["", "## 2. Information gain: what searchers ask that page one leaves unanswered",
          "Answer every one, briefly and directly (an FAQ or a short section). This is what makes the page worth "
          "ranking above pages Google already has. Use the facts below; your own knowledge may explain, never invent "
          "a number.", ""]
    for c in gain:
        lead = (answers.get(c["text"]) or {}).get("snippet")
        W.append(f"- [{c['id']}] {_cut(c['text'], 140)}" + (f"\n  - Google's answer lead: \"{_cut(lead, 220)}\"" if lead else ""))
    if not gain:
        W.append("- (none found: page one already answers every searcher question; add depth on the main task instead)")

    auth = [f for f in facts if f.get("status") in ("verified", "captured", "operator")
            and f.get("basis") not in ("client_page",) and not str(f.get("id", "")).startswith(("offer:", "client"))]
    client = [f for f in facts if f.get("status") in ("verified", "captured", "operator")
              and (f.get("basis") == "client_page" or str(f.get("id", "")).startswith(("offer:", "client")))]
    # the strongest points first (most sites, highest rank); the writer reads ~50, the rest stay usable in the sheet
    pagefacts = [f for f in facts if f.get("status") == "serp" and f.get("basis") != "paa_answer"][:40]
    paafacts = [f for f in facts if f.get("status") == "serp" and f.get("basis") == "paa_answer"]
    W += ["", "## 3. Facts you may state (in your own words; numbers exactly as given)",
          "Never reuse six or more consecutive words from a fact: lint blocks copied wording. Unit conversions and "
          "other numbers not shown here are blocked too; give the figure as the fact states it.", "",
          "### Authority facts (these win any disagreement; link the source on the words a reader would check)"]
    W += [f"- `{f['id']}` \"{_cut(f.get('value'), 220)}\" — {f.get('source_url')}"
          + (f" [applies to: {f['scope']}]" if f.get("scope") else "") for f in auth[:30]] or ["- (none)"]
    W += ["", "### Page-one validated points (Google ranks these pages for this query: state them as fact, never "
          "copy their wording, never link a competitor as the source; drop one only if you know it is wrong)"]
    for f in pagefacts:
        W.append(f"- `{f['id']}` [{f.get('consensus', 1)} site{'s' if f.get('consensus', 1) != 1 else ''}, rank "
                 f"{f.get('rank')}] \"{_cut(f.get('value'), 200)}\"")
    if paafacts:
        W += ["", "### Google's People Also Ask answers (validated answers to searcher questions)"]
        W += [f"- `{f['id']}` Q: {f.get('question')} — \"{_cut(f.get('value'), 220)}\"" for f in paafacts]
    if client:
        W += ["", f"### {b.get('client')}'s own published claims (use in its voice with their conditions; never stretch)"]
        W += [f"- `{f['id']}` \"{_cut(f.get('value'), 200)}\"" for f in client[:12]]
    conf = [f for f in pagefacts if f.get("conflicts")]
    over = [f for f in facts if f.get("status") == "serp_overridden"]
    if conf or over:
        W += ["", "### Contradictions already resolved (do not use the losing values)"]
        for f in conf:
            W.append(f"- `{f['id']}` uses rank {f.get('rank')}: \"{_cut(f.get('value'), 120)}\"; not: "
                     + "; ".join(f"\"{_cut(a['sentence'], 90)}\" (rank {a['rank']})" for a in f["conflicts"][:2]))
        for f in over:
            W.append(f"- not \"{_cut(f.get('value'), 120)}\": {f.get('note')}")

    rel = lm.get("client_related") or {}
    titles = lm.get("client_titles") or {}
    targets = list(dict.fromkeys((rel.get("commercial") or [])[:4] + (rel.get("guides") or [])[:5] + (rel.get("same_topic") or [])[:2]))
    W += ["", "## 4. Internal links (add 3–6 in the body as you write)",
          "Anchor each on the target page's main term, inside a sentence about that thing; never in the first sentence "
          "under a heading; no anchor used twice. Only these addresses (or others in link_map.json) are allowed."]
    W += [f"- {u}" + (f" — {titles[u]}" if titles.get(u) else "") for u in targets] or ["- (no related client pages found)"]
    W += ["", "## 5. Never",
          "- Mention the research (\"top results\", \"other guides\", \"according to competitors\").",
          "- Write a number no fact above carries (arithmetic you show from facts is fine).",
          "- Link a competitor's page, invent experience, statistics or credentials for the client, or use HTML."]
    out = rd / "write_brief.md"
    out.write_text("\n".join(W) + "\n", encoding="utf-8")
    return out
