"""`seo.py eval <run>`: measurable signals for the rubric in docs/EVAL_RUBRIC.md.

Humanization signals are compared with the human-written pages that already
rank for the same query (competitor_scrape), so targets are calibrated to the
niche, not invented. Writes eval.json and an eval.md scoring sheet whose
judgement rows the reviewer fills with quoted evidence.
"""
from __future__ import annotations

import re
import statistics as st
from collections import Counter
from pathlib import Path

from . import common as C
from .lint import Linter, human_paras, human_rhythm, lint_text, load_research, parse_md, rhythm_target, short_target, sentences, words

HEDGES = r"\b(may|might|could|typically|generally|usually|often|possibly|perhaps|likely|tend to|in some cases)\b"
META = r"\b(this (guide|article|page|post|section)|in this (guide|article|section)|below|above|read on|let's|we'll look|as mentioned)\b"
TRIPLET = r"\b[\w'-]+(?: [\w'-]+)?, [\w'-]+(?: [\w'-]+)?,? (?:and|or) [\w'-]+\b"


def _syllables(w: str) -> int:
    w = w.lower()
    v = re.findall(r"[aeiouy]+", w)
    n = len(v) - (1 if w.endswith("e") and len(v) > 1 else 0)
    return max(1, n)


def text_metrics(paras: list[str], nlp=None) -> dict:
    sents = [s for p in paras for s in sentences(p)]
    if len(sents) < 5:
        return {}
    lens = [len(words(s)) for s in sents]
    wc = sum(lens)
    first = Counter((re.findall(r"[A-Za-z']+", s) or [""])[0].lower() for s in sents)
    body = " ".join(paras)
    per_para = [len(sentences(p)) for p in paras if p.strip()]
    syl = sum(_syllables(w) for w in re.findall(r"[A-Za-z]+", body))
    flesch = 206.835 - 1.015 * (wc / len(sents)) - 84.6 * (syl / max(1, wc))
    m = {
        "sentences": len(sents), "words": wc,
        "mean_len": round(st.mean(lens), 1), "sd_len": round(st.pstdev(lens), 1),
        "short_share": round(sum(1 for x in lens if x < 8) / len(lens), 2),
        "long_share": round(sum(1 for x in lens if x > 25) / len(lens), 2),
        "top_opener": first.most_common(1)[0][0], "top_opener_share": round(first.most_common(1)[0][1] / len(sents), 2),
        "para_sd": round(st.pstdev(per_para), 2) if len(per_para) > 1 else 0,
        "colons_per100": round(100 * body.count(":") / max(1, wc), 2),
        "dashes_per100": round(100 * (body.count("—") + body.count(" – ")) / max(1, wc), 2),
        "hedges_per100": round(100 * len(re.findall(HEDGES, body, re.I)) / max(1, wc), 2),
        "meta_hits": list(Linter.META_RE.finditer(body)),  # the same detector lint uses, so the two never disagree
        "triplets": len(re.findall(TRIPLET, body)),
        "you_share": round(sum(1 for s in sents if re.search(r"\byou(r)?\b", s, re.I)) / len(sents), 2),
        "flesch": round(flesch, 1),
    }
    if nlp is not None:
        docs = list(nlp.pipe(sents[:400]))
        m["passive_share"] = round(sum(1 for d in docs if any(t.dep_ in ("auxpass", "nsubjpass") for t in d)) / len(docs), 2)
    m["meta_hits"] = len(m["meta_hits"])
    return m


