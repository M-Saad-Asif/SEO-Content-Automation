"""The per-website Search Console store: sites/<slug>/gsc/<dataset>.json, one file per dataset.

Each file is {"meta": {dataset, source (api|mcp|ui|csv), fetched_at, window, dims, type, property, truncated},
"rows": [...]} (inspections: {"meta", "items": {url: result}}). The same dataset names are used by the API pull,
the MCP fetch plan, `seo.py gsc ingest` and every reader, so a dataset is interchangeable whichever route filled it.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .. import common as C

# Performance datasets: what an experienced SEO pulls for a site audit. `window`: days, and how many days earlier
# it ends ("back"); 16 months is the API's retention. A dataset Google rejects for a site (no Discover traffic) is
# recorded as empty, never retried in a loop.
DATASETS: dict[str, dict] = {
    "pages": {"dims": ["page"], "days": 90, "agg": "byPage", "why": "page totals (byPage), the base of every page playbook"},
    "pages_prev": {"dims": ["page"], "days": 90, "back": 90, "agg": "byPage", "why": "previous 90 days: decay, emerging"},
    "pages_yoy": {"dims": ["page"], "days": 90, "back": 365, "agg": "byPage", "why": "same 90 days last year: decay, AI decoupling"},
    "query_page": {"dims": ["query", "page"], "days": 90, "max_rows": 100000,
                   "why": "the page x query map: striking distance, page optimiser, questions, cannibalisation"},
    "query_page_prev": {"dims": ["query", "page"], "days": 90, "back": 90, "max_rows": 50000,
                        "why": "previous 90 days of queries: emerging queries, topical growth"},
    "queries": {"dims": ["query"], "days": 90, "agg": "byProperty", "max_rows": 50000,
                "why": "site query totals (byProperty): the site's own CTR curve, brand split, intent mix"},
    "page_device": {"dims": ["page", "device"], "days": 90, "max_rows": 50000, "why": "mobile-first device gaps"},
    "page_country": {"dims": ["page", "country"], "days": 90, "max_rows": 50000, "why": "country gaps for the target market"},
    "appearance": {"dims": ["searchAppearance"], "days": 90, "why": "rich results and other search appearances"},
    "dates": {"dims": ["date"], "days": 480, "agg": "byProperty", "why": "16-month trend: drops, seasonality, momentum"},
    "discover": {"dims": ["page"], "days": 90, "type": "discover", "agg": "byPage", "why": "Discover traffic by page"},
    "news": {"dims": ["page"], "days": 90, "type": "googleNews", "agg": "byPage", "why": "Google News traffic by page"},
    "image": {"dims": ["page", "query"], "days": 90, "type": "image", "max_rows": 25000, "why": "image search"},
    "video": {"dims": ["page", "query"], "days": 90, "type": "video", "max_rows": 25000, "why": "video search"},
    "hourly": {"dims": ["hour", "page"], "days": 10, "lag": 0, "state": "hourly_all", "max_rows": 25000,
               "why": "the last 10 days by hour: new and changed pages, update onset"},
}
# Data the API cannot reach: the user pastes or exports it from the Search Console UI (see the MCP hub's UI
# checklists), and it is ingested under these names.
UI_DATASETS = {
    "ui_crawl_stats": "Settings > Crawl stats: summary, host status, every breakdown table and its example URLs",
    "ui_page_indexing": "Indexing > Pages: the chart, every 'Why pages aren't indexed' reason with its count and examples",
    "ui_links": "Links: export of top linked pages (internal and external), top linking sites and anchor text",
    "ui_cwv": "Experience > Core Web Vitals: mobile and desktop URL groups with status",
    "ui_genai": "Performance > Search generative AI: the Pages tab export (impressions only)",
    "ui_manual_actions": "Security & manual actions: what each report says (paste the text)",
    "ui_enhancements": "Enhancements and Shopping reports: each report's valid/invalid counts and issues",
    "ui_robots": "Settings > robots.txt: hosts, fetch status, last fetched",
    "ui_branded": "Performance with the branded/non-branded filter: the two totals",
}
FRESH_DAYS = 7


def base() -> Path:
    return Path(os.environ.get("SEO_SITES_DIR") or (C.ROOT / "sites"))


def site_dir(slug: str) -> Path:
    return base() / slug / "gsc"


def path(slug: str, name: str) -> Path:
    return site_dir(slug) / f"{name}.json"


def save(slug: str, name: str, rows=None, meta: dict | None = None, items: dict | None = None) -> Path:
    rec = {"meta": {"dataset": name, "fetched_at": C.now_iso(), **(meta or {})}}
    if items is not None:
        rec["items"] = items
    else:
        rec["rows"] = rows or []
    p = path(slug, name)
    C.save_json(p, rec)
    return p


def load(slug: str, name: str) -> dict | None:
    return C.load_json(path(slug, name)) if slug else None


def rows(slug: str, name: str) -> list[dict]:
    return (load(slug, name) or {}).get("rows") or []


def age_days(rec: dict | None) -> float | None:
    try:
        t = datetime.fromisoformat((rec or {})["meta"]["fetched_at"])
        return (datetime.now(timezone.utc) - t).total_seconds() / 86400
    except Exception:
        return None


def fresh(slug: str, name: str, days: float = FRESH_DAYS) -> bool:
    a = age_days(load(slug, name))
    return a is not None and a <= days


def manifest(slug: str) -> list[dict]:
    out = []
    for name in list(DATASETS) + ["inspections", "sitemaps"] + list(UI_DATASETS):
        rec = load(slug, name)
        if rec:
            m = rec.get("meta") or {}
            out.append({"dataset": name, "source": m.get("source"), "age_days": round(age_days(rec) or 0, 1),
                        "rows": len(rec.get("rows") or rec.get("items") or []), "window": m.get("window"),
                        "truncated": m.get("truncated", False)})
    return out


def profile(slug: str) -> dict:
    p = C.ROOT / "clients" / f"{slug}.yaml"
    return (C.load_yaml(p) or {}) if p.exists() else {}


def property_for(slug: str, brief: dict | None = None) -> str:
    """The Search Console property: the brief's or profile's `gsc_property`, else the Domain property."""
    prof = profile(slug)
    explicit = (brief or {}).get("gsc_property") or prof.get("gsc_property")
    if explicit:
        return explicit
    domain = ((brief or {}).get("domain") or prof.get("domain") or slug).lower()
    return "sc-domain:" + domain.removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")


def slug_for(brief: dict) -> str | None:
    """The client slug whose store belongs to this brief: its batch/site inventory, else the profile with its domain."""
    inv = brief.get("site_inventory")
    if inv:
        return Path(inv).parent.name
    dom = (brief.get("domain") or "").lower().removeprefix("www.")
    if not dom:
        return None
    for p in sorted((C.ROOT / "clients").glob("*.yaml")):
        try:
            d = (C.load_yaml(p) or {}).get("domain", "").lower().removeprefix("www.")
        except Exception:
            continue
        if d == dom:
            return p.stem
    return None


def changelog(slug: str) -> list[dict]:
    return (C.load_json(site_dir(slug) / "changelog.json") or {}).get("entries", [])


def log_change(slug: str, entry: dict) -> None:
    """Dated change log (Google's own advice: annotate every change), the input of impact measurement."""
    p = site_dir(slug) / "changelog.json"
    with C.file_lock(p):
        d = C.load_json(p) or {"entries": []}
        entry = {"date": time.strftime("%Y-%m-%d"), **entry}
        d["entries"] = [e for e in d["entries"] if not (e.get("url") == entry.get("url") and e.get("date") == entry["date"]
                                                         and e.get("kind") == entry.get("kind"))] + [entry]
        C.save_json(p, d)
