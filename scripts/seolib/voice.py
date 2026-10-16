"""The author's view, information gain and the GEO evidence checks.

- The author's view (operator's rule, 16 Oct 2026): every page gives its author's own take in the first person, 2-3
  times (1-2 on a short page), in the top and middle of the page, never in the opening or its last part. A view is
  judgement from what the author knows ("I'd pick X for Y because Z"); it never claims first-hand experience the
  pipeline doesn't have ("I tested", "in my experience", "my clients"), unless the client's own experience notes say it.
- Information gain: the items the researchers found beyond page one are used (Google's information-gain patent,
  US 12,013,887; its helpful-content questions on original information and analysis).
- GEO (Aggarwal et al., arXiv 2311.09735): cited sources, quotations and statistics raised a page's visibility in AI
  answers by up to 40%. The page cites the sources it has, quotes 1-2 of them word for word, and every quote is exact.
"""
from __future__ import annotations

import re

FIRST = re.compile(r"\bI\b|\bI'(?:d|m|ve|ll)\b|\b[Mm]y\b|\bme\b")
EXPERIENCE = re.compile(
    r"\bI(?:'ve| have)? (?:tried|tested|used|bought|owned|installed|fitted|painted|visited|grown|planted|driven|ridden|"
    r"cooked|worn|repaired|fixed|built|treated|advised|handled|trialled|reviewed|run|managed)\b|"
    r"\bwhen I (?:was|did|had|tried|used|first|started|bought|painted|fixed)\b|"
    r"(?i:\bin (?:my|our) (?:own )?(?:experience|years|time|career|practice|tests?)\b)|"
    r"\bI've (?:spent|been|seen|worked|found|lost|saved)\b|\bmy (?:clients|customers|patients|students)\b|"
    r"\b\d+\s+years? (?:of|in) (?:experience|the (?:trade|industry|business))\b|"
    r"\bI (?:found|noticed|learned|discovered) (?:that |when |it )?")


CALC_SITE = re.compile(r"(?i)calc|convert")


def check_sites(lint) -> None:
    """Other online calculator websites are never named or linked (a bank's or a brand's own tool may be described,
    never linked: the link rules already refuse addresses outside the link map). The page never links to itself."""
    client = re.sub(r"^www\.", "", (lint.b.get("domain") or "").lower()).split("/")[0]
    rivals = {re.sub(r"^www\.", "", str(d).lower()) for d in (lint.b.get("competitor_sites") or [])}
    serp = (lint.research.get("serp_intel") or {}).get("organic") or []
    rivals |= {re.sub(r"^www\.", "", o.get("domain", "")) for o in serp if CALC_SITE.search(o.get("domain", ""))}
    rivals.discard(client)
    rivals.discard("")
    page = (lint.b.get("page_url") or "").rstrip("/")
    for b in lint.blocks:
        raw = b.get("raw") or b["text"]
        for u in re.findall(r"\]\((https?://[^)\s]+)\)", raw):
            host = re.sub(r"^www\.", "", u.split("/")[2].lower())
            if page and u.rstrip("/") == page:
                lint.add("U25-self-link", "block", b, u, "the page links to itself", "drop the link; keep the words")
            elif any(host == r or host.endswith("." + r) for r in rivals):
                lint.add("C04-calculator-site", "block", b, u, "a link to another online calculator website",
                         "drop the link and the site's name; state the point in your own words")
        for r in rivals:
            name = r.split(".")[0]
            if len(name) > 4 and re.search(rf"(?i)\b{re.escape(name)}\b|\b{re.escape(r)}\b", re.sub(r"\]\([^)]*\)", "]", raw)):
                lint.add("C04-calculator-site", "block", b, b["text"][:140], f"names another online calculator website "
                         f"({r})", "never name other calculator sites; state the point in your own words")


