"""`seo.py gsc ...` and the `/page-seo <website> | gsc ...` route.

  seo.py gsc status  [client]                     route (API/MCP), stored datasets and their age
  seo.py gsc pull    <client> [--refresh] [--only a,b]   API route: fill the store
  seo.py gsc plan    <client> [--only a,b]        MCP route: the exact tool calls to make, and the ingest commands
  seo.py gsc ingest  <client> <dataset> <file>    store MCP output, an API JSON, a UI CSV export or pasted text
  seo.py gsc inspect <client> [--limit N]         URL Inspection on the most valuable URLs (2,000/day quota)
  seo.py gsc audit   <client>                     every playbook -> sites/<client>/gsc/audit.md, actions.json
  seo.py gsc data    <client> <view> [--page U] [--query Q] [--topic T] [--json]   any view, for any agent
  seo.py gsc queue   <client> [--kinds optimizer,questions,new,decay,ctr,ccni] [--limit N] [--run]
  seo.py gsc crawl   <client> <export>            Crawl Stats export/paste -> waste clusters, robots proposal
  seo.py gsc robots  <client> [--test URL ...] [--rule "Disallow: /x" ...]   live robots.txt, Google's matching
  seo.py gsc render  <url>                        raw vs rendered HTML (URL Inspection's rendered view, approximated)
  seo.py gsc log     <client> <url> "<what changed>"   add to the dated change log
"""
from __future__ import annotations

import json
import re

from .. import common as C
from . import api, store as S

SEP = "-" * 72


def resolve(client: str | None, create: bool = False) -> str:
    from ..sitecontext import client_for_website, resolve_client
    if client:
        if (C.ROOT / "clients" / f"{client}.yaml").exists():
            return client
        slug, prof = client_for_website(client, create=create)
        if prof or create:
            return slug
        raise ValueError(f"no client profile for {client}: run `seo.py client <slug> <domain>` or `seo.py site {client}` first")
    ctx = resolve_client()
    if not ctx:
        raise SystemExit("NEED A CLIENT: give the website domain (no single website context is configured)")
    return ctx[0]


def _print(obj, as_json: bool) -> None:
    if as_json or not isinstance(obj, (list, dict)):
        print(json.dumps(obj, ensure_ascii=False, indent=1) if not isinstance(obj, str) else obj)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            print(f"{k}: {json.dumps(v, ensure_ascii=False)[:600]}")
        return
    for x in obj[:60]:
        print("- " + json.dumps(x, ensure_ascii=False)[:500])
    if len(obj) > 60:
        print(f"... {len(obj) - 60} more (use --json)")


def status(slug: str) -> dict:
    why = api.configured()
    return {"client": slug, "property": S.property_for(slug), "api_route": "ready" if not why else f"not configured ({why})",
            "store": S.site_dir(slug).as_posix(), "datasets": S.manifest(slug)}


def main(a) -> int:
    from .bus import Console, VIEWS
    act = a.action
    if act == "render":
        from .render import check
        _print(check(a.args[0]), a.json)
        return 0
    slug = resolve(a.args[0] if a.args else None)
    rest = a.args[1:]
    if act == "status":
        _print(status(slug), a.json)
    elif act == "pull":
        from .audit import pull
        _print(pull(slug, a.only.split(",") if a.only else None, a.refresh), a.json)
    elif act == "plan":
        from .mcp import plan_text
        print("\n".join(plan_text(slug, a.only.split(",") if a.only else None)))
    elif act == "ingest":
        from .mcp import ingest
        if len(rest) < 2:
            raise ValueError("usage: seo.py gsc ingest <client> <dataset> <file>; datasets: "
                             + ", ".join(list(S.DATASETS) + ["inspections", "sitemaps"] + list(S.UI_DATASETS)))
        _print(ingest(slug, rest[0], rest[1]), a.json)
    elif act == "inspect":
        from .audit import inspect
        _print(inspect(slug, a.limit or 200), a.json)
    elif act == "audit":
        from .audit import run
        o = run(slug)
        print(f"AUDIT {(S.site_dir(slug) / 'audit.md').as_posix()}  ({len(o['actions'])} actions)")
    elif act == "data":
        if not rest:
            print("views:\n" + "\n".join(f"  {k:16s} {v}" for k, v in VIEWS.items()))
            return 0
        g = Console(slug)
        res = g.view(rest[0], page=a.page, query=a.query, topic=a.topic)
        if isinstance(res, list) and a.limit:
            res = res[: a.limit]
        _print(res, a.json)
    elif act == "queue":
        from .audit import queue
        plan = queue(slug, a.kinds.split(",") if a.kinds else None, a.limit or 10, run_now=a.run)
        print(f"BATCH PLAN: {plan}" if plan else "Nothing to queue: no rewrite/new actions of those kinds in actions.json")
    elif act == "crawl":
        from .mcp import ingest
        from .audit import run
        ingest(slug, "ui_crawl_stats", rest[0])
        o = run(slug) if Console(slug).available() else None
        cr = (o or {}).get("views", {}).get("crawl")
        if not cr:
            from .crawl import analyse
            cr = analyse((S.load(slug, "ui_crawl_stats") or {}).get("items") or {})
        _print(cr, a.json)
    elif act == "robots":
        from .crawl import fetch_robots, parse_robots, allowed, test_rules
        r = fetch_robots(S.profile(slug).get("domain") or slug)
        out = {k: v for k, v in r.items() if k != "text"}
        if a.test:
            p = parse_robots(r.get("text", ""))
            out["tests"] = [{"url": u, "allowed": allowed(p, u)[0], "rule": allowed(p, u)[1]} for u in a.test]
        if a.rule:
            imp = [x["page"] for x in sorted(S.rows(slug, "pages"), key=lambda x: -x["impressions"])[:300]]
            out["proposal"] = test_rules(r.get("text", ""), a.rule, imp + (a.test or []))
        _print(out, a.json)
    elif act == "log":
        S.log_change(slug, {"url": rest[0], "kind": "manual", "note": " ".join(rest[1:])})
        print("logged")
    else:
        raise ValueError(f"unknown gsc action {act}")
    return 0


