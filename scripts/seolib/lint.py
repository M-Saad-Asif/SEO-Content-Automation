"""Step 4: deterministic lint of draft.md against RULES.md and the fact sheet.

Each finding: rule, severity (block|warn), line, section, text, reason, fix.
`block` findings must be fixed before validate passes. `warn` findings are
semantic flags (dangling openers, vague "This", noun stacks): rewrite them
when the rule truly applies, leave them when the sentence is already clear.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from . import common as C
from .nlp import places, tokens

USABLE = {"verified", "captured", "operator"}
# Page-one points (plugins/serp_facts) support what a sentence says (its numbers, rules, terms), the way verified
# facts do; they never make a competitor page a citation or link target, so link rules keep USABLE.
SUPPORT = USABLE | {"serp"}
UNIT = r"(?:cm|mm|kg|g|in(?:ch(?:es)?)?|%|p\b|pence|days?|working days|hours?|minutes?|mins?|weeks?|months?|years?|litres?|l\b|ml)"
STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being it its this that these
those you your we our they their them he she his her i me my not no do does did can could will would should may might must
than then so such into over under up down out about after before between per via each any all more most less few very also just
only there here what which who whom whose when where why how""".split())
SERVICE_VERBS = r"\b(offer|offers|provide|provides|process|processes|handle|handles|help|helps|support|supports|escalate|escalates|audit|audits|guarantee|guarantees|liaise|liaises|secure|secures|fast-track|fast-tracks|expedite|expedites|deliver|delivers|ship|ships|check|checks|review|reviews|track|tracks|apply|applies|submit|submits|manage|manages|arrange|arranges|can)\b"
POSITION_VERBS = r"(design|designs|designed|manufacture|manufactures|manufactured|make|makes|made|craft|crafts|crafted|create|creates|created|build|builds|built|produce|produces|produced)"
ING_OK = {"during", "according", "including", "following", "regarding", "depending", "assuming", "excluding",
          "starting", "beginning", "something", "nothing", "anything", "everything", "morning", "evening",
          "spring", "string", "king", "thing", "sibling", "ceiling", "pudding", "wedding", "building",
          "clothing", "booking", "pricing", "shipping", "parking", "lining", "opening", "outstanding",
          "training", "funding", "housing", "heating", "lighting", "flooring", "roofing", "plumbing", "seating",
          "setting", "meeting", "heading", "landing", "missing", "remaining", "existing", "pending",
          "upcoming", "ongoing", "something's", "anything's"}
ABBR = re.compile(r"\b(e\.g|i\.e|etc|approx|vs|no|incl|max|min|dept|st|mr|mrs|ms|dr|u\.s|u\.k)\.$", re.I)


# ---------------------------------------------------------------- markdown

def strip_md(s: str) -> str:
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"(\*\*|__|\*|_|`)", "", s)
    return C.collapse(s)


def parse_md(md: str) -> tuple[dict, list[dict]]:
    meta = {}
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        j = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        if j:
            for ln in lines[1:j]:
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip('"').strip("'")
            i = j + 1
    blocks, section, sec_title, para = [], 0, "(intro)", []
    in_table = False

    def flush(end_line):
        nonlocal para
        if para:
            text = " ".join(x for _, x in para)
            blocks.append({"type": "p", "line": para[0][0], "raw": text, "text": strip_md(text),
                           "section": section, "section_title": sec_title})
            para = []

    for n in range(i, len(lines)):
        ln = lines[n]
        s = ln.strip()
        ln_no = n + 1
        if not s:
            flush(ln_no)
            in_table = False
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush(ln_no)
            lvl = len(m.group(1))
            if lvl == 2:
                section += 1
                sec_title = strip_md(m.group(2))
            blocks.append({"type": f"h{lvl}", "line": ln_no, "raw": m.group(2), "text": strip_md(m.group(2)),
                           "section": section, "section_title": sec_title})
            continue
        if s.startswith("|"):
            flush(ln_no)
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            blocks.append({"type": "tr", "line": ln_no, "raw": s, "cells": cells, "text": " | ".join(strip_md(c) for c in cells),
                           "header": not in_table, "section": section, "section_title": sec_title})
            in_table = True
            continue
        m = re.match(r"^([-*+]|\d+[.)])\s+(.*)$", s)
        if m:
            flush(ln_no)
            blocks.append({"type": "li", "line": ln_no, "raw": m.group(2), "text": strip_md(m.group(2)),
                           "ordered": m.group(1)[0].isdigit(), "section": section, "section_title": sec_title})
            continue
        if s.startswith(">"):
            s = s.lstrip("> ")
        para.append((ln_no, s))
    flush(len(lines))
    return meta, blocks


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])[\"”’)]?\s+(?=[A-Z0-9\"“(£$€]|[a-z]+[A-Z])", text)
    out, buf = [], ""
    for p in parts:
        buf = (buf + " " + p).strip() if buf else p
        if ABBR.search(buf):
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)
    final = []
    for x in out:
        pieces = re.split(r"(?<=[a-z0-9)%]\.)\s+(?=[a-z][a-z0-9.]{2,}\b)", x)
        acc = ""
        for pc in pieces:
            acc = (acc + " " + pc).strip() if acc else pc
            if len(acc.split()) >= 5 and not ABBR.search(acc):
                final.append(acc)
                acc = ""
        if acc:
            if final and len(acc.split()) < 5:
                final[-1] = final[-1] + " " + acc
            else:
                final.append(acc)
    return [s for s in (x.strip() for x in final) if s]


def words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9£$€][A-Za-z0-9£$€%'’.\-]*", s)


def unquote(s: str) -> str:
    return re.sub(r"[\"“][^\"”]{1,400}[\"”]", " ", s)


# ---------------------------------------------------------------- numbers

NUM = re.compile(r"(?<![\w.])([£$€])?\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:\s?(" + UNIT + r"))?", re.I)
TRIPLE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:cm)?\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:cm)?\s*[x×]\s*(\d+(?:\.\d+)?)", re.I)


def _f(x: str) -> float:
    return float(x.replace(",", ""))


def allowed_numbers(sheet: dict, research: dict | None = None) -> tuple[set, set, set, set]:
    nums, triples, money, prices = set(), set(), set(), set()

    def take(s, is_price=False):
        if not s:
            return
        s = str(s)
        for t in TRIPLE.findall(s):
            triples.add(tuple(sorted((_f(a) for a in t), reverse=True)))
        for cur, n, unit in NUM.findall(s):
            v = _f(n)
            nums.add(v)
            if cur:
                (prices if is_price else money).add((cur, v))
    for f in sheet.get("facts", []):
        if f.get("status") not in SUPPORT:
            continue
        is_price = f.get("kind") == "price"
        for k in ("value", "condition"):
            take(f.get(k), is_price)
        if f.get("basis") in ("script_fetch", "agent_capture", "official_page_auto"):
            take(f.get("claim"), is_price)
        for a in f.get("also") or []:
            take(a)
        for n in f.get("numbers") or []:
            nums.add(float(n))
    for p in sheet.get("products", []):
        if p.get("dims"):
            triples.add(tuple(sorted(p["dims"]["cm"], reverse=True)))
            nums.update(p["dims"]["cm"])
        take(p.get("description"))
    for c in sheet.get("client", {}).get("approved_claims", []):
        if c.get("seen_on_site", True):
            take(c["text"])
    for c in sheet.get("client", {}).get("facts", []):
        take(c)
    for res in (sheet.get("checks") or {}).values():
        for r in (res or {}).get("results", []):
            nums.update(r.get("bag_cm", []))
            nums.update(r.get("limit_cm", []))
            nums.update(abs(m) for m in r.get("margins_sorted_cm", []))
            triples.add(tuple(sorted(r.get("bag_cm", []), reverse=True)))
            triples.add(tuple(sorted(r.get("limit_cm", []), reverse=True)))
    for f in sheet.get("facts", []):
        for k in ("retrieved_at",):
            if f.get(k):
                nums.add(float(str(f[k])[:4]))
    nums.add(float(str(sheet.get("generated_at", "2026"))[:4]))
    # Non-YMYL pages may use a competitor number when 3+ independent domains state it.
    if research and sheet.get("brief", {}).get("ymyl") is not True:
        for rows in (research.get("semantic_graph") or {}).get("attributes", {}).values():
            for r in rows:
                if len(r.get("domains", [])) >= 3:
                    take(r["value"])
        for r in (research.get("semantic_graph") or {}).get("consensus_figures", []):
            for n in re.findall(r"\d+(?:\.\d+)?", r["figure"]):
                nums.add(float(n))
    return nums, triples, money, prices


_NLP = None


def _worked(s: str, v: float, nums: set) -> bool:
    """True when the sentence shows the sum that produces v from numbers in it, at least one of them sourced:
    "£80 plus the £20 top-up makes £100", "0.75 g × 60 kg = 45 g"."""
    if not re.search(r"[×x*/=+−]|\b(plus|minus|times|multiplied by|divided by|makes|equals|comes to|works out)\b", s):
        return False
    vals = [_f(n) for _, n, _ in NUM.findall(s)]
    if not any(x in nums for x in vals):
        return False
    for i, a in enumerate(vals):
        for c in vals[i + 1:] + vals[:i]:
            for r in (a + c, a - c, c - a, a * c, a / c if c else None, c / a if a else None):
                if r is not None and v and abs(r - v) <= 0.011 * abs(v):
                    return True
    return v in vals and any(abs(x * y - v) <= 0.011 * abs(v) or abs(x + y - v) <= 0.011 * abs(v)
                             for x in vals for y in vals if x is not y)


