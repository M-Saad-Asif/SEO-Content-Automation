#!/usr/bin/env python3
"""ASDivigitals page-SEO pipeline: one CLI for every deterministic step.

  python scripts/seo.py next     <brief.yaml>    # THE ENTRY POINT: runs the next step, prints the agent's one task
  python scripts/seo.py done     <brief.yaml> research|expert|review|expert_read|editor|verify|internal_links   # confirm an agent task the driver asked for
  python scripts/seo.py doctor                             # check Python, packages, spaCy model, keys, plugins
  python scripts/seo.py read     <url>                     # a page's text (HTML or PDF), for agents without a fetch tool

Lower-level commands (the driver calls these; agents only use them when a printed task says so):

  python scripts/seo.py client   <slug> <domain>          # new client profile from the live site (any niche)
  python scripts/seo.py brief    <client> "<query>" [--type guide|spoke|hub|product-guide|service]
  python scripts/seo.py research <brief.yaml> [--refresh]   # all research plugins
    python scripts/seo.py plugins                            # list the plugin harness
  python scripts/seo.py ingest   <run-dir> <plugin> <file.json>   # MCP route: store raw connector data, re-run downstream
  python scripts/seo.py prep     <brief.yaml> [--refresh]  # foundation only (site, products, official facts)
  python scripts/seo.py prep     <brief.yaml> --add-fact ID "claim" "value" URL [--source-text-file F] [--scope "who/when"]
  python scripts/seo.py prep     <brief.yaml> --add-facts facts.yaml   # many facts in one call (list of id, claim, value, url, scope)
  python scripts/seo.py capture  <url> <text-file>        # page text you read with your own browser
  python scripts/seo.py lint     <run-dir|brief.yaml> [--file other.md] [--json]
  python scripts/seo.py review   <run-dir>                 # editor's pass: each claim next to its fact, section shapes, gaps
  python scripts/seo.py validate <run-dir|brief.yaml>
  python scripts/seo.py mark     <run-dir|brief.yaml> <step> start|end
  python scripts/seo.py report   <run-dir|brief.yaml>
  python scripts/seo.py test     [fixture-name]          # regression fixtures

See WORKFLOW.md. Scripts do everything deterministic; the agent only writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seolib import common as C  # noqa: E402


def main(argv=None) -> int:
    C.utf8_stdout()
    ap = argparse.ArgumentParser(prog="seo.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("brief")
    p.add_argument("--refresh", action="store_true", help="ignore the cache")
    p.add_argument("--add-fact", nargs=4, metavar=("ID", "CLAIM", "VALUE", "URL"))
    p.add_argument("--add-facts", metavar="FILE", help="many facts at once: a YAML/JSON list of {id, claim, value, url, scope}")
    p.add_argument("--source-text-file", help="page text you captured when the source blocks scripts")
    p.add_argument("--scope", help="who/what/when the fact applies to (a group, product, country, tax year, version)")
    p = sub.add_parser("research")
    p.add_argument("brief")
    p.add_argument("--mode", choices=["full", "fast", "deep", "quick"], default=None, help=argparse.SUPPRESS)
    p.add_argument("--refresh", action="store_true")
    p = sub.add_parser("outline")
    p.add_argument("run")
    sub.add_parser("plugins")
    p = sub.add_parser("client")
    p.add_argument("slug")
    p.add_argument("domain")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("brief")
    p.add_argument("client")
    p.add_argument("query")
    p.add_argument("--url")
    p.add_argument("--type", default=None, choices=["guide", "hub", "spoke", "product-guide", "service",
                                                        "location", "product", "category", "home", "company"])
    p.add_argument("--words", nargs=2, type=int)
    p.add_argument("--task", default="new", choices=["new", "rewrite"])
    p.add_argument("--checks", nargs="*")
    p.add_argument("--slug")
    p = sub.add_parser("eval")
    p.add_argument("run")
    p = sub.add_parser("ingest")
    p.add_argument("run")
    p.add_argument("plugin", choices=["gsc_insights", "keyword_research", "clarity_ux", "reddit_voice"])
    p.add_argument("file")
    p = sub.add_parser("capture")
    p.add_argument("url")
    p.add_argument("text_file")
    p = sub.add_parser("lint")
    p.add_argument("run")
    p.add_argument("--file", help="lint this file instead of the run's draft.md (does not touch timing)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("review")
    p.add_argument("run")
    p = sub.add_parser("validate")
    p.add_argument("run")
    p.add_argument("--refresh-links", action="store_true")
    p = sub.add_parser("mark")
    p.add_argument("run")
    p.add_argument("step")
    p.add_argument("ev", choices=["start", "end", "event"])
    p = sub.add_parser("report")
    p.add_argument("run")
    p = sub.add_parser("test")
    p.add_argument("name", nargs="?")
    p.add_argument("--offline", action="store_true", help="unit regressions only; no network, client runs or paid APIs")
    p = sub.add_parser("start")
    p.add_argument("request", nargs="*", help="a brief, URL/domain, keyword, or: <website> | keywords: <file>")
    p.add_argument("--mode", choices=["full", "fast", "deep", "quick"], help=argparse.SUPPRESS)
    p.add_argument("--site", help="website domain or saved client slug")
    p.add_argument("--keywords", help="CSV, YAML, JSON or one-keyword-per-line file")
    p.add_argument("--pages", help="selected page URLs in a list file")
    p.add_argument("--all-pages", action="store_true")
    p.add_argument("--max-pages", type=int, default=250)
    p = sub.add_parser("site", help="read a website, save reusable context and optionally prepare a page queue")
    p.add_argument("website", nargs="?")
    p.add_argument("--keywords")
    p.add_argument("--pages")
    p.add_argument("--all-pages", action="store_true")
    p.add_argument("--max-pages", type=int, default=250)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--no-default", action="store_true", help="do not bind this project to the website")
    p = sub.add_parser("batch", help="resume a prepared website page queue")
    p.add_argument("plan")
    p.add_argument("--mode", choices=["full", "fast", "deep", "quick"], help=argparse.SUPPRESS)
    p = sub.add_parser("next")
    p.add_argument("brief")
    p.add_argument("--mode", choices=["full", "fast", "deep", "quick"], help=argparse.SUPPRESS)
    p = sub.add_parser("done")
    p.add_argument("brief")
    p.add_argument("step", choices=["research", "expert", "review", "expert_read", "editor", "verify", "internal_links", "retry"])
    sub.add_parser("doctor")
    p = sub.add_parser("read")
    p.add_argument("url")
    a = ap.parse_args(argv)

    if a.cmd == "read":
        from seolib.driver import read_page
        return 0 if read_page(a.url) else 1

    if a.cmd == "start":
        if a.keywords or a.pages or a.all_pages:
            from seolib.batch import setup
            setup(a.site, keywords=a.keywords, pages=a.pages, all_pages=a.all_pages, max_pages=a.max_pages, run=True, mode=a.mode)
            return 0
        from seolib.driver import start
        start((a.site + ": " if a.site else "") + " ".join(a.request), a.mode)
        return 0
    if a.cmd == "site":
        from seolib.batch import setup
        setup(a.website, keywords=a.keywords, pages=a.pages, all_pages=a.all_pages, max_pages=a.max_pages,
              refresh=a.refresh, bind=not a.no_default)
        return 0
    if a.cmd == "batch":
        from seolib.batch import next_page
        next_page(a.plan, a.mode)
        return 0
    if a.cmd == "next":
        from seolib.driver import next_step
        next_step(a.brief, a.mode)
        return 0
    if a.cmd == "done":
        from seolib.driver import mark_done
        mark_done(a.brief, a.step)
        return 0
    if a.cmd == "doctor":
        from seolib.driver import doctor
        return 0 if doctor() else 1

    if a.cmd == "prep":
        from seolib.prep import prep, add_fact
        if a.add_facts:
            from seolib.prep import add_facts
            try:
                out = add_facts(a.brief, a.add_facts)
            except ValueError as e:
                print(f"FACTS INVALID: {e}")
                return 1
            return 0 if out and all(f["status"] in ("verified", "captured", "operator") for f in out) else 1
        if a.add_fact:
            f = add_fact(a.brief, *a.add_fact, source_text_file=a.source_text_file, scope=a.scope)
            return 0 if f["status"] in ("verified", "captured", "operator") else 1
        from seolib.prep import load_brief, run_dir
        rd = run_dir(load_brief(a.brief))
        if (rd / "research").exists():  # a researched run: refresh everything, never drop the research
            from seolib.harness import run_research
            run_research(a.brief, None, a.refresh)
            return 0
        prep(a.brief, a.refresh)
        return 0
    if a.cmd == "research":
        from seolib.harness import run_research
        run_research(a.brief, a.mode, a.refresh)
        return 0
    if a.cmd == "outline":
        from seolib.validate import resolve_run
        from seolib.outline import check_outline
        return 0 if check_outline(resolve_run(a.run)) else 1
    if a.cmd == "plugins":
        from seolib.harness import manifests
        for n, m in manifests().items():
            print(f"{n:18s} {m.get('kind'):7s} needs={m.get('needs', [])} modes={m.get('modes', [])}")
            print(f"    {m.get('description', '')}")
        return 0
    if a.cmd == "client":
        from seolib.onboard import onboard
        onboard(a.slug, a.domain, a.force)
        return 0
    if a.cmd == "brief":
        from seolib.briefgen import make_brief
        make_brief(a.client, a.query, a.url, a.type, a.words, a.task, a.checks, a.slug)
        return 0
    if a.cmd == "eval":
        from seolib.validate import resolve_run
        from seolib.evaluate import evaluate
        r = evaluate(resolve_run(a.run))
        print(json.dumps({k: r[k] for k in ("ours", "human_baseline", "humanization_flags", "lint")}, indent=1))
        return 0
    if a.cmd == "ingest":
        from seolib.validate import resolve_run
        from seolib.harness import rerun_dependents
        from seolib.prep import load_brief
        need = {"gsc_insights": "page_rows", "keyword_research": "keywords", "clarity_ux": "metrics",
                "reddit_voice": "threads"}[a.plugin]
        data = json.loads(Path(a.file).read_text(encoding="utf-8"))
        if need not in data:
            print(f"INGEST REJECTED: {a.plugin} raw data needs a top-level \"{need}\" key (see plugins/{a.plugin}/SKILL.md)")
            return 2
        rd = resolve_run(a.run)
        data["_ingested_at"] = C.now_iso()
        C.save_json(rd / "research" / "raw" / f"{a.plugin}.json", data)
        sheet = C.load_json(rd / "fact_sheet.json")
        brief_path = next((p for p in [C.ROOT / "briefs" / (rd.name.split("-", 3)[-1] + ".yaml")] if p.exists()), None)
        brief = load_brief(sheet.get("brief_path") or str(brief_path))
        rerun_dependents(rd, brief, a.plugin)
        return 0
    if a.cmd == "capture":
        from seolib.prep import capture
        capture(a.url, a.text_file)
        return 0
    if a.cmd == "lint":
        from seolib.validate import resolve_run
        from seolib.lint import lint_text, print_findings, load_research
        from seolib.timing import mark
        rd = resolve_run(a.run)
        target = Path(a.file) if a.file else rd / "draft.md"
        if not target.exists():
            print(f"No draft to lint yet: write {target.as_posix()} first.")
            return 2
        if not a.file:
            mark(rd, "lint", "start")
        res = lint_text(target.read_text(encoding="utf-8"), C.load_json(rd / "fact_sheet.json"), C.load_json(rd / "link_map.json", {}), load_research(rd))
        if not a.file:
            C.save_json(rd / "lint.json", res)
            mark(rd, "lint", "end")
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print_findings(res)
        return 0 if res["summary"]["block"] == 0 else 1
    if a.cmd == "review":
        from seolib.validate import resolve_run
        from seolib.review import review
        review(resolve_run(a.run))
        return 0
    if a.cmd == "validate":
        from seolib.validate import validate
        return 0 if validate(a.run, a.refresh_links) else 1
    if a.cmd == "mark":
        from seolib.validate import resolve_run
        from seolib.timing import mark
        rd = resolve_run(a.run)
        mark(rd, a.step, a.ev)
        print(json.dumps(C.load_json(rd / "timing.json")["summary"]))
        return 0
    if a.cmd == "report":
        from seolib.validate import resolve_run, write_report
        rd = resolve_run(a.run)
        write_report(rd, C.load_json(rd / "fact_sheet.json"), C.load_json(rd / "lint.json", {}))
        print((rd / "report.md").read_text(encoding="utf-8"))
        return 0
    if a.cmd == "test":
        if a.offline:
            import unittest
            suite = unittest.defaultTestLoader.discover(str(C.ROOT / "tests"), pattern="test_*.py")
            return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
        from seolib.fixtures import run_fixtures
        return 0 if run_fixtures(a.name) else 1
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileNotFoundError) as error:
        print(f"INPUT ERROR: {error}")
        sys.exit(2)
