"""Topic outline: every question searchers and ranking pages ask about the topic, in the sections the ranking
pages share, ordered macro to micro, each section with the knowledge-graph items that belong to it.

Sections come from the ranking pages' own H2 and H3 headings (with the text under each), clustered across sites by
their words and their text, so "How much can I borrow?" and "Loan amounts" become one section. H3 clusters that
mostly sit under one section's H2s become its sub-sections. Order is where the ranking pages put each section.

Questions, in order of weight: Search Console queries, People Also Ask (this market's, then borrowed), question
autocomplete, competitors' question headings and FAQ entries (every one, not only the shared ones), related
searches, autocomplete. Routing (H2 here, inside a section, another page, dropped) is the query map's decision;
this plugin organises and never overrides it. Niche-free: nothing here names a sector.
"""
import math
import re
from collections import Counter, defaultdict
from statistics import median

from seolib import graph as G
from seolib.nlp import places, same_stem, tokens

STOP = {"how", "to", "what", "is", "be", "the", "a", "an", "my", "your", "for", "of", "in", "on", "do", "i", "can",
        "you", "are", "with", "by", "and", "or", "me", "it", "its", "that", "this", "there", "if", "at", "from", "as",
        "why", "which", "where", "when", "who", "should", "will", "would", "could", "any", "s", "does", "get", "need",
        "about", "more", "most", "best", "good", "our", "their", "they", "them", "than", "into", "out", "up", "so",
        "not", "no", "have", "has", "one", "some", "there", "here", "all", "also", "just", "much", "many"}
COMPARE = {"difference", "differ", "vs", "versus", "compare", "comparison", "compared", "between"}
QWORD = re.compile(r"^(how|what|why|which|where|when|who|whom|whose|can|could|should|would|will|do|does|did|is|are|"
                   r"was|were|has|have|may|might|must)\b", re.I)
SELF = re.compile(r"\b(our|we|we're|we've|we'll)\b|\b[Uu]s\b(?<!US)", re.I)
# where a kind of question sits in an article that explains something, when no ranking page gives a position
SLOT = [(0.03, re.compile(r"^(what (is|are)|what does .* mean|meaning|definition|define)\b", re.I)),
        (0.22, re.compile(r"\bhow (does|do|is|are)\b.*\bwork|\bworks?\b", re.I)),
        (0.35, re.compile(r"\b(why|when) (use|would|should|choose|consider)\b|\bused for\b|^why\b", re.I)),
        (0.42, re.compile(r"\b(can i|can you|eligib|qualif|criteria|requirement|who can|accept|refuse|allowed)", re.I)),
        (0.5, re.compile(r"\b(how much|cost|price|rate|fee|charge|interest|afford|cheap|expensive|pay)", re.I)),
        (0.6, re.compile(r"\b(how (long|quick|fast)|how to|apply|applying|application|process|step|timeline|arrange)\b", re.I)),
        (0.72, re.compile(r"\b(vs|versus|difference|compare|compared|alternative|instead)", re.I)),
        (0.8, re.compile(r"\b(risk|downside|drawback|disadvantage|pros|cons|danger|default|lose|worth it|good idea|"
                         r"bad idea|mistake|avoid|never|not to do|problem|wrong|go wrong)", re.I))]


_TOPIC: set = set()


def cluster_kind(c):
    """The sort of question most of a section's headings ask, when most of them ask one; else None."""
    ks = Counter(k for k in (kind_of(m["heading"]) for m in c.get("members", [])) if k is not None)
    if not ks:
        return None
    k, n = ks.most_common(1)[0]
    return k if n >= 0.5 * len(c["members"]) else None


def kind_of(text):
    """What sort of question a heading or search asks (definition, how it works, cost, risk ...); None: no clear sort.
    Read without the topic's own words ("charge" on a second-charge page is the topic, not a cost question). A specific
    sort wins over the generic "what is/are": "What are the risks?" is about risk, not a definition."""
    t = " ".join(w for w in re.findall(r"[\w'-]+", text) if not any(w.lower().startswith(x) for x in _TOPIC))
    k = next((n for n, (_, rx) in enumerate(SLOT) if n and rx.search(t)), None)
    return k if k is not None else (0 if SLOT[0][1].search(t) or re.search(r"\bmean\b", t, re.I) else None)
