"""Performance-report playbooks as pure functions over Search Console rows.

Rows are flat dicts: the dimensions by name (query, page, device, country, date, searchAppearance, hour) plus
clicks, impressions, ctr (0-1) and position. Playbook ids match the research report (docs/gsc_research):
U-B page optimiser, U-C question mining, PF1 striking distance, PF2 CTR deficit, PF3 zero-click, PF4 conversational,
PF5 site: queries, PF6 emerging, PF7 page-query alignment, PF8 intent mix, PF9 cannibalisation, PF10 decay,
PF15 device gap, PF16 country gap, PF17 appearance, PF22 brand split, PF27 topical coverage (Koray), PF29 anonymised
gap, AI2 decoupling. Thresholds marked [synth] are tunable defaults, not anyone's published rule.
"""
from __future__ import annotations

import re
from collections import defaultdict
from statistics import median
from urllib.parse import urlparse

from . import regexlib as RX

# Used only when the site has too little data for its own curve. Deliberately lower than pre-2024 industry curves:
# AI Overviews cut position-1 CTR by about 58% on the keywords that show one (Ahrefs, Dec 2025). [synth]
FALLBACK_CURVE = {1: 0.20, 2: 0.11, 3: 0.075, 4: 0.055, 5: 0.042, 6: 0.032, 7: 0.026, 8: 0.021, 9: 0.018, 10: 0.016}


def norm(u: str) -> str:
    u = (u or "").split("#")[0]
    p = urlparse(u)
    host = (p.netloc or "").lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/') or '/'}" + (f"?{p.query}" if p.query else "")


def wpos(rows: list[dict]) -> float:
    imp = sum(r.get("impressions", 0) for r in rows)
    if not imp:
        return round(sum(r.get("position", 0) for r in rows) / max(1, len(rows)), 1)
    return round(sum(r.get("position", 0) * r.get("impressions", 0) for r in rows) / imp, 1)


def agg(rows: list[dict], *keys: str) -> list[dict]:
    """Sum rows by `keys`, with impression-weighted position and recomputed CTR."""
    groups: dict = defaultdict(list)
    for r in rows:
        groups[tuple(r.get(k) for k in keys)].append(r)
    out = []
    for k, rs in groups.items():
        clicks, imp = sum(r.get("clicks", 0) for r in rs), sum(r.get("impressions", 0) for r in rs)
        out.append({**dict(zip(keys, k)), "clicks": clicks, "impressions": imp,
                    "ctr": round(clicks / imp, 4) if imp else 0.0, "position": wpos(rs)})
    return sorted(out, key=lambda r: -r["impressions"])


def by(rows: list[dict], key: str) -> dict:
    out: dict = defaultdict(list)
    for r in rows:
        out[r.get(key)].append(r)
    return out


def nonbrand(rows: list[dict], brand_re: str | None) -> list[dict]:
    return [r for r in rows if not RX.is_brand(r.get("query", ""), brand_re)] if brand_re else rows


# ---------------------------------------------------------------- PF2 the site's own CTR curve

def ctr_curve(query_rows: list[dict], brand_re: str | None = None, min_queries: int = 5, min_impr: int = 300) -> dict:
    """Non-brand CTR by rounded position 1-10, the impression-weighted median of the site's own queries (Botify's
    method); positions with too little data take the fallback, and the curve never rises with position."""
    rows = [r for r in nonbrand(query_rows, brand_re) if r.get("impressions", 0) >= 10 and 0 < r.get("position", 0) < 10.5]
    buckets: dict = defaultdict(list)
    for r in rows:
        buckets[max(1, round(r["position"]))].append(r)
    curve, source = {}, {}
    for p in range(1, 11):
        rs = buckets.get(p) or []
        if len(rs) >= min_queries and sum(r["impressions"] for r in rs) >= min_impr:
            # weighted median: each query counts by its impressions
            pts = sorted((r["ctr"], r["impressions"]) for r in rs)
            half, acc = sum(w for _, w in pts) / 2, 0
            for c, w in pts:
                acc += w
                if acc >= half:
                    curve[p] = round(c, 4)
                    break
            source[p] = "site"
        else:
            curve[p] = FALLBACK_CURVE[p]
            source[p] = "fallback"
    for p in range(2, 11):  # monotonic: a lower position never expects more clicks
        curve[p] = min(curve[p], curve[p - 1])
    return {"curve": curve, "source": source, "site_points": sum(v == "site" for v in source.values())}


