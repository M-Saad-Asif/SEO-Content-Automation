"""Independent fact-check (the last agent stage before DONE).

`build(rd)` lists every sentence of final.md that could state a fact, numbered C1..Cn, each with the links the
reader would follow and the closest verified fact. A fact-checker who did not write the page gives each one a
verdict in verify.md; `check(rd, text)` refuses a verify.md that skips a sentence or leaves one unsupported.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C
from .lint import SUPPORT, parse_md, sentences, strip_md
from .review import IMPERATIVE, _imperative, _toks

VERDICTS = ("SUPPORTED", "ADVICE", "FIXED", "CUT", "OK", "UNSURE")

# lines where an error costs the reader money, health, legal standing or safety, or where the page does maths
SENSITIVE = re.compile(
    r"=|×|\^|÷|\b\d+(?:\.\d+)?\s?%|[£$€₹]\s?\d"                                   # maths, percentages, money
    r"|\d[^.]{0,40}\b(rate|interest|tax\w*|allowance|limit|dose|dosage|mg|years?|months?)\b"   # a figure with its unit
    r"|\b(rate|interest|tax\w*|allowance|limit|dose|dosage)\b[^.]{0,40}\d"
    r"|\b(illegal|penalt\w*|deadline|must not|never (?:use|mix|take)|danger\w*|poison\w*)\b"  # rules and safety
    # a tax, benefit or legal rule stated without a number ("salary sacrifice saves National Insurance, not income tax")
    r"|\b(tax\w*|national insurance|relief|allowance|benefit|entitle\w*|eligib\w*|exempt\w*|deductible|liable)\b"
    r"[^.]{0,60}\b(only|not|no longer|rather than|instead of|cannot|can't|must|always|never|since|from)\b", re.I)


def build_fast(rd: Path, cap: int = 15) -> int:
    """The fact-check sheet for the one-flow pass: only the lines where a mistake would hurt (formulas and worked
    sums first, then figures no fact closely matches, then money, rates, doses, legal and safety rules), at most
    `cap`, each with its closest fact. A page with none needs no pass."""
    cl = [c for c in _claims(rd, "draft.md") if SENSITIVE.search(c["sentence"])]
    # a line the site's own rates data already states is checked: its figures sit together in one clause of the data
    # ("20% up to 37,700"), its year is the data's year, and it does no sum (a worked example can add up wrong from
    # the right rates). Figures the data holds in different clauses may be paired wrongly ("45% above £37,700"), so
    # those lines, and everything the data doesn't hold, keep this pass
    from .siterates import numbers
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    rates = [(numbers(f.get("value")), numbers(f.get("condition")),
              [numbers(x) for x in re.split(r";|,\s", str(f.get("value") or ""))],
              _toks(f"{f.get('value')} {f.get('claim')}", {}))
             for f in sheet.get("facts", []) if f.get("basis") == "site_rates"]

    def in_rates(c) -> bool:
        s = c["sentence"]
        figs = numbers(s)
        if not rates or not figs or re.search(r"=|×|\^|÷|\bformula\b", s):
            return False
        st = _toks(s, {})
        for nums, years, clauses, tk in rates:
            rest = figs - years
            if len(st & tk) >= 2 and figs <= nums | years and \
                    (len(rest) <= 1 or any(rest <= cl for cl in clauses)):
                return True
        return False
    by_data = [c for c in cl if in_rates(c)]
    cl = [c for c in cl if c not in by_data]

    def rank(c):
        s = c["sentence"]
        maths = bool(re.search(r"=|×|\^|÷|\bformula\b", s))
        return (not maths, c["match"] >= 0.35, -len(re.findall(r"\d", s)))
    cl = sorted(cl, key=rank)[:cap]
    cl = sorted(cl, key=lambda c: c["n"])
    for i, c in enumerate(cl, 1):
        c["n"] = i
    C.save_json(rd / "verify_claims.json", [{k: v for k, v in c.items() if k != "fact"} for c in cl])
    if not cl:
        return 0
    b = (C.load_json(rd / "fact_sheet.json") or {}).get("brief") or {}
    W = [f"# Fact-check sheet: {rd.name}", "",
         f"{len(cl)} lines from draft.md where a mistake would matter (maths, money, rates, health, legal, safety). "
         f"Page: {b.get('page_type')} for {b.get('client')}, query \"{b.get('target_query')}\", market {b.get('locale')}.",
         "Most lines are expected to be right. Give each one a verdict in verify.md as plugins/fact_check/SKILL.md "
         "says; change the draft only for a line that is wrong.", ""]
    if by_data:
        W[4:4] = [f"{len(by_data)} more line(s) state only figures in {b.get('client')}'s own rates data and are not "
                  "listed. A `rates:` fact below is that data: it is correct, so a figure that differs from it is the error.",
                  ""]
    for c in cl:
        W.append(f"## C{c['n']} [{c['section'][:60]}]")
        W.append(f"\"{c['sentence']}\"")
        f = c["fact"]
        if f and c["match"] >= 0.15:
            own = f.get("basis") == "site_rates"
            W.append(f"- closest fact `{f['id']}`{' (the site' + chr(39) + 's own rates data)' if own else ''}: "
                     f"\"{str(f.get('value', ''))[:900 if own else 400]}\""
                     + (f" [applies to: {f['scope']}]" if own and f.get("scope") else "")
                     + (f" — {f['source_url']}" if f.get("source_url") else ""))
        else:
            W.append("- no fact is close: check it by reasoning (maths, definitions) or one source lookup")
        W.append("")
    (rd / "verify_sheet.md").write_text("\n".join(W), encoding="utf-8")
    return len(cl)


def _claims(rd: Path, source: str = "final.md") -> list[dict]:
    md = (rd / source).read_text(encoding="utf-8")
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    syn = (sheet.get("brief") or {}).get("synonyms") or {}
    facts = [f for f in sheet.get("facts", []) if f.get("status") in SUPPORT]
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
    b = (C.load_json(rd / "fact_sheet.json") or {}).get("brief") or {}
    W += [f"Page context: {b.get('page_type')} for {b.get('client')}; query: {b.get('target_query')}.",
          "Preserve the page's purpose while fixing facts. Do not add official-site CTAs to replace a scoped client "
          "offer. Keep necessary official actions, material limitations and disclosures accurate.", ""]
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
    # an all-OK verify.md is a complete answer: a page with nothing wrong is the expected outcome, never a failure
    return probs
