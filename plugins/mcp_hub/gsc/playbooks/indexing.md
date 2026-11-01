# Indexing, URL Inspection, sitemaps, removals (U-A, IX1–IX15)

Data:
- URL Inspection: `seo.py gsc inspect <client>` (API), or the MCP batch-inspect tool → `gsc ingest <client> inspections <file>`.
- Page queries: the store.
- The Page indexing report itself is UI-only (`../ui_checklists.md`). Check its last-updated date: it was stale from 16 Oct 2026, and Mueller says indexing changes show in Performance first.

Read the result with `seo.py gsc data <client> index`. It gives buckets, templates, flags, the site-level gate, technical fixes and the CCNI triage.

## U-A. The user's workflow: fix every status, rescue "Crawled – currently not indexed"

**When.**
- Monthly.
- After a deploy.
- When a section's impressions fall.
- Fix only URLs you **want** indexed: those in a sitemap, linked internally, or earning impressions.
- "Not indexed" is not necessarily bad.

**Steps.**
1. **Replica.** Inspect sitemap URLs, pages with impressions and top linked URLs, most valuable first. Stay at ≤1,900/day per property; extra URL-prefix properties add quota. Bucket by `coverageState`, then by URL template: one template usually has one cause (Onely).
2. **Ask the user** for the Page indexing chart and the "All submitted pages" view (`ui_page_indexing`).
3. **Technical statuses first** (IX1–IX4, below), most urgent first:
   - 5xx;
   - 401/403 (WAF);
   - robots or noindex on wanted URLs;
   - redirect errors;
   - soft 404 on money pages;
   - internally linked 404s.
4. **Triage each CCNI URL.** `indexing.triage_ccni` does this automatically:
   1. **URL type.** A tag, filter, search, pagination or feed URL shouldn't be indexed: noindex, canonical, 404 or merge, and stop.
   2. **Redirect.** It reports the destination's status, so inspect every hop (Glenn Gabe).
   3. **Canonical.** If `googleCanonical` ≠ the URL, go to IX3.
   4. **Render.** Is the main text, H1 and links in the raw HTML? If not, go to `render.md`.
   5. **Crawl activity.** `lastCrawlTime` within about 60 days means Google is choosing not to index it: your "well crawled → content problem" case. An old or absent crawl date means a demand or authority problem, treated like DCNI.
   6. **Authority (David Quaid).** Count internal links from pages with clicks, and external links.
   7. **Title (Edward Sturm).** Make a generic or near-duplicate title unique: keyword + benefit + brand.
5. **Branch A: the page earned impressions.** Its own Performance queries are the rewrite seed. Put them into H2s and the main content (your tactic), check whether a stronger page now competes for them, and queue the rewrite: `/page-seo <site> | gsc queue ccni`.
6. **Branch B: no impressions ever.** There are no queries to use. Choose one:
   - merge into a stronger page and 301;
   - differentiate with unique data and first-hand experience (Mueller: "Anyone could have written this" content may stay out);
   - build authority with 3–5 contextual body links from indexed, trafficked pages (`seo.py gsc data <client> topic --topic "<topic>"` lists them).

   Seed any rewrite from keyword research and the SERP.
7. **Site-level gate.** If a large share of wanted URLs is CCNI or DCNI across many templates (the replica flags ≥30% across ≥3 templates [synth]), Google reads this as site quality (Mueller and Splitt, SOTR 112; Illyes). Run pruning and consolidation before page rewrites. There is **no target ratio**: Google's own docs site is about 5% indexed.
8. **Push.**
   - Bump `<lastmod>` on a real change.
   - Request indexing **once**, for a materially changed, high-value URL, and only with the user's approval.
   - Never use Validate fix for CCNI or DCNI.
9. **Validate.**
   - Re-inspect after 3–6 weeks [synth], and judge only once `lastCrawlTime` has moved.
   - Performance impressions on the URL are the leading signal.
   - Site-quality work takes "a couple of months, half a year, sometimes longer" (Mueller).

## Status by status

