"""Reusable website context, source-backed page inventory and keyword-to-page matching."""
from __future__ import annotations

import re
from collections import Counter, deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import yaml

from . import common as C
from . import pagetype

CONTEXT_NAMES = ("seo-context.yaml", ".seo-context.yaml")
ASSET = re.compile(r"\.(pdf|xml|txt|jpg|jpeg|png|gif|svg|webp|mp4|zip|css|js|woff2?)(?:$|\?)", re.I)
UTILITY = re.compile(r"/(wp-admin|wp-json|cart|checkout|login|logout|search|feed)(/|$)", re.I)


def website_url(value: str) -> str:
    value = value.strip()
    parsed = urlparse(value if "://" in value else "https://" + value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Give a website domain or an HTTP(S) page URL without credentials")
    return C.clean_url(urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", parsed.query, "")))


def client_for_website(value: str, create: bool = False) -> tuple[str, dict]:
    url = website_url(value)
    host = C.host(url)
    for path in sorted((C.ROOT / "clients").glob("*.yaml")):
        profile = C.load_yaml(path) or {}
        if C.host("https://" + profile.get("domain", "").removeprefix("https://").removeprefix("http://")) == host:
            return path.stem, profile
    slug = C.slugify(host)  # full host avoids example.com/example.org sharing a profile
    if not create:
        return slug, {}
    from .onboard import onboard
    onboard(slug, host)
    return slug, C.load_yaml(C.ROOT / "clients" / f"{slug}.yaml") or {}


def resolve_client() -> tuple[str, dict, str] | None:
    """Explicit project context wins. Only a single saved profile is an implicit default."""
    locations = [Path.cwd(), C.ROOT]
    for directory in dict.fromkeys(locations):
        for name in CONTEXT_NAMES:
            path = directory / name
            if not path.exists():
                continue
            data = C.load_yaml(path) or {}
            slug = data.get("client_slug") or data.get("client")
            profile_path = C.ROOT / "clients" / f"{slug}.yaml" if slug else None
            if profile_path and profile_path.exists():
                profile = C.load_yaml(profile_path) or {}
                if data.get("domain") and C.host(website_url(data["domain"])) != C.host(website_url(profile["domain"])):
                    raise ValueError(f"Website and client disagree in {path}; correct the context file")
                return str(slug), profile, str(path)
            if data.get("domain") or data.get("website"):
                slug, profile = client_for_website(data.get("domain") or data["website"], create=True)
                return slug, profile, str(path)
            raise ValueError(f"{path} needs client_slug or domain; do not guess another website")
    profiles = sorted((C.ROOT / "clients").glob("*.yaml"))
    if len(profiles) == 1:
        return profiles[0].stem, C.load_yaml(profiles[0]) or {}, "the only saved client profile"
    return None


def bind_client(slug: str, directory: Path | None = None) -> Path:
    profile = C.load_yaml(C.ROOT / "clients" / f"{slug}.yaml") or {}
    target = (directory or C.ROOT) / CONTEXT_NAMES[0]
    target.write_text(yaml.safe_dump({"client_slug": slug, "domain": profile["domain"],
                                    "inventory": f"sites/{slug}/inventory.json"}, sort_keys=False), encoding="utf-8")
    return target


def inventory_path(slug: str) -> Path:
    return C.ROOT / "sites" / slug / "inventory.json"


def inventory(slug: str) -> dict:
    return C.load_json(inventory_path(slug)) or {}


def _content_url(url: str, home: str) -> str | None:
    try:
        absolute = website_url(urljoin(home, url))
    except ValueError:
        return None
    parsed = urlparse(absolute)
    if C.host(absolute) != C.host(home) or parsed.query or ASSET.search(parsed.path) or UTILITY.search(parsed.path):
        return None
    return absolute


def discover(slug: str, max_pages: int = 250, refresh: bool = False, selected: list[str] | None = None) -> dict:
    inventory_path(slug).parent.mkdir(parents=True, exist_ok=True)
    with C.file_lock(inventory_path(slug), timeout=120):
        return _discover(slug, max_pages, refresh, selected)


def _discover(slug: str, max_pages: int, refresh: bool, selected: list[str] | None) -> dict:
    """Read same-site content pages, sitemap indexes and internal links. Bounded and resumable.

    A page cap or unreadable URL is reported, never presented as a complete successful site read.
    No article research or writing is started here.
    """
    if not 1 <= max_pages <= 5000:
        raise ValueError("max_pages must be between 1 and 5000; repeat discovery to resume a larger site")
    profile = C.load_yaml(C.ROOT / "clients" / f"{slug}.yaml") or {}
    base = website_url(profile["domain"])
    home = urlunparse((*urlparse(base)[:2], "/", "", "", ""))
    prior = {} if refresh else inventory(slug)
    initial = C.run_async(C.fetch_many([
        {"url": home, "parse": "raw", "kind": "page"},
        {"url": urljoin(home, "robots.txt"), "parse": "raw", "kind": "page"},
        {"url": urljoin(home, "sitemap.xml"), "parse": "xml", "kind": "sitemap"},
    ], refresh, timeout=10, attempts=1))
    robots_result = initial.get(urljoin(home, "robots.txt")) or {}
    robots_text = robots_result.get("raw") or ""
    robots = RobotFileParser()
    robots.parse(robots_text.splitlines())
    sitemap_queue = deque(prior.get("sitemap_frontier") or [urljoin(home, "sitemap.xml")])
    declared_maps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text)
    sitemap_queue.extend(declared_maps)
    required_maps = set(prior.get("sitemap_frontier") or []) | set(declared_maps)
    sitemap_queue.extend(urljoin(home, p) for p in ("sitemap_index.xml", "wp-sitemap.xml"))
    mapped = set(prior.get("sitemaps_read") or [])
    seen_maps = set(mapped)
    discovered = list(prior.get("discovered_urls") or []) + [home]
    gaps, failed_maps, recovered = [], [], set()
    maps_read = 0
    while sitemap_queue and maps_read < 50:
        wave = []
        while sitemap_queue and len(wave) < min(10, 50 - maps_read):
            url = sitemap_queue.popleft()
            if C.host(url) == C.host(home) and url not in seen_maps:
                seen_maps.add(url)
                wave.append(url)
        if not wave:
            continue
        missing = [u for u in wave if u not in initial]
        responses = {**initial, **(C.run_async(C.fetch_many(
            [{"url": u, "parse": "xml", "kind": "sitemap"} for u in missing], refresh, timeout=10, attempts=1)) if missing else {})}
        maps_read += len(wave)
        for url in wave:
            result = responses.get(url) or {}
            if result.get("status") != 200 or result.get("state", "ok") != "ok" or C.host(result.get("final_url") or url) != C.host(home):
                if url in required_maps or result.get("status") not in (404, 410):
                    failed_maps.append(url)
                    gaps.append({"url": url, "reason": "sitemap_unreadable", "status": result.get("status")})
                continue  # absent alternate endpoints are normal; failed discovered maps must remain retryable
            mapped.add(url)
            recovered.add(url)
            if result.get("is_index"):
                children = [u for u in result.get("locs", []) if C.host(u) == C.host(home)]
                required_maps.update(children)
                sitemap_queue.extend(children)
            else:
                discovered.extend(u for u in result.get("locs", []) if _content_url(u, home))
    pages = {p["url"]: p for p in prior.get("pages", [])}
    queue = deque(dict.fromkeys(([home] + (selected or []) + list(prior.get("frontier") or []) + discovered)))
    queued = set(queue)
    attempted = {url for url, page in pages.items() if page.get("words", 0) >= 80}
    count = 0
    home_html = (initial.get(home) or {}).get("raw") or ""
    home_doc = C.parse_doc(home_html)
    home_commerce = pagetype.commerce(home_doc.get("text", ""), home, home_doc.get("title", ""))
    while queue and count < max_pages:
        wave = []
        while queue and len(wave) < min(12, max_pages - count):
            url = _content_url(queue.popleft(), home)
            if not url or url in attempted:
                continue
            attempted.add(url)
            if robots_text and not robots.can_fetch("*", url):
                gaps.append({"url": url, "reason": "robots_disallowed"})
                continue
            wave.append(url)
        if not wave:
            continue
        missing = [u for u in wave if u not in initial]
        raw_pages = {**initial, **(C.run_async(C.fetch_many(
            [{"url": u, "parse": "raw", "kind": "page"} for u in missing], refresh, timeout=10, attempts=1)) if missing else {})}
        from . import spider
        thin = [u for u in wave if (raw_pages.get(u) or {}).get("status") == 200
                and (raw_pages.get(u) or {}).get("state") == "ok"
                and C.host((raw_pages.get(u) or {}).get("final_url") or u) == C.host(home)
                and C.parse_doc((raw_pages.get(u) or {}).get("raw") or "").get("words", 0) < 80]
        rendered = spider.scrape_many(thin, timeout_s=35, attempts=1, refresh=refresh) if thin and spider.api_key() else {}
        count += len(wave)
        for url in wave:
            result = raw_pages.get(url) or {}
            if result.get("status") != 200 or result.get("state") != "ok" or C.host(result.get("final_url") or url) != C.host(home):
                gaps.append({"url": url, "reason": result.get("state") or "unreadable", "status": result.get("status")})
                continue
            raw = result.get("raw") or ""
            doc, html = C.parse_doc(raw), C.parse_html(raw, result.get("final_url") or url)
            render = rendered.get(url) or {}
            if render.get("state") == "ok" and C.host(render.get("final_url") or url) == C.host(home):
                doc = render
            if url == home:
                home_doc = doc
                home_commerce = pagetype.commerce(doc.get("text", ""), home, doc.get("title", ""))
            C.cache_put(C._fetch_key("doc", url), {**result, **doc, "state": "ok" if doc.get("words", 0) >= 80 else "needs_js"})
            C.cache_put(C._fetch_key("html", url), {**result, **html})
            h1 = next((x for t, x in doc.get("blocks", []) if t == "h1"), "")
            ptype, evidence = pagetype.classify(url, doc, raw, home_commerce)
            pages[url] = {"url": url, "final_url": result.get("final_url") or url, "title": doc.get("title") or html.get("title"),
                          "exists": doc.get("words", 0) >= 80, "status": 200,
                          "read_state": "ok" if doc.get("words", 0) >= 80 else "needs_js",
                          "h1": h1, "target_query": pagetype.keyword_from(h1, doc.get("title", ""), url),
                          "page_type": ptype, "type_evidence": evidence, "words": doc.get("words", 0),
                          "headings": [[t, x] for t, x in doc.get("blocks", []) if t.startswith("h")],
                          "source_excerpt": (doc.get("text") or html.get("text") or "")[:2400], "fetched_at": C.now_iso()}
            if doc.get("words", 0) < 80:
                gaps.append({"url": url, "reason": "thin_or_js_page", "status": 200})
            else:
                recovered.add(url)
            for href, _ in html.get("links", []):
                linked = _content_url(href, home)
                if linked and linked not in queued and linked not in attempted:
                    queue.append(linked)
                    queued.add(linked)
                    discovered.append(linked)
    unread = [g["url"] for g in (prior.get("gaps") or []) + gaps
              if g["reason"] not in ("robots_disallowed", "sitemap_unreadable") and g["url"] not in recovered]
    frontier = list(dict.fromkeys(u for u in list(queue) + unread if _content_url(u, home)
                                  and (u not in pages or pages[u].get("words", 0) < 80)))
    result = {"schema_version": 1, "client_slug": slug, "client": profile.get("client"), "domain": profile["domain"],
              "generated_at": C.now_iso(), "source_context": {"home_url": home, "home_title": home_doc.get("title"),
                  "published_purpose_excerpt": home_doc.get("text", "")[:2000],
                  "note": "Published site context, not independent proof of its capabilities or outcomes"},
              "pages": list(pages.values()), "page_types": dict(Counter(p["page_type"] for p in pages.values())),
              "discovered_urls": list(dict.fromkeys(discovered)), "frontier": frontier,
              "sitemaps_read": sorted(mapped), "sitemap_frontier": list(dict.fromkeys(list(sitemap_queue) + failed_maps)),
              "gaps": list({(g["url"], g["reason"]): g for g in (prior.get("gaps") or []) + gaps if g["url"] not in recovered}.values()),
              "discovery_complete": not frontier and not sitemap_queue and not failed_maps, "pages_read_this_pass": count}
    C.save_json(inventory_path(slug), result)
    return result


def keyword_matches(query: str, data: dict) -> list[tuple[float, dict]]:
    from .nlp import tokens
    wanted = set(tokens(query)) - {"the", "and", "for", "a", "in", "of"}
    ranked = []
    for page in data.get("pages", []):
        terms = set(tokens(page.get("target_query") or page.get("h1") or "")) - {"the", "and", "for", "a", "in", "of"}
        score = len(wanted & terms) / max(1, len(wanted | terms))
        if score >= 0.75:
            ranked.append((score, page))
    ranked.sort(key=lambda x: -x[0])
    return ranked


def match_keyword(query: str, data: dict) -> dict | None:
    ranked = keyword_matches(query, data)
    if not ranked or len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.15:
        return None
    return ranked[0][1]
