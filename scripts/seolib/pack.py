"""Writer pack: the foundation pack (facts, products, links, client) plus the
research the plugins produced. The writer reads this file and the rules only."""
from __future__ import annotations

from pathlib import Path

from . import common as C
from .prep import writer_pack


def foreign_place(item: dict, region: str):
    """The other country a forum item is about, if any ("r/CarsAustralia" on a UK page), else None."""
    import re
    from urllib.parse import urlparse
    from .nlp import _gazetteer, places
    text = " ".join([item.get("url") or "", item.get("title") or "", " ".join(item.get("excerpts") or []),
                     item.get("snippet") or ""])
    found = places(text) - {region}
    m = re.search(r"/r/([A-Za-z0-9_]+)", urlparse(item.get("url") or "").path)
    if m:
        sub = m.group(1).lower()
        for name, code in _gazetteer().items():
            if len(name) >= 5 and " " not in name and name in sub and "geo:" + code.lower() != region:
                found.add("geo:" + code.lower())
    return sorted(found)[0] if found else None


def _load(rd: Path, name: str) -> dict:
    return C.load_json(rd / "research" / f"{name}.json") or {}


def _effective_range(rd: Path, sheet: dict) -> None:
    """Length follows the SERP both ways: toward the ranking pages' median, never into padding."""
    comp = _load(rd, "competitor_scrape") or {}
    med = comp.get("median_words") or 0
    lo, hi = (sheet["brief"].get("word_range") or [0, 0])
    if not (med and lo and sheet["brief"].get("page_type") in ("guide", "product-guide", "spoke")):
        return
    e_lo = int(min(max(lo, round(0.8 * med, -1)), 1.5 * lo))
    e_hi = int(min(max(hi, round(1.15 * med, -1)), 2 * hi))
    if med < lo:
        e_lo = int(max(0.6 * lo, round(1.3 * med, -1)))
    if (e_lo, e_hi) != (lo, hi):
        with C.file_lock(rd / "fact_sheet.json"):
            sh = C.load_json(rd / "fact_sheet.json")
            sh["brief"]["word_range_effective"] = [e_lo, e_hi]
            C.save_json(rd / "fact_sheet.json", sh)
        sheet["brief"]["word_range_effective"] = [e_lo, e_hi]


