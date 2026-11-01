# Data caveats: state the ones that apply before any conclusion

These are kept as data in `scripts/seolib/gsc/caveats.py`. `seo.py gsc data <client> summary` and every audit print the ones that touch the windows used.

| Caveat | Effect | Rule |
|---|---|---|
| Anonymised queries | 46.8% of clicks (Ahrefs, 887k properties, Apr 2025); about 75% of impressions (Kevin Indig) | State the anonymised share with every query-level finding; never prune "query-less" pages |
| Filters redact more | Any filter hides more rows (Mark Williams-Cook) | Compare filtered segments with each other, not with unfiltered totals |
| Top rows only | The API returns top rows; the UI shows 1,000 | Page totals come from page-only pulls; page past 25k with `startRow`; split by date/device/country |
| Property vs page aggregation | The chart, Queries and Countries tables count by property; Pages and Search appearance count by page | Use `byPage` for page work and `byProperty` for site query work, and label which |
| `num=100` removal (11–14 Sep 2025) | 87.7% of 319 properties lost impressions, and average position rose with no real change | Comparisons across September 2025 use clicks and per-query position |
| Impression-logging bug (13 May 2025 – 27 Apr 2026) | Impressions inflated, so CTR and position too; clicks unaffected | Use clicks for any window touching it |
| AI Mode in Web totals (since 16 Jun 2025) | All AI Overview links share one position; follow-ups count as new queries; impressions count only once in view | Expect position ≈1–2 with low CTR on cited queries; segment the CTR curve |
| Gen-AI report | Impressions only; included in Web totals; UI-only; dip 13–17 Aug 2026 | Never add it to totals; use it as a ratio |
| Branded filter | AI-classified; top-level properties only; misclassifies | Use the regex in automation; check the UI totals now and then |
| Freshness | `final` lags 2–3 days; the Page indexing report was stale from 16 Oct 2026 | Use `final` for before/after; trust Performance and URL Inspection first |
| Retention | 16 months; bulk export missing 28 Feb–1 Mar 2026 for some properties | The store keeps every pull; enable bulk export early |
| Deprecated appearances | Six types (Sep 2025); FAQ (May 2026) | Don't trend them across the cut |
| Discover | No position or query; logging errors on 7–8 May, 21 May, 24 Jun and 13 Aug 2026 | Page × date only; exclude those dates |