def expected_ctr(curve: dict, position: float) -> float:
    c = curve.get("curve", curve)
    p = max(1, min(10, round(position)))
    return c.get(p) or c.get(str(p)) or FALLBACK_CURVE[p]


def ctr_deficit(rows: list[dict], curve: dict, min_impr: int = 1000, ratio: float = 0.6, max_pos: float = 10.5,
                brand_re: str | None = None) -> list[dict]:
    """PF2 (Neil Patel's high-impression/low-CTR refresh, on the site's own curve): page-1 rows whose CTR is under
    `ratio` x expected, ranked by missed clicks. Titles only: past page 1, position matters first (Quaid)."""
    out = []
    for r in nonbrand(rows, brand_re):
        if r.get("impressions", 0) < min_impr or not (0 < r.get("position", 99) <= max_pos):
            continue
        exp = expected_ctr(curve, r["position"])
        if r["ctr"] < ratio * exp:
            out.append({**r, "expected_ctr": exp, "missed_clicks": round(r["impressions"] * exp - r["clicks"])})
    return sorted(out, key=lambda r: -r["missed_clicks"])


# ---------------------------------------------------------------- PF1 / U-B striking distance and the page optimiser

def striking(qp_rows: list[dict], band: tuple[float, float] = (4, 20), min_impr: int = 100,
             brand_re: str | None = None, dominant: float = 0.8) -> list[dict]:
    """PF1: queries in the position band with enough impressions; one dominant page (>=80% of the query's
    impressions [synth]) gets an on-page fix, several pages go to cannibalisation."""
    out = []
    for q, rs in by(nonbrand(qp_rows, brand_re), "query").items():
        imp = sum(r["impressions"] for r in rs)
        pos = wpos(rs)
        if imp < min_impr or not (band[0] <= pos <= band[1]):
            continue
        pages = sorted(rs, key=lambda r: -r["impressions"])
        share = pages[0]["impressions"] / imp if imp else 0
        out.append({"query": q, "impressions": imp, "clicks": sum(r["clicks"] for r in rs), "position": pos,
                    "page": pages[0].get("page"), "page_share": round(share, 2),
                    "route": "on_page" if share >= dominant else "cannibalisation",
                    "pages": [p.get("page") for p in pages[:3]]})
    return sorted(out, key=lambda r: -r["impressions"])


def classify_query(r: dict, band_hi: float = 20) -> str:
    q = r.get("query", "")
    if RX.QUESTION.search(q):
        return "question"
    if r.get("position", 99) <= band_hi:
        return "ranking"
    if r.get("position", 99) <= 50:
        return "should_rank"
    return "other"


def page_queries(rows: list[dict], band_hi: float = 20, min_impr: int = 20) -> dict:
    """U-B step 2 for one page: its queries bucketed as ranking (<= band), should-rank (band-50), question,
    with modifiers (words the queries add to the page's head terms)."""
    out = {"ranking": [], "should_rank": [], "question": []}
    for r in sorted(rows, key=lambda r: -r.get("impressions", 0)):
        if r.get("impressions", 0) < min_impr:
            continue
        k = classify_query(r, band_hi)
        if k in out:
            out[k].append(r)
    return out


def anonymised_share(page_total_clicks: float, query_rows: list[dict]) -> float | None:
    """PF29: share of a page's clicks on queries Search Console never lists."""
    if not page_total_clicks:
        return None
    listed = sum(r.get("clicks", 0) for r in query_rows)
    return round(max(0.0, (page_total_clicks - listed) / page_total_clicks), 2)