def research_pack(rd: Path) -> None:
    sheet = C.load_json(rd / "fact_sheet.json")
    lm = C.load_json(rd / "link_map.json")
    _effective_range(rd, sheet)
    # YMYL "auto" is decided by serp_intel, which runs alongside the foundation step: settle it here, once both
    # have finished, so the pack, lint and validate all see the same answer
    s_out = _load(rd, "serp_intel")
    if sheet.get("brief", {}).get("ymyl") not in (True, False) and s_out and "ymyl" in s_out:
        with C.file_lock(rd / "fact_sheet.json"):
            sheet = C.load_json(rd / "fact_sheet.json")
            sheet["brief"]["ymyl"] = bool(s_out["ymyl"])
            sheet["brief"]["ymyl_basis"] = f"auto: {s_out.get('authority_results')} authority results in the top 10"
            C.save_json(rd / "fact_sheet.json", sheet)
    writer_pack(rd, sheet, lm)
    serp, qmap, comp = _load(rd, "serp_intel"), _load(rd, "query_map"), _load(rd, "competitor_scrape")
    kg, gain, voice = _load(rd, "semantic_graph"), _load(rd, "info_gain"), _load(rd, "site_profile")
    mode = (sheet.get("research") or {}).get("mode", "deep")
    ymyl = sheet["brief"].get("ymyl") is True
    W = ["", "---", "", f"# Research ({mode} mode)", ""]
    if serp and not serp.get("error"):
        it = serp["intent"]
        W += ["## Search intent and what Google rewards",
              f"- Intent: **{it['primary']}**" + (f", secondary {it['secondary']}" if it.get("secondary") else "")
              + f" (confidence {it['confidence']}). Evidence: " + "; ".join(it["evidence"]),
              f"- Dominant format in the top 10: **{serp['format']['dominant']}** ({serp['format']['counts']})",
              "- SERP make-up: " + ", ".join(f"{k} {v}" for k, v in serp["composition"]["by_kind"].items()),
              "- SERP features: " + (", ".join(k for k, v in serp["features"].items() if v) or "none"),
              ]
        W += [f"- {n}" for n in serp["composition"]["notes"]]
        W += ["", "Top 10:"]
        W += [f"{o['position']}. {o['title']} ({o['domain']}, {o['kind']}, {o['shape']})" for o in serp["organic"]]
        W.append("")
    cur, gsc, kr, cl = _load(rd, "current_page"), _load(rd, "gsc_insights"), _load(rd, "keyword_research"), _load(rd, "clarity_ux")
    if cur.get("exists"):
        W += ["## Rewrite: what the page has today",
              f"- {cur.get('words')} words; title \"{cur.get('title')}\"; meta \"{cur.get('meta_description')}\"",
              "- Current outline: " + " / ".join(f"H{l} {h}" for l, h in cur.get("outline", [])[:25]),
              "- Keep what earns impressions (Search Console below); fix what doesn't. Don't drop a section that ranks.", ""]
    if gsc.get("rows") or gsc.get("existing_topic_pages"):
        W += [f"## Search Console (window {gsc.get('window')}; source {gsc.get('source')})"]
        if gsc.get("rows"):
            t = gsc["totals"]
            W += [f"{t['queries']} queries, {t['clicks']} clicks, {t['impressions']} impressions. Top queries:",
                  "| Query | Clicks | Impr. | CTR | Pos. |", "|---|---:|---:|---:|---:|"]
            W += [f"| {r['query']} | {r['clicks']} | {r['impressions']} | {r['ctr']:.1%} | {r['position']} |" for r in gsc["rows"][:15]]
            if gsc.get("striking"):
                W.append("Striking distance (positions 4–20; cover each explicitly, ideally in a heading or opening sentence): "
                         + "; ".join(f"{r['query']} (pos {r['position']}, {r['impressions']} impr.)" for r in gsc["striking"][:12]))
            if gsc.get("low_ctr"):
                W.append("Page-1 queries with weak CTR (rewrite title and meta description to match them): "
                         + "; ".join(f"{r['query']} (pos {r['position']}, CTR {r['ctr']:.1%})" for r in gsc["low_ctr"]))
            if gsc.get("gaps"):
                W.append("Query gaps (the page shows for these but lacks their words): "
                         + "; ".join(f"{r['query']} (missing: {', '.join(r['missing_terms'])})" for r in gsc["gaps"][:12]))
            if gsc.get("cannibalisation"):
                W.append("Cannibalisation (other client pages also show): " + "; ".join(
                    f"{q} → {', '.join(c['page'] for c in cs[:2])}" for q, cs in list(gsc["cannibalisation"].items())[:8]))
        for o in gsc.get("existing_topic_pages") or []:
            W.append(f"- Client page already showing for this topic: {o['page']} ({o['impressions']} impressions; e.g. {', '.join(o['queries'][:3])})")
        W.append("")
    if kr.get("keywords"):
        W += [f"## Keyword data (DataForSEO; source {kr.get('source')})",
              "Use the highest-volume variants that fit the intent in headings and opening sentences; never stuff."]
        W += [f"- {k['keyword']}: {k.get('search_volume') or 0}/mo, intent {k.get('intent') or '?'}" for k in kr["keywords"][:15]]
        W.append("")
    if cl.get("recommendations"):
        W += ["## Visitor behaviour (Microsoft Clarity, last 3 days)"] + [f"- {r}" for r in cl["recommendations"]] + [""]
    off = []
    for n in ("gsc_insights", "keyword_research", "clarity_ux", "reddit_voice"):
        d = _load(rd, n)
        if d.get("not_configured"):
            off.append(f"- {n}: not configured ({d['not_configured']})" + (f"; MCP route: {d['mcp_route']}" if d.get("mcp_route") else ""))
    if off:
        W += ["## Connectors not used this run"] + off + [""]
    if qmap and not qmap.get("error"):
        W += ["## Questions to answer as H2s (People Also Ask)",
              "Use each as an H2 in the reader's words, answered in its first 40–50 words."]
        answers = serp.get("paa_answers", {}) if serp else {}
        recs = {r["query"]: r for r in qmap.get("queries", [])}

        def extra(r):
            bits = [r.get("source", "")]
            if r.get("search_volume") is not None:
                bits.append(f"{r['search_volume']}/mo")
            if r.get("gsc"):
                bits.append(f"GSC pos {r['gsc']['position']}, {r['gsc']['impressions']} impr.")
            return " [" + ", ".join(b for b in bits if b) + "]"
        for q in qmap.get("h2_questions", []):
            a = answers.get(q) or {}
            hint = f" — Google's current answer source: {a.get('link')}" if a.get("link") else ""
            W.append(f"- {q}{extra(recs.get(q, {}))}{hint}")
            if a.get("snippet"):
                # a lead, not a fact: numbers in it need `seo.py prep --add-fact` against that link before they go in
                W.append(f"  - answer lead ({a.get('from', 'PAA')}, verify before stating numbers): \"{a['snippet'][:260]}\"")
        other = [r for r in qmap.get("queries", []) if r["decision"] not in ("h2", "drop")]
        if other:
            W += ["", "Related searches and variants:"]
            # a page offered as the link target must be live: a sitemap can list pages that are gone
            targets = sorted({r["url"] for r in other if r.get("url")})
            live = C.run_async(C.fetch_many([{"url": u, "kind": "status", "parse": "status"} for u in targets])) if targets else {}
            for r in other:
                st = (live.get(r.get("url")) or {}).get("status") if r.get("url") else None
                loc = (live.get(r.get("url")) or {}).get("location") or "" if r.get("url") else ""
                if st in (301, 302, 303, 307, 308) and loc:
                    from urllib.parse import urljoin
                    new = urljoin(r["url"], loc)
                    if C.host(new) == C.host(r["url"]):
                        r = dict(r, url=new)
                        if new not in lm.get("internal", []):
                            lm.setdefault("internal", []).append(new)
                            C.save_json(rd / "link_map.json", lm)
                if st in (404, 410):
                    r = dict(r, decision="cover_in_section", url=None,
                             reason=f"the client page listed for it is gone (HTTP {st}); answer it briefly in the closest section")
                tgt = f" → link {r['url']}" if r.get("url") else ""
                W.append(f"- \"{r['query']}\"{extra(r)}: **{r['decision']}**{tgt} ({r['reason']})")
        W.append("")
    if comp and not comp.get("error"):
        med = comp.get("median_words") or 0
        lo, hi = (sheet["brief"].get("word_range") or [0, 0])
        if med and lo and sheet["brief"].get("page_type") in ("guide", "product-guide", "spoke"):
            e_lo = int(min(max(lo, round(0.8 * med, -1)), 1.5 * lo))
            e_hi = int(min(max(hi, round(1.15 * med, -1)), 2 * hi))
            if med < lo:  # the pages that rank are short: don't pad to the brief's floor
                e_lo = int(max(0.6 * lo, round(1.3 * med, -1)))
            if (e_lo, e_hi) != (lo, hi):
                with C.file_lock(rd / "fact_sheet.json"):
                    sh = C.load_json(rd / "fact_sheet.json")
                    sh["brief"]["word_range_effective"] = [e_lo, e_hi]
                    C.save_json(rd / "fact_sheet.json", sh)
                sheet["brief"]["word_range_effective"] = [e_lo, e_hi]
                W += [f"## Length: aim for {e_lo}–{e_hi} words",
                      f"The brief asks for {lo}–{hi}, but the top pages' median is {med} words: a guide that skips what they "
                      "cover loses to them. Length comes from covering their shared topics and adding your own, never from padding.", ""]
        W += [f"## What the top pages cover ({len(comp['pages'])} read, median {comp.get('median_words')} words)",
              "Their shared sections, in their order, with every question asked under each: `topic_outline.md`."]
        if comp.get("skipped"):
            W.append("Not read: " + "; ".join(f"{s['url']} ({s['why']})" for s in comp["skipped"][:8]))
        W.append("")
    if kg and not kg.get("error"):
        g = kg.get("graph") or {}
        W += ["## Knowledge graph and topic outline (read both before the outline and the draft)",
              f"- `knowledge_graph.md`: {len(g.get('entities', []))} entities of this topic in this market, typed and defined, "
              f"{len(g.get('attributes', []))} attributes with the values the ranking pages state, "
              f"{len(g.get('relations', []))} relationships, and the verified facts attached to each entity. What to say.",
              "- `topic_outline.md`: the sections the ranking pages share, macro to micro, and every People Also Ask "
              "question, related search and competitor question placed in the section that answers it. What to cover.",
              ("- Numbers on this page come only from verified facts; values in the graph are leads." if ymyl else
               "- A value three or more sites state may be used as stated; any other number needs a verified fact.")]
        if kg.get("must_cover_entities"):
            W.append("- Must-cover entities (in 40%+ of top pages): " + ", ".join(kg["must_cover_entities"]))
        if kg.get("contradictions"):
            W.append("- Where the ranking pages disagree: " + "; ".join(
                f"{c['entity']}: " + ", ".join(f"{v} ({len(d)})" for v, d in c["values"]) for c in kg["contradictions"]))
        if kg.get("paa_gaps"):
            W.append("- Information gain, PAA questions no top page answers: " + "; ".join(kg["paa_gaps"]))
        W.append("")
    if gain and gain.get("items"):
        W += ["## Real-world experience and opinion (attribute it; never present it as fact)",
              "Use one only when it is a real comment from readers like this page's (same country, same situation) and it "
              "helps; quote or closely paraphrase it and say where it comes from. Never write a crowd claim (\"people on "
              "Reddit say…\") that no comment below supports. Never take a rule or a number from here."]
        region = "geo:" + ((sheet["brief"].get("locale") or "en-GB").partition("-")[2].lower() or "gb")
        local = [i for i in gain["items"] if foreign_place(i, region) is None]
        dropped = len(gain["items"]) - len(local)
        if dropped:
            W.append(f"(Left out {dropped} item(s) from another country's community or about another country.)")
        for i in local[:6]:
            src = f"{i['domain']} ({i['kind']})"
            if i.get("excerpts"):
                W += [f"- {src}, {i['url']}: \"{x[:300]}\"" for x in i["excerpts"][:2]]
            elif i.get("snippet"):
                W.append(f"- {src}, {i['url']} (Google snippet): \"{i['snippet'][:250]}\"")
        W.append("")
    if voice and not voice.get("error") and voice.get("pages_read"):
        W += ["## The client's voice (match it; keep the site's essence)",
              f"- Measured on {len(voice.get('pages_read', []))} of its pages: average sentence {voice.get('avg_sentence_words')} words; "
              f"\"you\" in {round(100 * (voice.get('you_share') or 0))}% of sentences, \"we/our\" in {round(100 * (voice.get('we_share') or 0))}%; "
              f"{voice.get('contractions_per_100_sentences')} contractions per 100 sentences; headings in {voice.get('heading_case')} "
              "(this page still uses sentence case unless the live H1 says otherwise)."]
        W += [f"- Sample: \"{x}\"" for x in voice.get("excerpts", [])[:2]]
        W.append("")
    if mode == "deep":
        W += ["## Next steps", "1. Write `outline.md` (H1, H2s, H3s, one line per heading on what it answers and which facts it uses).",
              "2. Run the outline check. 3. Write the draft from the outline. 4. Lint, fix, validate."]
    with open(rd / "writer_pack.md", "a", encoding="utf-8") as f:
        f.write("\n".join(W) + "\n")
    from .kgdoc import write_docs
    write_docs(rd)
