"""SERP-validated facts: what the pages already on Google's first page state, as a fact table the writer can use.

Google has already chosen these pages for this query in this market, so a point they make is validated evidence:
the writer may state it (in their own words) without a separate research trip, and must cover it. The writer's
own knowledge can still reject a point that is plainly wrong. Where ranking pages contradict each other on the
same point, the figure most ranking sites state wins (rank only breaks a tie) and the others are kept as
alternatives that are never used. A verified authority fact on the
same point beats any competitor. Everything here comes from text already rendered by competitor_scrape: no
network call, no model call.
"""
import html
import re
from collections import defaultdict

from seolib import common as C
from seolib.lint import sentences
from seolib.nlp import _rule_lemma, places

STOP = set("""a an the and or but of to in on for with by from at as is are was were be been being it its this that
these those your you our we they their them there here what which who how when where why can could should would will
may might must do does did done have has had not no so if then than too very just also more most much many some any
all each other into out up down over about after before such only own same both few per via get got make made one two
three yes""".split())
RULE = re.compile(r"\b(must|need to|needs to|cannot|can't|can only|only|at least|up to|within|no more than|maximum|"
                  r"minimum|costs?|fee|free|lasts?|takes?|allowed|required|should|shouldn't|avoid|never|always|best|"
                  r"ideal(ly)?|recommend\w*|aim for|keep|water|feed|plant|grow|use|choose|apply|between|every|once|"
                  r"twice|before|after|during|until|depends?|helps?|prevents?|causes?|means?|requires?|includes?)\b", re.I)
DEF = re.compile(r"^[A-Z][^.]{2,60}\b(is|are|refers to|means)\b (a|an|the|any|one|when|how)\b", re.I)
FIG = re.compile(r"(£|\$|€)?\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:\s?(?:-|–|to)\s?(?:£|\$|€)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?))?"
                 r"\s?(%|per cent|mm|cm|m|km|kg|mg|g|ml|litres?|l|inch(?:es)?|in|ft|feet|days?|weeks?|months?|years?|"
                 r"hours?|minutes?|times|°c|°f|degrees|pence|p|apr|kcal|calories)?\b", re.I)
PROMO = re.compile(r"(cookie|subscribe|newsletter|sign up|log ?in|shop now|buy now|add to (cart|basket)|free (delivery|"
                   r"shipping)|% off|discount|voucher|promo code|all rights reserved|written by|reviewed by|our (team|"
                   r"experts|customers)|trusted by|click here|download (our|the) app|affiliate|commission|sponsored|"
                   r"terms and conditions|privacy policy|last updated|share this|follow us|rated \d|\breviews?\b \(\d|"
                   r"\bread (our|more|the full)\b|for more (insights|info|information|tips|details)|check out (our|this)|"
                   r"mailto:|^share\b|watch:|\bvideo\b|\bcontact [A-Z]|\bcall (us|today|now)\b|second (opinion|reference)|"
                   r"this (quick |short |handy )?(diy )?(guide|article|post|video)|</?[a-z]+>|click & collect)", re.I)
ANAPHOR = re.compile(r"^(this|that|these|those|it|they|such|in this case|if so|otherwise|here)\b", re.I)
SELF = re.compile(r"\b(we|our|us|i|my|me)\b", re.I)  # a competitor's claims about itself are not facts about the topic
# ...nor are its sentences about its own tool, site or process ("The tool is one of five calculators…", "the calculator
# above", "An eligibility check takes 10 minutes", "Market introduces customers to…")
TOOL_SELF = re.compile(r"(?i)\b(this|the) (calculator|tool|page|site|website|app|checker|form)\b(?! (you|your|will|can) )|"
                       r"\b(calculators?|tools?) (above|below|on this)\b|\b(click|tap|press|select) (the|on|below|here)\b|"
                       r"\bintroduces? customers\b|\beligibility check\b|\bapplicant portal\b|\bonline banking\b|"
                       r"\bone of (our|five|four|three|several) (calculators|tools)\b")
VERB = re.compile(r"\b(is|are|was|were|be|been|has|have|had|do|does|can|could|will|would|should|must|may|might|need|"
                  r"needs|take|takes|cost|costs|\w+s|\w+ed)\b", re.I)


def toks(s: str) -> set[str]:
    return {_rule_lemma(w) for w in re.findall(r"[a-z][a-z']{2,}", s.lower()) if w not in STOP}