SOURCE_RANK = {"gsc": 0, "paa": 1, "paa_autocomplete": 2, "paa_dfs": 2, "paa_expanded": 3, "top_page_headings": 3,
               "competitor": 4, "related": 5, "keyword": 5, "related_expanded": 6, "autocomplete": 7}
STRONG = {"gsc", "paa", "paa_autocomplete", "paa_dfs", "paa_expanded", "top_page_headings"}


def _cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    return dot / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())))


def run(ctx):
    serp = ctx.load("serp_intel") or {}
    qmap = ctx.load("query_map") or {}
    comp = ctx.load("competitor_scrape") or {}
    kgo = ctx.load("semantic_graph") or {}
    if not qmap or qmap.get("error"):
        return {"error": "no query map"}
    graph = kgo.get("graph") or {}
    syn = ctx.brief.get("synonyms") or {}
    query = ctx.brief.get("target_query", "")
    main = {w for w in tokens(query, syn) if w not in STOP and not w.isdigit()}
    _TOPIC.clear()
    _TOPIC.update(w[:5] for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 3 and w not in STOP)

    def content(s):
        out = set()
        for w in tokens(s, syn):
            if w in COMPARE:
                out.add("_compare")
            elif w not in STOP and not w.isdigit() and len(w) > 1:
                out.add(w)
        return out

    topic_like = set()

    def own(s):  # the question's own words: the topic's words are in every one of them and say nothing
        o = {w for w in content(s) if w not in main and w not in topic_like and not any(same_stem(w, t) for t in main)}
        if not o:
            m = QWORD.match(s.strip()) or re.search(r"\b(what|how|why|when|which|who|where)\b", s, re.I)
            o = {"_" + m.group(1).lower()} if m else set()
        return o

    def jac(a, b):
        return len(a & b) / len(a | b) if a | b else 0.0
    away = set(graph.get("foreign_pages") or [])
    pages = [p for p in comp.get("pages", []) if p["domain"] not in away]
    n_pages = len({p["domain"] for p in pages}) or 1
    brands = {p["domain"].lower().removeprefix("www.").split(".")[0] for p in comp.get("pages", [])}
    brands |= {(o.get("domain") or "").lower().removeprefix("www.").split(".")[0] for o in serp.get("organic", [])}
    client_root = (ctx.brief.get("domain") or "").replace("https://", "").replace("www.", "").split(".")[0].lower()
    brands = {b for b in brands if len(b) > 3 and b != client_root and not any(same_stem(b, t) for t in main)}
    home_geo, home_cur = G.market_of(ctx.brief.get("locale") or "en-GB")

    def brand_of(h):
        flat = re.sub(r"[^a-z0-9]", "", h.lower())
        return next((b for b in brands if b in flat), None)

    def unusable(h):  # page furniture, a call to action, a competitor talking about itself, or another market
        return bool(G.UI_HEADING.search(h) or G.CTA.search(h) or SELF.search(h) or brand_of(h)
                    or G.foreign(h, home_geo, home_cur) or len(h.split()) > 16)
    # 1. units: every H2 and H3 of every ranking page, with the text under it
    units = []
    for p in pages:
        bl = p.get("blocks", [])
        has_h2 = sum(1 for t, _ in bl if t == "h2") >= 2
        lv = {"h2": 2, "h3": 3} if has_h2 else {"h3": 2, "h4": 3}
        heads = [i for i, (t, _) in enumerate(bl) if t in lv]
        cur, parent = None, None
        for i, (t, x) in enumerate(bl):
            x = G.clean(x).strip().lstrip("#").strip()
            if t in lv:
                level = lv[t]
                h = re.sub(r"^\s*(\d+[.)]|step \d+[:.]?)\s*", "", x, flags=re.I)
                bad = unusable(h) or (level == 3 and parent is not None and not parent["usable"])
                cur = {"dom": p["domain"], "heading": h, "level": level, "usable": not bad, "text": [],
                       "pos": heads.index(i) / max(1, len(heads) - 1), "parent": parent if level == 3 else None}
                if level == 2:
                    parent = cur
                units.append(cur)
            elif cur is not None and t in ("p", "li", "td", "dd", "tr", "h4", "dt"):
                cur["text"].append(G.clean(x))
    kids = Counter(id(u["parent"]) for u in units if u.get("parent"))
    for u in units:
        if u.get("parent") is not None and kids[id(u["parent"])] > 6:
            u["level"], u["parent"] = 2, None  # an H2 holding 7+ H3s is a wrapper, not a section
    # a word in the headings of most ranking pages is part of the topic here, not what one section is about
    usable = [u for u in units if u["usable"]]
    hdf = Counter()
    for d in {u["dom"] for u in usable}:
        hdf.update({w for u in usable if u["dom"] == d for w in own(u["heading"]) if not w.startswith("_")})
    n_dom = len({u["dom"] for u in usable}) or 1
    share = Counter(w for u in usable for w in own(u["heading"]))
    topic_like.update(w for w, n in hdf.items() if n >= max(3, 0.6 * n_dom) and share[w] >= 0.2 * len(usable))
    for u in units:
        u["tokens"] = own(u["heading"])
        u["vec"] = Counter(w for x in u["text"][:12] for w in own(x) if not w.startswith("_"))
    # 2. cluster them across sites: same own words in the heading, or related words and the same text
    clusters = []
    for u in sorted((u for u in units if u["usable"] and u["tokens"]), key=lambda u: u["level"]):
        best, bs = None, 0.0
        for c in clusters:
            j = max(jac(u["tokens"], m["tokens"]) for m in c["members"])
            cs = _cos(u["vec"], c["vec"])
            # same words in the heading; related words and similar text; or other words ("Eligibility",
            # "Criteria") over clearly the same text
            other_site = u["dom"] not in {m["dom"] for m in c["members"]}
            score = j if j >= 0.4 else (0.5 * j + 0.5 * cs if j >= 0.2 else 0)
            ku = kind_of(u["heading"])
            if score < 0.4 and ku and cs >= 0.15 and c["kinds"].get(ku, 0) >= max(1, len(c["members"]) / 2) \
                    and u["dom"] not in {m["dom"] for m in c["members"]}:
                score = 0.4  # "Drawbacks" and "What are the risks?" on two sites, over related text
            if score > bs:
                best, bs = c, score
        if best is not None and bs >= 0.4:
            best["members"].append(u)
            best["tokens"] |= u["tokens"]
            best["vec"] += u["vec"]
            best["kinds"][kind_of(u["heading"])] += 1
            u["cluster"] = best
        else:
            c = {"tokens": set(u["tokens"]), "vec": Counter(u["vec"]), "members": [u], "items": [], "subs": [],
                 "kinds": Counter([kind_of(u["heading"])])}
            clusters.append(c)
            u["cluster"] = c
    for c in clusters:
        c["domains"] = sorted({m["dom"] for m in c["members"]})
        c["pos"] = median(m["pos"] for m in c["members"])
        c["level"] = min(m["level"] for m in c["members"])
        c["text_tokens"] = Counter()
        for m in c["members"]:
            c["text_tokens"].update({w for x in m["text"] for w in own(x) if not w.startswith("_")})
    # H3 clusters that mostly sit under one section's H2s are that section's sub-sections
    nested = set()
    for c in clusters:
        if c["level"] != 3:
            continue
        par = Counter(id(m["parent"]["cluster"]) for m in c["members"] if m.get("parent") and m["parent"].get("cluster"))
        if par:
            pid, n = par.most_common(1)[0]
            host = next(x for x in clusters if id(x) == pid)
            if n >= 0.5 * len(c["members"]) and host is not c:
                host["subs"].append(c)
                nested.add(id(c))
    # 3. every question and search around the topic, with the query map's routing
    recs = {r["query"].lower(): r for r in qmap.get("queries", [])}
    answers = {k.lower(): v for k, v in (serp.get("paa_answers") or {}).items()}
    items = []
    for r in qmap.get("queries", []):
        a = answers.get(r["query"].lower()) or {}
        items.append({"q": r["query"], "source": r.get("source", ""), "decision": r.get("decision"),
                      "reason": r.get("reason", ""), "url": r.get("url"), "domains": set(), "variants": [],
                      "lead": {"snippet": a.get("snippet", "")[:220], "link": a.get("link")} if a.get("snippet") else None,
                      "own": own(r["query"])})
    raw = [(q, "paa") for q in serp.get("paa", [])] + [(q, "related") for q in serp.get("related", [])]
    raw += [(q, "paa_autocomplete") for q in serp.get("question_autocomplete", [])]
    for x in (serp.get("expansions") or {}).values():
        raw += [(q, "paa_expanded") for q in x.get("paa", [])] + [(q, "related_expanded") for q in x.get("related", [])]
    for q, src in raw:  # phrasings the query map merged into one question stay visible as variants
        if q.lower() in recs:
            continue
        o = own(q)
        tgt = max(items, key=lambda it: jac(o, it["own"]), default=None)
        if tgt and jac(o, tgt["own"]) >= 0.5 and q not in tgt["variants"]:
            tgt["variants"].append(q)
    # competitors' questions: every question heading and FAQ entry in a usable section
    comp_q = defaultdict(set)
    for u in units:
        if not u["usable"]:
            continue
        lines = [u["heading"]] + [x for x in u["text"] if len(x.split()) <= 16]
        for x in lines:
            h = re.sub(r"\s+", " ", x).strip()
            if h.endswith("?") and 3 <= len(h.split()) <= 16 and not unusable(h):
                comp_q[h].add(u["dom"])
    seps = [set(r.get("distinct_terms") or []) for r in qmap.get("queries", []) if r.get("decision") == "separate_page"]
    for h, doms in comp_q.items():
        o = own(h)
        tgt = max(items, key=lambda it: jac(o, it["own"]), default=None)
        if tgt and jac(o, tgt["own"]) >= 0.5:
            tgt["domains"] |= doms
            if h.lower() != tgt["q"].lower() and h not in tgt["variants"] and len(tgt["variants"]) < 6:
                tgt["variants"].append(h)
            continue
        if o <= {"_what"}:
            continue  # "What is a <topic>?" is the page itself: the opening answers it
        hit_sep = any(sd and sd <= content(h) for sd in seps)
        items.append({"q": h, "source": "competitor", "domains": set(doms), "variants": [], "lead": None, "own": o,
                      "decision": "separate_page" if hit_sep else "cover_in_section",
                      "reason": ("shares the terms of a query that deserves its own page" if hit_sep else
                                 f"asked by {len(doms)} ranking page(s) in a heading or FAQ"), "url": None})
    def is_q(q):
        return q.strip().endswith("?") or bool(QWORD.match(q.strip()))

    # 4. place each question in the cluster whose headings and text it matches best
    def fit(it, c):
        o = it["own"]
        if not o:
            return 0.0
        if any(re.sub(r"\W", "", m["heading"].lower()) == re.sub(r"\W", "", it["q"].lower()) for m in c["members"]):
            return 1.0
        head = max([jac(o, m["tokens"]) for m in c["members"]] + [jac(o, c["tokens"]) if not c["members"] else 0])
        if head == 0:
            return 0.0
        need = 2 if len(c["members"]) > 1 else 1
        plain = [w for w in o if not w.startswith("_")]
        text = sum(1 for w in plain if c["text_tokens"][w] >= need) / len(plain) if plain else 0.0
        return 0.7 * head + 0.3 * text
    not_here, mention, loose = [], [], []
    for it in sorted(items, key=lambda it: SOURCE_RANK.get(it["source"], 8)):
        if it["decision"] in ("drop", "separate_page"):
            not_here.append(it)
            continue
        away_ = places(it["q"]) - {home_geo, "geo:eu"} - set(places(query))
        if away_:
            it.update(decision="drop", reason=f"about another country ({', '.join(sorted(x[4:].upper() for x in away_))})")
            not_here.append(it)
            continue
        b = brand_of(it["q"])
        if b or str(it.get("reason", "")).startswith("about another brand"):
            it["reason"] = it["reason"] if not b else f"names another brand ({b})"
            mention.append(it)
            continue
        best = max(((fit(it, c), c) for c in clusters), key=lambda x: x[0], default=(0, None))
        if best[1] is not None and best[0] >= (0.3 if is_q(it["q"]) else 0.45):
            best[1]["items"].append(it)
        else:
            loose.append(it)

    # 5. keep what matters: a section 2+ ranking pages share, or one a searcher's question needs
    def demanded(c):
        return [i for i in c["items"] if i["decision"] == "h2" or (i["source"] in STRONG and is_q(i["q"]))]

    def shared(c):
        return len(c["domains"]) >= 2
    kinds = {id(c): c.get("kinds") or Counter() for c in clusters}

    def same_kind(it):  # a section 2+ sites share that answers the same sort of question
        k = kind_of(it["q"])
        cands = [c for c in clusters if k is not None and shared(c) and cluster_kind(c) == k]
        return max(cands, key=lambda c: len(c["domains"]), default=None)
    # loose questions: the shared section of the same sort, else a section of their own when searchers ask them
    single_q, other_s = [], []
    for it in loose:
        host = same_kind(it)
        if not (it["decision"] == "h2" or is_q(it["q"])):
            # a search phrasing is never a section of its own: the shared section of its sort, or the list
            (host["items"] if host is not None else other_s).append(it)
            continue
        if host is not None:
            host["items"].append(it)
            continue
        lv = Counter(w for w in own((it.get("lead") or {}).get("snippet") or "") if not w.startswith("_"))
        k = kind_of(it["q"])

        def joins(c):
            return jac(it["own"], c["tokens"]) >= 0.4 or (k not in (None, 0) and c["kinds"].get(k)) \
                or (lv and _cos(lv, c["vec"]) >= 0.35)
        g = next((c for c in clusters if not c["members"] and joins(c)), None)
        if g:
            g["items"].append(it)
            g["tokens"] |= it["own"]
            g["vec"] += lv
            g["kinds"][k] += 1
        else:
            clusters.append({"tokens": set(it["own"]), "vec": Counter(lv), "members": [], "items": [it], "subs": [],
                             "domains": [], "pos": None, "level": 2, "text_tokens": Counter(),
                             "kinds": Counter([k] if k is not None else [])})

    def keep(c):
        return shared(c) or bool(demanded(c))
    tops = [c for c in clusters if id(c) not in nested and keep(c)]
    for c in clusters:  # a shared sub-section under one page's own H2 stands as a section of its own
        if id(c) not in nested and not keep(c):
            for sc_ in [x for x in c["subs"] if keep(x)]:
                c["subs"].remove(sc_)
                tops.append(sc_)
    dropped = [c for c in clusters if id(c) not in nested and not keep(c)]
    dropped += [x for c in dropped for x in c["subs"]]
    angles = [c["members"][0]["heading"] for c in dropped if c["members"]]

    def slot(text):
        k = kind_of(text)
        return SLOT[k][0] if k is not None else 0.65
    # questions from a section only one page has: into the closest kept section, by words, text or sort of question
    for c in dropped:
        for it in c["items"]:
            best = max(((fit(it, t), t) for t in tops), key=lambda x: x[0], default=(0, None))
            k = kind_of(it["q"])
            same = [t for t in tops if k is not None and cluster_kind(t) == k]
            if best[1] is not None and best[0] >= (0.15 if is_q(it["q"]) else 0.4):
                best[1]["items"].append(it)
            elif same and is_q(it["q"]):
                max(same, key=lambda t: len(t["domains"]))["items"].append(it)
            elif is_q(it["q"]):
                single_q.append(it)
            else:
                other_s.append(it)
    loose_ac = other_s
    # sections that ask the same sort of question with a heading word in common are one section ("5 common risks
    # you must know" and "What are the risks?")
    merged_any = True
    while merged_any:
        merged_any = False
        for a in list(tops):
            ka = cluster_kind(a)
            for b in list(tops):
                if a is b or not a["members"] or not b["members"] or ka in (None, 0):
                    continue
                if ka == cluster_kind(b) and any(jac(m["tokens"], n["tokens"]) > 0 for m in a["members"] for n in b["members"]):
                    big, small = (a, b) if len(a["domains"]) >= len(b["domains"]) else (b, a)
                    big["members"] += small["members"]
                    big["items"] += small["items"]
                    big["subs"] += small["subs"]
                    big["tokens"] |= small["tokens"]
                    big["domains"] = sorted(set(big["domains"]) | set(small["domains"]))
                    big["pos"] = median(m["pos"] for m in big["members"])
                    big["text_tokens"] += small["text_tokens"]
                    tops.remove(small)
                    merged_any = True
                    break
            if merged_any:
                break
    for c in tops:
        if c["pos"] is None:
            c["pos"] = slot(c["items"][0]["q"])
        if c["tokens"] <= {"_what"}:
            c["pos"] = 0.0  # "What is …?": the definition opens the page
    tops.sort(key=lambda c: (c["pos"], -len(c["domains"])))
    # 6. the knowledge-graph items each section needs
    matcher = G.matcher_for(graph) if graph else None
    ents = {e["key"]: e for e in graph.get("entities", [])}
    central = graph.get("central")

    def describe(c, sid):
        texts = [x for m in c["members"] for x in m["text"]]
        qs = [i["q"] for i in c["items"]]
        ent_doms = defaultdict(set)
        if matcher:
            for m in c["members"]:
                for x in m["text"] + [m["heading"]]:
                    for _, _, k in matcher.find(G.words(x)):
                        ent_doms[k].add(m["dom"])
            for q in qs:
                for _, _, k in matcher.find(G.words(q)):
                    ent_doms[k].add("_search")
        need = 2 if len(c["domains"]) >= 3 else 1
        s_ents = [k for k, d in sorted(ent_doms.items(), key=lambda kv: -len(kv[1]))
                  if k != central and k in ents and len(d) >= need][:10]
        joined = " ".join(texts)
        mine = c["tokens"] | {w for q in qs for w in own(q)}
        s_attrs = [a for a in graph.get("attributes", [])
                   if any(v["example"]["sentence"][:80] in joined for v in a["values"])
                   or own(a["attribute_name"]) & mine - {"_what", "_how", "_why"}][:5]
        s_rels = [r for r in graph.get("relations", []) if r["example"]["sentence"][:80] in joined][:5]
        h2q = [i for i in c["items"] if i["decision"] == "h2"]
        names = [m["heading"] for m in c["members"]]
        if h2q:
            label = h2q[0]["q"]
        elif names:  # the heading most of the others resemble, preferring the topic's own words and a question
            label = max(names, key=lambda h: (sum(jac(own(h), own(x)) for x in names) + 0.3 * len(content(h) & main),
                                              bool(QWORD.match(h)), -len(h)))
        else:
            label = qs[0]
        return {
            "id": sid, "title": label, "pos": round(c["pos"] or 0, 2), "covered_by": c["domains"],
            "headings": list(dict.fromkeys(names))[:4],
            "questions": [{"q": i["q"], "source": i["source"], "decision": i["decision"], "reason": i["reason"],
                           "url": i.get("url"), "competitors": len(i["domains"]), "variants": i["variants"][:5],
                           "lead": i["lead"]}
                          for i in sorted(c["items"], key=lambda i: (i["decision"] != "h2", SOURCE_RANK.get(i["source"], 8)))],
            "entities": [ents[k]["name"] for k in s_ents],
            "attributes": [{"name": a["attribute_name"], "values": [(v["value"], v["qualifier"], len(v["domains"]))
                                                                      for v in a["values"][:3]]} for a in s_attrs],
            "relations": [{"s": r["example"]["s"], "p": r["predicate"], "o": r["example"]["o"],
                           "sites": len(r["domains"])} for r in s_rels],
            "tokens": sorted(w for w in mine if not w.startswith("_")),
        }
    out = []
    for n, c in enumerate(tops, 1):
        sec = describe(c, f"S{n}")
        subs = sorted(c["subs"], key=lambda s: s["pos"])
        sec["subsections"] = [describe(s, f"S{n}.{k}") for k, s in enumerate(subs, 1)][:8]
        out.append(sec)
    nh = [{"q": i["q"], "source": i["source"], "decision": i["decision"], "reason": i["reason"]} for i in not_here]
    mn = [{"q": i["q"], "source": i["source"], "reason": i["reason"]} for i in mention]
    ot = [{"q": i["q"], "source": i["source"], "decision": i["decision"]} for i in loose_ac]
    sq = [{"q": i["q"], "source": i["source"], "competitors": len(i["domains"])} for i in single_q]
    placed = [q for s in out for q in s["questions"] + [x for ss in s["subsections"] for x in ss["questions"]]]
    counts = Counter(q["source"] for q in placed)
    return {"sections": out, "not_here": nh, "mention_only": mn, "other_searches": ot, "single_site_questions": sq,
            "single_site_angles": angles[:12],
            "pages": n_pages, "counts": dict(counts),
            "summary": f"{len(out)} sections, {len(placed)} questions placed ("
                       + ", ".join(f"{k} {v}" for k, v in counts.most_common()) + f"), {len(mn)} other-brand, "
                       f"{len(nh)} for another page or dropped"}