| Status | Meaning | Fix | Validate |
|---|---|---|---|
| Server error (5xx) | Google got 5xx | Capacity; compare with Crawl Stats host status; 503 only for short maintenance | 7–14 days |
| Redirect error | Loop, chain >10 hops, empty or bad target | One hop to the final URL; test http↔https, slash, locale and consent-cookie loops cookie-less | 7–14 days |
| URL blocked by robots.txt | Disallowed | If wanted: remove the rule (test with `gsc robots --test`) | Re-inspect |
| URL marked 'noindex' | Meta or X-Robots-Tag | If wanted: remove it. If not wanted, it's correct | Re-inspect |
| Soft 404 | 200 that looks empty or "not found" | Real 404/410, or real content. Causes: out-of-stock, empty filters, "not found" text with 200, SPA routes. On Next.js: deploy version skew (`crawl.md` CR11) | 7–14 days |
| 401 / 403 / other 4xx | Auth, WAF or bot rule | Allowlist verified Googlebot (reverse + forward DNS); compare Googlebot UA vs browser (`gsc render`) | Live test |
| Not found (404) | Gone | Fix only if linked internally or in a sitemap; 301 only to a true equivalent (never mass-redirect to home) | n/a |
| Blocked by page removal tool | A Removals request | Cancel it if the page should show | n/a |
| Crawled – currently not indexed | Crawled, not chosen | U-A above | 3–6 weeks |
| Discovered – currently not indexed (IX2) | Known, not crawled | Internal-link depth, sitemap-only URLs (empty `referringUrls`), response time and 5xx/429, URL bloat (facets). Mueller: it "can be forever" | 4–8 weeks |
| Duplicate without user-selected canonical | No canonical chosen | Self-referencing canonical on the version you want | ~2 weeks |
| Duplicate, Google chose different canonical than user (IX3) | Google overrode you | Internal URL → merge, differentiate or 301 (a cannibalisation sign); other domain → syndication, copy or hack; http/www → site-wide redirect | ~2 weeks |
| Alternate page with proper canonical; Page with redirect | Expected | Nothing | n/a |
| Indexed, though blocked by robots.txt (IX4) | Indexed from links | Unblock and noindex to remove it; or unblock to include it properly | Re-inspect |
| Page indexed without content (IX4) | Google saw an empty page | WAF challenge, CSR, non-HTML: `render.md` | Re-inspect |
| URL is unknown to Google | Never seen | Link it from indexed pages and list it in a sitemap | Re-inspect |

## More playbooks

- **IX5, the replica's flags.** Run weekly:
  - empty `sitemap[]` on a wanted URL;
  - no `referringUrls` and no sitemap (orphan);
  - last crawl more than 90 days ago on a key page;
  - crawled as DESKTOP;
  - canonical mismatch;
  - noindex but in a sitemap;
  - fetch not SUCCESSFUL.
- **IX6, sitemap segmentation.**
  - One sitemap per template or section (≤50k URLs).
  - Index rate per sitemap = indexed ÷ inspected, with the share earning ≥1 impression as a second proxy.
  - List only canonical, 200, indexable URLs.
  - Use `lastmod` only for significant changes; `changefreq` and `priority` are ignored.
  - Templates far below the median index rate get a quality review (`weak_templates`).
- **IX7, "Couldn't fetch" sitemap.** Check, in turn:
  - the property type (http/https, www);
  - the path;
  - middleware intercepting the route (Next.js);
  - robots;
  - an HTML response.

  Resubmitting needs approval.
- **IX8, Validate fix.** Only for systemic technical fixes, once, after a live test of samples, and with approval. Google tests a sample, then recrawls faster (about 2 weeks).
- **IX9, Removals.** Emergencies only (legal, PII, leaks, hacked spam), always paired with a permanent fix: 404/410, noindex or auth. Never use it for canonicalisation, moves or old 404s. Needs approval.
- **IX10, video indexing.**
  - The video must be the main content of a watch page, at a real size, with VideoObject and a valid thumbnail.
  - Ignore the report on pages where video is only supporting.
  - The report is UI-only.
- **IX11, Request indexing.** Once per materially changed, high-value URL, a handful a day, with approval. Never in bulk, never to "fix" CCNI, never to move canonicals.
- **IX12, read the report as trend lines.**
  - An expected change (for example "Page with redirect" after a migration) should appear.
  - A steep unexpected slope means investigate.
  - A flat chronic level means ignore.
  - 5xx lasting more than about a day makes Google react.
- **IX13, CDN or bot protection.**
  - Warning signs: a sudden 403/404/410 surge, or mass foreign canonicalisation.
  - The worst case is a 200 challenge page.
  - Fix it with the provider; overload should return 503.
- **IX14, a new site not indexed.** If the homepage isn't crawled, it is almost always technical: robots, server, a removal request, CMS "discourage", a parked page, or a www mismatch.
- **IX15, programmatic and faceted inventory.**
  - Each page needs unique entities and data.
  - Community rule: if none of a pattern's first 10 pages index in 4–6 weeks, the pattern is too thin (anecdotal).
  - Keep the strongest page per cluster, plus hubs.

Sources: Google Page indexing and URL Inspection help; SOTR 112 (Mueller, Splitt) and 061 (Illyes); Onely; Ahrefs (Stox); Glenn Gabe; Quaid; Sturm. Links are in the research report §4.1–4.2.
