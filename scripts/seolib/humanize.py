"""What separates human writing from AI writing, from the University of Maryland / Google DeepMind research, as
checks a script can run on a draft (plugins/humanize/SKILL.md explains each one with its finding).

- IdeaLens (Rajendhran et al., 2026, arXiv 2610.06778): human ideas carry sources a reader can look up, details that
  pin down one case and could change the conclusion, numbers with context, the limits of a claim (when it applies
  and when it does not), costs, open problems and mixed results. AI ideas carry details that could apply to any
  subject (the commonest AI feature), made-up examples used as proof, sweeping claims from one case, every benefit
  at once, perfect or guaranteed solutions, forecasts that cannot be wrong, and reasons that restate the claim.
- StoryScope (Russell et al., 2026, arXiv 2604.03136): AI states its theme or lesson outright (77% vs 52% of
  stories), alludes vaguely instead of naming real works, places and brands (72% vs 50% vague allusions), and keeps
  structures tidy and uniform; surface style edits barely move detection (93.9 vs 95.5 macro-F1), so the signal is
  in ideas and structure, not word swaps.

Speed: each check names the sentence and the fix; the rules card tells the writer the same things before drafting,
so the checks rarely fire.
"""
from __future__ import annotations

import re

PERFECT = re.compile(r"(?i)\b(the perfect (solution|choice|way)|ideal solution|everything you need|all your needs|"
                     r"hassle[- ]free|stress[- ]free|worry[- ]free|peace of mind|one[- ]stop|best of both worlds|win[- ]win|"
                     r"no matter what|whatever your needs|for every need|second to none|like never before)\b")
FORECAST = re.compile(r"(?i)\bwill (always|never|definitely|certainly|undoubtedly|surely)\b|\b(is|are) (set|poised) to "
                      r"(transform|revolutioni[sz]e|change|redefine)\b|\bguaranteed to\b|\bwill transform\b")
VAGUE_AUTH = re.compile(r"(?i)\b(experts?|studies|research|surveys?|scientists|professionals|specialists|many people|"
                        r"most people|industry insiders|data)\s+(say|says|show|shows|suggest|suggests|agree|recommend|"
                        r"believe|found|finds|indicate|indicates|confirm|confirms)\b")
MADE_UP = re.compile(r"(?i)^(imagine|picture this|picture a|suppose|let'?s say|say you|consider (a|someone|this)|"
                     r"take (sarah|john|jane|tom|emma|alex)\b)|\b(meet|take) [A-Z][a-z]+, (a|an|who)\b")
MORAL = re.compile(r"(?i)^(the key takeaway|the takeaway|the bottom line|ultimately,|at the end of the day|in the end,|"
                   r"the lesson|the moral|all in all|to sum up|in short,|what this means is|the truth is|"
                   r"remember,|the real (value|reward|benefit))")
LIMIT = re.compile(r"(?i)\b(except|unless|does not apply|doesn't apply|do not apply|not suitable|isn't suitable|won't work|"
                   r"does not work|doesn't work|only if|only when|not covered|does not cover|doesn't cover|exception|"
                   r"falls outside|not for|limit(ation)?s?|cannot|can't be used|not recommended for|drawback|downside|"
                   r"costs? more|takes longer)\b")
STOP = set("a an the and or of to in on for with by from at as is are be it this that these those your you we our "
           "can will may has have had was were been its their there here which who what when how why".split())


def _specifics(lint) -> set[str]:
    """Word stems of the page's own nameable things: the topic's entities, the query, the headings, the facts, the
    client and its products. A sentence that shares none of them could sit on any page."""
    names = []
    kg = (lint.research.get("semantic_graph") or {})
    names += [e.get("name") or "" for e in ((kg.get("graph") or {}).get("entities") or [])[:80]]
    names += [e if isinstance(e, str) else e.get("entity", "") for e in kg.get("must_cover_entities") or []]
    names += [lint.b.get("target_query") or "", lint.b.get("client") or ""]
    names += [p.get("display_name", "") for p in lint.sheet.get("products", [])]
    names += [b["text"] for b in lint.blocks if b["type"] in ("h1", "h2", "h3")]
    names.append(lint.fact_text[:20000])
    return {w[:5] for n in names for w in re.findall(r"[a-z]{4,}", n.lower()) if w not in STOP}


