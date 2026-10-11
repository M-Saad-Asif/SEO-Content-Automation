"""`seo.py review <run>`: the editor's pass, made concrete.

Lint checks wording. The mistakes blind judges still found were about meaning: a claim that stretched its source,
dropped a condition, applied a group's advice to everyone, repeated itself, or left out a topic every top page
covers. This puts each claim next to the fact it rests on, so the writer compares meaning, not words, and shows
the page's shape (how each section opens and ends) so templates are visible. Niche-free: it only reads the run.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C
from .lint import STOP, USABLE, load_research, parse_md, sentences, strip_md
from .nlp import tokens

RULEISH = re.compile(r"\b(must|need|needs|should|cannot|can't|only|always|never|every|legal|illegal|law|required|"
                     r"recommend\w*|advise\w*|safe|unsafe|risk|limit|minimum|maximum|at least|up to|more than|less than|"
                     r"as much as|most|best|guarantee\w*|warrant\w*|free|includes?|covers?)\b", re.I)


IMPERATIVE = re.compile(r"^(decide|write|choose|pick|start|keep|check|make|list|ask|plan|use|try|avoid|test|set|"
                        r"book|compare|note|look|read|leave|stop|wait|put|add|give|take|find|start|open|tap|go)\b", re.I)


def _imperative(s: str) -> bool:
    """Starts with a bare verb ("Move to a CRM once…"): the author's advice."""
    try:
        from .lint import _NLP
        import spacy
        nlp = _NLP or spacy.load("en_core_web_sm", disable=["ner"])
        d = nlp(s[:80])
        return len(d) > 1 and d[0].tag_ == "VB"
    except Exception:
        return False


def _toks(s: str, syn: dict) -> set:
    return {w for w in tokens(s, syn) if w not in STOP and len(w) > 2}


