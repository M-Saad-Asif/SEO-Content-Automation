"""The MCP route: what to ask a Search Console MCP server for, and how its answers enter the store.

`request(name)` builds the exact searchAnalytics body for a dataset; the API route sends it, the MCP route prints
it as a tool call. `ingest()` accepts whatever the server or the user hands back: the API's own JSON ({rows: [{keys,
...}]}), a list of row objects with named fields (any server's shape: query/page/clicks/... in any case or
snake_case), a Search Console UI export (CSV with "Top queries", "Clicks", "CTR" headers), URL Inspection results,
sitemaps, or pasted Crawl Stats text. Numbers are never invented: a file without metrics is rejected.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from .. import common as C
from . import api, store as S

# Tool names per server for each capability (from each server's README/source, Nov 2026). The skill tells the agent
# to run its server's tools/list first and use whatever matches; these are hints, not a dependency.
TOOLS = {
    "search_analytics": {"open-gsc-mcp": "query_search_analytics (page with next_start_row)",
                         "mcp-search-console (AminForou)": "get_advanced_search_analytics / get_search_analytics",
                         "mcp-server-gsc (ahonn)": "search_analytics (regex via 'regex:' prefix; no startRow)",
                         "suganthan-gsc-mcp": "search analytics query tool", "gsc-mcp-tools": "search analytics tool"},
    "hourly": {"open-gsc-mcp": "query_hourly_analytics", "others": "not supported: skip the hourly dataset"},
    "discover": {"open-gsc-mcp": "query_discover_analytics", "others": "search analytics with type=discover"},
    "news": {"open-gsc-mcp": "query_google_news_analytics", "others": "search analytics with type=googleNews"},
    "inspect": {"open-gsc-mcp": "batch_inspect_urls (50 per call)", "mcp-search-console (AminForou)": "batch_url_inspection (10 per call)",
                "mcp-server-gsc (ahonn)": "index_inspect (one URL)"},
    "sitemaps": {"open-gsc-mcp": "list_sitemaps", "mcp-search-console (AminForou)": "get_sitemaps", "mcp-server-gsc (ahonn)": "list_sitemaps"},
}
NEVER = ["submit_sitemap", "delete_sitemap", "manage_sitemaps", "add_site", "delete_site", "request_indexing",
         "indexing API submits", "any tool that changes the property"]


def request(name: str) -> dict:
    spec = S.DATASETS[name]
    start, end = api.window(spec["days"], spec.get("lag", 3), spec.get("back", 0))
    body = {"startDate": start, "endDate": end, "dimensions": spec["dims"], "type": spec.get("type", "web"),
            "dataState": spec.get("state", "final")}
    if spec.get("agg"):
        body["aggregationType"] = spec["agg"]
    return body


def fetch_plan(slug: str, names: list[str] | None = None, outdir: Path | None = None) -> list[dict]:
    prop = S.property_for(slug)
    outdir = outdir or (S.site_dir(slug) / "incoming")
    plan = []
    for n in names or list(S.DATASETS):
        spec, body = S.DATASETS[n], request(n)
        cap = "hourly" if n == "hourly" else "discover" if n == "discover" else "news" if n == "news" else "search_analytics"
        plan.append({"dataset": n, "why": spec["why"], "capability": cap, "tools": TOOLS[cap],
                     "params": {"siteUrl": prop, **body, "rowLimit": 25000, "max_rows": spec.get("max_rows", 25000)},
                     "save_to": (outdir / f"{n}.json").as_posix()})
    return plan


def plan_text(slug: str, names: list[str] | None = None) -> list[str]:
    from ..driver import CMD
    L = [f"Property: {S.property_for(slug)} (a Domain property is `sc-domain:example.com`; a URL-prefix property is "
         "`https://www.example.com/` with the slash). First run your server's tool list; use read-only tools only, never: "
         + ", ".join(NEVER) + ".", ""]
    for i, p in enumerate(fetch_plan(slug, names), 1):
        pr = p["params"]
        L.append(f"{i}. `{p['dataset']}` ({p['why']}): tool {list(p['tools'].values())[0]} or your server's equivalent; "
                 f"siteUrl {pr['siteUrl']}, {pr['startDate']}..{pr['endDate']}, dimensions {pr['dimensions']}, type {pr['type']}, "
                 f"dataState {pr['dataState']}" + (f", aggregationType {pr['aggregationType']}" if pr.get("aggregationType") else "")
                 + f", up to {pr['max_rows']} rows (page with startRow/next_start_row when the server allows). Save the raw "
                 f"tool output as JSON to {p['save_to']}, then run `{CMD()} gsc ingest {slug} {p['dataset']} \"{p['save_to']}\"`.")
    L += ["", "A dataset the server can't return (no Discover traffic, no hourly tool) is skipped: say so, never fill it in.",
          "Quote numbers only from tool output; an empty result usually means the wrong property format or an account "
          "without access, not zero traffic."]
    return L


# ---------------------------------------------------------------- ingest

HEADERS = {"query": ("query", "queries", "top queries", "keys_query", "search query", "keyword"),
           "page": ("page", "pages", "top pages", "url", "landing page", "address"),
           "country": ("country", "countries"), "device": ("device", "devices"), "date": ("date", "day"),
           "searchAppearance": ("searchappearance", "search appearance", "search_appearance", "appearance"),
           "hour": ("hour", "datetime"),
           "clicks": ("clicks", "url clicks"), "impressions": ("impressions",), "ctr": ("ctr", "url ctr"),
           "position": ("position", "avg position", "average position", "avg. position")}


def _key(k: str) -> str | None:
    k2 = re.sub(r"[^a-z ]", "", re.sub(r"([a-z])([A-Z])", r"\1 \2", str(k)).replace("_", " ").lower()).strip()
    for std, alts in HEADERS.items():
        if k2 in alts or k2.replace(" ", "") in [a.replace(" ", "") for a in alts]:
            return std
    return None


def _num(v, pct: bool = False) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "0").strip().replace(",", "")
    if s.endswith("%"):
        return float(s[:-1] or 0) / 100
    try:
        return float(s)
    except ValueError:
        return 0.0


def norm_rows(items: list, dims: list[str] | None = None) -> list[dict]:
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if "keys" in it and dims:
            rec = dict(zip(dims, it["keys"]))
            rest = {k: v for k, v in it.items() if k != "keys"}
        else:
            rec, rest = {}, it
        for k, v in rest.items():
            std = _key(k)
            if std:
                rec[std] = v
        if "clicks" not in rec and "impressions" not in rec:
            continue
        for m in ("clicks", "impressions"):
            rec[m] = int(_num(rec.get(m)))
        ctr = rec.get("ctr")
        rec["ctr"] = _num(ctr) if ctr is not None else (rec["clicks"] / rec["impressions"] if rec["impressions"] else 0.0)
        if rec["ctr"] > 1:  # "4.5" meaning 4.5%
            rec["ctr"] /= 100
        rec["position"] = round(_num(rec.get("position")), 2)
        for d in ("query", "page", "country", "device"):
            if d in rec and isinstance(rec[d], str):
                rec[d] = rec[d].strip().lower() if d in ("query", "country") else rec[d].strip()
        out.append(rec)
    return out


def _find_list(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for k in ("rows", "data", "results", "items", "result", "content"):
            v = d.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                got = _find_list(v)
                if got is not None:
                    return got
            if isinstance(v, str) and v.strip()[:1] in "[{":  # MCP text content holding JSON
                try:
                    return _find_list(json.loads(v))
                except ValueError:
                    pass
    return None


def ingest(slug: str, dataset: str, file: str) -> dict:
    p = Path(file)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    src = "csv" if p.suffix.lower() in (".csv", ".tsv") else "mcp"
    if dataset == "ui_crawl_stats":
        from .crawl import parse_export
        parsed = parse_export(p)
        S.save(slug, dataset, items=parsed, meta={"source": "ui"})
        return {"dataset": dataset, "urls": len(parsed["urls"]), "shares": len(parsed["shares"])}
    if dataset == "inspections":
        data = json.loads(text)
        items = data if isinstance(data, dict) and not _find_list(data) else {}
        if not items:
            for it in _find_list(data) or []:
                u = it.get("url") or it.get("inspectionUrl") or it.get("inspection_url") or it.get("page")
                if u:
                    items[u] = it
        prev = (S.load(slug, "inspections") or {}).get("items") or {}
        stamp = C.now_iso()
        for v in items.values():
            if isinstance(v, dict):
                v.setdefault("_inspected_at", stamp)
        S.save(slug, "inspections", items={**prev, **items}, meta={"source": src})
        return {"dataset": dataset, "items": len(items)}
    if dataset == "sitemaps":
        data = json.loads(text)
        S.save(slug, dataset, rows=_find_list(data) or data.get("sitemap") or [], meta={"source": src})
        return {"dataset": dataset}
    if dataset.startswith("ui_") and p.suffix.lower() not in (".csv", ".tsv", ".json"):
        S.save(slug, dataset, items={"text": text}, meta={"source": "ui"})
        return {"dataset": dataset, "text_chars": len(text)}
    dims = (S.DATASETS.get(dataset) or {}).get("dims")
    if p.suffix.lower() in (".csv", ".tsv"):
        rows = list(csv.DictReader(io.StringIO(text), dialect="excel-tab" if p.suffix.lower() == ".tsv" else "excel"))
        rows = norm_rows(rows)
        src = "ui" if dataset.startswith("ui_") else "csv"
    else:
        data = json.loads(text)
        lst = _find_list(data)
        if lst is None:
            raise ValueError(f"{file}: no list of rows found (expected the API's rows, or a list of row objects)")
        rows = norm_rows(lst, dims)
    if not rows and not dataset.startswith("ui_"):
        raise ValueError(f"{file}: no rows with clicks/impressions; nothing stored (numbers are never invented)")
    if dims:
        missing = [d for d in dims if rows and d not in rows[0]]
        if missing:
            raise ValueError(f"{dataset} needs the dimensions {dims}; the rows have no {missing}")
    meta = {"source": src, "dims": dims}
    if dataset in S.DATASETS:
        body = request(dataset)
        meta.update(window=[body["startDate"], body["endDate"]], type=body["type"])
    S.save(slug, dataset, rows=rows, meta=meta)
    return {"dataset": dataset, "rows": len(rows), "source": src}
