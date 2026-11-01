# Experience, links, enhancements, shopping, settings (EX, LK, EN, OP)

| ID | When | How | Decision → action |
|---|---|---|---|
| EX1 Core Web Vitals | Monthly | The report is UI-only (`ui_cwv`); field data comes from the CrUX API / CrUX History API / PSI (Florian's gsc-mcp-tools or the APIs). Thresholds at p75: LCP ≤2.5 s (poor >4 s), INP ≤200 ms (poor >500 ms), CLS ≤0.1 (poor >0.25). A URL group's status is its worst metric | Fix Poor groups on money templates first, weighted by impressions (`pages` dataset); mobile first. Search Console's "Start tracking" runs 28 days; CrUX History responds faster |
| EX2 HTTPS | Quarterly | A crawl for http URLs, certificate errors and https→http redirects; URL Inspection canonicals | Fix redirects and canonicals |
| EX3 Mobile-first | Quarterly | `crawledAs` (URL Inspection), the Smartphone share (Crawl Stats), the device gap (`data device`), Lighthouse mobile. The Mobile usability report was retired 1 Dec 2023 | Mobile parity of content, links and schema |
| LK1 Internal links | Quarterly | The user exports Links → Internal (`ui_links`); join with page impressions and the sitemap | High-impression money pages with few internal links are under-linked → `internal_links` and the pipeline's link plan; sitemap URLs missing from the export may be orphans (confirm by crawl: the report is sampled). Every page run also lists **link sources** (`data topic`): trafficked pages that should link into it |
| LK2 Link reclamation | Quarterly | Export "Latest links" and "More sample links" (≤100k rows); crawl the targets | Targets returning 404/410 → redirect or restore |
| LK3 Anchor spam, disavow | Only when worried | Spammy anchors in Latest links | Google typically ignores spam links; disavow only "as a last resort", with a manual action or a paid-link history. Needs approval |
| EN1 Rich-result sweep | Monthly | URL Inspection `richResultsResult` over template samples (stored with inspections), the Rich Results Test | A drop in valid items usually means a template, JS or plugin change; spikes in Unparsable structured data mean JSON-LD syntax errors |
| EN2 Enhancement fixes | Issues listed | Open the issue → samples → fix the template → Validate fix (approval) | Merchant "missing field" errors (shippingDetails, return policy) cap Shopping eligibility |
| EN3 Deprecations | Always | Gone: FAQ rich results (ended 7 May 2026; report removed June; API end August 2026), six types (Sep 2025), Practice problem (Jan 2026). Added: Q&A properties (Mar 2026) | Don't promise removed rich results; their markup can stay |
| EN4 Shopping, merchant | Merchants | `appearance` dataset (product snippets vs merchant listings); Merchant Center association | Keep Merchant Center current (it also feeds AI features) |
| OP1 Property setup | Onboarding | A Domain property by default; URL-prefix properties for key folders add URL Inspection quota | Set `gsc_property` in the client profile when it isn't `sc-domain:<domain>`. Adding a property needs approval |
| OP2 Users and verification | Quarterly | Review owners, departed staff and agencies, and unused verification tokens (UI) | The owner removes them; lingering tokens re-grant ownership |
| OP3 Bulk export and history | Onboarding | The owner enables BigQuery bulk export (no backfill); a monthly archive beyond 16 months (the store keeps every pull) | Long-tail SQL through Google's BigQuery MCP: anonymised share, cannibalisation, CTR by position |
| OP5 Associations, alerts | Onboarding | Link GA4 and Merchant Center; email alerts are the only "push" signal | Forward alerts to whoever runs the audit |
| OP6 Insights, recommendations, achievements | Optional | UI cards | Low value: the API trends replace them |

Sources: Google's CWV, Links, Manual actions, Shopping and permissions help; the Search Central changelog; Screaming Frog (URL Inspection automation). Links are in the research report §4.6.
