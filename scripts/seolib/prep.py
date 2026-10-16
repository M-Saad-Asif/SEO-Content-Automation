"""Step 1 (prep) and step 2 helper (--add-fact).

Builds runs/<date>-<slug>/fact_sheet.json and link_map.json from the brief:
the live page, the sitemap, Shopify product JSON + product pages, and the
official sources listed in the brief. Everything is fetched in parallel and
cached. Facts are verified by finding the normalised value in the source text.
"""
from __future__ import annotations

import html as htmlmod
import importlib.util
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

from . import common as C
from .clientpages import clean_internal, client_passages, related, relevant_products, site_says
from .timing import mark

REQUIRED = ["client", "domain", "locale", "page_url", "page_type", "target_query",
            "search_intent", "word_range", "mode"]
from .pagetype import TYPES

PAGE_TYPES = set(TYPES) | {"hub", "spoke", "product-guide"}
USABLE = {"verified", "captured", "operator"}


# ---------------------------------------------------------------- brief

def load_brief(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_absolute():
        names = [p] if p.suffix in (".yaml", ".yml") else [p, p.with_suffix(".yaml")]
        cands = [base / n for n in names for base in (Path.cwd(), C.ROOT, C.ROOT / "briefs")]
        p = next((c for c in cands if c.is_file()), None)
        if p is None:
            raise SystemExit(f"BRIEF NOT FOUND: {path} (looked in the current folder, {C.ROOT} and {C.ROOT / 'briefs'})")
    b = C.load_yaml(p)
    # The client profile is the source of truth for client-level settings (bans, voice, synonyms, reader nouns):
    # anything the brief doesn't set itself comes from the current profile, so profile edits reach old briefs.
    # a brief may carry its client's profile beside it (fixtures do, so they run in a fresh clone with no clients/)
    beside = [p.parent / "client.yaml"] if (p.parent / "client.yaml").is_file() else []
    for prof_path in beside + sorted((C.ROOT / "clients").glob("*.yaml")):
        prof = C.load_yaml(prof_path) or {}
        if prof.get("client") and prof.get("client") == b.get("client"):
            for k, v in prof.items():
                if k in ("default_product_sources", "blog_path"):
                    continue
                if k in ("banned_phrases", "banned_claims", "known_failures", "reader_nouns", "proper_nouns",
                         "internal_codes") and isinstance(v, list) and isinstance(b.get(k), list):
                    b[k] = list(dict.fromkeys(b[k] + v))  # bans add up: a page can tighten, never loosen
                elif k == "synonyms" and isinstance(v, dict) and isinstance(b.get(k), dict):
                    b[k] = {**v, **b[k]}
                else:
                    b.setdefault(k, v)
            break
    errs = [f"missing field: {k}" for k in REQUIRED if b.get(k) in (None, "", [])]
    if b.get("page_type") and b["page_type"] not in PAGE_TYPES:
        errs.append(f"page_type must be one of {sorted(PAGE_TYPES)}")
    wr = b.get("word_range")
    if wr and (not isinstance(wr, list) or len(wr) != 2 or wr[0] >= wr[1]):
        errs.append("word_range must be [min, max]")
    if b.get("mode") not in (None, "auto", "interactive"):
        errs.append("mode must be auto or interactive")
    if errs:
        raise SystemExit("BRIEF INVALID (" + str(p) + "):\n  " + "\n  ".join(errs))
    b["_path"] = str(p)
    # Vertical checks bring their own official sources (e.g. airline limits for luggage_fit).
    for chk in b.get("vertical_checks") or []:
        pack_path = C.ROOT / "checks" / f"{chk}.sources.yaml"
        if pack_path.exists():
            pack = C.load_yaml(pack_path)
            have = {(s if isinstance(s, str) else s.get("url")) for s in b.get("official_sources") or []}
            b["official_sources"] = list(b.get("official_sources") or []) +                 [s for s in pack.get("official_sources", []) if s["url"] not in have]
            b["required_facts"] = list(dict.fromkeys(list(b.get("required_facts") or []) + pack.get("required_facts", [])))
    b.setdefault("slug", p.stem)
    b.setdefault("approved_claims", [])
    b.setdefault("banned_claims", [])
    b.setdefault("client_facts", [])
    b.setdefault("official_sources", [])
    b.setdefault("vertical_checks", [])
    b.setdefault("hardcode_prices", False)
    return b


REUSE_DAYS = 7


def client_site_search(rd: Path, brief: dict) -> int:
    """Google's own list of the client's pages on this topic ("site:client query"): the pages its sitemaps miss
    (Toolstation's tap guides are in no sitemap). Runs after the research waves, only when the run still has a paid
    search left (the main search and the authorities come first). Returns the pages added."""
    from . import serper
    s = serper.spent()
    if s["cap"] is not None and s["spent"] >= s["cap"]:
        return 0
    domain = re.sub(r"^https?://", "", brief.get("domain") or "").strip("/")
    page_url = brief.get("page_url") or ""
    lm = C.load_json(rd / "link_map.json") or {}
    if not domain or not lm:
        return 0
    try:
        res, _cr = serper.batch([("search", f"site:{domain} {brief['target_query']}")], brief.get("locale") or "en")
    except Exception:
        return 0
    found = [re.sub(r"[?&](srsltid|utm_\w+|gclid|fbclid)=[^&#]*", "", o.get("link", "").split("#")[0]).rstrip("?&")
             for r in res.values() for o in r.get("organic", [])[:6] if o.get("link")]
    found = [u for u in clean_internal(found, brief.get("locale") or "en")
             if u.rstrip("/") != page_url.rstrip("/") and C.host(u) == C.host(f"https://{domain}")]
    if not found:
        return 0
    from .clientpages import related as rel_fn
    cls = rel_fn(found, brief["target_query"], brief.get("synonyms"), exclude=page_url)
    rel = lm.setdefault("client_related", {"same_topic": [], "guides": [], "commercial": []})
    added = 0
    for k in ("same_topic", "guides", "commercial"):
        for u in cls.get(k, []):
            if u not in rel.setdefault(k, []):
                rel[k].append(u)
                added += 1
    for u in found[:4]:  # Google ranks them for the query: guides the URL words alone didn't match
        if u not in rel["guides"] and u not in rel["same_topic"] and u not in rel["commercial"]:
            rel["guides"].append(u)
            added += 1
    lm["client_candidates"] = list(dict.fromkeys((lm.get("client_candidates") or []) + found))
    lm["internal"] = list(dict.fromkeys((lm.get("internal") or []) + found))
    C.save_json(rd / "link_map.json", lm)
    return added


def run_dir(brief: dict, day: str | None = None) -> Path:
    """Today's run, unless a run for this page started within the last REUSE_DAYS: a run that crosses midnight
    (or is picked up again tomorrow) keeps its outline, draft and verified facts instead of starting over."""
    if day:
        return C.RUNS / f"{day}-{brief['slug']}"
    today = date.today()
    for p in sorted(C.RUNS.glob(f"*-{brief['slug']}"), reverse=True):
        try:
            started = date.fromisoformat(p.name[:10])
        except ValueError:
            continue
        if p.name[11:] == brief["slug"] and 0 <= (today - started).days < REUSE_DAYS:
            return p
    return C.RUNS / f"{today.isoformat()}-{brief['slug']}"


def latest_run(brief: dict) -> Path:
    today = run_dir(brief)
    if today.exists():
        return today
    cands = sorted(C.RUNS.glob(f"*-{brief['slug']}"))
    if not cands:
        raise SystemExit("No run found for this brief; run `seo.py prep` first.")
    return cands[-1]


# ---------------------------------------------------------------- dimensions

def parse_dims(raw: str) -> dict | None:
    """'45 cm x 33 cm x 20 cm (Length x Height x Width)' -> cm [45,33,20].
    Irregular shapes like '30 (bottom) / 50 (top) x 20 x 38 cm' use the max."""
    if not raw:
        return None
    s = htmlmod.unescape(raw).replace("×", "x").replace("X", "x")
    labels = None
    m = re.search(r"\(([A-Za-z ]+x[A-Za-z x]+)\)", s)
    if m:
        labels = C.collapse(m.group(1))
    s2 = re.sub(r"\([^)]*\)", " ", s)
    m = re.search(r"((?:\d+(?:\.\d+)?\s*(?:cm)?\s*(?:/\s*\d+(?:\.\d+)?\s*(?:cm)?\s*)?)"
                  r"(?:x\s*\d+(?:\.\d+)?\s*(?:cm)?\s*){2})", s2)
    if not m:
        return None
    parts = [p for p in m.group(1).split("x")]
    nums, irregular = [], False
    for part in parts:
        ns = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", part)]
        if not ns:
            return None
        if len(ns) > 1:
            irregular = True
        nums.append(max(ns))
    if len(nums) != 3:
        return None
    unit_mm = " mm" in s2 and "cm" not in s2
    if unit_mm:
        nums = [n / 10 for n in nums]
    # "57 x 37 x 23 - 25 cm": the last side expands from 23 to 25 cm. Fit uses the unexpanded size.
    rng = re.match(r"\s*(?:cm)?\s*[-–]\s*(\d+(?:\.\d+)?)", s2[m.end():])
    expanded = None
    if rng:
        expanded = nums[:2] + [float(rng.group(1))]
    return {"raw": C.collapse(raw), "cm": nums, "irregular": irregular, "expanded_cm": expanded,
            "expandable": bool(expanded) or bool(re.search(r"expan", s, re.I)), "labels": labels}


def parse_weight(raw: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg", raw or "", re.I)
    return float(m.group(1)) if m else None


def fmt_num(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def fmt_dims(cm: list[float]) -> str:
    return " × ".join(fmt_num(x) for x in cm) + " cm"


# ---------------------------------------------------------------- facts

def verify_value(text: str, value: str, also: list[str] | None = None) -> bool:
    t = C.norm_for_match(text)
    vals = [value] + list(also or [])
    return all(C.norm_for_match(v) in t for v in vals if v)


# a value that depends on a sentence it doesn't include: "…You must do this within 30 days", "if this is the case"
BACKREF_VALUE = re.compile(r"\b(if|when) (this|that|so) (is|happens|applies)( the case)?\b|\bif so\b|"
                           r"\bin (this|that|such) case\b|\b(must|should|need to|have to) do (this|that|so)\b", re.I)


def fact_from_source(spec: dict, url: str, res: dict | None) -> dict:
    f = {k: v for k, v in spec.items()}
    url = C.clean_url(url)  # facts carried over in the brief from older runs may still hold ?bc=… or ?utm_…
    f["source_url"] = url
    f.setdefault("claim", f.get("id"))
    f["value"] = str(f.get("value", ""))
    state = (res or {}).get("state")
    text = (res or {}).get("text", "")
    cap = C.captured_text(url)
    if f.get("absence_of"):
        # "X has no Y": verified when the authoritative page loads, states the
        # alternative (`also`) and contains none of the `absence_of` phrases.
        body = text if state == "ok" else (cap or "")
        if not body:
            f.update(status="pending", basis="none", reason=f"source {state or 'unreachable'} ({(res or {}).get('status')})")
        else:
            hits = [p for p in f["absence_of"] if C.norm_for_match(p) in C.norm_for_match(body)]
            ok = not hits and verify_value(body, "", f.get("also"))
            f.update(status=("verified" if state == "ok" else "captured") if ok else "not_found",
                     basis="absence_check", retrieved_at=(res or {}).get("fetched_at") or _cap_date(url),
                     reason=None if ok else f"page mentions {hits or 'none of the required alternatives'}")
    elif state == "ok" and verify_value(text, f["value"], f.get("also")):
        f.update(status="verified", basis="script_fetch", retrieved_at=res["fetched_at"])
    elif state == "ok" and cap and verify_value(cap, f["value"], f.get("also")):
        f.update(status="captured", basis="agent_capture", retrieved_at=_cap_date(url))
    elif state == "ok":
        f.update(status="not_found", basis="script_fetch", retrieved_at=res["fetched_at"],
                 reason="source fetched but value not found in its text")
    elif cap and verify_value(cap, f["value"], f.get("also")):
        f.update(status="captured", basis="agent_capture", retrieved_at=_cap_date(url))
    elif cap:
        f.update(status="not_found", basis="agent_capture", retrieved_at=_cap_date(url),
                 reason="agent-captured page text does not contain the value")
    else:
        # Never usable on anyone's word: step 2 verifies it another way, or the copy writes around it.
        f.update(status="pending", basis="none",
                 reason=f"source {state or 'unreachable'} to scripts ({(res or {}).get('status')})")
    f["verified"] = f["status"] in ("verified", "captured")
    return f


def _cap_date(url: str) -> str:
    p = C.captured_path(url)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.stat().st_mtime))


# ---------------------------------------------------------------- sitemap

def pick_child_sitemaps(locs: list[str], brief: dict, limit: int = 40) -> list[str]:
    """The child sitemaps to read. Up to 40, fetched at once in the background research (Toolstation's 31 take about
    6 s): a sitemap named by number ("category/17.xml") can't be judged by its name, and the one holding the guides
    ("information.xml") once scored nothing, so every related guide and product was missed. Content sitemaps first."""
    explicit = brief.get("sitemaps")
    if explicit:
        return explicit
    if len(locs) <= limit:
        return locs
    path = urlparse(brief.get("page_url") or "").path.strip("/")
    tokens = [t for t in re.split(r"[/\-_]", path) if len(t) > 2]
    tokens += [t for t in re.findall(r"[a-z]{4,}", (brief.get("target_query") or "").lower())]
    seg = path.split("/")[0] if path else ""
    scored = []
    for loc in locs:
        name = urlparse(loc).path.lower()
        score = 0
        if seg and seg in name:
            score += 10
        score += sum(1 for t in tokens if t in name)
        if re.search(r"(^|/)(page|pages)[-_]?sitemap|sitemap[-_]pages", name):
            score += 3
        if re.search(r"(post|blog|article|news|guide|learn|help|advice|information|info|resource|knowledge|how-?to)", name):
            score += 5  # where a site keeps its guides: what a guide links to
        if re.search(r"(product|collection|categor|service)", name):
            score += 2
        scored.append((score, loc))
    scored.sort(key=lambda x: -x[0])
    return [loc for s, loc in scored if s > 0][:limit] or [loc for s, loc in scored][:limit]


# ---------------------------------------------------------------- products

def product_record(pj: dict, page: dict | None, domain: str, currency: str = "") -> dict:
    handle = pj["handle"]
    url = f"https://{domain}/products/{handle}"
    body = C.collapse(re.sub(r"<[^>]+>", " ", htmlmod.unescape(pj.get("body_html") or "")))
    specs = {}
    for k, v in (page or {}).get("dl", []):
        if k and v and len(k) < 40:
            specs[k] = v
    # "Dimensions" beats "Size" (which is often a label like 20" (Cabin)); only take values that contain digits x digits.
    dims_raw = next((specs[k] for key in ("dimensions", "measurements", "size", "external dimensions")
                     for k in specs if k.lower() == key and re.search(r"\d\s*(?:cm)?\s*[x×]\s*\d", specs[k])), "")
    if not dims_raw:
        m = re.search(r"\d+(?:\.\d+)?\s*(?:cm)?\s*[x×]\s*\d+(?:\.\d+)?\s*(?:cm)?\s*[x×]\s*\d+(?:\.\d+)?\s*cm", body)
        dims_raw = m.group(0) if m else ""
    weight_raw = next((v for k, v in specs.items() if k.lower() == "weight"), "")
    if not weight_raw:
        m = re.search(r"\d+(?:\.\d+)?\s*kg", body, re.I)
        weight_raw = m.group(0) if m else ""
    variants = pj.get("variants") or []
    prices = sorted({v.get("price") for v in variants if v.get("price")})
    colours = []
    for o in pj.get("options") or []:
        if (o.get("name") or "").lower() in ("color", "colour", "colours", "colors"):
            colours = o.get("values") or []
    title = (page or {}).get("h1", [None])[0] if (page or {}).get("h1") else pj.get("title")
    vendor = pj.get("vendor") or ""
    display = title if vendor.lower() in (title or "").lower() else f"{vendor} {title}".strip()
    laptop = re.search(r"(?:laptops?|devices?)[^.]{0,30}?up to\s*(\d+(?:\.\d+)?)\s*(?:\"|”|inch|in\b)", body, re.I)
    codes = [t.split(":", 1)[1] for t in (pj.get("tags") or []) if str(t).startswith("source-ref:")]
    status = page.get("status") if page else None
    final = page.get("final_url") if page else None
    return {
        "handle": handle, "url": url, "display_name": display, "title": title, "vendor": vendor,
        "product_type": pj.get("product_type"), "prices": prices, "currency": currency, "colours": colours,
        "specs": {k: v for k, v in specs.items() if k.lower() != "brand"},
        "dims": parse_dims(dims_raw), "weight_kg": parse_weight(weight_raw),
        # "Approx. 1.2 kg (estimated)" is the shop's guess, not a spec: never quote it as a weight
        "weight_estimated": bool(re.search(r"approx|estimat|around|about|~", weight_raw or "", re.I)),
        "laptop_max_in": float(laptop.group(1)) if laptop else None,
        "description": body[:600], "internal_codes": codes,
        "page_status": status, "page_final_url": final,
        # Shopify marks each variant available or not; a product nobody can buy is not a recommendation
        "in_stock": (any(v.get("available") for v in variants) if any("available" in v for v in variants) else None),
    }


def product_facts(p: dict, fetched_at: str) -> list[dict]:
    base = {"source_url": p["url"], "status": "verified", "basis": "client_product_page",
            "verified": True, "retrieved_at": fetched_at, "subject": p["display_name"]}
    out = []
    if p["dims"]:
        out.append({**base, "id": f"p:{p['handle']}:dims", "claim": f"{p['display_name']} dimensions",
                    "value": p["dims"]["raw"], "numbers": p["dims"]["cm"]})
    if p["weight_kg"] and not p.get("weight_estimated"):
        out.append({**base, "id": f"p:{p['handle']}:weight", "claim": f"{p['display_name']} weight",
                    "value": f"{fmt_num(p['weight_kg'])} kg", "numbers": [p["weight_kg"]]})
    if p["laptop_max_in"]:
        out.append({**base, "id": f"p:{p['handle']}:laptop", "claim": f"{p['display_name']} laptop sleeve",
                    "value": f"laptops up to {fmt_num(p['laptop_max_in'])}\"", "numbers": [p["laptop_max_in"]]})
    for k, v in p["specs"].items():
        if k.lower() in ("dimensions", "size", "weight"):
            continue
        out.append({**base, "id": f"p:{p['handle']}:{C.slugify(k)}", "claim": f"{p['display_name']} {k.lower()}", "value": v})
    prices = p.get("prices") or p.get("prices_gbp") or []  # in the shop's market currency, never assumed
    sym = p.get("currency", "£" if p.get("prices_gbp") else "")
    if prices:
        out.append({**base, "id": f"p:{p['handle']}:price", "claim": f"{p['display_name']} price",
                    "value": " / ".join(sym + x for x in prices), "kind": "price",
                    "numbers": [float(x) for x in prices]})
    return out


# ---------------------------------------------------------------- checks

def run_checks(sheet: dict, brief: dict) -> dict:
    out = {}
    for name in brief.get("vertical_checks") or []:
        path = C.ROOT / "checks" / f"{name}.py"
        if not path.exists():
            out[name] = {"error": f"no check module checks/{name}.py"}
            continue
        spec = importlib.util.spec_from_file_location(f"checks.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        try:
            out[name] = mod.run(sheet, brief)
        except Exception as e:  # never let a check crash prep
            out[name] = {"error": f"{type(e).__name__}: {e}"}
    return out


# ---------------------------------------------------------------- main

def prep(brief_path: str, refresh: bool = False, quiet: bool = False, timing: bool = True) -> Path:
    t0 = time.time()
    brief = load_brief(brief_path)
    rd = run_dir(brief)
    rd.mkdir(parents=True, exist_ok=True)
    if timing:
        mark(rd, "prep", "start", fresh=True)
    domain = brief["domain"].removeprefix("https://").removeprefix("http://").strip("/")
    page_url = brief["page_url"]

    # ---- round 1: page, sitemap, product JSON, official sources
    # Client claims are checked against the client's own pages: this page, the homepage and any claims_pages.
    claim_pages = list(dict.fromkeys([f"https://{domain}/"] + list(brief.get("claims_pages") or [])))
    blog_index = f"https://{domain}{brief.get('blog_path') or '/blog/'}"
    reqs = [{"url": page_url, "kind": "page", "parse": "html"},
            {"url": f"https://{domain}/sitemap.xml", "kind": "sitemap", "parse": "xml"},
            {"url": f"https://{domain}/robots.txt", "kind": "page", "parse": "raw"},
            {"url": blog_index, "kind": "page", "parse": "html"}]
    reqs += [{"url": u, "kind": "page", "parse": "html"} for u in claim_pages if u != page_url]
    ps = brief.get("product_sources") or {}
    shopify = brief.get("platform") == "shopify" and ps
    if shopify:
        cols = ps.get("collection")
        for col in ([cols] if isinstance(cols, str) else cols or []):
            reqs.append({"url": f"https://{domain}/collections/{col}/products.json?limit=250",
                         "kind": "product", "parse": "json"})
        for h in ps.get("handles") or []:
            reqs.append({"url": f"https://{domain}/products/{h}.json", "kind": "product", "parse": "json"})
    srcs, by_url = [], {}
    for s in brief["official_sources"]:
        s = {"url": s} if isinstance(s, str) else dict(s)
        s["url"] = C.clean_url(s["url"])
        s["facts"] = list(s.get("facts") or [])
        srcs.append(s)
        by_url[s["url"]] = s
    seen_extra = set()
    for e in brief.get("extra_facts") or []:  # facts added by --add-fact in earlier runs
        e = dict(e)
        u = C.clean_url(e.pop("source_url"))
        if (u, str(e.get("value"))) in seen_extra:
            continue
        if BACKREF_VALUE.search(str(e.get("value", ""))):
            print(f"  saved fact {e.get('id')} skipped: it points back to a case it doesn't include (\"do this\", \"if so\")")
            continue
        seen_extra.add((u, str(e.get("value"))))
        if u not in by_url:
            by_url[u] = {"url": u, "facts": []}
            srcs.append(by_url[u])
        by_url[u]["facts"].append(e)
    reqs += [{"url": s["url"], "kind": "official", "parse": "html"} for s in srcs]
    r1 = C.run_async(C.fetch_many(reqs, refresh))

    # ---- round 2: child sitemaps + product pages
    sm = r1.get(f"https://{domain}/sitemap.xml") or {}
    locs = sm.get("locs") or []
    if not locs:
        robots = (r1.get(f"https://{domain}/robots.txt") or {}).get("raw") or ""
        alts = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
        alts += [f"https://{domain}/{x}" for x in ("sitemap_index.xml", "sitemap-index.xml", "wp-sitemap.xml",
                                                    "sitemap/sitemap.xml", "sitemaps/sitemap.xml")]
        ra = C.run_async(C.fetch_many([{"url": u, "kind": "sitemap", "parse": "xml"} for u in dict.fromkeys(alts)],
                                      refresh))
        for u in dict.fromkeys(alts):
            if (ra.get(u) or {}).get("locs"):
                sm, locs = ra[u], ra[u]["locs"]
                break
    child_maps = pick_child_sitemaps(locs, brief) if sm.get("is_index") else []
    product_json = []
    for u, res in r1.items():
        j = res.get("json") or {}
        if "products" in j:
            product_json += j["products"]
        elif "product" in j:
            product_json.append(j["product"])
    seen, prods_raw = set(), []
    inc = [x.lower() for x in ps.get("include") or []] if ps else []
    exc = [x.lower() for x in ps.get("exclude") or []] if ps else []
    for pj in product_json:
        h = pj.get("handle")
        if not h or h in seen:
            continue
        name = f"{h} {pj.get('title', '')}".lower()
        if inc and not any(x in name for x in inc):
            continue
        if any(x in name for x in exc):
            continue
        seen.add(h)
        prods_raw.append(pj)
    reqs2 = [{"url": u, "kind": "sitemap", "parse": "xml"} for u in child_maps]
    reqs2 += [{"url": f"https://{domain}/products/{pj['handle']}", "kind": "product", "parse": "html"}
              for pj in prods_raw]
    r2 = C.run_async(C.fetch_many(reqs2, refresh, timeout=8, attempts=1)) if reqs2 else {}  # one try: child maps can be huge

    # ---- page
    page = r1.get(page_url) or {}
    page_info = {"url": page_url, "status": page.get("status"), "state": page.get("state"),
                 "title": page.get("title"), "h1": (page.get("h1") or [None])[0] if page.get("state") == "ok" else None,
                 "h2": page.get("h2", []) if page.get("state") == "ok" else [],
                 "meta_description": page.get("meta_description"),
                 "exists": page.get("status") == 200}
    if page_info["exists"]:
        page_info["text_excerpt"] = page.get("text", "")[:1500]

    # ---- products
    products = []
    for pj in prods_raw:
        pg = r2.get(f"https://{domain}/products/{pj['handle']}")
        from .graph import market_of
        products.append(product_record(pj, pg, domain, market_of(brief.get("locale") or "en")[1]))
    cols = (ps or {}).get("collection")
    chosen = (bool(ps) and cols not in (None, "all", ["all"])) or bool((ps or {}).get("handles"))
    products = relevant_products(products, brief["target_query"], brief.get("synonyms"), chosen=chosen)

    # ---- facts
    facts: list[dict] = []
    for p in products:
        facts += product_facts(p, (r2.get(p["url"]) or {}).get("fetched_at", C.now_iso()))
    blocked = []
    for s in srcs:
        res = r1.get(s["url"])
        if s["url"].lower().split("?")[0].endswith(".pdf") and (res or {}).get("state") != "ok" or \
                s["url"].lower().split("?")[0].endswith(".pdf") and len((res or {}).get("text") or "") < 400:
            try:
                txt = pdf_text(s["url"])
            except Exception:
                txt = ""
            if txt:
                res = {"state": "ok", "text": txt, "fetched_at": C.now_iso(), "status": 200}
        if (res or {}).get("state") != "ok":
            blocked.append({"url": s["url"], "status": (res or {}).get("status"), "state": (res or {}).get("state"),
                            "captured": bool(C.captured_text(s["url"]))})
        fu = (res or {}).get("final_url") or ""
        if (res or {}).get("state") == "ok" and fu and C.host(fu) == C.host(s["url"]) and fu.rstrip("/") != s["url"].rstrip("/"):
            s["url"] = fu.split("#")[0]  # the page moved: cite it where it lives now
        for spec in s.get("facts") or []:
            facts.append(fact_from_source(spec, s["url"], res))
    for i, cf in enumerate(brief["client_facts"]):
        facts.append({"id": f"client:{i + 1}", "claim": "client fact (operator)", "value": cf,
                      "status": "operator", "basis": "operator", "verified": False, "source_url": None})
    site_text = " ".join([page.get("text", "")] + [(r2.get(p["url"]) or {}).get("text", "") for p in products]
                         + [(r1.get(u) or {}).get("text", "") for u in claim_pages])
    claims = []
    for i, c in enumerate(brief["approved_claims"]):
        on_site = verify_value(site_text, c) if site_text else False
        claims.append({"id": f"claim:{i + 1}", "text": c, "seen_on_site": on_site})
    # What the client publicly says about itself (homepage title and description) may describe the client.
    home_page = r1.get(f"https://{domain}/") or {}
    says = site_says(home_page)
    visible = re.sub(r"\s+", " ", (home_page.get("text") or "")).replace(",", "")
    kept_says = []
    for s in says:
        bad = [n for n in re.findall(r"\d[\d,]{2,}", s) if visible and n.replace(",", "") not in visible]
        if bad:
            # "fitted at one of over 2,300 UK garages" -> "fitted at one of UK garages": the offer stands, the stale count goes
            s2 = s
            for n in bad:
                s2 = re.sub(r"\b(over|more than|around|about|nearly|almost|up to)?\s*" + re.escape(n) + r"\+?\s*", "", s2)
            s2 = re.sub(r"\s{2,}", " ", s2).strip()
            print(f"  client claim figure dropped (not on the visible homepage): {', '.join(bad)}")
            s = s2
        page_cur = {"gb": "£", "us": "$", "ie": "€", "de": "€", "fr": "€", "es": "€", "it": "€", "nl": "€",
                    "au": "$", "ca": "$"}.get((brief.get("locale") or "en").partition("-")[2].lower())
        if page_cur and any(x in s and x != page_cur for x in ("£", "$", "€")):
            print(f"  client claim dropped (another market's currency): {s[:70]}")
            continue
        kept_says.append(s)
    says = kept_says
    for i, s in enumerate(says):
        claims.append({"id": f"site:{i + 1}", "text": s, "seen_on_site": True, "basis": "client homepage",
                       "source_url": f"https://{domain}/"})

    # ---- link map
    sm_urls = []
    for u in child_maps:
        sm_urls += [x for x in (r2.get(u) or {}).get("locs", []) if C.host(x) == C.host(f"https://{domain}")]
    if not sm.get("is_index"):
        sm_urls += [x for x in locs if C.host(x) == C.host(f"https://{domain}")]
    if not sm_urls:
        for src in (f"https://{domain}/", blog_index, page_url):
            for href, _label in (r1.get(src) or {}).get("links", []):
                u = href.split("#")[0]
                if C.host(u) == C.host(f"https://{domain}"):
                    sm_urls.append(u)
    sm_urls = sorted(set(u.split("?")[0].rstrip("/") for u in sm_urls))
    prefix = urlparse(page_url).path.rstrip("/") + "/"
    children = {}
    if brief["page_type"] == "hub":
        explicit = brief.get("child_pages")
        if isinstance(explicit, list):
            children = {u: "" for u in explicit}
        else:
            for href, label in page.get("links", []):
                u = href.split("#")[0].split("?")[0].rstrip("/")
                if C.host(u) == C.host(page_url) and urlparse(u).path.startswith(prefix):
                    children.setdefault(u, label)
            for u in sm_urls:
                if urlparse(u).path.startswith(prefix):
                    children.setdefault(u, "")
        for u in list(children):
            if not children[u]:
                children[u] = urlparse(u).path.rstrip("/").split("/")[-1].replace("-", " ").title()
    in_sitemap = set(sm_urls)
    link_map = {
        "generated_at": C.now_iso(),
        "page": page_url,
        "products": [{"name": p["display_name"], "url": p["url"], "status": p["page_status"],
                      "redirected_to": p["page_final_url"] if p["page_final_url"] and p["page_final_url"].rstrip("/") != p["url"] else None}
                     for p in products],
        "children": [{"name": n, "url": u, "in_sitemap": u in in_sitemap} for u, n in sorted(children.items(), key=lambda x: x[1])],
        "official": [{"url": s["url"], "state": (r1.get(s["url"]) or {}).get("state"),
                      "status": (r1.get(s["url"]) or {}).get("status"),
                      "captured": bool(C.captured_text(s["url"])), "label": s.get("label", "")}
                     for s in srcs] + [{"url": u, "state": "listed", "status": None, "label": l}
                                       for u, l in (brief.get("extra_links") or {}).items()],
        "internal": clean_internal([u for u in sm_urls if u not in children and "/products/" not in u],
                                   brief.get("locale") or "en")[:3000],
    }
    # the client's own pages on this topic: same-topic pages (cannibalisation), related guides, next-step pages
    rel = related(clean_internal(sm_urls, brief.get("locale") or "en"), brief["target_query"],
                  brief.get("synonyms"), exclude=page_url)
    link_map["client_candidates"] = rel.pop("candidates", [])  # re-ranked by the topic's entities in plan.py
    # (the "site:client query" Google search runs after the research waves, when a credit is left: client_site_search)
    offered = list(dict.fromkeys(rel["same_topic"] + rel["guides"] + rel["commercial"]))
    # one round for every client page this step reads (related pages, and the pages the offer model reads), short
    # limits and no retry: they help the page, none is worth waiting on (sequential rounds of 12 s with a retry made
    # this step take a minute on large sites)
    opages_pre = ([page_url] if page_info.get("exists") else []) + [f"https://{domain}/"] \
        + rel["same_topic"][:1] + rel["commercial"][:2]
    async def _both():  # results are keyed by URL, so the two readings of a page run as two calls, side by side
        import asyncio
        return await asyncio.gather(
            C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in offered], refresh, timeout=6, attempts=1),
            C.fetch_many([{"url": u, "kind": "page", "parse": "html"} for u in dict.fromkeys(opages_pre)], refresh,
                         timeout=6, attempts=1))
    pre_res, _offer_res = C.run_async(_both())
    if offered:
        chk = {u: pre_res.get(u) or {} for u in offered}
        final = {}
        for u in offered:
            r = chk.get(u) or {}
            fu = (r.get("final_url") or u).split("#")[0]
            if r.get("status") and r["status"] >= 400:
                final[u] = None  # dead page: never offer it
            elif C.host(fu) == C.host(u):
                final[u] = fu.rstrip("/") if not u.endswith("/") else fu
            else:
                final[u] = u
        rel = {k: list(dict.fromkeys(final[u] for u in v if final.get(u, u))) for k, v in rel.items()}
        # each page's own title, so an anchor can promise what the page really is
        link_map["client_titles"] = {final[u]: re.split(r"\s[|–—-]\s", (chk.get(u) or {}).get("title") or "")[0].strip()
                                     for u in offered if final.get(u) and (chk.get(u) or {}).get("title")}
        link_map["internal"] = list(dict.fromkeys(link_map["internal"] + [x for v in rel.values() for x in v]))
    link_map["client_related"] = rel
    gpages = rel["guides"][:4] + rel["same_topic"][:1]
    if gpages:
        gres = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in gpages], refresh,
                                        timeout=6, attempts=1))
        for i, cp in enumerate(client_passages({u: gres.get(u) or {} for u in gpages}, brief["target_query"],
                                               rich=tuple(rel["same_topic"][:1]), syn=
                                               brief.get("synonyms")), 1):
            facts.append({"id": f"client-page:{i}", "claim": f"the client's own guide (its wording; where an authority "
                                                               f"fact differs, the authority wins): {cp['title'][:70]}",
                          "value": cp["text"], "status": "verified", "basis": "client_page", "verified": True,
                          "source_url": cp["url"], "retrieved_at": C.now_iso()})
    # What the client sells, from its own pages (this page, its home page, its pages on the topic): the offer a
    # commercial page exists to make. Each offer sentence is the client's own published claim, usable in its voice.
    offer = {}
    try:
        from .offer import offer_profile
        opages = ([page_url] if page_info.get("exists") else []) + [f"https://{domain}/"] \
            + rel["same_topic"][:1] + rel["commercial"][:2]
        offer = offer_profile(brief["client"], domain, opages, page_info.get("title") or "",
                              banned=list(brief.get("banned_claims") or []) + list(brief.get("banned_phrases") or []),
                              refresh=refresh, target_query=brief["target_query"], page_url=page_url)
        for i, o in enumerate(offer.get("offers", []), 1):
            facts.append({"id": f"offer:{i}", "claim": "what the client offers, in its own words on its own page",
                          "value": o["text"], "status": "verified", "basis": "client_page", "verified": True,
                          "scope": o.get("scope"), "source_url": o["url"], "retrieved_at": C.now_iso()})
        for c in offer.get("ctas", []):
            if c["url"] not in link_map["internal"]:
                link_map["internal"].append(c["url"])
    except Exception as e:  # the offer model is help, never a reason to stop
        print(f"  offer model skipped ({type(e).__name__}: {e})")
    # URLs quoted inside verified facts (e.g. an embassy page naming the CEAC address) are linkable too
    known = {o["url"] for o in link_map["official"]}
    for f in facts:
        if f["status"] not in ("verified", "captured"):
            continue
        for u in re.findall(r"https?://[^\s\"')]+", " ".join([f["value"]] + list(f.get("also") or []))):
            u = u.rstrip(".,;")
            if u not in known:
                known.add(u)
                link_map["official"].append({"url": u, "state": "cited", "status": None, "captured": False,
                                             "label": f"cited by {f['source_url']}"})

    # ---- sheet
    sheet = {
        "brief": {k: brief.get(k) for k in ("client", "client_aliases", "domain", "locale", "page_url", "page_type",
                                             "target_query", "search_intent", "word_range", "ymyl", "mode",
                                             "hardcode_prices", "h1", "single_brand", "banned_phrases", "proper_nouns",
                                             "link_context_bans", "secondary_queries", "notes", "synonyms",
                                             "reader_nouns", "known_failures", "internal_codes", "banned_claims", "author", "experience", "task",
                                             "instructions", "page_type_source", "word_range_source", "page_url_source", "conversion_targets",
                                             "source_context", "site_inventory", "research_format", "batch_plan", "batch_item")},
        "generated_at": C.now_iso(),
        "brief_path": brief["_path"],
        "page": page_info,
        "products": products,
        "facts": facts,
        "client": {"facts": brief["client_facts"], "approved_claims": claims, "banned_claims": brief["banned_claims"],
                   "offer": offer,
                   "site_says": says},
        "children_count": len(children),
        "blocked_sources": blocked,
    }
    sheet["checks"] = run_checks(sheet, brief)
    sheet["gaps"] = gaps(sheet, brief)
    sheet["decisions"] = decisions(sheet, brief)
    # a client whose homepage now redirects to another organisation's site has been renamed or taken over: the page
    # must name the business as its live site does, or readers meet a brand that no longer exists
    from .domains import org_domain
    home = r1.get(f"https://{domain}/") or {}
    moved_to = home.get("final_url") or ""
    if moved_to and org_domain(moved_to) != org_domain(f"https://{domain}/"):
        sheet["client"]["moved_to"] = moved_to
        sheet["decisions"].insert(0,
            f"The client's site {domain} now redirects to {moved_to} (a rename, merger or takeover). Name the business "
            f"as that live site does, mention the former name once (\"formerly {brief.get('client')}\"), take client facts "
            f"from the live site, and the operator should update the client profile (domain, name) before the next run.")
    for u in link_map.get("client_related", {}).get("same_topic", []):
        sheet["decisions"].append(
            f"The client already has a page on this topic: {u}. Two pages on one query compete with each other; "
            "write this page as the stronger, consolidated page for the query (cover everything that page covers, and "
            "more), don't link it in the opening sections, and the operator should merge it into this page or "
            "301-redirect it here once this page is live.")
    C.save_json(rd / "fact_sheet.json", sheet)
    C.save_json(rd / "link_map.json", link_map)
    writer_pack(rd, sheet, link_map)
    if timing:
        mark(rd, "prep", "end")
    if not quiet:
        print_summary(rd, sheet, link_map, time.time() - t0)
    return rd


