"""Step 6: validate. Re-lint, check every link's live status, write final.md
(only on pass) and report.md."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import common as C
from .lint import lint_text, print_findings, sentences, parse_md, load_research
from .timing import mark, table

USABLE = {"verified", "captured", "operator"}


def _same_page(a: str, b: str) -> bool:
    """example.com/page and https://www.example.com/page/ are one page; anything else is a real redirect."""
    from urllib.parse import urljoin, urlparse
    b = urljoin(a, b)
    norm = lambda u: (urlparse(u).netloc.lower().removeprefix("www.") + urlparse(u).path.rstrip("/").lower(),
                      urlparse(u).query)
    return bool(b) and norm(a) == norm(b)


def resolve_run(arg: str) -> Path:
    p = Path(arg)
    for cand in (p, C.ROOT / p, C.RUNS / p):
        if cand.is_dir() and (cand / "fact_sheet.json").exists():
            return cand.resolve()
    if p.suffix in (".yaml", ".yml"):
        from .prep import load_brief, latest_run
        return latest_run(load_brief(arg))
    raise SystemExit(f"Not a run directory (no fact_sheet.json): {arg}")


def link_status(md: str, sheet: dict, lm: dict, refresh: bool = False) -> list[dict]:
    urls = sorted({u.split("#")[0] for u in re.findall(r"\]\((https?://[^)\s]+)\)", md)})
    if not urls:
        return []
    res = C.run_async(C.fetch_many([{"url": u, "kind": "status", "parse": "status"} for u in urls], refresh))
    # A URL that refuses scripts still counts as live when an agent captured it,
    # or when a verified official page links to that exact URL.
    captured = {o["url"].rstrip("/") for o in lm.get("official", []) if o.get("captured")}
    client_listed = {u.rstrip("/") for u in lm.get("internal", [])} | \
        {u.rstrip("/") for v in (lm.get("client_related") or {}).values() for u in v} | \
        {p["url"].rstrip("/") for p in lm.get("products", [])}
    cited_by = {}
    for o in lm.get("official", []):
        if o.get("state") != "ok":
            continue
        c = C.cache_get(f"html|{o['url']}", "official") or {}
        hay = c.get("text", "") + " " + " ".join(h for h, _ in c.get("links", []))
        for u in urls:
            if u.rstrip("/").lower() in hay.lower():
                cited_by.setdefault(u, o["url"])
    out = []
    for u in urls:
        r = res.get(u) or {}
        st = r.get("status")
        if st == 200:
            verdict, sev = "ok", None
        elif st in (301, 302, 303, 307, 308) and _same_page(u, r.get("location") or ""):
            verdict, sev = f"cosmetic redirect to {r.get('location')} (slash, www or https only)", None
        elif st in (301, 302, 303, 307, 308):
            verdict, sev = f"redirects to {r.get('location')}", "block"
        elif st == 429 and u.rstrip("/") in client_listed:
            verdict, sev = "client site rate-limited the check (429); the page is in the client's sitemap", "warn"
        elif r.get("state") == "blocked" or st in (0, None, 403, 429):
            if u in cited_by:
                verdict, sev = f"blocks scripts ({st}); linked by verified official page {cited_by[u]}", None
            elif u.rstrip("/") in captured:
                verdict, sev = f"blocks scripts ({st}); page read and captured by the agent", None
            else:
                verdict, sev = f"blocked or unreachable ({st}); not confirmed", "block"
        elif st == 404 and (u.rstrip("/") in captured or C.captured_text(u)):
            verdict, sev = "scripts get 404; a saved capture of the live page exists (accepted, not re-checked)", "warn"
        else:
            verdict, sev = f"HTTP {st}", "block"
        out.append({"url": u, "status": st, "verdict": verdict, "severity": sev})
    return out


def facts_used(md: str, sheet: dict) -> list[dict]:
    """Facts the copy rests on: quoted verbatim, or paraphrased (its numbers present and most of its words in one
    sentence of the page)."""
    import re
    from .lint import STOP, sentences
    from .nlp import tokens
    body = C.norm_for_match(md)
    syn = (sheet.get("brief") or {}).get("synonyms") or {}
    sents = [(set(re.findall(r"\d+(?:\.\d+)?", s)), {w for w in tokens(s, syn) if w not in STOP and len(w) > 2})
             for s in sentences(re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md))]
    used = []
    for f in sheet.get("facts", []):
        if f.get("status") not in ("verified", "captured", "operator"):
            continue
        v = str(f.get("value", ""))
        fn = set(re.findall(r"\d+(?:\.\d+)?", v))
        ft = {w for w in tokens(v, syn) if w not in STOP and len(w) > 2}
        verbatim = len(v) >= 3 and C.norm_for_match(v) in body
        para = ft and any(fn <= sn and len(ft & st) >= max(2, 0.4 * len(ft)) for sn, st in sents)
        if verbatim or para:
            used.append({"id": f["id"], "value": v, "status": f["status"], "source": f.get("source_url"),
                         "how": "quoted" if verbatim else "paraphrased"})
    return used


