"""Information gain: what the page will say that page one doesn't.

Page one already gives the page its facts, statistics and questions (serp_facts, PAA, related searches). That makes
the page complete, not new. Google's information-gain patent (US 12,013,887) scores a document by what it adds beyond
the results a reader has already seen, and Google's helpful-content questions ask for "original information,
reporting, research, or analysis" and insight "beyond the obvious". So, while the research scripts run, researcher
agents use the coding tool's own web search (no Serper credit) to collect what page one lacks: people's first-hand
experiences and opinions from forums and Q&A sites, data from studies, tests, official statistics and manufacturers'
sheets, recent changes, common mistakes and real costs. Each item comes with the source's exact words.

This module then, by script:
- reads the researchers' files (gain_A.yaml, gain_B.yaml) and keeps well-formed items;
- checks each quote against the page it cites (a direct fetch, Spider for pages that block scripts): a quote found
  there makes the item a verified fact; an experience or opinion whose page can't be read stays usable as an
  attributed experience (status captured), and a figure that can't be checked is dropped;
- drops items page one already says (the page-one sentences are compared word by word), the client's own pages and
  page-one competitors (never a competitor's link);
- registers what's left as `gain:N` facts, which the plan places under their headings and the check counts.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import common as C

KINDS = ("experience", "opinion", "data", "change", "mistake", "cost")
STOP = set("a an the and or but of to in on at by for with from into is are was were be been it its this that these "
           "those you your we our they their i my me he she his her can could will would should may might must do does "
           "did have has had not no so if as than then there here which who what when where why how very just also more "
           "most some any all".split())


def files(rd: Path) -> list[Path]:
    return sorted(p for p in Path(rd).glob("gain_*.*") if p.suffix in (".yaml", ".yml", ".md", ".txt"))


def task_lines(brief: dict, R: str) -> list[str]:
    """The researchers' task: two at the same time, each with its own brief and file."""
    q, loc = brief.get("target_query"), brief.get("locale") or "en-GB"
    client, ptype = brief.get("client"), brief.get("page_type") or "guide"
    common = [
        f"Topic: \"{q}\" for {client} ({brief.get('domain')}), a {ptype} page, market {loc}.",
        "Use your own web search and page reading (the tool's built-in search; never Serper, never a login, never "
        "Reddit, never a page that blocks you). At most 4 searches and 6 page reads; stop after about 2 minutes.",
        "Look past the first page of results for the exact query: page one is already covered.",
        "Keep 4-8 items. Each item is something a reader can't get from the top 10 results.",
        f"Write {R}/gain_X.yaml (X = your letter) with one write, in exactly this form (YAML list, nothing else):",
        "- kind: experience | opinion | data | change | mistake | cost",
        "  point: one sentence in your own words (figures exactly as the source gives them, with their condition)",
        "  quote: the source's exact words that carry the point, 8-40 words, copied character for character",
        "  source: the page's full URL",
        "  who: who says it, as a reader would see it (\"a member of the DIYnot forum\", \"Which? (2025 test)\"); "
        "never a username",
        "  date: the year or date the page shows (blank if none)",
        "Never invent, merge or round a quote; skip anything you could not read yourself. Skip the client's own site, "
        "shops selling the same thing, and anything an official body contradicts.",
    ]
    return [
        f"Run folder: {R}",
        "The research scripts are running in the background (about a minute). Meanwhile, find what page one doesn't "
        "have (information gain). Start 2 `seo-gain-researcher` sub-agents in ONE turn, A and B, each given the "
        "common instructions plus its own focus (Claude Code: the Agent tool with subagent_type `seo-gain-researcher`, "
        "both in one message; Codex: spawn two `seo_gain_researcher` agents and wait for both; Cursor, Antigravity, "
        "Gemini CLI, Copilot: the `seo-gain-researcher` subagent, twice, at the same time; a tool without sub-agents: "
        "do A yourself, then B; without web search, skip this task).",
        "",
        "A (people): first-hand experiences and opinions from forums, Q&A sites, community and specialist sites "
        "(Quora, trade and hobby forums, Mumsnet, public Facebook groups, review sites, YouTube comments): what people "
        "found when they did it, what went wrong, what they'd do differently, which option they prefer and why.",
        "B (evidence): data and changes beyond page one: studies, independent tests, official statistics, "
        "manufacturers' data sheets, rule or price changes from the last 12 months, common mistakes and their cost.",
        "",
        "Common instructions:",
        *[f"- {x}" if not x.startswith(("- ", "  ")) else f"  {x}" for x in common],
    ]


def parse(text: str) -> list[dict]:
    import yaml
    text = re.sub(r"^```\w*\s*$", "", text, flags=re.M)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        data = None
    if isinstance(data, dict):
        data = data.get("items") or next((v for v in data.values() if isinstance(v, list)), [])
    out = []
    for it in data if isinstance(data, list) else []:
        if not isinstance(it, dict):
            continue
        item = {k: " ".join(str(it.get(k) or "").split()) for k in ("kind", "point", "quote", "source", "who", "date")}
        item["kind"] = item["kind"].lower().split()[0] if item["kind"] else "data"
        if item["kind"] not in KINDS:
            item["kind"] = "data"
        if not re.match(r"https?://[^\s/]+\.[^\s]+", item["source"]) or len(item["point"].split()) < 5 \
                or len(item["quote"].split()) < 5:
            continue
        out.append(item)
    return out


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[–—-]", "-", s)
    return " ".join(re.sub(r"[^\w%£$€'.-]+", " ", s).split())


def _content(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9£$€%]{3,}", _norm(s)) if w not in STOP}