def page_optimizer(page_rows: list[dict], qp_rows: list[dict], band_hi: float = 20, min_impr: int = 500,
                   brand_re: str | None = None, limit: int = 50) -> list[dict]:
    """U-B, the user's own workflow: pages with impression-weighted position <= band_hi (20, or 30) and enough
    impressions; for each, the queries it ranks for, should rank for and is asked as questions. Scored by the
    impressions on in-band and should-rank queries (the clicks a better position would unlock)."""
    qp = by(nonbrand(qp_rows, brand_re), "page")
    out = []
    for p in page_rows:
        if p.get("impressions", 0) < min_impr or not (0 < p.get("position", 99) <= band_hi):
            continue
        rows = qp.get(p["page"], [])
        b = page_queries(rows, band_hi)
        score = sum(r["impressions"] for r in b["ranking"] if r["position"] > 3) + \
            sum(r["impressions"] for r in b["should_rank"]) + sum(r["impressions"] for r in b["question"])
        if not score:
            continue
        top = [r["query"] for r in sorted(rows, key=lambda r: -r["impressions"])[:5]]
        out.append({"page": p["page"], "impressions": p["impressions"], "clicks": p["clicks"], "position": p["position"],
                    "score": score, "top_queries": top,
                    "ranking": [_slim(r) for r in b["ranking"][:15]],
                    "should_rank": [_slim(r) for r in b["should_rank"][:15]],
                    "questions": [_slim(r) for r in b["question"][:10]],
                    "anonymised_share": anonymised_share(p.get("clicks", 0), rows)})
    return sorted(out, key=lambda r: -r["score"])[:limit]


def _slim(r: dict) -> dict:
    return {k: r[k] for k in ("query", "page", "clicks", "impressions", "position") if k in r}


# ---------------------------------------------------------------- U-C questions, PF4 conversational, PF5 site:

def questions(qp_rows: list[dict], brand_re: str | None = None, update_band: tuple[float, float] = (5, 30),
              min_impr: int = 10) -> dict:
    """U-C: question queries. Served by a page at positions 5-30 [synth] = content-update candidate (an H2 with the
    exact question and a direct answer); worse or off-intent = new-article candidate."""
    upd, new = [], []
    for q, rs in by(nonbrand(qp_rows, brand_re), "query").items():
        if not RX.QUESTION.search(q or ""):
            continue
        imp = sum(r["impressions"] for r in rs)
        if imp < min_impr:
            continue
        best = min(rs, key=lambda r: r["position"])
        rec = {"query": q, "impressions": imp, "position": wpos(rs), "page": best.get("page"),
               "page_kind": RX.page_kind(best.get("page", ""))}
        if rec["position"] < update_band[0] and rec["page_kind"] != "money":
            continue  # already answered near the top
        (upd if rec["position"] <= update_band[1] and rec["page_kind"] != "money" else new).append(rec)
    return {"update": sorted(upd, key=lambda r: -r["impressions"]), "new": sorted(new, key=lambda r: -r["impressions"])}


def conversational(qp_rows: list[dict]) -> list[dict]:
    """PF4 (Chris Long): 10+ word queries, often AI-Mode style; theme them, don't treat each as a keyword."""
    return agg([r for r in qp_rows if RX.CONVERSATIONAL.search(r.get("query", ""))], "query", "page")


def site_operator(qp_rows: list[dict]) -> list[dict]:
    """PF5: queries containing `site:` (LLM fan-out footprints, Chris Long)."""
    return agg([r for r in qp_rows if "site:" in (r.get("query") or "")], "query", "page")


def zero_click(rows: list[dict], min_impr: int = 1000, max_clicks: int = 5, max_pos: float = 5) -> list[dict]:
    """PF3: lots of impressions, near-zero clicks at a top position: definitional/AI-Overview queries (target the
    citation; impressions are the KPI) or commercial (send to the CTR playbook)."""
    out = []
    for r in rows:
        if r.get("impressions", 0) >= min_impr and r.get("clicks", 0) <= max_clicks and r.get("position", 99) <= max_pos:
            kind = "commercial" if RX.intent(r.get("query", "")) in ("R-TRANS", "R-SERVICE", "R-COMP") else "definitional"
            out.append({**r, "kind": kind})
    return sorted(out, key=lambda r: -r["impressions"])


# ---------------------------------------------------------------- PF6 emerging, PF27 topical coverage

def emerging(cur_qp: list[dict], prev_qp: list[dict], min_impr: int = 50) -> list[dict]:
    """PF6: queries with impressions now and none in the previous window [synth]."""
    before = {r.get("query") for r in prev_qp}
    rows = agg([r for r in cur_qp if r.get("query") not in before], "query")
    return [r for r in rows if r["impressions"] >= min_impr]


def folder(url: str) -> str:
    parts = [p for p in urlparse(url or "").path.split("/") if p]
    return "/" + parts[0] + "/" if len(parts) > 1 else "/"