def validate(run_arg: str, refresh_links: bool = False) -> bool:
    rd = resolve_run(run_arg)
    mark(rd, "validate", "start")
    sheet = C.load_json(rd / "fact_sheet.json")
    lm = C.load_json(rd / "link_map.json", {})
    draft = rd / "draft.md"
    if not draft.exists():
        raise SystemExit(f"{draft} not found")
    md = draft.read_text(encoding="utf-8")
    res = lint_text(md, sheet, lm, load_research(rd))
    links = link_status(md, sheet, lm, refresh_links)
    for l in links:
        if l["severity"]:
            res["findings"].append({"id": f"K{len(res['findings']) + 1:03d}", "rule": "U07-link-status", "severity": l["severity"],
                                    "line": None, "section": None, "text": l["url"], "reason": l["verdict"], "fix": "use a URL that returns 200"})
    blocks = [f for f in res["findings"] if f["severity"] == "block"]
    res["summary"]["block"] = len(blocks)
    res["summary"]["warn"] = sum(1 for f in res["findings"] if f["severity"] == "warn")
    res["links"] = links
    C.save_json(rd / "lint.json", res)
    ok = not blocks
    final = rd / "final.md"
    if ok:
        shutil.copyfile(draft, final)
    elif final.exists():
        final.unlink()
    mark(rd, "validate", "end")
    write_report(rd, sheet, res, ok)
    print_findings({"summary": res["summary"], "findings": [f for f in res["findings"] if f["severity"] == "block"]})
    ok_n = sum(1 for l in links if l["severity"] is None)
    warn_n = sum(1 for l in links if l["severity"] == "warn")
    print(f"links: {ok_n}/{len(links)} fine (200 or a slash/www/https-only redirect)"
          + (f", {warn_n} unconfirmed but accepted" if warn_n else ""))
    t = C.load_json(rd / "timing.json", {}).get("summary", {})
    last = C.load_json(rd / "timing.json", {}).get("events", [])
    vs = [e["t"] for e in last if e.get("step") == "validate"][-2:]
    this = f"{vs[1] - vs[0]:.1f}s" if len(vs) == 2 else "?"
    run_min = (t.get("total") or 0) / 60
    print(f"VALIDATE {'PASS' if ok else 'FAIL'}  this check {this}, run so far {run_min:.0f} min  report: {(rd / 'report.md').as_posix()}"
          + (f"  final: {(rd / 'final.md').as_posix()}" if ok else ""))
    return ok


SOURCE_NAMES = {"paa": "People Also Ask", "paa_expanded": "People Also Ask (follow-up search)", "paa_dfs": "People Also Ask",
                "paa_autocomplete": "question search", "related": "related search", "related_expanded": "related search",
                "autocomplete": "autocomplete", "top_page_headings": "competitors' question", "gsc": "Search Console",
                "keyword": "keyword research"}