def quote_on_page(quote: str, page: str) -> bool:
    """The quote, or nearly all of its 6-word runs, is on the page (layout and punctuation differ between readers)."""
    q, p = _norm(quote), _norm(page)
    if not q or not p:
        return False
    if q in p:
        return True
    ws = q.split()
    grams = [" ".join(ws[i:i + 6]) for i in range(max(1, len(ws) - 5))]
    return sum(g in p for g in grams) / len(grams) >= 0.8


def _read_pages(urls: list[str]) -> dict[str, str]:
    """Page text: a direct fetch first, Spider for the pages that block scripts or need JavaScript."""
    if not urls:
        return {}
    res = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in urls], timeout=8.0, attempts=1))
    text = {u: (r.get("text") or "") for u, r in res.items() if r.get("state") == "ok"}
    rest = [u for u in urls if len(text.get(u, "")) < 300]
    if rest:
        try:
            from . import spider
            for u, r in (spider.scrape_many(rest, concurrency=5, timeout_s=15, attempts=1) or {}).items():
                t = r.get("text") or r.get("markdown") or "\n".join(" ".join(b) if isinstance(b, list) else str(b)
                                                                    for b in r.get("blocks") or [])
                if len(t) > len(text.get(u, "")):
                    text[u] = t
        except Exception:
            pass
    return text


def verify(rd: Path) -> dict:
    """Read the researchers' files and check every quote against its page. Saved to research/gain.json. Runs while
    the research scripts may still be running (it touches nothing they write)."""
    rd = Path(rd)
    items, bad = [], 0
    for f in files(rd):
        got = parse(f.read_text(encoding="utf-8", errors="replace"))
        bad += 0 if got else 1
        for it in got:
            it["file"] = f.name
            items.append(it)
    seen, uniq = set(), []
    for it in items:
        key = (_norm(it["quote"])[:80], it["source"].rstrip("/"))
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    pages = _read_pages(list(dict.fromkeys(it["source"] for it in uniq)))
    for it in uniq:
        page = pages.get(it["source"], "")
        it["read"] = len(page) >= 300
        it["quote_found"] = quote_on_page(it["quote"], page) if it["read"] else False
    out = {"items": uniq, "files": [p.name for p in files(rd)], "unreadable_files": bad}
    (rd / "research").mkdir(exist_ok=True)
    C.save_json(rd / "research" / "gain.json", out)
    return out


def register(rd: Path) -> list[dict]:
    """After the research scripts: drop what page one already says, the client's own pages and competitors; register
    the rest as gain:N facts in fact_sheet.json. Returns the registered facts."""
    rd = Path(rd)
    g = C.load_json(rd / "research" / "gain.json") or {}
    if not g.get("items"):
        return []
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    b = sheet.get("brief") or {}
    client_host = re.sub(r"^www\.", "", (b.get("domain") or "").lower()).split("/")[0]
    serp = C.load_json(rd / "research" / "serp_intel.json") or {}
    rivals = {re.sub(r"^www\.", "", o.get("domain", "")) for o in serp.get("organic", [])
              if o.get("kind") in ("ecommerce", "business_site")}
    comp = C.load_json(rd / "research" / "competitor_scrape.json") or {}
    page_one = []
    for p in comp.get("pages", []) if isinstance(comp.get("pages"), list) else []:
        for blk in p.get("blocks", []) or []:
            txt = blk.get("text") if isinstance(blk, dict) else blk[-1] if isinstance(blk, (list, tuple)) and blk else str(blk)
            for s in re.split(r"(?<=[.!?])\s+", txt or ""):
                cs = _content(s)
                if len(cs) >= 4:
                    page_one.append(cs)

    def on_page_one(it) -> bool:
        cs = _content(it["point"]) | _content(it["quote"])
        nums = set(re.findall(r"\d+(?:\.\d+)?", it["quote"]))
        for ps in page_one:
            if len(cs & ps) / max(1, min(len(cs), len(ps))) >= 0.6 and (not nums or nums & ps):
                return True
        return False

    facts, decisions = [], []
    for it in g["items"]:
        host = re.sub(r"^www\.", "", it["source"].split("/")[2].lower())
        if client_host and (host == client_host or host.endswith("." + client_host)):
            continue
        if host in rivals:
            decisions.append(f"Gain item from {host} skipped: a page-one competitor (never linked).")
            continue
        if on_page_one(it):
            continue
        if it.get("quote_found"):
            status = "verified"
        elif it["kind"] in ("experience", "opinion") and not re.search(r"\d", it["quote"]):
            status = "captured"  # read by the researcher, not by the script; usable only as an attributed experience
        else:
            decisions.append(f"Gain item \"{it['point'][:80]}\" dropped: its quote could not be checked on {host}.")
            continue
        date = str(it.get("date") or "")
        facts.append({"id": f"gain:{len(facts) + 1}", "claim": f"{it['who'] or host}" + (f" ({date})" if date else "")
                      + f": {it['point']}", "value": it["quote"], "point": it["point"], "who": it["who"] or host,
                      "kind": it["kind"], "date": date,
                      "condition": (f"published {date}" if date else ""),  # the page's date is a citable figure too
                      "status": status, "basis": f"gain_{it['kind']}",
                      "verified": status == "verified", "source_url": it["source"], "retrieved_at": C.now_iso()})
    with C.file_lock(rd / "fact_sheet.json"):
        sh = C.load_json(rd / "fact_sheet.json") or {}
        sh["facts"] = [f for f in sh.get("facts", []) if not str(f.get("id", "")).startswith("gain:")] + facts
        sh["decisions"] = list(dict.fromkeys((sh.get("decisions") or []) + decisions +
                                             [f"Information gain: {len(facts)} item(s) beyond page one from the "
                                              f"researchers ({sum(f['status'] == 'verified' for f in facts)} quote-checked)."]))
        C.save_json(rd / "fact_sheet.json", sh)
    return facts
