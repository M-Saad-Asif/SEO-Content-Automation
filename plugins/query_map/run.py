"""Query map: what belongs in this article and what belongs on another page
(keyword clustering by SERP overlap, plus the client's existing pages).

Niche-free by design: words are compared as lemmas (seolib.nlp), places come from a world gazetteer, the
subject of the query is found from the data (the main-query word the related searches repeat most), and any
niche vocabulary ("carry-on" = "cabin") comes from the client profile's `synonyms:`.
"""
import re
from collections import Counter
from urllib.parse import urlparse

from seolib.nlp import places, same_stem, tokens

# General English only. Function words, and modifiers that narrow a query without changing what it asks:
# comparison words restate a "vs" query; platforms, audiences, years and navigational words don't change the topic.
STOP = {"how", "to", "what", "is", "be", "the", "a", "an", "my", "your", "for", "of", "in", "on", "do", "i", "can",
        "you", "are", "with", "by", "and", "or", "me", "it", "its", "that", "this", "there", "if", "at", "from", "as",
        "why", "which", "where", "when", "who", "should", "will", "would", "could", "much", "many", "any", "s", "we"}
MODIFIERS = {"best", "top", "good", "great", "free", "near", "online", "check", "official", "website", "site", "legit",
             "genuine", "form", "download", "app", "difference", "between", "vs", "versus", "compare", "comparison",
             "better", "reddit", "quora", "youtube", "amazon", "woman", "women", "man", "men", "lady", "ladies",
             "citizen", "national", "resident", "holder", "people", "uk", "2024", "2025", "2026", "2027", "now",
             "today", "still", "really", "actually", "both", "some", "famous", "most", "easy", "quick", "simple",
             "spring", "summer", "autumn", "fall", "winter", "january", "february", "march", "april", "may", "june",
             "july", "august", "september", "october", "november", "december", "late", "early", "too", "year",
             "season", "month", "week"}
# light verbs and adverbs: "how long for X to be approved" asks what "how long does X take" asks
FILLER = {"be", "get", "take", "will", "do", "usually", "normally", "approve", "grant", "need", "apply"}
# words that ask for a format of the same answer ("… and how to calculate it", "… chart", "explain …"), not a new topic
FORMAT = {"explain", "explained", "calculate", "calculation", "calculator", "work", "out", "guide", "meaning", "mean",
          "definition", "define", "chart", "table", "list", "example", "examples", "formula", "estimate", "figure"}