def topical_coverage(cur_qp: list[dict], prev_qp: list[dict] | None = None) -> list[dict]:
    """PF27 (Koray Tuğberk Gübür): distinct ranking queries per folder by position band, and new queries since the
    previous window. Impressions growing with a flat position = the query network expanding."""
    prev_by = defaultdict(set)
    for r in prev_qp or []:
        prev_by[folder(r.get("page"))].add(r.get("query"))
    out = []
    for f, rs in by([{**r, "folder": folder(r.get("page"))} for r in cur_qp], "folder").items():
        qs = agg(rs, "query")
        bands = {"1-3": 0, "4-10": 0, "11-20": 0, "21-100": 0}
        for q in qs:
            p = q["position"]
            bands["1-3" if p <= 3 else "4-10" if p <= 10 else "11-20" if p <= 20 else "21-100"] += 1
        cur = {q["query"] for q in qs}
        out.append({"folder": f, "queries": len(cur), "bands": bands, "new_queries": len(cur - prev_by[f]) if prev_qp else None,
                    "lost_queries": len(prev_by[f] - cur) if prev_qp else None,
                    "impressions": sum(q["impressions"] for q in qs), "clicks": sum(q["clicks"] for q in qs),
                    "position": wpos(qs)})
    return sorted(out, key=lambda r: -r["impressions"])


# ---------------------------------------------------------------- PF7 alignment, PF8 intent mix, PF22 brand

def alignment(qp_rows: list[dict], min_impr: int = 50) -> list[dict]:
    """PF7: queries landing on the wrong kind of page: commercial queries on a blog post, questions on a
    product/service page. Fix with internal anchors to the right page, strengthening it, de-optimising the wrong one."""
    out = []
    for r in agg(qp_rows, "query", "page"):
        if r["impressions"] < min_impr:
            continue
        kind, intent = RX.page_kind(r["page"]), RX.intent(r["query"])
        if kind == "blog" and intent in ("R-TRANS", "R-SERVICE"):
            out.append({**r, "issue": "commercial query on an informational page", "intent": intent, "page_kind": kind})
        elif kind == "money" and RX.QUESTION.search(r["query"]) and intent in ("R-Q1", "R-INFO", "other"):
            out.append({**r, "issue": "informational question on a commercial page", "intent": intent, "page_kind": kind})
    return out


def intent_mix(query_rows: list[dict], brand_re: str | None = None) -> dict:
    """PF8: impressions and clicks by intent class (regex, not the UI's AI filter: deterministic and API-safe)."""
    out: dict = defaultdict(lambda: {"queries": 0, "impressions": 0, "clicks": 0})
    for r in query_rows:
        k = "brand" if RX.is_brand(r.get("query", ""), brand_re) else RX.intent(r.get("query", ""))
        out[k]["queries"] += 1
        out[k]["impressions"] += r.get("impressions", 0)
        out[k]["clicks"] += r.get("clicks", 0)
    return dict(out)


def brand_split(query_rows: list[dict], brand_re: str | None) -> dict:
    """PF22: brand vs non-brand. Non-brand clicks are the SEO KPI; branded demand rising is, for Koray, the
    strongest pattern of all."""
    b = [r for r in query_rows if RX.is_brand(r.get("query", ""), brand_re)]
    n = [r for r in query_rows if not RX.is_brand(r.get("query", ""), brand_re)]
    tot = lambda rs, k: sum(r.get(k, 0) for r in rs)
    return {"brand": {"clicks": tot(b, "clicks"), "impressions": tot(b, "impressions"), "queries": len(b)},
            "nonbrand": {"clicks": tot(n, "clicks"), "impressions": tot(n, "impressions"), "queries": len(n)},
            "regex": brand_re}


# ---------------------------------------------------------------- PF9 cannibalisation