def questions_answered(rd: Path, md: str, sheet: dict) -> list[str]:
    """Every searcher question the plan said this page answers, and where it does: the heading that answers it, or the
    sentence, or "not answered". The operator can see at a glance that PAA, related and competitor questions are on
    the page."""
    import re
    from .lint import parse_md, sentences, STOP
    from .nlp import tokens
    qmap = C.load_json(rd / "research" / "query_map.json") or {}
    plan = [r for r in qmap.get("queries", []) if r.get("decision") in ("h2", "cover_in_section")]
    if not plan:
        return []
    syn = (sheet.get("brief") or {}).get("synonyms") or {}

    def tk(s):
        return {w for w in tokens(s, syn) if w not in STOP and len(w) > 2}
    _, blocks = parse_md(md)
    heads = [b["text"] for b in blocks if b["type"] in ("h2", "h3")]
    sents = [s for b in blocks if b["type"] in ("p", "li", "tr") for s in sentences(b["text"])]
    main = tk((sheet.get("brief") or {}).get("target_query", ""))
    skips = {s["question"].lower(): s.get("reason", "") for s in
             (C.load_json(rd / "research" / "outline.json") or {}).get("skips", [])}
    L = ["\n## Searcher questions and where the page answers them\n",
         "| Question | Source | Plan | Answered at |", "|---|---|---|---|"]
    n_ok = n_skip = 0
    for r in plan:
        q = r["query"]
        qt, own = tk(q), tk(" ".join(r.get("distinct_terms") or [])) or (tk(q) - main)
        key = own or qt  # the question's own words decide; the topic words are in every heading
        need = 1.0 if len(key) <= 2 else 0.67
        h = max(heads, key=lambda x: len(key & tk(x)), default="")
        where = ""
        if h and key and len(key & tk(h)) / len(key) >= (need if own else 0.6):
            where = f"heading \"{h}\""
        else:
            s = max(sents, key=lambda x: len(own & tk(x)), default="") if own else ""
            if s and own and len(own & tk(s)) / len(own) >= (1.0 if len(own) <= 2 else 0.67):
                where = f"\"{s[:110]}{'…' if len(s) > 110 else ''}\""
        skipped = not where and skips.get(q.lower())
        n_ok += bool(where)
        n_skip += bool(skipped)
        shown = where or (f"skipped: {skipped}" if skipped else "**not answered**")
        L.append(f"| {q} | {SOURCE_NAMES.get(r.get('source'), r.get('source'))} | "
                 f"{'own H2' if r['decision'] == 'h2' else 'inside a section'} | {shown} |")
    L.insert(1, f"{n_ok} of {len(plan)} answered, {n_skip} skipped with a reason (outline), "
                f"{len(plan) - n_ok - n_skip} not answered.\n")
    return L


def write_report(rd: Path, sheet: dict, res: dict, ok: bool | None = None) -> None:
    if ok is None:
        ok = (rd / "final.md").exists()
    timing = C.load_json(rd / "timing.json", {}).get("summary", {})
    md = (rd / "draft.md").read_text(encoding="utf-8") if (rd / "draft.md").exists() else ""
    s = res.get("summary", {})
    L = []
    L.append(f"# Run report: {sheet['brief']['client']} — {sheet['brief']['page_url']}\n")
    L.append(f"**Status: {'PASS' if ok else 'FAIL'}** · {s.get('block', 0)} blocking · {s.get('warn', 0)} warnings · {s.get('words', 0)} words · mode {(sheet.get('research') or {}).get('mode') or sheet['brief'].get('mode')}\n")
    L.append("## Timing\n")
    mode = (sheet.get("research") or {}).get("mode", "quick")
    L.append(table(timing, mode))
    if sheet.get("research"):
        r = sheet["research"]
        L.append("\nPlugins: " + ", ".join(f"{k} {v}s" for k, v in r.get("plugin_seconds", {}).items())
                 + f". Serper credits: {r.get('serper_credits', 0)}.")
    L.append("\n## Unresolved findings\n")
    unresolved = [f for f in res.get("findings", [])]
    if not unresolved:
        L.append("None.")
    for f in unresolved:
        L.append(f"- **{f['severity']}** `{f['rule']}` (line {f['line']}): {f['text'][:200]} — {f['reason']}")
    L.append("\n## Decisions the automation made\n")
    qs = sheet.get("decisions") or []
    L += [f"- {q}" for q in qs] or ["None."]
    L.append("\n## Links checked\n")
    links = res.get("links", [])
    if links:
        L.append("| URL | Status | Verdict |\n|---|---|---|")
        L += [f"| {l['url']} | {l['status']} | {l['verdict']} |" for l in links]
    else:
        L.append("No links.")
    L.append("\n## Facts used in the copy\n")
    used = facts_used(md, sheet)
    if used:
        L.append("| Fact | Value | Basis | Used | Source |\n|---|---|---|---|---|")
        L += [f"| {u['id']} | {u['value'][:60]} | {u['status']} | {u['how']} | {u['source'] or 'client brief'} |" for u in used]
    else:
        L.append("No fact matched the copy (numbers are still traced by lint rule N01).")
    L += questions_answered(rd, md, sheet)
    skips = (C.load_json(rd / "research" / "outline.json") or {}).get("skips") if (rd / "research").exists() else []
    if skips:
        L.append("\n## Questions deliberately left out or linked (outline decisions)\n")
        L += [f"- {s['question']} — {s['reason']}" for s in skips]
    gaps = sheet.get("gaps") or []
    if gaps:
        L.append("\n## Facts that could not be verified (written around)\n")
        L += [f"- {g['id']}: {g['reason']}" for g in gaps]
    (rd / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
