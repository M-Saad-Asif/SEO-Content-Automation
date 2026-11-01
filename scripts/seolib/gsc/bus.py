"""The Search Console data bus: one object every plugin, script and agent asks for Search Console data.

    from seolib.gsc.bus import Console, for_brief
    gsc = for_brief(brief)              # None when the client has no stored Search Console data
    gsc.page(url)                       # queries, striking, questions, should-rank, CTR deficit, index state, decay
    gsc.topic("fence paint")            # client pages already ranking for the topic (link targets, cannibal risk)
    gsc.link_sources(url, "fence paint")# trafficked client pages that should link INTO this page
    gsc.query("how to paint a fence")   # every client page Google shows for that query
    gsc.view("striking")                # any site-level playbook by name (see VIEWS)

Agents use the same views from the command line: `seo.py gsc data <client> <view> [--page URL] [--query Q]
[--topic T] [--json]`. Everything reads the per-site store (sites/<slug>/gsc), however it was filled.
"""
from __future__ import annotations

import re
from functools import cached_property

from . import analyze as A, caveats as CV, indexing as IX, regexlib as RX, store as S

STOP = set("a an the and or of to in on for with by from at is are be how what why when where which who can do does "
           "you your my i it me near best online vs".split())

VIEWS = {
    "summary": "what data is stored, its age and window, totals and caveats",
    "page": "one page (--page): its queries by bucket, CTR deficit, index state, decay, anonymised share",
    "query": "one query (--query): every client page Google shows for it",
    "topic": "a topic (--topic): client pages ranking for it, and the queries",
    "optimizer": "U-B page optimiser: pages at position <=20 with ranking/should-rank/question queries",
    "striking": "PF1 striking-distance queries (positions 4-20) with the page that should win",
    "ctr": "PF2 page-1 queries under the site's own CTR curve, by missed clicks",
    "questions": "U-C question queries: content-update and new-article candidates",
    "conversational": "PF4 10+ word (AI-Mode style) queries",
    "site_operator": "PF5 queries containing site:",
    "zero_click": "PF3 high-impression, near-zero-click queries",
    "emerging": "PF6 queries new since the previous 90 days",
    "alignment": "PF7 queries landing on the wrong kind of page",
    "intent": "PF8 impressions and clicks by intent class",
    "brand": "PF22 brand vs non-brand",
    "cannibalisation": "PF9 queries split between client pages, with the action",
    "decay": "PF10 pages losing clicks, with the likely cause",
    "decoupling": "AI2 pages likely cited in AI Overviews (impressions up, CTR down)",
    "device": "PF15 mobile vs desktop gaps",
    "country": "PF16 target-country gaps",
    "appearance": "PF17 search appearances",
    "coverage": "PF27 topical coverage by folder (Koray's query-count bands)",
    "trend": "16-month trend, last 28 vs previous 28 days",
    "curve": "the site's own CTR curve (non-brand)",
    "index": "IX5 replica of the Page indexing report from URL Inspection",
    "changes": "the dated change log (impact measurement input)",
    "impact": "PF26 logged changes vs the page's current totals (indicative)",
}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOP and len(w) > 2}