def cannibalisation(qp_rows: list[dict], min_impr: int = 100, share: float = 0.15, brand_re: str | None = None,
                    home: str | None = None) -> list[dict]:
    """PF9: a query where two or more pages each take >=15% of its impressions [synth], brand, homepage pairs and
    pagination excluded. Suggested action by page kinds: same intent -> merge + 301 or differentiate; blog vs money
    page -> de-optimise the blog and link to the money page. Act only on money queries or flip-flopping
    (Quaid/Sturm: fix it when it matters)."""
    out = []
    home_n = norm(home) if home else None
    for q, rs in by(nonbrand(qp_rows, brand_re), "query").items():
        imp = sum(r["impressions"] for r in rs)
        if imp < min_impr:
            continue
        pages = [r for r in agg(rs, "page") if r["impressions"] / imp >= share
                 and not re.search(r"[?&/]page[=/]\d", r["page"] or "")]
        if home_n:
            pages = [p for p in pages if norm(p["page"]) != home_n]
        if len(pages) < 2:
            continue
        kinds = {RX.page_kind(p["page"]) for p in pages}
        action = ("de-optimise the informational page for this query and link it to the commercial page"
                  if {"blog", "money"} <= kinds else
                  "same intent: merge into the stronger page and 301, or differentiate the angles and remove the shared "
                  "query from the weaker page's title, H1 and H2s")
        money = RX.intent(q) in ("R-TRANS", "R-SERVICE", "R-COMP")
        out.append({"query": q, "impressions": imp, "money_query": money, "pages": [_slim(p) for p in pages[:4]],
                    "keep": min(pages, key=lambda p: p["position"])["page"], "action": action})
    return sorted(out, key=lambda r: (not r["money_query"], -r["impressions"]))


# ---------------------------------------------------------------- PF10 decay, AI2 decoupling, PF15/16 gaps

def _index(rows: list[dict]) -> dict:
    return {norm(r.get("page")): r for r in rows}


def decay(cur: list[dict], prev: list[dict], yoy: list[dict] | None = None, min_prev_clicks: int = 100,
          drop: float = 0.2, metric: str = "clicks") -> list[dict]:
    """PF10: pages losing >=20% clicks against the previous window (and year on year when available) [synth], with
    the likely cause: lost position (competitors or intent), lost CTR at a stable position (SERP feature or AI
    Overview), or lost impressions (demand or indexing)."""
    p_ix, y_ix = _index(prev), _index(yoy or [])
    out = []
    for r in cur:
        k = norm(r.get("page"))
        p = p_ix.get(k)
        if not p or p.get(metric, 0) < min_prev_clicks:
            continue
        ch = (r.get(metric, 0) - p[metric]) / p[metric]
        y = y_ix.get(k)
        ych = (r.get(metric, 0) - y[metric]) / y[metric] if y and y.get(metric) else None
        if ch > -drop or (ych is not None and ych > -drop):
            continue
        dpos = round(r.get("position", 0) - p.get("position", 0), 1)
        dimp = (r.get("impressions", 0) - p.get("impressions", 0)) / p["impressions"] if p.get("impressions") else 0
        cause = ("position loss: compare the live SERP and the competitors now ahead; refresh through the pipeline"
                 if dpos >= 1.5 else
                 "CTR loss at a stable position: a SERP feature or AI Overview took the clicks (check the SERP; title/meta)"
                 if dimp > -drop else "impression loss: demand fell or the page lost queries/indexing (check URL Inspection)")
        out.append({"page": r.get("page"), "clicks": r.get("clicks", 0), "prev_clicks": p.get("clicks", 0),
                    "change": round(ch, 2), "yoy_change": round(ych, 2) if ych is not None else None,
                    "position": r.get("position"), "prev_position": p.get("position"), "position_change": dpos,
                    "cause": cause})
    return sorted(out, key=lambda r: r["clicks"] - r["prev_clicks"])


def decoupling(cur: list[dict], yoy: list[dict], min_impr: int = 500) -> list[dict]:
    """AI2: impressions up, CTR down, position stable or near the top = likely cited in AI Overviews/AI Mode [synth].
    Route to the AI-visibility playbook (add a click reason), not to a title rewrite."""
    y_ix = _index(yoy)
    out = []
    for r in cur:
        y = y_ix.get(norm(r.get("page")))
        if not y or r.get("impressions", 0) < min_impr or not y.get("impressions"):
            continue
        di = (r["impressions"] - y["impressions"]) / y["impressions"]
        dc = (r.get("ctr", 0) - y.get("ctr", 0)) / y["ctr"] if y.get("ctr") else 0
        dpos = r.get("position", 0) - y.get("position", 0)
        if di >= 0.2 and dc <= -0.25 and (dpos <= 1 or r.get("position", 99) <= 3):
            out.append({"page": r["page"], "impressions_change": round(di, 2), "ctr_change": round(dc, 2),
                        "position": r.get("position"), "yoy_position": y.get("position")})
    return sorted(out, key=lambda r: r["ctr_change"])


