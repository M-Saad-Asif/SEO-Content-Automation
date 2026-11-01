"""Search Console API, read-only: Search Analytics (paged past 25k rows), URL Inspection, Sitemaps, Sites.

Credentials (either):
  GSC_SERVICE_ACCOUNT_JSON  path to a service-account key; add its email as a user on the property
  GSC_OAUTH_JSON            path to an OAuth "authorized user" file (refresh token) for a Google account with access
Scope is always `webmasters.readonly`: nothing here can change a property. Responses are cached (Search Analytics
for a day, inspections for a week), every call returns {"error": ...} or {"not_configured": ...} instead of raising.

API facts this module encodes (Google's API reference, Nov 2026): rowLimit max 25,000, page with startRow; filter
groups are AND only (OR goes inside one RE2 regex, max 4,096 chars); searchAppearance can't be combined with other
dimensions; Discover and Google News have no query dimension and no byProperty; Discover has no device dimension;
hourly data (`dataState: hourly_all`, dimension `hour`) covers about 10 days; data is kept 16 months.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
from urllib.parse import quote

from .. import common as C

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
BASE = "https://searchconsole.googleapis.com/webmasters/v3"
INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
MAX_ROWS = 25000
_TOKEN: dict = {}


def env(name: str) -> str | None:
    from ..connectors import env as _env
    return _env(name)


def configured() -> str | None:
    """None when the API route works on this machine, else what to set."""
    sa, oa = env("GSC_SERVICE_ACCOUNT_JSON"), env("GSC_OAUTH_JSON")
    if not sa and not oa:
        return ("set GSC_SERVICE_ACCOUNT_JSON (a service-account key added as a user on the property) or GSC_OAUTH_JSON "
                "(an authorized-user file), or use a Search Console MCP server and `seo.py gsc ingest`")
    path = sa or oa
    if not os.path.exists(path):
        return f"{'GSC_SERVICE_ACCOUNT_JSON' if sa else 'GSC_OAUTH_JSON'} points to a missing file: {path}"
    try:
        import google.auth  # noqa: F401
    except ImportError:
        return "the google-auth package is missing: pip install google-auth"
    return None


def _token() -> str:
    if _TOKEN.get("exp", 0) > time.time() + 60:
        return _TOKEN["tok"]
    from google.auth.transport.requests import Request
    sa = env("GSC_SERVICE_ACCOUNT_JSON")
    if sa:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(sa, scopes=[SCOPE])
    else:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(env("GSC_OAUTH_JSON"), scopes=[SCOPE])
    creds.refresh(Request())
    _TOKEN.update(tok=creds.token, exp=time.time() + 3000)
    return creds.token


def _cached(key: str, ttl: float):
    d = C.load_json(C._cache_path(key))
    return d if d and time.time() - d.get("_ts", 0) < ttl else None


def _call(method: str, url: str, body: dict | None = None, key: str | None = None, ttl: float = 86400) -> dict:
    why = configured()
    if why:
        return {"not_configured": why}
    if key:
        hit = _cached(key, ttl)
        if hit:
            return hit
    import httpx
    for attempt in range(3):
        try:
            r = httpx.request(method, url, headers={"Authorization": f"Bearer {_token()}"}, json=body, timeout=60)
        except Exception as e:
            if attempt == 2:
                return {"error": f"GSC {type(e).__name__}: {e}"}
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 502, 503) and attempt < 2:
            time.sleep(5 * (attempt + 1))  # short-term quota: Google says wait; a page+query pull is the costly kind
            continue
        if r.status_code != 200:
            return {"error": f"GSC {r.status_code}: {_explain(r.status_code, r.text)}"}
        data = r.json()
        return C.cache_put(key, data) if key else data
    return {"error": "GSC: gave up after retries"}


def _explain(code: int, text: str) -> str:
    hint = {403: "the API is disabled for the key's project, the scope is missing, or the account has no access to "
                 "this property (add the service account's email under Settings > Users and permissions)",
            404: "property not found: check the format (sc-domain:example.com, or https://www.example.com/ with the "
                 "trailing slash)",
            400: "a parameter Google rejects (dimension combination, regex, dates)"}.get(code, "")
    return f"{text[:300]}" + (f" — {hint}" if hint else "")


def window(days: int, lag: int = 3, back: int = 0) -> tuple[str, str]:
    """[start, end] of `days` days ending `lag` days ago (final data lags 2-3 days), shifted `back` days earlier."""
    end = date.today() - timedelta(days=lag + back)
    return (end - timedelta(days=days - 1)).isoformat(), end.isoformat()


def query(site: str, body: dict, ttl: float = 86400) -> dict:
    """One searchAnalytics.query call (one page of rows)."""
    key = "gsc|q|" + site + "|" + json.dumps(body, sort_keys=True)
    return _call("POST", f"{BASE}/sites/{quote(site, safe='')}/searchAnalytics/query", body, key, ttl)


def query_all(site: str, body: dict, max_rows: int = 100000, ttl: float = 86400) -> dict:
    """Every row up to `max_rows`, paged with startRow. Returns {"rows": [...], "truncated": bool, "metadata": ...}
    or {"error"/"not_configured": ...}. The API itself returns top rows only, never every row."""
    rows: list = []
    meta = None
    start = 0
    while start < max_rows:
        page = dict(body, rowLimit=min(MAX_ROWS, max_rows - start), startRow=start)
        r = query(site, page, ttl)
        if r.get("error") or r.get("not_configured"):
            return r if not rows else {"rows": rows, "truncated": True, "metadata": meta, "partial_error": r}
        got = r.get("rows") or []
        meta = meta or r.get("metadata")
        rows += got
        if len(got) < page["rowLimit"]:
            return {"rows": rows, "truncated": False, "metadata": meta, "responseAggregationType": r.get("responseAggregationType")}
        start += len(got)
    return {"rows": rows, "truncated": True, "metadata": meta}


def rows(resp: dict, dims: list[str]) -> list[dict]:
    """API rows ({keys: [...], clicks, ...}) as flat dicts keyed by dimension name."""
    out = []
    for r in resp.get("rows") or []:
        rec = dict(zip(dims, r.get("keys") or []))
        rec.update(clicks=r.get("clicks", 0), impressions=r.get("impressions", 0), ctr=r.get("ctr", 0.0),
                   position=round(r.get("position", 0.0), 2))
        out.append(rec)
    return out


def inspect(site: str, url: str, lang: str = "en", ttl: float = 7 * 86400) -> dict:
    """urlInspection.index.inspect: the indexed view only (no live test, rendered HTML or Request indexing).
    Quota: 2,000 a day and 600 a minute per property."""
    key = f"gsc|inspect|{site}|{url}"
    r = _call("POST", INSPECT, {"inspectionUrl": url, "siteUrl": site, "languageCode": lang}, key, ttl)
    return r.get("inspectionResult", r) if isinstance(r, dict) else r


def sitemaps(site: str) -> dict:
    return _call("GET", f"{BASE}/sites/{quote(site, safe='')}/sitemaps", key=f"gsc|sitemaps|{site}", ttl=86400)


def sites() -> dict:
    return _call("GET", f"{BASE}/sites", key="gsc|sites", ttl=3600)