def figures(s: str) -> list[tuple[str, str]]:
    out = []
    for m in FIG.finditer(s):
        raw = (m.group(4) or "").lower()
        unit = raw if raw in ("%", "times", "inches") else raw.rstrip("s")
        if not (unit or m.group(1)):
            continue  # a bare number ("step 3") is not a figure
        unit = {"per cent": "%", "inches": "inch", "in": "inch", "feet": "ft", "litre": "l", "degree": "°c"}.get(unit, unit)
        lo, hi = m.group(2).replace(",", ""), (m.group(3) or "").replace(",", "")
        out.append(((m.group(1) or "") + lo + ("-" + hi if hi else ""), (m.group(1) or "") + unit))
    return out


def clean(x: str) -> str:
    """Rendered markdown leaves entities and markup in the text ("8&ndash;10", "#### Benefits", "*The Best Soil*")."""
    x = html.unescape(x or "")
    x = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", x)
    x = re.sub(r"\s#{1,6}\s+", " ", x)
    x = re.sub(r"(\*\*|\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", x)
    return " ".join(x.split())


def clash(a: list, b: list) -> bool:
    """Two statements give different figures of the same kind ("8 inches deep" vs "12 inches deep")."""
    sa, sb = set(a), set(b)
    return bool(sa and sb and ({u for _, u in sa} & {u for _, u in sb}) and not (sa & sb))


YEAR = re.compile(r"\b(?:19|20)\d\d\b")


def same_case(a: str, b: str) -> bool:
    """Statements naming different years (a 2026/27 table row and a 2015/16 one) describe different cases: their
    different figures are history, not a contradiction."""
    ya, yb = set(YEAR.findall(a)), set(YEAR.findall(b))
    return not (ya and yb and not (ya & yb))


def units_of(page: dict) -> list[tuple[str, str, str]]:
    """(kind, text, heading) units, the way a reader meets them: paragraphs, list items (lead-ins joined to their
    list), table rows with their column names."""
    out, heading, header, blocks = [], "", "", page.get("blocks") or []
    skip_rest = False
    for i, (t, x) in enumerate(blocks):
        x = clean(x)
        if t in ("h2", "h3", "h4"):
            heading = x
            if re.match(r"^(\d+\s+)?(comments?|responses?|replies|leave a (reply|comment)|related (posts|articles)|"
                        r"you may also like|about the author|more from)\b", x, re.I):
                skip_rest = True
            continue
        if skip_rest:
            continue
        if t == "trh":
            header = x
        elif t == "tr":
            out.append(("row", f"{x} ({header})" if header else x, heading))
        elif t in ("p", "li", "dd", "blockquote"):
            if x.rstrip().endswith(":"):
                items = [clean(x2).rstrip(".;") for t2, x2 in blocks[i + 1:i + 9] if t2 == "li"]
                if items:
                    out.append(("list", f"{x} {'; '.join(items)}.", heading))
                continue
            out.append(("p", x, heading))
    return out


