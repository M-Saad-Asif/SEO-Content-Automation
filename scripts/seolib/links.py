"""Internal-link candidates for a finished draft (the internal_links stage).

`build(rd)` ranks the client's own pages against the draft, section by section: for each page, its main term (the
head phrase of its title, else its address) is the suggested anchor, and the paragraph that talks most about that
term is where the link belongs. It writes `internal_links_plan.md` for the agent and `internal_links_plan.json` for
the `done` gate. Pages the draft must not link (itself, the page it replaces, redirects and dead pages, the home page,
which the site's header already links) are left out.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from . import common as C
from .lint import STOP, parse_md, strip_md
from .nlp import tokens


def _norm(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", (u or "").split("#")[0].split("?")[0].lower()).rstrip("/")


def _term(url: str, title: str) -> str:
    from .pagetype import keyword_from
    return keyword_from("", title or "", url) or " ".join(re.sub(r"[-_]+", " ", urlparse(url).path.strip("/").split("/")[-1]).split())


def build(rd: Path) -> list[dict]:
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    lm = C.load_json(rd / "link_map.json") or {}
    b = sheet.get("brief") or {}
    syn = b.get("synonyms") or {}
    md = (rd / "draft.md").read_text(encoding="utf-8")
    _, blocks = parse_md(md)

    def tk(s):
        return {w for w in tokens(s, syn) if w not in STOP and len(w) > 2 and not w.isdigit()}
    page = _norm(b.get("page_url", ""))
    rel = lm.get("client_related") or {}
    replaced = set() if b.get("task") == "rewrite" else {_norm(u) for u in rel.get("same_topic", [])}
    titles = {_norm(u): t for u, t in (lm.get("client_titles") or {}).items()}
    pool = list(dict.fromkeys(rel.get("commercial", []) + rel.get("guides", []) + rel.get("same_topic", [])
                              + [c["url"] for c in lm.get("children", [])] + lm.get("internal", [])))
    home = _norm(f"https://{(b.get('domain') or '').removeprefix('www.')}/")
    linked = {_norm(u) for u in re.findall(r"\]\((https?://[^)\s]+)\)", md)}
    sections, sec = [], "intro"
    for blk in blocks:
        if blk["type"] in ("h2", "h3"):
            sec = blk["text"]
        elif blk["type"] in ("p", "li"):
            sections.append((sec, blk.get("line"), blk["text"], tk(blk["text"])))
    page_tk = tk(" ".join(t for _, _, t, _ in sections))
    roles = {**{_norm(u): "service or commercial page" for u in rel.get("commercial", [])},
             **{_norm(u): "related guide" for u in rel.get("guides", [])},
             **{_norm(u): "the client's other page on this topic" for u in rel.get("same_topic", [])}}
    def seq(s):  # content words in order, for phrase matching
        return [w for w in tokens(s, syn) if w not in STOP and len(w) > 2 and not w.isdigit()]

    def pairs(ws):
        return {(a, b_) for a, b_ in zip(ws, ws[1:])}
    sec_pairs = [pairs(seq(t)) for _, _, t, _ in sections]
    out, seen_n = [], set()
    for u in pool:
        n = _norm(u)
        if not n or n in seen_n or n in (page, home) or n in replaced or n.endswith(
                ("/about-us", "/contact", "/contact-us", "/privacy-policy", "/terms", "/cookie-policy", "/sitemap", "/team")):
            continue
        seen_n.add(n)
        term = _term(u, titles.get(n, ""))
        tw = seq(term)
        tp = pairs(tw)
        if len(tw) < 2 or not tp:
            continue  # a one-word page name ("team", "bridging") is too vague to place by relevance
        # the paragraph must talk about the target's subject as a phrase: its word pairs, in order
        best_i = max(range(len(sections)), key=lambda i: len(tp & sec_pairs[i]), default=None)
        if best_i is None or not (tp & sec_pairs[best_i]):
            continue
        best = sections[best_i]
        score = round(len(tp & sec_pairs[best_i]) / len(tp), 2)
        if score < 0.5:
            continue
        out.append({"url": u, "term": term, "title": titles.get(n, ""), "role": roles.get(n, "site page"),
                    "section": best[0], "line": best[1], "excerpt": best[2][:220], "score": score,
                    "already_linked": n in linked})
    out.sort(key=lambda r: (-r["score"], r["role"] == "site page", len(r["term"])))
    by_term, uniq = set(), []
    for r in out:  # one anchor, one page: the best-placed page for each term
        if r["term"] not in by_term:
            by_term.add(r["term"])
            uniq.append(r)
    out = uniq[:15]
    # anchors waiting: questions the plan sends to another page that the client hasn't written yet
    qmap = C.load_json(rd / "research" / "query_map.json") or {}
    waiting = [r["query"] for r in qmap.get("queries", []) if r.get("decision") == "separate_page"][:8]
    C.save_json(rd / "internal_links_plan.json", {"candidates": out, "waiting": waiting})
    W = [f"# Internal-link candidates: {b.get('target_query', '')}", "",
         "Ranked by how much each client page's main term is what a paragraph of this draft is about. Follow "
         "plugins/internal_links/SKILL.md: link only where the sentence is about the target, with the target's main term "
         "as the anchor, a few strong links rather than many.", "",
         "| # | Target | Its main term (anchor) | Role | Best place (section, line) | Fit |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(out, 1):
        W.append(f"| {i} | {r['url']} | {r['term']} | {r['role']}{' (already linked)' if r['already_linked'] else ''} | "
                 f"{r['section'][:50]}, line {r['line']} | {r['score']:.0%} |")
    W += ["", "## Where each would go", ""]
    for i, r in enumerate(out, 1):
        W.append(f"{i}. **{r['term']}** → {r['url']}  \n   \"{r['excerpt']}\"")
    W += ["", "## Anchors waiting (pages the client could write; no link yet)", ""]
    W += [f"- {q}" for q in waiting] or ["- none"]
    (rd / "internal_links_plan.md").write_text("\n".join(W) + "\n", encoding="utf-8")
    return out


def check(rd: Path, text: str) -> list[str]:
    """The `done internal_links` gate: the log has its sections, and every link it says it added is in the draft."""
    probs = []
    heads = [h.lower() for h in re.findall(r"^#{1,4}\s+(.+)$", text, re.M)]
    for need in ("links added", "not linked"):
        if not any(need in h for h in heads):
            probs.append(f"missing section \"{need}\" (see plugins/internal_links/SKILL.md)")
    sec = re.search(r"^#{1,4}[^\n]*links added[^\n]*$(.*?)(?=^#{1,4}\s|\Z)", text, re.M | re.I | re.S)
    draft = {_norm(u) for u in re.findall(r"\]\((https?://[^)\s]+)\)", (rd / "draft.md").read_text(encoding="utf-8"))}
    for u in re.findall(r"https?://[^\s)|>]+", sec.group(1) if sec else ""):
        if _norm(u.rstrip(".,;")) not in draft:
            probs.append(f"{u} is listed as added but is not linked in draft.md")
    return probs