def gaps(sheet: dict, brief: dict) -> list[dict]:
    out = []
    by_id = {f["id"]: f for f in sheet["facts"]}
    for rid in brief.get("required_facts") or []:
        f = by_id.get(rid)
        if not f or f["status"] not in USABLE:
            out.append({"id": rid, "claim": (f or {}).get("claim", rid),
                        "reason": (f or {}).get("reason", "not declared in brief"),
                        "source_url": (f or {}).get("source_url")})
    for f in sheet["facts"]:
        if f["status"] in ("not_found", "unverified", "pending") and f["id"] not in {g["id"] for g in out}:
            out.append({"id": f["id"], "claim": f.get("claim"), "reason": f.get("reason"),
                        "source_url": f.get("source_url"), "optional": True})
    return out


def decisions(sheet: dict, brief: dict) -> list[str]:
    """What the automation decided on its own. Logged in report.md; never asked."""
    d = []
    for f in sheet["facts"]:
        if f["status"] == "pending":
            d.append(f"{f['claim']} (\"{f['value']}\"): {f['source_url']} is {f.get('reason')}. "
                     "Step 2 verifies it through the agent's own browser or another official source; otherwise the copy omits it.")
        elif f["status"] in ("not_found", "unverified"):
            d.append(f"Omitted {f['claim']} (\"{f['value']}\"): {f.get('reason')}.")
    if not (sheet.get("brief") or {}).get("author"):
        d.append("No named author in the client profile (`author:` with a name and role). Pages with a named, qualified "
                 "author earn more trust: the operator should add one; the page is written without a byline meanwhile.")
    for c in sheet["client"]["approved_claims"]:
        if not c["seen_on_site"]:
            d.append(f"Client claim \"{c['text']}\" is not on the client's pages, so it is not used.")
    for name, res in sheet.get("checks", {}).items():
        for w in (res or {}).get("decisions", []):
            d.append(f"[{name}] {w}")
    if not sheet["page"]["exists"]:
        d.append(f"{sheet['page']['url']} returned {sheet['page']['status']}: written as a new page.")
    return d


