"""Known Search Console data events: any comparison that crosses one must say so, and switch metric where needed.

Sources: Google's Data anomalies page (support.google.com/webmasters/answer/6211453), the Search Central changelog,
Search Engine Land's num=100 study. Kept as data so `seo.py gsc` and every plugin state the same caveats.
"""
from __future__ import annotations

# (start, end, id, what it does, rule)
EVENTS = [
    ("2025-05-13", "2026-04-27", "impression_bug",
     "an impression-logging bug inflated impressions (so CTR and position too); clicks were not affected",
     "compare clicks, not impressions/CTR, for any window touching it"),
    ("2025-06-16", "2099-12-31", "ai_mode_in_web",
     "AI Mode data is counted in Web totals; every link in an AI Overview shares the Overview's one position",
     "expect position near 1-2 with low CTR on AI-cited queries; don't read it as a ranking gain"),
    ("2025-09-11", "2025-09-14", "num100",
     "Google removed &num=100: scraper impressions vanished, impressions fell and average position rose with no real change",
     "comparisons across September 2025 use clicks and per-query positions"),
    ("2026-02-28", "2026-03-01", "bulk_export_gap", "BigQuery bulk export missing for some properties", "exclude those days in BigQuery work"),
    ("2026-05-07", "2026-05-08", "discover_logging", "Discover logging error", "exclude from Discover trends"),
    ("2026-05-07", "2099-12-31", "faq_ended", "FAQ rich results stopped showing; the FAQ appearance filter was removed in June 2026",
     "don't trend FAQ appearances across it; question H2s are for ranking and AI answers, not FAQ snippets"),
    ("2026-05-21", "2026-05-21", "discover_logging_2", "Discover logging error", "exclude from Discover trends"),
    ("2026-06-24", "2026-06-24", "discover_logging_3", "Discover logging error", "exclude from Discover trends"),
    ("2026-08-13", "2026-08-17", "genai_dip", "Gen-AI report impressions dipped; Discover logging error on 13 Aug",
     "exclude from Gen-AI and Discover trends"),
    ("2026-09-24", "2099-12-31", "multimodal_split", "Web split into text-based and multimodal (Lens, Circle to Search); multimodal has no query data",
     "image-led sites: ask for the multimodal export"),
    ("2026-10-16", "2099-12-31", "index_report_stale", "the Page indexing report was reported stale from 16 Oct 2026; Performance shows indexing changes first",
     "check the report's last-updated date; trust URL Inspection and Performance first"),
]

GENERAL = [
    "About half of clicks sit on anonymised queries that are never listed (Ahrefs: 46.8% of clicks, 2025): query-level "
    "findings undercount the long tail. Never prune a page for having no listed queries.",
    "Any filter hides more anonymised rows: compare filtered segments with each other, not with unfiltered totals.",
    "The API returns top rows only; page totals come from page-only pulls, not from summing query rows.",
    "Average position is impression-weighted and site averages mislead: decide per query or per page.",
]


def for_window(start: str, end: str) -> list[dict]:
    """The events overlapping [start, end] (ISO dates)."""
    return [{"id": i, "from": s, "to": e, "what": w, "rule": r} for s, e, i, w, r in EVENTS if s <= end and e >= start]


def crossing(cur: tuple[str, str], prev: tuple[str, str]) -> list[dict]:
    """Events that differ between two compared windows: those make a naive comparison wrong."""
    a, b = {x["id"] for x in for_window(*cur)}, {x["id"] for x in for_window(*prev)}
    return [x for x in for_window(min(cur[0], prev[0]), max(cur[1], prev[1])) if (x["id"] in a) != (x["id"] in b)]


def metric_for(cur: tuple[str, str], prev: tuple[str, str]) -> str:
    """'clicks' when impressions are unreliable across the two windows, else 'impressions'."""
    bad = {"impression_bug", "num100"}
    return "clicks" if any(x["id"] in bad for x in crossing(cur, prev)) else "impressions"


def lines(*windows: tuple[str, str]) -> list[str]:
    seen, out = set(), []
    for w in windows:
        for x in for_window(*w):
            if x["id"] not in seen:
                seen.add(x["id"])
                out.append(f"{x['from']}..{x['to'] if x['to'] < '2099' else 'now'}: {x['what']} → {x['rule']}")
    return out
