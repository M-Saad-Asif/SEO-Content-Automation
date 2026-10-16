"""The page plan: every heading the page will have, decided by script before anyone writes.

Nothing a top-10 page covers is left out: every shared section, every section only one ranking page has, every
People Also Ask question, related question and competitor question becomes a heading (H2, or H3 under the H2 it
belongs to), merged with the headings that say the same thing. A searcher question that deserves its own heading
gets one; variants of the main query ("how long does water based fence paint take to dry") become one comparison
block instead of a heading each. Commercial page types get the client's own sections (how the client does it, its
next step). Each heading carries the facts and internal links it uses and a word budget, and the plan is split into
parts that writers can draft at the same time.

Writing from a finished plan is what makes the single write fast: the writer no longer sorts 60 coverage items,
and the check after the write is exact (each planned heading is on the page or it isn't).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C

STOP = set("a an the and or of to in on for with by from at as is are be your my our their its this that these those "
           "how what why when where which who can do does you i it much many should would could will there here if "
           "about into than then so not no get".split())
QWORD = re.compile(r"^(how|what|why|when|where|which|who|can|could|should|would|will|do|does|did|is|are|was|were|"
                   r"has|have|may|might|must)\b", re.I)
COMMERCIAL = {"service", "product", "category", "location", "home", "company"}
# A ranking page's furniture, not its topic: never a heading on ours ("Special offers", "Recent posts", "Related
# sinks & taps articles" came through from the competitor outlines on "how to unblock a sink")
BOILER = re.compile(
    r"(?i)^(special offers?|offers?|deals?|sale|recent (posts|articles)|latest (news|posts|articles)|popular posts|"
    r"related (\w+\s*(&|and)?\s*)*(articles|posts|guides|products|reading|content)|you (may|might) also like|"
    r"more (articles|guides|posts|from)|read more|further reading|share (this|on)|follow us|subscribe|newsletter|"
    r"sign up|contact( us)?|get in touch|about (us|the author)|author|comments?|leave a (reply|comment)|reviews?|"
    r"testimonials?|categories|tags|archives?|table of contents|contents|in this (article|guide|post)|"
    r"related searches|people also ask|shop (now|the range|all)|our (services|products|range)|why choose us|"
    r"disclaimer|sources|references|faqs?|frequently asked questions|video|watch( the video)?|summary|conclusion|"
    r"introduction|overview|final thoughts|key takeaways|good to know|need (some )?help|for example|"
    r"already started an application|more information|useful links|let'?s take a closer look|"
    r"important( \w+)? information|(\w+ )?tools and resources|applies to (england|scotland|wales|"
    r"northern ireland|the uk))\b")
# A form's label, not a section: an empty slot where the tool puts a number ("…an hourly wage of £ and hours per
# week"), or the form talking to the user ("I want to see…", "Which of the below…")
PLACEHOLDER = re.compile(r"(?i)[£$€₹]\s+(and|or|per|for|\W|$)|\bof £?\s*and\b|^i want to\b|\bof the below\b|"
                         r"\bbest describes\b|^are you a\b")


# Headings that sell, invite or label a form, not a topic: "See how compound interest can make your savings glow",
# "Discover more savings tools", "Your savings details"
PITCH = re.compile(r"(?i)^(see how|discover|explore|find out|check out|learn more|try|start (your|now)|get (your|a free|"
                   r"started)|why choose|join|sign up|subscribe)\b|^your [\w\s]{2,25}$")


def menu_or_pitch(title: str, depth) -> bool:
    """A competitor heading that is a link in its menu (no prose under it on its page) or a sales line."""
    if PITCH.search((title or "").strip()):
        return True
    n = text_under(depth, title)
    return n is not None and n < 25


def boiler(title: str) -> bool:
    """The whole heading is furniture ("Reviews" is; "Reviews of drain unblockers" is a topic)."""
    s = (title or "").strip(" :?!.-–—")
    m = BOILER.match(s)
    return bool(m and m.end() == len(s))


def words(s: str) -> set[str]:
    from .nlp import tokens
    return {w for w in tokens(s or "") if w not in STOP and len(w) > 1 and not w.isdigit()}


def jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


ACRONYMS = {w.lower(): w for w in ("UK", "US", "USA", "EU", "UAE", "ISA", "ISAs", "LISA", "APR", "AER", "LTV", "SDLT",
                                       "LBTT", "LTT", "HMRC", "NHS", "VAT", "PAYE", "BMI", "IRS", "CRA", "RRSP", "TFSA",
                                       "GDP", "RPI", "CPI", "ERC", "ERCs", "FCA", "PDF", "GBP", "USD", "EUR", "BTL")}
# the same thing named three ways in search phrases: one word for the duplicate check
SAME_WORD = {"house": "home", "property": "home", "flat": "home", "homes": "home", "properties": "home"}


def sentence_case(h: str) -> str:
    """"How Long To Wait Before Painting" -> "How long to wait before painting"; acronyms and names stay."""
    h = re.sub(r"^\W+|\s+", " ", h or "").strip(" -–—:|")
    out = []
    for i, w in enumerate(h.split()):
        parts = w.split("-")
        for j, x in enumerate(parts):
            if (i or j) and x[:1].isupper() and not x.isupper() and len(x) > 1 and not re.search(r"[A-Z]", x[1:]):
                parts[j] = x[0].lower() + x[1:]
            elif (i or j) and x == "A":
                parts[j] = "a"  # "How to get A mortgage"
            if x.lower() == "i":
                parts[j] = "I"  # "Can i get…" from a search phrase
            core = re.sub(r"\W", "", x).lower()
            if core in ACRONYMS:
                parts[j] = x.lower().replace(core, ACRONYMS[core])  # "…mortgage uk" -> "…mortgage UK"
        out.append("-".join(parts))
    s = " ".join(out)
    return s[:1].upper() + s[1:] if s else s


def is_question(q: str) -> bool:
    return q.strip().endswith("?") or bool(QWORD.match(q.strip()))


def is_step(t: str) -> bool:
    """An instruction, not a topic: three or more words starting with a verb ("Seal the overflow", "Clear remaining
    residues with water"); "Wire hanger" and "Hot water" are topics."""
    ws = t.strip().split()
    if len(ws) < 3 or is_question(t):
        return False
    if ws[0].lower() in ("clear", "clean", "empty", "dry", "open", "close", "warm", "level", "smooth", "free", "loosen",
                         "tighten", "flush", "rinse", "repeat", "test"):
        return True  # instruction verbs a tagger reads as adjectives or nouns
    try:
        from .nlp import _nlp
        nlp = _nlp()
        own = nlp(t)[0].tag_
        # a line-initial imperative is often tagged as a noun ("Plunge the sink"); an adjective never is a step
        return own in ("VB", "VBP") or (own in ("NN", "NNP") and nlp(f"you {ws[0].lower()} it")[1].tag_ in ("VB", "VBP"))
    except Exception:
        return False


def build(rd: Path) -> dict:
    rd = Path(rd)
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    b = sheet.get("brief") or {}
    out = C.load_json(rd / "research" / "topic_outline.json") or {}
    qmap = C.load_json(rd / "research" / "query_map.json") or {}
    lm = C.load_json(rd / "link_map.json") or {}
    query = b.get("target_query") or ""
    client = b.get("client") or "the client"
    ptype = b.get("page_type") or "guide"
    main = words(query)
    from .graph import foreign, market_of
    from .market import filter_locale
    home_geo, home_cur = market_of(filter_locale(b))  # no market filter on a global page
    decision = {r["query"].lower(): r.get("decision") for r in qmap.get("queries", [])}

    def own(s):  # a heading's own words: the topic's words are in every heading and say nothing
        return words(s) - main

    # the topic's entities (what the ranking pages are about): a heading only one competitor uses must be built
    # from them, or it is that site's joke or slogan ("What better solution … than some fizzy stuff to drink?")
    kg = C.load_json(rd / "research" / "semantic_graph.json") or {}
    ent_names = [e if isinstance(e, str) else e.get("entity", "") for e in kg.get("must_cover_entities") or []]
    ent_names += [e.get("name") or "" for e in ((kg.get("graph") or {}).get("entities") or [])[:60]]
    ew = set().union(*(words(e) for e in ent_names if e)) | main

    def entity_based(t: str) -> bool:
        from .clientpages import _shared
        w = words(re.sub(r"['’]s\b", " ", t))  # "Plumber's snake": two words, not one
        return bool(w) and len(_shared(w, ew)) / len(w) >= 0.3  # word forms count: "painting" is "paint"

    def opposite(question: str, title: str) -> bool:
        """"…without a plunger?" is not the title for a section on using a plunger."""
        m = re.search(r"(?i)\b(without|instead of|no|not|never|avoid|alternatives? to)\s+(?:an?\s+|the\s+|using\s+)?(\w+)",
                      question)
        return bool(m and m.group(2).lower()[:5] in title.lower() and not re.search(
            rf"(?i)\b{re.escape(m.group(1))}\b", title))

    heads: list[dict] = []  # {"title", "level", "covers": [...], "questions": [...], "kind", "parent"}
    depth = section_depths(C.load_json(rd / "research" / "competitor_scrape.json") or {})

    # rewrite: the live page already ranks. Its own headings come first, in its order, each with its own text as the
    # client's facts (its formula, its worked example, its inputs); page one's sections merge into them below. A
    # rewrite that drops what the page already says loses what ranks.
    cp = C.load_json(rd / "research" / "current_page.json") or {}
    if b.get("task") == "rewrite" and cp.get("exists") and cp.get("blocks"):
        live_facts, cur, n = {}, None, 0
        for tag, text in cp["blocks"]:
            if tag in ("h2", "h3"):
                ht = sentence_case(str(text))
                if boiler(ht) or re.search(r"(?i)\b(questions|faqs?)$", ht) or foreign(ht, home_geo, home_cur) \
                        or PLACEHOLDER.search(ht) or PITCH.search(ht):
                    cur = None  # furniture, or an FAQ block: its answers stay usable, not as a heading
                    continue
                item = {"title": ht, "level": 2, "covers": [], "questions": [], "kind": "live", "sites": 0, "subs": []}
                if tag == "h3" and heads:
                    item["level"] = 3
                    heads[-1]["subs"].append(item)
                else:
                    heads.append(item)
                cur = item
            elif tag in ("p", "li") and len(str(text).split()) >= 6:
                n += 1
                fid = f"live:{n}"
                live_facts[fid] = {"id": fid, "claim": f"{client}'s current page"
                                   + (f", under \"{cur['title']}\"" if cur else ""), "value": str(text),
                                   "status": "verified", "basis": "client_page", "verified": True,
                                   "source_url": b.get("page_url"), "retrieved_at": C.now_iso()}
                if cur is not None:
                    cur.setdefault("live", []).append(fid)
        if live_facts:
            with C.file_lock(rd / "fact_sheet.json"):
                sh = C.load_json(rd / "fact_sheet.json") or {}
                sh["facts"] = [f for f in sh.get("facts", []) if not str(f.get("id", "")).startswith("live:")] \
                    + list(live_facts.values())
                C.save_json(rd / "fact_sheet.json", sh)
            sheet = C.load_json(rd / "fact_sheet.json") or sheet

    def norm_w(s):  # a heading's own words, with one word for the same thing ("house", "property" -> "home")
        return {SAME_WORD.get(w, w) for w in (own(s) or words(s))}

    def find_dup(title: str, pool=None):
        t = norm_w(title)
        # two questions are one heading at a lower bar ("…a second mortgage on another property?" and "…to buy
        # another house?"); a topic heading needs more of its words shared
        bar = 0.5 if is_question(title) else 0.6
        for h in (pool if pool is not None else heads):
            if not own(title) and not own(h["title"]):  # "How compound interest calculator" and "Compound interest
                return h                                  # calculator" say nothing beyond the topic: one heading
            if jac(t, norm_w(h["title"])) >= bar:
                return h
            for q in h["questions"]:
                if jac(t, norm_w(q)) >= bar:
                    return h
            for x in h.get("subs", []):
                if jac(t, norm_w(x["title"])) >= bar:
                    return h
        return None

    def usable(q: str, src: str = "") -> bool:
        return bool(q.strip()) and not foreign(q, home_geo, home_cur) and decision.get(q.lower()) not in (
            "drop", "separate_page")

    # 1. the sections the ranking pages share (and the ones searchers need), in their order
    for s in out.get("sections", []):
        qs = [q for q in s.get("questions", []) if usable(q["q"])]
        h2q = [q for q in qs if q.get("decision") == "h2" and is_question(q["q"])]
        # the section takes a searcher's question as its title only when the question means what the section says
        fit = [q for q in h2q if not opposite(q["q"], s["title"])]
        h2q = fit + [q for q in h2q if q not in fit]  # an opposite question becomes its own H2 below
        title = fit[0]["q"] if fit else s["title"]
        if foreign(title, home_geo, home_cur) or boiler(title) or (not h2q and menu_or_pitch(title, depth)):
            continue
        sec = {"title": sentence_case(title), "level": 2, "covers": [s["id"]], "questions": [], "kind": "topic",
               "sites": len(s.get("covered_by") or []), "subs": []}
        dup = find_dup(sec["title"])
        if dup:
            dup["covers"].append(s["id"])
            sec = dup
        else:
            heads.append(sec)
        # a searcher question that deserves its own heading gets one: every further H2-routed question is an H2
        for q in (h2q[1:] if fit else h2q):
            if not find_dup(q["q"]):
                heads.append({"title": sentence_case(q["q"]), "level": 2, "covers": [s["id"]], "questions": [],
                              "kind": "question", "sites": q.get("competitors", 0), "subs": []})
        for q in qs:
            if q in h2q:
                continue
            if is_question(q["q"]):
                same = find_dup(q["q"])  # the same question asked another way, anywhere on the page
                if same is not None and same is not sec:
                    same["questions"].append(q["q"])
                    continue
                if not find_dup(q["q"], [sec] + sec["subs"]):
                    sec["subs"].append({"title": sentence_case(q["q"]), "level": 3, "covers": [], "questions": [],
                                        "kind": "question", "sites": q.get("competitors", 0), "subs": []})
            else:
                sec["questions"].append(q["q"])  # a search phrasing: answered inside the section in its words
        flipped = None  # steps that contradict the section's title ("Plunge the sink" under "…without a plunger?")
        for ss in s.get("subsections", []):
            if foreign(ss["title"], home_geo, home_cur) or boiler(ss["title"]) or menu_or_pitch(ss["title"], depth) \
                    or find_dup(ss["title"], [sec] + sec["subs"]):
                continue
            sub = {"title": sentence_case(ss["title"]), "level": 3, "covers": [ss["id"]], "questions":
                   [q["q"] for q in ss.get("questions", []) if usable(q["q"])], "kind": "topic",
                   "sites": len(ss.get("covered_by") or []), "subs": []}
            if opposite(sec["title"], ss["title"]):
                if flipped is None:
                    flip_title = re.sub(r"(?i)\b(without|instead of)\s+", "with ", sec["title"])
                    flip_title = re.sub(r"(?i)\b(no|not|never|avoid)\s+", "", flip_title)
                    flipped = find_dup(flip_title) or {"title": sentence_case(flip_title), "level": 2, "covers": [s["id"]],
                                                       "questions": [], "kind": "topic", "sites": sec.get("sites", 0),
                                                       "subs": []}
                    if flipped not in heads:
                        heads.insert(heads.index(sec) if sec in heads else len(heads), flipped)
                flipped["subs"].append(sub)
            else:
                sec["subs"].append(sub)

    # 2. what only one ranking page covers is still covered: under the heading it belongs to, or as its own
    def place(title: str, kind: str, single_site: bool = False):
        if foreign(title, home_geo, home_cur) or boiler(title) or find_dup(title) or any(find_dup(title, h["subs"]) for h in heads):
            return
        if single_site and not entity_based(title):
            return  # one site's slogan or joke, not the topic
        if single_site and menu_or_pitch(title, depth):
            return  # a link in that page's menu ("Pension calculator"), or a sales line, not a section
        t = own(title) or words(title)
        best = max(heads, key=lambda h: jac(t, own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))
                   if h["subs"] else jac(t, own(h["title"])), default=None)
        score = jac(t, own(best["title"])) if best else 0
        item = {"title": sentence_case(title), "level": 3, "covers": [], "questions": [], "kind": kind, "sites": 1,
                "subs": []}
        # a bare method or tool name ("Plumber's snake", "Coat hanger") is one of the options under the section that
        # lists the methods, not a section of its own
        methods = [h for h in heads if re.search(r"(?i)\b(methods?|ways?|options?|types?|tools?|alternatives?|kinds?)\b",
                                                 h["title"])]
        bare = len(title.split()) <= 4 and not is_question(title) and not re.match(r"(?i)(how|why|when|what)\b", title)
        if best and score >= 0.25:
            best["subs"].append(item)
        elif bare and methods:
            max(methods, key=lambda h: len(h["subs"]))["subs"].append(item)
        else:
            item["level"] = 2
            heads.append(item)
    for a in out.get("single_site_angles", []):
        if len(re.findall(r"[A-Za-z]{3,}", a)) >= 2:
            place(a, "angle", single_site=True)
    variants = []
    for q in [dict(x, single=True) for x in out.get("single_site_questions", [])] + \
            [{"q": x["q"]} for x in out.get("other_searches", [])]:
        text = q["q"]
        if not usable(text):
            continue
        extra = own(text) - {"take", "dry", "long"}
        # the main query with one or two words added ("... water based fence paint ...") is a variant of the answer
        if main and main <= words(text) and 0 < len(own(text)) <= 2:
            variants.append(text)
            continue
        if extra:
            place(text, "question", single_site=bool(q.get("single")))

    # order: the ranking pages' own order (what Google already rewards); a question only searchers ask sits right
    # after the section it belongs to instead of in a block of questions
    for h in [x for x in heads if x["kind"] == "question" and not x.get("sites")]:
        t = own(h["title"])
        rest = [x for x in heads if x is not h and x["kind"] != "question"]
        best = max(rest, key=lambda x: jac(t, own(x["title"]) | set().union(*(own(y["title"]) for y in x["subs"]))),
                   default=None)
        if best is not None and jac(t, own(best["title"]) | set().union(*(own(y["title"]) for y in best["subs"]))) >= 0.15:
            heads.remove(h)
            heads.insert(heads.index(best) + 1, h)
    # 3. the page's own job: a commercial page shows the client's offer and ends with its next step
    offer = (sheet.get("client") or {}).get("offer") or {}
    ctas = offer.get("ctas") or []
    if ptype in COMMERCIAL:
        heads.insert(0, {"title": f"How {client} helps", "level": 2, "covers": ["page-job"], "questions": [],
                         "kind": "offer", "sites": 0, "subs": [],
                         "note": "what the client does about this need, from its offer:N facts, with its main next step"})
        heads.append({"title": f"Get started with {client}", "level": 2, "covers": ["page-job"], "questions": [],
                      "kind": "cta", "sites": 0, "subs": [],
                      "note": "the next step: " + (f"\"{ctas[0]['text']}\" → {ctas[0]['url']}" if ctas else "the client's page")})

    # a tool page (a calculator, converter, checker…): how to use it and a worked example are always there
    if ptype == "tool":
        name = (b.get("h1") or query).strip()
        name = name[:1].lower() + name[1:] if name[1:2].islower() else name

        def ensure(title: str, note: str, at: int | None = None, same: str = ""):
            # the live page or page one may already have this section under another name ("Inputs for the …")
            dup = find_dup(title) or next((h for h in heads if same and re.search(same, " ".join(
                [h["title"]] + [x["title"] for x in h["subs"]]))), None)
            if dup:
                dup["note"] = (dup.get("note", "") + " " + note).strip()
                return
            heads.insert(len(heads) if at is None else at, {"title": title, "level": 2, "covers": [], "questions": [],
                                                             "kind": "tool", "sites": 0, "subs": [], "note": note,
                                                             "match": same})
        ensure(f"How to use the {name}", "each input the tool asks for, in its order on the page: what to enter and "
               "where to find it", at=0, same=r"(?i)\binputs?\b|\bhow to use\b|\busing the\b")
        fi = next((i for i, h in enumerate(heads) if re.search(r"(?i)formula|how .*calculat|method", h["title"])), None)
        ensure("Worked example", "one complete example with real figures: the inputs, the formula or method filled in, "
               "each step, the result; as numbered steps or a table", at=None if fi is None else fi + 1,
               same=r"(?i)\bworked example\b|\bexample calculation\b")
    for h in heads:  # a formula heading shows the formula
        if re.search(r"(?i)\bformulae?\b|\bequation\b", " ".join([h["title"]] + [x["title"] for x in h["subs"]])):
            h["note"] = (h.get("note", "") + " write the formula itself as an equation, define each term, then fill it "
                         "in once with real figures").strip()

    # a ranking page's numbered steps arrive as its H3s ("Seal the overflow", "Plunge the sink"): two or more
    # instructions under one heading are that section's numbered list, not headings
    for h in heads:
        steps = [x for x in h["subs"] if is_step(x["title"])]
        if len(steps) >= 2:
            h["steps"] = [x["title"] for x in steps]
            h["subs"] = [x for x in h["subs"] if x not in steps]

    # 4. facts for each heading: the points page one makes, the authority facts, the client's own
    facts = [f for f in sheet.get("facts", []) if f.get("status") in ("verified", "captured", "operator", "serp")]
    ftok = [(f, own(str(f.get("value", "")) + " " + str(f.get("question") or ""))) for f in facts]
    used = set()

    def assign(h):
        t = own(h["title"]) | set().union(*(own(q) for q in h["questions"])) | \
            set().union(*(own(x["title"]) for x in h["subs"])) if True else set()
        if h["kind"] in ("offer", "cta"):
            return [f["id"] for f in facts if str(f.get("id", "")).startswith("offer:")][:6]
        mine = list(h.get("live", [])) + [i for x in h["subs"] for i in x.get("live", [])]  # the live page's own text
        used.update(mine)
        scored = sorted(((len(t & ft), -(f.get("consensus") or 1), f["id"]) for f, ft in ftok
                         if len(t & ft) >= (2 if len(t) >= 3 else 1)), reverse=True)
        ids = [i for _, _, i in scored if i not in used][:8]
        used.update(ids)
        return mine + ids
    for h in heads:
        h["facts"] = assign(h)
    # no consensus point is left behind: unplaced points two or more sites make go to their closest heading
    for f, ft in ftok:
        if f["id"] in used or (f.get("consensus") or 1) < 2 or not heads:
            continue
        best = max(heads, key=lambda h: len(ft & (own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))))
        best["facts"].append(f["id"])
        used.add(f["id"])

    # information gain: an item beyond page one goes under the heading it is about, and only there: an item no
    # heading is about (ISA statistics on a compound interest calculator) is left out rather than forced in
    placed = set()
    for f, ft in ftok:
        if str(f["id"]).startswith("gain:") and heads:
            hw = lambda h: own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])) | \
                set().union(*(own(q) for q in h["questions"]))
            best = max(heads, key=lambda h: len(ft & hw(h)))
            if len(ft & hw(best)) >= (2 if len(hw(best)) >= 3 else 1):
                if f["id"] not in best["facts"]:
                    best["facts"].append(f["id"])
                for h in heads:
                    if h is not best and f["id"] in h["facts"]:
                        h["facts"].remove(f["id"])
                used.add(f["id"])
                placed.add(f["id"])
            else:
                for h in heads:
                    if f["id"] in h["facts"]:
                        h["facts"].remove(f["id"])
    for h in heads:
        h["gain"] = [i for i in h["facts"] if str(i).startswith("gain:")]
    # quotations (GEO: quotes, statistics and cited sources raise visibility in AI answers): 1-2 exact quotes
    byid = {f["id"]: f for f in facts}
    picked, hosts = 0, set()
    for f in quote_candidates(facts):
        h = next((x for x in heads if f["id"] in x["facts"] and not x.get("quote")), None)
        host = (f.get("source_url") or "").split("/")[2:3]
        if h is None or picked >= 2 or tuple(host) in hosts:
            continue
        h["quote"], picked = f["id"], picked + 1
        hosts.add(tuple(host))
    # the author's view: 2-3 first-person passages in the top and middle of the page, where the reader decides
    mark_views(heads, byid)

    # 5. internal links: each client page goes to the heading its title fits. URL words alone can't tell a leaking
    # tap's washers from a gas-leak detector, but the topic's entities can: the client's candidate pages are
    # re-ranked by the entities the ranking pages use (washer, cartridge, valve; plunger, drain, unblocker)
    rel = lm.get("client_related") or {}
    cands = lm.get("client_candidates") or []
    if cands:
        from .clientpages import COMMERCIAL as SHOP_URL, slug_words, _shared
        from urllib.parse import urlparse
        kg = C.load_json(rd / "research" / "semantic_graph.json") or {}
        ents = [e if isinstance(e, str) else e.get("entity", "") for e in kg.get("must_cover_entities") or []]
        ents += [e.get("name") or "" for e in ((kg.get("graph") or {}).get("entities") or [])[:40]]
        ew = set().union(*(words(e) for e in ents if e)) | main
        scored = sorted(((len(_shared(slug_words(u), ew)), u) for u in cands), key=lambda x: -x[0])
        best_c = [u for s, u in scored if s >= 2 and SHOP_URL.search(urlparse(u).path + "/")][:4]
        best_g = [u for s, u in scored if s >= 2 and not SHOP_URL.search(urlparse(u).path + "/")][:5]
        if best_c or best_g:
            rel = {**rel, "commercial": list(dict.fromkeys(best_c + (rel.get("commercial") or [])))[:6],
                   "guides": list(dict.fromkeys((rel.get("guides") or []) + best_g))[:8]}
            with C.file_lock(rd / "link_map.json"):  # the check allows exactly the pages the plan offers
                lm2 = C.load_json(rd / "link_map.json") or {}
                lm2["client_related"] = {**(lm2.get("client_related") or {}), **rel}
                lm2["internal"] = list(dict.fromkeys((lm2.get("internal") or []) + best_c + best_g))
                C.save_json(rd / "link_map.json", lm2)
    titles = lm.get("client_titles") or {}
    targets = list(dict.fromkeys((rel.get("commercial") or [])[:4] + (rel.get("guides") or [])[:5]
                                 + [c["url"] for c in ctas[:2]]))
    unplaced: list[str] = []
    for u in targets:
        tt = own(titles.get(u, "") + " " + re.sub(r"[-_/]", " ", u.split("/", 3)[-1]))
        best = max(heads, key=lambda h: len(tt & (own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))),
                   default=None)
        if best is not None and tt & (own(best["title"]) | set().union(*(own(x["title"]) for x in best["subs"]))):
            best.setdefault("links", []).append(u)
        else:
            unplaced.append(u)
    # a related client page that shares only the topic's words with every heading ("equity release compound interest
    # calculator") still belongs on the page: the two closest go to the section about the topic itself
    body = [h for h in heads if h["kind"] not in ("offer", "cta")]
    for u in unplaced[:2]:
        if body:
            tw = words(titles.get(u, "") + " " + re.sub(r"[-_/]", " ", u.split("/", 3)[-1]))
            max(body, key=lambda h: len(tw & words(h["title"])) - 0.01 * heads.index(h)).setdefault("links", []).append(u)

    # 6. words per heading, and parts for writers working at the same time. No fixed length for every page: each
    # heading gets the room the ranking pages give that topic (the median of what they write under it) and the
    # room its facts need; the page is the sum. A range the operator set in the brief is the only hard limit.
    sec_heads = {s["id"]: s.get("headings") or [s["title"]] for s in out.get("sections", [])}
    for s in out.get("sections", []):
        for ss in s.get("subsections", []):
            sec_heads[ss["id"]] = ss.get("headings") or [ss["title"]]

    def room(item: dict, top: bool) -> int:
        names = [item["title"]] + [n for c in item.get("covers", []) for n in sec_heads.get(c, [])]
        seen = depth_of(depth, names, own_only=bool(item.get("subs")))
        need = (50 if top else 40) + 20 * min(len(item.get("facts", [])), 6) + 15 * len(item.get("steps", []))
        base = max(seen, int(0.7 * need)) if seen else need  # what page one writes, never less than the facts need
        # a topic most ranking pages cover gets their full depth; one only a single site covers, a short section
        weight = min(1.0, 0.4 + 0.2 * (item.get("sites") or 1)) if seen else 1.0
        return int(min(max(base * weight, 60 if top else 40), 400 if top else 220))  # at least the ~40-word answer

    for h in heads:
        h["words"] = room(h, True) + sum(room(x, False) for x in h["subs"])
    total = 90 + sum(h["words"] for h in heads)
    # never far longer than the most thorough page Google already ranks for the query
    comp_words = [p.get("words") or 0 for p in (C.load_json(rd / "research" / "competitor_scrape.json") or {})
                  .get("pages", []) or []]
    ceiling = int(1.2 * max(comp_words)) if comp_words and max(comp_words) > 300 else 0
    if ceiling and total > ceiling:
        f = (ceiling - 90) / max(1, total - 90)
        for h in heads:
            h["words"] = max(60, int(h["words"] * f))
        total = 90 + sum(h["words"] for h in heads)
    if not heads:  # nothing planned (no outline): the page type's usual range
        total = sum(b.get("word_range") or [900, 1400]) // 2
    explicit = b.get("word_range_source") == "explicit" and b.get("word_range")
    if explicit:  # the operator's range: the plan's shares scale to fit it
        e_lo, e_hi = b["word_range"]
        scale = min(1.0, (e_lo + e_hi) / 2 / total) if total > e_hi else max(1.0, (e_lo + e_hi) / 2 / total) \
            if total < e_lo else 1.0
        for h in heads:
            h["words"] = int(h["words"] * scale)
        lo, hi = e_lo, e_hi
    else:
        lo, hi = int(total * 0.8), int(total * 1.25)
    with C.file_lock(rd / "fact_sheet.json"):
        sh = C.load_json(rd / "fact_sheet.json")
        for f in sh.get("facts", []):
            if str(f.get("id", "")).startswith("gain:"):
                f["placed"] = f["id"] in placed
        sh["brief"]["word_range_effective"] = [lo, hi]
        sh["brief"]["length_from"] = "operator" if explicit else "plan"
        C.save_json(rd / "fact_sheet.json", sh)
    n_parts = 3 if len(heads) >= 9 else 2 if len(heads) >= 5 else 1
    parts, size = [], -(-len(heads) // n_parts)
    for i in range(n_parts):
        chunk = heads[i * size:(i + 1) * size]
        if chunk:
            parts.append({"id": "ABC"[i], "headings": [h["title"] for h in chunk], "with_intro": i == 0})
    meanings = mixed_meanings(rd, query, lm, out)
    plan = {"h1": b.get("h1") or sentence_case(query), "intro_words": 90, "headings": heads, "variants": variants,
            "meanings": meanings,
            "parts": parts, "words": [lo, hi]}
    C.save_json(rd / "plan.json", plan)
    return plan


def mixed_meanings(rd: Path, query: str, lm: dict, out: dict) -> list[dict]:
    """When page one mixes several calculators or products for one query (an equity loan, Help to Buy, equity
    release), Google is answering several needs at once. The client's own calculators for those other needs, with
    the evidence that page one shows them: the page opens with a compact list (each term, what it is for, the link)."""
    from .clientpages import slug_words, _shared
    page = ((C.load_json(Path(rd) / "fact_sheet.json") or {}).get("brief") or {}).get("page_url") or ""
    q = words(query) - {"calculator", "calculators", "calc", "uk", "online", "free", "tool"}
    shown = [words(t) for s in out.get("sections", []) for t in (s.get("headings") or [s.get("title", "")])]
    shown += [words(x) for x in out.get("single_site_angles", [])]
    shown += [words(x.get("q", "")) for x in out.get("single_site_questions", []) + out.get("other_searches", [])]
    titles = lm.get("client_titles") or {}
    pool = list(dict.fromkeys((lm.get("client_candidates") or []) + [u for v in (lm.get("client_related") or {}).values()
                                                                     for u in v]))
    found = []
    for u in pool:
        if page and u.rstrip("/") == page.rstrip("/"):
            continue
        sw = slug_words(u)
        if not re.search(r"calculat|checker|converter|estimator|planner", u, re.I) or not _shared(q, sw):
            continue
        own_w = sw - q - {"calculator", "calculators", "uk"}
        if not own_w:
            continue
        evidence = sum(1 for s in shown if s and len(_shared(own_w, s)) >= max(1, len(own_w) // 2))
        if evidence >= 3:  # several page-one sections or searches, not a passing mention
            found.append({"title": titles.get(u) or " ".join(re.sub(r"[-_]+", " ", u.rstrip("/").rsplit("/", 1)[-1]).split()).capitalize(),
                          "url": u, "evidence": evidence})
    return sorted(found, key=lambda x: -x["evidence"])[:5]


def section_depths(comp: dict) -> list[tuple[set, int, int]]:
    """For every heading on every ranking page: its words, the words right under it (to the next heading of any
    level), and the words of its whole section (to the next heading of the same or a higher level)."""
    out = []
    for pg in comp.get("pages", []) or []:
        blocks = pg.get("blocks") or []
        for i, (tag, text) in enumerate(blocks):
            if not (isinstance(tag, str) and re.fullmatch(r"h[2-4]", tag)):
                continue
            lvl, own, whole, under_sub = int(tag[1]), 0, 0, False
            for t2, x2 in blocks[i + 1:]:
                if isinstance(t2, str) and re.fullmatch(r"h[1-6]", t2):
                    if int(t2[1]) <= lvl:
                        break
                    under_sub = True
                    continue
                n = len(str(x2).split())
                if t2 in ("p", "td", "tr") or (t2 == "li" and n >= 6):  # "ISA calculator" list items are links
                    whole += n
                    own += 0 if under_sub else n
            out.append((words(text), own, whole))
    return out


def text_under(depth: list[tuple[set, int, int]], title: str) -> int | None:
    """The fewest words a ranking page writes under this heading (None: no page has it)."""
    k = words(title)
    got = [w2 for w, o, w2 in depth if w and k and jac(k, w) >= 0.6]
    return min(got) if got else None


def depth_of(depth: list[tuple[set, int, int]], names: list[str], own_only: bool = False) -> int:
    """The median words the ranking pages write under a heading matching any of these names (0: none found). With
    own_only, only the words before its first subheading (our plan writes its subheadings separately)."""
    import statistics
    keys = [words(n) for n in names if n]
    got = [(o if own_only else w2) for w, o, w2 in depth if w and any(k and jac(k, w) >= 0.6 for k in keys)]
    got = [g for g in got if g]
    return int(statistics.median(got)) if got else 0


DECIDE = re.compile(r"(?i)\b(which|best|vs\.?|versus|or|better|worth|choose|choosing|should|compare|comparison|cost|"
                    r"costs|price|cheap|types?|methods?|ways?|options?|pros|cons|difference|mistakes?|avoid|right|"
                    r"recommended|how to|when to|tips?)\b")
VIEW_SHARE = 0.7  # views sit in the top and middle of the page, never in its last part (operator's rule)


def view_count(n_heads: int) -> int:
    return 3 if n_heads >= 7 else 2 if n_heads >= 3 else 1


def mark_views(heads: list[dict], byid: dict) -> None:
    """Mark the headings where the author gives a view: where the reader decides, in the first 70% of the page,
    spread out. Gain items that are experiences or opinions make a heading a better place for one."""
    for h in heads:
        h.pop("view", None)
    ok = [i for i, h in enumerate(heads) if h["kind"] not in ("offer", "cta", "tool") and (i + 1) / len(heads) <= VIEW_SHARE]
    if not ok and heads:
        ok = [i for i, h in enumerate(heads) if h["kind"] not in ("offer", "cta")][:1]

    def score(i):
        h = heads[i]
        text = " ".join([h["title"]] + [x["title"] for x in h["subs"]] + h["questions"])
        s = len(DECIDE.findall(text)) + 2 * sum(1 for g in h.get("gain", []) if (byid.get(g) or {}).get("kind")
                                                 in ("experience", "opinion")) + 0.5 * len(h.get("facts", []))
        return s - (1 if i == 0 else 0)
    chosen = []
    for i in sorted(ok, key=score, reverse=True):
        if len(chosen) >= view_count(len(heads)):
            break
        if any(abs(i - j) < 2 for j in chosen) and len(ok) >= 2 * view_count(len(heads)):
            continue  # spread them out when the page has room
        chosen.append(i)
    for i in chosen:
        heads[i]["view"] = True


def quote_candidates(facts: list[dict]) -> list[dict]:
    """Facts whose exact words can be quoted: an authority's rule or figure, or a quote-checked item beyond page one,
    8-40 words, with a source page. Rules and figures first."""
    out = []
    for f in facts:
        v = str(f.get("value") or "")
        if f.get("status") != "verified" or not f.get("source_url") or f.get("basis") == "client_page" \
                or str(f.get("id", "")).startswith(("offer:", "client", "serp:")):
            continue
        if 8 <= len(v.split()) <= 40 and not re.search(r"[|\n]", v):
            out.append(f)
    return sorted(out, key=lambda f: (not re.search(r"(?i)\b(must|should|never|at least|recommend|law|legal|\d)", str(f["value"])),
                                      not str(f["id"]).startswith("gain:")))


def render(plan: dict, facts_by_id: dict) -> list[str]:
    """The plan as the writer reads it."""
    L = [f"H1: {plan['h1']}",
         f"Opening (no heading, about {plan['intro_words']} words): answer the main query in the first two sentences."]
    # each outside source is linked once on the page: writers draft their parts at the same time and can't see
    # each other's links, so the plan says which heading links it (the first in page order); the others name it
    link_at: dict = {}
    for h in plan["headings"]:
        for i in h.get("gain", []) + ([h["quote"]] if h.get("quote") else []):
            u = (facts_by_id.get(i) or {}).get("source_url")
            if u:
                link_at.setdefault(u, h["title"])
    if plan.get("meanings"):
        L.append("  Page one mixes several needs for this query. Open (right after the first answer) with a compact list: "
                 "each term in one line, what it is and when to use it, with the link to our calculator for it; then "
                 "cover them in the page: " + "; ".join(f"\"{m['title']}\" → {m['url']}" for m in plan["meanings"]))
    if plan.get("variants"):
        L.append("  Variants of the main query (answer them in one comparison table or list near the top whose first "
                 "column names the option, e.g. the frequency or the type, never the search (no \"What you searched\"); "
                 "a row only "
                 "where a fact carries it): " + "; ".join(f"\"{v}\"" for v in plan["variants"][:10]))
    for part in plan.get("parts", []):
        L.append(f"\n### Part {part['id']}" + (" (also writes the front matter, H1 and opening)" if part["with_intro"] else ""))
        for h in [x for x in plan["headings"] if x["title"] in part["headings"]]:
            tag = {"offer": " [the client's offer]", "cta": " [next step]"}.get(h["kind"], "")
            sites = f" — on {h['sites']} ranking page(s)" if h.get("sites") else (" — searchers ask; page one doesn't answer"
                                                                                     if h["kind"] == "question" else "")
            L.append(f"## {h['title']}{tag}{sites} (~{h['words']} words)")
            if h.get("note"):
                L.append(f"   {h['note']}")
            if h["questions"]:
                L.append("   also answer, in these words: " + "; ".join(f"\"{q}\"" for q in h["questions"][:6]))
            for s in h["subs"]:
                L.append(f"   ### {s['title']}" + (f" — also: " + "; ".join(s["questions"][:3]) if s["questions"] else ""))
            if h.get("steps"):
                L.append("   steps (a numbered list in this section, not headings): " + "; ".join(h["steps"]))
            plain = [i for i in h.get("facts", []) if not str(i).startswith("gain:")]
            if plain:
                L.append("   facts: " + ", ".join(f"`{i}`" for i in plain))
            if h.get("gain"):
                bits = []
                for i in h["gain"]:
                    u = (facts_by_id.get(i) or {}).get("source_url")
                    first = link_at.get(u) == h["title"]
                    bits.append(f"`{i}`" + ("" if first or not u else f" (name the source only: it is linked under "
                                                                         f"\"{link_at.get(u)}\")"))
                L.append("   beyond page one: " + ", ".join(bits) + " — use each here, crediting who says it; link a "
                         "source here only where no other heading is named for it")
            if h.get("quote"):
                L.append(f"   quote: `{h['quote']}` — its exact words (section 3) in quotation marks, the source named "
                         "and linked in the same sentence")
            if h.get("view"):
                L.append("   your view (first person \"I\", 2-4 sentences inside this section, not its first sentence): "
                         "what you'd pick or do and why, from the facts and experiences here, and when you'd choose "
                         "differently. A real opinion, stated firmly; never a claim that you used, tried or saw it")
            if h.get("links"):
                L.append("   link: " + ", ".join(h["links"][:2]))
    return L


def check(rd: Path, md: str) -> list[str]:
    """Planned headings the draft doesn't have (by their words, so rephrasing is fine)."""
    plan = C.load_json(Path(rd) / "plan.json") or {}
    titles = [re.sub(r"^#+\s*", "", ln) for ln in md.splitlines() if re.match(r"^#{2,4}\s", ln)]
    have = [words(x) for x in titles]
    missing = []
    for h in plan.get("headings", []):
        for item in [h] + h.get("subs", []):
            t = words(item["title"])
            if item.get("match") and any(re.search(item["match"], x) for x in titles):
                continue  # a tool section the writer named its own way ("What does a let-to-buy example cost?")
            if t and not any(len(t & x) / len(t) >= 0.6 for x in have):
                missing.append(("H2 " if item["level"] == 2 else "H3 ") + item["title"])
    return missing
