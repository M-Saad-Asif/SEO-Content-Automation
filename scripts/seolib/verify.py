"""Independent fact-check (the last agent stage before DONE).

`build(rd)` lists every sentence of final.md that could state a fact, numbered C1..Cn, each with the links the
reader would follow and the closest verified fact. A fact-checker who did not write the page gives each one a
verdict in verify.md; `check(rd, text)` refuses a verify.md that skips a sentence or leaves one unsupported.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C
from .lint import USABLE, parse_md, sentences, strip_md
from .review import IMPERATIVE, _imperative, _toks

VERDICTS = ("SUPPORTED", "ADVICE", "FIXED", "CUT")


def _claims(rd: Path) -> list[dict]:
    md = (rd / "final.md").read_text(encoding="utf-8")
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    syn = (sheet.get("brief") or {}).get("synonyms") or {}
    facts = [f for f in sheet.get("facts", []) if f.get("status") in USABLE]
    approved = [c for c in (sheet.get("client") or {}).get("approved_claims", []) if c.get("seen_on_site", True)]
    facts += [{"id": c.get("id", "claim"), "claim": "approved client claim", "value": c["text"], "source_url": ""}
              for c in approved]
    ftok = [(f, _toks(f"{f.get('value', '')} {f.get('claim', '')}", syn)) for f in facts]
    _, blocks = parse_md(md)
    out, sec, sec_links = [], "intro", []
    for b in blocks:
        if b["type"] == "h2":
            sec, sec_links = b["text"], []
        if b["type"] in ("h3",):
            sec = b["text"]
        if b["type"] not in ("p", "li", "tr"):
            continue
        raw = b.get("raw", "")
        sec_links += re.findall(r"\]\((https?://[^)\s]+)\)", raw)
        units = [raw] if b["type"] == "tr" else sentences(raw)
        for s in units:
            plain = strip_md(s).strip()
            if len(plain.split()) < 5:
                continue
            if not re.search(r"\d", plain) and (IMPERATIVE.match(plain) or _imperative(plain)):
                continue  # advice addressed to the reader carries no fact of its own
            st = _toks(plain, syn)
            best = max(((len(st & ft) / ((len(st) * len(ft)) ** 0.5 or 1), f) for f, ft in ftok if ft),
                       key=lambda x: x[0], default=(0.0, None))
            out.append({"n": len(out) + 1, "section": sec, "sentence": plain,
                        "links": re.findall(r"\]\((https?://[^)\s]+)\)", s), "section_links": list(dict.fromkeys(sec_links)),
                        "fact": best[1], "match": round(best[0], 2)})
    return out


def build(rd: Path) -> int:
    cl = _claims(rd)
    C.save_json(rd / "verify_claims.json", [{k: v for k, v in c.items() if k != "fact"} for c in cl])
    W = [f"# Fact-check sheet: {rd.name}", "",
         f"{len(cl)} sentences from final.md that may state a fact. Give each a verdict in verify.md "
         "(format in plugins/fact_check/SKILL.md).", ""]
    for c in cl:
        W.append(f"## C{c['n']} [{c['section'][:60]}]")
        W.append(f"\"{c['sentence']}\"")
        if c["links"]:
            W.append(f"- links in the sentence: {', '.join(c['links'])}")
        elif c["section_links"]:
            W.append(f"- links in this section: {', '.join(c['section_links'][:6])}")
        f = c["fact"]
        if f and c["match"] >= 0.15:
            W.append(f"- closest verified fact `{f['id']}` ({c['match']:.0%}): \"{str(f.get('value', ''))[:400]}\""
                     + (f" — {f['source_url']}" if f.get("source_url") else "")
                     + (f" [applies to: {f['scope']}]" if f.get("scope") else ""))
        else:
            W.append("- no verified fact is close: open the linked page, or search, before you mark it SUPPORTED")
        W.append("")
    (rd / "verify_sheet.md").write_text("\n".join(W), encoding="utf-8")
    return len(cl)


def check(rd: Path, text: str) -> list[str]:
    cl = C.load_json(rd / "verify_claims.json") or []
    rows = {}
    for m in re.finditer(r"^\s*[-*|]?\s*\**C(\d+)\**\s*[|:—–-]+\s*\**([A-Z]+)\**(.*)$", text, re.M):
        rows[int(m.group(1))] = (m.group(2), m.group(3))
    probs = []
    missing = [c["n"] for c in cl if c["n"] not in rows]
    if missing:
        probs.append(f"no verdict for {len(missing)} sentence(s): " + ", ".join(f"C{n}" for n in missing[:30]))
    bad = [f"C{n} ({v})" for n, (v, _) in rows.items() if v not in VERDICTS]
    if bad:
        probs.append("verdicts must be one of " + "/".join(VERDICTS) + "; fix or cut these: " + ", ".join(bad[:20]))
    nourl = [f"C{n}" for n, (v, rest) in rows.items() if v == "SUPPORTED" and not re.search(r"https?://|`[\w:.-]+`", rest)]
    if nourl:
        probs.append("SUPPORTED needs the URL you checked or the fact id: " + ", ".join(nourl[:20]))
    return probs
