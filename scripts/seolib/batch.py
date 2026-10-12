"""Prepare a website's requested pages once, then resume the existing page driver sequentially."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import yaml

from . import common as C, pagetype, sitecontext


def read_list(path: str, kind: str = "keywords") -> list[dict]:
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig")
    if source.suffix.lower() == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
    elif source.suffix.lower() in (".yaml", ".yml", ".json"):
        rows = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
        if isinstance(rows, dict):
            rows = rows.get(kind)
    else:
        rows = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{source} needs a non-empty {kind} list")
    result = []
    for number, row in enumerate(rows, 1):
        if isinstance(row, str):
            row = {"url" if kind == "pages" or re.match(r"https?://", row, re.I) else "keyword": row}
        if not isinstance(row, dict) or not any(row.get(k) for k in ("keyword", "query", "url")):
            raise ValueError(f"{source}, row {number}: supply keyword or url")
        result.append({k: v.strip() if isinstance(v, str) else v for k, v in row.items() if v is not None})
    return result


def prepare(slug: str, rows: list[dict] | None = None, all_pages: bool = False) -> Path:
    """Make a reviewable, resumable plan and briefs. Never starts research or writing."""
    from .briefgen import make_brief
    profile = C.load_yaml(C.ROOT / "clients" / f"{slug}.yaml") or {}
    data = sitecontext.inventory(slug)
    home = sitecontext.website_url(profile["domain"])
    indexed = {C.clean_url(p["url"]).rstrip("/"): p for p in data.get("pages", [])}
    requests = list(rows or [])
    if all_pages:
        requests += [{"url": p["url"]} for p in data.get("pages", [])]
    if not requests:
        raise ValueError("Supply keywords, selected page URLs or --all-pages")
    entries = []
    merged = {}
    for row in requests:
        query = str(row.get("keyword") or row.get("query") or "").strip()
        url = sitecontext.website_url(row["url"]) if row.get("url") else ""
        if not url and re.fullmatch(r"(?:https?://|(?:www\.)?[\w-]+\.)[^\s]+", query, re.I):
            url, query = sitecontext.website_url(query), ""
        if url and C.host(url) != C.host(home):
            raise ValueError(f"Selected page is outside {profile['domain']}: {url}")
        page = indexed.get(url.rstrip("/")) if url else sitecontext.match_keyword(query, data)
        if not url and not page and sitecontext.keyword_matches(query, data):
            entries.append({"url": "", "keyword": query, "status": "blocked",
                            "reason": "multiple existing pages match this keyword; supply the intended page URL"})
            continue
        if not page and url:
            page = pagetype.intake(url)
            if not page.get("exists") and not query:
                entries.append({"url": url, "keyword": "", "status": "blocked", "reason": "page unreadable; supply a target keyword"})
                continue
        instructions = str(row.get("instructions") or "")
        explicit = row.get("page_type") or row.get("type") or pagetype.explicit_type(instructions)
        from .briefgen import WORDS
        if explicit and explicit not in WORDS:
            raise ValueError(f"Unsupported page type {explicit!r}")
        if page and page.get("exists") is False and page.get("status") not in (404, 410) and not (query and explicit):
            entries.append({"url": url, "keyword": query, "status": "blocked",
                            "reason": "page context unreadable; supply both target keyword and page_type, or a readable page"})
            continue
        query = query or (page or {}).get("target_query") or ""
        if not query:
            raise ValueError(f"No target keyword for {url}; supply one in the list")
        page_type = explicit or (page or {}).get("page_type") or pagetype.infer_type(instructions, query)[0]
        url = url or (page or {}).get("page_url") or (page or {}).get("url") or ""
        key = url.rstrip("/") or query.lower()
        if key in merged:
            if explicit and explicit != merged[key]["page_type"]:
                raise ValueError(f"Conflicting page types for {url or query}")
            if query.lower() != merged[key]["keyword"].lower():
                merged[key]["secondary_queries"].append(query)
            continue
        entry = {"keyword": query, "url": url, "page_type": page_type, "instructions": instructions,
                 "page_type_source": "explicit" if explicit else "page" if page else "keyword",
                 "task": "rewrite" if page and page.get("status") not in (404, 410) else "new", "secondary_queries": [], "status": "pending"}
        entries.append(entry)
        merged[key] = entry
    fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()[:12]
    path = C.ROOT / "batches" / f"{slug}-{fingerprint}.json"
    if path.exists():
        return path
    for entry in entries:
        if entry["status"] == "blocked":
            continue
        entry_id = hashlib.sha256((entry["url"] or entry["keyword"]).encode()).hexdigest()[:8]
        brief_slug = f"{C.slugify(entry['keyword'])}-{slug}-{entry_id}-{fingerprint[:6]}"
        brief_path = C.ROOT / "briefs" / f"{brief_slug}.yaml"
        if not brief_path.exists():
            make_brief(slug, entry["keyword"], url=entry["url"] or None, page_type=entry["page_type"],
                       task=entry["task"], slug=brief_slug, instructions=entry["instructions"] or None,
                       page_type_source=entry["page_type_source"])
        brief = C.load_yaml(brief_path)
        brief.update(instructions=entry["instructions"], target_query=entry["keyword"], page_type=entry["page_type"])
        brief.update(batch_plan=str(path), batch_item=entry_id, site_inventory=str(sitecontext.inventory_path(slug)),
                     source_context=data.get("source_context") or {}, secondary_queries=entry["secondary_queries"])
        brief_path.write_text(yaml.safe_dump(brief, sort_keys=False, allow_unicode=True), encoding="utf-8")
        entry.update(id=entry_id, brief=str(brief_path))
    C.save_json(path, {"schema_version": 1, "client_slug": slug, "domain": profile["domain"], "created_at": C.now_iso(),
                       "inventory": str(sitecontext.inventory_path(slug)), "site_discovery_complete": data.get("discovery_complete", False),
                       "inventory_gaps": data.get("gaps") or [], "items": entries})
    return path


def setup(website: str | None = None, *, keywords: str | None = None, pages: str | None = None,
          all_pages: bool = False, rows: list[dict] | None = None, max_pages: int = 250,
          refresh: bool = False, bind: bool = True, run: bool = False, mode: str | None = None) -> Path | None:
    if website:
        candidate = C.ROOT / "clients" / f"{website}.yaml" if re.fullmatch(r"[\w-]+", website) else C.ROOT / "clients" / "__no_slug__.yaml"
        slug = candidate.stem if candidate.exists() else sitecontext.client_for_website(website, create=True)[0]
    else:
        context = sitecontext.resolve_client()
        if not context:
            raise SystemExit("NEED A CLIENT: give the website domain or page link; no single website context is configured")
        slug = context[0]
    requests = list(rows or [])
    if keywords:
        requests += read_list(keywords)
    if pages:
        requests += read_list(pages, "pages")
    data = sitecontext.discover(slug, max_pages, refresh, [r["url"] for r in requests if r.get("url")])
    if bind:
        sitecontext.bind_client(slug)
    print(f"WEBSITE: {data['domain']}; {len(data['pages'])} pages read; {len(data['frontier'])} pending; {len(data['gaps'])} gaps")
    if not data["discovery_complete"]:
        print("SITE INVENTORY INCOMPLETE: repeat site discovery to resume the saved frontier; unread pages have not been silently dropped")
    if not requests and not all_pages:
        print(f"CONTEXT SAVED: {sitecontext.inventory_path(slug)}; keyword-only requests can use this website")
        return None
    plan = prepare(slug, requests, all_pages)
    print(f"BATCH PLAN: {plan}")
    if run:
        next_page(str(plan), mode)
    return plan


def route_request(text: str, mode: str | None = None) -> bool:
    """Explicit list syntax works through every installed /page-seo adapter."""
    import re
    match = re.fullmatch(r"(?:(.+?)\s*\|\s*)?(keywords|pages):\s*(.+)", text.strip(), re.I | re.S)
    if not match:
        return False
    website, kind, value = match.groups()
    source = Path(value.strip().strip('"'))
    try:
        is_file = len(value) < 240 and "\n" not in value and ";" not in value and source.is_file()
    except OSError:
        is_file = False
    if is_file:
        setup(website.strip() if website else None, **{kind.lower(): str(source)}, run=True, mode=mode)
    else:
        if not re.match(r"https?://", value, re.I) and "\n" not in value and ";" not in value and source.suffix.lower() in (".txt", ".csv", ".json", ".yaml", ".yml"):
            raise FileNotFoundError(f"List file not found: {source}")
        values = [x.strip() for x in re.split(r"[\n;]+", value) if x.strip()]
        if not values:
            raise ValueError("Give a list file or semicolon-separated keywords/page URLs")
        rows = [{"url" if kind.lower() == "pages" else "keyword": x} for x in values]
        setup(website.strip() if website else None, rows=rows, run=True, mode=mode)
    return True


def next_page(path: str, mode: str | None = None, completed: dict | None = None) -> None:
    from .driver import CMD, next_step
    target = Path(path)
    with C.file_lock(target):
        plan = C.load_json(target)
        if not plan or not isinstance(plan.get("items"), list):
            raise ValueError(f"Invalid batch plan: {target}")
        if mode:
            plan["mode"] = mode
        mode = mode or plan.get("mode")
        if completed:
            item = next((i for i in plan["items"] if i.get("id") == completed["id"]), None)
            if not item:
                raise ValueError("Completed page is not in this batch")
            item.update(status="complete", result=completed["result"], completed_at=C.now_iso())
        pending = next((i for i in plan["items"] if i["status"] == "running"), None) or next(
            (i for i in plan["items"] if i["status"] == "pending"), None)
        if pending:
            pending["status"] = "running"
        C.save_json(target, plan)
    if pending:
        print(f"BATCH PAGE: {pending['keyword']} ({pending['page_type']}); plan {target}")
        next_step(pending["brief"], mode)
        return
    blocked = [i for i in plan["items"] if i["status"] == "blocked"]
    print("STOPPED" if blocked else "DONE")
    print(f"Batch: {target}; {sum(i['status'] == 'complete' for i in plan['items'])} complete; {len(blocked)} blocked")
    for item in blocked:
        print(f"NEEDS INPUT: {item.get('url') or item.get('keyword')} — {item.get('reason')}")
    print(f"Results: {[i.get('result') for i in plan['items'] if i.get('result')]}")
    if blocked:
        print(f"Correct the blocked entries and prepare a new plan with: {CMD()} site <website> --pages <file>")
