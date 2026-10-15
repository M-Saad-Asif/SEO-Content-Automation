"""Shared helpers: paths, YAML/JSON IO, cache, async fetching and HTML parsing."""
from __future__ import annotations

import asyncio
import hashlib
import html as htmlmod
import json
import os
import re
import sys
import threading
import time
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "cache"
RUNS = ROOT / "runs"
LEXICON_PATH = ROOT / "scripts" / "lexicon.yaml"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 asdivigitals-seo/2.0")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9",
           "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8"}

# Cache time-to-live per kind of resource, in seconds.
TTL = {"official": 7 * 86400, "product": 6 * 3600, "sitemap": 86400,
       "page": 86400, "status": 86400}

BLOCK_MARKERS = ("access denied", "just a moment", "cf-chl", "captcha",
                 "performing security verification", "request unsuccessful",
                 "attention required")


def utf8_stdout() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Parallel cache writers must not share a temporary filename.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(data, f, ensure_ascii=False, indent=1)
        except BaseException:
            f.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        with file_lock(path):
            for attempt in range(6):
                try:
                    tmp.replace(path)
                    break
                except PermissionError:
                    if attempt == 5:
                        raise
                    time.sleep(0.01 * 2 ** attempt)  # Windows readers and file scanners can briefly deny replacement
    finally:
        tmp.unlink(missing_ok=True)


class file_lock:
    """Cross-process lock (lock file created with O_EXCL, holding the owner's process id) for read-modify-write of
    shared files, so parallel `--add-fact` calls cannot overwrite each other.

    Re-entrant within a process: `add_fact` holds the fact-sheet lock while the writer pack it rebuilds takes the
    same lock again. A non-re-entrant lock made every added fact wait out the stale-lock timeout (30 s per fact, more
    than half of an hour-long run), and the inner release freed the outer lock early."""

    _held: dict = {}  # (process, lock path) -> recursion depth; protected by the per-path RLock
    _locks: dict = {}
    _guard = threading.RLock()

    def __init__(self, path: Path, timeout: float = 30.0):
        self.lock = Path(str(path) + ".lock")
        self.timeout = timeout
        self.key = (os.getpid(), os.path.normcase(str(self.lock.resolve())))
        with file_lock._guard:
            self.local = file_lock._locks.setdefault(self.key, threading.RLock())

    def _stale(self) -> bool:
        """The owner is gone (its process no longer runs), or the lock is far older than any write takes."""
        try:
            pid = int((self.lock.read_text(encoding="utf-8") or "0").strip() or 0)
        except (OSError, ValueError):
            return False
        if pid and pid != os.getpid():
            return not _pid_alive(pid)
        return False

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        if not self.local.acquire(timeout=self.timeout):
            raise TimeoutError(f"Timed out waiting for {self.lock}")
        try:
            if file_lock._held.get(self.key):
                file_lock._held[self.key] += 1
                return self
            while True:
                try:
                    fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    try:
                        os.write(fd, str(os.getpid()).encode())
                    finally:
                        os.close(fd)
                    file_lock._held[self.key] = 1
                    return self
                except FileExistsError:
                    if self._stale():
                        self.lock.unlink(missing_ok=True)
                        continue
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out waiting for {self.lock}; its live owner was not interrupted")
                    time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        except BaseException:
            self.local.release()
            raise

    def __exit__(self, *exc):
        try:
            depth = file_lock._held.get(self.key, 1) - 1
            if depth > 0:
                file_lock._held[self.key] = depth
                return
            file_lock._held.pop(self.key, None)
            self.lock.unlink(missing_ok=True)
        finally:
            self.local.release()