def device_gap(page_device: list[dict], min_impr: int = 200, pos_gap: float = 3, ctr_ratio: float = 0.7) -> list[dict]:
    """PF15 (mobile-first): mobile position >=3 worse or mobile CTR <70% of desktop [synth]."""
    out = []
    for page, rs in by(page_device, "page").items():
        d = {r.get("device", "").upper(): r for r in rs}
        m, dk = d.get("MOBILE"), d.get("DESKTOP")
        if not m or not dk or m["impressions"] < min_impr or dk["impressions"] < min_impr:
            continue
        if m["position"] - dk["position"] >= pos_gap or (dk["ctr"] and m["ctr"] < ctr_ratio * dk["ctr"]):
            out.append({"page": page, "mobile_position": m["position"], "desktop_position": dk["position"],
                        "mobile_ctr": m["ctr"], "desktop_ctr": dk["ctr"], "mobile_impressions": m["impressions"]})
    return sorted(out, key=lambda r: -r["mobile_impressions"])


def country_gap(page_country: list[dict], target: str, min_share: float = 0.2, pos_gap: float = 5) -> list[dict]:
    """PF16: the target country brings >=20% of a page's impressions but ranks >=5 positions worse than elsewhere [synth]."""
    target = (target or "").lower()
    out = []
    for page, rs in by(page_country, "page").items():
        tot = sum(r["impressions"] for r in rs)
        t = [r for r in rs if (r.get("country") or "").lower() == target]
        rest = [r for r in rs if (r.get("country") or "").lower() != target]
        if not t or not rest or not tot or t[0]["impressions"] / tot < min_share:
            continue
        if t[0]["position"] - wpos(rest) >= pos_gap:
            out.append({"page": page, "country": target, "position": t[0]["position"], "elsewhere": wpos(rest),
                        "share": round(t[0]["impressions"] / tot, 2)})
    return out


def appearance(rows: list[dict]) -> list[dict]:
    """PF17: the search appearances the site earns (FAQ ended May 2026: don't chase it)."""
    return agg(rows, "searchAppearance")


# ---------------------------------------------------------------- trend and momentum

def trend(date_rows: list[dict]) -> dict:
    """Last 28 days vs the 28 before, and the 16-month weekly series (for drop shape: sharp = update/technical,
    yearly = seasonal, gradual = page-level or demand)."""
    rs = sorted(date_rows, key=lambda r: r.get("date", ""))
    if not rs:
        return {}
    last, prev = rs[-28:], rs[-56:-28]
    s = lambda xs, k: sum(r.get(k, 0) for r in xs)
    weeks = [{"week_start": rs[i]["date"], "clicks": s(rs[i:i + 7], "clicks"), "impressions": s(rs[i:i + 7], "impressions")}
             for i in range(0, len(rs), 7)]
    daily_imp = [r.get("impressions", 0) for r in rs[-28:]]
    return {"last_28": {"clicks": s(last, "clicks"), "impressions": s(last, "impressions")},
            "prev_28": {"clicks": s(prev, "clicks"), "impressions": s(prev, "impressions")},
            "clicks_change": round((s(last, "clicks") - s(prev, "clicks")) / s(prev, "clicks"), 2) if s(prev, "clicks") else None,
            "median_daily_impressions": median(daily_imp) if daily_imp else 0,
            "weeks": weeks, "from": rs[0]["date"], "to": rs[-1]["date"]}


def page_rows_for(qp_rows: list[dict], url: str) -> list[dict]:
    k = norm(url)
    return [r for r in qp_rows if norm(r.get("page")) == k]


def topic_rows(qp_rows: list[dict], words: set[str], min_overlap: int = 1) -> list[dict]:
    """Rows whose query shares the topic's content words (for 'which client pages already rank for this topic')."""
    out = []
    for r in qp_rows:
        qw = set(re.findall(r"[a-z0-9]+", (r.get("query") or "").lower()))
        if len(qw & words) >= min_overlap:
            out.append(r)
    return out
