"""Knowledge graph of one topic in one market, built from the pages that rank there.

Entities (typed, with aliases, a definition, and how widely the ranking pages and the searches use them),
entity -> attribute -> values (each value with the sites that state it and a qualifier: max, min, range, typical),
and relationships between entities (subject - predicate - object) with the sentence that states each one. Every
node and edge carries its sources.

Plain rules, so it gives a usable graph with or without spaCy; when spaCy loads, its part-of-speech tags keep verbs
and adjectives out of entity names and its named-entity labels sharpen the types. Niche-free: nothing here names a
sector. The vocabulary comes from the pages, the searches and the query; the market comes from the locale
(sentences about another country or in another currency are left out).
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from .nlp import places

FUNC = set("""a an the and or but if then than so as of to in on at by for with from into onto over under about
after before between through during without within against across per via up down out off upon while because
is are was were be been being am do does did doing have has had having will would shall should can could may might
must i you he she it we they me him her us them my your his its our their this that these those who whom whose
which what when where why how there here not no nor only also just too very more most less least much many some any
all each every both either neither other others another such own same few several yes etc eg ie vs versus whether
let lets""".split())
PRONOUNS = set("i you he she it we they me him her us them my your his its our their this that these those".split())
# words that qualify a noun without naming anything: stripped from the edges of entity names
SOFT = set("""usually typically often generally normally sometimes always never really actually simply quite rather
fairly mostly mainly largely possibly probably likely potentially currently already still even ever however therefore
also easily quickly fully new good great best better big small key main important different various certain available
possible able free full total extra additional specific particular general typical common standard average usual
similar right wrong ideal perfect simple easy quick fast slow whole overall actual real true exact precise further
maximum minimum max min approximately roughly around just only clear little back fastest lowest highest somewhere""".split())
# nouns that never name anything on their own ("people", "option"): fine inside a longer name
GENERIC = set("""person people example date status thing things way ways time times information detail details case cases
step steps part parts number numbers type types lot lots kind kinds option options question questions answer answers
article page site website post day days month months week weeks year years hour hours minute minutes reason reasons
place problem problems issue issues result results point points use user users side sides bit bits top bottom end
start beginning everything something anything nothing help need needs solution solutions situation situations
circumstance circumstances aspect aspects factor factors benefit benefits advantage advantages disadvantage
disadvantages pro pros con cons guide guides team customer customers client clients service services product
products company companies business businesses amount amounts level levels range area areas form forms list idea
ideas tip tips fact facts choice choices difference differences matter matters world life home today
contact call email phone quote review reviews star stars rating click link links button menu policy cookie cookies
image video read more purpose deal work works offer offers""".split())
PRON_MODAL = set("i you we they he she it can could will would may might must should shall to not don't doesn't "
                 "won't can't cannot".split())
# base forms of verbs that carry a relationship between two things ("X is secured against Y", "X requires Y")
VERBS = set("""be is are was were been being become becomes have has had require need allow let enable offer provide
give take make mean include cover depend differ vary charge lend borrow repay pay cost use secure rank sit apply
regulate protect reduce increase affect replace fund buy sell get involve add carry hold own work help support
determine define describe refer call know consider treat count qualify accept approve decline refuse reject assess
check calculate base set limit cap range start begin end last run release raise fall rise exceed match compare
relate belong lead cause result prevent avoid risk lose gain earn save spend owe transfer convert register record
report list show state permit prohibit ban exempt rank come go keep remain stay sit act serve""".split())
# words that may sit in a relation phrase besides verbs and function words ("is subject to", "is cheaper than")
REL_EXTRA = set("""subject able likely unlikely similar different based known called available responsible liable
eligible entitled secured repaid paid owed due than more less higher lower cheaper faster slower usually typically
often generally normally also only still always never not no""".split())
RULE_WORDS = {"act", "regulation", "rule", "handbook", "code", "law", "directive", "guidance", "standard", "scheme",
              "section", "clause", "licence", "license", "permission", "agreement", "contract", "policy"}
AGENT_SUFFIX = ("er", "or", "ant", "ee", "ist", "ian")  # not "-ent": payment, consent, refurbishment are things
MEASURE_WORD = re.compile(r"\b(rate|fee|cost|price|amount|size|value|term|period|time|length|ratio|limit|level|"
                          r"percentage|share|duration|age|weight|height|width|depth|speed|score|income|salary|"
                          r"deposit|balance|tax|charge|apr|ltv)s?\b|%", re.I)
NOT_AGENT = set("""order number letter paper water power cover matter center centre register other rather either neither
offer interest value ratio sector factor minor major manner chapter quarter percent content event rent payment
statement agreement amount equipment investment document management requirement assessment settlement repayment
commitment adjustment development improvement environment instrument segment moment element component treatment
calculator computer printer filter folder browser server charger container sensor monitor generator indicator
counter meter error mirror colour color floor door winter summer river corner border""".split())
NOISE = re.compile(r"(written by|edited by|reviewed by|^by:|\bauthor\b|app store|play store|\brating\b|"
                   r"\d[\d,.]*\s*(google |trustpilot )?reviews\b|free forever|click here|subscribe|cookie|captcha|"
                   r"enter your (email|phone)|trusted by|sign up|log ?in\b|download (our|the) app|^home\b|"
                   r"all rights reserved|last updated|call (us|now|today)|get (started|in touch|a quote)|contact us|"
                   r"privacy|terms (and|&) conditions|\bmon(day)?\s*-\s*fri|\b0\d{3,4}\s?\d{3}\s?\d{3,4}\b|@\w+\.\w+|"
                   r"\]\(https?:|learn more|let'?s speak|read more)", re.I)
# headings that are page furniture (widgets, calls to action, tables of contents), never a topic
UI_HEADING = re.compile(r"\b(recently viewed|you may also like|related (products|posts|articles)|customer reviews|reviews?|"
                        r"newsletter|sign up|subscribe|share this|leave a (comment|reply)|comments?|cart|basket|"
                        r"shop now|follow us|about the author|table of contents|contents|how can we help( you)?|(more )?frequently asked questions|faqs?|"
                        r"contact us|get in touch|quick links|useful links|more [\w -]{0,30}(posts|articles|guides|stories)|"
                        r"related (topics|links|content|reading|pages|searches)|see also|explore (more|the topic)|"
                        r"more (on|about|in) this|other (topics|guides)|popular (posts|guides|articles)|in this section|"
                        r"book (your|a|now|online)|get (a|your) (free )?quote|call (us|now|today)|today$|near (you|me)|"
                        r"why choose|our (services|prices|team|reviews)|video|watch|(others )?also viewed|most popular|"
                        r"latest (news|posts|articles|insights)|trending|recommended (for you|reading)|you might (also )?like|"
                        r"testimonials?|case stud(y|ies)|what (our )?(clients|customers) say|the bottom line|"
                        r"additional resources|key takeaways|final thoughts|conclusion|summary|disclaimer|"
                        r"related (solutions|services|guides)|select your (location|country|region|store)|store locator|"
                        r"find (a|your) (store|stockist))\b|^(day|step|week|stage|phase)\s*\d+\b", re.I)
CTA = re.compile(r"(?i)^(ready to|want to|looking (for|to)|need (a|an|help|finance)|why choose|get started|"
                 r"how can we help|contact|call us|speak to|is (a|an|this) .{3,60} right for you|interested in)"
                 r"|\b(with us|from us|our (team|experts|product|service|account|app))\b")
NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
MULT = r"(?:\s?(k|m|bn|million|billion|thousand)\b)?"
UNIT = (r"(%|per cent|percent|inches|inch|feet|foot|ft|gallons?|quarts?|pints?|mm|cm|km|kg|mg|g|ml|litres?|l|working days|business days|days?|weeks?|months?|years?|"
        r"hours?|minutes?|times|kcal|calories|°c|degrees|pence|p)(?!\w)")
FIG = re.compile(r"(£|\$|€)?\s?" + NUM + MULT + r"(?:\s?%)?(?:\s?(?:-|–|to)\s?(£|\$|€)?" + NUM + MULT + r")?(?:\s?" + UNIT + r")?", re.I)
RANGE_JOIN = re.compile(r"([£$€]?\d[\d,.]*(?:\s?(?:k|m|bn))?(?:\s?%)?)\s*(?:and|up to|-|–)\s*(?=[£$€]?\d)", re.I)
QUAL = [("max", re.compile(r"\b(up to|maximum( of)?|max\.?|no more than|at most|as much as|capped at|limit of|"
                           r"less than|under|below|within)\W*$", re.I)),
        ("min", re.compile(r"\b(from|starting (at|from)|start (at|from)|minimum( of)?|min\.?|at least|as little as|"
                           r"as low as|as few as|no less than|more than|over|above|lowest)\W*(just\W*)?$", re.I)),
        ("typical", re.compile(r"\b(around|about|approximately|roughly|typically|usually|on average|average( of)?|"
                               r"normally|generally|often|commonly|in the region of|somewhere around)\W*$", re.I))]
TIME_UNITS = re.compile(r"(day|week|month|year|hour|minute)", re.I)
WORD = re.compile(r"[A-Za-z][A-Za-z']*(?:-[A-Za-z]+)*")
CUR_OF = {"gb": "£", "uk": "£", "us": "$", "ca": "$", "au": "$", "nz": "$", "ie": "€", "de": "€", "fr": "€",
          "es": "€", "it": "€", "nl": "€", "pt": "€", "at": "€", "be": "€", "fi": "€", "in": "₹"}
MAX_WORDS_PER_PAGE = 4000
BULLETS = re.compile(r"\s*(?:[•▪●‣⁃◦|]|[\U0001F300-\U0001FAFF☀-➿]️?)+\s*")


def clean(text: str) -> str:
    """One spelling for the punctuation scraped pages vary on (non-breaking hyphens, curly quotes, bad decodes)."""
    t = (text or "").replace("‑", "-").replace("‐", "-").replace("‒", "-").replace("­", "")
    return t.replace("�", "'").replace("’", "'").replace("‘", "'").replace(" ", " ").replace(" ", " ")


def lemma(w: str) -> str:
    """Plural-only lemma: "loans"/"loan" and "lenders"/"lender" merge; "bridging" and "secured" stay as written,
    because in a name they are part of the name."""
    w = w.lower().replace("’", "'")
    if w.endswith("'s"):
        w = w[:-2]
    if len(w) <= 3 or not w.isalpha() or w.endswith(("ss", "us", "is", "ics", "ous")):
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("sses", "shes", "ches", "xes", "zes")) or (w.endswith("oes") and len(w) > 5):
        return w[:-2]
    return w[:-1] if w.endswith("s") else w


def verb_base(w: str) -> str | None:
    """'requires' -> 'require', 'secured' -> 'secure', 'applies' -> 'apply'; None when it is no relation verb."""
    w = w.lower()
    for c in (w, w[:-1], w[:-2], w[:-1] if w.endswith("ed") else "", w[:-3] + "y" if w.endswith(("ies", "ied")) else "",
              w[:-3] if w.endswith("ing") else "", w[:-3] + "e" if w.endswith("ing") else ""):
        if c and c in VERBS:
            return c
    return None


def words(text: str) -> list[str]:
    """Words, with compounds split ("second-charge" -> "second charge") unless a function word is inside them
    ("loan-to-value" stays one word, the way readers search it)."""
    out = []
    for m in WORD.finditer(clean(text)):
        w = m.group(0).strip("'")
        if not w:
            continue
        if "-" in w and not any(p.lower() in FUNC for p in w.split("-")):
            out += [x for x in w.split("-") if x]
        else:
            out.append(w)
    return out


def sentences(text: str) -> list[str]:
    out = []
    for part in BULLETS.split(clean(text)):
        out += [s.strip(" -–*") for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9£$€\"'(])", part) if s.strip(" -–*")]
    return out


def market_of(locale: str) -> tuple[str, str]:
    region = (locale or "en-GB").partition("-")[2].lower() or "gb"
    return ("geo:" + ("gb" if region == "uk" else region)), CUR_OF.get(region, "")


def foreign(sentence: str, home_geo: str, home_cur: str) -> bool:
    """About another market: another currency, another market's units (Fahrenheit, US gallons outside the US), or a
    country other than this one (the EU counts as neighbourly)."""
    if home_cur and any(c in sentence for c in "£$€₹" if c != home_cur):
        return True
    if home_geo != "geo:us" and re.search(r"°\s?F\b|\bfahrenheit\b|\bgallons?\b|\bquarts?\b", sentence, re.I):
        return True
    return bool(places(sentence) - {home_geo, "geo:eu"})


class Matcher:
    """Finds known entities in a sentence: longest match first, by plural-free lemmas, no overlaps."""

    def __init__(self, keys: dict[tuple, str]):
        self.keys = keys
        self.longest = max((len(k) for k in keys), default=1)

    def find(self, toks: list[str]) -> list[tuple[int, int, str]]:
        lem = [lemma(t) for t in toks]
        out, i = [], 0
        while i < len(lem):
            for n in range(min(self.longest, len(lem) - i), 0, -1):
                k = tuple(lem[i:i + n])
                if k in self.keys:
                    out.append((i, i + n, self.keys[k]))
                    i += n
                    break
            else:
                i += 1
        return out


def matcher_for(graph: dict) -> Matcher:
    keys = {}
    for e in graph.get("entities", []):
        keys[tuple(e["tokens"])] = e["key"]
        for a in e.get("aliases", []):
            keys[(a.lower(),)] = e["key"]
    return Matcher(keys)


def _spacy(texts: list[str]) -> tuple[dict, dict]:
    """(named-entity labels by entity key, majority part of speech by lower-case word) from spaCy when it loads;
    ({}, {}) when it does not."""
    try:
        from .nlp import _LOAD, import_spacy
        with _LOAD:
            nlp = import_spacy().load("en_core_web_sm", disable=["parser", "lemmatizer"])
    except Exception:
        return {}, {}
    labels: dict[str, Counter] = defaultdict(Counter)
    pos: dict[str, Counter] = defaultdict(Counter)
    try:
        for doc in nlp.pipe(texts, batch_size=4):
            for t in doc:
                if t.is_alpha:
                    pos[t.lower_][t.pos_] += 1
            for e in doc.ents:
                if e.label_ in ("ORG", "LAW", "PERSON", "GPE", "PRODUCT", "NORP"):
                    k = " ".join(lemma(w) for w in words(e.text) if w.lower() != "the")
                    if k:
                        labels[k][e.label_] += 1
    except Exception:
        return {}, {}
    return ({k: c.most_common(1)[0][0] for k, c in labels.items()},
            {w: c.most_common(1)[0][0] for w, c in pos.items()})


def _qualifier(before: str, has_hi: bool) -> str:
    if has_hi:
        return "range"
    for name, rx in QUAL:
        if rx.search(before[-40:]):
            return name
    return ""


def _strip_qual(before: str) -> str:
    """The words before a figure without its qualifier and linking words: "Borrow up to" -> "Borrow"."""
    s = before
    for _ in range(4):
        prev = s
        for _, rx in QUAL:
            s = rx.sub("", s)
        s = re.sub(r"(?i)(\b(" + "|".join(sorted(FUNC | SOFT, key=len, reverse=True)) + r")\b|[\s:;,(\-–])+$", "", s)
        if s == prev:
            break
    return s


def value_kind(m: re.Match) -> str:
    unit = (m.group(7) or "").lower()
    if m.group(1) or m.group(4) or m.group(3):
        return "money"
    if unit in ("%", "per cent", "percent") or "%" in m.group(0):
        return "percent"
    if TIME_UNITS.match(unit):
        return "duration"
    return "quantity" if unit else "number"


def build(pages: list[dict], query: str, locale: str, searches: list[str] | None = None,
          use_spacy: bool = True, strict_market: bool = True) -> dict:
    """The graph. `pages` are competitor_scrape pages (domain, blocks); `searches` are the questions and queries
    people type around the topic (PAA, related, autocomplete), used to mark which entities searchers name."""
    home_geo, home_cur = market_of(locale)
    n_pages = len({p["domain"] for p in pages}) or 1
    qlem = [lemma(w) for w in words(query) if w.lower() not in FUNC and not places(w)]
    qset = set(qlem)
    # 1. sentences in this market, with the section they sit in
    sents = []  # (domain, heading, sentence, block type)
    heads_by_dom = defaultdict(list)
    dropped_foreign, foreign_pages = 0, []
    for p in pages:
        dom, h, budget = p["domain"], "", MAX_WORDS_PER_PAGE
        # a page written for another market (a US lender ranking in a UK search): its amounts, rules and terms are
        # that market's, so it adds nothing true to this market's graph
        body = " ".join(x for t, x in p.get("blocks", []) if t not in ("h1", "h2", "h3", "h4"))
        cur = Counter(c for c in body if c in "£$€₹")
        other = sum(n for c, n in cur.items() if c != home_cur)
        geo = Counter(g for x in sentences(body)[:400] for g in places(x))
        other_geo = sum(n for g, n in geo.items() if g not in (home_geo, "geo:eu"))
        # only where the market decides the facts (money, law, health): a US gardening guide in a UK search still
        # teaches how tomatoes grow; its dollar and Fahrenheit sentences are dropped one by one below
        if strict_market and (home_cur and (other >= 3 and other > 2 * cur.get(home_cur, 0)) or
                              (other_geo >= 5 and other_geo > 2 * geo.get(home_geo, 0))):
            foreign_pages.append(dom)
            continue
        for t, x in p.get("blocks", []):
            if t in ("h1", "h2", "h3", "h4"):
                h = clean(x).strip().lstrip("#").strip()
                heads_by_dom[dom].append(h)
                continue
            if t not in ("p", "li", "td", "dd", "tr", "blockquote") or budget <= 0:
                continue
            for s in sentences(x):
                n = len(s.split())
                if n < 3 or n > 60 or NOISE.search(s) or CTA.search(s):
                    continue
                if foreign(s, home_geo, home_cur):
                    dropped_foreign += 1
                    continue
                budget -= n
                sents.append((dom, h, s, t))
    tok_sents = [(d, h, s, t, words(s)) for d, h, s, t in sents]
    n_pages = len({p["domain"] for p in pages} - set(foreign_pages)) or 1  # "6/8 sites" counts this market's pages
    # "loan to value" and "loan-to-value" are one name: spaced forms join up with the hyphenated one the pages use
    compounds = {tuple(w.lower().split("-")) for *_, toks in tok_sents for w in toks if "-" in w}
    if compounds:
        tok_sents = [(d, h, s, t, join_compounds(toks, compounds)) for d, h, s, t, toks in tok_sents]
    labels, pos = _spacy([" ".join(s for d, h, s, *_ in sents if d == dom)[:30000]
                          for dom in dict.fromkeys(d for d, *_ in sents)]) if use_spacy else ({}, {})
    # 2. words used as verbs ("you can apply", "to borrow"): never part of an entity name
    prev_pm, total, acts = Counter(), Counter(), Counter()
    for *_, toks in tok_sents:
        for i, w in enumerate(toks):
            lw = w.lower()
            total[lw] += 1
            if i and toks[i - 1].lower() in PRON_MODAL:
                prev_pm[lw] += 1
            if i + 1 < len(toks):
                nx = toks[i + 1].lower()
                if nx in ("can", "will", "may", "might", "must", "should", "would", "could", "usually", "often") or \
                        verb_base(nx) not in (None, "be", "have", "become"):
                    acts[lemma(lw)] += 1
    ltotal = Counter()
    for w, n in total.items():
        ltotal[lemma(w)] += n
    verbish = {w for w, n in total.items() if n >= 3 and prev_pm[w] / n >= 0.3}
    verbish |= {w for w in total if verb_base(w) in ("be", "have", "become")}
    if pos:  # a word spaCy reads mostly as a verb, adverb or pronoun breaks a name ("-ing" words stay: "bridging loan")
        verbish |= {w for w, p in pos.items() if p in ("VERB", "AUX", "ADV", "PRON", "DET", "ADP", "SCONJ", "CCONJ",
                                                        "PART", "INTJ") and not w.endswith("ing")}
    upper = Counter(w.lower() for *_, toks in tok_sents for w in toks if w.isupper() and 2 <= len(w) <= 6)
    acronyms = {w for w, n in upper.items() if n >= 0.7 * total[w]}

    def nounish(w: str) -> bool:
        lw = w.lower()
        if lw in acronyms:
            return True
        if pos and lw in pos:
            return pos[lw] in ("NOUN", "PROPN")
        return lw not in verbish and "'" not in lw and \
            not lw.endswith(("ed", "ly", "ible", "able", "ive", "ous", "ful", "less"))
    # 3. candidate names: every 1-4 word slice of a noun run, counted per site
    tf, df, maximal, topical = Counter(), defaultdict(set), Counter(), defaultdict(set)
    forms: dict[tuple, Counter] = defaultdict(Counter)
    mid: dict[tuple, Counter] = defaultdict(Counter)
    for dom, h, s, t, toks in tok_sents:
        on_topic = bool(qset & {lemma(w) for w in toks})
        first = toks[0] if toks else ""
        for run in _runs(toks, verbish):
            lem = [lemma(w) for w in run]
            for n in range(1, min(4, len(run)) + 1):
                for i in range(0, len(run) - n + 1):
                    k = tuple(lem[i:i + n])
                    if k[0] in SOFT or k[-1] in SOFT:
                        continue
                    tf[k] += 1
                    df[k].add(dom)
                    if n == len(run):
                        maximal[k] += 1
                    if on_topic:
                        topical[k].add(dom)
                    forms[k][" ".join(run[i:i + n])] += 1
                    if not (i == 0 and run[0] == first):
                        mid[k][" ".join(run[i:i + n])] += 1
    # aliases written in the pages: "loan to value (LTV)", "Financial Conduct Authority (FCA)"
    alias = {}
    for *_, s, t, toks in tok_sents:
        for m in re.finditer(r"((?:[A-Za-z][\w'-]*\s+){1,7})\(([A-Z]{2,6})s?\)", s):
            ac, long_w = m.group(2), [w for x in m.group(1).split() for w in x.split("-") if w]
            for n in range(len(ac) - 1, min(len(long_w), len(ac) + 3) + 1):
                cand = long_w[-n:]
                if not cand or cand[0].lower() in FUNC:
                    continue
                every = "".join(w[0].upper() for w in cand)
                content = "".join(w[0].upper() for w in cand if w.lower() not in FUNC)
                if ac in (every, content):
                    alias[(ac.lower(),)] = tuple(lemma(w) for w in join_compounds(cand, compounds))
                    break
    for ac, long_k in alias.items():  # "loan to value" never forms one noun run (split at "to"): count it directly
        if long_k in tf:
            continue
        n = len(long_k)
        for dom, h, s, t, toks in tok_sents:
            lem = [lemma(w) for w in toks]
            at = [i for i in range(len(lem) - n + 1) if tuple(lem[i:i + n]) == long_k]
            if at:
                tf[long_k] += len(at)
                maximal[long_k] += len(at)
                df[long_k].add(dom)
                topical[long_k].add(dom)
                forms[long_k][" ".join(toks[at[0]:at[0] + n])] += len(at)
    surface_last = {k: f.most_common(1)[0][0].split()[-1] for k, f in forms.items() if f}
    surface_first = {k: f.most_common(1)[0][0].split()[0] for k, f in forms.items() if f}

    def ok_name(k, last_surface=None):
        if all(w in GENERIC or w in FUNC or w.isdigit() for w in k) or len(" ".join(k)) <= 2:
            return False
        last, first = last_surface or surface_last.get(k, k[-1]), surface_first.get(k, k[0])
        if len(k) == 1 and (last.lower() in verbish or len(k[0]) < 4 and k[0] not in acronyms):
            return False  # "funds" is a thing even where "fund" is also a verb
        if not nounish(last) and "-" not in last:
            return False  # a name ends in a noun: "flexible", "required" are not things
        if len(k) > 1 and pos and pos.get(first.lower()) in ("VERB", "ADV", "PRON", "DET", "AUX") \
                and not first.lower().endswith(("ing", "ed")):
            return False
        return True
    # 4. keep names several sites use near the topic, that stand on their own (not only inside a longer name)
    keep = {}
    for k, n in tf.items():
        if not ok_name(k) or len(df[k]) < 2 or not topical[k]:
            continue
        if maximal[k] < max(2, 0.25 * n) and k not in alias.values():
            continue  # "charge bridging" only ever appears inside "second charge bridging loan"
        keep[k] = n
    for ac, long_k in alias.items():
        if (long_k in keep or ac in keep) and long_k in tf:
            keep[long_k] = keep.get(long_k, 0) + keep.get(ac, 0) or tf[long_k]
            df[long_k] |= df.get(ac, set())
    # the topic itself is always the central entity, under the name the query uses
    central = tuple(qlem) if qlem else ()
    qruns = [tuple(lemma(w) for w in r) for r in _runs([w for w in words(query) if not places(w)], verbish)]
    qruns = [r for r in qruns if r and ok_name(r)]
    if len(qruns) > 1 or (qruns and qruns[0] != central):
        central = max(qruns, key=lambda r: (tf.get(r, 0) * len(df.get(r, ())), len(r)))
    if central:
        keep[central] = max(keep.get(central, 0), tf.get(central, 0), 1)
        if central not in forms:
            forms[central][" ".join(w for w in words(query) if lemma(w) in central)] += 1
    srch_lem = [[lemma(w) for w in words(q)] for q in (searches or [])]

    def searched(k):
        n = len(k)
        return sum(1 for ql in srch_lem if any(tuple(ql[i:i + n]) == k for i in range(len(ql) - n + 1)))
    head_lem = {d: [[lemma(w) for w in words(h)] for h in hs] for d, hs in heads_by_dom.items()}

    def in_heads(k):
        n = len(k)
        return sum(1 for d, hl in head_lem.items() if any(any(tuple(x[i:i + n]) == k for i in range(len(x) - n + 1)) for x in hl))
    sc = {k: 3 * len(df.get(k, ())) / n_pages + math.log1p(keep[k]) + 1.5 * min(3, searched(k))
          + 0.8 * min(3, in_heads(k)) + 0.4 * (len(k) - 1) for k in keep}
    ranked = sorted(keep, key=lambda k: (k != central, -sc[k]))[:90]
    acr_of = {long_k: ac for ac, long_k in alias.items() if long_k in ranked}
    ranked = [k for k in ranked if not (k in alias and alias[k] in ranked)]

    def display(k):
        f = forms.get(k)
        if not f:
            return " ".join(k)
        name = f.most_common(1)[0][0]
        m = mid.get(k) or Counter()
        caps = sum(n for s, n in m.items() if s[:1].isupper()) / sum(m.values()) if sum(m.values()) >= 2 else 0
        return name if caps >= 0.7 or name.isupper() else name.lower()
    keys = {k: " ".join(k) for k in ranked}
    for long_k, ac in acr_of.items():
        keys[ac] = " ".join(long_k)
    matcher = Matcher(keys)
    ent = {" ".join(k): {"key": " ".join(k), "name": display(k), "tokens": list(k),
                         "aliases": [acr_of[k][0].upper()] if k in acr_of else [],
                         "domains": sorted(df.get(k, ())), "mentions": tf.get(k, 0) + (tf.get(acr_of[k], 0) if k in acr_of else 0),
                         "searched": searched(k) + (searched(acr_of[k]) if k in acr_of else 0),
                         "in_headings": in_heads(k), "type": None, "label": labels.get(" ".join(k)),
                         "definition": None, "attributes": {}} for k in ranked}
    ck = " ".join(central)
    head = central[-1:] if central else ()

    def is_kind(k):  # "first charge bridging loan" on a "second charge bridging loan" page: same head, its own name
        kt = tuple(k.split())
        return bool(head) and kt[-1:] == head and len(kt) > 1 and k != ck

    def agent(k):  # "lender", "broker": an agent noun the pages show acting ("lenders can", "brokers charge")
        last = k.split()[-1]
        if not (last.endswith(AGENT_SUFFIX) and last not in NOT_AGENT and len(last) >= 5):
            return False
        stem = re.sub(r"(er|or|ee|ist|ian|ant)$", "", last)
        from_verb = any(verb_base(x) or x in verbish or pos.get(x) == "VERB"
                        for x in (stem, stem + "e", stem[:-1] if len(stem) > 3 and stem[-1] == stem[-2] else stem))
        return from_verb and acts[last] >= max(2, 0.12 * ltotal[last])
    # 5. attribute values: a figure, the measure it is a value of, the entity it belongs to, the sites that state it
    raw_vals, unnamed = [], []
    for dom, h, s, t, toks in tok_sents:
        # on topic: names the topic or one of its entities, sits under a heading that does, or is a list or table row
        if not (qset & {lemma(w) for w in toks + words(h)}) and not matcher.find(toks) and ":" not in s \
                and t not in ("li", "td", "tr", "dd"):
            continue
        # "between £50k and £750k", "from £25,000 up to £500,000", "60 %-75 %": one range, not two figures
        sf = RANGE_JOIN.sub(r"\1 to ", s)
        for m in FIG.finditer(sf):
            if not m.group(2) or not (m.group(1) or m.group(3) or m.group(7) or "%" in m.group(0)):
                continue
            if re.fullmatch(r"(19|20)\d\d", m.group(2)) and not m.group(7):
                continue  # a year
            if re.fullmatch(r"0+(\.0+)?", m.group(2)) and not m.group(5):
                continue  # "0 %": a counter the page fills in with script
            before, after = sf[:m.start()], sf[m.end():]
            q = _qualifier(before, bool(m.group(5)))
            kind = value_kind(m)
            val = re.sub(r"\s+", " ", m.group(0)).strip()
            tail = re.match(r"\s*((?:per|a|an|each|every|of)\s+(?:the\s+|your\s+|a\s+|its\s+)?[a-z][a-z'-]*"
                            r"(?:\s+(?!(?:of|the|on|in|for|to|and|or|with|at|by|a|an|is|are|so|if)\b)[a-z][a-z'-]*){0,2})",
                            after, re.I)
            if tail and not re.search(r"\b(and|or|but|which|that|if|you|we|so|to)\b", tail.group(1), re.I):
                val += " " + tail.group(1).strip()
            attr = None
            # (1) a label: "Loan Term: 1 to 18 months", "LTV limits: commonly capped at 60-75%"
            lab = re.search(r"([A-Za-z][A-Za-z' -]{2,40}):\s*[^:]*$", before)
            if lab:
                lw = [w for w in words(lab.group(1)) if w.lower() not in FUNC][-4:]
                cand = tuple(lemma(w) for w in lw)
                while cand and cand[0] in SOFT:
                    cand = cand[1:]
                if cand and ok_name(cand) or (len(cand) == 1 and cand[0] in acronyms):
                    attr = " ".join(cand)
            # (2) the measure named before the figure, with only verbs and linking words between them: "Terms from
            # 3 to 24 months", "discharge fee of £245", "a decision will usually be made within 24 hours"
            core = _strip_qual(before)
            bt = join_compounds(words(core), compounds)[-6:]
            if attr is None and bt:
                def linking(ws):
                    return all(w.lower() in FUNC or w.lower() in SOFT or w.lower() in verbish or verb_base(w)
                               or w.lower().endswith("ed") for w in ws)
                hits = [x for x in matcher.find(bt) if x[2] != ck and not agent(x[2]) and linking(bt[x[1]:])]
                if hits:
                    attr = hits[-1][2]
                else:
                    for run in reversed(_runs(bt, verbish)):
                        end = max(i for i, w in enumerate(bt) if w == run[-1]) + 1
                        cand = tuple(lemma(w) for w in run[-3:])
                        if linking(bt[end:]) and ok_name(cand, run[-1]) and not agent(" ".join(cand)) \
                                and " ".join(cand) != ck:
                            attr = " ".join(cand)
                        break
            # (3) the measure named right after it: "up to 75% loan to value"
            if attr is None:
                at = join_compounds(words(after), compounds)[:4]
                ah = matcher.find(at)
                if ah and ah[0][0] == 0 and ah[0][2] != ck and not agent(ah[0][2]):
                    attr = ah[0][2]
            # (4) a share of something: "75% of the property value"
            if attr is None and kind == "percent" and tail and tail.group(1).lower().startswith("of"):
                of = [w for w in words(tail.group(1))[1:] if w.lower() not in FUNC]
                if of:
                    attr = "% of " + " ".join(lemma(w) for w in of)
            # (5) a rate: "1.5% per month", "£50 a week"
            per = re.match(r"(?i)\s*(?:per|a|an|each|every)\s+(day|week|month|year|annum|hour)\b", after)
            if attr is None and per and kind in ("percent", "money"):
                attr = ("rate per " if kind == "percent" else "cost per ") + per.group(1).lower().replace("annum", "year")
            # (6) what the reader does with it: "borrow between £50k and £750k", "access from £5,000"
            if attr is None:
                vb = next((verb_base(w) for w in reversed(bt) if verb_base(w) and verb_base(w) not in
                           ("be", "have", "become", "get", "make", "take", "help", "work")), None)
                if vb:
                    attr = {"money": f"{vb} amount", "duration": f"time to {vb}", "percent": f"{vb} share"}.get(kind)
            if attr is None:
                unnamed.append((dom, val, s[:160]))
                continue
            owner = ck
            for i0, i1, k in matcher.find(toks):
                if k != attr and is_kind(k):
                    owner = k  # "first charge loans go up to 80%": the value belongs to that kind
                    break
            raw_vals.append((owner, attr, kind, val, q, dom, s))
    groups = defaultdict(lambda: defaultdict(lambda: {"domains": set(), "qualifier": Counter(), "example": None}))
    for owner, attr, kind, val, q, dom, s in raw_vals:
        v = groups[(owner, attr, kind)][re.sub(r"\s+", "", val.lower()).replace("percent", "%").replace("percent", "%")]
        v["domains"].add(dom)
        v["qualifier"][q] += 1
        v["example"] = v["example"] or {"sentence": s[:240], "source": dom, "value": val}
    # one measure, several names: "term" and "loan term" (same kind of value) are one attribute
    names = sorted(groups, key=lambda g: (-len({d for v in groups[g].values() for d in v["domains"]}), len(g[1])))
    merged = {}

    def content_set(name):  # "% of value" and "loan-to-value" share "value": both are a share of the property value
        return {w for w in re.split(r"[\s-]+", name) if w and w not in FUNC and w != "%"}
    for g in names:
        gt = content_set(g[1])
        tgt = next((m for m in merged if m[0] == g[0] and m[2] == g[2] and gt and content_set(m[1]) and
                    (gt <= content_set(m[1]) or content_set(m[1]) <= gt or
                     ("% of " in g[1] + m[1] and re.split(r"[\s-]+", g[1])[-1] == re.split(r"[\s-]+", m[1])[-1]))), None)
        merged.setdefault(tgt or g, []).append(g)
    attributes = []
    for top, members in merged.items():
        vs = defaultdict(lambda: {"domains": set(), "qualifier": Counter(), "example": None})
        for g in members:
            for k, v in groups[g].items():
                vs[k]["domains"] |= v["domains"]
                vs[k]["qualifier"] += v["qualifier"]
                vs[k]["example"] = vs[k]["example"] or v["example"]
        rows = sorted(({"value": x["example"]["value"], "qualifier": x["qualifier"].most_common(1)[0][0],
                        "domains": sorted(x["domains"]), "example": x["example"]} for x in vs.values()),
                      key=lambda r: -len(r["domains"]))
        sites = {d for r in rows for d in r["domains"]}
        if len(sites) < 2:
            continue  # one site's numbers are leads for the fact-check, not the topic's graph
        owner, attr, kind = top
        aname = ent[attr]["name"] if attr in ent else attr
        if not MEASURE_WORD.search(aname):  # "loan" with a money value is the loan amount; "funds" in hours, a time
            aname += {"money": " (amount)", "duration": " (time)", "percent": " (%)"}.get(kind, "")
        attributes.append({"entity": owner, "attribute": attr, "attribute_name": aname, "kind": kind,
                           "also_called": sorted({g[1] for g in members} - {attr}),
                           "values": rows[:6], "sites": len(sites),
                           "differs": len({r["value"].lower() for r in rows if r["qualifier"] == "max"}) >= 2})
    attributes.sort(key=lambda a: (-a["sites"], a["attribute"]))
    for a in attributes:
        if a["entity"] in ent:
            ent[a["entity"]]["attributes"][a["attribute_name"]] = a["values"][:4]
        if a["attribute"] in ent and tuple(a["attribute"].split()) != head:  # "loan" on a loan page stays a thing
            ent[a["attribute"]]["type"] = "measure"
    # 6. relationships: two entities and the verb phrase between them, in one clause; and definitions
    def bare(toks, a0):  # the entity is the whole subject: nothing qualifies it from the left
        return a0 == 0 or toks[a0 - 1].lower() in FUNC - {"of"} and toks[a0 - 1].lower() != "of"

    rel = defaultdict(lambda: {"domains": set(), "examples": []})
    defs = defaultdict(list)
    for dom, h, s, t, toks in tok_sents:
        if len(toks) > 45 or s.rstrip().endswith("?"):
            continue
        hits = matcher.find(toks)
        lw = [w.lower() for w in toks]
        if hits and len(toks) >= 8 and (hits[0][0] == 0 or (hits[0][0] == 1 and lw[0] in ("a", "an", "the"))):
            nxt = lw[hits[0][1]:hits[0][1] + 2] + ["", ""]
            if nxt[0] in ("means", "describes") or nxt[:2] == ["refers", "to"] or \
                    (nxt[0] in ("is", "are") and nxt[1] in ("a", "an", "the", "one", "when", "where", "used", "defined",
                                                             "known", "essentially", "simply", "basically", "typically",
                                                             "usually", "generally", "any")):
                if len(hits) >= 2 or any(lemma(w) in qset for w in toks[hits[0][1]:]):
                    defs[hits[0][2]].append((dom, s[:300]))
        for (a0, a1, ka), (b0, b1, kb) in zip(hits, hits[1:]):
            if ka == kb or not 1 <= b0 - a1 <= 6 or not bare(toks, a0):
                continue
            gap = toks[a1:b0]
            gl = [w.lower() for w in gap]
            if any(w in PRONOUNS or w in ("which", "who", "whereas", "while", "but", "if", "when", "because", "and",
                                          "or", "where", "so") for w in gl):
                continue
            if gl[0] in ("to", "whether", "than", "as") or "whether" in gl:
                continue  # a purpose or comparison clause, not a link between the two
            if not all(w in FUNC or w in REL_EXTRA or verb_base(w) or w.endswith("ed") for w in gl):
                continue  # a noun in between: the two entities are not what the clause links
            if not any(verb_base(w) or w.endswith("ed") for w in gl):
                continue
            link = [toks[a1 - 1]] + gap + [toks[b0]]
            if not re.search(r"(?<![\w-])" + r"[\s-]+".join(map(re.escape, link)) + r"(?![\w-])", s):
                continue  # punctuation between them: two clauses
            pred = [w for w in gl if w not in SOFT - {"not", "no", "never", "only"} and w not in ("a", "an", "the")]
            if not pred:
                continue
            key_p = " ".join(verb_base(w) or w for w in pred)
            r = rel[(ka, key_p, kb)]
            r["domains"].add(dom)
            if len(r["examples"]) < 2 and all(e["source"] != dom for e in r["examples"]):
                r["examples"].append({"s": ent[ka]["name"], "p": " ".join(pred), "o": ent[kb]["name"],
                                      "sentence": s[:240], "source": dom})
    top = {e for e in list(ent)[:40]} | {ck}
    for dom, h, s, t, toks in tok_sents:
        if len(toks) > 45 or s.rstrip().endswith("?"):
            continue
        hits = matcher.find(toks)
        starts = {x[0] for x in hits}
        for a0, a1, ka in hits:
            if ka not in top or not bare(toks, a0):
                continue
            j, gap = a1, []
            while j < len(toks) and len(gap) < 5 and (toks[j].lower() in FUNC or toks[j].lower() in REL_EXTRA
                                                      or verb_base(toks[j]) or toks[j].lower().endswith("ed")):
                gap.append(toks[j])
                j += 1
            gl = [w.lower() for w in gap]
            if not gap or j in starts or not any(verb_base(w) or w.endswith("ed") for w in gl) \
                    or any(w in PRONOUNS or w in ("which", "who", "if", "when", "because", "and", "or", "but", "to")
                           for w in gl[:1] + [w for w in gl if w in PRONOUNS]):
                continue
            run = []
            while j < len(toks) and len(run) < 3 and toks[j].lower() not in FUNC and toks[j].lower() not in verbish \
                    and "'" not in toks[j]:
                run.append(toks[j])
                j += 1
            while run and run[0].lower() in SOFT:
                run = run[1:]
            ok_ = tuple(lemma(w) for w in run)
            if not run or not ok_name(ok_, run[-1]) or " ".join(ok_) == ka:
                continue
            link = [toks[a1 - 1]] + gap + [run[0]]
            if not re.search(r"(?<![\w-])" + r"[\s-]+".join(map(re.escape, link)) + r"(?![\w-])", s):
                continue
            pred = [w for w in gl if w not in SOFT - {"not", "no", "never", "only"} and w not in ("a", "an", "the")]
            if not pred:
                continue
            kb = "~" + " ".join(ok_)
            r = rel[(ka, " ".join(verb_base(w) or w for w in pred), kb)]
            r["domains"].add(dom)
            if len(r["examples"]) < 2 and all(e["source"] != dom for e in r["examples"]):
                r["examples"].append({"s": ent[ka]["name"], "p": " ".join(pred), "o": " ".join(run).lower()
                                      if not run[0].isupper() else " ".join(run), "sentence": s[:240], "source": dom})
    relations = []
    per_dom = Counter()
    for (ka, p, kb), r in sorted(rel.items(), key=lambda kv: -len(kv[1]["domains"])):
        n = len(r["domains"])
        ex = r["examples"][0]
        if n < 2:
            # one site's link: kept when it is specific (a number, a named body) or touches the topic itself
            if per_dom[ex["source"]] >= 6 or not (re.search(r"\d|[A-Z]{2,}", ex["sentence"]) or ck in (ka, kb)
                                                   or is_kind(ka) or is_kind(kb)):
                continue
            per_dom[ex["source"]] += 1
        relations.append({"subject": ka, "predicate": ex["p"], "object": kb, "domains": sorted(r["domains"]),
                          "consensus": n >= 2, "example": ex})
    relations = relations[:90]
    for k, ds in defs.items():
        seen, uniq = set(), []
        for dom, s in ds:
            if dom not in seen:
                seen.add(dom)
                uniq.append((dom, s))
        bag = [set(lemma(w) for w in words(s)) - FUNC for _, s in uniq]
        best = max(range(len(uniq)), key=lambda i: (sum(len(bag[i] & b) / max(1, len(bag[i] | b)) for b in bag), -len(uniq[i][1])))
        ent[k]["definition"] = {"text": uniq[best][1], "source": uniq[best][0], "sites": len(uniq)}
    # 7. types: what kind of thing each entity is (labels for the writer, not facts)
    for r in relations:
        if re.fullmatch(r"(is|are)( (a|an))?( (type|form|kind|sort) of)?", r["predicate"]):
            if r["object"] == ck:
                ent[r["subject"]]["type"] = ent[r["subject"]]["type"] or "kind"
            elif r["subject"] == ck and r["object"] in ent:
                ent[r["object"]]["type"] = ent[r["object"]]["type"] or "broader class"
    for k, e in ent.items():
        kt = tuple(e["tokens"])
        proper = e["name"][:1].isupper() or e["name"].isupper()
        if k == ck:
            e["type"] = "central"
        elif e["type"]:
            pass
        elif is_kind(k):
            e["type"] = "kind"
        elif places(e["name"]):
            e["type"] = "place"
        elif (proper and e["label"] == "LAW") or kt[-1] in RULE_WORDS:
            e["type"] = "rule or document"
        elif proper and e["label"] == "PERSON":
            e["type"] = "person"
        elif proper and (e["label"] in ("ORG", "PRODUCT") or len(kt) >= 2 or e["name"].isupper()):
            e["type"] = "organisation or named thing"
        elif agent(k):
            e["type"] = "party"
        else:
            e["type"] = "concept"
    entities = sorted(ent.values(), key=lambda e: (e["type"] != "central", -sc[tuple(e["tokens"])]))
    return {"central": ck, "pages": n_pages, "market": home_geo, "entities": entities, "attributes": attributes,
            "relations": relations, "sentences": len(sents), "dropped_foreign_sentences": dropped_foreign,
            "spacy": bool(pos), "foreign_pages": foreign_pages, "unnamed_figures": unnamed[:60]}


def join_compounds(toks: list[str], compounds: set[tuple]) -> list[str]:
    out, i = [], 0
    while i < len(toks):
        for c in compounds:
            n = len(c)
            if tuple(w.lower() for w in toks[i:i + n]) == c:
                out.append("-".join(toks[i:i + n]))
                i += n
                break
        else:
            out.append(toks[i])
            i += 1
    return out


def _runs(toks: list[str], verbish: set[str]) -> list[list[str]]:
    """Maximal noun-like runs: split at function words, verbs and adverbs; soft modifiers trimmed at the edges."""
    runs, cur = [], []
    for t in toks:
        lw = t.lower()
        if lw in FUNC or lw in verbish or (lw.endswith("ly") and len(lw) > 4) or "'" in lw:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        runs.append(cur)
    out = []
    for r in runs:
        while r and r[0].lower() in SOFT:
            r = r[1:]
        while r and r[-1].lower() in SOFT:
            r = r[:-1]
        if r:
            out.append(r)
    return out