def check_required(lint) -> None:
    """What a section's heading promises is in it: a formula heading shows an equation, a worked example shows its
    figures. A table never talks about the reader's search ("What you searched")."""
    sections, cur = [], None
    for b in lint.blocks:
        if b["type"] in ("h2", "h3"):
            cur = [b, []]
            sections.append(cur)
        elif cur is not None:
            cur[1].append(b)
    for h, body in sections:
        text = " ".join(x.get("raw") or x["text"] for x in body)
        if re.search(r"(?i)\bformulae?\b|\bequation\b", h["text"]) and not re.search(r"=|\^|×|\*\*|\$\$|`", text):
            lint.add("F01-formula-missing", "block", h, h["text"], "the section is about a formula but never shows it",
                     "write the formula as an equation (A = P(1 + r/n)^(nt) style), define each term, fill it in once")
        if re.search(r"(?i)\bworked example\b|\bexample calculation\b", h["text"]) and \
                len(re.findall(r"\d[\d,.]*", text)) < 3:
            lint.add("F02-example-without-figures", "block", h, h["text"], "a worked example with no real figures",
                     "give the inputs, each step and the result as numbers from the facts")
    for b in lint.blocks:
        if b["type"] == "tr" and re.search(r"(?i)what you (searched|asked|typed)|search(ed)? (term|query)|your (query|search)",
                                           b["text"]):
            lint.add("H05-meta-commentary", "block", b, b["text"][:120], "the table talks about the reader's search",
                     "name the option in the first column (the frequency, the type), not the search")


def _unq(s: str) -> str:
    return re.sub(r"[\"“][^\"”]{1,400}[\"”]", " ", s)


def _norm(s: str) -> str:
    from .gain import _norm as n
    return n(s)


def _words(s: str) -> set[str]:
    from .gain import _content
    return _content(s)


def is_view(text: str) -> bool:
    return bool(FIRST.search(_unq(text)))


