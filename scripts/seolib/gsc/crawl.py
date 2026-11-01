"""Crawl Stats and robots.txt (U-D, CR1-CR12): crawl-waste classification, Google-style robots.txt testing and
safe rule proposals.

Crawl Stats is UI-only (root properties, 90 days, counts requests not URLs): the user pastes or exports it and it is
ingested as `ui_crawl_stats`. Rules this module enforces, from Google's docs and the practitioners in the research:
- "Other file type" includes redirects (and fonts, RSC payloads): classify the example URLs before blaming rendering.
- Never block what rendering needs (`/_next/static/`, CSS, JS, fonts, images used on pages).
- A Disallow is proposed only for a cluster that is neither needed for rendering nor earning Search impressions,
  and only after testing it against the site's important URLs. Every robots.txt change needs the user's approval.
- Next.js `_rsc`: noindex on the `RSC: 1` request header and `prefetch={false}` on big link grids first; robots
  Disallow last (it can leave "Indexed, though blocked by robots.txt").
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

# id, URL regex, label, needed for rendering (True/False/None=test it), what to do, robots rule (None = never block)
WASTE = [
    ("rsc", r"[?&]_rsc=", "Next.js React Server Component payloads (prefetch)", False,
     "noindex via `X-Robots-Tag` only when the request has the `RSC: 1` header (a query-only rule also noindexes the "
     "HTML), `prefetch={false}` on large link grids, keep `_rsc` out of sitemaps/canonicals/links, vary the CDN cache "
     "on the RSC header; only then robots", ["Disallow: /*?_rsc=", "Disallow: /*&_rsc="]),
    ("next_static", r"/_next/static/", "Next.js JS/CSS chunks", True,
     "never block: Googlebot needs them to render. Reduce chunk count; enable deploy skew protection (soft 404s on "
     "valid pages come from version skew)", None),
    ("next_image", r"/_next/image\?", "Next.js image optimiser", True,
     "don't block if the images matter for image search or rendering; cache them long", None),
    ("next_data", r"/_next/data/", "Next.js data JSON (pages router)", None,
     "test before touching: client navigation uses it; no published Google guidance", None),
    ("og_image", r"/(opengraph-image|twitter-image|apple-icon|icon)(-[\w]+)?(\.\w+)?(\?|$)", "Open Graph / icon image routes", False,
     "serve stable URLs without query permutations; block only if they aren't needed in image search (social "
     "scrapers ignore Googlebot rules)", ["Disallow: /*opengraph-image*?", "Disallow: /*twitter-image*?"]),
    ("search", r"[?&](s|q|query|search|keyword|k)=|/search(/|\?|$)", "internal site search", False,
     "remove crawlable links to search results; block the search path", ["Disallow: /search", "Disallow: /*?s=", "Disallow: /*?q="]),
    ("facet", r"[?&](filter[^=&]*|colou?r|size|brand|price|min_price|max_price|attr[^=&]*|f|pa_[^=&]+)=", "faceted navigation filters", False,
     "Google: about half of all crawl problems. Block the filter parameters, return 404 for empty or invalid "
     "combinations, keep filter links out of the crawlable HTML where possible",
     ["Disallow: /*?*filter", "Disallow: /*?*price=", "Disallow: /*?*colour=", "Disallow: /*?*color="]),
    ("sort", r"[?&](sort|sort_by|orderby|order|dir|view|layout|per_page|limit|display)=", "sort/view parameters", False,
     "block named parameters; canonical to the unsorted page", ["Disallow: /*?*sort", "Disallow: /*?*orderby=", "Disallow: /*?*view="]),
    ("action", r"[?&](add-to-cart|add_to_cart|add-to-wishlist|wishlist|compare|action|replytocom|share)=", "action URLs", False,
     "Gary Illyes: block action URLs in robots.txt (about a quarter of crawl problems)",
     ["Disallow: /*?*add-to-cart=", "Disallow: /*?*add_to_cart=", "Disallow: /*?*replytocom="]),
    ("tracking", r"[?&](utm_[a-z]+|gclid|fbclid|msclkid|sessionid|sid|phpsessid|_ga|mc_cid|mc_eid)=", "tracking/session parameters", False,
     "fix the source: internal links must never carry these; canonical to the clean URL", None),
    ("wp_feed", r"/feed/?$|/comments/feed|[?&]feed=", "WordPress feeds", False,
     "low value; block comment feeds, keep the main feed if anything discovers posts through it", ["Disallow: /comments/feed/"]),
    ("wp_json", r"/wp-json/", "WordPress REST API", None, "test first: some themes render from it", None),
    ("calendar", r"[?&](date|month|year|day|calendar|ical)=|/(calendar|events?)/\d{4}/\d{1,2}", "calendar traps", False,
     "infinite date URLs: block them and cap the range linked", ["Disallow: /*?*ical=", "Disallow: /*?*month="]),
    ("pagination", r"[?&](page|p|pg|paged)=\d+|/page/\d+", "pagination", True,
     "keep crawlable (discovery); only a problem when it is infinite or empty past the last page (return 404 there)", None),
    ("variant", r"[?&]variant=", "Shopify product variants", False, "canonical handles it; leave unless it dominates", None),
    ("cache_bust", r"\.(js|css|mjs)\?(v|ver|version|cb|t|_)=", "cache-busting asset versions", True,
     "never block; stabilise version strings so each deploy doesn't create new URLs", None),
    ("font", r"\.(woff2?|ttf|otf|eot)(\?|$)", "web fonts", True, "normal resource; never block, trim weights", None),
    ("nuxt", r"/_nuxt/|/_payload\.json", "Nuxt assets/payloads", None, "assets are needed; test payload blocking first", None),
    ("api_json", r"/api/|\.json(\?|$)", "API / JSON fetches", None,
     "a client-side data dependency: if pages need it to show content, raise server rendering with the site owner", None),
    ("image", r"\.(png|jpe?g|gif|webp|avif|svg|ico)(\?|$)", "images", True, "normal", None),
    ("script_css", r"\.(css|js|mjs)(\?|$)", "CSS/JS", True, "needed for rendering; never block", None),
]
WASTE_RE = [(w[0], re.compile(w[1], re.I)) for w in WASTE]
WASTE_BY = {w[0]: w for w in WASTE}
NUM = r"([\d.,]+\s*[KkMm]?)"


def classify(url: str) -> str:
    for wid, rx in WASTE_RE:
        if rx.search(url):
            return wid
    return "page"


def _num(s: str) -> float:
    s = s.replace(",", "").strip()
    mult = 1000 if s[-1:] in "Kk" else 1_000_000 if s[-1:] in "Mm" else 1
    return float(s.rstrip("KkMm ").strip() or 0) * mult


def parse_export(source: str | Path) -> dict:
    """Crawl Stats as pasted text, a CSV/TSV export, or a folder of exported CSVs: headline numbers, every
    'label NN%' breakdown line, and the example URLs (with any status/type/date columns)."""
    p = Path(str(source)) if len(str(source)) < 400 else None
    texts = []
    if p and p.is_dir():
        texts = [f.read_text(encoding="utf-8-sig", errors="replace") for f in sorted(p.glob("*.csv")) + sorted(p.glob("*.txt"))]
    elif p and p.is_file():
        texts = [p.read_text(encoding="utf-8-sig", errors="replace")]
    else:
        texts = [str(source)]
    summary, shares, urls = {}, {}, []
    for text in texts:
        for label, key in (("total crawl requests", "requests"), ("total download size", "download_size"),
                           ("average response time", "response_ms")):
            m = re.search(label + r"\D{0,20}" + NUM, text, re.I)
            if m:
                summary[key] = _num(m.group(1))
        for m in re.finditer(r"^[ \t]*([A-Za-z][^\t\n%]{1,60}?)[ \t,:]+([\d.]+)\s*%", text, re.M):
            shares[" ".join(m.group(1).split())] = float(m.group(2))
        if "," in text or "\t" in text:
            dialect = "excel-tab" if text.count("\t") > text.count(",") else "excel"
            for row in csv.reader(io.StringIO(text), dialect=dialect):
                u = next((c for c in row if re.match(r"https?://", c.strip())), None)
                if u:
                    rest = [c.strip() for c in row if c.strip() and c.strip() != u.strip()]
                    urls.append({"url": u.strip(), "cols": rest})
        else:
            urls += [{"url": u, "cols": []} for u in re.findall(r"https?://[^\s\"'<>]+", text)]
    seen, uniq = set(), []
    for u in urls:
        if u["url"] not in seen:
            seen.add(u["url"])
            uniq.append(u)
    return {"summary": summary, "shares": shares, "urls": uniq}


def analyse(export: dict, impressions_by_url: dict[str, int] | None = None, important: list[str] | None = None,
            robots_text: str | None = None) -> dict:
    """U-D: headline checks, the 'Other' file type explained by its examples, by-response problems, the crawl-waste
    clusters, and robots.txt proposals tested against the important URLs."""
    from . import analyze as A
    imp = {A.norm(k): v for k, v in (impressions_by_url or {}).items()}
    s, sh = export.get("summary") or {}, {k.lower(): v for k, v in (export.get("shares") or {}).items()}
    notes = []
    ms = s.get("response_ms")
    if ms:
        if ms > 600:
            notes.append(f"Average response time {int(ms)} ms: above Barry Adams' 600 ms ceiling (200 ms ideal). Slow "
                         "responses lower Google's crawl rate: caching, CDN, server capacity.")
        elif ms > 200:
            notes.append(f"Average response time {int(ms)} ms: acceptable (Adams: 200 ms ideal; Koray reportedly aims under 100 ms).")
    other = next((v for k, v in sh.items() if k.startswith("other file type") or k == "other"), None)
    html = next((v for k, v in sh.items() if k == "html"), None)
    clusters: dict = defaultdict(list)
    for u in export.get("urls") or []:
        clusters[classify(u["url"])].append(u["url"])
    if other is not None and html is not None and other > html:
        kinds = Counter(classify(u) for u in sum(clusters.values(), []))
        notes.append(f"'Other file type' ({other}%) outranks HTML ({html}%). Google counts redirects as Other, so the "
                     "examples decide: " + (", ".join(f"{WASTE_BY[k][2] if k in WASTE_BY else k} {n}" for k, n in kinds.most_common(5))
                                           or "no example URLs were given: export the 'Other file type' examples")
                     + ". Only JSON/API examples point to client-side rendering worth raising with the site owner.")
    for label, cap, why in (("moved permanently (301)", 10, "update internal links, canonicals, sitemaps and hreflang to the final URLs; collapse chains"),
                            ("found (302)", 5, "302s for permanent moves should be 301s"),
                            ("not found (404)", 10, "fix only the 404s that are linked internally or listed in sitemaps; expected 404s are fine"),
                            ("server error (5xx)", 1, "capacity: any sustained 5xx lowers crawling; 503 only for short maintenance"),
                            ("robots.txt not available", 0.1, "serve robots.txt as a static file exempt from WAF and rate limits"),
                            ("page could not be reached", 1, "timeouts/connectivity: check hosting and the WAF"),
                            ("page timeout", 1, "slow pages: server performance")):
        v = next((x for k, x in sh.items() if label in k), None)
        if v is not None and v >= cap:
            notes.append(f"{label}: {v}% of requests [threshold {cap}% synth] → {why}.")
    disc = next((v for k, v in sh.items() if k == "discovery"), None)
    if disc is not None and disc > 10:
        notes.append(f"Discovery is {disc}% of requests. Adams flags >10% for established publishers; a growing site "
                     "runs higher legitimately. Open the Discovery examples: parameters, _rsc, calendars or hacked "
                     "sections mean waste.")
    smart = next((v for k, v in sh.items() if "smartphone" in k), None)
    if smart is not None and smart < 50:
        notes.append(f"Smartphone Googlebot is only {smart}% of requests: mobile-first sites should be dominated by it.")
    found = []
    for wid, urls in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        if wid == "page":
            continue
        w = WASTE_BY[wid]
        earning = [u for u in urls if imp.get(A.norm(u), 0) > 0]
        found.append({"cluster": wid, "label": w[2], "examples": urls[:5], "count": len(urls),
                      "needed_for_render": w[3], "earning_impressions": len(earning), "action": w[4],
                      "robots_rules": w[5] if (w[3] is False and not earning) else None})
    proposals = [r for f in found if f["robots_rules"] for r in f["robots_rules"]]
    test = test_rules(robots_text or "", proposals, important or []) if proposals else None
    return {"summary": s, "shares": export.get("shares"), "notes": notes, "clusters": found,
            "robots_proposal": proposals, "robots_test": test,
            "approval": "Every robots.txt change needs the user's approval: show the diff and the test, never deploy it."}


# ---------------------------------------------------------------- robots.txt, Google's way (RFC 9309)

def parse_robots(text: str) -> dict:
    groups, cur, last_was_agent, sitemaps = [], None, False, []
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if not last_was_agent:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(v.lower())
            last_was_agent = True
            continue
        last_was_agent = False
        if k == "sitemap":
            sitemaps.append(v)
        elif k in ("allow", "disallow") and cur is not None and v:
            cur["rules"].append((k == "allow", v))
    return {"groups": groups, "sitemaps": sitemaps}


def rules_for(parsed: dict, agent: str = "googlebot") -> list[tuple[bool, str]]:
    """Google: the most specific matching user-agent group(s) apply (groups for the same agent merge); `*` only
    when no group names the crawler. A `Googlebot` group therefore replaces `*` for Googlebot entirely."""
    agent = agent.lower()
    best, rules = "", []
    for g in parsed["groups"]:
        for a in g["agents"]:
            if a != "*" and agent.startswith(a) and len(a) > len(best):
                best = a
    for g in parsed["groups"]:
        if (best and best in g["agents"]) or (not best and "*" in g["agents"]):
            rules += g["rules"]
    return rules


def _rx(pattern: str) -> re.Pattern:
    end = pattern.endswith("$")
    body = re.escape(pattern[:-1] if end else pattern).replace(r"\*", ".*")
    return re.compile("^" + body + ("$" if end else ""))


def allowed(parsed: dict, url: str, agent: str = "googlebot") -> tuple[bool, str | None]:
    """Longest matching rule wins; on a tie, Allow wins. (True, None) when nothing matches."""
    u = urlparse(url)
    target = (u.path or "/") + (f"?{u.query}" if u.query else "")
    best: tuple[int, bool, str] | None = None
    for allow, pat in rules_for(parsed, agent):
        if _rx(pat).match(target):
            cand = (len(pat), allow, pat)
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and allow and not best[1]):
                best = cand
    return (True, None) if best is None else (best[1], ("Allow: " if best[1] else "Disallow: ") + best[2])


def test_rules(current: str, new_rules: list[str], important: list[str], agent: str = "googlebot") -> dict:
    """Add the proposed rules to every group that applies to Googlebot and check the important URLs: a proposal
    that blocks any of them is rejected."""
    parsed = parse_robots(current or "User-agent: *\n")
    if not any(rules_for(parsed, agent)) and not parsed["groups"]:
        parsed = parse_robots("User-agent: *\n")
    agent_groups = [g for g in parsed["groups"] if any(a != "*" and agent.startswith(a) for a in g["agents"])] or \
        [g for g in parsed["groups"] if "*" in g["agents"]]
    if not agent_groups:
        parsed["groups"].append({"agents": ["*"], "rules": []})
        agent_groups = parsed["groups"][-1:]
    for g in agent_groups:
        for r in new_rules:
            k, v = (x.strip() for x in r.split(":", 1))
            g["rules"].append((k.lower() == "allow", v))
    blocked = []
    for u in important:
        ok, rule = allowed(parsed, u, agent)
        if not ok:
            blocked.append({"url": u, "rule": rule})
    return {"rules": new_rules, "important_tested": len(important), "would_block": blocked,
            "verdict": "safe for the tested URLs" if not blocked else "REJECTED: it blocks important URLs"}


def fetch_robots(domain: str) -> dict:
    """Live robots.txt for the https host (and its www/non-www twin when the first fails)."""
    import httpx
    from .. import common as C
    host = domain.removeprefix("https://").removeprefix("http://").strip("/")
    out = {}
    for h in dict.fromkeys([host, host.removeprefix("www.") if host.startswith("www.") else "www." + host]):
        try:
            r = httpx.get(f"https://{h}/robots.txt", headers=C.HEADERS, timeout=15, follow_redirects=True)
            out = {"host": h, "status": r.status_code, "text": r.text if r.status_code == 200 else "",
                   "content_type": r.headers.get("content-type", ""), "final_url": str(r.url)}
            if r.status_code == 200:
                break
        except Exception as e:
            out = {"host": h, "status": 0, "error": f"{type(e).__name__}: {e}", "text": ""}
    if out.get("status") == 200 and "html" in out.get("content_type", "") and "<html" in out.get("text", "")[:500].lower():
        out["problem"] = "robots.txt answers with an HTML page (200): Google may misread it; serve plain text"
    elif out.get("status", 0) >= 500 or out.get("status") == 429:
        out["problem"] = "robots.txt answers 5xx/429: Google halts crawling for 12 hours, then uses a cached copy up to 30 days"
    return out