def review(rd: Path) -> Path:
    md_path = rd / "draft.md" if (rd / "draft.md").exists() else rd / "final.md"
    md = md_path.read_text(encoding="utf-8")
    sheet = C.load_json(rd / "fact_sheet.json")
    research = load_research(rd)
    b = sheet.get("brief", {})
    syn = b.get("synonyms") or {}
    meta, blocks = parse_md(md)
    facts = [f for f in sheet.get("facts", []) if f.get("status") in USABLE]
    claims = [c for c in sheet.get("client", {}).get("approved_claims", []) if c.get("seen_on_site", True)]
    # approved client claims are sources too ("over 10,000 businesses" rests on one)
    facts = facts + [{"id": c.get("id", "claim"), "claim": "approved client claim", "value": c["text"]} for c in claims]
    ftok = [(f, _toks(" ".join([str(f.get("value", "")), str(f.get("claim", ""))]), syn)) for f in facts]
    client = b.get("client") or ""
    aliases = [a for a in [client] + list(b.get("client_aliases") or []) if a]

    W = [f"# Editor's review: {md_path.name}", "",
         "Read each item and fix the draft in place. For every claim, ask: does my sentence say what the source says, "
         "for the same group, with the same condition and the same strength? A low match means the claim needs a "
         "fact, a rewrite, or cutting.", ""]

    # 1. claim map
    W += ["## 1. Claims and the facts they rest on", ""]
    n_check = 0
    sec = "intro"
    for blk in blocks:
        if blk["type"] in ("h2", "h3"):
            sec = blk["text"]
        if blk["type"] not in ("p", "li", "tr"):
            continue
        units = [strip_md(c) for c in blk.get("cells", [])] if blk["type"] == "tr" else sentences(blk["text"])
        if blk["type"] == "tr":
            units = [" | ".join(units)]
        for s in units:
            if not (re.search(r"\d", s) or RULEISH.search(s)):
                continue
            if re.match(r"^(official )?sources?\b", s, re.I) or re.search(r"\bchecked (in )?[A-Z][a-z]+ (19|20)\d\d\b", s):
                continue  # the sources line
            if not re.search(r"\d", s) and (IMPERATIVE.match(s) or _imperative(s)):
                continue  # your own advice ("Decide which fields you need…") rests on judgement, not a fact
            st = _toks(s, syn)
            if len(st) < 3:
                continue
            s_nums = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})\b", r"\1\2", s))) - {"1", "2", "3"}

            def f_nums(f):
                return set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})\b", r"\1\2",
                                                              str(f.get("value", "")) + " " + str(f.get("claim", "")))))
            scored = sorted(((len(st & ft) / (len(st) * len(ft)) ** 0.5 + (0.3 if s_nums & f_nums(f) else 0), f)
                             for f, ft in ftok if ft), key=lambda x: -x[0])
            best, bf = scored[0] if scored else (0.0, None)
            second = scored[1][1] if len(scored) > 1 else None
            nums = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})\b", r"\1\2", s)))
            fnums = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})\b", r"\1\2", " ".join(
                str((x or {}).get(k, "")) for x in (bf, second) for k in ("value", "claim")))))
            other_nums = set(re.findall(r"\d+(?:\.\d+)?", " ".join(str(f.get("value", "")) for f in facts)))
            fnums |= nums & other_nums  # a number that another fact carries is sourced; the meaning is still yours to check
            try:
                from .lint import _derived
                para = blk.get("text") or s
                srcnums = {float(x) for x in other_nums if re.fullmatch(r"\d+(?:\.\d+)?", x)}
                fnums |= {n for n in nums if _derived(float(n), para, srcnums)}  # shown arithmetic
            except Exception:
                pass
            flag = bool(best < 0.35 or (nums and bf is not None and not nums <= fnums))
            n_check += flag
            W.append(f"- {'**CHECK** ' if flag else ''}[{sec[:50]}] \"{s[:220]}\"")
            if bf:
                W.append(f"  - closest fact `{bf['id']}` ({min(best, 1.0):.0%} match) — {str(bf.get('claim', ''))[:140]}: "
                         f"\"{str(bf.get('value', ''))[:260]}\"" + (f" [applies to: {bf['scope']}]" if bf.get("scope") else ""))
                if nums and not nums <= fnums:
                    W.append(f"  - numbers not in that fact: {', '.join(sorted(nums - fnums))} (another fact, a shown sum, or a mistake?)")
            else:
                W.append("  - no fact matches: verify it, or cut it")
    W.append("")

    # 2. the client
    if aliases:
        alias_re = re.compile(r"\b(" + "|".join(re.escape(a) for a in aliases) + r"|we|our)\b", re.I)
        lines = [s for blk in blocks if blk["type"] in ("p", "li") for s in sentences(blk["text"]) if alias_re.search(s)]
        if lines:
            W += ["## 2. What the page says about the client", "",
                  "Each must match an approved claim word for word in meaning, with its conditions (\"on screen repairs\", "
                  "\"from £…\", asterisks). Approved claims:"]
            W += [f"  - \"{c['text']}\"" for c in claims] or ["  - (none)"]
            W += [f"- \"{s[:220]}\"" for s in lines] + [""]

    # 3. shape: how each section opens and ends
    W += ["## 3. How each section opens and ends", "",
          "If several openings or endings follow the same pattern (the same first words, a yes/no, a warning, a link "
          "sentence), rewrite some so each section starts and ends on its own point.", ""]
    cur, first, last = None, {}, {}
    for blk in blocks:
        if blk["type"] in ("h2", "h3"):
            cur = blk["text"]
            continue
        if cur and blk["type"] in ("p", "li"):
            ss = sentences(blk["text"])
            if ss:
                first.setdefault(cur, ss[0])
                last[cur] = ss[-1]
    for h in first:
        W += [f"- **{h}**", f"  - opens: \"{first[h][:160]}\"", f"  - ends: \"{last[h][:160]}\""]
    W.append("")

    # 4. what the top pages share that the page doesn't
    kg = research.get("semantic_graph") or {}
    comp = research.get("competitor_scrape") or {}
    n_pages = len(comp.get("pages", [])) or 1
    heads = " ".join(blk["text"] for blk in blocks if blk["type"].startswith("h"))
    body = " ".join(blk["text"] for blk in blocks if blk["type"] in ("p", "li", "tr"))
    ht, bt = _toks(heads, syn), _toks(body, syn)
    miss = []
    for tp in kg.get("heading_topics", [])[:15]:
        tt = _toks(tp["topic"], syn)
        if tp["domains"] >= max(2, 0.4 * n_pages) and tt and len(tt & (ht | bt)) < 0.6 * len(tt):
            miss.append(f"- \"{tp['topic']}\" ({tp['domains']}/{n_pages} top pages)")
    words_num = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
                 "nine": "9", "ten": "10", "twelve": "12", "fifteen": "15", "twenty": "20", "thirty": "30"}
    body_n = re.sub(r"\b(" + "|".join(words_num) + r")\b", lambda m: words_num[m.group(1).lower()], body, flags=re.I)
    figs = [r for r in kg.get("consensus_figures", []) if r["figure"].split()[0] not in body_n][:8]
    if miss or figs:
        W += ["## 4. What readers expect that the page may be missing", ""]
        W += miss
        if figs:
            W.append("Figures several top pages state that the page doesn't (cover them if they answer the reader, "
                     "verified as facts first):")
            W += [f"- {r['figure']} ({len(r['domains'])} sites), e.g. \"{r['examples'][0]['sentence'][:160]}\"" for r in figs]
        W.append("")

    out = rd / "review.md"
    out.write_text("\n".join(W) + "\n", encoding="utf-8")
    print(f"REVIEW: {n_check} claim(s) to check, {len(first)} sections, {len(miss)} topic gap(s) -> {out.as_posix()}")
    return out