def writer_pack(rd: Path, sheet: dict, lm: dict) -> None:
    """One compact file with everything the writer may use. The agent reads
    this and RULES.md, nothing else."""
    b = sheet["brief"]
    pg = sheet["page"]
    W = [f"# Writer pack: {b['client']} · {b['page_url']}", ""]
    W.append(f"- Page type: **{b['page_type']}** · query: \"{b['target_query']}\" · intent: {b['search_intent']} · "
             f"locale: {b['locale']} · words: {(b.get('word_range_effective') or b['word_range'])[0]}–{(b.get('word_range_effective') or b['word_range'])[1]} · YMYL: {b.get('ymyl') if b.get('ymyl') in (True, False) else 'auto (set by the SERP during research)'}")
    h1 = b.get("h1") or pg.get("h1")
    W.append(f"- H1: " + (f"use exactly \"{h1}\"" if h1 else "new page; write a sentence-case H1 that matches the query"))
    W.append(f"- Prices: {'product prices may be stated' if b.get('hardcode_prices') else 'do NOT state product prices (they change daily; link the product instead)'}"
             "; a fee, rate or charge that is a verified fact may be stated, with its source and the date it applies from")
    W.append(f"- Write to: {(rd / 'draft.md').resolve().as_posix()} (front matter: title, meta_description)")
    if b.get("notes"):
        W.append(f"- Operator notes: {b['notes']}")
    if b.get("instructions"):
        W.append(f"- **Operator instructions for this page:** {b['instructions']} (follow them for angle, audience, tone, "
                 "emphasis and length; where one would need an unverified fact or break an accuracy rule, keep the rule "
                 "and log it in editor.md)")
    from .pagejob import lines as _job
    job = _job(sheet)
    W += job
    (rd / "page_context.md").write_text("\n".join(job) + "\n", encoding="utf-8")
    if pg.get("exists"):
        W += ["", "## Live page now", f"- Title: {pg.get('title')}", f"- H1: {pg.get('h1')}",
              f"- H2s: {'; '.join(pg.get('h2') or [])}", f"- Text: {pg.get('text_excerpt', '')[:900]}"]
    if b.get("secondary_queries"):
        W.append("- Also answer these searches (in headings or opening sentences, naturally): "
                 + "; ".join(f"\"{q}\"" for q in b["secondary_queries"]))
    W += ["", "## Facts you may use", "Every number, size, fee, date, portal name and feature must come from here. Basis: verified = script found it on the source; captured = found in page text an agent read with its own browser.", ""]
    from .domains import kind as _kind
    groups = {}
    # brands that sell in the same results as the client are competitors: their data is context, not the page's backbone
    serp = C.load_json(rd / "research" / "serp_intel.json") if (rd / "research" / "serp_intel.json").exists() else {}
    client_dom = (b.get("domain") or "").replace("www.", "")
    rivals = {o.get("domain", "").removeprefix("www.") for o in (serp or {}).get("organic", [])
              if o.get("kind") in ("business_site", "ecommerce", "marketplace")} - {client_dom}
    COMP = "brands that compete with the client (context only: attribute it as theirs, limit it to their product, never the main answer or the first link)"
    from .nlp import tokens as _tok
    says = " ".join(c["text"] for c in sheet["client"].get("approved_claims", []))
    category = ({w for w in _tok(b.get("target_query", ""), b.get("synonyms")) if len(w) > 2}
                & {w for w in _tok(says, b.get("synonyms")) if len(w) > 2})
    for f in sheet["facts"]:
        if f["status"] not in USABLE or f["id"].startswith("p:") or f["id"].startswith("client:"):
            continue
        src = f.get("source_url") or ""
        sk = _kind(src)
        sd = urlparse(src).netloc.lower().removeprefix("www.")
        if f.get("basis") == "client_page" or (client_dom and sd.endswith(client_dom)):
            k = "client's own pages (use in the client's voice)"
        elif sk in ("government", "international"):
            k = "authorities"
        elif sk in ("nonprofit", "education"):
            k = "independent organisations (charities, professional bodies, universities)"
        elif sd and (sd in rivals or (not serp and sk in ("business_site", "ecommerce")) or (
                sk in ("business_site", "ecommerce") and category
                and category & set(_tok(str(f.get("claim", "")) + " " + str(f.get("value", "")), b.get("synonyms"))))):
            k = COMP
        else:
            k = "other sources (publishers, trade bodies, brands)"
        groups.setdefault(k, []).append(f)
    for k in ("authorities", "independent organisations (charities, professional bodies, universities)",
              "other sources (publishers, trade bodies, brands)", COMP, "client's own pages (use in the client's voice)"):
        if not groups.get(k):
            continue
        W.append(f"From {k}:")
        seen_vals = set()
        for f in groups[k]:
            nv = re.sub(r"\W+", " ", str(f["value"]).lower()).strip()
            if nv in seen_vals:
                continue
            seen_vals.add(nv)
            cond = f" ({f['condition']})" if f.get("condition") else ""
            also = "".join(f" + \"{a}\"" for a in f.get("also") or [])
            replaced = (f.get("source_url") or "").rstrip("/") in {u.rstrip("/") for u in (lm.get("client_related") or {}).get("same_topic", [])}
            clash = ""
            if k.startswith("client's own") and groups.get("authorities"):
                fn = set(re.findall(r"\d+(?:\.\d+)?", str(f["value"])))
                ft = {w for w in _tok(str(f["value"]), b.get("synonyms")) if len(w) > 3 and not w.isdigit()}
                for a in groups["authorities"]:
                    an = set(re.findall(r"\d+(?:\.\d+)?", str(a["value"])))
                    at = {w for w in _tok(str(a["value"]) + " " + str(a.get("claim", "")), b.get("synonyms"))
                          if len(w) > 3 and not w.isdigit()}
                    same_unit = ("%" in str(f["value"])) == ("%" in str(a["value"]))
                    if fn and an and same_unit and len(ft & at) >= 3 and not (fn & an):
                        clash = f" ⚠ differs from authority `{a['id']}` (\"{str(a['value'])[:80]}\"): use the authority's figure"
                        break
            cond += f" [applies to: {f['scope']}]" if f.get("scope") else ""
            W.append(f"- `{f['id']}` [{f['status']}] {f.get('claim')}: \"{f['value']}\"{also}{cond} — "
                     + ("from the page this one replaces: use the fact, don't link it" if replaced else f"{f.get('source_url')}")
                     + clash)
    if sheet["products"]:
        W += ["", "## Products (link each by its URL; never link a product to a collection)"]
        for p in sheet["products"]:
            d = fmt_dims(p["dims"]["cm"]) + (f" [{p['dims']['labels']}]" if p["dims"] and p["dims"].get("labels") else "") if p["dims"] else "dimensions not listed"
            extra = []
            if p.get("in_stock") is False:
                extra.append("OUT OF STOCK: don't recommend or link it")
            if p["dims"] and p["dims"].get("irregular"):
                extra.append(f"irregular shape: {p['dims']['raw']}")
            if p["dims"] and p["dims"].get("expandable"):
                extra.append("expandable")
            if p.get("weight_kg"):
                extra.append(f"{fmt_num(p['weight_kg'])} kg" + (" (shop's estimate; do not quote)" if p.get("weight_estimated") else ""))
            twin = [q["display_name"] for q in sheet["products"] if q is not p and q.get("dims") and p.get("dims")
                    and q["dims"]["cm"] == p["dims"]["cm"] and q.get("weight_kg") == p.get("weight_kg")
                    and p.get("weight_kg") and q["display_name"].split()[:3] != p["display_name"].split()[:3]]
            # colour variants ("Canary Laptop Bag Black") share everything legitimately; different models shouldn't
            if twin:
                extra.append(f"DATA CHECK: same listed size and weight as {twin[0]}; one listing may be copied, so don't quote these")
            if p.get("laptop_max_in"):
                extra.append(f"laptops up to {fmt_num(p['laptop_max_in'])}\"")
            specs = "; ".join(f"{k}: {v}" for k, v in p["specs"].items() if k.lower() not in ("dimensions", "size", "weight", "model"))
            W.append(f"- **{p['display_name']}** — {p['url']} — {d}" + (f" — {', '.join(extra)}" if extra else "")
                     + (f" — colours: {', '.join(p['colours'])}" if p["colours"] else ""))
            if specs:
                W.append(f"  - specs: {specs}")
            W.append(f"  - description (client's own copy, facts only): {p['description'][:420 if len(sheet['products']) <= 12 else 200]}")
    for name, res in (sheet.get("checks") or {}).items():
        if res.get("lines"):
            W += ["", f"## Computed check: {name} (state these results; do not work out fit yourself)",
                  f"Method: {res.get('method', '')}"]
            seen = set()
            for r in res.get("results", []):
                if r["verdict"] == "dims_doubtful":
                    if r["product"] not in seen:
                        seen.add(r["product"])
                        W.append(f"- {r['product']}: {r['note']}")
                    continue
                key = (tuple(r["bag_cm"]), r["limit_id"])
                if key in seen:
                    continue  # colour variants share dimensions
                seen.add(key)
                W.append(f"- {r['product']} vs {r['carrier']} {r['allowance']} ({fmt_dims(r['limit_cm'])}"
                         f"{', ' + r['condition'] if r['condition'] else ''}): {r['note']}")
            if res.get("fit_lists"):
                W += ["", "Counts to copy (never count by eye):"]
                W += [f"- Fits {k}: {len(v)} — {', '.join(v)}" for k, v in res["fit_lists"].items()]
            if res.get("weight_ranking"):
                W.append("Listed weights, lightest first: " + "; ".join(f"{x['product']} {x['weight_kg']} kg"
                                                                      for x in res["weight_ranking"]))
                if res.get("weight_not_listed"):
                    W.append(f"No listed weight ({len(res['weight_not_listed'])}): " + ", ".join(res["weight_not_listed"])
                             + ". So never call any product the lightest or heaviest overall; say \"lightest of those with a listed weight\".")
            wheels = [n for n, a in (res.get("attributes") or {}).items() if a.get("wheels")]
            if res.get("attributes"):
                W.append("Wheels listed for: " + (", ".join(f"{n} ({res['attributes'][n]['wheels']})" for n in wheels) or "none")
                         + ". Don't give that feature to any other product.")
    cl = sheet["client"]
    W += ["", "## Client", "Positioning (client_facts; the only source for who the client is):"]
    offer_lines = (cl.get("offer") or {}).get("offers") or []
    W += [f"- {x}" for x in cl["facts"]] or (
        [f"- From its own pages: see \"Page job\" above (`offer:N` facts). Describe {b['client']} only with those words "
         "and the approved claims below."] if offer_lines else
        ["- (none supplied and none found on its pages: describe the client only with the approved claims below)"])
    W.append("Approved claims, confirmed on the client's site (with the facts from the client's own pages, including the `offer:N` lines, the ONLY things the copy may say about the client's services):")
    W += [f"- \"{c['text']}\"" + (f" (from the client's homepage, {c.get('source_url')}; link it there or not at all)"
                                    if c.get("basis") else "")
          for c in cl["approved_claims"] if c["seen_on_site"]] or [
              "- No additional approved claims. Use the scoped offer:N and client-page facts above where relevant; invent no service capabilities."]
    cur_of = {"gb": "£", "us": "$", "ie": "€", "de": "€", "fr": "€", "es": "€", "it": "€", "nl": "€", "au": "$", "ca": "$"}
    want_cur = cur_of.get((b.get("locale") or "en").partition("-")[2].lower())
    for c in cl["approved_claims"]:
        other = [x for x in ("£", "$", "€") if x in c["text"] and x != want_cur]
        if want_cur and other:
            W.append(f"- Note: \"{c['text'][:60]}…\" is in {other[0]} (another market): don't use it on this page.")
    nums_seen = {}
    for c in cl["approved_claims"]:
        for n in re.findall(r"\d[\d,]{2,}", c["text"]):
            nums_seen.setdefault(re.sub(r"\D", "", c["text"].split(n)[1][:25]), set()).add(n)
    if any(len(v) > 1 for v in nums_seen.values()):
        W.append("Note: the client's own pages give different counts for the same thing "
                 + "; ".join(" vs ".join(sorted(v)) for v in nums_seen.values() if len(v) > 1)
                 + ". Use the approved claim's figure, or no figure.")
    W.append("Banned claims: " + (", ".join(f"\"{x}\"" for x in cl["banned_claims"]) or "none"))
    if b.get("banned_phrases"):
        W.append("Page-specific banned phrases: " + ", ".join(f"\"{x}\"" for x in b["banned_phrases"]))
    if b.get("reader_nouns"):
        W.append("Don't call the reader: " + ", ".join(f"\"{x}\"" for x in b["reader_nouns"]) + " (use \"you\")")
    for r in b.get("link_context_bans") or []:
        W.append(f"Link rule: {r['url']} must not be described with {', '.join(r['words'])} — {r.get('reason', '')}")
    W += ["", "## Links you may use (any URL not named in this pack fails validation)"]
    if lm["children"]:
        W.append(f"Child pages ({len(lm['children'])}); link the relevant ones, do not rebuild their content:")
        W.append("; ".join(f"{c['name']}: {c['url']}" for c in lm["children"]))
    off = list({o["url"].rstrip("/"): o for o in lm["official"]}.values())
    if off:
        from .domains import kind as _k
        replaced_urls = {u.rstrip("/") for u in (lm.get("client_related") or {}).get("same_topic", [])}
        off = [o for o in off if o["url"].rstrip("/") not in replaced_urls]
        W.append("Sources (link the claim to its source):")
        W += [f"- {o['url']} ({o.get('label') or _k(o['url'])}; {_k(o['url'])}; "
              f"{'captured' if o.get('captured') else o['state']})" for o in off]
    rel = lm.get("client_related") or {}
    ttl = lm.get("client_titles") or {}
    named = lambda us: ", ".join(f"{u}" + (f" (\"{ttl[u]}\")" if ttl.get(u) else "") for us_ in [us] for u in us_)
    if rel.get("commercial"):
        W.append("Client pages that are the reader's natural next step (link inside the relevant section; the anchor "
                 "describes the page's own title): " + named(rel["commercial"]))
    if rel.get("guides"):
        W.append("Client guides on related questions (link where they answer a follow-up): " + named(rel["guides"]))
    if rel.get("same_topic"):
        W.append("Client pages on this same topic. This page is written as the stronger, consolidated page for the query; "
                 "don't link them in the opening sections, and the report recommends merging or redirecting them: "
                 + named(rel["same_topic"]))
    page_path = urlparse(b["page_url"]).path.rstrip("/")
    parent = page_path.rsplit("/", 1)[0]
    from .nlp import place_slugs, places, tokens
    # pages about the query's own subject words, or about the places it names (any slug form of the place)
    common = {"how", "what", "why", "when", "where", "which", "who", "for", "does", "do", "the", "and", "best", "can",
              "is", "are", "to", "a", "an", "of", "in", "on", "my", "your", "be", "take", "get", "check", "online"}
    qtoks = {w for w in tokens(b["target_query"], b.get("synonyms")) if len(w) > 2 and not w.startswith("geo:")} - common
    slugs = set().union(*(place_slugs(p) for p in places(b["target_query"]))) if places(b["target_query"]) else set()
    slugs = {s for s in slugs if len(s) > 2}
    related = [u for u in lm["internal"] if (qtoks & set(re.findall(r"[a-z0-9]+", urlparse(u).path.lower()))
                                             or slugs & set(urlparse(u).path.lower().split("/")))
               and urlparse(u).path.rstrip("/") != page_path]
    if parent and b.get("page_type") in ("spoke", "guide", "product-guide"):
        hub = [u for u in lm["internal"] if urlparse(u).path.rstrip("/") == parent]
        sibs = [u for u in lm["internal"] if urlparse(u).path.rsplit("/", 1)[0] == parent and urlparse(u).path.rstrip("/") != page_path]
        if hub:
            W.append(f"Parent hub (link up to it): {hub[0]}")
        if sibs:
            sib_rank = sorted(sibs, key=lambda u: -len(qtoks & set(re.findall(r"[a-z0-9]+", urlparse(u).path.lower()))))
            W.append(f"Sibling pages ({len(sibs)} in total; the {min(15, len(sibs))} closest to this topic, link the few "
                     "that matter to this reader): " + ", ".join(sib_rank[:15]))
    # a page shares more than one word with the query, not just the site's general subject ("dog" on a dog site)
    if related and len(qtoks) >= 2:
        site_df = {}
        for u in lm["internal"]:
            for w in set(re.findall(r"[a-z0-9]+", urlparse(u).path.lower())):
                site_df[w] = site_df.get(w, 0) + 1
        generic = {w for w, c in site_df.items() if len(lm["internal"]) >= 20 and c / len(lm["internal"]) > 0.1}
        related = [u for u in related if len((qtoks - generic) & set(re.findall(r"[a-z0-9]+", urlparse(u).path.lower()))) >= 1
                   and len(qtoks & set(re.findall(r"[a-z0-9]+", urlparse(u).path.lower()))) >= 2]
    if related:
        W.append("Client pages about the same entity: " + ", ".join(related[:15]))
    internal = [u for u in lm["internal"] if urlparse(u).path.count("/") <= 2 and not u.endswith((".md", ".xml", ".txt"))]
    # A big family of pages (every country, every product) is noise here; name the family, list only the related ones.
    fam = {}
    for u in internal:
        fam.setdefault(urlparse(u).path.rstrip("/").rsplit("/", 1)[0], []).append(u)
    big = {p: us for p, us in fam.items() if p and len(us) > 12}
    internal = [u for u in internal if urlparse(u).path.rstrip("/").rsplit("/", 1)[0] not in big]
    if internal:
        W.append("Other site pages: " + ", ".join(internal[:30]))
    for p, us in big.items():
        W.append(f"Plus {len(us)} pages under {p}/ (link one only when it is about this page's entity)")
    pend = [f for f in sheet["facts"] if f["status"] == "pending"]
    if pend:
        W += ["", "## Pending: verify in step 2 or write around (do not state unless verified)"]
        W += [f"- `{f['id']}` {f.get('claim')}: \"{f['value']}\" — {f['source_url']} ({f['reason']})" for f in pend]
    other = [g for g in sheet["gaps"] if g["id"] not in {f["id"] for f in pend}]
    if other:
        W += ["", "## Not verified: write around these, do not state them"]
        W += [f"- {g['id']}: {g.get('claim')} ({g['reason']})" for g in other]
    if b.get("author"):
        W += ["", f"Byline: add `author: {b['author']}` to the front matter."]
    W += ["", "## Decisions already made (follow them; never ask the operator)"]
    W += [f"- {q}" for q in sheet["decisions"]] or ["- none"]
    (rd / "writer_pack.md").write_text("\n".join(W) + "\n", encoding="utf-8")