def run(ctx):
    serp = ctx.load("serp_intel")
    if not serp or serp.get("error"):
        return {"error": "no SERP data"}
    syn = ctx.brief.get("synonyms") or {}

    def toks(s):
        return tokens(s, syn)

    def content(s):
        return {w for w in toks(s) if w not in STOP and not w.isdigit()}

    def page_key(u):
        """Same site section = same result: example.org/topic and example.org/topic/apply answer the same query."""
        pu = urlparse(u)
        seg = [x for x in pu.path.split("/") if x][:1]
        return (pu.netloc.lower().removeprefix("www.") + "/" + "/".join(seg)).rstrip("/")

    def shape(q):
        """Numbers blanked: "for 5 days" and "for 7 days" share one SERP check."""
        return re.sub(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", "#", " ".join(toks(q)))

    main = serp["query"]
    main_toks = toks(main)
    main_content = content(main) - MODIFIERS
    main_places = {w for w in main_toks if w.startswith("geo:")}

    def distinct(q):
        # "cleaner" on a "clean" page and "packing" on a "pack" page are the same topic, not new terms
        return [w for w in toks(q) if w not in main_toks and w not in STOP and w not in MODIFIERS and not w.isdigit()
                and w not in FORMAT and not any(same_stem(w, x) for x in main_toks)]

    lm = ctx.load("foundation")["link_map"]
    gsc = ctx.load("gsc_insights") or {}
    kr = ctx.load("keyword_research") or {}
    vol = {(k.get("keyword") or "").lower(): k.get("search_volume") for k in kr.get("keywords", [])}
    impr = {r["query"].lower(): r for r in (gsc.get("rows") or [])}
    cannibal = gsc.get("cannibalisation") or {}
    # Priority order: queries the page already shows for, real PAA (Serper, then DataForSEO click-depth), then the rest.
    cands = [(r["query"], "gsc") for r in (gsc.get("striking") or []) + (gsc.get("gaps") or [])]
    # questions borrowed from another market's SERP (the results API has no PAA for this one) rank below this
    # market's own question searches: local demand first, borrowed phrasing second
    borrowed = serp.get("paa_locale") and serp.get("paa_locale") != serp.get("locale")
    local_q = [(p, "paa_autocomplete") for p in serp.get("question_autocomplete", [])]
    if borrowed:
        cands += local_q
    cands += [(p, "paa") for p in serp.get("paa", [])]
    cands += [(p, "paa_dfs") for p in kr.get("paa", [])]
    for x in serp.get("expansions", {}).values():
        cands += [(p, "paa_expanded") for p in x.get("paa", [])]
    if not borrowed:
        cands += local_q
    cands += [(r, "related") for r in serp.get("related", [])]
    for x in serp.get("expansions", {}).values():
        cands += [(r, "related_expanded") for r in x.get("related", [])]
    cands += [(a, "autocomplete") for a in serp.get("autocomplete", [])]
    cands += [(k["keyword"], "keyword") for k in kr.get("keywords", [])[:25] if k.get("keyword")]

    # The subject is the main-query word the searches around it repeat most ("eta" in "uk eta application",
    # "bag" in "how to clean a faux leather bag"), not whatever word happens to come last.
    freq = Counter(w for q, _ in cands for w in content(q) if w in main_content)
    subject = max(main_content, key=lambda w: (freq[w], main_toks.index(w)), default="")

    seen, uniq = [], []
    cands = [(q, s) for q, s in cands if q and q.lower().split()[-1] not in
             {"without", "with", "for", "to", "on", "in", "of", "and", "or", "the", "a", "an", "from", "by", "vs", "at"}]
    for q, src in cands:
        isq = src.startswith("paa") or src == "gsc"
        n = content(q) - MODIFIERS - FILLER
        if isq:  # in a question the number is the point ("Is 100 g too much?"); in a keyword family it isn't
            n |= {w for w in tokens(q, syn) if w.isdigit()}
        # same words, or one question's words all inside another's: one heading answers both. Questions merge with
        # questions and keywords with keywords, because a keyword variant carries its own routing. Questions that
        # share two content words and half their words ask the same thing ("Is 2 cups a day enough?" /
        # "Is 2 cups … too much?" / "How many cups a day…").
        if not n or any(sq == isq and (len(n & s) / len(n | s) >= 0.75 or
                                        (isq and len(n & s) >= 2 and len(n & s) / len(n | s) >= 0.5) or
                                        (isq and len(n) >= 3 and len(s) >= 3 and (n <= s or s <= n)))
                        for s, sq in seen):
            continue
        seen.append((n, isq))
        uniq.append((q, src))

    pages = [(c["url"], c.get("name", "")) for c in lm.get("children", [])] + [(u, "") for u in lm.get("internal", [])]
    # a client page can only answer a query whose new terms its slug or name carries (the match below needs every
    # term): pages sharing no 4-letter stem with any candidate query are left out before the tagger runs
    stems = {w[:4] for q in [main] + [q for q, _ in cands] for w in re.findall(r"[a-z]{3,}", q.lower())}
    pages = [(u, n) for u, n in pages
             if any(x[:4] in stems for x in re.findall(r"[a-z0-9]{3,}", (urlparse(u).path.split("/")[-1] + " " + n).lower()))]
    from seolib.nlp import prime
    prime([urlparse(u).path.split("/")[-1].replace("-", " ") for u, _ in pages] + [n for _, n in pages]
          + [q for q, _ in cands] + [h for pg in (ctx.load("competitor_scrape") or {}).get("pages", []) for _, h in pg.get("outline", [])], syn)
    comp = ctx.load("competitor_scrape") or {}
    head_sets = [content(h) - MODIFIERS for pg in comp.get("pages", []) for _, h in pg.get("outline", [])]
    # SERP-overlap checks (one paid search per question, up to 12) are off under the 3-credit cap: whether a
    # question shares the page is decided from the top 10 pages' own headings (head_sets) below
    overlaps: dict = {}

    def jac(a, b):
        x, y = content(a) - MODIFIERS - FILLER, content(b) - MODIFIERS - FILLER
        return len(x & y) / len(x | y) if x | y else 0

    def near(q, measured):
        return [x for x in measured if jac(q, x) >= 0.6 or shape(x) == shape(q)]

    def cluster_overlap(q, measured):
        # "cups a day" and "cups per day" are one search: the same SERP evidence decides both, so they can't split
        group = ([q] if q in measured else []) + near(q, measured)
        return max(measured[x] for x in group)

    # other brands in the results: a question about one of them ("Is <brand> a …?") is not a section on the client's page
    client_root = (ctx.brief.get("domain") or "").replace("www.", "").split(".")[0].lower()
    brands = set()
    for o in serp.get("organic", []):
        if o.get("kind") not in ("business_site", "ecommerce", "help_centre"):
            continue
        root = (o.get("domain") or "").lower().removeprefix("www.").split(".")[0]
        if len(root) > 3 and root != client_root and root not in main_toks:
            brands.add(root)
    out, h2 = [], []
    cap = 8 if ctx.deep() else 5
    # another market's questions leak into a SERP (a UK search showing "$100,000" or a US radio host): a question in
    # another currency, or naming someone or something no ranking page for this market mentions, isn't this reader's
    region = (ctx.brief.get("locale") or "en").partition("-")[2].lower() or ""
    home_cur = {"gb": "£", "uk": "£", "us": "$", "ca": "$", "au": "$", "nz": "$", "ie": "€", "de": "€", "fr": "€",
                "es": "€", "it": "€", "nl": "€", "ae": "aed", "in": "₹"}.get(region, "")
    foreign_cur = [c for c in ("$", "£", "€", "₹") if c != home_cur and home_cur]
    corpus = " ".join(x for pg in comp.get("pages", []) for _, x in pg.get("blocks", [])).lower()
    corpus += " " + " ".join(str(f.get("value", "")) for f in (ctx.load("foundation") or {}).get("facts", []) or []).lower()
    client_name = (ctx.brief.get("client") or "").lower()
    CTA = re.compile(r"(?i)^(ready to|want to|looking (for|to)|need (a|an|help|finance)|why choose|get started|"
                     r"how can we help|contact|call us|speak to|is (a|an|this) .{3,60} right for you|interested in)"
                     r"|\b(with us|from us|our (team|experts|product|service|isa|account|app))\b")

    home_tld = {"gb": ".uk", "uk": ".uk", "au": ".au", "ie": ".ie", "ca": ".ca", "nz": ".nz", "de": ".de", "fr": ".fr",
                "es": ".es", "it": ".it", "nl": ".nl", "in": ".in", "ae": ".ae"}.get(region)
    name_home = {}

    def home_market(name):
        """Whose market is this person or brand? Google, searched in this locale, answers: mostly this country's
        sites (".uk" for the UK) means a local name (Martin Lewis); mostly elsewhere means another market's (Dave
        Ramsey). Free under the 3-credit cap: a name this market's own top 10 pages mention is local; one they
        never mention is another market's (its question isn't page-one demand here either)."""
        if region == "us":
            return True
        if name not in name_home:
            name_home[name] = name.lower() in corpus
        return name_home[name]

    def foreign(q):
        if any(c in q for c in foreign_cur) or (home_cur != "$" and re.search(r"\bdollars?\b", q, re.I)):
            return "another market's currency"
        # "how to grow tomatoes in pots nz" on a UK page: another country's version of the question
        home_geo = "geo:" + ("gb" if region in ("gb", "uk") else region)
        away = places(q) - {home_geo, "geo:eu"} - main_places
        if away:
            return "about another country (" + ", ".join(sorted(x[4:].upper() for x in away)) + ")"
        for name in re.findall(r"\b([A-Z][a-z]+(?:\s+(?:of\s+)?[A-Z][a-z]+)+)", q):
            n = name.lower()
            if n in corpus or n in client_name or n in main.lower() or re.match(r"(?i)(what|how|why|when|which|who|can|is|are|do|does)\b", name):
                continue
            if not home_market(name):
                return f"names {name}, who belongs to another market's results"
        return ""
    for q, src in uniq:
        d = distinct(q)
        rec = {"query": q, "source": src, "distinct_terms": d}
        if vol.get(q.lower()) is not None:
            rec["search_volume"] = vol[q.lower()]
        g = impr.get(q.lower())
        if g:
            rec["gsc"] = {"impressions": g["impressions"], "clicks": g["clicks"], "position": g["position"]}
        qt = set(toks(q))
        why = foreign(q) if src != "gsc" else ""
        if why:
            rec.update(decision="drop", reason=f"another market's question ({why})")
            out.append(rec)
            continue
        if re.search(r"\bnear (me|you)\b|\bnearby\b|\bopen now\b", q.lower()) and ctx.brief.get("page_type") != "service":
            rec.update(decision="drop", reason="a local search (\"near me\"): answered by maps and listings, not this page")
            out.append(rec)
            continue
        named = sorted(b for b in brands if b in qt or b in re.sub(r"[^a-z0-9]", "", q.lower()))
        if named and src != "gsc":
            rec.update(decision="cover_in_section", reason=f"about another brand ({', '.join(named)}): mention it where a "
                                                           "comparison helps, never as a section on the client's page")
            out.append(rec)
            continue
        if src == "gsc":
            better = [c for c in cannibal.get(q, []) if g and c["position"] < g["position"]]
            if better:
                rec.update(decision="existing_page", url=better[0]["page"],
                           reason=f"another client page ranks better for it (position {better[0]['position']}); link it")
            elif re.match(r"(how|what|why|which|where|when|who|can|should|do|does|is|are)\b", q.lower()) and len(h2) < cap:
                rec.update(decision="h2", reason="the page already shows for this question in Search Console: answer it as an H2")
                h2.append(q)
            else:
                rec.update(decision="cover_in_section",
                           reason="the page already shows for it in Search Console: use its words where they fit")
            out.append(rec)
            continue
        topic = {w for w in main_content if not w.startswith("geo:")}
        if src.startswith("paa") and topic and not (qt & topic) and not any(same_stem(w, t) for w in qt for t in topic):
            # Google's PAA box drifts with the query's place words ("…in the UK" → "UK vs Great Britain"): a question
            # that never mentions the topic is not this page's question
            rec.update(decision="drop", reason=f"never mentions the topic ({', '.join(sorted(topic))}): a drifted question")
            out.append(rec)
            continue
        if main_content and len(qt & main_content) / len(main_content) < 0.34 and not src.startswith("paa") \
                and src != "keyword":
            rec.update(decision="drop", reason="shares too little with the main query to belong to this topic")
            out.append(rec)
            continue
        new_places = {w for w in qt if w.startswith("geo:")} - main_places
        if new_places and subject and subject not in qt:
            rec.update(decision="drop", reason=f"about another place ({', '.join(sorted(p[4:] for p in new_places))}) "
                                               f"and not about the {subject}: a different topic")
            out.append(rec)
            continue
        if new_places and main_places:
            # the page names its places ("… for uk citizens"); a question for another place has a different reader
            rec.update(decision="drop", reason=f"asks about {', '.join(sorted(p[4:] for p in new_places))}; this page is "
                                               f"for {', '.join(sorted(p[4:] for p in main_places))}")
            out.append(rec)
            continue
        qc = content(q) - MODIFIERS - FILLER
        drift = qc - main_content - {subject}
        if src in ("paa_expanded", "related_expanded") and drift and head_sets and \
                not (qt & (main_content - {subject})) and not any(drift & h and subject in h for h in head_sets):
            rec.update(decision="drop", reason="a second-hop question that drifts from the topic: it shares only the "
                                               f"subject (\"{subject}\") with the query and no top page covers it")
            out.append(rec)
            continue
        if src.startswith("paa") and qc and main_content and qc <= main_content:
            rec.update(decision="cover_in_section", reason="restates the main query; the page as a whole answers it")
            out.append(rec)
            continue
        match = None
        if d:
            task = main_content - {subject} - set(d)
            for u, name in pages:
                slug = set(toks(urlparse(u).path.split("/")[-1].replace("-", " ")) + toks(name))
                # the page must cover the new terms AND the task: a "handbag styles" page doesn't answer
                # "how to clean a handbag"
                extra = {x for x in slug if x not in main_toks and x not in STOP and x not in MODIFIERS and
                         not any(same_stem(x, t) or x == t for t in d)}
                # ... and be about little else: "asana-vs-monday-do-they-work-as-crm-systems" is not "how does it work"
                if slug and all(any(same_stem(t, x) or t == x for x in slug) for t in d) and len(extra) <= 1 and \
                        (not task or any(any(same_stem(w, x) or w == x for x in slug) for w in task)):
                    match = u
                    break
        if src.startswith("paa") or (src == "keyword" and re.match(r"(how|what|why|which|can|is|are|do|does)\b", q.lower())):
            if match and ctx.brief.get("page_type") == "hub":
                rec.update(decision="existing_page", url=match, reason="a child page already answers this; link it")
            elif len(h2) < cap:
                rec.update(decision="h2", reason="People Also Ask: answer it as its own H2" if src != "paa_autocomplete"
                           else "real question search (autocomplete; no PAA box): answer it as its own H2")
                h2.append(q)
            else:
                rec.update(decision="cover_in_section", reason=f"more than {cap} PAA questions; fold into the closest H2")
        elif match:
            rec.update(decision="existing_page", url=match,
                       reason="the client already has a page for this; link it instead of duplicating it")
        elif not d:
            rec.update(decision="cover_in_section", reason="same intent as the main query (no distinct terms)")
        elif q in overlaps or any(shape(q) == shape(x) for x in overlaps) or near(q, overlaps):
            ov = cluster_overlap(q, overlaps)
            rec["serp_overlap"] = ov
            if ov >= 3:
                rec.update(decision="cover_in_section", reason=f"{ov} of the top 10 results are shared with the main query: same page")
            else:
                rec.update(decision="separate_page", reason=f"only {ov} shared top-10 results: Google treats it as a different topic")
        else:
            rec.update(decision="separate_page" if len(d) >= 2 else "cover_in_section",
                       reason="distinct entity or modifier (heuristic; no overlap check in this mode)")
        out.append(rec)
    # The questions ranking pages ask under their own headings are search demand seen from the results: the ones two
    # or more of them share belong on this page too, whether or not Google showed a People Also Ask box.
    shared = []
    if comp.get("pages"):
        qheads = {}
        for pg in comp["pages"]:
            own_brand = (pg.get("domain") or "").lower().removeprefix("www.").split(".")[0]
            lines = [h for _, h in pg.get("outline", [])]
            # FAQ lists and accordions: short question lines in the body are questions the page answers too
            lines += [x for t_, x in pg.get("blocks", []) if t_ in ("p", "li", "dt", "h4") and len(x.split()) <= 16]
            for h in lines:
                hs = re.sub(r"\s+", " ", h).strip()
                if not (hs.endswith("?") and 3 <= len(hs.split()) <= 14):
                    continue
                flat = re.sub(r"[^a-z0-9]", "", hs.lower())
                if (own_brand and len(own_brand) > 3 and own_brand in flat) or \
                        any(b in flat for b in brands if len(b) > 3) or CTA.search(hs) or foreign(hs):
                    continue  # "Why choose Commercial Trust?" is a sales pitch, not a reader's question
                qheads.setdefault(pg["domain"], []).append(hs)
        def own(q):  # a question's own words: the topic ("bridging loan") is in all of them and says nothing
            return {w for w in content(q) - MODIFIERS - FILLER
                    if w not in main_content and not any(same_stem(w, t) for t in main_content)}
        pool = []
        for dom, hs in qheads.items():
            for h in hs:
                n = own(h)
                if not n:
                    continue  # "What is a bridging loan?" is the page itself
                for other in pool:
                    if len(n & other["n"]) / len(n | other["n"]) >= 0.5:
                        other["domains"].add(dom)
                        break
                else:
                    pool.append({"q": h, "n": n, "domains": {dom}})
        shared = sorted((p for p in pool if len(p["domains"]) >= 2), key=lambda p: -len(p["domains"]))

        def covered(n):  # already one of this page's questions
            return any(r["decision"] in ("h2", "cover_in_section") and own(r["query"]) and
                       len(n & own(r["query"])) / len(n | own(r["query"])) >= 0.5 for r in out)
        for p in shared:
            if covered(p["n"]):
                continue
            top = len(h2) < cap
            out.append({"query": p["q"], "source": "top_page_headings", "distinct_terms": distinct(p["q"]),
                        "decision": "h2" if top else "cover_in_section",
                        "reason": f"asked under a heading by {len(p['domains'])} ranking pages"
                                  + ("" if top else f"; more than {cap} H2 questions, so answer it inside the closest one")})
            if top:
                h2.append(p["q"])
    # "Separate page" means "don't build this page around it", not "leave it out": when ranking guides answer the
    # same question inside their own pages (rates, alternatives, bad credit), this page gives a short answer too,
    # and links the deeper page when the client has one.
    def in_heading(dt, h):  # most of the query's own terms appear in one ranking page's heading
        hit = {t for t in dt if any(t == w or same_stem(t, w) for w in h)}
        return len(hit) / len(dt) >= 0.5
    for r in out:
        if r["decision"] != "separate_page" or not r["distinct_terms"]:
            continue
        dt = set(r["distinct_terms"])
        if any(in_heading(dt, h) for h in head_sets if h):
            r.update(decision="cover_in_section", reason="ranking guides answer it inside their own pages: give it a "
                                                         "short answer here (a sentence or a short section), and link a "
                                                         "deeper client page if there is one")
    # A question that carries a separate page's distinguishing terms belongs on that page too.
    seps = [set(r["distinct_terms"]) for r in out if r["decision"] == "separate_page" and r["distinct_terms"]]
    for r in out:
        if r["decision"] == "h2" and any(s and s <= set(r["distinct_terms"]) for s in seps):
            r.update(decision="separate_page", reason="shares the distinguishing terms of a query that deserves its own page")
            h2.remove(r["query"])
    counts = Counter(r["decision"] for r in out)
    decisions = [f"\"{r['query']}\" deserves its own page ({r['reason']}); not written here."
                 for r in out if r["decision"] == "separate_page"][:6]
    return {"queries": out, "h2_questions": h2, "counts": dict(counts), "decisions": decisions, "subject": subject,
            "summary": ", ".join(f"{k} {v}" for k, v in counts.items()) + f"; subject \"{subject}\""}
