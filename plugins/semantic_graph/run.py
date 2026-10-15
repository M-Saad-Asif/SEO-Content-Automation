"""Semantic graph: the knowledge graph of the topic in this market (seolib.graph: entities, attribute values,
relationships, definitions, every node and edge with its sources), the figures most top pages agree on, the heading
topics Google expects, and the PAA questions no top page answers."""
import re
import hashlib
import json
from pathlib import Path
from collections import Counter, defaultdict

STOPW = set("a an the and or of to in on for with by from at as is are be your our their its this that these those "
            "how what why when where which who can do does you we it more most".split())
from seolib.graph import UI_HEADING
NOISE = re.compile(r"(written by|edited by|reviewed by|^by:|\bauthor\b|app store|play store|\brating\b|verified reviews|"
                   r"free forever|click here|subscribe|cookie|captcha|enter your (email|phone)|a minute of your time|"
                   r"we submit|our (team|experts|customers)|trusted by|over \d[\d,.]* (million|thousand)? ?\w+|"
                   r"sign up|log ?in to|download (our|the) app|^home\b|all rights reserved|last updated)", re.I)


def ctoks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOPW and len(w) > 2}


def run(ctx):
    comp = ctx.load("competitor_scrape")
    pages = comp.get("pages", [])
    if not pages:
        return {"error": "no competitor pages to analyse"}
    srcs = [p["domain"] for p in pages]
    # The knowledge graph: entities, attribute values and relationships, each with its sources (seolib.graph).
    from seolib import graph as G
    serp = ctx.load("serp_intel") or {}
    qmap0 = ctx.load("query_map") or {}
    searches = list(serp.get("paa", [])) + list(serp.get("related", [])) + list(serp.get("autocomplete", []))
    searches += list(serp.get("question_autocomplete", [])) + [r["query"] for r in qmap0.get("queries", [])]
    for x in (serp.get("expansions") or {}).values():
        searches += list(x.get("paa", [])) + list(x.get("related", []))
    # whole pages from another market are left out only where the market decides the facts (YMYL: money, law, health)
    ym = ctx.brief.get("ymyl")
    strict = ym is True or (ym not in (True, False) and bool(serp.get("ymyl")))
    # Local extraction is already JSON. Fact verification alone need not extract sources again.
    code = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (__file__, G.__file__)]
    digest = hashlib.sha256(json.dumps([code, pages, searches, qmap0, strict, ctx.brief.get("target_query"),
                                       ctx.brief.get("locale"), ctx.brief.get("synonyms")], sort_keys=True).encode()).hexdigest()
    previous = ctx.load("semantic_graph") or {}
    if not ctx.refresh and previous.get("input_digest") == digest:
        return previous
    kg_full = G.build(pages, ctx.brief.get("target_query", ""), ctx.brief.get("locale") or "en", searches,
                      strict_market=strict)
    kg_full.pop("unnamed_figures", None)
    if not kg_full.get("spacy"):
        ctx.decisions.append("semantic_graph: spaCy unavailable; the knowledge graph ran on plain rules "
                             "(entity types are less precise, everything else is the same)")
    if kg_full.get("foreign_pages"):
        ctx.decisions.append("Knowledge graph: left out " + ", ".join(kg_full["foreign_pages"]) +
                             " (written for another market: its amounts and rules are not this market's)")
    n_pages = len(pages)
    # Figures (number + unit) that several independent top pages state: the industry consensus a reader expects
    # ("replace at 3 mm", "100-350 g a day"). Usable on ordinary pages; leads to verify on YMYL pages.
    # a figure is a number with a unit, or a money amount ("£20,000", "$7,000") that needs no unit after it
    FIG = re.compile(r"(£|\$|€)?\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:\s?(?:-|–|to)\s?(£|\$|€)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?))?"
                     r"(?:\s?(%|per cent|mm|cm|km|kg|mg|g|ml|litres?|l|days?|weeks?|months?|years?|hours?|minutes?|"
                     r"times a (?:day|week|year)|kcal|calories|°c|degrees|pence|p)\b)?", re.I)
    figs = defaultdict(lambda: {"df": set(), "examples": []})
    # block by block: figures often sit in table cells and list items, which run together if joined
    from seolib.domains import org_domain
    away = set(kg_full.get("foreign_pages") or [])
    units = [(x, org_domain(p["domain"])) for p in pages if p["domain"] not in away
             for t, x in p["blocks"] if t in ("p", "li", "td", "dd", "tr", "blockquote")]
    from seolib.nlp import tokens as _tk
    # short topic words count too ("ISA", "VAT", "CRM"): only function words are left out
    qwords = {w for w in _tk(ctx.brief.get("target_query", ""), ctx.brief.get("synonyms"))
              if len(w) >= 3 and w not in STOPW}
    for text, dom in units:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if len(sent.split()) > 45 or NOISE.search(sent):
                continue
            if qwords and not (qwords & set(_tk(sent, ctx.brief.get("synonyms")))):
                continue  # "10 years" from an unrelated statistic is not the topic's consensus
            for m in FIG.finditer(sent):
                if not (m.group(5) or m.group(1)):
                    continue  # a bare number with no unit or currency is not a figure
                u5 = (m.group(5) or "").lower()
                unit = u5 if u5 in ("%", "kg", "mg", "g", "") else u5.rstrip("s")
                lo, hi = m.group(2).replace(",", ""), (m.group(4) or "").replace(",", "")
                val = ((m.group(1) or "") + lo + (("-" + hi) if hi else "") + (" " + unit if unit else "")).strip()
                key = val
                f = figs[key]
                if dom not in f["df"] and len(f["examples"]) < 2:
                    f["examples"].append({"sentence": sent.strip()[:220], "source": dom})
                f["df"].add(dom)
    consensus_figures = sorted(({"figure": k, "domains": sorted(v["df"]), "examples": v["examples"]}
                                for k, v in figs.items() if len(v["df"]) >= max(2, round(0.35 * len(set(srcs))))),
                               key=lambda r: -len(r["domains"]))[:20]
    ents = kg_full["entities"]
    ent_list = [{"entity": e["name"], "key": e["key"], "label": e["type"], "domains": len(e["domains"]),
                 "mentions": e["mentions"]} for e in ents[:60]]
    must = [e["name"] for e in ents if len(e["domains"]) >= max(2, round(0.4 * n_pages))
            and e["type"] not in ("measure",)][:25]
    name = {e["key"]: e["name"] for e in ents}

    def legacy_triple(r):
        ex = r["example"]
        return {"triple": [r["subject"], r["predicate"], r["object"]], "domains": r["domains"],
                "example": {"s": ex["s"], "p": ex["p"], "o": ex["o"], "sentence": ex["sentence"], "source": ex["source"]}}
    consensus = [legacy_triple(r) for r in kg_full["relations"] if r["consensus"]]
    unique = [legacy_triple(r) for r in kg_full["relations"] if not r["consensus"]][:40]
    attrs = {}
    for a in kg_full["attributes"]:
        label = a["attribute_name"] if a["entity"] == kg_full["central"] else f"{name.get(a['entity'], a['entity'])} {a['attribute_name']}"
        attrs[label] = [{"value": v["value"], "domains": v["domains"],
                         "example": {"sentence": v["example"]["sentence"], "source": v["example"]["source"],
                                     "label": a["kind"].upper()}} for v in a["values"]]
    contra = [{"entity": a["attribute_name"], "values": [(v["value"], v["domains"]) for v in a["values"][:4]]}
              for a in kg_full["attributes"] if a.get("differs")]
    # heading topics: cluster competitor H2/H3s by shared content words
    heads = [(p["domain"], re.sub(r"^\s*(#+\s*)?(\d+[.)]|step \d+[:.]?)?\s*", "", h, flags=re.I))
             for p in pages for lvl, h in p["outline"] if lvl in (2, 3)]
    topics = []
    # the query's own words are in every heading ("CRM", "tulips"): clustering on them merges unrelated sections
    q_stem = {w.rstrip("s") for w in ctoks(ctx.brief.get("target_query", ""))}
    for dom, h in heads:
        if UI_HEADING.search(h):  # shop and blog widgets are not topics
            continue
        ht = {w for w in ctoks(h) if w.rstrip("s") not in q_stem}
        if not ht:  # "Where to plant tulips": the question word is the topic
            wh = re.match(r"\W*(when|where|how|why|what|which|who)\b", h.lower())
            if not wh:
                continue
            ht = {"_" + wh.group(1)}
        best = None
        for tp in topics:
            j = len(ht & tp["tokens"]) / len(ht | tp["tokens"])
            if j >= 0.4 and (best is None or j > best[0]):
                best = (j, tp)
        if best:
            best[1]["domains"].add(dom)
            best[1]["tokens"] |= ht
            if len(best[1]["examples"]) < 3:
                best[1]["examples"].append(h)
        else:
            topics.append({"tokens": set(ht), "domains": {dom}, "examples": [h]})
    topics = sorted(({"topic": t["examples"][0], "examples": t["examples"], "domains": len(t["domains"])}
                     for t in topics), key=lambda t: -t["domains"])
    expected = [t for t in topics if t["domains"] >= 2][:20]
    qmap = ctx.load("query_map")
    all_heads = [h for _, h in heads]
    gaps = []
    for q in qmap.get("h2_questions", []):
        qt = ctoks(q)
        cov = max((len(qt & ctoks(h)) / max(1, len(qt)) for h in all_heads), default=0)
        if cov < 0.5:
            gaps.append(q)
    decisions = []
    if gaps:
        decisions.append(f"{len(gaps)} People Also Ask question(s) are not answered by any top-10 page: "
                         "answering them is this page's information gain.")
    return {
        "input_digest": digest,
        "pages_analysed": n_pages, "entities": ent_list, "must_cover_entities": must,
        "attributes": attrs, "triples_consensus": consensus[:60], "triples_unique": unique,
        "contradictions": contra, "heading_topics": expected, "paa_gaps": gaps, "decisions": decisions,
        "consensus_figures": consensus_figures, "graph": kg_full,
        "summary": f"{len(ents)} entities ({len(must)} must-cover), {len(kg_full['attributes'])} attributes, "
                   f"{len(kg_full['relations'])} relations ({len(consensus)} consensus), {len(expected)} expected "
                   f"topics, {len(gaps)} PAA gaps" + (" [spaCy off]" if not kg_full.get("spacy") else ""),
    }
