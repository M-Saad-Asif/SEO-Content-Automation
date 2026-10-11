"""Data connectors: Google Search Console, DataForSEO, Microsoft Clarity, Reddit.

Each connector reads credentials from the environment or the repo's .env
(git-ignored), caches responses (respecting each API's limits), and returns
{"error": ...} or {"not_configured": ...} instead of raising, so a missing
connector never breaks a run.

The same data can come from an MCP server instead: the agent calls the MCP
tool and stores the result with `seo.py ingest <run> <connector> <file>`.
"""
from __future__ import annotations

import base64
import os
import time
from datetime import date, timedelta

from . import common as C

LOCATIONS = {"gb": "United Kingdom", "us": "United States", "ae": "United Arab Emirates", "au": "Australia",
             "ca": "Canada", "in": "India", "ie": "Ireland", "nz": "New Zealand", "pk": "Pakistan",
             "sa": "Saudi Arabia", "de": "Germany", "fr": "France", "es": "Spain", "it": "Italy", "nl": "Netherlands"}


def env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name].strip()
    p = C.ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def _cached(key: str, ttl: float):
    d = C.load_json(C._cache_path(key))
    return d if d and time.time() - d.get("_ts", 0) < ttl else None


# ---------------------------------------------------------------- Google Search Console

def gsc_configured() -> str | None:
    p = env("GSC_SERVICE_ACCOUNT_JSON")
    if not p:
        return "set GSC_SERVICE_ACCOUNT_JSON (path to a service-account key added as a user on the GSC property)"
    if not os.path.exists(p):
        return f"GSC_SERVICE_ACCOUNT_JSON points to a missing file: {p}"
    return None


def _gsc_token() -> str:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_file(
        env("GSC_SERVICE_ACCOUNT_JSON"), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    creds.refresh(Request())
    return creds.token


def gsc_query(site: str, body: dict, ttl: float = 86400) -> dict:
    """POST searchAnalytics/query. `site` is 'sc-domain:example.com' or 'https://example.com/'."""
    why = gsc_configured()
    if why:
        return {"not_configured": why}
    key = f"gsc|{site}|{sorted(body.items())}"
    hit = _cached(key, ttl)
    if hit:
        return hit
    import httpx
    from urllib.parse import quote
    try:
        tok = _gsc_token()
        r = httpx.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query",
                       headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=30)
        if r.status_code != 200:
            return {"error": f"GSC {r.status_code}: {r.text[:300]}"}
        return C.cache_put(key, r.json())
    except Exception as e:
        return {"error": f"GSC {type(e).__name__}: {e}"}


def gsc_window(days: int = 90) -> tuple[str, str]:
    end = date.today() - timedelta(days=3)  # GSC data lags about 2-3 days
    return (end - timedelta(days=days)).isoformat(), end.isoformat()


# ---------------------------------------------------------------- DataForSEO

def dfs_configured() -> str | None:
    if not (env("DATAFORSEO_USERNAME") and env("DATAFORSEO_PASSWORD")):
        return "set DATAFORSEO_USERNAME and DATAFORSEO_PASSWORD (same names the official DataForSEO MCP server uses)"
    return None


def dfs_post(path: str, tasks: list[dict], ttl: float = 7 * 86400) -> dict:
    """POST https://api.dataforseo.com/v3/<path> with a list of tasks. Paid per task; cached 7 days."""
    why = dfs_configured()
    if why:
        return {"not_configured": why}
    key = f"dfs|{path}|{tasks}"
    hit = _cached(key, ttl)
    if hit:
        hit["cached"] = True
        return hit
    import httpx
    auth = base64.b64encode(f"{env('DATAFORSEO_USERNAME')}:{env('DATAFORSEO_PASSWORD')}".encode()).decode()
    try:
        r = httpx.post(f"https://api.dataforseo.com/v3/{path}", json=tasks,
                       headers={"Authorization": f"Basic {auth}"}, timeout=60)
        d = r.json()
        if r.status_code != 200 or d.get("status_code") != 20000:
            return {"error": f"DataForSEO {r.status_code}/{d.get('status_code')}: {d.get('status_message')}"}
        return C.cache_put(key, d)
    except Exception as e:
        return {"error": f"DataForSEO {type(e).__name__}: {e}"}