def _pid_alive(pid: int) -> bool:
    import os
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        h = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() != 87  # access denied is not proof the process is dead
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(h, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def lexicon() -> dict:
    return load_yaml(LEXICON_PATH)


# ---------------------------------------------------------------- text utils

def collapse(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def norm_for_match(s: str) -> str:
    """Normalise a string so that a fact value can be found in source text
    regardless of spacing, ×/x, curly quotes or case."""
    s = htmlmod.unescape(s or "").lower()
    s = s.replace("×", "x").replace(" ", " ")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\bcms\b", "cm", s)
    s = s.replace("|", "")  # `seo.py read` shows a table row as "Basic rate | 10.75%"; the page has no pipes
    return re.sub(r"\s+", "", s)


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "page"


# ---------------------------------------------------------------- HTML parse

class _Extract(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.skip = 0
        self.text: list[str] = []
        self.title = ""
        self._in_title = False
        self.heads: list[tuple[str, str]] = []
        self._head: list | None = None
        self.links: list[tuple[str, str]] = []
        self._a: list | None = None
        self.dl: list[tuple[str, str]] = []
        self._dt: list | None = None
        self._dd: list | None = None
        self._last_dt = ""
        self.canonical = ""
        self.meta_desc = ""
        self.main_depth = 0
        self.btn = 0        # an inline tooltip button keeps its label; the popup inside it is not page text
        self.btn_block = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self.skip += 1
            return
        if not self.skip:
            if tag == "button":
                self.btn += 1
            elif self.btn and tag in ("div", "p", "figure"):
                self.btn_block += 1
                return
        if tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2", "h3"):
            self._head = [tag, []]
        elif tag == "a" and a.get("href"):
            self._a = [urljoin(self.base, a["href"]), []]
        elif tag == "dt":
            self._dt = []
        elif tag == "dd":
            self._dd = []
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href", "")
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.meta_desc = a.get("content", "")
        if tag in ("p", "div", "li", "br", "tr", "section", "article", "h1", "h2", "h3", "h4", "dt", "dd", "td", "th"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip:
            if tag == "button" and self.btn:
                self.btn -= 1
                if not self.btn:
                    self.btn_block = 0
            elif self.btn and tag in ("div", "p", "figure"):
                self.btn_block = max(0, self.btn_block - 1)
                return
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3") and self._head:
            self.heads.append((self._head[0], collapse("".join(self._head[1]))))
            self._head = None
        elif tag == "a" and self._a:
            self.links.append((self._a[0], collapse("".join(self._a[1]))))
            self._a = None
        elif tag == "dt" and self._dt is not None:
            self._last_dt = collapse("".join(self._dt))
            self._dt = None
        elif tag == "dd" and self._dd is not None:
            self.dl.append((self._last_dt, collapse("".join(self._dd))))
            self._dd = None

    def handle_data(self, data):
        if self.skip or (self.btn and self.btn_block):
            return
        if self._in_title:
            self.title += data
        for buf in (self._head, self._a):
            if buf:
                buf[1].append(data)
        for buf in (self._dt, self._dd):
            if buf is not None:
                buf.append(data)
        self.text.append(data)


def parse_html(html: str, base: str) -> dict:
    p = _Extract(base)
    try:
        p.feed(html)
    except Exception:
        pass
    lines = [collapse(x) for x in "".join(p.text).split("\n")]
    text = "\n".join(x for x in lines if x)
    return {
        "title": collapse(p.title),
        "h1": [h for t, h in p.heads if t == "h1"],
        "h2": [h for t, h in p.heads if t == "h2"][:40],
        "links": p.links,
        "dl": p.dl,
        "canonical": p.canonical,
        "meta_description": collapse(p.meta_desc),
        "text": text,
    }


PARSER_VERSION = 3  # bump when _Doc or _Extract changes what it extracts, so cached parses are redone


def _fetch_key(parse: str, url: str) -> str:
    return f"{parse}{PARSER_VERSION if parse in ('doc', 'html') else ''}|{url}"


class _Doc(HTMLParser):
    """Main-content blocks in reading order: [tag, text]. Skips chrome
    (nav, header, footer, aside, forms); prefers <main>/<article> when present."""
    SKIP = {"script", "style", "noscript", "svg", "template", "nav", "header", "footer", "aside", "form",
            "select", "iframe"}
    # <button> is handled apart: an inline glossary tooltip ("Dry <button>bulbs<div>…definition…</div></button> are
    # planted…") keeps its own label in the sentence and drops the popup inside it
    BLOCK = {"h1", "h2", "h3", "h4", "p", "li", "td", "th", "blockquote", "dt", "dd", "figcaption"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.main = 0
        self.blocks: list[list] = []  # [tag, text, in_main]
        self.cur: list | None = None
        self.title, self._t = "", False
        self.tables = 0
        self.row: list | None = None  # cells of the open <tr>, emitted as one "tr"/"trh" block so rows keep their meaning
        self.row_head = True
        self.btn = 0        # open <button> elements
        self.btn_block = 0  # block elements open inside a button (a tooltip's popup)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
            return
        if self.skip:
            pass  # inside chrome: only SKIP tags are counted (their end tags are the only ones handled there)
        elif tag == "button":
            self.btn += 1
            return
        elif self.btn:
            if tag in self.BLOCK or tag in ("div", "figure"):
                self.btn_block += 1
            return
        if tag in ("main", "article"):
            self.main += 1
        if tag == "title":
            self._t = True
        if tag == "table":
            self.tables += 1
        if tag == "tr" and not self.skip:
            self._flush()
            self.row, self.row_head = [], True
        if tag in self.BLOCK and not self.skip:
            self._flush()
            self.cur = [tag, [], self.main > 0]
        elif tag == "br" and self.cur:
            self.cur[1].append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            # a closing tag inside skipped chrome must not end the paragraph around it
            return
        if tag == "button":
            self.btn = max(0, self.btn - 1)
            if not self.btn:
                self.btn_block = 0
            return
        if self.btn:
            # the popup's own </p> or </div> must not end the sentence the button sits in
            if tag in self.BLOCK or tag in ("div", "figure"):
                self.btn_block = max(0, self.btn_block - 1)
            return
        if tag in ("main", "article"):
            self.main = max(0, self.main - 1)
        if tag == "title":
            self._t = False
        if tag in self.BLOCK:
            self._flush()
        if tag == "tr" and self.row is not None:
            self._flush()
            if len(self.row) >= 2:
                self.blocks.append(["trh" if self.row_head else "tr", " | ".join(self.row), self.main > 0])
            self.row = None

    def _flush(self):
        if self.cur:
            t = collapse("".join(self.cur[1]))
            if t:
                self.blocks.append([self.cur[0], t, self.cur[2]])
                if self.row is not None and self.cur[0] in ("td", "th"):
                    self.row.append(t)
                    self.row_head &= self.cur[0] == "th"
        self.cur = None

    def handle_data(self, data):
        if self._t:
            self.title += data
        if self.skip or (self.btn and self.btn_block):
            return
        if self.cur is not None:
            self.cur[1].append(data)


def parse_doc(html: str) -> dict:
    p = _Doc()
    try:
        p.feed(html)
        p._flush()
    except Exception:
        pass
    blocks = p.blocks
    in_main = [b for b in blocks if b[2]]
    if in_main and sum(len(b[1]) for b in in_main) > 0.3 * sum(len(b[1]) for b in blocks):
        blocks = in_main
    blocks = [[t, x] for t, x, _ in blocks if len(x) > 1]
    words = sum(len(x.split()) for t, x in blocks if t in ("p", "li", "td", "blockquote", "dd"))
    return {"title": collapse(p.title), "blocks": blocks[:600], "words": words, "tables": p.tables,
            "text": "\n".join(x for _, x in blocks)}


# ---------------------------------------------------------------- cache

def _cache_path(key: str) -> Path:
    return CACHE / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")


def cache_get(key: str, kind: str, refresh: bool = False):
    if refresh:
        return None
    d = load_json(_cache_path(key))
    if not d:
        return None
    if time.time() - d.get("_ts", 0) > TTL.get(kind, 86400):
        return None
    return d


def cache_put(key: str, data: dict) -> dict:
    data = dict(data)
    data["_ts"] = time.time()
    save_json(_cache_path(key), data)
    return data


def captured_path(url: str) -> Path:
    return CACHE / "captured" / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".txt")


def captured_text(url: str) -> str | None:
    """Page text an agent read when the source blocks scripts. Expires like an
    official-source fetch, so a stale capture can never keep verifying a fact."""
    p = captured_path(url)
    if not p.exists() or time.time() - p.stat().st_mtime > TTL["official"]:
        return None
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------- fetching

def classify(status: int, text: str) -> str:
    low = (text or "")[:4000].lower()
    if status in (401, 403, 429) or (status == 503 and any(m in low for m in BLOCK_MARKERS)):
        return "blocked"
    if status == 200 and any(m in low for m in ("just a moment", "performing security verification",
                                                 "pardon our interruption", "are you a robot", "verify you are human",
                                                 "attention required", "access denied", "request unsuccessful")):
        return "blocked"
    if status == 200:
        return "ok"
    if status in (301, 302, 303, 307, 308):
        return "redirect"
    return "error"


async def _deadline(coro, seconds: float):
    """A wall-clock cap on one request. Without a running event loop (a coroutine driven by hand, as the offline
    tests do) there is nothing to time against, so the request simply runs."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return await coro
    return await asyncio.wait_for(coro, seconds)


async def fetch_many(reqs: list[dict], refresh: bool = False, concurrency: int = 12,
                     timeout: float = 12.0, attempts: int = 2) -> dict[str, dict]:
    """reqs: [{url, kind, parse: html|json|xml|status}] -> {url: result}.
    Results are cached by (parse, url). One retry on timeout or 5xx."""
    import httpx

    out: dict[str, dict] = {}
    todo = []
    for r in reqs:
        key = _fetch_key(r.get("parse", "html"), r["url"])
        c = cache_get(key, r.get("kind", "page"), refresh)
        if c:
            c["cached"] = True
            out[r["url"]] = c
        else:
            todo.append(r)
    if not todo:
        return out
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async def one(client, r):
        url, parse = r["url"], r.get("parse", "html")
        follow = parse != "status"
        res = None
        for attempt in range(1, max(attempts, 1) + 1):
            t0 = time.time()
            try:
                async with sem:
                    # httpx's timeout is per read: a server trickling bytes can hold a request far longer. One
                    # wall-clock deadline per request keeps a slow site from stalling the whole research wave.
                    if parse == "status":
                        resp = await _deadline(client.head(url, follow_redirects=False), timeout + 3)
                        if resp.status_code in (405, 403, 400, 404, 501):
                            resp = await _deadline(client.get(url, follow_redirects=False), timeout + 3)
                    else:
                        resp = await _deadline(client.get(url, follow_redirects=follow), timeout + 3)
                body = resp.text if parse != "status" else (resp.text[:4000] if resp.request.method == "GET" else "")
                st = resp.status_code
                res = {"url": url, "status": st, "final_url": str(resp.url),
                       "state": classify(st, body), "location": resp.headers.get("location", ""),
                       "fetched_at": now_iso(), "ms": int((time.time() - t0) * 1000)}
                if st == 200 and parse == "json":
                    try:
                        res["json"] = resp.json()
                    except Exception:
                        res["state"] = "error"
                elif st == 200 and parse == "xml":
                    res["locs"] = re.findall(r"<loc>\s*(.*?)\s*</loc>", body, re.S)
                    res["is_index"] = "<sitemapindex" in body[:2000]
                elif st == 200 and parse == "html":
                    res.update(parse_html(body, str(resp.url)))
                    if len(res.get("text", "")) < 400:
                        res["state"] = "needs_js"
                elif st == 200 and parse == "raw":  # markup itself (platform, lang, meta tags)
                    res["raw"] = body[:300000]
                elif st == 200 and parse == "doc":
                    if "html" not in resp.headers.get("content-type", "html"):
                        res["state"] = "not_html"
                    else:
                        res.update(parse_doc(body))
                        if res["words"] < 80:
                            res["state"] = "needs_js"
                if st >= 500 and attempt < attempts:
                    continue
                if st == 429 and attempt < attempts:
                    # the site asked us to slow down: wait as long as it says (capped), then ask once more
                    ra = resp.headers.get("retry-after", "")
                    await asyncio.sleep(min(float(ra) if ra.replace(".", "", 1).isdigit() else 3.0, 5.0))
                    continue
                break
            except Exception as e:  # timeout, DNS, TLS
                res = {"url": url, "status": 0, "state": "error", "error": type(e).__name__,
                       "fetched_at": now_iso(), "ms": int((time.time() - t0) * 1000)}
                if attempt < attempts:
                    continue
                break
        key = _fetch_key(parse, url)
        # a sitemap that timed out (huge, slow XML) is remembered for a day like a good one, so every run doesn't
        # wait out the same timeouts again; the page just has fewer known internal links
        timed_out_map = r.get("kind") == "sitemap" and res and res.get("error") in ("TimeoutError", "ReadTimeout")
        if res and res["state"] in ("ok", "redirect") or (parse == "status" and res and res["status"]) or timed_out_map:
            res = cache_put(key, res)
        out[url] = res

    async with httpx.AsyncClient(headers=HEADERS, timeout=httpx.Timeout(timeout, connect=6.0),
                                 limits=limits) as client:
        await asyncio.gather(*(one(client, r) for r in todo))
    return out


def run_async(coro):
    return asyncio.run(coro)


TRACKING = re.compile(r"([?&])(utm_\w+|bc|gclid|fbclid|srsltid|ref|cmpid|cid|mc_\w+)=[^&#]*&?")


def clean_url(url: str) -> str:
    """The page's own address: tracking parameters (some sites add them on redirect) are not part of it."""
    prev = None
    while prev != url:
        prev, url = url, TRACKING.sub(r"\1", url)
    return url.rstrip("?&")


def host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")
