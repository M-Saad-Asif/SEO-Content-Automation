"""Spider (spider.cloud) client: rendered page content as markdown, and an organic-results search.

Used once per keyword by the research step: the organic results' content (JavaScript-rendered pages included) and,
when SERP_PROVIDER=spider, the results list itself. Agents doing their own follow-up research use their host's
search tools, never this API.

Reads SPIDER_API_KEY from the environment or the repo's git-ignored .env. Every call caps pages per site at 1
(Spider's default crawls whole sites) and results are cached for 3 days, so re-runs cost nothing.
"""
from __future__ import annotations

import asyncio
import os
import re
import time

from . import common as C

ENDPOINT = "https://api.spider.cloud"
TTL = 3 * 86400


def api_key() -> str | None:
    if os.environ.get("SPIDER_API_KEY"):
        return os.environ["SPIDER_API_KEY"].strip()
    env = C.ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SPIDER_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def provider() -> str:
    """Which service lists the organic results: "serper" (localised Google ranking) unless SERP_PROVIDER says
    otherwise or only Spider has a key."""
    want = os.environ.get("SERP_PROVIDER", "").strip().lower()
    if not want:
        env = C.ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("SERP_PROVIDER="):
                    want = line.split("=", 1)[1].strip().lower()
    if want in ("spider", "serper"):
        return want
    from . import serper
    return "serper" if serper.api_key() else ("spider" if api_key() else "serper")


def _headers() -> dict:
    return {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}


# ---------------------------------------------------------------- markdown -> blocks (the shape parse_doc returns)

