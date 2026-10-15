"""Google autocomplete, free: the suggestions Google shows as people type (suggestqueries.google.com).

No key and no credits. It is not an official, documented API: Google can change or rate-limit it without notice, so
every failure returns no suggestions and the run carries on (the pipeline never retries around a block). A run makes
about seven calls, the same as a person typing. Results are cached for 3 days like the SERP.
"""
from __future__ import annotations

import asyncio
import json
import time

from . import common as C

URL = "https://suggestqueries.google.com/complete/search"
TTL = 3 * 86400


def _params(q: str, locale: str) -> dict:
    from .serper import locale_params
    gl, hl = locale_params(locale)
    return {"client": "firefox", "q": q, "hl": hl, "gl": gl}


async def _one(client, q: str, locale: str) -> list[str]:
    key = f"suggest|{q.lower()}|{locale.lower()}"
    cached = C.load_json(C._cache_path(key))
    if cached and time.time() - cached.get("_ts", 0) < TTL:
        return cached.get("suggestions", [])
    try:
        r = await client.get(URL, params=_params(q, locale))
        if r.status_code != 200:
            return []
        data = json.loads(r.content.decode(r.encoding or "utf-8", errors="replace"))
        out = [s for s in (data[1] if isinstance(data, list) and len(data) > 1 else []) if isinstance(s, str)]
    except Exception:  # unofficial endpoint: any failure means no suggestions this time
        return []
    C.cache_put(key, {"suggestions": out})
    return out


def many(queries: list[str], locale: str) -> dict[str, list[str]]:
    """{query: [suggestions]} for each query, fetched at the same time."""
    import httpx
    queries = list(dict.fromkeys(q for q in queries if q.strip()))
    if not queries:
        return {}

    async def go():
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=4.0),
                                     headers={"User-Agent": "Mozilla/5.0 (page-seo research)"}) as client:
            res = await asyncio.gather(*(_one(client, q, locale) for q in queries))
        return dict(zip(queries, res))
    return C.run_async(go())


def as_serper(suggestions: list[str]) -> dict:
    """The shape the pipeline already reads (Serper's autocomplete response)."""
    return {"suggestions": [{"value": s} for s in suggestions]}