def _derived(v: float, ctx: str, nums: set) -> bool:
    """True when v takes part in a sum the paragraph itself carries, with at least one sourced number in it:
    "a 10 kg dog needs about 600 g, so two meals of 300 g" (600 / 2), or a worked row "80 kg | 60 g" from a
    sourced 0.75 g per kg. Either v is the result of two of the paragraph's numbers, or v and another number
    produce a third one."""
    vals = list(dict.fromkeys(_f(n) for _, n, _ in NUM.findall(ctx)))
    words_n = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
               "twice": 2, "double": 2, "half": 0.5, "triple": 3}
    vals += [float(words_n[w.lower()]) for w in re.findall(r"\b(" + "|".join(words_n) + r")\b", ctx, re.I)]
    if not any(x in nums for x in vals):
        return False

    pcts = [_f(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|per ?cent)", ctx)]

    def ops(a, c):
        base = [a + c, a - c, c - a, a * c, a * c / 100, a * c / 1000] + ([a / c] if c else []) + ([c / a] if a else [])
        return base + [a * (1 - q / 100) for q in pcts] + [a * (1 + q / 100) for q in pcts]

    def near(r, w):
        if not w:
            return False
        tol = 0.011 * abs(w)
        if w != int(w):
            tol = max(tol, 0.051)  # shown to one decimal place
        elif abs(w) >= 10:
            tol = max(tol, 0.5)  # rounded to a whole number
        return abs(r - w) <= tol
    others = [x for x in vals if x != v]
    if re.search(re.escape(f"{v:g}") + r"\s*(%|per ?cent)", ctx):
        for i, a in enumerate(others):
            for c in others:
                if c is a or not c:
                    continue
                for r in (a / c * 100, (a - c) / a * 100 if a else 0, (c - a) / c * 100):
                    if r and abs(r - v) <= max(0.6, 0.011 * v):
                        return True
    for a in others:  # "drops by 10%": 800 g becomes 720 g
        if any(abs(a * (1 - q / 100) - v) <= 0.011 * v or abs(a * (1 + q / 100) - v) <= 0.011 * v for q in pcts):
            return True
    if v and v % 5 == 0 and re.search(r"\b(about|around|roughly|approximately|nearly|almost|just over|just under)\s+"
                                      + re.escape(f"{v:g}"), ctx):
        if any(abs(v - x) <= 0.1 * x for x in others):
            return True  # a rounded figure of a number the paragraph carries
    for i, a in enumerate(others):
        for c in others[i + 1:]:
            if (a in nums or c in nums) and any(near(r, v) for r in ops(a, c)):
                return True
    for c in others:
        for w in others:
            if w != c and (c in nums or w in nums) and any(near(r, w) for r in ops(v, c)):
                return True
    return False


def _has_finite(clause: str) -> bool:
    """'Eating 100 g of protein a day sits within …': a finite verb before the first comma means the -ing phrase
    is the subject, not a dangling modifier."""
    global _NLP
    try:
        if _NLP is None:
            from .nlp import import_spacy
            _NLP = import_spacy().load("en_core_web_sm", disable=["ner"])
        return any(tk.tag_ in ("VBZ", "VBP", "VBD", "MD") for tk in _NLP(clause)[1:])
    except Exception:
        return False


def _base_verb_first(s: str) -> bool:
    """"Feed for…", "Need help…": a bare verb starts an instruction (spaCy tag VB)."""
    global _NLP
    try:
        if _NLP is None:
            from .nlp import import_spacy
            _NLP = import_spacy().load("en_core_web_sm", disable=["ner"])
        d = _NLP(s[:80])
        return len(d) > 1 and d[0].tag_ in ("VB", "VBP")
    except Exception:
        return s.split()[0].lower() in ("feed", "need", "seed", "speed", "breed", "shed", "bleed", "heed", "weed")


def _gerund_subject(s: str) -> bool:
    """'Applying early leaves room…' uses the -ing phrase as the subject: nothing dangles. Needs spaCy; without it,
    fall back to the regex verdict."""
    global _NLP
    try:
        if _NLP is None:
            from .nlp import import_spacy
            _NLP = import_spacy().load("en_core_web_sm", disable=["ner"])
        d = _NLP(s)
    except Exception:
        return False
    t = d[0]
    return t.dep_ in ("csubj", "csubjpass", "nsubj", "nsubjpass") or (t.head.dep_ in ("csubj", "csubjpass") and t.head.i < 4)


def human_paras(page: dict) -> list[str]:
    """A ranking page's prose paragraphs: 3+ words ending like a sentence (drops buttons, captions, UI text but
    keeps the short paragraphs real writers use, so short-sentence shares compare fairly)."""
    return [x for t, x in page.get("blocks", []) if t == "p" and len(x.split()) >= 3
            and re.search(r"[.?!:][\"”)]?$", x.strip())]


def human_stats(research: dict) -> dict:
    """Medians over the ranking pages with real prose (15+ sentences; parse-artifact sentences over 50 words
    dropped): sentence-length SD and share of sentences under 8 words. Lint and eval both use this."""
    import statistics as st
    sds, shorts = [], []
    for p in (research.get("competitor_scrape") or {}).get("pages", []):
        ls = [n for x in human_paras(p) for n in (len(words(s)) for s in sentences(x)) if n <= 50]
        if len(ls) >= 15:
            sds.append(st.pstdev(ls))
            shorts.append(sum(1 for n in ls if n < 8) / len(ls))
    return {"sd": round(st.median(sds), 2) if sds else None, "short": round(st.median(shorts), 3) if shorts else None}


def human_rhythm(research: dict) -> float | None:
    return human_stats(research)["sd"]


def short_target(research: dict) -> float:
    """Most sentences under 8 words a page may have before it reads as clipped, fragment-led copy."""
    h = human_stats(research)["short"]
    return round(max(0.12, 1.6 * h), 2) if h is not None else 0.12


def rhythm_target(research: dict) -> float:
    h = human_rhythm(research)
    return round(max(6.0, 0.8 * h), 1) if h else 6.0


def load_research(rd) -> dict:
    from pathlib import Path
    d = Path(rd) / "research"
    return {p.stem: C.load_json(p) for p in d.glob("*.json")} if d.exists() else {}


# ---------------------------------------------------------------- lint

class Linter:
    def __init__(self, md: str, sheet: dict, link_map: dict, research: dict | None = None):
        self.md = md
        self.sheet = sheet
        self.research = research or {}
        self.lm = link_map or {}
        self.b = sheet.get("brief", {})
        self.lex = C.lexicon()
        self.meta, self.blocks = parse_md(md)
        self.findings: list[dict] = []
        self.fact_text = " ".join(str(f.get("value", "")) + " " + str(f.get("condition", ""))
                                  for f in sheet.get("facts", []) if f.get("status") in SUPPORT).lower()
        self.fact_text += " " + " ".join(c["text"] for c in sheet.get("client", {}).get("approved_claims", []) if c.get("seen_on_site", True)).lower()

    def add(self, rule, sev, blk, text, reason, fix=""):
        self.findings.append({"rule": rule, "severity": sev, "line": blk.get("line") if blk else None,
                              "section": blk.get("section_title") if blk else None,
                              "text": text[:300], "reason": reason, "fix": fix})

    # units of prose: (block, sentence)
    def prose(self, include_cells=False, include_headings=False):
        for b in self.blocks:
            if b["type"] in ("p", "li"):
                for s in sentences(b["text"]):
                    yield b, s
            elif b["type"] == "tr" and include_cells:
                for c in b["cells"]:
                    yield b, strip_md(c)
            elif b["type"].startswith("h") and include_headings:
                yield b, b["text"]

    def r_page_job(self):
        """Commercial pages explain the scoped client offer and next step. Keep official obligations and
        limitations; flag duplicated competing CTAs. Informational pages have no sales quota."""
        from .pagejob import ANTI, COMMERCIAL, STEER, brand_terms, is_client_url, next_steps, offer
        pt = self.b.get("page_type") or "guide"
        commercial = pt in COMMERCIAL
        if not commercial:
            return
        sev = "block" if commercial else "warn"
        brands = brand_terms(self.sheet)
        # the brand is present by name, or in its own voice ("our rate table", "we arrange") on its own page
        brx = re.compile(r"(?i)\b(" + "|".join(re.escape(x) for x in brands) + r")\b|\b(we|we'll|we've|our|ours)\b") \
            if brands else None
        body = [b for b in self.blocks if b["type"] in ("p", "li", "tr")]
        paras = [b for b in self.blocks if b["type"] == "p"]
        if commercial and brx and paras and not any(brx.search(b["text"]) for b in paras[:2]):
            self.add("P01-brand-late", sev if pt in ("service", "location", "product") else "warn", paras[0],
                     paras[0]["text"][:120], f"a {pt} page that doesn't name {brands[0]} in its first two paragraphs: "
                     "the reader can't tell whose offer this is", f"say what {brands[0]} does about this need in the "
                                                                 "opening, with its main next step")
        links = [(b, u) for b in body for _, u in re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", b.get("raw", ""))]
        own = [(b, u) for b, u in links if is_client_url(u, self.sheet)]
        deep_own = next_steps(body, self.sheet)
        if commercial and not deep_own:
            known = bool(offer(self.sheet).get("ctas") or self.b.get("conversion_targets"))
            self.add("P02-no-client-next-step", sev if known else "warn", None, f"{len(own)} internal link(s)",
                     "the page has no identifiable client action; a general blog link is not a conversion step",
                     "use a relevant verified CTA, contact or browse target from Page job; verify a missing target before adding it")
        elif commercial and body and deep_own:
            last = body[int(len(body) * 0.7):]
            if not any(b in last for b, _ in deep_own):
                self.add("P02-no-closing-step", "warn", body[-1], body[-1]["text"][:100],
                         "the page ends without the client's next step", "close with a link to the client's next step")
        steer = {}
        for b, s in self.prose():
            external = [(a, u) for a, u in re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", b.get("raw", ""))
                        if not is_client_url(u, self.sheet)]
            named = {C.host(u) for a, u in external if a.lower() in s.lower() or C.host(u).lower() in s.lower()}
            imperative = re.search(r"(?i)^(apply|pay|book|submit|order|buy|renew|register)\b|"
                                   r"\b(you (can|should)|we recommend|remember (that |to )?)\b", s)
            obligation = re.search(r"(?i)\b(must|required|statutory|mandatory|need to|only you|personally|"
                                   r"biometrics?|identity check|identity verification)\b", s)
            if STEER.search(s) and named and imperative and not obligation:
                for destination in named:
                    steer.setdefault(destination, []).append((b, s))
        for destination, repeated in steer.items():
            for b, s in repeated[1:]:
                self.add("P03-steers-elsewhere", sev, b, s, f"repeated directions to act at {destination} "
                         f"({len(repeated)} sentences) can displace the client's offer on a {pt} page",
                         "consolidate duplicated competing CTAs; preserve distinct official obligations, limitations "
                         "and the verified direct-route disclosure")
        # whose page is it? On a commercial page one outside site named sentence after sentence, against a client
        # named once or twice, makes the page that site's guide (the visa page that was a GOV.UK manual)
        if commercial and brx and brands:
            from collections import Counter
            from urllib.parse import urlparse
            from .pagejob import external_names
            ext = Counter(urlparse(u).netloc.lower().removeprefix("www.") for _, u in links
                          if not is_client_url(u, self.sheet))
            sents = [s for _, s in self.prose()]
            mine = sum(1 for s in sents if brx.search(s))
            for d, _n in ext.most_common(2):
                rx = re.compile(r"(?i)(?<![\w.])(" + "|".join(re.escape(x) for x in external_names(d)) + r")(?![\w])")
                theirs = sum(1 for s in sents if rx.search(s))
                if theirs >= 6 and theirs > 2 * max(1, mine):
                    self.add("P05-another-sites-page", "warn", None, f"{d}: {theirs} sentences; {brands[0]}: {mine}",
                             f"the page is centred on {d} ({theirs} sentences) rather than on {brands[0]} ({mine}): it "
                             "reads as a guide to that site, not the client's page",
                             f"cite {d} where a rule or figure needs it; build the sections around what {brands[0]} "
                             "does (writer pack: Page job)")
        for b, s in self.prose(include_headings=True):
            if ANTI.search(s):
                self.add("P04-warns-off-client", "warn", b, s, "check whether this is a necessary limitation or an "
                         "unhelpful repeated warning against the client", "preserve the material fact and its scope; explain "
                         "the verified service value nearby and consolidate duplicate disclosures")

    def run(self) -> list[dict]:
        for fn in (self.r_page_job, self.r_length, self.r_snippet, self.r_openers, self.r_trailing_ing, self.r_vague,
                   self.r_noun_stack, self.r_nominal, self.r_person, self.r_locale, self.r_times,
                   self.r_lexicon, self.r_tells, self.r_labels, self.r_signposts, self.r_bold_bullets, self.r_numbers,
                   self.r_links, self.r_tables, self.r_absolutes, self.r_client, self.r_codes,
                   self.r_headings, self.r_structure, self.r_hub_duplication, self.r_length_total, self.r_keywords, self.r_koray, self.r_research, self.r_claims_of_scale, self.r_rhythm, self.r_grounding, self.r_meta, self.r_link_dump,
                   self.r_copy, self.r_attribution, self.r_heading_echo, self.r_embedded_query, self.r_repeats,
                   self.r_units, self.r_boundary, self.r_table_source, self.r_link_matches_figure,
                   self.r_named_source_unlinked, self.r_inherited_attribution, self.r_self_contained, self.r_heading_numbers, self.r_anchor_rules,
                   self.r_yes_no_openers,
                   self.r_misc):
            fn()
        order = {"block": 0, "warn": 1}
        self.findings.sort(key=lambda f: (order[f["severity"]], f["line"] or 0))
        for i, f in enumerate(self.findings, 1):
            f["id"] = f"F{i:03d}"
        return self.findings

    # 1 sentence length
    def r_length(self):
        # Human pages that rank put 5-15% of sentences past 30 words; a hard 30 cap forces the even rhythm and
        # fragments that read as machine-made. Block only the unreadable, and cap how often long ones appear.
        lens = []
        for b, s in self.prose():
            n = len(words(s))
            lens.append(n)
            if n > 42:
                self.add("S01-long-sentence", "block", b, s, f"{n} words (cap about 40)", "split into two sentences with explicit subjects")
            elif n > 35:
                self.add("S01-long-sentence", "warn", b, s, f"{n} words", "keep it only if it carries a list or a condition clearly")
        if len(lens) >= 15 and sum(1 for n in lens if n > 30) / len(lens) > 0.15:
            self.add("S01-long-sentence", "warn", None, f"{sum(1 for n in lens if n > 30)} of {len(lens)} sentences over 30 words",
                     "more long sentences than the human pages that rank (about 1 in 10)", "split the ones that don't need their length")

    # 1b snippet answers
    def r_snippet(self):
        prev = None
        for b in self.blocks:
            if b["type"] in ("h1", "h2"):
                prev = b
                continue
            if prev is not None and b["type"] == "p":
                n = len(words(b["text"]))
                q = prev["text"].rstrip().endswith("?")
                if q and n > 50:
                    self.add("S02-snippet-length", "block", b, b["text"], f"answer under a question heading is {n} words (40-50 max)",
                             "answer in 2-3 sentences, 40-50 words, then support it in the next paragraph")
                elif n > 90 or (n > 70 and prev["type"] == "h1"):
                    self.add("S02-snippet-length", "warn", b, b["text"], f"opening paragraph is {n} words", "tighten the first paragraph under this heading")
                prev = None
            elif b["type"] not in ("h3",):
                prev = None

    # 2 openers
    def r_openers(self):
        for b, s in self.prose():
            first = s.split(",")[0]
            fw = (re.match(r"[A-Za-z]+", s) or [None])[0] if re.match(r"[A-Za-z]+", s) else ""
            reason = None
            finite = re.search(r"\b(is|are|was|were|costs?|needs?|takes?|has|have|means|helps|gives|requires|uses|lets|makes|keeps|depends|works|saves|can|will|may|must|should)\b", first)
            if re.match(r"^\w+ing\s+(\w+\s+)?(lowers|raises|is|are|was|means|takes|makes|keeps|helps|cuts|adds|reduces|"
                        r"increases|needs|can|will|may|should|works|costs|gives)\b", s):
                continue  # "Neutering lowers the amount…": the -ing word is the subject
            if fw and fw.lower().endswith("ing") and fw.lower() not in ING_OK and "," in s[:120] and not finite \
                    and not _gerund_subject(s) and not _has_finite(first):
                reason = f"opens with a participial phrase (\"{first[:60]}\")"
            elif re.match(r"^[A-Z][a-z]+ed\s+(from|with|in|by|for|to|on|at|into|under)\b[^.]{0,100},", s) \
                    and not _base_verb_first(s):
                reason = f"opens with a past-participle phrase (\"{first[:60]}\")"
            elif re.match(r"^At\s+(?:[£$€]?\d|around|about|just|only|under|over)", s):
                reason = "opens with \"At + number\""
            elif re.match(r"^(When|If|While|Once|After|Before|Although|Though|Until|Unless)\s+\w+(ing|ed)\b", s):
                reason = f"opens with \"{' '.join(s.split()[:2])}\" + participle"
            if not reason:
                continue
            main = s.split(",", 1)[1] if "," in s else ""
            unrelated = bool(re.search(r"\d+(?:\.\d+)?\s*(?:cm|kg|×)", main)) and not re.search(r"\d", first)
            sev = "block" if unrelated and re.match(r"^[A-Z][a-z]+ed\s", s) else "warn"
            self.add("S03-opener", sev, b, s, reason + ("; the main clause makes an unrelated measurement claim" if sev == "block" else ""),
                     "make the opening phrase describe the subject of the main clause, and relate it to the claim; or rewrite as two plain sentences")

    # 3 trailing -ing
    def r_trailing_ing(self):
        hard = r"(making|ensuring|allowing|giving|helping|leaving|creating|providing|offering|keeping|enabling|letting|adding|reflecting|highlighting|underscoring|showcasing)"
        for b, s in self.prose():
            m = re.search(r",\s+(\w+ing)\b[^,;]*[.!?]?$", s)
            if not m or m.group(1).lower() in ING_OK:
                continue
            if len(words(s[:m.start()])) <= 5:  # "From outside the UK, contacting UKVI costs…": gerund subject, not a tail
                continue
            # "by adding users, integrating tools and tracking …" and "age, activity, neutering status and health" are
            # lists, not a commentary clause tacked on the end
            if re.search(r"\b(by|from|of|for|about|without|before|after|including|like|such as|between)\s+\w+ing\b", s[:m.start()], re.I) \
                    or re.search(r",\s+\w+ing\s+\w+\s+(and|or)\s+\w+", s[m.start():]) \
                    or re.search(r",\s+\w+ing(\s+\w+)?\s+(and|or)\b", s[m.start():]) or s[:m.start()].count(",") >= 1 \
                    and re.search(r"\b(and|or)\b", s[m.end():]):
                continue
            sev = "block" if re.fullmatch(hard, m.group(1).lower()) else "warn"
            self.add("S04-trailing-ing", sev, b, s, f"trailing \", {m.group(1)} …\" commentary clause",
                     "end the sentence before the comma, or make the -ing clause its own sentence with a subject")

    # 4 vague openers
    def r_vague(self):
        verbs = r"(is|are|was|were|means|ensures|helps|makes|allows|lets|provides|gives|can|will|has|have|keeps|adds|offers|creates|matters|works|comes|leaves|shows|depends|applies|also)"
        for b, s in self.prose():
            if re.match(rf"^(This|It|These|That|Those|Such)\s+{verbs}\b", s):
                self.add("S05-vague-opener", "warn", b, s, f"sentence opens with a vague \"{s.split()[0]}\"",
                         "name the thing (\"The report…\", \"The £20 fee…\")")

    # 5 noun stacks
    def r_noun_stack(self):
        brk = set(self.lex.get("stack_breakers", []))
        for b, s in self.prose():
            toks = re.findall(r"[A-Za-z]+/[A-Za-z0-9_]+|[A-Za-z][A-Za-z'-]*|[^\sA-Za-z]+", unquote(s))
            run = []
            for t in toks + ["."]:
                lw = t.lower()
                ok = (t.isalpha() or "-" in t) and lw not in STOP and lw not in brk and not lw.endswith("ly") \
                    and not t[0].isupper() and len(t) > 2 and not lw.endswith(("ing", "ed"))
                # a word ending in -s inside a run is usually a verb ("features") or the head noun: break there
                if ok and run and lw.endswith("s") and not lw.endswith("ss"):
                    run.append(t)
                    if len(run) >= 6:
                        self.add("S06-noun-stack", "warn", b, s, f"noun stack \"{' '.join(run)}\"",
                                 "unpack into a phrase with a verb or preposition")
                    run = []
                    continue
                if ok:
                    run.append(t)
                    continue
                if len(run) >= 5:
                    self.add("S06-noun-stack", "warn", b, s, f"noun stack \"{' '.join(run)}\"",
                             "unpack into a phrase with a verb or preposition (\"limits that the council sets for permits\")")
                run = []

    def r_nominal(self):
        for pat in self.lex.get("nominalisations", []):
            for b, s in self.prose():
                m = re.search(pat, s, re.I)
                if m:
                    self.add("S07-nominalisation", "warn", b, s, f"nominalisation \"{m.group(0)}\"", "use the real verb (\"enforce\", \"store\", \"protect\")")

    # 6 person drift
    def r_person(self):
        pd = dict(self.lex.get("person_drift", {}))
        # niche role nouns ("traveller", "patient", "applicant") come from the client profile
        pd["block"] = list(pd.get("block", [])) + list(self.b.get("reader_nouns") or [])
        you = len(re.findall(r"\byou(r|rs)?\b", self.md, re.I))
        if you < 3:
            return
        for b, s in self.prose(include_cells=True, include_headings=True):
            t = unquote(s)
            for sev in ("block", "warn"):
                for w in pd.get(sev, []):
                    # "one traveller describes…" is a third party, not the reader
                    if re.search(rf"\b(one|a|an|another|some|several|other|many|most|that|this)\s+(\w+\s+)?{re.escape(w)}\b", t, re.I):
                        continue
                    hits = re.findall(rf"(\S+)\s+({re.escape(w)})\b", t, re.I)
                    if hits and all(h[1][0].isupper() and h[0][:1].isupper() | h[0][:1].isdigit() for h in hits) \
                            and not re.search(rf"(^|[.!?]\s+){re.escape(w)}\b", t, re.I):
                        continue  # part of a name: "The 5 Kilo Traveller", "Condé Nast Traveller"
                    near = re.search(rf"(\w+[\s-])?{re.escape(w)}([\s-]\w+)?", t, re.I)
                    if near and re.sub(r"[-\s]+", " ", near.group(0).lower()) in re.sub(r"[-\s]+", " ", self.fact_text):
                        continue
                    if re.search(rf"\b{re.escape(w)}\b(?!-)", t, re.I) and w.lower() not in self.fact_text:
                        self.add("P01-person-drift", sev, b, s, f"\"{w}\" in a \"you\" article", "address the reader as \"you\"")

    # 7 locale spelling + × symbol
    def r_locale(self):
        loc = (self.b.get("locale") or "en-GB").lower()
        table = self.lex.get("us_to_uk", {})
        exc = set(self.lex.get("ize_exceptions", []))
        if loc.startswith("en-us"):
            table = {v: k for k, v in table.items()}
        for b, s in self.prose(include_cells=True, include_headings=True):
            t = unquote(s)
            for bad, good in table.items():
                if re.search(rf"\b{re.escape(bad)}\b", t, re.I if bad.islower() else 0):
                    if re.search(rf"\b{re.escape(bad)}\b", t):  # lower-case only: skip proper names
                        self.add("L01-locale-spelling", "block", b, s, f"\"{bad}\" is not {loc} spelling", f"use \"{good}\"")
            if loc.startswith("en-gb"):
                for w in re.findall(r"\b[a-z]+(?:iz|yz)(?:e|es|ed|ing|ation|ations|er|ers)\b", t):
                    if w not in exc and not any(w.startswith(x) for x in exc):
                        self.add("L01-locale-spelling", "block", b, s, f"\"{w}\" is US spelling", f"use \"{w.replace('iz', 'is').replace('yz', 'ys')}\"")
        return

    def r_times(self):
        for b, s in self.prose(include_cells=True, include_headings=True):
            if re.search(r"\d(?:\.\d+)?\s*(?:cm)?\s*x\s*\d", s):
                self.add("L02-dimension-symbol", "block", b, s, "dimensions written with \"x\"", "use the × symbol: 45 × 36 × 20 cm")

    # 8 banned / limited
    def r_lexicon(self):
        counts = Counter()
        extra = [x.lower() for x in (self.b.get("banned_phrases") or [])]
        for b, s in self.prose(include_cells=True, include_headings=True):
            t = unquote(s).lower()
            for ph in self.lex.get("banned", []) + extra:
                if re.search(rf"(?<![\w-]){re.escape(ph.lower())}(?![\w-])", t) and ph.lower() not in self.fact_text:
                    self.add("X01-banned-phrase", "block", b, s, f"banned phrase \"{ph}\"", "rewrite in plain words; state the fact or cut the sentence")
            for pat in self.lex.get("known_failures", []) + list(self.b.get("known_failures") or []):
                if re.search(pat, t):
                    self.add("X01-known-failure", "block", b, s, f"matches a known failure pattern /{pat}/", "rewrite from the fact sheet")
            for ph, cap in (self.lex.get("limited") or {}).items():
                hits = list(re.finditer(rf"(?<![\w-]){re.escape(ph)}(?![\w-])", t))
                if ph in ("addresses", "address", "highlights", "highlight", "features", "feature"):
                    # the noun ("saved addresses", "the highlights") isn't the AI-tell verb ("addresses the issue")
                    hits = [h for h in hits if not re.search(r"\b(the|a|an|your|my|our|their|its|saved|email|home|web|"
                                                             r"ip|postal|delivery|billing|these|those|key)\s+$", t[:h.start()])]
                n = len(hits)
                if n:
                    counts[ph] += n
                    if counts[ph] > cap:
                        self.add("X02-limited-phrase", "block", b, s, f"\"{ph}\" used {counts[ph]} times (cap {cap})", "use a plainer or more specific word")

    def r_tells(self):
        """Structural habits readers recognise as rewritten AI copy, even when every word is plain."""
        paras = [b for b in self.blocks if b["type"] == "p"]
        contrast = re.compile(r"\b(isn't|is not|aren't|are not|wasn't|not)\b[^.;:?]{1,45}[,;—–]\s*(it's|it is|they're|but it's|but)\b"
                              r"|\bit's not (about|that)\b|\bnot because\b[^.]{1,40}, but\b"
                              # the tail form: "Choose on fit, not size." / "…which vendors are big, not which one fits"
                              r"|\w,\s+not\s+(?!only\b|including\b|counting\b|least\b|yet\b|always\b|all\b|every\b|even\b|"
                              r"to\b|so\b|too\b|more\b|less\b|later\b|earlier\b|before\b|after\b)[^,.;:?]{1,50}[.;]?$", re.I)
        reveal = re.compile(r"^(the|here's the|one|a) (catch|trick|thing|problem|twist|good news|bad news|upshot|kicker|"
                            r"short version|reality|truth)\b[^.:]{0,40}:", re.I)
        tease = re.compile(r"^(?:[\w'’-]+\s+){0,5}(?:has|have|comes with|carries)\s+(?:one|two|a|a few|an)\s+"
                           r"(?:clear |big |key |important |real |main |obvious |simple )?(?:limit|limitation|catch|caveat|"
                           r"downside|drawback|exception|problem|flaw|weakness|thing|twist)s?"
                           r"(?:\s+(?:worth|to)\s+(?:knowing|know|noting|note|remembering|remember|watch|watching))?\.$"
                           r"|^here(?:'s|’s| is| are)\s+(?:a|an|the|how|what|why)\b[^.]{0,40}[.:]$"
                           r"|^(?:[\w'’-]+\s+){0,4}(?:is|are) real(?:,)?(?: too| as well)?\.$", re.I)
        for b, s in self.prose():
            if tease.match(s.strip()):
                self.add("H10-teaser", "block", b, s, "announces a point instead of making it",
                         "cut it and state the point itself")
        n_contrast, n_q, closers = 0, 0, 0
        for b in paras:
            ss = sentences(b["text"])
            for s in ss:
                if contrast.search(s):
                    n_contrast += 1
                    if n_contrast > 1:
                        self.add("H01-contrast-framing", "block" if n_contrast > 2 else "warn", b, s,
                                 f"\"X, not Y\" / \"not X, it's Y\" framing used {n_contrast} times",
                                 "state what it is; drop the straw man (once per page at most)")
                if reveal.match(s):
                    self.add("H03-colon-reveal", "warn", b, s, "set-up-and-reveal (\"The catch: …\")",
                             "say the point directly in a normal sentence")
            # a question the paragraph then answers itself ("Missing one? Call…")
            if any(s.rstrip().endswith("?") for s in ss[:-1]):
                n_q += 1
                if n_q > 1:
                    self.add("H02-self-answered-question", "warn", b, b["text"],
                             "rhetorical question answered in the next breath, more than once",
                             "turn it into a statement (\"Without one of them, call…\")")
            # a short, numberless punchline as the paragraph's last word
            if len(ss) >= 2:
                last = ss[-1]
                if len(words(last)) <= 9 and not re.search(r"\d", last) and len(words(last)) < min(len(words(x)) for x in ss[:-1]):
                    closers += 1
        if closers > max(2, len(paras) // 6):
            self.add("H04-punchline-closers", "warn", None, f"{closers} paragraphs end on a short punchline",
                     "paragraphs that all land on a one-liner read as written to a formula",
                     "end most paragraphs on the fact or the reason, not a quip")

    # 9 framework labels
    def r_labels(self):
        labels = self.lex.get("framework_labels", [])
        pat = re.compile(r"^\s*(?:\*\*|__)?(" + "|".join(re.escape(x) for x in labels) + r")s?(?:\*\*|__)?\s*(?::|—|–|\*\*:|-\s)", re.I)
        for b in self.blocks:
            if b["type"] in ("p", "li") and pat.match(b["raw"]):
                self.add("X03-framework-label", "block", b, b["text"], f"visible framework label \"{pat.match(b['raw']).group(1)}\"",
                         "fold the point into a normal sentence")
            if b["type"].startswith("h") and re.fullmatch(r"(key )?takeaways?|verdict|summary|tl;dr|bottom line|pros and cons",
                                                           b["text"].strip(" :?").lower()):
                self.add("X03-framework-label", "block", b, b["text"], "heading is a framework label", "use a heading that names the reader's question")

    def r_signposts(self):
        seen = defaultdict(set)
        where = defaultdict(list)
        for b in self.blocks:
            if b["type"] != "p":
                continue
            first = sentences(b["text"])[0] if b["text"] else ""
            key = " ".join(first.lower().split()[:3])
            if len(key.split()) == 3:
                seen[key].add(b["section"])
                where[key].append((b, first))
        for key, secs in seen.items():
            if len(secs) >= 3:
                for b, s in where[key]:
                    self.add("X04-repeated-opener", "warn", b, s, f"\"{key}…\" opens paragraphs in {len(secs)} sections", "vary how sections open")

    def r_bold_bullets(self):
        group = []
        for b in self.blocks + [{"type": "end"}]:
            if b["type"] == "li":
                group.append(b)
                continue
            if group:
                bold = [g for g in group if re.match(r"^(\*\*|__)[^*_]{1,50}(\*\*|__)\s*[:—–-]|^(\*\*|__)[^*_]{1,50}[:—–](\*\*|__)", g["raw"])]
                if len(bold) >= 3:
                    self.add("X05-bold-label-bullets", "block", bold[0], bold[0]["text"], f"{len(bold)} bullets use \"**Label:** text\"",
                             "write the bullets as plain sentences or a table; keep bold for one or two key terms")
            group = []

    # 10 numbers trace to the fact sheet
    def r_numbers(self):
        nums, triples, money, prices = allowed_numbers(self.sheet, self.research)
        hard = bool(self.b.get("hardcode_prices"))
        units = list(self.prose(include_cells=True, include_headings=True))
        if self.meta.get("title"):
            units.append(({"line": 1, "section_title": "(title)"}, self.meta["title"]))
        if self.meta.get("meta_description"):
            units.append(({"line": 2, "section_title": "(meta)"}, self.meta["meta_description"]))
        for b, s in units:
            if (b.get("type") or "").startswith("h") and s.rstrip().endswith("?"):
                continue
            t = re.sub(r"\]\([^)]*\)", "]", s)
            for tr in TRIPLE.findall(t):
                key = tuple(sorted((_f(x) for x in tr), reverse=True))
                if key not in triples:
                    self.add("N01-untraced-number", "block", b, s, f"dimension set {' × '.join(tr)} is not in the fact sheet or check output",
                             "use the exact figures from fact_sheet.json, or remove")
            t2 = TRIPLE.sub(" ", t)
            t2 = re.sub(r"\b(19|20)\d\d\s?[-–/]\s?(\d\d|(19|20)\d\d)\b", " ", t2)
            for cur, n, unit in NUM.findall(t2):
                v = _f(n)
                if cur:
                    if (cur, v) in prices and not hard:
                        self.add("N02-hardcoded-price", "block", b, s, f"product price {cur}{n} hardcoded", "remove the price (prices change; the product page shows it)")
                    elif (cur, v) not in money and (cur, v) not in prices and not (
                            _worked(s, v, nums | {x for _, x in money})
                            or _derived(v, self._ctx(b, s), nums | {x for _, x in money})):
                        self.add("N01-untraced-number", "block", b, s, f"amount {cur}{n} is not in the fact sheet", "use a verified figure or write around it")
                    continue
                material = bool(unit) or v > 10 or "." in n
                if not material:
                    continue
                if v not in nums and (_worked(s, v, nums) or _derived(v, self._ctx(b, s), nums)):
                    continue
                if v not in nums:
                    self.add("N01-untraced-number", "block", b, s, f"number {n}{(' ' + unit) if unit else ''} is not in the fact sheet",
                             "use a verified figure, add one with `seo.py prep --add-fact`, or write around it")

    def _ctx(self, b, s):
        """The text a number is read with: its paragraph or list item, or its whole table row."""
        if b.get("type") == "li":
            i = next((k for k, x in enumerate(self.blocks) if x is b), None)
            if i is not None:
                j, k = i, i
                while j > 0 and self.blocks[j - 1]["type"] == "li":
                    j -= 1
                while k + 1 < len(self.blocks) and self.blocks[k + 1]["type"] == "li":
                    k += 1
                intro = self.blocks[j - 1]["text"] if j > 0 and self.blocks[j - 1]["type"] == "p" else ""
                return intro + " " + " ; ".join(x["text"] for x in self.blocks[j:k + 1])
        if b.get("type") == "tr":
            i = next((k for k, x in enumerate(self.blocks) if x is b), None)
            if i is None:
                return " | ".join(strip_md(c) for c in b.get("cells", []))
            j, k = i, i
            while j > 0 and self.blocks[j - 1]["type"] == "tr":
                j -= 1
            while k + 1 < len(self.blocks) and self.blocks[k + 1]["type"] == "tr":
                k += 1
            # the table plus the paragraph that introduces it
            intro = self.blocks[j - 1]["text"] if j > 0 and self.blocks[j - 1]["type"] == "p" else ""
            return intro + " " + " ; ".join(" | ".join(strip_md(c) for c in x.get("cells", [])) for x in self.blocks[j:k + 1])
        i = next((k for k, x in enumerate(self.blocks) if x is b), None)
        prev = self.blocks[i - 1]["text"] if i and self.blocks[i - 1]["type"] in ("p", "li") else ""
        return prev + " " + (b.get("text") or s)

    # 11 links
    def r_links(self):
        lm = self.lm
        allowed = {lm.get("page", "").rstrip("/")}
        prod = {p["url"].rstrip("/"): p for p in lm.get("products", [])}
        allowed |= set(prod)
        allowed |= {c["url"].rstrip("/") for c in lm.get("children", [])}
        allowed |= {u.rstrip("/") for u in lm.get("internal", [])}
        allowed |= {o["url"].rstrip("/") for o in lm.get("official", [])}
        allowed |= {f["source_url"].rstrip("/") for f in self.sheet.get("facts", []) if f.get("source_url") and f.get("status") in USABLE}
        allowed |= {u.rstrip("/") for v in (lm.get("client_related") or {}).values() for u in v}  # the pack offers these
        if self.b.get("domain"):
            allowed |= {f"https://{self.b['domain']}".rstrip("/"), f"https://www.{self.b['domain'].removeprefix('www.')}".rstrip("/")}
        pairs = Counter()
        per_url = Counter()
        names = {p["name"].lower(): p["url"] for p in lm.get("products", [])}
        for b in self.blocks:
            raw = b.get("raw", "")
            for anchor, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", raw):
                u = url.rstrip("/") if url.rstrip("/") in allowed else url.split("#")[0].rstrip("/")
                pairs[(anchor.lower(), u)] += 1
                per_url[u] += 1
                if u not in allowed:
                    self.add("U01-url-not-in-link-map", "block", b, f"[{anchor}]({url})", "URL is not in link_map.json (never guess a URL)",
                             "use a URL from link_map.json or drop the link")
                elif u in prod and prod[u].get("redirected_to"):
                    self.add("U02-redirecting-url", "block", b, f"[{anchor}]({url})", f"redirects to {prod[u]['redirected_to']}", "link the final URL")
                if "/collections/" in u and any(n in anchor.lower() for n in names):
                    self.add("U03-product-to-collection", "block", b, f"[{anchor}]({url})", "product name linked to a collection", "link the product page")
            for anchor, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", raw):
                if len(anchor.split()) > 8:
                    self.add("U11-long-anchor", "warn", b, f"[{anchor}]", f"{len(anchor.split())}-word anchor",
                             "anchor 2–6 words that name the target page")
            txt = strip_md(raw)
            if re.search(r"\b(r/\w+|reddit|forum|commenter|one (user|poster|reader|owner))\b", txt, re.I) \
                    and re.search(r"[\"“][^\"”]{12,}[\"”]", txt) \
                    and not re.search(r"\]\(https?://[^)]*(reddit|forum|community|mumsnet|quora)", raw, re.I):
                self.add("U12-unlinked-forum-quote", "block", b, txt[:200], "quotes a forum comment without linking it",
                         "link the comment from the pack's forum quotes, or cut the quote")
            for bare in re.findall(r"(?<![(\[])https?://[^\s)]+", strip_md(raw)):
                self.add("U04-bare-url", "warn", b, bare, "bare URL in copy", "use a descriptive anchor")
        from .domains import kind as _kd
        dom0 = (self.b.get("domain") or "").replace("www.", "")
        first_sec = next((b["section"] for b in self.blocks if b["type"] == "h2"), None)
        for b in self.blocks:
            if first_sec is not None and b.get("section") == first_sec:
                break
            hit = next(((a, u) for a, u in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", b.get("raw", ""))
                        if dom0 not in u), None)
            if hit and _kd(hit[1]) in ("business_site", "ecommerce", "marketplace", "help_centre"):
                self.add("U14-commercial-first-link", "block", b, f"[{hit[0]}]({hit[1]})",
                         "the page's first outbound link sends readers to a business (possibly a competitor)",
                         "open with your own answer; link an independent source, or the business later where it helps")
                break
        for b in self.blocks:
            for _a, u in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", b.get("raw", "")):
                if re.search(r"[?&](utm_\w+|bc|gclid|fbclid|srsltid|ref|source|campaign|cmpid|cid|mc_\w+)=", u):
                    self.add("U15-tracking-parameter", "warn", b, u, "link carries a tracking parameter",
                             "link the clean URL (the page without ?utm_…/?bc=…)")
        # a rival brand named again and again turns the client's page into the rival's
        serp = self.research.get("serp_intel") or {}
        body_txt = " ".join(b["text"] for b in self.blocks if b["type"] in ("p", "li", "tr", "h2", "h3"))
        qwords = set(tokens(self.b.get("target_query") or "", self.b.get("synonyms") or {}))
        roots = {(o.get("domain") or "").removeprefix("www.").split(".")[0] for o in serp.get("organic", [])
                 if o.get("kind") in ("business_site", "ecommerce")} - {dom0.split(".")[0], ""}
        roots = {r for r in roots if r not in qwords and not any(r == w or r == w + "s" for w in qwords)}
        for r in sorted(roots):
            if len(r) < 4:
                continue
            n_r = len(re.findall(rf"\b{re.escape(r)}\b", body_txt, re.I))
            if n_r > 3:
                self.add("U16-competitor-prominence", "warn", None, f"\"{r}\" named {n_r} times",
                         "a business competing for this query is a main voice on the client's page",
                         "lead with independent sources and the client's own method; keep the rival to one attributed example")
        for (anchor, u), n in pairs.items():
            if n > 2:
                self.add("U05-repeated-link", "block", None, f"[{anchor}]({u})", f"same anchor and URL used {n} times (cap 2)", "remove repeats")
        for u in per_url:
            if u in {x.rstrip("/") for x in (lm.get("client_related") or {}).get("same_topic", [])}:
                self.add("U13-links-replaced-page", "block", None, u,
                         "links the client's existing page on this same query, which this page replaces",
                         "use its facts directly; the old page will be merged or redirected here")
        from .pagejob import COMMERCIAL, next_steps, is_client_url
        action_urls = {url for _, url in next_steps(self.blocks, self.sheet)} if self.b.get("page_type") in COMMERCIAL else set()
        for u, n in per_url.items():
            # an outside page may be linked again where another page of its publisher came in between (U18); beyond
            # two links, or any repeat of the client's own pages, it reads as link-stuffing
            cap = 2 if u.rstrip("/") in action_urls else 1 if is_client_url(u, self.sheet) else 2
            if n > cap and not any(p == u for (_, p), m in pairs.items() if m > 2):
                # RULES: never one page more than twice (the client's own pages once each)
                self.add("U07-url-linked-twice", "block" if n > 2 else "warn", None, u, f"linked {n} times",
                         "keep the link on the first sentence that credits this page, and a second only where a later "
                         "sentence credits it after a different page of the same publisher (U18); unlink the rest and "
                         "name the source in words")
        # internal links: density, and the same "X's guide shows how" closer section after section
        dom = (self.b.get("domain") or "").replace("www.", "")
        n_words = sum(len(words(b["text"])) for b in self.blocks if b["type"] in ("p", "li", "tr"))
        internal = sum(n for u, n in per_url.items() if dom and dom in u)
        if dom and n_words and internal > max(4, n_words / 150 + 1):
            self.add("U09-link-density", "warn", None, f"{internal} internal links in {n_words} words",
                     "more internal links than a reader follows (about one per 150 words)", "keep the ones that are a real next step")
        closer = re.compile(r"\b(guide|walkthrough|article|post|comparison|checklist|explainer|page|breakdown|tutorial)\b.*"
                            r"\b(shows?|covers?|explains?|walks?|sets? out|goes through|has more|compares?|details?)\b", re.I)
        hits = []
        for b in self.blocks:
            if b["type"] != "p":
                continue
            ss = sentences(b.get("raw", ""))
            last = ss[-1] if ss else ""
            if dom and dom in last and closer.search(strip_md(last)):
                hits.append((b, strip_md(last)))
        if len({b["section"] for b, _ in hits}) >= 3:
            for b, s in hits:
                self.add("U10-link-closer", "warn", b, s, f"{len(hits)} paragraphs end on a sentence that only carries a link",
                         "put the link on words in a sentence that says something useful, and drop the closer")
        if self.b.get("page_type") == "hub" and lm.get("children"):
            kids = {c["url"].rstrip("/") for c in lm["children"]}
            if not any(u in kids for u in per_url):
                self.add("U06-hub-no-children", "block", None, "(page)", "hub page links to none of its child pages", "link the relevant child pages")
        # page-specific: a URL must not appear next to words that misdescribe it
        for rule in self.b.get("link_context_bans") or []:
            for i, b in enumerate(self.blocks):
                raw = b.get("raw", "")
                if rule["url"] not in raw:
                    continue
                ctx = strip_md(raw)
                if b["type"] in ("tr", "li"):  # a row or bullet is read with its table header and intro sentence
                    j = i - 1
                    while j >= 0 and self.blocks[j]["type"] == b["type"]:
                        if self.blocks[j].get("header"):
                            ctx += " " + self.blocks[j]["text"]
                        j -= 1
                    if j >= 0 and self.blocks[j]["type"] == "p":
                        ctx += " " + sentences(self.blocks[j]["text"])[-1]
                ctx = ctx.lower()
                hit = [w for w in rule["words"] if re.search(rf"\b{re.escape(w.lower())}", ctx)]
                if hit:
                    self.add("U08-link-context", "block", b, strip_md(raw), f"{rule['url']} presented with \"{hit[0]}\": {rule.get('reason', '')}",
                             rule.get("fix", "describe the link for what it is"))

    def r_hub_duplication(self):
        """Hubs support their selector: they must not rebuild child-page content country by country."""
        if self.b.get("page_type") != "hub" or not self.lm.get("children"):
            return
        names = {c["name"].lower() for c in self.lm["children"] if c.get("name")}
        rows = [b for b in self.blocks if b["type"] == "tr" and not b.get("header")
                and (strip_md(b["cells"][0]).lower().strip(" *") in names or places(strip_md(b["cells"][0])))]
        if len(rows) >= 4:
            self.add("R02-hub-rebuilds-children", "block", rows[0], f"{len(rows)} country rows",
                     "hub rebuilds child-page content in a country table", "link the child pages instead and keep the hub short")
        def starts_with_country(t):
            t = t.strip(" *").lower()
            return any(re.match(rf"{re.escape(n)}\b", t) for n in names)
        items = [b for b in self.blocks if b["type"] == "li" and starts_with_country(strip_md(b["raw"])) and len(words(b["text"])) > 12]
        if len(items) >= 3:
            self.add("R02-hub-rebuilds-children", "block", items[0], f"{len(items)} country bullets",
                     "hub explains countries one by one", "keep country detail on the child pages; link them")

    # 12 tables
    def r_tables(self):
        pats = [re.compile(p, re.I) for p in self.lex.get("placeholders", [])]
        named = re.compile(r"\b[A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*\s+(Portal|Tracker|Console|Platform|System|Website|Service|Services|Centre|Center|Account|Checker|Tool)\b(?!\s+[A-Z])")
        for b in self.blocks:
            cells = b.get("cells") if b["type"] == "tr" else ([b["raw"]] if b["type"] == "li" else [])
            for c in cells:
                plain = strip_md(c)
                for p in pats:
                    if p.search(plain):
                        self.add("T01-placeholder", "block", b, plain, f"placeholder text (/{p.pattern}/)", "put a verified fact in the cell, or drop the row/column")
                        break
                nm = named.search(plain) if b["type"] == "tr" and not b.get("header") else None
                if nm and "](" not in c and nm.group(0).lower() not in self.fact_text:
                    self.add("T02-unlinked-portal", "block", b, plain, "cell names a portal or service without a link", "link it from link_map.json or describe it without a proper name")

    # 13 absolutes
    def r_absolutes(self):
        ab = self.lex.get("absolutes", {})
        for b, s in self.prose(include_cells=True, include_headings=True):
            t = unquote(s).lower()
            for ph in ab.get("block", []):
                if re.search(rf"(?<![\w-]){re.escape(ph)}(?![\w-])", t) and ph not in self.fact_text:
                    self.add("A01-absolute", "block", b, s, f"absolute/guarantee \"{ph}\" not supported by the fact sheet", "qualify it or state the sourced rule")
            # "all <plural noun>" generalises over a whole class; only a fact can say that
            m = re.search(r"\ball\s+(?:the\s+)?(?:\w+\s+)?([a-z]{4,}s)\b", t)
            label = m and re.search(r"\bAll\s+[A-Z]\w+", s)  # "Block All Cookies" is a setting's name
            squash = lambda x: re.sub(r"[\s-]+", "", x)
            if m and not label and squash(m.group(0)) not in squash(self.fact_text) and m.group(1) not in (
                    "others", "sizes", "ways", "things", "days", "kinds", "types", "sorts", "options"):
                self.add("A01-absolute", "block", b, s, f"\"{m.group(0)}\" overgeneralises", "name the cases the fact sheet covers")
            for ph in ab.get("warn", []):
                if ph in ("all", "every"):
                    continue
                if re.search(rf"(?<!\bnot )(?<!\bnot quite )(?<!n't )\b{re.escape(ph)}\b", t) and ph not in self.fact_text:
                    self.add("A01-absolute", "warn", b, s, f"absolute word \"{ph}\"", "check the claim is literally true")

    # 14 client claims
    def r_client(self):
        client = self.b.get("client") or ""
        aliases = [client, client.replace(" ", "")] + list(self.b.get("client_aliases") or [])
        aliases = [a for a in aliases if a]
        claims = [c["text"] for c in self.sheet.get("client", {}).get("approved_claims", []) if c.get("seen_on_site", True)]
        from .domains import org_domain
        # the client's sites: the brief's domain, and where it now redirects after a rename or takeover
        client_orgs = {org_domain(f"https://{self.b['domain']}/")} if self.b.get("domain") else set()
        if (self.sheet.get("client") or {}).get("moved_to"):
            client_orgs.add(org_domain(self.sheet["client"]["moved_to"]))
        own = [str(f.get("value", "")) for f in self.sheet.get("facts", [])
               if f.get("status") in USABLE and (f.get("basis") == "client_page" or (
                   (f.get("source_url") or "").startswith("http") and org_domain(f["source_url"]) in client_orgs
                   and "/products/" not in (f.get("source_url") or "")))]  # product copy describes the maker
        claims += own  # what the client's own pages say, verified, is the client's approved wording
        if self.b.get("task") == "rewrite":  # rewriting the client's live page: its own words are the client's voice
            cur = (self.research.get("current_page") or {})
            claims += [s for s in sentences(cur.get("text") or "") if len(s.split()) >= 5]
        claims += [f"{p.get('display_name', '')}. {p.get('description', '')}" for p in self.sheet.get("products", [])]
        cfacts = list(self.sheet.get("client", {}).get("facts", [])) + own  # taglines don't state the client's role
        banned = [x.lower() for x in self.sheet.get("client", {}).get("banned_claims", [])]

        def content(s):
            return {re.sub(r"(ing|ed|es|s)$", "", w.lower()) for w in re.findall(r"[A-Za-z0-9]+", s)
                    if w.lower() not in STOP and len(w) > 2}
        cl = [(c, content(c)) for c in claims]
        # brands are matched with their capital ("Bulk", not "in bulk")
        alias_re = re.compile(r"\b(" + "|".join(re.escape(a.strip("™®")) for a in aliases) + r")\b") if aliases else None
        dom = (self.b.get("domain") or "").replace("www.", "")
        for b, s in self.prose(include_cells=True, include_headings=True):
            low = s.lower()
            # anchor text of links to other sites is a cited title, not the client speaking ("…should we really eat?")
            for anchor, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", b.get("raw", "")):
                if dom and dom not in url:
                    s = s.replace(anchor, " ")
            s = unquote(s)
            about_c = bool(re.search(r"\b(we|our|ours|us)\b", s, re.I) or (alias_re and alias_re.search(s)))
            third = re.search(r"\b[A-Z][\w&'’-]+(?:\s+[A-Z][\w&'’-]+)*(?:'s|’s)\s+(?:\w+\s+){0,3}(guarantee|warranty)", s)
            for bc in banned:
                if bc in low and third and not about_c:
                    continue  # another company's guarantee, named as theirs
                if bc in low:
                    # an official fact may use the word ("An ETA does not guarantee entry"); the ban is on the
                    # client promising it, so allow it when the sentence carries the fact's own phrase
                    near = re.search(rf"[^.]{{0,40}}{re.escape(bc)}[^.]{{0,25}}", low)
                    if near and bc in self.fact_text and any(
                            near.group(0).strip()[i:i + 25] in self.fact_text for i in range(0, max(1, len(near.group(0)) - 25), 5)):
                        continue
                    self.add("C01-banned-claim", "block", b, s, f"banned claim \"{bc}\"", "remove")
            about_client = bool(re.search(r"\b(we|our|ours)\b", s, re.I) or re.search(r"\bus\b", s)
                                or (alias_re and alias_re.search(s)))
            if not about_client:
                continue
            m = re.search(r"\b(we|" + "|".join(re.escape(a) for a in aliases) + r")\s+(?:\w+\s+)?" + POSITION_VERBS + r"\b", s, re.I)
            def affirmed(stem, fact):  # "is not the designer" does not support "designs"
                return any(not re.search(r"\b(not|n't|never|no)\b", fact[max(0, x.start() - 25):x.start()], re.I)
                           for x in re.finditer(stem, fact, re.I))
            if m and re.search(r"\s(is|are|was|were|been|being)\s+\w+$", m.group(0), re.I):
                m = None  # passive description of the product, not the client's role
            if m and not any(affirmed(m.group(2)[:5], f) for f in cfacts):
                self.add("C02-client-positioning", "block", b, s, f"positions the client as one who {m.group(2)} (not in client_facts)",
                         "describe the client only as client_facts do (e.g. retailer)")
            sw = content(s)
            # supported when it repeats most of a claim, or when most of this sentence is the client's own words
            # (a short sentence restating one detail of a long client sentence: "a panel of 400 lenders")
            best = max((max(len(sw & cw) / max(1, len(cw)),
                            len(sw & cw) / len(sw) if len(sw) >= 4 and len(sw & cw) >= 3 else 0) for c, cw in cl), default=0)
            if best >= 0.6:
                continue
            # pointing to the client's own guide or tool is navigation, not a service claim
            if alias_re and re.search(alias_re.pattern + r"('s)?\s+(\w+\s+){0,2}(guide|blog|page|article|post|calculator|tool|"
                                      r"checker|help ?centre|faq|range|collection)s?\b", s):
                continue
            if re.search(r"\bour (\w+\s+){0,2}(guide|blog|page|article|post|calculator|tool|checker|faq|range|collection)s?\b", s, re.I):
                continue
            if re.search(r"\b(we|i)(\s+(recommend|suggest|advise|would|prefer)\b|['’]d\b)|\bour (advice|recommendation|view|tip|pick)\b", s, re.I):
                continue
            if re.search(SERVICE_VERBS, s, re.I):
                self.add("C01-unapproved-claim", "block", b, s, "statement about the client's service matches no approved_claims entry",
                         "use only approved claim wording, or cut it")
            else:
                self.add("C01-client-mention", "warn", b, s, "mentions the client; check it only repeats approved claims or client facts", "")

    # 15 internal codes
    def r_codes(self):
        pats = [re.compile(p, re.I) for p in self.lex.get("internal_codes", []) + list(self.b.get("internal_codes") or [])]
        codes = {c for p in self.sheet.get("products", []) for c in p.get("internal_codes", [])}
        for b, s in self.prose(include_cells=True, include_headings=True):
            for p in pats:
                if p.search(s):
                    self.add("I01-internal-code", "block", b, s, f"internal code (/{p.pattern}/)", "remove codes and SKUs from copy")
            for c in codes:
                if re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", s):
                    self.add("I01-internal-code", "block", b, s, f"supplier/internal code \"{c}\"", "remove it")

    # 17 headings
    def r_headings(self):
        proper = set()
        for p in self.sheet.get("products", []):
            proper |= set(re.findall(r"[A-Z][\w'-]+", f"{p['display_name']} {p.get('vendor', '')}"))
        for f in self.sheet.get("facts", []):
            proper |= set(re.findall(r"\b[A-Z][\w'-]*[A-Z0-9][\w'-]*\b|\b[A-Z][a-z]+(?=\s[A-Z])", str(f.get("value", "")) + " " + str(f.get("claim", ""))))
            for k in ("carrier", "subject"):
                if f.get(k):
                    proper |= set(re.findall(r"[A-Z][\w'-]+", f[k]))
        for c in self.lm.get("children", []):
            proper |= set(re.findall(r"[A-Z][\w'-]+", c.get("name", "")))
        proper |= set(re.findall(r"[A-Z][\w'-]+", " ".join([self.b.get("client") or ""] + list(self.b.get("client_aliases") or []))))
        proper |= set((self.b.get("proper_nouns") or []))
        proper |= {"UK", "US", "EU", "I", "GOV.UK"}
        h1s = [b for b in self.blocks if b["type"] == "h1"]
        live = (self.sheet.get("page") or {}).get("h1")
        want = self.b.get("h1") or live
        if len(h1s) != 1:
            self.add("H02-h1", "block", h1s[1] if len(h1s) > 1 else None, "(page)", f"{len(h1s)} H1 headings", "use exactly one H1")
        elif want and C.norm_for_match(h1s[0]["text"]) != C.norm_for_match(want):
            self.add("H02-h1", "block", h1s[0], h1s[0]["text"], f"H1 differs from the live/brief H1 \"{want}\"", f"use \"{want}\" or set brief.h1")
        for b in self.blocks:
            if not b["type"].startswith("h"):
                continue
            t = b["text"]
            if b["type"] == "h1" and want:
                continue
            ws = re.findall(r"[A-Za-z][\w'’-]*", t)[1:]
            geo = set()
            for i in range(len(ws)):
                for span in (ws[i:i + 1], ws[i:i + 2]):
                    if len(span) and span[0][:1].isupper() and places(" ".join(span)):
                        geo |= set(span)
            elig = [w for w in ws if len(w) > 3 and w not in proper and w not in geo and not w.isupper()]
            caps = [w for w in elig if w[0].isupper()]
            if len(caps) >= 2 and len(caps) >= 0.5 * max(1, len(elig)):
                self.add("H01-title-case", "block", b, t, "heading uses Title Case", "use sentence case: capitalise the first word and proper nouns only")
            if len(t) > 70:
                self.add("H01-heading-length", "warn", b, t, f"heading is {len(t)} characters", "shorten to under about 70")
            if b["type"] == "h2" and self.b.get("page_type") in ("guide", "spoke", "product-guide") and not (
                    t.endswith("?") or re.match(r"(how to|how do|how much|which|what|when|where|why|can|do|does|is|are|should)\b", t, re.I)):
                self.add("H03-question-heading", "warn", b, t, "explanatory H2 is not a reader question or How-to task",
                         "phrase it as the entity-specific question the section answers")
        title = self.meta.get("title")
        if not title:
            self.add("H04-title", "warn", None, "(front matter)", "no title in front matter", "add `title:` (about 60 characters)")
        else:
            if len(title) > 70:
                self.add("H04-title", "block", None, title, f"title is {len(title)} characters", "keep it about 60 or under")
            elif len(title) > 62:
                self.add("H04-title", "warn", None, title, f"title is {len(title)} characters", "keep it about 60 or under")
            if self.b.get("single_brand") and re.search(r"\bbest\b", title, re.I):
                self.add("H04-title", "block", None, title, "\"best\" on a single-brand page", "qualify it or drop \"best\"")

    # 16 repeated section structure
    def r_structure(self):
        sigs = defaultdict(list)
        for b in self.blocks:
            if b["section"] and b["type"] in ("p", "li", "tr", "h3"):
                t = {"p": "P", "li": "L", "tr": "T", "h3": "H"}[b["type"]]
                s = sigs[b["section"]]
                if not s or s[-1] != t:
                    s.append(t)
        keys = sorted(sigs)
        run = 1
        for a, c in zip(keys, keys[1:]):
            if len(sigs[a]) >= 3 and sigs[a] == sigs[c]:
                run += 1
                if run == 3:
                    b = next(x for x in self.blocks if x["section"] == c)
                    self.add("R01-repeated-structure", "warn", b, "-".join(sigs[c]),
                             "three or more consecutive sections share the same block pattern", "vary the shape: lead with a table, a list, or a single paragraph")
            else:
                run = 1

    def r_keywords(self):
        """Rankability: the target query belongs in the title and the opening; secondary queries get covered."""
        mods = STOP | {"best", "top", "cheap", "near", "me", "online", "uk", "us", "free"}

        def toks(q):
            return [w for w in re.findall(r"[a-z0-9]+", q.lower()) if w not in mods and len(w) > 2]

        def covered(tokens, text):
            low = re.sub(r"[()]", "", text.lower())  # "221(g)" matches a search for "221g"
            return sum(1 for w in tokens if re.search(r"\b" + re.escape(w[:5]), low)) / max(1, len(tokens))
        q = toks(self.b.get("target_query") or "")
        if q:
            title = self.meta.get("title", "")
            if title and covered(q, title) < 1:
                self.add("K01-query-in-title", "block", None, title, f"title lacks the target query terms {q}",
                         "put the main query words in the title, naturally")
            first = next((b for b in self.blocks if b["type"] == "p"), None)
            h1 = next((b["text"] for b in self.blocks if b["type"] == "h1"), "")
            if first and covered(q, first["text"] + " " + h1) < 0.67:
                self.add("K01-query-in-opening", "warn", first, first["text"], f"opening paragraph barely uses the query terms {q}",
                         "say what the page answers in the reader's words")
        for sq in self.b.get("secondary_queries") or []:
            t = toks(sq)
            if t and not any(covered(t, b["text"]) >= 0.7 for b in self.blocks if b["type"] in ("h2", "h3", "p", "li")):
                self.add("K02-secondary-query", "warn", None, sq, "secondary search not answered in any heading or paragraph",
                         "cover it in a heading or opening sentence where it fits")

    def r_koray(self):
        """Mechanically checkable algorithmic-authorship rules."""
        # contextless headings
        for b in self.blocks:
            if b["type"] in ("h2", "h3", "h4") and re.fullmatch(
                    r"(introduction|overview|conclusion|final thoughts|about|miscellaneous|summary|wrap[- ]up|"
                    r"faqs?|frequently asked questions)", b["text"].lower().strip(" :?")):
                from .pagejob import COMMERCIAL
                if self.b.get("page_type") in COMMERCIAL and re.fullmatch(r"faqs?|frequently asked questions", b["text"], re.I):
                    continue
                self.add("K03-contextless-heading", "block", b, b["text"], "contextless heading",
                         "name the subject the section covers; place questions according to the Page job")
        # sentence-initial "If": declaration first
        for b, s in self.prose():
            m_if = re.match(r"^If\b([^,]*),", s)
            if m_if and len(m_if.group(1).split()) > 12:
                self.add("K04-if-opener", "warn", b, s, "opens with a condition", "state the declaration first, then the condition")
        # bold: at most one per section, never a whole sentence
        per_sec = Counter()
        for b in self.blocks:
            raw = b.get("raw", "")
            for m in re.finditer(r"\*\*([^*]+)\*\*", raw):
                per_sec[b["section"]] += 1
                if len(m.group(1).split()) > 8:
                    self.add("K05-bold", "warn", b, m.group(1), "bold on a whole phrase or sentence", "bold only the answer value")
        for sec, n in per_sec.items():
            if n > 2:
                b = next(x for x in self.blocks if x["section"] == sec)
                self.add("K05-bold", "warn", b, b.get("section_title") or "", f"{n} bold spans in one section", "one bold per section, on the answer")
        # acronyms expanded on first use
        body = " ".join(b["raw"] for b in self.blocks if b["type"] in ("p", "li", "tr", "h2", "h3"))
        body = re.sub(r"\]\([^)]*\)", "]", body)
        body = re.sub(r"https?://\S+", " ", body)
        known = {"UK", "US", "USA", "EU", "ID", "PDF", "FAQ", "OK", "TV", "PM", "AM", "UAE", "GOV", "URL", "UTC", "GMT", "USB", "SIM", "PIN", "GPS", "LED", "ATM", "DIY"} | set(self.b.get("known_acronyms") or [])
        known |= set(re.findall(r"\b[A-Z]{2,6}\b", " ".join(str(f.get("value", "")) + " " + str(f.get("claim", "")) + " "
                                                            + " ".join(f.get("also") or [])
                                                            for f in self.sheet.get("facts", []) if f.get("status") in SUPPORT)))
        known |= set(re.findall(r"\b[A-Z]{2,6}\b", " ".join([self.b.get("client") or ""] + list(self.b.get("proper_nouns") or [])
                                                            + [o.get("label") or "" for o in self.lm.get("official", [])])))
        known |= set(re.findall(r"\b([A-Z]{2,6})!", body))  # campaign names such as THINK!
        seen = set()
        for m in re.finditer(r"\b([A-Z]{2,6})\b", body):
            ac = m.group(1)
            if ac in seen or ac in known or re.match(r"-\d", body[m.end():m.end() + 2]) or body[m.start() - 1:m.start()] in "\"“'":
                continue  # form names (DS-160) and quoted official statuses ("REFUSED") are not acronyms
            seen.add(ac)
            win = body[max(0, m.start() - 90): m.end() + 90]
            initials = "".join(w[0] for w in re.findall(r"\b[A-Z][a-z]+", body[max(0, m.start() - 90): m.start()]))
            expanded = f"({ac})" in win or re.search(re.escape(ac) + r"\s*\(", win) or ac in initials
            if not expanded:
                self.add("K06-acronym", "warn", None, ac, f"\"{ac}\" is not expanded on first use", f"write the full name first, then ({ac})")
        # trigram repetition (excluding entity names and stop-only phrases)
        names = {w.lower() for c in self.lm.get("children", []) for w in c.get("name", "").split()}
        names |= {w.lower() for p in self.sheet.get("products", []) for w in re.findall(r"[A-Za-z']+", p.get("display_name", ""))}
        names |= {w.lower() for p in (self.b.get("proper_nouns") or []) for w in str(p).split()}
        words_ = [w.lower() for w in re.findall(r"[A-Za-z']+", " ".join(b["text"] for b in self.blocks if b["type"] in ("p", "li")))]
        tri = Counter(tuple(words_[i:i + 3]) for i in range(len(words_) - 2))
        keep = " ".join([self.b.get("target_query") or ""] + list(self.b.get("secondary_queries") or [])
                        + list((self.research.get("semantic_graph") or {}).get("must_cover_entities") or [])).lower()
        for g, n in tri.most_common(12):
            content = [w for w in g if w not in STOP and w not in names and len(w) > 2]
            fact_norm = re.sub(r"[-–&/]", " ", self.fact_text)
            fact_norm = re.sub(r"\s+", " ", fact_norm)
            if " ".join(g) in keep or " ".join(g) in fact_norm:
                continue  # the target query, entity names and official product names are meant to repeat
            if n > 2 and len(content) >= 2:
                self.add("K07-trigram", "warn", None, " ".join(g), f"\"{' '.join(g)}\" used {n} times", "vary the phrasing or merge the sentences")
        # paragraphs: one idea, 2–4 sentences (warn above 5)
        for b in self.blocks:
            if b["type"] == "p" and len(sentences(b["text"])) > 5:
                self.add("K08-long-paragraph", "warn", b, b["text"][:120], f"{len(sentences(b['text']))} sentences in one paragraph",
                         "split at the natural boundary; 2–4 sentences per paragraph")
        # anchors carry the target's name
        names_by_url = {c["url"].rstrip("/"): c.get("name", "") for c in self.lm.get("children", [])}
        names_by_url.update({p["url"].rstrip("/"): p.get("name", "") for p in self.lm.get("products", [])})
        for b in self.blocks:
            for anchor, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", b.get("raw", "")):
                name = names_by_url.get(url.rstrip("/"))
                if name:
                    nt = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", name)}
                    if nt and not nt & {w.lower() for w in re.findall(r"[A-Za-z]{3,}", anchor)}:
                        self.add("K09-anchor", "warn", b, f"[{anchor}]({url})", f"anchor doesn't name the target (\"{name}\")",
                                 "use the target page's name in the anchor")

    def r_claims_of_scale(self):
        """Counts and superlatives must come from computed lists, not from eyeballing a table."""
        sup = r"\b(lightest|heaviest|cheapest|smallest|largest|biggest|roomiest|strongest|toughest|most durable|" \
              r"most popular|best[- ]selling|safest)\b"
        num_words = r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(of\s+(them|these|those)|[a-z]+s)\b"
        meta = [(None, str(self.meta.get(k, ""))) for k in ("title", "meta_description") if self.meta.get(k)]
        for b, s in list(self.prose(include_cells=True)) + meta:
            low = s.lower()
            m = re.search(sup, low)
            if m and not re.search(r"\b(listed|of those with|of the \w+ (here|above|below) with|among the)\b", low) \
                    and m.group(0) not in self.fact_text:
                self.add("N03-unsupported-superlative", "block", b, s, f"\"{m.group(0)}\" needs a computed ranking",
                         "state the basis (\"lightest of the bags with a listed weight\") from the pack's rankings, or cut it")
            m = re.search(num_words, low)
            if m and not re.search(r"\b(times|steps?|ways?|sides?|days?|weeks?|months?|years?|hours?|minutes?|conditions?|things?|"
                                   r"questions?|options?|sizes?|parts?|stages?|phases?)\b", m.group(0)):
                heads = " ".join(x["text"].lower() for x in self.blocks if x["type"].startswith("h"))
                in_heading = m.group(1) in heads or str(self.NUMW.get(m.group(1))) in re.findall(r"\d+", heads)
                if re.match(r"^(If|When|Once|Unless|Suppose|Say)\b", s):
                    continue
                follow = self._list_after(b) if b and s.rstrip().endswith(":") else 0
                n_want = self.NUMW.get(m.group(1))
                as_digit = f"{self.NUMW.get(m.group(1))} {m.group(2)}" if self.NUMW.get(m.group(1)) else ""
                word_in_fact = re.search(rf"\b{m.group(1)}\b|\b{self.NUMW.get(m.group(1), 'x')}\b", self.fact_text)
                if in_heading or m.group(0) in self.fact_text or (as_digit and as_digit in self.fact_text) or word_in_fact \
                        or self._enumerates(s, m.group(1)) \
                        or (follow and n_want and n_want <= follow <= n_want + 1) \
                        or self.NUMW.get(m.group(1)) in self._computed_counts() \
                        or re.search(r"\b(the|those|these|first|last|other|next|all|same|both)\s+$", low[:m.start()]):
                    # "the last two of those" points back at a list; it doesn't count anything new
                    continue
                # YMYL: a count that no fact states and the sentence doesn't spell out is how "five emirates"
                # slips in when the source lists six. Name the members, or copy a count a fact states.
                sev = "block" if (self.b.get("ymyl") is True) else "warn"
                self.add("N04-count-check", sev, b, s, f"count \"{m.group(0)}\": no fact states it and the sentence doesn't list the members",
                         "name the members instead of counting, or copy the count from \"Counts to copy\" or a fact")

    def _list_after(self, b) -> int:
        """How many list items directly follow this block (the members a "three cases:" lead-in announces)."""
        i = next((k for k, x in enumerate(self.blocks) if x is b), None)
        if i is None:
            return 0
        n = 0
        for x in self.blocks[i + 1:]:
            if x["type"] != "li":
                break
            n += 1
        return n

    NUMW = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12}

    def _computed_counts(self) -> set:
        """Counts the checks computed for the pack's "Counts to copy" (fit lists, wheels, listed weights)."""
        out = set()
        for res in (self.sheet.get("checks") or {}).values():
            if not isinstance(res, dict):
                continue
            out |= {len(v) for v in (res.get("fit_lists") or {}).values()}
            for k in ("weight_ranking", "weight_not_listed"):
                if res.get(k):
                    out.add(len(res[k]))
            attrs = res.get("attributes") or {}
            if attrs:
                out.add(len([a for a in attrs.values() if a.get("wheels")]))
                out.add(len(attrs))
        return out

    @classmethod
    def _enumerates(cls, s, word):
        """True when the sentence itself lists exactly that many members (after a colon or in brackets)."""
        n = cls.NUMW.get(word)
        for part in re.findall(r"\(([^)]*)\)|:\s*(.+)$", s):
            seg = next((p for p in part if p), "")
            items = [x for x in re.split(r",\s*|\s+(?:and|or)\s+", seg.rstrip(".")) if x.strip()]
            if n and n <= len(items) <= n + 1:
                return True
        return False

    def r_grounding(self):
        """A sentence that states a rule must be grounded in a verified fact (content overlap). Blocks on YMYL pages,
        warns elsewhere: unsourced rules sitting next to sourced ones were a judge's top complaint on every niche."""
        ymyl = self.b.get("ymyl") is True
        rule = re.compile(r"\b(must|has to|have to|need to|needs to|cannot|can't|won't|will not|only|refuses?|requires?|"
                          r"required|not allowed|doesn't|does not|never|always|has no|no public)\b", re.I)
        stop = STOP | {"your", "you", "will", "not", "only", "must", "need", "can", "cannot", "be", "do", "have"}
        syn = self.b.get("synonyms") or {}

        def tk(s):
            return {w for w in tokens(s, syn) if w not in stop and len(w) > 2}
        usable = [f for f in self.sheet.get("facts", []) if f.get("status") in SUPPORT]
        facts = [tk(" ".join([str(f.get("value", "")), str(f.get("claim", "")), " ".join(f.get("also") or [])]))
                 for f in usable]
        fnums = [(set(re.findall(r"\d+(?:\.\d+)?", str(f.get("value", "")) + " " + str(f.get("claim", "")))), fs)
                 for f, fs in zip(usable, facts)]
        facts += [tk(c["text"]) for c in self.sheet.get("client", {}).get("approved_claims", []) if c.get("seen_on_site", True)]
        prev_b, prev_s = None, ""
        for b, s in self.prose(include_cells=True):
            carry = prev_s if b is prev_b else ""
            prev_b, prev_s = b, s
            if not rule.search(s) or "](" in b.get("raw", "") and len(words(s)) < 8:
                continue
            if not ymyl and re.search(r"\b(if|when|once|until|unless)\b", s, re.I) and not re.search(r"\d", s):
                continue
            if not ymyl and not re.search(r"\d", s) and re.match(r"(Decide|Write|Choose|Pick|Start|Keep|Check|Make|List|"
                                                                 r"Ask|Plan|Use|Try|Avoid|Test|Set|Compare|Note|Look|Leave)\b", s):
                continue  # imperative advice is the author's judgement, not a rule to source
            st = tk(s)
            if carry and re.match(r"(That|This|So|Which|It)\b", s):
                # "That's the main reason not to book…" leans on the sentence before it; judge them together
                st |= tk(carry)
            if len(st) < 3:
                continue
            sn = set(re.findall(r"\d+(?:\.\d+)?", s))
            if sn and any(sn & ns and st & fs for ns, fs in fnums):
                continue
            # grounded when the sentence is mostly fact, or when it contains most of one fact's content
            # (a long sentence that carries a whole rule plus framing words is still that rule)
            best = max((max(len(st & f) / len(st), len(st & f) / len(f) if len(f) >= 4 else 0) for f in facts if f),
                       default=0)
            best = best if best < 0.6 else max(best, 0.35)
            if best < 0.35:
                self.add("G01-ungrounded-rule", "block" if ymyl else "warn", b, s,
                         f"states a rule but matches no verified fact (best overlap {best:.0%})",
                         "ground it in a fact from the pack (verify it in step 2 if needed), or cut it")

    META_RE = re.compile(r"\b(the (table|list|steps?|sections?|chart|figures?|guides?|links?) (below|above)|"
                         r"(below|above)(?= (shows?|lists?|explains?|covers?|sets? out|outlines?))|"
                         r"as (shown|explained|covered|mentioned|noted|described) (above|below|earlier)|covered (above|earlier)|"
                         r"\bthis (guide|article|post)\b|\bin this (guide|article|section|post)\b|read on\b|"
                         r"the sections? (that follow|below)|\b(the )?top[- ](recipes|results|pages|guides|articles|sites|ranking \w+)\b|"
                         r"\branking pages\b|\bthe serp\b|\bsearch results\b|\bmost (guides|recipes|articles|sites) online\b)", re.I)

    def r_meta(self):
        """Talk about the page itself ("the table below", "this guide") instead of the topic."""
        for b, s in self.prose(include_cells=False):
            m = self.META_RE.search(s)
            if m:
                self.add("H05-meta-commentary", "block", b, s, f"talks about the page (\"{m.group(0)}\")",
                         "say the thing itself; let headings and tables speak for themselves")

    def r_link_dump(self):
        """The page ends on a list of links instead of the last answer."""
        secs = [b for b in self.blocks if b["type"] == "h2"]
        if not secs:
            return
        last = secs[-1]
        body = [b for b in self.blocks if b.get("section") == last.get("section") and b["type"] in ("p", "li")]
        raw = " ".join(b.get("raw", "") for b in body)
        links = re.findall(r"\[([^\]]+)\]\(", raw)
        plain = len(words(re.sub(r"\[[^\]]+\]\([^)]*\)", " ", raw)))
        if len(links) >= 3 and plain < 25 * len(links) / 2:
            self.add("H06-link-dump", "warn", last, last["text"], f"the last section is mostly a list of {len(links)} links",
                     "end on the answer; put each link in the section where the reader needs it")

    def r_copy(self):
        """Eight or more words in a row lifted from a source or a ranking page, outside quotation marks."""
        def shingles(text, n=8):
            ws = re.findall(r"[a-z0-9£$€%']+", text.lower())
            return {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)
                    if sum(1 for w in ws[i:i + n] if w not in STOP and len(w) > 3) >= 4}
        from .domains import kind as _kind
        strict, auth = set(), set()
        for f in self.sheet.get("facts", []):
            if f.get("basis") == "client_page":
                continue  # the client's own words are the client's to reuse
            sh = shingles(str(f.get("value", "")))
            (auth if _kind(f.get("source_url") or "") in ("government", "international") else strict).update(sh)
        for pg in (self.research.get("competitor_scrape") or {}).get("pages", []):
            sh = shingles(" ".join(x for tp, x in pg.get("blocks", []) if tp in ("p", "li")))
            (auth if pg.get("kind") in ("government", "international") else strict).update(sh)
        serp = self.research.get("serp_intel") or {}
        asked = set()
        for q in (serp.get("paa") or []) + (serp.get("related") or []):
            asked |= shingles(q)
        strict -= asked
        auth -= asked
        if not strict and not auth:
            return
        ui = re.compile(r"\b(tap|select|click|go to|open|choose|scroll|press|toggle|turn on|turn off)\b", re.I)
        for b, s in self.prose(include_cells=True):
            names_out = re.sub(r"\b[A-Z][\w'’-]*(?:\s+(?:of|on|and|for|the|in|to|&)?\s*[A-Z][\w'’-]*){2,}", " ", unquote(s))
            own = shingles(names_out)
            hit = own & strict
            if hit and not ui.search(s):
                self.add("C03-copied-text", "block", b, s, f"copies a source word for word (\"{sorted(hit)[0]}…\")",
                         "say it in your own words, or quote it and name the source")
            elif own & auth and not ui.search(s):
                self.add("C03-copied-text", "warn", b, s, "repeats an authority's wording without quotation marks",
                         "quote the rule exactly (\"…\") or put it in your own words")

    # a named source, optionally with its acronym and its document: "The Debt Management Office (DMO) says",
    # "The HMRC factsheet adds", "FCA guidance on investing says"
    ATTRIB = re.compile(r"\b(according to\b|(?:[A-Z][\w.&'’-]*\s){0,3}[A-Z][\w.&'’-]*(?:'s|’s)?(?:\s\([A-Z]{2,}\))?"
                        r"(?:\s(?:[a-z][\w'’-]*\s){0,3}(?:factsheet|guide|guidance|newsletter|page|report|website|data|"
                        r"research|survey|study|table|figures|analysis|calculator|rules?|overview|notes?))?\s+"
                        r"(?:says|said|notes|adds|points out|explains|recommends|advises|warns|confirms|describes|states|"
                        r"suggests|calls|lists|puts it|frames|tells|defines|reports|finds|found|rates|gives|sets out|"
                        r"cautions|agrees|argues|observes)\b)")

    def r_attribution(self):
        """Source names in sentence after sentence read as a research paste, not an expert's page."""
        sents = [(b, s) for b, s in self.prose() if b["type"] in ("p", "li")]
        if len(sents) < 15:
            return
        hits = [(b, s) for b, s in sents if self.ATTRIB.search(s)]
        share = len(hits) / len(sents)
        if share > 0.10:
            self.add("H07-attribution-density", "block" if share > 0.15 else "warn", None,
                     f"{len(hits)} of {len(sents)} sentences name a source",
                     "group each source's facts in one paragraph: credit it once in the paragraph's first claim, and let "
                     "the following sentences from that same source stand on their own (U20 treats them as that "
                     "source's); name sources mid-paragraph only for opinions, findings or contested points", "")

    def r_heading_echo(self):
        """Sections that open by restating their own heading as a statement (a template readers notice)."""
        syn = self.b.get("synonyms") or {}
        echo = []
        cur = None
        for b in self.blocks:
            if b["type"] in ("h2", "h3"):
                cur = b
                continue
            if cur is not None and b["type"] == "p":
                first = sentences(b["text"])[0] if b["text"] else ""
                if re.match(r"^(yes|no)\b", first, re.I):
                    cur = None
                    continue
                h = {w for w in tokens(cur["text"], syn) if w not in STOP and len(w) > 2}
                f = {w for w in tokens(first, syn) if w not in STOP and len(w) > 2}
                if len(h) >= 3 and len(h & f) / len(h) >= 0.9:
                    echo.append((b, first))
                cur = None
        if len(echo) >= 4:
            for b, s in echo:
                self.add("H08-heading-echo", "warn", b, s, f"{len(echo)} sections open by restating their heading",
                         "open with the number, the condition, the action or the reason instead")

    def r_repeats(self):
        syn = self.b.get("synonyms") or {}
        steps = re.compile(r"^(open|tap|click|select|go to|choose|scroll|press|turn|toggle|enter|type|swipe|find)\b", re.I)
        sents = [(b, s, {w for w in tokens(s, syn) if w not in STOP and len(w) > 2}) for b, s in self.prose()
                 if b["type"] in ("p", "li") and not steps.match(s.strip())]
        flagged = set()
        first_h2 = next((b["section"] for b in self.blocks if b["type"] == "h2"), None)
        for i, (b1, s1, t1) in enumerate(sents):
            if len(t1) < 5 or (first_h2 is not None and b1.get("section") != first_h2 and
                               self.blocks.index(b1) < next(k for k, x in enumerate(self.blocks) if x.get("section") == first_h2)):
                continue
            for b2, s2, t2 in sents[i + 1:]:
                if b2.get("section") == b1.get("section") or len(t2) < 5 or s2 in flagged:
                    continue
                n1, n2 = set(re.findall(r"\d+(?:\.\d+)?", s1)), set(re.findall(r"\d+(?:\.\d+)?", s2))
                if n1 and n2 and n1 != n2:
                    continue
                if len(t1 & t2) / min(len(t1), len(t2)) >= 0.7:
                    flagged.add(s2)
                    self.add("E06-repeated-point", "warn", b2, s2, f"repeats a point made earlier (\"{s1[:80]}…\")",
                             "say it once, where it matters most")
        # the last sentence of each section: the same opening words three times is a template
        last = {}
        for b in self.blocks:
            if b["type"] in ("p", "li") and b.get("section") is not None:
                ss = sentences(b["text"])
                if ss:
                    last[b["section"]] = (b, ss[-1])
        heads = Counter(" ".join(s.lower().split()[:2]) for _, s in last.values() if len(s.split()) >= 2)
        for key, n in heads.items():
            if n >= 3:
                for b, s in last.values():
                    if " ".join(s.lower().split()[:2]) == key:
                        self.add("E07-closing-template", "warn", b, s, f"{n} sections end with \"{key}…\"",
                                 "end sections on their own last point, not the same move")
        frag, run_ = [], []
        for b in self.blocks + [{"type": "end"}]:
            if b["type"] == "li":
                ss = sentences(b.get("text", ""))
                if ss and len(words(ss[0])) <= 4 and not re.search(r"\d", ss[0]):
                    run_.append(b)
                continue
            if len(run_) >= 3:
                frag.append(run_)
            run_ = []
        for grp in frag:
            self.add("E09-fragment-bullets", "warn", grp[0], grp[0]["text"][:120],
                     f"{len(grp)} bullets open with a clipped fragment of the same shape",
                     "start each bullet with a full statement, or merge them into a sentence")
        orders = [(b, s) for b, s in last.values() if _base_verb_first(s) or re.match(r"^(If|When|Before)\b[^,]{3,60},\s+\w+\b", s)
                  and _base_verb_first(re.sub(r"^(If|When|Before)\b[^,]{3,60},\s+", "", s))]
        howto = bool(re.match(r"^how (to|do i|do you|can i)\b", (self.b.get("target_query") or "").lower()))
        if not howto and len(orders) >= max(3, len(last) // 2 + 1):
            for b, s in orders:
                self.add("E07-closing-template", "warn", b, s, f"{len(orders)} of {len(last)} sections close on an instruction",
                         "end some sections on the fact, the outcome or the reason instead of another tip")
        because = [(b, s) for b, s in last.values() if re.match(r"^[A-Z][a-z]+\b", s) and re.search(r",? because\b", s)
                   and not re.match(r"^(The|This|That|These|Those|It|They|You|Your|Our|We|A|An)\b", s)]
        if len(because) >= 3:
            for b, s in because:
                self.add("E07-closing-template", "warn", b, s, f"{len(because)} sections close on \"do X, because Y\"",
                         "end some sections on the fact or the outcome instead of another tip")
        # the brand's verdict as every section's last word ("In our view…", "We'd suggest…", "Our advice…"): however it
        # is phrased, the same move at the end of section after section is the template readers notice
        verdict = re.compile(r"^(?:(?:for|if|in|on|with)\b[^,]{0,60},\s+)?"
                             r"(in our (view|experience|opinion)|our (advice|view|take|verdict|recommendation|suggestion)|"
                             r"we('d| would) \w+|we (recommend|suggest|advise)|"
                             r"for most (people|readers|teams|businesses|owners|households))\b", re.I)
        # the verdict may close the section's last paragraph or open it ("We'd aim for November. …")
        verdicts = []
        for sec, (b, s) in last.items():
            ss = sentences(b["text"]) if b else []
            if verdict.match(s.strip()) or (ss and verdict.match(ss[0].strip())):
                verdicts.append((b, s if verdict.match(s.strip()) else ss[0]))
        if len(verdicts) >= 3:
            for b, s in verdicts[2:]:
                self.add("E07-closing-template", "block", b, s,
                         f"{len(verdicts)} sections end on the brand's verdict",
                         "keep the closing verdict where the reader faces a real choice (two sections at most); "
                         "elsewhere give the recommendation where the decision comes up and end on the section's last fact")
        rt = [(b, s) for b, s in self.prose() if re.search(r"\brather than\b|\binstead of\b", s, re.I)]
        if len(rt) > 2:
            for b, s in rt[2:]:
                self.add("H01-contrast-framing", "warn", b, s, f"\"rather than / instead of\" used {len(rt)} times",
                         "state what to do; drop the contrast where the reader didn't expect the other option")
        # "No." / "Yes." as a sentence of their own
        for b, s in self.prose():
            if re.fullmatch(r"(Yes|No)[.!]", s.strip()):
                self.add("E08-bare-yes-no", "warn", b, s, "one-word answer sentence",
                         "put the yes or no inside the answer: \"No, you can't…\"")

    def r_units(self):
        """Units the reader uses: imperial first on en-US pages, metric on others (a conversion in brackets is fine)."""
        loc = (self.b.get("locale") or "en-GB").lower()
        metric = re.compile(r"\d\s?(°c|cm|mm|km|kg|g|ml|litres?|liters?|metres?|meters?)\b", re.I)
        imperial = re.compile(r"\d\s?(°f|inch(es)?|ft|feet|foot|" + ("" if loc.startswith("en-gb") else "miles?|") + r"lbs?|pounds? (of|in weight)|oz|ounces?|gallons?|"
                              r"fl oz|yards?)\b|\d+\s?(\"|'')", re.I)
        for b, s in self.prose(include_cells=True):
            m, i = metric.search(s), imperial.search(s)
            if loc.startswith("en-us") and m and not (i and i.start() < m.start()):
                self.add("L03-locale-units", "warn", b, s, "metric figure first on an en-US page",
                         "lead with the US unit and put the metric one in brackets (\"50°F (10°C)\")")
            elif not loc.startswith("en-us") and i and not m:
                self.add("L03-locale-units", "warn", b, s, "imperial-only figure on a metric-locale page",
                         "give the metric figure (convert it, or use a source that states it)")

    def r_boundary(self):
        """"At least 1.6 mm" means 1.6 mm is allowed: writing "1.6 mm or less is illegal" flips the boundary.
        Facts that set a floor or a ceiling are compared with how the page words the same number."""
        num = r"(\d+(?:[.,]\d+)?)"
        floors, ceilings = set(), set()
        for f in self.sheet.get("facts", []):
            if f.get("status") not in SUPPORT:
                continue
            v = str(f.get("value", "")).lower()
            floors |= {m.group(2) for m in re.finditer(r"\b(at least|minimum(?: of)?|no less than|not less than)\s*[£$€]?" + num, v)}
            floors |= {m.group(1) for m in re.finditer(num + r"\s*\w*\s*or (more|above|over|higher)\b", v)}
            ceilings |= {m.group(2) for m in re.finditer(r"\b(no more than|not more than|up to|maximum(?: of)?|at most)\s*[£$€]?" + num, v)}
            ceilings |= {m.group(1) for m in re.finditer(num + r"\s*\w*\s*or (less|fewer|below|under|lower)\b", v)}
        floors -= ceilings
        ceilings -= floors
        for b, s in self.prose(include_cells=True):
            low = s.lower()
            for n in floors:
                if re.search(re.escape(n) + r"\s*\w*\s*or (less|lower|below|under|fewer)\b", low) or \
                        re.search(r"\b(at|of)\s+" + re.escape(n) + r"\s*\w*\s*or below\b", low):
                    self.add("A02-boundary", "block", b, s, f"the source sets {n} as a minimum (\"at least {n}\"): {n} itself is allowed",
                             f"say \"below {n}\" (or \"at {n} you are at the limit\")")
            for n in ceilings:
                if re.search(re.escape(n) + r"\s*\w*\s*or (more|above|over|higher)\b", low):
                    self.add("A02-boundary", "block", b, s, f"the source sets {n} as a maximum: {n} itself is allowed",
                             f"say \"over {n}\" (or \"at {n} you are at the limit\")")

    def r_table_source(self):
        i = 0
        while i < len(self.blocks):
            if self.blocks[i]["type"] != "tr":
                i += 1
                continue
            j = i
            while j < len(self.blocks) and self.blocks[j]["type"] == "tr":
                j += 1
            rows = self.blocks[i:j]
            body = " ".join(" ".join(r.get("cells", [])) for r in rows if not r.get("header"))
            around = " ".join(self.blocks[k].get("raw", "") for k in (i - 1, j) if 0 <= k < len(self.blocks))
            linked = "](" in " ".join(r.get("raw", "") for r in rows) or "](" in around
            named = re.search(r"\b(according to|source[sd]?:|from the|figures from|data from|sets out|gives|publishes)\b", around, re.I)
            if re.search(r"\d", body) and not linked and not named:
                self.add("T03-table-without-source", "warn", rows[0], strip_md(rows[0].get("raw", ""))[:120],
                         "a table of figures with no source next to it: a reader (or a fact-checker) can't trace its numbers",
                         "link the source in the sentence that introduces the table")
            i = j

    def r_link_matches_figure(self):
        """"15 colours" linked to a page that doesn't say 15: the reader (and a fact-checker) follows the link and
        finds nothing. When a sentence states a figure and links a page, some fact with that figure must come from
        that page."""
        by_num = {}
        for f in self.sheet.get("facts", []):
            if f.get("status") not in USABLE or not f.get("source_url"):
                continue
            txt = re.sub(r"(\d),(\d{3})\b", r"\1\2", str(f.get("value", "")) + " " + str(f.get("claim", "")))
            for n in set(re.findall(r"\d+(?:\.\d+)?", txt)):
                by_num.setdefault(n, set()).add(f["source_url"].split("#")[0].rstrip("/"))
        for b in self.blocks:
            if b["type"] not in ("p", "li"):
                continue
            for s in sentences(b.get("raw", "")):
                links = [u.split("#")[0].rstrip("/") for _, u in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", s)]
                if not links:
                    continue
                plain = re.sub(r"\]\([^)]*\)", "]", s)
                nums = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})\b", r"\1\2", plain))) - {"1", "2"}
                for n in nums:
                    srcs = by_num.get(n)
                    if srcs and not any(l in srcs for l in links):
                        self.add("U17-link-not-figure-source", "block", b, strip_md(s)[:200],
                                 f"{n} comes from {sorted(srcs)[0]}, but the sentence links another page",
                                 "link the page the figure comes from (or move the link to the words it supports)")
                        break

    ATTRIB_VERB = re.compile(r"\b(according to|says?|said|states?|recommends?|advises?|warns?|notes?|suggests?|explains?|"
                        r"rates?|treats?|lists?|gives?|sets? out|puts? it|reports?|found|finds|calls?)\b", re.I)

    def r_named_source_unlinked(self):
        """A sentence that credits a named publisher with a claim must let the reader open the page the claim is on.
        Publishers often have several pages: naming "the RHS" after linking one RHS page sends the reader (and any
        fact-checker) to the wrong page. So the page whose fact the sentence matches must be linked in the same
        section; a publisher that has no fact on the sheet must at least be linked in the paragraph."""
        from .domains import org_domain
        dom0 = org_domain(self.b.get("domain") or "x.invalid")
        syn = self.b.get("synonyms") or {}

        def tk(x):
            return {w for w in tokens(x, syn) if w not in STOP and len(w) > 2 and not w.isdigit()}
        def norm(u):
            return re.sub(r"^https?://(www\.)?", "", u.split("#")[0].split("?")[0].lower()).rstrip("/")

        def same_pub(a, b):
            da, db = org_domain(a), org_domain(b)
            return da == db or da.endswith("." + db) or db.endswith("." + da)
        generic = {"uk", "gov", "org", "com", "net", "co", "www", "service", "assets", "blog", "media", "info", "news",
                   "www2", "web", "en", "help", "support", "nutrition", "health", "home", "garden"}
        pubs = defaultdict(list)  # org label ("rhs") -> [(url, tokens)]
        for f in self.sheet.get("facts", []):
            u = (f.get("source_url") or "").split("#")[0].rstrip("/")
            if f.get("status") in USABLE and u.startswith("http") and org_domain(u) != dom0:
                label = org_domain(u).split(".")[0]
                if label not in generic and len(label) > 2:  # a label that is also an ordinary word names no one
                    pubs[label].append((u, tk(f"{f.get('value', '')} {f.get('claim', '')}")))

        named = self._source_names
        # links still to come in each block's H2 section: an intro that names the RHS before the section links its
        # page has still given the reader the page
        later_in_sec: dict[int, list[str]] = {}
        pending: list[tuple[int, list[str]]] = []
        for i, b in enumerate(self.blocks + [{"type": "h2"}]):
            if b["type"] == "h2":
                for j, _ in pending:
                    later_in_sec[j] = [u for k, ls in pending if k > j for u in ls]
                pending = []
            elif b["type"] in ("p", "li"):
                pending.append((i, re.findall(r"\]\((https?://[^)\s]+)\)", b.get("raw", ""))))
        seen: list[str] = []  # every link so far, in reading order
        for i, b in enumerate(self.blocks):
            if b["type"] not in ("p", "li"):
                continue
            raw = b.get("raw", "")
            para_links = re.findall(r"\]\((https?://[^)\s]+)\)", raw)
            for s in sentences(raw):
                plain = strip_md(s)
                if not self.ATTRIB_VERB.search(plain):
                    continue
                names = named(plain)
                hit = next((p for p in pubs if p in names), None)
                if hit:
                    own = re.findall(r"\]\((https?://[^)\s]+)\)", s)
                    if any(same_pub(u, pubs[hit][0][0]) for u in own):
                        continue  # the sentence links that publisher's page itself: the writer chose the page
                    # the page a reader would open: the paragraph's link to this publisher, else the nearest earlier one
                    near = [u for u in para_links if same_pub(u, pubs[hit][0][0])] or \
                        [u for u in seen if same_pub(u, pubs[hit][0][0])][-1:] or \
                        [u for u in later_in_sec.get(i, []) if same_pub(u, pubs[hit][0][0])][:1]
                    st = tk(plain)
                    best = max(pubs[hit], key=lambda x: len(st & x[1]) / (len(st) or 1))
                    score = len(st & best[1]) / (len(st) or 1)
                    if not near:
                        self.add("U18-named-source-unlinked", "block", b, plain,
                                 f"credits {hit.upper()} but no page of theirs is linked in or before this section",
                                 f"link the page the claim is on ({best[0]}), on this sentence")
                    elif score >= 0.35 and norm(best[0]) not in {norm(u) for u in near}:
                        self.add("U18-named-source-unlinked", "block", b, plain,
                                 f"credits {hit.upper()} with a claim that is on {best[0]}, but the nearest {hit.upper()} "
                                 f"link is {near[-1]}: a reader checking it opens the wrong page",
                                 f"link {best[0]} on this sentence, with an anchor that names that page")
                elif not para_links and re.search(r"\d", plain) and (names - {w.lower() for w in plain.split()[:1]}):
                    self.add("U18-named-source-unlinked", "warn", b, plain,
                             "a figure credited to a named source with no link in its paragraph",
                             "link the source page the figure is on, on the words the reader would check")
            seen += para_links

    @staticmethod
    def _source_names(plain: str) -> set[str]:
        """Ways a sentence can name a publisher, lower-cased: single capitalised words and acronyms ("RHS", "Wickes"),
        initials of a multi-word name ("Royal Horticultural Society" -> "rhs") and the name run together the way
        domains spell it ("Gardeners' World" -> "gardenersworld")."""
        # the first word counts too ("Salesforce reports…"): names are only ever matched against publishers' labels,
        # so "The" or "This" at the start can't match anything
        out = {w.lower() for w in re.findall(r"\b[A-Z][A-Za-z&-]+\b", plain)}
        for run in re.findall(r"(?:\b[A-Z][a-z]+(?:'s|s')?(?:\s+(?:of|for|and|the)\s+|\s+)?){2,}", plain):
            ws = re.findall(r"\b[A-Z][a-z]+", run)
            out.add("".join(w[0] for w in ws).lower())
            out.add("".join(ws).lower())
        return out

    def r_inherited_attribution(self):
        """A sentence that credits no one reads as the claim of the source credited just before it ("Gardeners' World
        says X. Use John Innes compost…" reads as Gardeners' World's advice). When the sentence's fact comes from a
        different publisher, a reader who checks the credited page won't find it. Lists and tables inherit the source
        of the paragraph that introduces them."""
        from .domains import org_domain
        dom0 = org_domain(self.b.get("domain") or "x.invalid")
        syn = self.b.get("synonyms") or {}

        def tk(x):
            return {w for w in tokens(x, syn) if w not in STOP and len(w) > 2 and not w.isdigit()}
        facts = []
        for f in self.sheet.get("facts", []):
            u = (f.get("source_url") or "").split("#")[0]
            if f.get("status") in USABLE and u.startswith("http"):
                facts.append((org_domain(u), u, tk(f"{f.get('value', '')} {f.get('claim', '')}"),
                              set(re.findall(r"\d+(?:\.\d+)?", str(f.get("value", ""))))))
        labels = {o.split(".")[0]: o for o, *_ in facts if len(o.split(".")[0]) > 2}

        def credited(raw_s, plain):
            for u in re.findall(r"\]\((https?://[^)\s]+)\)", raw_s):
                if org_domain(u) != dom0:
                    return org_domain(u)
            low = self._source_names(plain)
            known = next((o for lab, o in labels.items() if lab in low), None)
            if known:
                return known
            # a person, garden, firm or document named as the source ("Philippa Burrough plants…", "A US seller's blog
            # describes…"): the reader now attributes to them, not to the earlier source
            if (self.ATTRIB_VERB.search(plain) and low - {(plain.split() or [""])[0].lower()}) or \
                    re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+(?:\w+ly\s+)?[a-z]+s\b", plain) or \
                    re.search(r"\b\w+'s (blog|guide|site|page|article|book|advice|website|research|study|survey|report|"
                              r"team|method|data)\b", plain):
                return "named"
            return None
        ctx = None
        for b in self.blocks:
            if b["type"] in ("h1", "h2", "h3", "h4"):
                ctx = None
                continue
            if b["type"] not in ("p", "li", "tr"):
                continue
            # a reader carries the last source named in a section until another is named or the section ends
            raw = b.get("raw", "")
            units = [raw] if b["type"] == "tr" else sentences(raw)
            for s in units:
                plain = strip_md(s)
                who = credited(s, plain)
                if who:
                    ctx = who
                    continue
                if not ctx or ctx in (dom0, "named"):
                    continue
                st = tk(plain)
                nums = set(re.findall(r"\d+(?:\.\d+)?", plain))
                if len(st) < (4 if nums else 6):
                    continue  # "Fill the hole and firm the soil" is general practice, not anyone's claim

                def score(fact):
                    return len(st & fact[2]) / len(st) + (0.2 if nums and nums & fact[3] else 0)
                best = max(facts, key=score, default=None)
                if not best or best[0] in (ctx, dom0) or score(best) < 0.5:
                    continue

                def family(o):  # one government's sites read as one authority (state.gov / usembassy.gov, gov.uk / nidirect)
                    m = re.search(r"(?:^|\.)(gov(?:\.[a-z]{2})?)$", o)
                    return m.group(1) if m else o
                if family(best[0]) == family(ctx):
                    continue
                own = max((score(f) for f in facts if f[0] == ctx), default=0)
                if own >= score(best) - 0.1:
                    continue  # the credited source says much the same thing
                self.add("U20-inherited-attribution", "block", b, plain,
                         f"reads as {ctx}'s claim (credited just before), but it is on {best[1]}",
                         "name that source on this sentence by its usual name (\"the RHS advises…\"); it needs a link "
                         "only if U18 asks for one, so keep each page's links within the cap")

    def r_anchor_rules(self):
        """Koray Tuğberk Gübür's interlinking rules, the checkable part: an anchor names its target (never "click
        here"), no anchor text more than 3 times, one anchor never points at two pages; and the first sentence under a
        heading (the self-contained answer an AI engine quotes) carries no link."""
        by_text = defaultdict(set)
        count = Counter()
        generic = re.compile(r"^(click here|here|this (page|guide|article|post|link)|read more|find out more|learn more|"
                             r"more (info|information|here)|see (here|more)|this|link|website|our (guide|page|website))$", re.I)
        for b in self.blocks:
            for anchor, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", b.get("raw", "")):
                a = " ".join(anchor.lower().split())
                by_text[a].add(url.split("#")[0].rstrip("/"))
                count[a] += 1
                if generic.match(a):
                    self.add("U21-empty-anchor", "block", b, f"[{anchor}]({url})", "the anchor says nothing about the page it opens",
                             "anchor the link on the target page's main term")
        for a, n in count.items():
            if n > 3:
                self.add("U22-anchor-repeated", "block", None, a, f"the same anchor text is used {n} times (cap 3)",
                         "vary the wording or drop the extra links")
            if len(by_text[a]) > 1:
                self.add("U23-anchor-two-targets", "block", None, a, f"one anchor text points at {len(by_text[a])} different pages",
                         "give each page its own anchor (its main term)")
        prev_h = False
        for b in self.blocks:
            if b["type"] in ("h2", "h3"):
                prev_h = True
                continue
            if prev_h and b["type"] == "p":
                first = (sentences(b.get("raw", "")) or [""])[0]
                if "](" in first:
                    self.add("U24-link-in-answer-sentence", "warn", b, strip_md(first),
                             "a link in the first sentence under a heading (the answer an AI engine quotes on its own)",
                             "move the link to a later sentence in the paragraph")
            prev_h = False

    def r_heading_numbers(self):
        """A number in a question heading is a promise ("…over 10 years?"): the section must answer with it, or a fact
        must carry it. A 15-year average under a 10-year heading misstates its own evidence (RULES: a heading
        promises exactly what its section delivers)."""
        evidence = " ".join(f"{f.get('value', '')} {f.get('claim', '')}" for f in self.sheet.get("facts", [])
                            if f.get("status") in SUPPORT).lower()
        for b in self.blocks:
            if b["type"] not in ("h2", "h3") or not b["text"].rstrip().endswith("?"):
                continue
            # the number with its unit is the promise ("10 years", "7%", "3 months"); a bare number is too common to test
            for n, unit in re.findall(r"(\d+(?:\.\d+)?)\s*-?\s*(%|per cent|years?|months?|weeks?|days?|hours?|"
                                      r"minutes?|times|kg|g|mg|cm|mm|m|miles?|km)\b", b["text"].lower()):
                stem = re.escape(unit.rstrip("s")) if unit not in ("%", "per cent") else r"(?:%|per ?cent)"
                if not re.search(rf"(?<![\d.]){re.escape(n)}\s*-?\s*{stem}", evidence):
                    self.add("H11-heading-number-unanswered", "block", b, b["text"],
                             f"the heading asks about \"{n} {unit}\", but no fact gives a figure for {n} {unit}",
                             "word the heading to what the evidence answers (its real period, group or measure), "
                             "or Skip the question")

    def r_self_contained(self):
        """Answer engines lift the first sentence under a heading on its own (RULES 8b). "It is a tax wrapper…" means
        nothing out of context; "A stocks and shares ISA is a tax wrapper…" can be quoted as it stands."""
        prev_h = None
        for b in self.blocks:
            if b["type"] in ("h2", "h3"):
                prev_h = b
                continue
            if prev_h is not None and b["type"] in ("p", "li"):
                first = (sentences(b["text"]) or [""])[0].strip()
                if re.match(r"^(it|it's|its|this|that|these|those|they|they're|both|such|the latter|the former)\b",
                            first, re.I):
                    self.add("A03-answer-not-self-contained", "block", b, first,
                             f"the first sentence under \"{prev_h['text'][:60]}\" starts with a back-reference, so it "
                             "can't be quoted on its own", "name the subject in full (\"A stocks and shares ISA is…\")")
            prev_h = None if b["type"] in ("p", "li", "tr") else prev_h

    def r_yes_no_openers(self):
        heads = 0
        prev_h = False
        for b in self.blocks:
            if b["type"] in ("h2", "h3"):
                prev_h = True
                continue
            if prev_h and b["type"] == "p" and re.match(r"^(yes|no)\b", b["text"].strip(), re.I):
                heads += 1
                if heads > 2:
                    self.add("E08-yes-no-template", "warn", b, sentences(b["text"])[0],
                             f"{heads} sections open with \"Yes,\" or \"No,\"",
                             "lead with the fact itself here (\"Two eggs give about 13 g…\"); keep yes/no openers to two")
            prev_h = False

    def r_embedded_query(self):
        """The query pasted into a sentence as an embedded question ("The question of how much should I feed…")."""
        q = (self.b.get("target_query") or "").lower().strip()
        if not re.match(r"(how|what|when|where|why|which|who|can|do|does|is|are|should)\b", q):
            return
        for b, s in self.prose():
            low = re.sub(r"[^a-z0-9 ]", " ", s.lower())
            low = re.sub(r"\s+", " ", low)
            i = low.find(q)
            if i > 0:
                self.add("H09-embedded-query", "block", b, s, "the search query is pasted into the sentence",
                         "answer in natural grammar; the query belongs in the title and H1")

    def r_rhythm(self):
        """Sentence-length variety against the human pages that rank (burstiness)."""
        import statistics as st
        lens = [len(words(s)) for b, s in self.prose() if b["type"] == "p"]
        if len(lens) < 15:
            return
        sd, mean = st.pstdev(lens), st.mean(lens)
        target = rhythm_target(self.research)
        if round(sd, 1) < target:
            self.add("E03-rhythm", "warn", None, f"sentence-length SD {sd:.1f}, mean {mean:.1f}",
                     f"rhythm is more even than the human pages that rank (target SD ≥ {target:.1f})",
                     "join related ideas into longer, clause-rich sentences (a reason, a condition, a contrast); "
                     "don't reach for fragments")
        firsts = Counter((re.findall(r"[A-Za-z']+", s) or [""])[0].lower() for b, s in self.prose() if b["type"] == "p")
        top, cnt = firsts.most_common(1)[0]
        if cnt >= 5 and cnt / len(lens) >= 0.25:
            self.add("E05-opener-monotony", "warn", None, f"\"{top.capitalize()}\" starts {cnt} of {len(lens)} sentences",
                     "readers hear the same opening word over and over (human pages: about 1 in 7)",
                     "open some sentences with the subject's name, a condition's result, a time or a place instead")
        short = sum(1 for n in lens if n < 8) / len(lens)
        cap = short_target(self.research)
        if short > cap:
            self.add("E04-fragments", "warn", None, f"{short:.0%} of sentences under 8 words",
                     f"more clipped sentences than the human pages that rank (cap {cap:.0%}); punchy one-liners read as "
                     "rewritten AI copy", "merge most of them into the sentence they introduce or explain")
        if mean < 13:
            self.add("E03-rhythm", "warn", None, f"mean sentence length {mean:.1f}",
                     "sentences are choppy (RULES target 15–20 on average)", "join related short sentences")

    def r_research(self):
        """Checks against the research plugins: PAA coverage, query routing, entity coverage."""
        qmap = self.research.get("query_map") or {}
        kg = self.research.get("semantic_graph") or {}
        if not qmap and not kg:
            return
        stop = STOP | {"check", "how", "what", "can", "your", "online"}

        syn = self.b.get("synonyms") or {}

        def tk(s):
            return {w for w in tokens(re.sub(r"[()]", "", s), syn) if w not in stop and len(w) > 2}
        # a Skip whose only reason is "it belongs on its own page" can't stand once the current plan says to answer it
        # here (the plan was refreshed after the outline was written); other reasons (no reliable source, another
        # intent) still count
        answer_here = {r["query"].lower() for r in qmap.get("queries", []) if r.get("decision") in ("h2", "cover_in_section")}
        skips = [x["question"] for x in (self.research.get("outline") or {}).get("skips", [])
                 if not (x["question"].lower() in answer_here and
                         re.search(r"own page|separate page|deserves (its|a) (own|separate)", str(x.get("reason", "")), re.I))]
        heads = [b["text"] for b in self.blocks if b["type"] in ("h2", "h3")]
        paras = [b["text"] for b in self.blocks if b["type"] in ("p", "li", "tr")]

        def cov(q, texts):
            qt = tk(q)
            return max((len(qt & tk(t)) / max(1, len(qt)) for t in texts), default=0) if qt else 1
        deep = (self.sheet.get("research") or {}).get("mode") == "deep"
        opening = [b["text"] for b in self.blocks if b["type"] == "h1"] + paras[:1]
        for q in qmap.get("h2_questions", []):
            from .pagejob import COMMERCIAL
            covered = heads + paras
            if cov(q, covered) < 0.6 and cov(q, [" ".join(opening)]) < 0.75 and not (skips and cov(q, skips) >= 0.8):
                self.add("Q01-question-not-answered", "warn", None, q,
                         "lexical coverage check did not locate an answer to this question",
                         "check its coverage id; answer in a relevant section, table or FAQ, or explain the exclusion")
        # questions planned "inside a section" (PAA, related questions, competitors' shared questions) still need an
        # answer on the page: their own words, not just the topic, somewhere in the body
        units = [tk(t) for t in paras] + [tk(h) for h in heads]
        for r in qmap.get("queries", []):
            if r["decision"] != "cover_in_section" or not r.get("distinct_terms"):
                continue
            own = {t for t in tk(" ".join(r["distinct_terms"]))}
            isq = re.match(r"(how|what|why|which|where|when|who|can|could|should|do|does|is|are|will)\b", r["query"].lower())
            if not own or (not isq and len(own) < 2):
                continue  # a one-word keyword variant ("… calculator") is a word to use where it fits, not a question
            need = 1.0 if len(own) <= 2 else 0.67  # answered = its own words together in one paragraph or heading
            if not any(len(own & u) / len(own) >= need for u in units) and not (skips and cov(r["query"], skips) >= 0.8):
                strong = str(r.get("source", "")).startswith(("paa", "top_page_headings", "gsc"))
                self.add("Q03-planned-question-unanswered", "warn", None, r["query"],
                         "searchers ask this and the plan put it inside a section, but the page never answers it",
                         "answer it in a sentence or two in the closest section (or record a Skip line in the outline)")
        for r in qmap.get("queries", []):
            if r["decision"] == "drop" and str(r.get("reason", "")).startswith("never mentions the topic") \
                    and cov(r["query"], heads) >= 0.75:
                self.add("Q04-off-topic-heading", "warn", None, r["query"],
                         "this question drifted away from the topic (it never mentions it), yet it has a heading here",
                         "check relevance and page purpose; retain relevant information with a documented coverage decision")
            if r["decision"] == "separate_page" and r.get("distinct_terms") and cov(r["query"], heads) >= 0.85:
                self.add("Q02-belongs-elsewhere", "warn", None, r["query"],
                         "the automated query map suggested another page for this section",
                         "check the source context and user task; document why it belongs here or link the existing page")
        gsc = self.research.get("gsc_insights") or {}
        for r in (gsc.get("striking") or [])[:12]:
            if cov(r["query"], heads + paras) < 0.75:
                self.add("Q04-gsc-query-dropped", "block" if r["impressions"] >= 100 else "warn", None, r["query"],
                         f"the page shows for this in Search Console (position {r['position']}, {r['impressions']} impressions) "
                         "but the draft doesn't cover it", "cover it in a heading or opening sentence, in the searcher's words")
        title = (self.meta.get("title") or "").lower()
        for r in (gsc.get("low_ctr") or [])[:3]:
            if cov(r["query"], [title]) < 0.6:
                self.add("Q05-title-misses-query", "warn", None, r["query"],
                         f"ranks on page 1 with weak CTR ({r['ctr']:.1%}) and the title doesn't speak to it",
                         "make the title answer this query")
        must = kg.get("must_cover_entities") or []
        if must:
            text = " ".join(heads + paras).lower()
            hit = [e for e in must if e.lower() in text]
            if len(hit) < 0.5 * len(must):
                missing = [e for e in must if e not in hit][:10]
                self.add("Q03-entity-coverage", "warn", None, f"{len(hit)}/{len(must)} must-cover entities",
                         "the page covers less than half of the entities most top pages use",
                         "cover where relevant: " + ", ".join(missing))

    def r_length_total(self):
        body = " ".join(b["text"] for b in self.blocks)
        n = len(words(body))
        lo, hi = (self.b.get("word_range_effective") or self.b.get("word_range") or [0, 10 ** 6])
        if n < lo or n > hi:
            sev = "block" if (n < lo * 0.75 or n > hi * 1.25) else "warn"
            self.add("W01-word-count", sev, None, f"{n} words", f"outside word_range {lo}-{hi}", "trim or extend to fit the brief")
        # SERP display: titles past ~60 chars and descriptions past ~160 get cut mid-thought
        tl, md = len(str(self.meta.get("title", ""))), len(str(self.meta.get("meta_description", "")))
        if tl > 65:
            self.add("M01-title-length", "block" if tl > 70 else "warn", None, f"title {tl} chars", "Google cuts titles at about 60 characters",
                     "lead with the query and trim to 50-60 characters")
        if md and not 110 <= md <= 160:
            self.add("M02-meta-length", "block" if md > 170 or md < 80 else "warn", None, f"meta description {md} chars",
                     "aim for 120-160 characters so it isn't cut or padded", "rewrite to 120-160 characters")
        # YMYL: rules change, so the reader needs to know when the official pages were last checked
        if (self.b.get("ymyl") is True) and not re.search(r"\b(checked|reviewed|updated|verified)\b[^.\n]{0,40}\b(19|20)\d\d\b", self.md, re.I):
            self.add("T01-check-date", "warn", None, "no check date", "YMYL page doesn't say when the official sources were checked",
                     "add the month and year to the sources line, e.g. \"Official sources (checked October 2026):\"")

    def r_misc(self):
        body = " ".join(b["text"] for b in self.blocks)
        n = max(1, len(words(body)))
        dashes = body.count("—")
        if dashes > n / 150 + 1:
            self.add("E01-em-dash", "warn", None, f"{dashes} em dashes", "heavy em-dash use", "use commas, full stops or brackets")
        for b, s in self.prose():
            if "!" in s and not all(x.lower() in self.fact_text or x.isupper() for x in re.findall(r"\w+!", s)):
                self.add("E02-exclamation", "warn", b, s, "exclamation mark", "remove")


def lint_text(md: str, sheet: dict, link_map: dict, research: dict | None = None) -> dict:
    L = Linter(md, sheet, link_map, research)
    fs = L.run()
    by = Counter(f["rule"] for f in fs)
    return {"summary": {"block": sum(1 for f in fs if f["severity"] == "block"),
                        "warn": sum(1 for f in fs if f["severity"] == "warn"),
                        "by_rule": dict(sorted(by.items())),
                        "words": len(words(" ".join(b["text"] for b in L.blocks)))},
            "findings": fs}


def print_findings(res: dict, limit: int = 200) -> None:
    s = res["summary"]
    print(f"lint: {s['block']} block, {s['warn']} warn, {s['words']} words")
    for f in res["findings"][:limit]:
        sev = "B" if f["severity"] == "block" else "w"
        print(f"{sev} {f['id']} {f['rule']} L{f['line']}: {f['text'][:160]!r}\n     -> {f['reason']}" + (f" | fix: {f['fix']}" if f["fix"] else ""))