def check(lint) -> None:
    body = [b for b in lint.blocks if b["type"] in ("p", "li", "h2", "h3", "h4", "tr")]
    sizes = [len(b["text"].split()) for b in body]
    total = sum(s for b, s in zip(body, sizes) if b["type"] in ("p", "li", "tr")) or 1
    notes = lint.b.get("experience") or []
    notes = [_words(x) for x in (notes if isinstance(notes, list) else [notes]) if str(x).strip()]

    # 1. the author's view: how many, where, and no invented experience
    passages, pos, first_h2, last_h2_at, prev_view = [], 0, None, None, False
    for b, n in zip(body, sizes):
        if b["type"] == "h2":
            first_h2 = pos if first_h2 is None else first_h2
            last_h2_at = pos
        if b["type"] in ("p", "li") and is_view(b["text"]):
            if not (prev_view and b["type"] == "li"):
                passages.append((b, pos))
            prev_view = True
        elif b["type"] in ("p", "li", "tr"):
            prev_view = False
        if b["type"] in ("p", "li", "tr"):
            pos += n
        for s in re.split(r"(?<=[.!?])\s+", _unq(b["text"])) if b["type"] in ("p", "li") else []:
            m = EXPERIENCE.search(s)
            if m and not any(len(_words(s) & nw) / max(1, len(_words(s))) >= 0.4 for nw in notes):
                lint.add("V03-claimed-experience", "block", b, s, f"\"{m.group(0).strip()}\" claims first-hand "
                         "experience the page doesn't have (FTC rules on misrepresented experience; Google's trust "
                         "guidance)", "give the view as judgement from the facts (\"I'd pick X because…\"), or "
                         "attribute the experience to the person it came from")
    lo = 1 if total < 800 else 2
    if len(passages) < lo:
        lint.add("V01-author-view-count", "block", None, f"{len(passages)} first-person passage(s)",
                 f"the page gives no author's view (every page needs {lo}-3)", "where the plan says \"your view\", "
                 "add 2-4 sentences in the first person: what you'd pick or do and why, and when you'd choose otherwise")
    elif len(passages) > 3:
        for b, _ in passages[3:]:
            lint.add("V01-author-view-count", "block", b, b["text"][:160], f"{len(passages)} first-person passages; "
                     "at most 3", "keep the 3 strongest views; state the rest as facts")
    from .plan import VIEW_SHARE
    for b, at in passages:
        if first_h2 is None or at < first_h2:
            lint.add("V02-view-placement", "block", b, b["text"][:160], "the author's view is in the opening",
                     "the opening answers the query; move the view into a section in the top half of the page")
        elif at / total > VIEW_SHARE or (last_h2_at is not None and at >= last_h2_at and len(passages) > 0):
            lint.add("V02-view-placement", "block", b, b["text"][:160], "the author's view is in the last part of the "
                     "page", "move it to a section in the top or middle of the page, where the plan says \"your view\"")

    # 2. information gain: the items beyond page one are on the page
    facts = lint.sheet.get("facts") or []
    links = {u.rstrip("/") for u in re.findall(r"\]\((https?://[^)\s]+)\)", lint.md)}
    # only the items the plan placed under a heading they are about: an item no heading is about is left out
    gain = [f for f in facts if str(f.get("id", "")).startswith("gain:") and f.get("placed", True)]
    if gain:
        paras = [_words(b["text"]) for b in lint.blocks if b["type"] in ("p", "li", "tr")]
        used = [f for f in gain if (f.get("source_url") or "").rstrip("/") in links
                or any(len(_words(f.get("point", "")) & p) / max(1, len(_words(f.get("point", "")))) >= 0.5 for p in paras)]
        need = min(2, len(gain))
        if len(used) < need:
            left = [f["id"] for f in gain if f not in used]
            lint.add("IG01-no-information-gain", "block", None, f"{len(used)} of {len(gain)} items beyond page one used",
                     "the page says little that page one doesn't (Google's information-gain patent; helpful-content "
                     "questions on original information)", f"use at least {need - len(used)} more under their headings, "
                     "crediting who says it and linking the source: " + ", ".join(left[:8]))

    # 3. GEO: cite the sources the page has, quote 1-2 of them, quote exactly
    client = re.sub(r"^www\.", "", (lint.b.get("domain") or "").lower()).split("/")[0]
    host = lambda u: re.sub(r"^www\.", "", u.split("/")[2].lower()) if u.count("/") >= 2 else ""
    ext = {host(u) for u in links} - {client, ""}
    avail = {host(f["source_url"]) for f in facts if f.get("source_url") and f.get("status") in ("verified", "captured",
             "operator") and f.get("basis") != "client_page" and not str(f.get("id", "")).startswith(("offer:", "client"))}
    avail -= {client, ""}
    need = min(3, len(avail))
    if len(ext) < need:
        lint.add("G02-few-citations", "block", None, f"{len(ext)} outside source(s) cited, {len(avail)} available",
                 "cited sources raise a page's visibility in AI answers (GEO, up to 40%) and its trust",
                 "link the source on the words a reader would check, where its fact is used, with one of these exact "
                 "addresses (never another page of the site): " + ", ".join(
                     list(dict.fromkeys(f["source_url"] for f in facts if f.get("source_url")
                                        and host(f["source_url"]) in (avail - ext)))[:6]))
    # quotation marks pair left to right ("REFUSED" … "ISSUED" are two short quotes, not one long one)
    quotes = [(b, q) for b in lint.blocks if b["type"] in ("p", "li")
              for m in re.finditer(r"\"([^\"]*)\"|“([^”]*)”", b["raw"]) for q in [m.group(1) or m.group(2) or ""]
              if len(q.split()) >= 8]
    from .plan import quote_candidates
    if not quotes and quote_candidates(facts):
        lint.add("G03-no-quotation", "block", None, "no quotation on the page",
                 "a source's exact words, quoted and named, raise visibility in AI answers (GEO)",
                 "quote the plan's quote fact word for word in quotation marks, name and link its source")
    values = [_norm(str(f.get("value") or "")) for f in facts]
    for b, q in quotes:
        q = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", q)  # a link on the quoted words is not part of the quote
        nq = _norm(q)
        if q.rstrip().endswith("?"):
            continue  # a question people ask, not a source's words
        if nq and not any(nq in v for v in values):
            from .gain import quote_on_page
            if not any(quote_on_page(q, v) for v in values if v):
                lint.add("G04-misquote", "block", b, q[:160], "the quotation isn't the source's exact words (no fact "
                         "carries them)", "copy the words exactly from the fact's quote, or paraphrase without "
                         "quotation marks")