def print_summary(rd: Path, sheet: dict, lm: dict, secs: float) -> None:
    facts = sheet["facts"]
    cnt = {}
    for f in facts:
        cnt[f["status"]] = cnt.get(f["status"], 0) + 1
    pg = sheet["page"]
    print(f"RUN {rd.resolve().as_posix()}  ({secs:.1f}s)")
    print(f"page: {pg['status']} {pg['state']}  H1: {pg['h1']!r}  H2s: {len(pg['h2'])}")
    if sheet["products"]:
        nd = sum(1 for p in sheet["products"] if p["dims"])
        print(f"products: {len(sheet['products'])} (with dimensions: {nd})")
        for p in sheet["products"]:
            d = fmt_dims(p["dims"]["cm"]) if p["dims"] else "no dims"
            print(f"  - {p['display_name']} | {p['url']} [{p['page_status']}] | {d}")
    print("facts: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    for b in sheet["blocked_sources"]:
        print(f"  blocked: {b['url']} ({b['status']} {b['state']}){' - captured text used' if b['captured'] else ''}")
    for name, res in sheet["checks"].items():
        print(f"check {name}: " + (res.get("summary") or res.get("error") or "done"))
    print(f"links: {len(lm['products'])} products, {len(lm['children'])} children, {len(lm['internal'])} internal, {len(lm['official'])} official")
    if sheet["gaps"]:
        print("gaps (write around unless step 2 finds them):")
        for g in sheet["gaps"]:
            print(f"  - {g['id']}: {g['reason']}{' (optional)' if g.get('optional') else ''}")
    print(f"decisions logged: {len(sheet['decisions'])}")
    seo = (C.ROOT / "scripts" / "seo.py").as_posix()
    print(f"next: read {(rd / 'writer_pack.md').resolve().as_posix()}, write {(rd / 'draft.md').resolve().as_posix()}, "
          f"then `python \"{seo}\" lint \"{rd.resolve().as_posix()}\"`")


# ---------------------------------------------------------------- add-fact

def add_facts(brief_path: str, file: str) -> list[dict]:
    """Add many facts in one call: a YAML or JSON list of {id, claim, value, url, scope?, source_text_file?}. One
    process and one writer-pack rebuild for the whole batch, instead of a Python start and a rebuild per fact."""
    items = C.load_yaml(Path(file))
    if isinstance(items, dict):
        items = items.get("facts")
    if not isinstance(items, list) or not items:
        raise ValueError("facts file must contain a non-empty list (or a facts: list)")
    brief = load_brief(brief_path)
    rd = latest_run(brief)
    out, valid, seen = [], [], set()
    for it in items or []:
        if not isinstance(it, dict):
            it = {}
        missing = [k for k in ("id", "claim", "value", "url") if not str(it.get(k) or "").strip()]
        fid = str(it.get("id") or "?")
        if missing or fid in seen:
            reason = "missing " + ", ".join(missing) if missing else "duplicate id in batch"
            out.append({"id": fid, "status": "invalid", "reason": reason})
            print(f"{fid}: invalid - {reason}")
            continue
        seen.add(fid)
        valid.append(it)
    mark(rd, "facts", "start")
    try:
        # Fetch each source once, concurrently. Verification still checks every claim and condition.
        reqs = [{"url": u, "kind": "official", "parse": "html"}
                for u in dict.fromkeys(C.clean_url(str(it["url"])) for it in valid)]
        pages = C.run_async(C.fetch_many(reqs)) if reqs else {}
        records = []
        for it in valid:
            url = C.clean_url(str(it["url"]))
            f, res = _verify_fact(str(it["id"]), str(it["claim"]), str(it["value"]), url,
                                  it.get("source_text_file"), it.get("scope"), pages.get(url))
            records.append((f, res))
            out.append(f)
            print(f"{f['id']}: {f['status']}" + (f" - {f['reason']}" if f.get("reason") else ""))
        if records:
            _record_facts(brief, rd, records)
    finally:
        mark(rd, "facts", "end")
    ok = sum(1 for f in out if f["status"] in USABLE)
    print(f"{ok} of {len(out)} facts verified" + (f"; fix and re-add the {len(out) - ok} rejected (reasons above)"
                                                  if ok < len(out) else ""))
    return out


def add_fact(brief_path: str, fid: str, claim: str, value: str, url: str,
             source_text_file: str | None = None, persist: bool = True, scope: str | None = None,
             rebuild: bool = True) -> dict:
    """Add one fact found during step 2. Re-verifies the value against the
    source page (fetched, or text the agent captured when scripts are blocked)."""
    brief = load_brief(brief_path)
    rd = latest_run(brief)
    mark(rd, "verify", "event")
    f, res = _verify_fact(fid, claim, value, url, source_text_file, scope)
    _record_facts(brief, rd, [(f, res)], rebuild, persist)
    print(f"{fid}: {f['status']}" + (f" - {f.get('reason')}" if f.get("reason") else ""))
    return f


def _verify_fact(fid: str, claim: str, value: str, url: str, source_text_file: str | None = None,
                 scope: str | None = None, res: dict | None = None) -> tuple[dict, dict | None]:
    # tracking parameters are not part of the page: cite the clean address
    url = C.clean_url(url)
    if source_text_file:
        capture(url, source_text_file)
    if res is None:
        res = C.run_async(C.fetch_many([{"url": url, "kind": "official", "parse": "html"}])).get(url)
    if (res or {}).get("final_url") and C.clean_url(res["final_url"]).rstrip("/") != url.rstrip("/") \
            and res.get("state") == "ok":
        # link the page where the fact lives, not the address that redirects to it (minus any tracking the redirect adds)
        url = C.clean_url(res["final_url"])
    if url.lower().split("?")[0].endswith(".pdf") or (res or {}).get("state") in ("not_html", "needs_js", None) and \
            url.lower().split("?")[0].endswith(".pdf"):
        txt = pdf_text(url)
        if txt:
            res = {"state": "ok", "text": txt, "fetched_at": C.now_iso(), "status": 200}
    # a list item copied with its marker ("- Contact management", "3. Click Save"): the marker is not page text
    value = re.sub(r"^\s*(?:[-*•▪◦–]|\d{1,2}[.)])\s+", "", value)
    f = fact_from_source({"id": fid, "claim": claim, "value": value}, url, res)
    if f["status"] == "not_found" and (res or {}).get("state") == "ok":
        # the full-page text inlines tooltip popups mid-sentence ("If the pH <definition…> of your soil"); the reading
        # text (what `seo.py read` shows) drops them, so a value copied from it is checked against that text too
        doc = C.run_async(C.fetch_many([{"url": url, "kind": "page", "parse": "doc"}])).get(url) or {}
        if doc.get("text"):
            f2 = fact_from_source({"id": fid, "claim": claim, "value": value}, url, {**res, "text": doc["text"]})
            if f2["status"] in USABLE:
                f, res = f2, {**res, "text": res.get("text", "") + "\n" + doc["text"]}
    if scope:
        f["scope"] = scope.strip()
    v0 = value.strip()
    if f["status"] in USABLE and BACKREF_VALUE.search(v0):
        f.update(status="not_found", verified=False,
                 reason="the value starts mid-sentence or points back to a case it doesn't include (\"if this is the "
                        "case\", \"do this\"): copy the whole passage, including the sentence that says when the rule applies")
    if f["status"] in USABLE:
        body = (res or {}).get("text", "") if (res or {}).get("state") == "ok" else (C.captured_text(url) or "")
        missing = [n for n in re.findall(r"\d+(?:[.,]\d+)?", claim)
                   if n not in re.findall(r"\d+(?:[.,]\d+)?", body + " " + value)]
        if missing:
            f.update(status="not_found", verified=False,
                     reason=f"the claim's number(s) {', '.join(missing)} are not on the page; every number you write "
                            "must be on the source")
        elif len(value.split()) < 4 and body:
            # "Protein 50 g" matches almost any nutrition page: a short value must sit next to the claim's own words
            flat = re.sub(r"\s+", " ", body.lower())
            i = flat.find(re.sub(r"\s+", " ", value.lower().strip()))
            win = flat[max(0, i - 300): i + 300] if i >= 0 else ""
            cw = {w for w in re.findall(r"[a-z]{4,}", claim.lower())} - {"about", "this", "that", "with", "from", "page",
                                                                         "says", "each", "your", "their", "which"}
            if cw and sum(1 for w in cw if w in win) < max(1, len(cw) // 2):
                f.update(status="not_found", verified=False,
                         reason="the value is too short to prove the claim on its own: give the whole sentence or "
                                "table row it appears in as the value")
    return f, res


def _record_facts(brief: dict, rd: Path, records: list[tuple[dict, dict | None]],
                  rebuild: bool = True, persist: bool = True) -> None:
    with C.file_lock(rd / "fact_sheet.json"):
        sheet = C.load_json(rd / "fact_sheet.json")
        keep_decisions = [d for d in sheet.get("decisions", []) if d not in decisions(sheet, brief)]
        ids = {f["id"] for f, _ in records}
        sheet["facts"] = [x for x in sheet["facts"] if x["id"] not in ids] + [f for f, _ in records]
        sheet["checks"] = run_checks(sheet, brief)
        sheet["gaps"] = gaps(sheet, brief)
        sheet["decisions"] = decisions(sheet, brief) + keep_decisions
        C.save_json(rd / "fact_sheet.json", sheet)
        lm = C.load_json(rd / "link_map.json")
        known = {o["url"] for o in lm.setdefault("official", [])}
        for f, res in records:
            url = f["source_url"]
            if url not in known:
                lm["official"].append({"url": url, "state": (res or {}).get("state"), "status": (res or {}).get("status"),
                                       "captured": bool(C.captured_text(url)), "label": ((res or {}).get("title") or "")[:60]})
                known.add(url)
        C.save_json(rd / "link_map.json", lm)
        if not rebuild:
            pass  # a batch rebuilds the pack once at the end
        elif (rd / "research").exists():
            from .pack import research_pack
            research_pack(rd)
        else:
            writer_pack(rd, sheet, lm)
        if persist:
            _persist_extras(brief, [f for f, _ in records if f["status"] in USABLE])


def _persist_extra(brief: dict, f: dict) -> None:
    _persist_extras(brief, [f])


def _persist_extras(brief: dict, facts: list[dict]) -> None:
    """Persist a batch once; replacing an id also replaces its old scope and evidence."""
    if not facts:
        return
    p = Path(brief["_path"])
    with C.file_lock(p):
        data = C.load_yaml(p)
        ids = {f["id"] for f in facts}
        data["extra_facts"] = [f for f in data.get("extra_facts") or [] if f.get("id") not in ids]
        data["extra_facts"] += [{k: f[k] for k in ("id", "claim", "value", "scope", "source_url") if k in f}
                                for f in facts]
        p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def pdf_text(url: str) -> str:
    """Text of a PDF source (official guidance often lives in PDFs). Uses pypdf when installed, else pdftotext."""
    import subprocess
    import tempfile
    try:
        import httpx
        r = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (asdivigitals-seo)"})
        if r.status_code != 200:
            return ""
        data = r.content
    except Exception:
        return ""
    try:
        import io
        from pypdf import PdfReader
        return " ".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages)
    except Exception:
        pass
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data)
        out = subprocess.run(["pdftotext", "-layout", fh.name, "-"], capture_output=True, timeout=60)
        return out.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def capture(url: str, text_file: str) -> None:
    """Store page text the agent read with its own browser/fetch tool, for a
    source that blocks scripts. Prep verifies values against it."""
    cp = C.captured_path(url)
    cp.parent.mkdir(parents=True, exist_ok=True)
    raw = Path(text_file).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            body = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    cp.write_text(f"[captured {C.now_iso()} from {url}]\n" + body, encoding="utf-8")
    print(f"captured {len(cp.read_text(encoding='utf-8'))} chars for {url}")
