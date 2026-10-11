"""Serper.dev client (Google SERP data through an official API account).

Reads SERPER_API_KEY from the environment or the repo's .env (git-ignored).
Responses are cached for 3 days per (endpoint, query, gl, hl), so re-runs and
pages in the same keyword cluster cost no extra credits.
"""
from __future__ import annotations

import asyncio
import os

from . import common as C

ENDPOINT = "https://google.serper.dev"
TTL_SERP = 3 * 86400


def api_key() -> str | None:
    if os.environ.get("SERPER_API_KEY"):
        return os.environ["SERPER_API_KEY"].strip()
    env = C.ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SERPER_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def locale_params(locale: str) -> tuple[str, str]:
    lang, _, region = (locale or "en-GB").partition("-")
    region = (region or "us").lower()
    # Google's country code for the United Kingdom is "uk", not the ISO "gb": with gl=gb Google returns organic
    # results but no People Also Ask and no related searches, so every UK page lost its question data
    return {"gb": "uk"}.get(region, region), lang.lower()


# Google's own country codes that differ from ISO, both ways: if one gives no question data, the other is tried
ALT_GL = {"uk": ["gb"], "gb": ["uk"]}


async def _call(client, kind: str, q: str, gl: str, hl: str, credits: list) -> dict:
    """One search, self-checked: a results page with rankings but no People Also Ask and no related searches is
    retried with the country's alternative Google code and with plain "en", and the question data of the first
    variant that has it is kept (the local rankings stay). A wrong or quirky code can never empty a run again."""
    d = await _call_once(client, kind, q, gl, hl, credits)
    if kind != "search" or d.get("error") or not d.get("organic") or d.get("peopleAlsoAsk") or d.get("relatedSearches"):
        return d
    for g, h in [(a, hl) for a in ALT_GL.get(gl, [])] + ([(gl, "en")] if hl != "en" else []):
        alt = await _call_once(client, kind, q, g, h, credits)
        if alt.get("peopleAlsoAsk") or alt.get("relatedSearches"):
            d = dict(d, peopleAlsoAsk=alt.get("peopleAlsoAsk", []), relatedSearches=alt.get("relatedSearches", []),
                     _questions_from=f"gl={g}, hl={h}")
            break
    return d


async def _call_once(client, kind: str, q: str, gl: str, hl: str, credits: list) -> dict:
    key = f"serper|{kind}|{q.lower()}|{gl}|{hl}"
    cached = C.load_json(C._cache_path(key))
    import time
    if cached and time.time() - cached.get("_ts", 0) < TTL_SERP:
        cached["cached"] = True
        return cached
    body = {"q": q, "gl": gl, "hl": hl}
    for attempt in (1, 2, 3):
        try:
            r = await client.post(f"{ENDPOINT}/{kind}", json=body)
            if r.status_code == 200:
                d = r.json()
                credits.append(d.get("credits", 1))
                return C.cache_put(key, d)
            if r.status_code in (401, 403):
                return {"error": f"Serper rejected the key ({r.status_code})"}
        except Exception as e:  # network blips (ConnectError) usually clear within a second or two
            if attempt == 3:
                return {"error": type(e).__name__}
        await asyncio.sleep(0.6 * attempt * attempt)
    return {"error": "Serper request failed"}


def batch(requests: list[tuple[str, str]], locale: str) -> tuple[dict, int]:
    """requests: [(kind, query)] with kind in search|autocomplete.
    Returns ({(kind, query): response}, credits_spent)."""
    import httpx
    key = api_key()
    if not key:
        return {r: {"error": "SERPER_API_KEY not set (put it in .env)"} for r in requests}, 0
    gl, hl = locale_params(locale)
    credits: list = []

    async def go():
        async with httpx.AsyncClient(headers={"X-API-KEY": key, "Content-Type": "application/json"},
                                     timeout=httpx.Timeout(20.0, connect=6.0)) as client:
            res = await asyncio.gather(*(_call(client, k, q, gl, hl, credits) for k, q in requests))
        return dict(zip(requests, res))
    out = C.run_async(go())
    return out, sum(credits)