def check(lint) -> None:
    body = [(b, s) for b, s in lint.prose() if b["type"] in ("p", "li")]
    if not body:
        return
    spec = _specifics(lint)
    generic = []
    for b, s in body:
        low = s.lower()
        if PERFECT.search(s):
            lint.add("HU02-perfect-solution", "block", b, s, "a perfect, all-needs or guaranteed solution (an AI pattern in "
                     "IdeaLens: every benefit at once, nothing costs anything)", "say what it does, for whom, and what it "
                     "doesn't do or costs")
        if FORECAST.search(s):
            lint.add("HU03-unconditional-forecast", "block", b, s, "a forecast that cannot be wrong (an AI pattern in "
                     "IdeaLens)", "state the condition under which it happens, from a fact, or cut it")
        if VAGUE_AUTH.search(s) and not re.search(r"\]\(https?://|\b[A-Z]{2,}\b|\b[A-Z][a-z]+ (says|found|reports)", s):
            lint.add("HU04-vague-authority", "block", b, s, "an unnamed authority (\"experts say\", \"studies show\"): "
                     "human writing names a source the reader can look up (IdeaLens)", "name and link the source, or "
                     "state the fact from the brief without the crowd")
        if MADE_UP.search(s.strip()):
            lint.add("HU05-made-up-example", "block", b, s, "an invented scenario used as proof (the strongest AI idea "
                     "pattern in IdeaLens)", "use a worked example built from the facts, with real figures, or cut it")
        if MORAL.search(s.strip()):
            lint.add("HU06-stated-lesson", "block", b, s, "states the lesson or theme outright (StoryScope: AI 77% vs "
                     "human 52%)", "cut it: the facts already make the point")
        m = re.search(r"(?i)^(.{12,}?),?\s+because\s+(.{8,})$", s)
        if m:
            a = {w for w in re.findall(r"[a-z]{4,}", m.group(1).lower())} - STOP
            r = {w for w in re.findall(r"[a-z]{4,}", m.group(2).lower())} - STOP
            if r and len(a & r) / len(r) >= 0.6:
                lint.add("HU07-circular-reason", "warn", b, s, "the reason repeats the claim (IdeaLens: a reason that "
                         "restates the claim reads as AI)", "give the reason the reader doesn't already have, or none")
        # could this sentence sit on any page? no figure, no name, none of the topic's entities
        if len(s.split()) >= 10 and not re.search(r"\d", s) and not re.search(r"(?<=\s)[A-Z][a-z]{2,}", s) \
                and not ({w[:5] for w in re.findall(r"[a-z]{4,}", low)} & spec):
            generic.append((b, s))
    share = len(generic) / len(body)
    if generic and share > 0.12:
        for b, s in generic[:8]:
            lint.add("HU01-could-be-any-page", "block", b, s, f"could sit on any page about anything ({share:.0%} of "
                     "sentences; IdeaLens's commonest AI feature)", "anchor it to this topic: a figure, a named thing, "
                     "the case it applies to, or cut it")
    elif generic:
        for b, s in generic[:5]:
            lint.add("HU01-could-be-any-page", "warn", b, s, "could sit on any page about anything", "anchor it, or cut it")
    words = sum(len(s.split()) for _, s in body)
    if words >= 700 and not any(LIMIT.search(s) for _, s in body):
        lint.add("HU08-no-limits", "block", None, f"{words} words, no limit stated",
                 "the page never says when its advice doesn't apply, what it costs or what it can't do (human writing "
                 "does: IdeaLens)", "state the limits the facts give: who it doesn't suit, when it doesn't apply, its "
                 "cost or drawback")
