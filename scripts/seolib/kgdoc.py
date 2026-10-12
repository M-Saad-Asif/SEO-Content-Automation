"""Build the cached article-context JSON; optionally export two legacy Markdown research documents.

- knowledge_graph.md: the topic's entities (typed, defined), their attributes and the values the ranking pages
  state, the relationships between them, and the verified facts attached to each entity. What to say.
- topic_outline.md: every question searchers and ranking pages ask, in the sections the ranking pages share,
  macro to micro, each with the entities, figures and facts that belong to it. What to cover, in what order.

Rendered from research/semantic_graph.json, research/topic_outline.json and fact_sheet.json. Rendered again
before the outline and the draft, so facts the researcher verified after the scripts ran are attached too.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C
from .nlp import tokens

DECISION = {"h2": "H2", "cover_in_section": "in section", "existing_page": "link", "separate_page": "other page",
            "drop": "dropped"}
SOURCE = {"paa": "People Also Ask", "paa_expanded": "PAA (follow-on search)", "paa_dfs": "People Also Ask",
          "paa_autocomplete": "question searched (autocomplete)", "related": "related search",
          "related_expanded": "related search (follow-on)", "autocomplete": "autocomplete", "gsc": "Search Console",
          "keyword": "keyword data", "top_page_headings": "ranking pages' headings", "competitor": "ranking page"}
TYPE_ORDER = ["kind", "broader class", "party", "organisation or named thing", "rule or document", "measure",
              "concept", "place", "person"]
TYPE_TITLE = {"kind": "Kinds and variants of the topic", "broader class": "What the topic is a kind of",
              "party": "People and parties", "organisation or named thing": "Organisations, products and named things",
              "rule or document": "Rules, laws and documents", "measure": "Measures (what the figures are about)",
              "concept": "Concepts", "place": "Places", "person": "People"}
STOP = set("a an the and or of to in on for with by from at as is are be your our their its this that how what why "
           "when where which who can do does you i it much many".split())


def _toks(s: str, syn=None) -> set:
    return {w for w in tokens(s or "", syn) if w not in STOP and len(w) > 2}


def _facts(sheet: dict) -> list[dict]:
    out = []
    for f in sheet.get("facts", []):
        if f.get("status") not in ("verified", "captured", "operator"):
            continue
        text = f"{f.get('claim', '')} {f.get('value', '')}"
        out.append({"id": f.get("id"), "text": text, "value": str(f.get("value", "")), "scope": f.get("scope"),
                    "url": f.get("source_url"), "client": f.get("basis") == "client_page"})
    return out


def _market(locale: str) -> str:
    region = (locale or "en-GB").partition("-")[2].upper() or "GB"
    names = {"GB": "United Kingdom", "UK": "United Kingdom", "US": "United States", "IE": "Ireland", "AU": "Australia",
             "CA": "Canada", "NZ": "New Zealand", "IN": "India", "AE": "United Arab Emirates", "DE": "Germany",
             "FR": "France", "ES": "Spain", "IT": "Italy", "NL": "Netherlands"}
    return f"{names.get(region, region)} ({locale})"


def write_docs(rd: Path) -> None:
    rd = Path(rd)
    from .article_context import build
    build(rd)
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    b = sheet.get("brief") or {}
    # One cached JSON handoff is the default. Keep old Markdown exports only for an explicit legacy brief.
    if b.get("research_format") != "markdown":
        return
    kgo = C.load_json(rd / "research" / "semantic_graph.json") or {}
    out = C.load_json(rd / "research" / "topic_outline.json") or {}
    g = kgo.get("graph") or {}
    if g.get("entities"):
        (rd / "knowledge_graph.md").write_text(_graph_md(g, kgo, sheet, b), encoding="utf-8")
    if out.get("sections"):
        (rd / "topic_outline.md").write_text(_outline_md(out, g, sheet, b), encoding="utf-8")


def _fact_line(f: dict) -> str:
    sc = f" (scope: {f['scope']})" if f.get("scope") else ""
    who = "client's own page" if f["client"] else (C.host(f["url"]) if f.get("url") else "")
    return f"- `{f['id']}` {f['value'][:220]}{sc} — {who}"


def _graph_md(g: dict, kgo: dict, sheet: dict, b: dict) -> str:
    syn = b.get("synonyms") or {}
    ymyl = b.get("ymyl") is True
    ents = g["entities"]
    by_key = {e["key"]: e for e in ents}
    central = by_key.get(g["central"]) or ents[0]
    n = g.get("pages") or 1
    facts = _facts(sheet)
    # attach each verified fact to the most specific entity it names: the longest name found in it (so a fact about
    # "second charge bridging loans" goes to the topic, not to "loan"). The client's own sentences only when they are
    # about this topic (its other product pages are in the fact sheet too).
    names = sorted(((e, [e["name"].lower()] + [a.lower() for a in e.get("aliases", [])]) for e in ents),
                   key=lambda x: -max(len(n) for n in x[1]))
    ftopic = _toks(b.get("target_query", ""), syn)
    per_ent: dict[str, list] = {}
    seen = set()
    for f in facts:
        key = re.sub(r"\W+", " ", f["value"].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        on_topic = len(ftopic & _toks(f["text"], syn)) >= max(1, len(ftopic) - 1)
        if f["client"] and not on_topic:
            continue
        low = f["text"].lower()
        hit = next((e for e, ns in names if any(re.search(r"\b" + re.escape(x) + r"s?\b", low) for x in ns)), None)
        if hit is None and on_topic:
            hit = central
        if hit is not None:
            per_ent.setdefault(hit["key"], []).append(f)
    L = [f"# Knowledge graph: {b.get('target_query', '')} — {_market(b.get('locale'))}", "",
         f"Built from {n} ranking pages read for this market"
         + (f" (left out as another market's: {', '.join(g['foreign_pages'])})" if g.get("foreign_pages") else "")
         + f", the searches around the topic, and {len(facts)} verified facts. Every value names the sites that state it.",
         "", "**How to use it**",
         "- Entities are what the page must be about: name the ones a section needs, in the words searchers use.",
         "- A definition or relationship two or more sites share is the consensus: say it in your own words.",
         ("- Every number, fee, limit or time must come from a verified fact (the `fact id`s below, or `prep --add-fact`). "
          "Values the ranking pages state are leads to verify, never facts, on this page."
          if ymyl else
          "- A value three or more sites state may be used as stated; any other number needs a verified fact."),
         "- Single-site items are claims, not facts: use one only when a verified fact backs it, or attribute it.",
         "- Where sites disagree, the verified fact decides; with no fact, give the range and say it varies.", ""]
    # central entity
    L += [f"## The topic: {central['name']}", ""]
    d = central.get("definition")
    if d:
        L.append(f"- Definition {d['sites']} site(s) give, most shared wording: \"{d['text']}\" — {d['source']}")
    kinds = [e for e in ents if e["type"] == "kind"]
    broader = [e for e in ents if e["type"] == "broader class"]
    if broader:
        L.append("- It is a kind of: " + ", ".join(e["name"] for e in broader))
    if kinds:
        L.append("- Kinds and neighbours the pages name: " + ", ".join(f"{e['name']} ({len(e['domains'])} sites)" for e in kinds[:8]))
    attrs = [a for a in g.get("attributes", [])]
    if attrs:
        L += ["", "| Attribute | Values the ranking pages state (sites) | Sites | Use |", "|---|---|---:|---|"]
        for a in attrs:
            vals = "; ".join(f"{_q(v['qualifier'])}{v['value']} ({len(v['domains'])})" for v in a["values"][:4])
            owner = "" if a["entity"] == g["central"] else f" — of {by_key.get(a['entity'], {}).get('name', a['entity'])}"
            top = max(len(v["domains"]) for v in a["values"])
            use = "verify first" if ymyl else ("usable" if top >= 3 else "verify first")
            if a.get("differs"):
                use += "; sites differ, give the range"
            L.append(f"| {a['attribute_name']}{owner} | {vals} | {a['sites']} | {use} |")
    cf = per_ent.get(central["key"], [])
    if cf:
        L += ["", f"Verified facts about {central['name']}:"] + [_fact_line(f) for f in cf[:14]]
    # entities by type
    L += ["", "## Entities", ""]
    for t in TYPE_ORDER:
        group = [e for e in ents if e["type"] == t and e is not central]
        if not group:
            continue
        L.append(f"### {TYPE_TITLE[t]}")
        for e in group[:18 if t == "concept" else 12]:
            bits = [f"{len(e['domains'])}/{n} sites"]
            if e.get("in_headings"):
                bits.append(f"in headings on {e['in_headings']}")
            if e.get("searched"):
                bits.append(f"in {e['searched']} search(es)")
            aka = f" (also: {', '.join(e['aliases'])})" if e.get("aliases") else ""
            L.append(f"- **{e['name']}**{aka} — " + ", ".join(bits))
            if e.get("definition"):
                L.append(f"  - defined ({e['definition']['sites']} site(s)): \"{e['definition']['text'][:220]}\" — {e['definition']['source']}")
            for an, vals in list((e.get("attributes") or {}).items())[:3]:
                L.append(f"  - {an}: " + "; ".join(f"{_q(v['qualifier'])}{v['value']} ({len(v['domains'])})" for v in vals[:3]))
            for f in per_ent.get(e["key"], [])[:4]:
                L.append("  " + _fact_line(f))
        L.append("")
    # relationships
    rels = g.get("relations", [])
    cons = [r for r in rels if r["consensus"]]
    single = [r for r in rels if not r["consensus"]]
    if rels:
        L += ["## Relationships (subject — predicate — object)", ""]
    if cons:
        L.append("Shared by two or more sites (consensus):")
        L += [f"- {r['example']['s']} — {r['predicate']} — {r['example']['o']} ({len(r['domains'])} sites): "
              f"\"{r['example']['sentence'][:200]}\"" for r in cons[:30]]
        L.append("")
    if single:
        L.append("Stated by one site (a claim to check, not a fact):")
        L += [f"- {r['example']['s']} — {r['predicate']} — {r['example']['o']} — {r['example']['source']}: "
              f"\"{r['example']['sentence'][:180]}\"" for r in single[:25]]
        L.append("")
    figs = kgo.get("consensus_figures") or []
    if figs:
        L += ["## Figures several sites state", ""]
        L += [f"- {r['figure']} ({len(r['domains'])} sites): \"{r['examples'][0]['sentence'][:180]}\" — {r['examples'][0]['source']}"
              for r in figs[:12]]
        L.append("")
    rest = [f for k, fs in per_ent.items() for f in fs]
    loose = [f for f in facts if f not in rest and not f["client"]]
    if loose:
        L += ["## Other verified facts for this page", ""] + [_fact_line(f) for f in loose[:20]] + [""]
    if kgo.get("paa_gaps"):
        L += ["## Questions no ranking page answers (information gain)", ""] + [f"- {q}" for q in kgo["paa_gaps"]] + [""]
    return "\n".join(L).rstrip() + "\n"


def _q(q: str) -> str:
    return {"max": "up to ", "min": "from ", "typical": "about ", "range": ""}.get(q or "", "")


def _outline_md(o: dict, g: dict, sheet: dict, b: dict) -> str:
    syn = b.get("synonyms") or {}
    facts = [f for f in _facts(sheet)]
    ftok = [(f, _toks(f["text"], syn)) for f in facts]
    n = o.get("pages") or 1
    secs = o["sections"]
    allq = [q for s in secs for q in s["questions"] + [x for ss in s.get("subsections", []) for x in ss["questions"]]]
    h2 = sum(1 for q in allq if q["decision"] == "h2")
    src = {}
    for q in allq:
        src[SOURCE.get(q["source"], q["source"])] = src.get(SOURCE.get(q["source"], q["source"]), 0) + 1
    L = [f"# Topic outline: {b.get('target_query', '')} — {_market(b.get('locale'))}", "",
         f"{len(secs)} sections the ranking pages share ({n} pages read), in the order they put them, holding "
         f"{len(allq)} questions ({h2} planned as H2s): " + ", ".join(f"{k} {v}" for k, v in sorted(src.items(), key=lambda kv: -kv[1])) + ".",
         "", "**How to use it**",
         "- Build `outline.md` from these sections, macro to micro: one H2 per section that fits the page type, in the "
         "reader's words, and its sub-sections as H3s where the page needs them. **[H2]** marks high-priority question coverage, not a compulsory heading on every page type.",
         "- Page job takes precedence over competitor section order. On commercial pages, place questions in the "
         "offer/process/eligibility sections or a compact FAQ with H3s; record their placement in outline coverage notes.",
         "- Answer every relevant question listed: **[H2]** as a guide heading or commercial section/FAQ answer; **[in section]** in a sentence or two inside that "
         "section, in the question's own words; **[link]** briefly, then link the page named. A question you cannot "
         "answer from verified facts or the client's pages gets `Skip: <question> — <reason>` in outline.md.",
         "- \"Cover\" lists what the ranking pages discuss in that section: the entities to name and the figures to give. "
         "Take values from knowledge_graph.md; numbers only from verified facts (the fact ids under each section).",
         "- Sections and questions from one site only are optional angles; use the ones that serve this page's reader.", ""]

    def facts_for(s):
        st = set(s.get("tokens") or [])
        need = 2 if len(st) >= 3 else 1
        hits = [(len(st & t), f) for f, t in ftok if len(st & t) >= need]
        hits.sort(key=lambda x: (-x[0], x[1]["client"]))
        return [f for _, f in hits[:5]]

    def block(s, level):
        hd = "#" * level
        cov = len(s["covered_by"])
        L.append(f"{hd} {s['id']}. {s['title']} — {cov}/{n} ranking pages" if cov else f"{hd} {s['id']}. {s['title']} — from searches")
        heads = [h for h in s["headings"] if h.lower() != s["title"].lower()]
        if heads:
            L.append("Ranking pages head it: " + " · ".join(f"\"{h}\"" for h in heads[:3]))
        if s["questions"]:
            L.append("Questions:")
            for q in s["questions"]:
                tag = DECISION.get(q["decision"], q["decision"])
                extra = []
                if q.get("competitors"):
                    extra.append(f"asked on {q['competitors']} ranking page(s)")
                where = SOURCE.get(q["source"], q["source"])
                line = f"- **[{tag}]** {q['q']} ({where}{'; ' + '; '.join(extra) if extra else ''})"
                if q["decision"] == "existing_page" and q.get("url"):
                    line += f" → {q['url']}"
                L.append(line)
                if q.get("variants"):
                    L.append("  - also asked as: " + " · ".join(f"\"{v}\"" for v in q["variants"][:4]))
                if q.get("lead") and q["lead"].get("snippet"):
                    L.append(f"  - Google's current answer (a lead; verify any number): \"{q['lead']['snippet'][:200]}\""
                             + (f" — {q['lead']['link']}" if q["lead"].get("link") else ""))
        cover = []
        if s.get("entities"):
            cover.append("entities: " + ", ".join(s["entities"][:8]))
        if s.get("attributes"):
            cover.append("figures: " + "; ".join(f"{a['name']} " + ", ".join(f"{_q(q)}{v} ({c})" for v, q, c in a["values"][:2])
                                                  for a in s["attributes"][:3]))
        if s.get("relations"):
            cover.append("links: " + "; ".join(f"{r['s']} {r['p']} {r['o']}" for r in s["relations"][:3]))
        if cover:
            L.append("Cover — " + " | ".join(cover))
        fs = facts_for(s)
        if fs:
            L.append("Facts for it: " + ", ".join(f"`{f['id']}`" for f in fs))
        L.append("")
        for ss in s.get("subsections", []):
            block(ss, level + 1)
    for s in secs:
        block(s, 2)
    if o.get("not_here"):
        L += ["## Not on this page", ""]
        L += [f"- {x['q']} — {DECISION.get(x['decision'], x['decision'])}: {x['reason']}" for x in o["not_here"]]
        L.append("")
    if o.get("mention_only"):
        L += ["## Other brands searchers name (mention only where a comparison helps; never a section)", ""]
        L += [f"- {x['q']}" for x in o["mention_only"]] + [""]
    if o.get("other_searches"):
        L += ["## Search phrasings to use where they fit (not questions, not sections)", ""]
        L += ["- " + " · ".join(x["q"] for x in o["other_searches"][:20]), ""]
    if o.get("single_site_questions"):
        L += ["## Questions one ranking page asks that fit no section (answer briefly if they serve the reader)", ""]
        L += [f"- {x['q']}" for x in o["single_site_questions"][:15]] + [""]
    if o.get("single_site_angles"):
        L += ["## Sections only one ranking page has (optional angles, information gain)", ""]
        L += ["- " + " · ".join(o["single_site_angles"][:12]), ""]
    return "\n".join(L).rstrip() + "\n"