# ---------------------------------------------------------------- /page-seo <website> | gsc ...

ROUTE = re.compile(r"^\s*(?:(?P<site>[^|]+?)\s*\|\s*)?(?:gsc|search console|google search console)\b\s*:?\s*(?P<rest>.*)$", re.I | re.S)


def route(text: str) -> bool:
    m = ROUTE.match(text or "")
    # only an explicit request: "<site> | gsc [action]" or "gsc[:] <action> ...", never a keyword about Search Console
    if not m:
        return False
    rest = (m.group("rest") or "").strip().lower()
    if not (re.match(r"(audit|queue|crawl|page|inspect)\b", rest) or (m.group("site") and not rest)):
        return False
    start(m.group("site"), m.group("rest") or "")
    return True


def start(site: str | None, rest: str) -> None:
    """The operator flow: audit (default), queue, crawl <file>, page <url>, inspect. Prints DONE, STOPPED or one
    NEXT TASK, like the page driver."""
    from ..driver import CMD, ARG
    from .audit import pull, inspect, run, queue
    from .bus import Console
    slug = resolve(site.strip() if site else None, create=True)
    words = rest.split()
    act = (words[0].lower() if words else "audit")
    request = f"{site + ' | ' if site else ''}gsc {rest}".strip()
    if act == "queue":
        kinds = [w for w in words[1:] if w in ("optimizer", "questions", "new", "decay", "ctr", "ccni")] or None
        n = next((int(w) for w in words[1:] if w.isdigit()), 10)
        plan = queue(slug, kinds, n, run_now=True)
        if not plan:
            print("STOPPED\nNothing to queue: run the audit first (`/page-seo <website> | gsc`) or choose other kinds.")
        return
    if act == "page" and len(words) > 1:
        _print(Console(slug).page(words[1]), True)
        return
    if act == "crawl" and len(words) > 1:
        from .mcp import ingest
        ingest(slug, "ui_crawl_stats", " ".join(words[1:]).strip('"'))
    why = api.configured()
    g = Console(slug)
    if why and not (g.available() and S.fresh(slug, "query_page")):
        print(SEP)
        print("NEXT TASK: FETCH SEARCH CONSOLE DATA (role: operator, through your Search Console MCP server)")
        print(SEP)
        print(f"The API route is not set up ({why}), so the data comes through the MCP server attached to you. "
              "If no Search Console MCP server is attached, stop and reply: STOPPED: connect a Search Console MCP "
              f"server (see {(C.ROOT / 'plugins' / 'mcp_hub' / 'gsc' / 'SKILL.md').as_posix()}) or set "
              "GSC_SERVICE_ACCOUNT_JSON.")
        print()
        from .mcp import plan_text
        print("\n".join(plan_text(slug)))
        print()
        print(f"Then run: {CMD()} start {ARG(request)}")
        print("Do only this task.")
        return
    if not why:
        got = pull(slug)
        print("PULL " + ", ".join(f"{k}: {v}" for k, v in got.items()))
        ins = inspect(slug, 200)
        print(f"INSPECT {ins}")
    o = run(slug)
    print(SEP)
    print("DONE")
    print(SEP)
    print(f"Audit:   {(S.site_dir(slug) / 'audit.md').as_posix()}")
    print(f"Actions: {(S.site_dir(slug) / 'actions.json').as_posix()} ({len(o['actions'])}; "
          f"{sum(a['kind'] in ('rewrite', 'new') for a in o['actions'])} can go to the page pipeline)")
    print(f"To rewrite the top pages: /page-seo {site or slug} | gsc queue optimizer 10 "
          "(kinds: optimizer, questions, new, decay, ctr, ccni)")
    if o.get("missing_ui"):
        print(f"Not reachable through the API (export from Search Console, then `{CMD()} gsc ingest {slug} <dataset> <file>`): "
              + ", ".join(o["missing_ui"]))
    print("Stop here. Reply with the audit path, the number of actions and the queue command, and nothing else.")
