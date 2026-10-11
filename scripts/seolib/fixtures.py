"""`seo.py test`: regression fixtures in fixtures/<case>/.

For each case: prep the brief (cache is fine), lint every bad_v*.md and check
that each expected phrase present in it gets a BLOCK finding on its line, that
must_rules fire, that the vertical checks give the expected verdicts, that old
product handles redirect to products in the link map, and that good.md (a
passing output from a real run) has zero blocking findings.
"""
from __future__ import annotations

import io
import re
from contextlib import redirect_stdout
from pathlib import Path

from . import common as C
from .lint import lint_text
from .prep import load_brief, prep


def _lines_with(text: str, phrase: str) -> set[int]:
    return {i for i, ln in enumerate(text.splitlines(), 1) if phrase.lower() in ln.lower()}


def check_plugins() -> list[tuple[bool, str]]:
    """Every plugin has a manifest, a run.py or SKILL.md, and dependencies that exist."""
    from .harness import manifests
    ms = manifests()
    out = []
    for n, m in ms.items():
        has_impl = (m["_dir"] / "run.py").exists() if m.get("kind") == "script" else \
            (m["_dir"] / "SKILL.md").exists() if m.get("kind") == "agent" else bool(m.get("entry"))
        skill = m["_dir"] / "SKILL.md"
        has_skill = skill.exists() and skill.read_text(encoding="utf-8").startswith("---\nname: ") \
            and len(skill.read_text(encoding="utf-8").split()) >= 120
        missing = [d for d in m.get("needs", []) if d not in ms]
        ok = has_impl and has_skill and not missing
        out.append((ok, f"plugin {n} ({m.get('kind')}): " + ("ok" if ok else
                    f"implementation {has_impl}, full skill {has_skill}, missing needs {missing}")))
    bad = [str(p) for p in list((C.ROOT / "plugins").rglob("*.py")) + list((C.ROOT / "scripts").rglob("*.py"))
           if chr(8) in p.read_text(encoding="utf-8")]
    out.append((not bad, "no control characters in source" + (f": {bad}" if bad else "")))
    return out


