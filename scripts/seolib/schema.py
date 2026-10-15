"""JSON-LD for the finished page (Koray's semantic rules: structured data that names the page's central entity and the
entities it covers). Built by script from final.md, the brief and the knowledge graph when the run completes, so it
costs no model call. Written to schema.json; paste it into the page's <script type="application/ld+json">."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from . import common as C

COMMERCIAL = {"service", "location", "home", "category", "company"}


def _front(md: str) -> dict:
    if not md.startswith("---\n"):
        return {}
    try:
        return yaml.safe_load(md.split("\n---", 1)[0][4:]) or {}
    except yaml.YAMLError:
        return {}


def build(rd: Path) -> dict | None:
    final = rd / "final.md"
    if not final.exists():
        return None
    md = final.read_text(encoding="utf-8")
    fm = _front(md)
    brief = (C.load_json(rd / "fact_sheet.json") or {}).get("brief") or {}
    h1 = (re.search(r"(?m)^# (.+)$", md) or [None, fm.get("title") or ""])[1].strip()
    domain = (brief.get("domain") or "").strip().rstrip("/")
    site = domain if domain.startswith("http") else f"https://{domain}" if domain else ""
    url = brief.get("page_url") or ""
    org = {"@type": "Organization", "@id": f"{site}/#organization", "name": brief.get("client") or domain, "url": site}
    kg = C.load_json(rd / "research" / "semantic_graph.json") or {}
    ents = (kg.get("graph") or {}).get("entities") or []
    central = next((e.get("name") for e in ents if e.get("type") == "central"), None) or brief.get("target_query") or h1
    must = [e if isinstance(e, str) else e.get("entity", "") for e in kg.get("must_cover_entities") or []]
    body = md.lower()
    # only entities the page itself uses (drops another market's words, e.g. "faucet" on an en-GB page)
    mentions = [m for m in dict.fromkeys(must) if m and m.lower() != str(central).lower()
                and re.search(r"\b" + re.escape(m.lower()) + r"\b", body)][:12]
    page_type = (brief.get("page_type") or "guide").lower()
    node = {"@type": "Service" if page_type in ("service", "location") else
            "WebPage" if page_type in COMMERCIAL or page_type == "product" else "Article",
            "name" if page_type in ("service", "location") else "headline": h1,
            "description": fm.get("meta_description") or "",
            "about": {"@type": "Thing", "name": central},
            "mentions": [{"@type": "Thing", "name": m} for m in mentions],
            "inLanguage": brief.get("locale") or "en"}
    if url:
        node["url"] = url
        node["@id"] = f"{url}#main"
    if node["@type"] == "Service":
        node["provider"] = {"@id": org["@id"]}
        if brief.get("market"):
            node["areaServed"] = brief["market"]
    else:
        node["publisher"] = {"@id": org["@id"]}
        if fm.get("updated"):
            node["dateModified"] = str(fm["updated"])
        if fm.get("author"):
            node["author"] = {"@type": "Person", "name": str(fm["author"]).split(",")[0].strip()}
    if not node["mentions"]:
        del node["mentions"]
    data = {"@context": "https://schema.org", "@graph": [org, node]}
    (rd / "schema.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