def md_blocks(md: str) -> list[list[str]]:
    """Turn Spider's markdown into the pipeline's block list: [[tag, text]] with h1-h4, p, li, tr/trh."""
    blocks, para, header_seen = [], [], False
    pending_h = 0  # Spider often writes a heading as a bare "##" line with its text on the next line

    def flush():
        if para:
            text = re.sub(r"\s+", " ", " ".join(para)).strip()
            if len(text) > 1:
                blocks.append(["p", text])
            para.clear()
    for raw in (md or "").splitlines():
        line = raw.strip()
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)           # images
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)       # links -> anchor text
        line = re.sub(r"(\*\*|__|`)", "", line).strip()
        if re.search(r"</?script|</?style|\bfunction\s*\(|[{};]\s*$|\w+\s*=\s*(true|false|null|\d+);", line) or \
                re.match(r"^(image|photo|picture) (credit|courtesy|source)s?:", line, re.I) or \
                re.search(r"\b(we use cookies|accept (all )?cookies|cookie settings)\b", line, re.I):
            continue
        if not line:
            flush()
            header_seen = False
            continue
        if re.fullmatch(r"#{1,6}", line):
            flush()
            pending_h = len(line)
            continue
        if pending_h:
            blocks.append([f"h{min(4, pending_h)}", line.lstrip("# ").strip()])
            pending_h = 0
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            blocks.append([f"h{min(4, len(m.group(1)))}", m.group(2).strip()])
            continue
        if re.match(r"^\|?\s*:?-{2,}", line):                       # table separator row
            header_seen = True
            continue
        if line.startswith("|") and line.count("|") >= 2:
            flush()
            cells = [c.strip() for c in line.strip("|").split("|")]
            blocks.append(["tr" if header_seen or any(b[0] == "trh" for b in blocks[-3:]) else "trh", " | ".join(cells)])
            continue
        m = re.match(r"^([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            flush()
            blocks.append(["li", m.group(2).strip()])
            continue
        para.append(line)
    flush()
    return blocks


def tidy(blocks: list) -> list:
    """Entities and stray markdown Spider leaves in text ("8&ndash;10", "What&rsquo;s", "…watering ## Will they…"):
    applied to fresh and cached results alike, so old cache entries need no re-render."""
    import html
    out = []
    for t, x in blocks or []:
        x = html.unescape(x)
        m = re.search(r"\s(#{2,6})\s+(?=\S)", x) if t in ("p", "li") else None
        if m:
            before, after = x[:m.start()].strip(), x[m.end():].strip()
            if before:
                out.append([t, before])
            out.append([f"h{min(4, len(m.group(1)))}", after])
            continue
        out.append([t, x.lstrip("# ").strip() if t.startswith("h") else x])
    return out


# ---------------------------------------------------------------- calls

async def _scrape_one(client, url: str, sem, *, attempts: int = 2, refresh: bool = False,
                      request_timeout: float = 40) -> dict:
    key = f"spider|scrape2|{url}"  # scrape2: headings written as a bare "##" line are now kept
    cached = C.load_json(C._cache_path(key))
    if not refresh and cached and time.time() - cached.get("_ts", 0) < TTL:
        cached["cached"] = True
        cached["blocks"] = tidy(cached.get("blocks"))
        cached["title"] = next((x for t, x in cached["blocks"] if t == "h1"), cached.get("title", ""))
        return cached
    body = {"url": url, "limit": 1, "return_format": "markdown", "request": "smart", "request_timeout": request_timeout,
            "max_credits_per_page": 200}
    async with sem:
        for attempt in range(1, max(1, attempts) + 1):
            try:
                r = await client.post(f"{ENDPOINT}/scrape", json=body, headers=_headers())
                if r.status_code == 429 and attempt < attempts:
                    await asyncio.sleep(3)
                    continue
                d = r.json()
                item = d[0] if isinstance(d, list) and d else (d if isinstance(d, dict) else {})
                status = item.get("status") or r.status_code
                if r.status_code != 200 or str(status) != "200":
                    return {"url": url, "status": status, "state": "error", "via": "spider"}
                md = item.get("content") or ""
                blocks = tidy(md_blocks(md))
                words = sum(len(x.split()) for t, x in blocks if t in ("p", "li"))
                title = next((x for t, x in blocks if t == "h1"), "")
                res = {"url": url, "status": status, "final_url": item.get("url") or url,
                       "state": "ok" if md and words >= 80 else ("needs_js" if md else "error"), "blocks": blocks,
                       "words": words, "title": title, "text": " ".join(x for _, x in blocks),
                       "cost": (item.get("costs") or {}).get("total_cost", 0), "via": "spider",
                       "fetched_at": C.now_iso()}
                return C.cache_put(key, res) if res["state"] == "ok" else res
            except Exception as e:
                if attempt >= attempts:
                    return {"url": url, "status": 0, "state": "error", "error": type(e).__name__, "via": "spider"}
                await asyncio.sleep(1.5)
    return {"url": url, "status": 0, "state": "error", "via": "spider"}


async def _bounded_scrape(client, url, sem, timeout_s, attempts, refresh):
    try:
        return await asyncio.wait_for(
            _scrape_one(client, url, sem, attempts=attempts, refresh=refresh,
                        request_timeout=min(40, max(1, int(timeout_s - 2)))), timeout=timeout_s)
    except asyncio.TimeoutError:
        return {"url": url, "status": 0, "state": "timeout", "error": "render_budget_exceeded",
                "via": "spider", "budget_s": timeout_s}


def scrape_many(urls: list[str], concurrency: int = 5, *, timeout_s: float = 70,
                attempts: int = 2, refresh: bool = False) -> dict[str, dict]:
    """Rendered content, cached, with a per-URL elapsed budget including queueing and retries.

    Completed pages survive other pages timing out. Failed pages remain explicit research gaps.
    """
    if not urls or not api_key():
        return {}
    if timeout_s <= 0 or concurrency < 1 or attempts < 1:
        raise ValueError("Rendering timeout, concurrency and attempts must be positive")
    urls = list(dict.fromkeys(urls))
    import httpx

    async def go():
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(timeout=httpx.Timeout(70.0, connect=10.0)) as client:
            out = await asyncio.gather(*(_bounded_scrape(client, u, sem, timeout_s, attempts, refresh) for u in urls))
        return {u: r for u, r in zip(urls, out)}
    return C.run_async(go())


def search(query: str, locale: str, num: int = 10) -> dict:
    """Organic results in the same shape serp_intel reads from Serper: {"organic": [{position, link, title, snippet}]}.
    Spider's search returns organic results only (no People Also Ask, related searches or answer box)."""
    key = f"spider|search|{query.lower()}|{locale}"
    cached = C.load_json(C._cache_path(key))
    if cached and time.time() - cached.get("_ts", 0) < TTL:
        cached["cached"] = True
        return cached
    import httpx
    lang, _, region = (locale or "en-GB").partition("-")
    body = {"search": query, "num": num, "country": (region or "us").lower(), "language": lang.lower()}
    try:
        r = httpx.post(f"{ENDPOINT}/search", json=body, headers=_headers(), timeout=90)
        d = r.json()
    except Exception as e:
        return {"error": type(e).__name__}
    items = d.get("content") if isinstance(d, dict) else d
    organic = [{"position": i, "link": x.get("url"), "title": x.get("title") or "",
                "snippet": re.sub(r"&#x27;", "'", x.get("description") or "")}
               for i, x in enumerate(items or [], 1) if isinstance(x, dict) and x.get("url")]
    return C.cache_put(key, {"organic": organic, "via": "spider"})