def check_connectors() -> list[tuple[bool, str]]:
    """Run each connector plugin's analysis on synthetic raw data (the MCP route) in a
    throwaway run folder. Tests the parsing and rules without credentials or network."""
    import importlib.util
    import shutil
    import tempfile
    from .harness import Ctx, PLUGINS
    page = "https://example.com/visa-status-check"
    brief = {"client": "Example", "domain": "example.com", "page_url": page, "target_query": "visa status check",
             "locale": "en-GB", "task": "rewrite", "connectors": "auto", "_path": "synthetic"}
    tmp = Path(tempfile.mkdtemp(prefix="seo-conn-"))
    out = []
    try:
        ctx = Ctx(brief, tmp, "deep")
        raw = ctx.dir / "raw"
        raw.mkdir(parents=True)
        C.save_json(ctx.dir / "current_page.json", {"exists": True, "text": "Visa status check. UK visa application status by email."})
        C.save_json(raw / "gsc_insights.json", {"window": ["2026-01-01", "2026-03-31"], "page_rows": [
            {"query": "visa status check", "clicks": 40, "impressions": 2100, "ctr": 0.019, "position": 6.2},
            {"query": "ceac visa status check", "clicks": 12, "impressions": 300, "ctr": 0.04, "position": 4.8},
            {"query": "visa status check uae", "clicks": 5, "impressions": 90, "ctr": 0.055, "position": 9.1}],
            "site_rows": [{"query": "visa status check uae", "page": "https://example.com/visa-status-check/uae",
                           "clicks": 30, "impressions": 400, "position": 3.2}]})
        C.save_json(raw / "keyword_research.json", {"keywords": [
            {"keyword": "visa status check", "search_volume": 5400, "intent": "navigational"},
            {"keyword": "check visa status online", "search_volume": 1900, "intent": "informational"}],
            "paa": ["How do I check my visa status?"]})
        C.save_json(raw / "clarity_ux.json", {"metrics": [
            {"metricName": "ScrollDepth", "information": [{"URL": page + "/", "averageScrollDepth": "35.2"}]},
            {"metricName": "DeadClickCount", "information": [{"URL": "https://www.example.com/visa-status-check?x=1",
                                                               "sessionsCount": "40", "sessionsWithMetricPercentage": "8.5"}]}]})
        C.save_json(raw / "reddit_voice.json", {"threads": [{"url": "https://www.reddit.com/r/ukvisa/comments/x/",
            "subreddit": "ukvisa", "title": "Waiting for decision", "comments": [
                {"text": "I applied in March and waited six weeks before I got the decision email from UKVI.", "score": 12},
                {"text": "lol same", "score": 30}]}]})

        def run(name):
            spec = importlib.util.spec_from_file_location(f"t_{name}", PLUGINS / name / "run.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.run(ctx)
        g = run("gsc_insights")
        out.append((g.get("source") == "mcp" and any(r["query"] == "visa status check" for r in g.get("low_ctr", []))
                    and any("ceac" in r["missing_terms"] for r in g.get("gaps", []))
                    and "visa status check uae" in g.get("cannibalisation", {}),
                    "gsc_insights: weak-CTR, gap and cannibalisation detected from MCP rows"))
        k = run("keyword_research")
        out.append((k.get("main", {}).get("search_volume") == 5400 and k["keywords"][0]["keyword"] == "visa status check"
                    and k.get("paa"), "keyword_research: volumes, main keyword and PAA from MCP data"))
        c = run("clarity_ux")
        recs = " ".join(c.get("recommendations", []))
        out.append(("scroll depth" in recs.lower() and "aren't links" in recs.lower(),
                    "clarity_ux: URL variants matched; scroll-depth and dead-click fixes produced"))
        r = run("reddit_voice")
        ex = [e for i in r.get("items", []) for e in i["excerpts"]]
        out.append((len(ex) == 1 and "six weeks" in ex[0], "reddit_voice: first-hand comment kept, noise dropped"))
    except Exception as e:
        out.append((False, f"connector analysis raised {type(e).__name__}: {e}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def run_fixtures(name: str | None = None) -> bool:
    ok_all = True
    if not name:
        print("== plugins")
        for good, msg in check_plugins():
            print(("  PASS " if good else "  FAIL ") + msg)
            ok_all &= good
        print("== connectors (synthetic MCP data, offline)")
        for good, msg in check_connectors():
            good = bool(good)
            print(("  PASS " if good else "  FAIL ") + msg)
            ok_all &= good
    for exp_path in sorted((C.ROOT / "fixtures").glob("*/expect.yaml")):
        case = exp_path.parent
        if name and case.name != name:
            continue
        exp = C.load_yaml(exp_path)
        print(f"== {case.name}")
        with redirect_stdout(io.StringIO()):
            rd = prep(exp["brief"])
        sheet = C.load_json(rd / "fact_sheet.json")
        lm = C.load_json(rd / "link_map.json")
        results = []

        for bad in sorted(case.glob("bad_v*.md")):
            text = bad.read_text(encoding="utf-8")
            res = lint_text(text, sheet, lm)
            blocks = [f for f in res["findings"] if f["severity"] == "block"]
            blines = {f["line"] for f in blocks}
            for ph in exp.get("must_block_phrases", []):
                lines = _lines_with(text, ph)
                if not lines:
                    continue
                hit = bool(lines & blines) or any(ph.lower() in f["text"].lower() for f in blocks)
                results.append((hit, f"{bad.name}: blocks \"{ph}\""))
            rules = {f["rule"] for f in blocks}
            for r in exp.get("must_rules", []):
                results.append((r in rules, f"{bad.name}: rule {r} fires"))
            results.append((True, f"{bad.name}: {res['summary']['block']} block / {res['summary']['warn']} warn"))

        unread = {(p.get("display_name") or p.get("name") or "").lower() for p in sheet.get("products", [])
                  if p.get("page_status") in (None, 0, 429, 503)}
        skipped_fit = 0
        for e in exp.get("luggage_fit", []):
            rs = [r for r in sheet["checks"]["luggage_fit"]["results"]
                  if e["product"].lower() in r["product"].lower() and r["limit_id"] == e["limit"]]
            if not rs and any(e["product"].lower() in n for n in unread):
                skipped_fit += 1  # the shop refused the product page (rate limit): no measurements to check
                continue
            if rs and all(r["limit_status"] not in ("verified", "captured") for r in rs) and e["verdict"] != "dims_doubtful":
                ok_unknown = all(r["verdict"] == "unknown" for r in rs)
                results.append((ok_unknown, f"luggage_fit {e['product']} vs {e['limit']}: limit not verifiable from here, verdict withheld (unknown)"))
                continue
            good = bool(rs) and all(r["verdict"] == e["verdict"] for r in rs)
            if good and "zero_margin" in e:
                good = all(r["zero_margin"] == e["zero_margin"] for r in rs)
            results.append((good, f"luggage_fit {e['product']} vs {e['limit']} = {e['verdict']}"
                                  + (" (zero margin)" if e.get("zero_margin") else "")
                                  + ("" if good else f" [got {[r['verdict'] for r in rs]}]")))

        if skipped_fit:
            print(f"  SKIP {skipped_fit} luggage-fit checks: their product pages were rate-limited (429) on this fetch")

        if exp.get("redirecting_handles") or exp.get("dead_handles"):
            dom = sheet["brief"]["domain"]
            prods = {p["url"] for p in lm["products"]}
            urls = [f"https://{dom}/products/{h}" for h in exp.get("redirecting_handles", []) + exp.get("dead_handles", [])]
            st = C.run_async(C.fetch_many([{"url": u, "kind": "status", "parse": "status"} for u in urls]))
            throttled = [u for u in urls if (st.get(u) or {}).get("status") in (None, 0, 429, 503)]
            if throttled:  # the live site is rate-limiting us: not a pipeline result either way
                print(f"  SKIP {len(throttled)} live handle checks: {dom} is rate-limiting or unreachable right now")
            for h in exp.get("redirecting_handles", []):
                r = st.get(f"https://{dom}/products/{h}") or {}
                if f"https://{dom}/products/{h}" in throttled:
                    continue
                tgt = "https://" + dom + r.get("location", "") if r.get("location", "").startswith("/") else r.get("location", "")
                good = r.get("status") == 301 and tgt.rstrip("/") in prods
                results.append((good, f"old handle {h} -> {tgt or r.get('status')} (in link map)"))
            for h in exp.get("dead_handles", []):
                u = f"https://{dom}/products/{h}"
                if u in throttled:
                    continue
                results.append((u not in prods and (st.get(u) or {}).get("status") == 404, f"guessed handle {h} is 404 and not in link map"))

        for good_md in [case / "good.md"]:
            if good_md.exists():
                res = lint_text(good_md.read_text(encoding="utf-8"), sheet, lm)
                # a client claim the live site no longer shows is rightly refused: that is the site changing, not
                # the pipeline failing, so blocks on those lines are reported as a SKIP
                gone = [c["text"].lower()[:40] for c in sheet.get("client", {}).get("approved_claims", [])
                        if not c.get("seen_on_site", True)]
                blocks = [f for f in res["findings"] if f["severity"] == "block"]
                live = [f for f in blocks if not any(g and g in (f.get("text") or "").lower() for g in gone)]
                if len(live) < len(blocks):
                    print(f"  SKIP {len(blocks) - len(live)} good.md block(s): the client's site no longer shows "
                          f"the claim they use")
                results.append((not live, f"good.md: {len(live)} block / {res['summary']['warn']} warn"))

        for good, msg in results:
            print(("  PASS " if good else "  FAIL ") + msg)
            ok_all &= good
    print("ALL PASS" if ok_all else "SOME FAILED")
    return ok_all