def run(ctx):
    comp = ctx.load("competitor_scrape") or {}
    sem = ctx.load("semantic_graph") or {}
    away = set((sem.get("graph") or {}).get("foreign_pages") or [])
    pages = [p for p in comp.get("pages", []) if p.get("domain") not in away]
    if not pages:
        return {"facts_added": 0, "summary": "no readable ranking pages: nothing to validate against"}
    syn = ctx.brief.get("synonyms") or {}
    from seolib.market import filter_locale
    loc = filter_locale(ctx.brief).partition("-")[2].lower()  # "" on a global page: every country's facts count
    home = ("geo:" + {"uk": "gb"}.get(loc, loc)) if loc else ""
    qt = toks(ctx.brief.get("target_query", "") + " " + " ".join(f"{k} {v}" for k, v in syn.items()))
    topic = set(qt)
    for e in (sem.get("must_cover_entities") or [])[:25]:
        topic |= toks(e if isinstance(e, str) else e.get("entity", ""))
    for t in sem.get("heading_topics") or []:
        topic |= toks(t.get("topic", ""))

    from seolib.graph import foreign as _foreign, market_of
    hgeo, hcur = market_of(filter_locale(ctx.brief))

    def foreign_units(s):
        if hgeo != "geo:us" and re.search(r"\b\d{2,3}\s?(°\s?)?F\b", s):
            return True  # "50 F" with its degree sign lost in rendering
        return _foreign(s, hgeo, hcur)

    def rank(p):  # ranked organic pages first; PAA/related answer sources after page one
        return p["position"] if p.get("position") else 10 + (2 if p.get("source_role") == "paa_source" else 4)

    cands = []
    for p in pages:
        last = ""
        pg_root = (p.get("domain") or "").lower().removeprefix("www.").split(".")[0]
        pg_root = pg_root if len(pg_root) > 3 else ""  # a sentence naming its own site is about that site
        for kind_, x, hdr in units_of(p):
            for s in ([x] if kind_ in ("row", "list") else sentences(x)):
                s = " ".join(s.split())
                if kind_ == "p" and ANAPHOR.match(s) and last:
                    s = last + " " + s  # "This takes 2 weeks." means nothing without the sentence before it
                last = s if kind_ == "p" else last
                n = len(s.split())
                if not (6 <= n <= (70 if kind_ == "list" else 45)) or PROMO.search(s) or s.rstrip().endswith("?"):
                    continue
                own_brand = pg_root and re.search(rf"(?i)\b{re.escape(pg_root)}\b", s)
                if SELF.search(s) or TOOL_SELF.search(s) or own_brand or "..." in s or (kind_ == "p" and not VERB.search(s)):
                    continue
                if kind_ != "row" and " | " in s:
                    continue  # a page title or menu line ("How to Fix a Dripping Tap | Wickes"), not a statement
                where = (places(s) - {home}) if home else set()
                if where:
                    continue  # names another country's body or rule ("the Australian Government…"): not this market's fact
                if foreign_units(s):
                    continue  # another market's currency or units ("between 50 F and 85 F" on a UK page)
                tk = toks(s)
                rel = len(tk & topic)
                figs = figures(s)
                if not rel or not (figs or RULE.search(s) or DEF.match(s)) or (rel < 2 and not (tk & qt)):
                    continue
                cands.append({"s": s, "tk": tk, "figs": figs, "rank": rank(p), "domain": p["domain"],
                              "url": p.get("final_url") or p["url"], "heading": hdr, "title": p.get("title") or "",
                              "rel": rel})
    cands.sort(key=lambda c: (c["rank"], -c["rel"]))
    # cluster statements of the same point (same content words; figures of the same kind when both have them)
    clusters, index = [], defaultdict(set)
    for c in cands:
        best, best_j = None, 0.0
        for ci in set().union(*(index[w] for w in c["tk"])) if c["tk"] else set():
            k = clusters[ci]
            j = len(c["tk"] & k["tk"]) / len(c["tk"] | k["tk"])
            cu, ku = {u for _, u in c["figs"]}, {u for _, u in k["lead"]["figs"]}
            if cu and ku and not (cu & ku):
                continue
            # different figures only merge as a contradiction when the statements are about the very same thing
            # ("12 inches wide" is a different point from "8 inches deep", not a disagreement with it)
            if clash(c["figs"], k["lead"]["figs"]) and (j < 0.5 or not same_case(c["s"], k["lead"]["s"])):
                continue
            if j > best_j:
                best, best_j = ci, j
        if best is not None and best_j >= 0.34:
            k = clusters[best]
            k["members"].append(c)
            k["domains"].add(c["domain"])
        else:
            clusters.append({"tk": set(c["tk"]), "lead": c, "members": [c], "domains": {c["domain"]}})
            for w in c["tk"]:
                index[w].add(len(clusters) - 1)
    official = [f for f in C.load_json(ctx.rd / "fact_sheet.json").get("facts", [])
                if f.get("status") == "verified" and f.get("basis") in ("official_page_auto", "script_fetch", "agent_capture", "site_rates")]
    off_idx = [(toks(str(f.get("value", ""))), figures(str(f.get("value", ""))), f) for f in official]
    auth_vals = {fig for _, figs, _ in off_idx for fig in figs}
    total = len({p["domain"] for p in pages})
    out, conflicts, overridden = [], 0, 0
    for k in clusters:
        # Majority decides a disagreement: the figure most distinct ranking sites state is the fact (7 sites against
        # 3), because one site's ranking rests on many other factors. Rank only breaks a tie. Statements without a
        # figure agree with every version and don't vote.
        groups = []
        for m in k["members"]:
            if not m["figs"]:
                continue
            g = next((g for g in groups if not clash(g[0]["figs"], m["figs"])), None)
            if g is None:
                groups.append([m])
            else:
                g.append(m)
        if len(groups) > 1:
            win = max(groups, key=lambda g: (len({m["domain"] for m in g}), -min(m["rank"] for m in g)))
            lead = min(win, key=lambda m: m["rank"])
            k["votes"] = {"won": len({m["domain"] for m in win}),
                          "lost": sorted((len({m["domain"] for m in g}) for g in groups if g is not win), reverse=True)}
        else:
            lead = k["lead"]  # no disagreement: the highest-ranked statement of this point
        alts, also = [], []
        for m in k["members"]:
            if m is lead or m["domain"] == lead["domain"] or m["s"] == lead["s"]:
                continue
            if clash(lead["figs"], m["figs"]) and same_case(lead["s"], m["s"]):
                if m["s"] not in [a["sentence"] for a in alts]:
                    alts.append({"sentence": m["s"], "rank": m["rank"], "domain": m["domain"], "url": m["url"]})
            elif len(also) < 2 and m["s"] not in also:
                also.append(m["s"])  # other sites' wording of the same point keeps their extra detail
        note = None
        # an authority overrides only a figure no authority confirms, and only on the very same statement: official
        # sentences often carry several figures ("£60,000 … or £10,000 if tapered"), and a near-topic sentence with
        # another figure is not a contradiction
        if lead["figs"] and not (set(lead["figs"]) & auth_vals):
            for otk, ofigs, of in off_idx:
                if clash(lead["figs"], ofigs) and same_case(lead["s"], str(of.get("value", ""))) and \
                        len(otk & lead["tk"]) / max(1, len(otk | lead["tk"])) >= 0.5:
                    note = f"an authority ({C.host(of['source_url'])}, fact {of['id']}) states a different figure: use the authority"
                    break
        n = len(k["domains"])
        score = 3 * min(n, 5) + lead["rel"] + (2 if lead["figs"] else 0) - 0.25 * lead["rank"]
        out.append((score, k, lead, alts, note, also))
    out.sort(key=lambda x: -x[0])
    # every ranking page keeps its own points too: a point only one page-one result makes is still validated
    picked, per_page = [], defaultdict(int)
    for item in out:
        k = item[1]
        if len(picked) < 70 or (per_page[item[2]["url"]] < 4 and len(picked) < 110):
            picked.append(item)
            per_page[item[2]["url"]] += 1
    facts = []
    for i, (score, k, lead, alts, note, also) in enumerate(picked, 1):
        n = len(k["domains"])
        where = f"\"{lead['heading'][:70]}\" on " if lead["heading"] else ""
        v = k.get("votes")
        claim = (f"{where}{lead['domain']} (rank {lead['rank']}); {n} of {total} ranking sites make this point"
                 + (f"; ranking sites disagree: this figure is stated by {v['won']} site(s) against "
                    + ", ".join(str(x) for x in v["lost"]) + " (the majority wins; rank only breaks a tie); not: "
                    + "; ".join(f"rank {a['rank']} {a['domain']}" for a in alts[:3]) if alts and v else ""))
        f = {"id": f"serp:{i}", "claim": claim, "value": lead["s"], "status": "serp_overridden" if note else "serp",
             "basis": "serp_consensus" if n >= 2 else "serp_single", "verified": not note, "source_url": lead["url"],
             "rank": lead["rank"], "domains": sorted(k["domains"]), "consensus": n,
             "retrieved_at": C.now_iso()}
        if also:
            f["also"] = also
        if alts:
            f["conflicts"] = alts[:3]
            conflicts += 1
        if note:
            f["note"] = note
            overridden += 1
        facts.append(f)
    # Google's own People Also Ask answers: the passage Google chose to answer a searcher's question (information
    # gain the ranking pages may lack). Borrowed from another market's results, they only count off YMYL topics.
    serp = ctx.load("serp_intel") or {}
    ym = ctx.brief.get("ymyl")
    strict = ym is True or (ym not in (True, False) and bool(serp.get("ymyl")))
    borrowed = bool(serp.get("paa_locale")) and serp.get("paa_locale") != ctx.brief.get("locale")
    if not (strict and borrowed):
        for j, (q, a) in enumerate((serp.get("paa_answers") or {}).items(), 1):
            snippet = clean((a or {}).get("snippet") or "")
            if not q or not a.get("link") or len(snippet.split()) < 6 or SELF.search(snippet):
                continue
            facts.append({"id": f"serp:paa:{j}", "claim": f"Google's answer to the searcher question \"{q}\" ({C.host(a['link'])})",
                          "value": snippet, "status": "serp", "basis": "paa_answer", "verified": True,
                          "source_url": a["link"], "rank": None, "domains": [C.host(a["link"])], "consensus": 1,
                          "question": q, "retrieved_at": C.now_iso()})
    with C.file_lock(ctx.rd / "fact_sheet.json"):
        sheet = C.load_json(ctx.rd / "fact_sheet.json")
        sheet["facts"] = [f for f in sheet["facts"] if not str(f.get("id", "")).startswith("serp:")] + facts
        C.save_json(ctx.rd / "fact_sheet.json", sheet)
    decisions = [f"SERP-validated facts: {len(facts)} points from {total} page-one sites"
                 f" ({sum(1 for f in facts if f['consensus'] >= 2)} made by 2+ sites); {conflicts} contradictions resolved"
                 " by majority of ranking sites (rank breaks ties)" + (f"; {overridden} overridden by an authority fact" if overridden else "")]
    return {"facts_added": len(facts), "conflicts": conflicts, "overridden": overridden, "decisions": decisions,
            "summary": f"{len(facts)} SERP-validated points ({sum(1 for f in facts if f['consensus'] >= 2)} consensus), "
                       f"{conflicts} conflicts resolved by majority, {overridden} authority overrides"}
