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


def fix_text(md: str) -> tuple[str, int]:
    """(fixed markdown, number of changes). Headings, tables, front matter and code are left alone."""
    out, n, in_front = [], 0, False
    for i, line in enumerate(md.splitlines()):
        if i == 0 and line.strip() == "---":
            in_front = True
            out.append(line)
            continue
        if in_front:
            out.append(line)
            if line.strip() == "---":
                in_front = False
            continue
        if not line.strip() or line.lstrip().startswith(("#", "|", "```", ">")):
            out.append(line)
            continue
        prefix = re.match(r"^(\s*(?:[-*]|\d+[.)])\s+)?", line).group(0)
        body = line[len(prefix):]
        parts = SENT.split(body)
        new = []
        for p in parts:
            q = p
            for rx, rep in FLUFF:
                q = rx.sub(rep, q)
            q = _invert_if(q)
            if q != p:
                n += 1
                q = _cap(q) if p[:1].isupper() else q
            new.append(q)
        out.append(prefix + " ".join(new))
    return "\n".join(out) + ("\n" if md.endswith("\n") else ""), n
