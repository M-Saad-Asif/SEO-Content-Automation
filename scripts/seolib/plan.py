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


def words(s: str) -> set[str]:
    from .nlp import tokens
    return {w for w in tokens(s or "") if w not in STOP and len(w) > 1 and not w.isdigit()}


def jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def sentence_case(h: str) -> str:
    """"How Long To Wait Before Painting" -> "How long to wait before painting"; acronyms and names stay."""
    h = re.sub(r"^\W+|\s+", " ", h or "").strip(" -–—:|")
    out = []
    for i, w in enumerate(h.split()):
        parts = w.split("-")
        for j, x in enumerate(parts):
            if (i or j) and x[:1].isupper() and not x.isupper() and len(x) > 1 and not re.search(r"[A-Z]", x[1:]):
                parts[j] = x[0].lower() + x[1:]
        out.append("-".join(parts))
    s = " ".join(out)
    return s[:1].upper() + s[1:] if s else s


def is_question(q: str) -> bool:
    return q.strip().endswith("?") or bool(QWORD.match(q.strip()))


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
    home_geo, home_cur = market_of(b.get("locale") or "en-GB")
    decision = {r["query"].lower(): r.get("decision") for r in qmap.get("queries", [])}

    def own(s):  # a heading's own words: the topic's words are in every heading and say nothing
        return words(s) - main

    heads: list[dict] = []  # {"title", "level", "covers": [...], "questions": [...], "kind", "parent"}

    def find_dup(title: str, pool=None):
        t = own(title) or words(title)
        for h in (pool if pool is not None else heads):
            if jac(t, own(h["title"]) or words(h["title"])) >= 0.6:
                return h
            for q in h["questions"]:
                if jac(t, own(q) or words(q)) >= 0.6:
                    return h
            for x in h.get("subs", []):
                if jac(t, own(x["title"]) or words(x["title"])) >= 0.6:
                    return h
        return None

    def usable(q: str, src: str = "") -> bool:
        return bool(q.strip()) and not foreign(q, home_geo, home_cur) and decision.get(q.lower()) not in (
            "drop", "separate_page")

    # 1. the sections the ranking pages share (and the ones searchers need), in their order
    for s in out.get("sections", []):
        qs = [q for q in s.get("questions", []) if usable(q["q"])]
        h2q = [q for q in qs if q.get("decision") == "h2" and is_question(q["q"])]
        title = h2q[0]["q"] if h2q else s["title"]
        if foreign(title, home_geo, home_cur):
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
        for q in h2q[1:]:
            if not find_dup(q["q"]):
                heads.append({"title": sentence_case(q["q"]), "level": 2, "covers": [s["id"]], "questions": [],
                              "kind": "question", "sites": q.get("competitors", 0), "subs": []})
        for q in qs:
            if q in h2q:
                continue
            if is_question(q["q"]):
                if not find_dup(q["q"], [sec] + sec["subs"]):
                    sec["subs"].append({"title": sentence_case(q["q"]), "level": 3, "covers": [], "questions": [],
                                        "kind": "question", "sites": q.get("competitors", 0), "subs": []})
            else:
                sec["questions"].append(q["q"])  # a search phrasing: answered inside the section in its words
        for ss in s.get("subsections", []):
            if foreign(ss["title"], home_geo, home_cur) or find_dup(ss["title"], [sec] + sec["subs"]):
                continue
            sec["subs"].append({"title": sentence_case(ss["title"]), "level": 3, "covers": [ss["id"]], "questions":
                                [q["q"] for q in ss.get("questions", []) if usable(q["q"])], "kind": "topic",
                                "sites": len(ss.get("covered_by") or []), "subs": []})

    # 2. what only one ranking page covers is still covered: under the heading it belongs to, or as its own
    def place(title: str, kind: str):
        if foreign(title, home_geo, home_cur) or find_dup(title) or any(find_dup(title, h["subs"]) for h in heads):
            return
        t = own(title) or words(title)
        best = max(heads, key=lambda h: jac(t, own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))
                   if h["subs"] else jac(t, own(h["title"])), default=None)
        score = jac(t, own(best["title"])) if best else 0
        item = {"title": sentence_case(title), "level": 3, "covers": [], "questions": [], "kind": kind, "sites": 1,
                "subs": []}
        if best and score >= 0.25:
            best["subs"].append(item)
        else:
            item["level"] = 2
            heads.append(item)
    for a in out.get("single_site_angles", []):
        if len(re.findall(r"[A-Za-z]{3,}", a)) >= 2:
            place(a, "angle")
    variants = []
    for q in out.get("single_site_questions", []) + [{"q": x["q"]} for x in out.get("other_searches", [])]:
        text = q["q"]
        if not usable(text):
            continue
        extra = own(text) - {"take", "dry", "long"}
        # the main query with one or two words added ("... water based fence paint ...") is a variant of the answer
        if main and main <= words(text) and 0 < len(own(text)) <= 2:
            variants.append(text)
            continue
        if extra:
            place(text, "question")

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

    # 4. facts for each heading: the points page one makes, the authority facts, the client's own
    facts = [f for f in sheet.get("facts", []) if f.get("status") in ("verified", "captured", "operator", "serp")]
    ftok = [(f, own(str(f.get("value", "")) + " " + str(f.get("question") or ""))) for f in facts]
    used = set()

    def assign(h):
        t = own(h["title"]) | set().union(*(own(q) for q in h["questions"])) | \
            set().union(*(own(x["title"]) for x in h["subs"])) if True else set()
        if h["kind"] in ("offer", "cta"):
            return [f["id"] for f in facts if str(f.get("id", "")).startswith("offer:")][:6]
        scored = sorted(((len(t & ft), -(f.get("consensus") or 1), f["id"]) for f, ft in ftok
                         if len(t & ft) >= (2 if len(t) >= 3 else 1)), reverse=True)
        ids = [i for _, _, i in scored if i not in used][:8]
        used.update(ids)
        return ids
    for h in heads:
        h["facts"] = assign(h)
    # no consensus point is left behind: unplaced points two or more sites make go to their closest heading
    for f, ft in ftok:
        if f["id"] in used or (f.get("consensus") or 1) < 2 or not heads:
            continue
        best = max(heads, key=lambda h: len(ft & (own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))))
        best["facts"].append(f["id"])
        used.add(f["id"])

    # information gain: every item beyond page one goes under the heading it fits (it's why the page is worth reading)
    for f, ft in ftok:
        if str(f["id"]).startswith("gain:") and f["id"] not in used and heads:
            best = max(heads, key=lambda h: len(ft & (own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))))
            best["facts"].append(f["id"])
            used.add(f["id"])
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

    # 5. internal links: each client page goes to the heading its title fits
    rel = lm.get("client_related") or {}
    titles = lm.get("client_titles") or {}
    targets = list(dict.fromkeys((rel.get("commercial") or [])[:4] + (rel.get("guides") or [])[:5]
                                 + [c["url"] for c in ctas[:2]]))
    for u in targets:
        tt = own(titles.get(u, "") + " " + re.sub(r"[-_/]", " ", u.split("/", 3)[-1]))
        best = max(heads, key=lambda h: len(tt & (own(h["title"]) | set().union(*(own(x["title"]) for x in h["subs"])))),
                   default=None)
        if best is not None and tt & (own(best["title"]) | set().union(*(own(x["title"]) for x in best["subs"]))):
            best.setdefault("links", []).append(u)

    # 6. words per heading, and parts for writers working at the same time
    lo, hi = b.get("word_range_effective") or b.get("word_range") or [900, 1400]
    budget = (lo + hi) // 2
    units = sum(1 + 0.5 * len(h["subs"]) for h in heads) or 1
    per = max(110, int((budget - 90) / units))
    for h in heads:
        h["words"] = int(per * (1 + 0.5 * len(h["subs"])))
    total = 90 + sum(h["words"] for h in heads)
    if total > hi:  # every heading answered properly: the length range follows the plan
        lo, hi = int(total * 0.85), int(total * 1.2)
        with C.file_lock(rd / "fact_sheet.json"):
            sh = C.load_json(rd / "fact_sheet.json")
            sh["brief"]["word_range_effective"] = [lo, hi]
            C.save_json(rd / "fact_sheet.json", sh)
    n_parts = 3 if len(heads) >= 9 else 2 if len(heads) >= 5 else 1
    parts, size = [], -(-len(heads) // n_parts)
    for i in range(n_parts):
        chunk = heads[i * size:(i + 1) * size]
        if chunk:
            parts.append({"id": "ABC"[i], "headings": [h["title"] for h in chunk], "with_intro": i == 0})
    plan = {"h1": b.get("h1") or sentence_case(query), "intro_words": 90, "headings": heads, "variants": variants,
            "parts": parts, "words": [lo, hi]}
    C.save_json(rd / "plan.json", plan)
    return plan


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
    ok = [i for i, h in enumerate(heads) if h["kind"] not in ("offer", "cta") and (i + 1) / len(heads) <= VIEW_SHARE]
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
    if plan.get("variants"):
        L.append("  Variants of the main query (answer each in one comparison table or list near the top; a row only "
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
            plain = [i for i in h.get("facts", []) if not str(i).startswith("gain:")]
            if plain:
                L.append("   facts: " + ", ".join(f"`{i}`" for i in plain))
            if h.get("gain"):
                L.append("   beyond page one: " + ", ".join(f"`{i}`" for i in h["gain"])
                         + " — use each here, crediting who says it, and link it")
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
    have = [words(re.sub(r"^#+\s*", "", ln)) for ln in md.splitlines() if re.match(r"^#{2,4}\s", ln)]
    missing = []
    for h in plan.get("headings", []):
        for item in [h] + h.get("subs", []):
            t = words(item["title"])
            if t and not any(len(t & x) / len(t) >= 0.6 for x in have):
                missing.append(("H2 " if item["level"] == 2 else "H3 ") + item["title"])
    return missing