def evaluate(rd: Path) -> dict:
    md_path = rd / "final.md" if (rd / "final.md").exists() else rd / "draft.md"
    md = md_path.read_text(encoding="utf-8")
    sheet = C.load_json(rd / "fact_sheet.json")
    lm = C.load_json(rd / "link_map.json", {})
    research = load_research(rd)
    meta, blocks = parse_md(md)
    paras = [b["text"] for b in blocks if b["type"] == "p"]
    try:
        from .nlp import import_spacy
        nlp = import_spacy().load("en_core_web_sm", disable=["ner"])
    except Exception:
        nlp = None
    ours = text_metrics(paras, nlp)
    comp = []
    for p in (research.get("competitor_scrape") or {}).get("pages", []):
        cp = human_paras(p)
        m = text_metrics(cp)
        if m:
            comp.append(m)

    def med(k):
        vals = [c[k] for c in comp if isinstance(c.get(k), (int, float))]
        return round(st.median(vals), 2) if vals else None
    base = {k: med(k) for k in ("mean_len", "sd_len", "short_share", "top_opener_share", "colons_per100",
                                 "hedges_per100", "flesch", "you_share")}
    q = (sheet["brief"].get("target_query") or "").lower()
    norm = lambda x: re.sub(r"[-‐–]", " ", x.lower())  # "carry-on" and "carry on" are the same search
    qcount = norm(md).count(norm(q)) if q else 0
    lint = lint_text(md, sheet, lm, research)
    flags = []
    base["sd_len"] = human_rhythm(research) or base.get("sd_len")
    if ours.get("sd_len", 0) < rhythm_target(research):
        flags.append(f"rhythm too even: SD {ours['sd_len']} vs human top pages {base['sd_len']} "
                     f"(target {rhythm_target(research)}, −3)")
    if ours.get("short_share", 0) > short_target(research):
        flags.append(f"clipped copy: {ours['short_share']:.0%} of sentences under 8 words vs human {base.get('short_share')} "
                     f"(cap {short_target(research):.0%}, −2)")
    if ours.get("top_opener_share", 0) >= 0.25:
        flags.append(f"opener monotony: \"{ours['top_opener']}\" starts {ours['top_opener_share']:.0%} of sentences (−2)")
    if ours.get("meta_hits", 0) > 1:
        flags.append(f"meta-commentary x{ours['meta_hits']} (−1 each after the first)")
    if ours.get("colons_per100", 0) + ours.get("dashes_per100", 0) > 1.5:
        flags.append(f"colon/dash habit: {ours['colons_per100'] + ours['dashes_per100']:.2f} per 100 words (−1)")
    if ours.get("hedges_per100", 0) > 2.5:
        flags.append(f"over-hedging: {ours['hedges_per100']} per 100 words (−1)")
    if ours.get("words") and qcount / ours["words"] * 100 > 0.8:
        flags.append(f"exact query used {qcount} times in {ours['words']} words: check for stuffing (−2 if forced)")
    if ours.get("triplets", 0) > max(2, ours.get("words", 0) / 300):
        flags.append(f"{ours['triplets']} A, B and C lists: check for rule-of-three padding (−1 each if not real)")
    res = {"file": md_path.name, "ours": ours, "human_baseline": base, "competitors_measured": len(comp),
           "exact_query_uses": qcount, "lint": lint["summary"], "humanization_flags": flags,
           "title_len": len(meta.get("title", "")), "meta_len": len(meta.get("meta_description", ""))}
    C.save_json(rd / "eval.json", res)
    _sheet(rd, res)
    return res


def _sheet(rd: Path, r: dict) -> None:
    o, b = r["ours"], r["human_baseline"]
    rows = [("mean sentence length", "mean_len"), ("sentence length SD (burstiness)", "sd_len"),
            ("share of sentences under 8 words", "short_share"), ("top opener share", "top_opener_share"),
            ("colons per 100 words", "colons_per100"), ("hedges per 100 words", "hedges_per100"),
            ("Flesch reading ease", "flesch"), ("share of sentences with you/your", "you_share")]
    L = [f"# Evaluation: {rd.name}", "", f"Rubric: docs/EVAL_RUBRIC.md. File: {r['file']}. Lint: {r['lint']['block']} block, "
         f"{r['lint']['warn']} warn. Page length {r['lint'].get('words')} words (the brief's word range counts this); "
         f"the signals below measure the {r['ours'].get('words')} words in paragraphs. Title {r['title_len']} chars, "
         f"meta {r['meta_len']} chars.", "",
         f"## Measured humanization signals (human baseline = median of {r['competitors_measured']} top-ranking pages)", "",
         "| Signal | This article | Human top pages |", "|---|---:|---:|"]
    L += [f"| {lab} | {o.get(k)} | {b.get(k)} |" for lab, k in rows]
    L += [f"| meta-commentary phrases | {o.get('meta_hits')} | – |", f"| A, B and C lists | {o.get('triplets')} | – |",
          f"| passive-voice sentences | {o.get('passive_share')} | – |", f"| exact target-query uses | {r['exact_query_uses']} | – |",
          "", "Automatic flags: " + ("; ".join(r["humanization_flags"]) or "none"), "",
          "## Scores (reviewer fills; every deduction quotes the line)", "",
          "| # | Criterion | Max | Score | Evidence for deductions |", "|---|---|---:|---:|---|"]
    for i, (name, mx) in enumerate([("Intent and SERP fit", 10), ("Coverage and responsiveness", 15),
                                     ("Accuracy and sourcing", 15), ("Information gain", 10), ("Humanization", 20),
                                     ("Language quality", 10), ("Structure and on-page SEO", 10),
                                     ("Brand and conversion", 5), ("Trust and E-E-A-T signals", 5)], 1):
        L.append(f"| {i} | {name} | {mx} |  |  |")
    L += ["", "**Total:** /100"]
    out = rd / "eval.md"
    text = "\n".join(L) + "\n"
    if out.exists() and "**Total:** /100" not in out.read_text(encoding="utf-8"):
        # a filled-in review keeps its scores; only the measured part above them is refreshed
        old = out.read_text(encoding="utf-8")
        head = text.split("## Scores", 1)[0]
        text = head + "## Scores" + old.split("## Scores", 1)[1] if "## Scores" in old else old
    out.write_text(text, encoding="utf-8")