class Console:
    def __init__(self, slug: str, brief: dict | None = None):
        self.slug = slug
        self.brief = brief or {}
        self.profile = S.profile(slug)
        self.domain = (self.brief.get("domain") or self.profile.get("domain") or "").lower().removeprefix("www.")
        self.property = S.property_for(slug, self.brief)
        self.brand_re = RX.brand_regex(self.profile, self.domain)
        self._rows: dict = {}

    # ------------------------------------------------------------ data
    def rows(self, name: str) -> list[dict]:
        if name not in self._rows:
            self._rows[name] = S.rows(self.slug, name)
        return self._rows[name]

    def has(self, name: str) -> bool:
        return bool(self.rows(name))

    def available(self) -> bool:
        return self.has("query_page") or self.has("pages")

    def meta(self, name: str) -> dict:
        return (S.load(self.slug, name) or {}).get("meta") or {}

    @cached_property
    def inspections(self) -> dict:
        return (S.load(self.slug, "inspections") or {}).get("items") or {}

    @cached_property
    def curve(self) -> dict:
        return A.ctr_curve(self.rows("queries") or A.agg(self.rows("query_page"), "query"), self.brand_re)

    def caveats(self) -> list[str]:
        wins = [tuple(self.meta(n).get("window") or []) for n in ("query_page", "pages", "pages_prev", "pages_yoy")]
        return CV.lines(*[w for w in wins if len(w) == 2]) + CV.GENERAL[:2]

    # ------------------------------------------------------------ one page
    def page(self, url: str, band_hi: float = 20) -> dict:
        qrows = A.page_rows_for(self.rows("query_page"), url)
        prow = next((r for r in self.rows("pages") if A.norm(r.get("page")) == A.norm(url)), None)
        out = {"url": url, "property": self.property, "queries": len(qrows),
               "totals": {k: prow[k] for k in ("clicks", "impressions", "ctr", "position")} if prow else
               {"clicks": sum(r["clicks"] for r in qrows), "impressions": sum(r["impressions"] for r in qrows),
                "position": A.wpos(qrows)},
               "rows": sorted(qrows, key=lambda r: -r["impressions"])[:60]}
        b = A.page_queries(qrows, band_hi, min_impr=5)
        out["ranking"], out["should_rank"], out["questions"] = ([A._slim(r) for r in b[k][:20]] for k in ("ranking", "should_rank", "question"))
        out["striking"] = [A._slim(r) for r in qrows if 4 <= r.get("position", 0) <= band_hi and r.get("impressions", 0) >= 10][:25]
        out["low_ctr"] = A.ctr_deficit(qrows, self.curve, min_impr=50)[:10]
        out["anonymised_share"] = A.anonymised_share((prow or {}).get("clicks", 0), qrows) if prow else None
        insp = self.inspections.get(url) or next((v for k, v in self.inspections.items() if A.norm(k) == A.norm(url)), None)
        if insp:
            n = IX.norm_inspection(insp)
            bucket, pb, what = IX.route(n)
            out["index"] = {**{k: n.get(k) for k in ("coverageState", "googleCanonical", "userCanonical", "lastCrawlTime",
                                                      "pageFetchState", "indexingState", "crawledAs")},
                            "bucket": bucket, "playbook": pb, "what_to_do": what, "flags": IX.flags(url, n, out["totals"].get("impressions", 0))}
        dec = [d for d in A.decay(self.rows("pages"), self.rows("pages_prev"), self.rows("pages_yoy"), min_prev_clicks=20)
               if A.norm(d["page"]) == A.norm(url)]
        out["decay"] = dec[0] if dec else None
        dev = [d for d in A.device_gap(self.rows("page_device"), min_impr=50) if A.norm(d["page"]) == A.norm(url)]
        out["device_gap"] = dev[0] if dev else None
        out["cannibalisation"] = [c for c in A.cannibalisation(self.rows("query_page"), min_impr=20, brand_re=self.brand_re)
                                  if any(A.norm(p["page"]) == A.norm(url) for p in c["pages"])][:15]
        out["changes"] = [e for e in S.changelog(self.slug) if A.norm(e.get("url", "")) == A.norm(url)]
        return out

    # ------------------------------------------------------------ queries, topics, links
    def query(self, q: str) -> list[dict]:
        q = (q or "").lower().strip()
        return [A._slim(r) for r in A.agg([r for r in self.rows("query_page") if (r.get("query") or "") == q], "page")]

    def topic(self, text: str, exclude: str | None = None, min_impr: int = 10, limit: int = 10) -> list[dict]:
        """Client pages already showing for the topic's words: link targets for a new page, cannibalisation risk."""
        tw = words(text)
        need = 1 if len(tw) <= 2 else 2
        rows = [r for r in A.topic_rows(self.rows("query_page"), tw, need)
                if not exclude or A.norm(r.get("page")) != A.norm(exclude)]
        pages = []
        for page, rs in A.by(rows, "page").items():
            imp = sum(r["impressions"] for r in rs)
            if imp >= min_impr:
                pages.append({"page": page, "impressions": imp, "clicks": sum(r["clicks"] for r in rs), "position": A.wpos(rs),
                              "queries": [r["query"] for r in sorted(rs, key=lambda r: -r["impressions"])[:5]]})
        return sorted(pages, key=lambda p: -p["impressions"])[:limit]

    def link_sources(self, url: str, text: str, limit: int = 8) -> list[dict]:
        """Pages that should link INTO this page (Onely/Quaid: contextual body links from indexed pages that get
        traffic): topically related client pages with clicks, best first."""
        return [p for p in self.topic(text, exclude=url, min_impr=1, limit=30) if p["clicks"] > 0][:limit]

    # ------------------------------------------------------------ site views
    def view(self, name: str, **kw) -> object:
        qp, br = self.rows("query_page"), self.brand_re
        target_country = kw.get("country") or self._country()
        if name == "summary":
            return self.summary()
        if name == "page":
            return self.page(kw["page"])
        if name == "query":
            return self.query(kw["query"])
        if name == "topic":
            return self.topic(kw["topic"])
        if name == "optimizer":
            return A.page_optimizer(self.rows("pages"), qp, kw.get("band", 20), kw.get("min_impr", 500), br)
        if name == "striking":
            return A.striking(qp, (4, kw.get("band", 20)), kw.get("min_impr", 100), br)
        if name == "ctr":
            return A.ctr_deficit(A.agg(qp, "query", "page"), self.curve, kw.get("min_impr", 500), brand_re=br)
        if name == "questions":
            return A.questions(qp, br)
        if name == "conversational":
            return A.conversational(qp)
        if name == "site_operator":
            return A.site_operator(qp)
        if name == "zero_click":
            return A.zero_click(self.rows("queries") or A.agg(qp, "query"))
        if name == "emerging":
            return A.emerging(qp, self.rows("query_page_prev")) if self.has("query_page_prev") else []
        if name == "alignment":
            return A.alignment(qp)
        if name == "intent":
            return A.intent_mix(self.rows("queries") or A.agg(qp, "query"), br)
        if name == "brand":
            return A.brand_split(self.rows("queries") or A.agg(qp, "query"), br)
        if name == "cannibalisation":
            return A.cannibalisation(qp, brand_re=br, home=f"https://{self.domain}/")
        if name == "decay":
            return A.decay(self.rows("pages"), self.rows("pages_prev"), self.rows("pages_yoy"))
        if name == "decoupling":
            return A.decoupling(self.rows("pages"), self.rows("pages_yoy"))
        if name == "device":
            return A.device_gap(self.rows("page_device"))
        if name == "country":
            return A.country_gap(self.rows("page_country"), target_country)
        if name == "appearance":
            return A.appearance(self.rows("appearance"))
        if name == "coverage":
            return A.topical_coverage(qp, self.rows("query_page_prev"))
        if name == "trend":
            return A.trend(self.rows("dates"))
        if name == "curve":
            return self.curve
        if name == "index":
            perf = {A.norm(r["page"]): r["impressions"] for r in self.rows("pages")}
            return IX.summary(self.inspections, perf, qp) if self.inspections else {}
        if name == "changes":
            return S.changelog(self.slug)
        if name == "impact":
            return self.impact()
        raise ValueError(f"unknown view {name!r}; views: {', '.join(VIEWS)}")

    def impact(self, min_days: int = 35) -> list[dict]:
        """PF26, indicative: each logged change at least 35 days old (28 days of data after a week's settling),
        its baseline against the page's current 90-day totals. For a controlled test, compare 28 days before vs 28
        days starting 7 days after with `final` data and a control group from the same folder (Google: wait a
        few weeks)."""
        from datetime import date
        now = {A.norm(r["page"]): r for r in self.rows("pages")}
        out = []
        for e in S.changelog(self.slug):
            try:
                age = (date.today() - date.fromisoformat(e["date"])).days
            except (KeyError, ValueError):
                continue
            cur, base = now.get(A.norm(e.get("url") or "")), e.get("baseline") or {}
            if age < min_days or not cur or not base:
                continue
            out.append({"url": e["url"], "changed": e["date"], "days": age, "kind": e.get("kind"),
                        "clicks_before": base.get("clicks"), "clicks_now": cur["clicks"],
                        "position_before": base.get("position"), "position_now": cur["position"],
                        "note": "90-day windows overlap the change until 90 days have passed: treat as direction only"})
        return out

    def _country(self) -> str:
        """ISO alpha-3 of the client's market (Search Console's country codes), from the locale."""
        region = ((self.brief.get("locale") or self.profile.get("locale") or "en-GB").partition("-")[2] or "GB").upper()
        try:
            import pycountry
            return pycountry.countries.get(alpha_2=region).alpha_3.lower()
        except Exception:
            return {"GB": "gbr", "US": "usa", "AU": "aus", "CA": "can", "IE": "irl", "IN": "ind", "AE": "are",
                    "PK": "pak", "NZ": "nzl"}.get(region, region.lower())

    def summary(self) -> dict:
        pages = self.rows("pages")
        return {"client": self.slug, "property": self.property, "brand_regex": self.brand_re,
                "datasets": S.manifest(self.slug),
                "totals_90d": {"clicks": sum(r["clicks"] for r in pages), "impressions": sum(r["impressions"] for r in pages),
                               "pages": len(pages), "queries": len({r["query"] for r in self.rows("query_page")})},
                "inspected_urls": len(self.inspections), "caveats": self.caveats()}


def for_brief(brief: dict) -> Console | None:
    slug = S.slug_for(brief or {})
    if not slug:
        return None
    c = Console(slug, brief)
    return c if c.available() or c.inspections else None
