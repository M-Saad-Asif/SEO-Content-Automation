"""Mechanical fixes applied to the draft by script before it is checked, so they never cost a fix round.

Only rewrites that keep the meaning exactly are made here:
- Koray rule 10, "if" goes second: "If rain is due, wait for a dry day." -> "Wait for a dry day if rain is due."
  (only a plain "If A, B." sentence: one condition, one main clause, no question, no quote, no link inside).
- Koray rule 3, fluff words: "in order to" -> "to"; "basically", "actually", "needless to say", "as a matter of
  fact", "it is important to note that" are cut.
Anything less certain is left to the writer.
"""
from __future__ import annotations

import re

FLUFF = [(re.compile(r"\bin order to\b", re.I), "to"),
         (re.compile(r"\b(?:basically|actually|needless to say|as a matter of fact|it goes without saying that),?\s+", re.I), ""),
         (re.compile(r"\b(?:it is|it's) important to note that\s+", re.I), "")]
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(*])")


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _invert_if(sentence: str) -> str:
    m = re.match(r"^If ([^,]{3,140}), ([^,].+?)([.!])$", sentence)
    if not m or "[" in sentence or "\"" in sentence or "“" in sentence:
        return sentence
    cond, main, end = m.group(1), m.group(2), m.group(3)
    if len(main.split()) < 2 or re.match(r"(?i)(then|so|and|but|or|which|this)\b", main) or "?" in main:
        return sentence
    first = main.split()[0]
    if not (first.isupper() or (first[:1].isupper() and first[1:].islower() and first.lower() not in
                                ("the", "a", "an", "it", "you", "your", "this", "that", "there", "check", "use", "wait",
                                 "choose", "call", "ask", "apply", "allow", "replace", "clean", "shut", "turn", "hold",
                                 "wash", "book", "pick", "keep", "add", "test", "start", "stop", "leave", "let", "give",
                                 "make", "take", "get", "put", "move", "open", "close"))):
        main = main[:1].lower() + main[1:]  # a common word, not a name, starts the moved clause
    return f"{_cap(main)} if {cond}{end}"


def _prose_lines(lines: list[str]):
    """(index, prefix, sentences, first-under-a-heading) for each prose line; front matter, headings, tables, code
    and quotes are skipped."""
    in_front, after_heading = False, True
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_front = True
            continue
        if in_front:
            in_front = line.strip() != "---"
            continue
        if line.lstrip().startswith("#"):
            after_heading = True
            continue
        if not line.strip() or line.lstrip().startswith(("|", "```", ">")):
            continue
        prefix = re.match(r"^(\s*(?:[-*]|\d+[.)])\s+)?", line).group(0)
        yield i, prefix, SENT.split(line[len(prefix):]), after_heading
        after_heading = False


def fix_text(md: str) -> tuple[str, int]:
    """(fixed markdown, number of changes). Headings, tables, front matter and code are left alone.

    "If" openers are an allowance, not a ban (lint.ALLOWANCE: about one per 500 words, at least 3): only the one
    that opens a section (the direct answer) and the ones past the allowance are turned round, so pages keep the
    few a human writer uses."""
    lines = md.splitlines()
    prose = list(_prose_lines(lines))
    n_words = sum(len(" ".join(parts).split()) for _, _, parts, _ in prose) or 1
    cap = max(3, round(n_words / 500))
    cands = [(i, j, first and j == 0) for i, _, parts, first in prose for j, p in enumerate(parts) if _invert_if(p) != p]
    hard = [c for c in cands if c[2]]
    soft = [c for c in cands if not c[2]]
    flip = {(i, j) for i, j, _ in hard + soft[max(0, cap - len(hard)):]}
    n = 0
    for i, prefix, parts, _ in prose:
        new = []
        for j, p in enumerate(parts):
            q = p
            for rx, rep in FLUFF:
                q = rx.sub(rep, q)
            if (i, j) in flip:
                q = _invert_if(q)
            if q != p:
                n += 1
                q = _cap(q) if p[:1].isupper() else q
            new.append(q)
        lines[i] = prefix + " ".join(new)
    return "\n".join(lines) + ("\n" if md.endswith("\n") else ""), n