def dfs_items(resp: dict) -> list[dict]:
    out = []
    for t in resp.get("tasks") or []:
        for r in t.get("result") or []:
            out += r.get("items") or []
    return out


def dfs_location(locale: str, override: str | None = None) -> str:
    if override:
        return override
    region = (locale or "en-GB").partition("-")[2].lower() or "us"
    return LOCATIONS.get(region, "United States")


# ---------------------------------------------------------------- Microsoft Clarity

def clarity_configured(token_env: str = "CLARITY_API_TOKEN") -> str | None:
    if not env(token_env):
        return f"set {token_env} (Clarity project > Settings > Data Export > Generate new API token)"
    return None


def clarity_insights(days: int = 3, dimensions: tuple[str, ...] = ("URL",), token_env: str = "CLARITY_API_TOKEN") -> dict:
    """Clarity Data Export API: live insights for the last 1-3 days. 10 requests/day/project,
    so results are cached for 20 hours."""
    why = clarity_configured(token_env)
    if why:
        return {"not_configured": why}
    key = f"clarity|{token_env}|{days}|{dimensions}"
    hit = _cached(key, 20 * 3600)
    if hit:
        return hit
    import httpx
    params = {"numOfDays": str(max(1, min(3, days)))}
    for i, d in enumerate(dimensions[:3], 1):
        params[f"dimension{i}"] = d
    try:
        r = httpx.get("https://www.clarity.ms/export-data/api/v1/project-live-insights", params=params,
                      headers={"Authorization": f"Bearer {env(token_env)}", "Content-Type": "application/json"},
                      timeout=30)
        if r.status_code != 200:
            return {"error": f"Clarity {r.status_code}: {r.text[:200]}"}
        return C.cache_put(key, {"metrics": r.json()})
    except Exception as e:
        return {"error": f"Clarity {type(e).__name__}: {e}"}


# ---------------------------------------------------------------- Reddit (official Data API)

def reddit_configured() -> str | None:
    if not (env("REDDIT_CLIENT_ID") and env("REDDIT_CLIENT_SECRET")):
        return ("set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT (a 'script' app at "
                "reddit.com/prefs/apps; commercial use needs Reddit's approval)")
    return None


def _reddit_token() -> str:
    import httpx
    hit = _cached("reddit|token", 3000)
    if hit:
        return hit["access_token"]
    r = httpx.post("https://www.reddit.com/api/v1/access_token", data={"grant_type": "client_credentials"},
                   auth=(env("REDDIT_CLIENT_ID"), env("REDDIT_CLIENT_SECRET")),
                   headers={"User-Agent": env("REDDIT_USER_AGENT") or "asdivigitals-seo/2.0"}, timeout=20)
    r.raise_for_status()
    return C.cache_put("reddit|token", r.json())["access_token"]


def reddit_get(path: str, params: dict, ttl: float = 3 * 86400) -> dict:
    why = reddit_configured()
    if why:
        return {"not_configured": why}
    key = f"reddit|{path}|{sorted(params.items())}"
    hit = _cached(key, ttl)
    if hit:
        return hit
    import httpx
    try:
        r = httpx.get(f"https://oauth.reddit.com{path}", params=params, timeout=20,
                      headers={"Authorization": f"Bearer {_reddit_token()}",
                               "User-Agent": env("REDDIT_USER_AGENT") or "asdivigitals-seo/2.0"})
        if r.status_code != 200:
            return {"error": f"Reddit {r.status_code}"}
        d = r.json()
        return C.cache_put(key, d if isinstance(d, dict) else {"listing": d})
    except Exception as e:
        return {"error": f"Reddit {type(e).__name__}: {e}"}
