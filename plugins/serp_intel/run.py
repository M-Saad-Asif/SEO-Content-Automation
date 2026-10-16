"""SERP intelligence: what Google already rewards for this keyword in this country."""
import re
from collections import Counter

from seolib import common as C
from seolib import serper
from seolib.domains import domain, kind, page_shape

INTENT_TERMS = {
    "transactional": r"\b(buy|price|prices|cheap|deal|deals|order|shop|sale|discount|cost)\b",
    "commercial": r"\b(best|top|vs|versus|review|reviews|compare|comparison|alternatives?)\b",
    "informational": r"\b(how|what|why|when|where|guide|meaning|explained|does|can|tips)\b",
    "navigational": r"\b(login|log in|sign in|official|website|portal|contact|account)\b",
    "local": r"\b(near me|nearby|opening hours|directions)\b",
}


def classify(q, organic, features):
    score = Counter()
    ev = []
    for intent, pat in INTENT_TERMS.items():
        if re.search(pat, q.lower()):
            score[intent] += 2
            ev.append(f"query wording suggests {intent}")
    shapes = Counter(o["shape"] for o in organic)
    kinds = Counter(o["kind"] for o in organic)
    for shape, n in shapes.items():
        if shape == "product_listing":
            score["transactional"] += n
        elif shape in ("listicle", "comparison_review"):
            score["commercial"] += n
        elif shape in ("guide", "article", "discussion", "video"):
            score["informational"] += n
        elif shape == "tool_or_service":
            score["navigational"] += n * 0.7
            score["informational"] += n * 0.3
    if kinds.get("government", 0) >= 3:
        score["navigational"] += 2
        ev.append(f"{kinds['government']} government pages rank: strong official-source/navigation signal; the page's offer and purpose still come from the brief and client")
    if features.get("places"):
        score["local"] += 4
        ev.append("local pack shown")
    if features.get("shopping"):
        score["transactional"] += 3
        ev.append("shopping results shown")
    ranked = score.most_common()
    primary = ranked[0][0] if ranked else "informational"
    secondary = ranked[1][0] if len(ranked) > 1 and ranked[1][1] >= 0.5 * ranked[0][1] else None
    total = sum(score.values()) or 1
    ev.append("result shapes: " + ", ".join(f"{k} {v}" for k, v in shapes.most_common()))
    return {"primary": primary, "secondary": secondary,
            "confidence": round(ranked[0][1] / total, 2) if ranked else 0,
            "scores": {k: round(v, 1) for k, v in score.items()}, "evidence": ev}, shapes, kinds


# Units and money that mark a question as written for another country's readers (when PAA had to be borrowed)
US_MARKS = re.compile(r"\$|\bdollars?\b|\bcents?\b|\bpenn(y|ies)\b|\b\d+/\d+\b|°\s?f\b|fahrenheit|\bfl\.? ?oz\b|"
                      r"\bounces?\b|\boz\b|\blbs?\b|(?<!£)\b\d+\s?(-| )?pounds?\b|"
                      r"\b(irs|medicare|medicaid|401k|social security|zip code|dmv)\b|\bzones? \d{1,2}[ab]?\b|"
                      r"\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|"
                      r"hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|"
                      r"michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|"
                      r"new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|"
                      r"south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington state|"
                      r"west virginia|wisconsin|wyoming|ny|nj|ct|nyc|socal|norcal|midwest)\b", re.I)


def foreign(q, locale):
    """True when a borrowed question assumes another country: its units, money, institutions or places."""
    from seolib.nlp import places
    region = (locale.partition("-")[2] or "").lower()
    if region != "us" and US_MARKS.search(q):
        return True
    return region != "us" and "geo:us" in places(q)  # borrowed from the US SERP: only US-specific ones are off


# How each language starts a question (for question autocomplete and for telling questions from keywords)
QUESTION_WORDS = {
    "en": ["how", "what", "can", "why", "is", "does", "which", "when", "should", "are", "do", "where", "who", "will"],
    "de": ["wie", "was", "warum", "kann", "ist", "welche", "wann", "wo", "muss", "sind"],
    "fr": ["comment", "quel", "pourquoi", "combien", "est-ce", "peut-on", "quelle", "quand", "où", "faut-il"],
    "es": ["cómo", "qué", "cuánto", "por qué", "puedo", "cuál", "cuándo", "dónde", "es", "se puede"],
    "it": ["come", "cosa", "quanto", "perché", "posso", "quale", "quando", "dove", "si può", "è"],
    "nl": ["hoe", "wat", "waarom", "kan", "is", "welke", "wanneer", "waar", "moet", "zijn"],
    "pt": ["como", "o que", "quanto", "por que", "posso", "qual", "quando", "onde", "é", "pode"],
}

# Your-Money-or-Your-Life topics (Google Search Quality Rater Guidelines): financial security, health and safety,
# legal standing, civic matters. Words that put a query in that territory in any niche.
YMYL_TOPIC = re.compile(
    r"\b(invest\w*|isas?|pensions?|retire\w*|tax(es|ed)?|mortgages?|loans?|credit|debt|insurance|savings?|bank\w*|"
    r"stocks?|shares|funds?|crypto\w*|interest rates?|inflation|benefits?|allowance|inheritance|"
    r"symptoms?|diseases?|medic\w*|dosage|dose|pregnan\w*|vaccin\w*|treatment|diagnos\w*|mental health|"
    r"legal\w*|law|laws|lawyer|solicitor|visas?|immigration|tenan\w*|landlord|contract|divorce|"
    r"safety|carbon monoxide|gas safe|electrical|fire risk)\b")


def run(ctx):
    b = ctx.brief
    q = b["target_query"]
    from seolib import spider, suggest
    # one paid search: the top 10, People Also Ask, related searches and the answer box come back together;
    # autocomplete is Google's free suggestion service (seolib/suggest.py), never a paid call
    if spider.provider() == "spider":
        main = spider.search(q, b["locale"])
    else:
        got, cr = serper.batch([("search", q)], b["locale"])
        ctx.credits += cr
        main = got[("search", q)]
    first = {("search", q): main, ("autocomplete", q): suggest.as_serper(suggest.many([q], b["locale"]).get(q, []))}
    main = first[("search", q)]
    if main.get("error"):
        return {"error": main["error"]}
    if main.get("_gl_ignored"):
        ctx.decide(f"WARNING: Serper ignored the country code \"{main['_gl_ignored']}\": these results are for "
                   "another country (Google's default). Check the locale in the brief.")
    organic = []
    for o in main.get("organic", [])[:10]:
        link = o.get("link", "")
        organic.append({"position": o.get("position"), "link": link, "title": o.get("title"),
                        "snippet": o.get("snippet"), "date": o.get("date"), "kind": kind(link),
                        "shape": page_shape(link, o.get("title", "")), "domain": domain(link)})
    paa = [p.get("question") for p in main.get("peopleAlsoAsk", []) if p.get("question")]
    paa_answers = {p.get("question"): {"snippet": p.get("snippet"), "link": p.get("link")}
                   for p in main.get("peopleAlsoAsk", [])}
    related = [r.get("query") for r in main.get("relatedSearches", []) if r.get("query")]
    auto = [s.get("value") for s in first[("autocomplete", q)].get("suggestions", [])
            if s.get("value") and s.get("value").lower() != q.lower()]
    features = {k: bool(main.get(k)) for k in ("answerBox", "knowledgeGraph", "topStories", "images", "videos",
                                                 "places", "shopping", "peopleAlsoAsk", "relatedSearches")}
    decisions = []
    paa_locale = b["locale"]
    lang = b["locale"].split("-")[0].lower()
    if not paa and not related and lang == "en" and not b["locale"].lower().endswith("-us"):
        # The results API returns PAA and related searches only for some countries (UK and US). The questions people
        # ask are language-level, so borrow them from the closest English market that has them (UK English for the
        # Commonwealth, then US); organic results stay local. Other languages never borrow English questions: their
        # local autocomplete questions below are the question data.
        um = {}
        for borrow in (["en-GB"] if not b["locale"].lower().endswith("-gb") else ["en-US"]):  # one search (3-credit cap)
            got, cr = serper.batch([("search", q)], borrow)
            ctx.credits += cr
            um = got[("search", q)]
            if um.get("peopleAlsoAsk") or um.get("relatedSearches"):
                break
        paa = [p.get("question") for p in um.get("peopleAlsoAsk", []) if p.get("question")]
        paa_answers = {p.get("question"): {"snippet": p.get("snippet"), "link": p.get("link")}
                       for p in um.get("peopleAlsoAsk", [])}
        related = [r.get("query") for r in um.get("relatedSearches", []) if r.get("query")]
        if paa or related:
            paa_locale = borrow
            n0 = len(paa) + len(related)
            paa = [x for x in paa if not foreign(x, b["locale"])]
            related = [x for x in related if not foreign(x, b["locale"])]
            if n0 > len(paa) + len(related):
                decisions.append(f"Dropped {n0 - len(paa) - len(related)} borrowed {borrow} question(s) that assume another "
                                 "country's units, money or places.")
            decisions.append(f"The results API gives no People Also Ask or related searches for {b['locale']}; "
                             f"{len(paa)} PAA questions and {len(related)} related searches come from the {borrow} SERP "
                             "(answer them for this locale), alongside this market's own autocomplete questions.")
    if not paa:
        decisions.append(f"Google shows no People Also Ask box for \"{q}\" in {b['locale']}; questions come from "
                         "the PAA boxes of the closest autocomplete variants instead.")
    # One search follows People Also Ask one level down (or the closest autocomplete variant when the main SERP has
    # none), unless the questions were already borrowed from another market's SERP. Most PAA questions are covered
    # by the top 10 pages, which are read in full; the 3-credit cap (seolib/serper.py) keeps the rest for the
    # official sources.
    # One paid search follows People Also Ask one level down (or the closest autocomplete variant when there is no
    # PAA): measured on "how to unblock a sink", it brought 4 deeper questions, 8 related searches and the source
    # pages for about 8 planned headings the first page alone didn't give.
    exp_queries = []
    if ctx.deep() and paa_locale == b["locale"]:
        exp_queries = paa[:1] if paa else [a for a in auto if len(a.split()) >= len(q.split())][:1]
    expansions = {}
    if exp_queries:
        more, cr = serper.batch([("search", e) for e in exp_queries], paa_locale)
        ctx.credits += cr
        for (_, e), r in more.items():
            expansions[e] = {"source": "paa" if e in paa else "related" if e in related else "autocomplete",
                             "locale": paa_locale,
                             "paa": [p.get("question") for p in r.get("peopleAlsoAsk", []) if p.get("question")
                                     and not (paa_locale != b["locale"] and foreign(p.get("question"), b["locale"]))],
                             "related": [x.get("query") for x in r.get("relatedSearches", []) if x.get("query")
                                         and not (paa_locale != b["locale"] and foreign(x.get("query"), b["locale"]))],
                             "organic": [o.get("link") for o in r.get("organic", [])[:10]]}
            for p in r.get("peopleAlsoAsk", []):
                paa_answers.setdefault(p.get("question"), {"snippet": p.get("snippet"), "link": p.get("link")})
    # PAA answers are not looked up one by one any more (8 paid searches a run): the top 10 pages, read in full,
    # and the information-gain researchers answer them; Google's own PAA snippets are kept where Serper gives them.
    # The questions people type in this market, in its language (question-prefixed autocomplete, as AnswerThePublic
    # does): always in deep mode, because they are local search demand in every country, PAA box or not.
    question_ac = []
    no_paa = not paa and not any(v["paa"] for v in expansions.values())
    if ctx.deep() or no_paa:
        words = QUESTION_WORDS.get(lang, QUESTION_WORDS["en"])
        prefixes = words[:6] if ctx.deep() else words[:2]
        qs = suggest.many([f"{pre} {q}" for pre in prefixes], b["locale"])  # free
        qrx = re.compile(r"(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
        for _pq, sugg in qs.items():
            for v in sugg:
                v = (v or "").strip()
                if v and len(v.split()) >= 4 and v not in question_ac and qrx.match(v) and not foreign(v, b["locale"]):
                    question_ac.append(v)
        question_ac = question_ac[:20]
        if question_ac:
            decisions.append(f"{len(question_ac)} real question searches from {b['locale']} autocomplete"
                             + (" stand in for People Also Ask." if no_paa else " add to People Also Ask."))
    intent, shapes, kinds = classify(q, organic, features)
    # YMYL "auto": when Google ranks two or more authorities (government, education, international bodies, public
    # health services) for the query, the topic is one where mistakes cost readers money, health or legal standing.
    authorities = sum(1 for o in organic if o["kind"] in ("government", "education", "international"))
    # ...and by topic, as Google's rater guidelines define YMYL: money, health, legal standing, safety. A finance
    # SERP is often all providers and publishers, with no government page in the top 10, and is still YMYL.
    topic_text = " ".join([q] + [o.get("title", "") for o in organic[:10]]).lower()
    topic = [m.group(0) for m in YMYL_TOPIC.finditer(topic_text)]
    if b.get("ymyl") in (None, "auto"):
        b["ymyl"] = authorities >= 2 or len(set(topic)) >= 2 or bool(YMYL_TOPIC.search(q.lower()))
        basis = f"{authorities} authority result(s) in the top 10" + (f"; YMYL topic words: {', '.join(sorted(set(topic))[:6])}"
                                                                      if topic else "")
        decisions.append(f"YMYL {'on' if b['ymyl'] else 'off'}: {basis} (the stricter accuracy rules apply when on).")
        with C.file_lock(ctx.rd / "fact_sheet.json"):
            sheet = C.load_json(ctx.rd / "fact_sheet.json") or {}
            if sheet.get("brief") is not None:
                sheet["brief"]["ymyl"] = b["ymyl"]
                sheet["brief"]["ymyl_basis"] = f"auto: {basis}"
                C.save_json(ctx.rd / "fact_sheet.json", sheet)
    fmt = shapes.most_common(1)[0][0] if shapes else "article"
    comp = {
        "by_kind": dict(kinds),
        "forums_ugc_rank": [o["position"] for o in organic if o["kind"] == "forum_ugc"],
        "government_rank": [o["position"] for o in organic if o["kind"] == "government"],
        "video_or_image_rank": [o["position"] for o in organic if o["kind"] in ("video", "image")],
        "notes": [],
    }
    if kinds.get("forum_ugc", 0) >= 2:
        comp["notes"].append("Forums rank: Google rewards first-hand experience here. The strongest is the client's own "
                             "(its guides, data, staff know-how); a quoted forum comment from the reader's country is second.")
    if kinds.get("government", 0) >= 3:
        comp["notes"].append("Official sources dominate: verify rules, fees, conditions and mandatory actions against them. "
                             "Keep the brief's page purpose and scoped client offer; official-source prevalence does not "
                             "turn a commercial page into an official-service guide. Add useful verified context and avoid repeated competing CTAs.")
    if kinds.get("video", 0) >= 2:
        comp["notes"].append("Video ranks: people want to see the steps. Use numbered, screen-by-screen steps.")
    if kinds.get("marketplace", 0) + kinds.get("ecommerce", 0) >= 4:
        comp["notes"].append("Product listings dominate: lead with products and specs, not long prose.")
    if re.match(r"(best|top)\b", q.lower()) and shapes.get("listicle", 0) + shapes.get("comparison_review", 0) >= 4 \
            and (b.get("platform") == "shopify" or b.get("page_type") == "product-guide"):
        comp["notes"].append("Independent cross-brand roundups rank for this \"best\" query. A retailer page that only lists "
                             "its own range will trail them unless it says so plainly and adds first-hand testing (put "
                             "fit or weight tests in client_facts); a collection-style intent may rank better.")
    if kinds.get("major_publisher", 0) + kinds.get("reference", 0) >= 4:
        comp["notes"].append("High-authority publishers dominate: win on specificity and unique data, not breadth.")
    exp_paa = sum(len(v["paa"]) for v in expansions.values())
    return {
        "ymyl": b.get("ymyl") is True, "authority_results": authorities,
        "query": q, "locale": b["locale"], "paa_locale": paa_locale, "organic": organic, "paa": paa, "paa_answers": paa_answers,
        "related": related, "autocomplete": auto, "question_autocomplete": question_ac[:12],
        "expansions": expansions, "features": features,
        "intent": intent, "format": {"dominant": fmt, "counts": dict(shapes)}, "composition": comp,
        "decisions": decisions,
        "summary": f"intent {intent['primary']}{'/' + intent['secondary'] if intent['secondary'] else ''}, "
                   f"format {fmt}, PAA {len(paa)}+{exp_paa} expanded, question searches {len(question_ac)}, "
                   f"related {len(related)}, autocomplete {len(auto)}",
    }
