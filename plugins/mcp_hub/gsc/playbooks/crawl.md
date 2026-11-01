# Crawl Stats, crawl budget, robots.txt (U-D, CR1–CR12)

Crawl Stats has these limits:
- it is UI-only and root-property-only;
- it covers 90 days;
- it counts requests, not URLs.

**Getting it in.** The user exports or pastes the summary, host status and every breakdown table with its example URLs (`../ui_checklists.md`). Then run `seo.py gsc crawl <client> <export>` (or `/page-seo <site> | gsc crawl <file>`). That classifies the examples, checks the thresholds, and proposes robots.txt rules, tested against the site's top 200 pages.

**Scale.**
- Sites under about 1,000 pages: call it crawl **hygiene**, not budget.
- Google's budget guide targets 1M+ pages, 10k+ pages changing daily, or many DCNI URLs.
- Barry Adams monitors from about 100k URLs.

## U-D. The user's workflow, with the research corrections

1. **"Other file type" dominant: read the examples before blaming rendering.**
   - Google defines Other as "anything else, *including redirect responses*". It also catches fonts and Next.js RSC payloads.
   - One Next.js site had 87% Other (`text/x-component`) against 8% HTML.
   - The classifier labels each example:
     - `?_rsc=` → RSC prefetch waste. The site is already server-rendered, so "make it SSR" is the wrong fix.
     - Redirect URLs → treat as a 3xx problem.
     - `.woff2` → normal; trim font weights, never block.
     - `/opengraph-image`, `/twitter-image`, `/icon` permutations → route loops.
     - JSON or extensionless `/api/` calls → a client-side data dependency. **Only then** raise server rendering with the site owner, as a question for them.
2. **By response.**
   - 301/308 share large or rising → update internal links, canonicals, sitemaps and hreflang to the final URLs; collapse chains (Googlebot follows ≤10 hops).
   - 302 for a permanent move → 301.
   - 404 → fix only the linked ones or those in sitemaps; 301 only to true equivalents.
   - 5xx/429 → capacity. Use 503 only for maintenance under 2–3 days; longer cuts crawling.
   - 401/403 → WAF or bot rules; allowlist verified Googlebot (reverse + forward DNS).
   - Redirect error → loops; test without cookies.
   - robots.txt not available → CR2.
3. **OK (200) examples: the crawl-waste library (CR10).**
   - Cluster the examples by path and parameter, and ask two questions of each cluster: **needed for rendering?** and **earning impressions in Search?** (Search Console page rows on the pattern).
   - Only a no/no cluster gets a Disallow proposal.
   - Patterns:

| Pattern | Rendering? | Do this |
|---|---|---|
| `?_rsc=` (Next.js RSC) | No | **Order:** (a) `X-Robots-Tag: noindex` only when the request has the `RSC: 1` header (a query-only rule also noindexes the HTML; verified on next@16.2.9); (b) `prefetch={false}` on large link grids; (c) keep `_rsc` out of sitemaps, links and canonicals, and vary the CDN cache on the RSC header; (d) **then** `Disallow: /*?_rsc=` and `/*&_rsc=`, accepting that some URLs may show as "Indexed, though blocked" |
| `/_next/static/` | **Yes** | **Never block.** Blocking chunks broke rendering (Next.js #78288); Google warns against blocking resources |
| `/_next/image?`, fonts, CSS/JS, cache-busting `?v=` | Yes | Never block; stabilise version strings |
| `/_next/data/`, `/wp-json/`, Nuxt `_payload.json`, `/api/` | Test first | Client navigation or themes may need them |
| Internal search (`/search`, `?s=`, `?q=`) | No | Remove crawlable links to results; Disallow the path |
| Facets (filter, colour, size, price) | No | Google: about **50%** of crawl problems. Disallow the named parameters, 404 empty combinations, keep filter links out of the crawlable HTML |
| Sort/view parameters | No | Disallow the named parameters; canonical to the unsorted page |
| Action URLs (`add-to-cart`, `wishlist`, `replytocom`) | No | Google: about **25%** of crawl problems. Disallow (Gary Illyes) |
| UTM, session and click IDs | No | Fix the source: internal links must never carry them |
| Calendar traps | No | Disallow and cap the linked range |
| OG/icon image routes | No | Stable URLs without query permutations; block only if not wanted in image search |
| Pagination | Yes | Keep crawlable; 404 past the last page |
| Shopify `?variant=` | No | The canonical handles it; leave unless it dominates |

4. **Test every rule before proposing it.** `seo.py gsc robots <client> --rule "Disallow: /*?_rsc=" --test <url>...` tests the rule the way Google does:
   - the longest match wins;
   - Allow wins a tie;
   - a `User-agent: Googlebot` group **replaces** `*` for Googlebot.

   A rule that blocks an important URL is rejected.
5. **Approval.** Show the diff and the test, and **ask the user**. Never deploy a robots.txt change yourself.

**Thresholds** (Google publishes none):

| Source | Measure | Threshold |
|---|---|---|
| Adams | Average response time | ≤600 ms, 200 ms ideal |
| Adams | File types | HTML should be the top file type |
| Adams | Discovery share | >10% is a red flag *for established publishers*; growing sites run higher |
| Adams | Googlebot type | Smartphone should dominate |
| Koray (interview-reported, not in his own articles) | Response time | <100 ms |
| Koray (interview-reported) | Canonical HTML hits | 99% |
| Koray (interview-reported) | 200/304 responses | 99% |

**Validate.**
- The robots.txt report shows "Fetched" with 0 errors.
- URL Inspection on sample blocked and allowed URLs.
- The pattern's examples fade in 2–6 weeks.
- Logs show fewer hits.
- Disallowed budget "evaporates": it does not move to other pages (Adams).

## Other crawl playbooks

**CR1, headline metrics**:
- Requests down while response time rises → a capacity problem.
- Requests down while response time stays flat → demand, robots or availability.
- Requests rising sharply → a new URL space, a launch, or spoofed bots.
- Download size rising while requests stay flat → heavier pages.

**CR2, host status:**
- A robots.txt 429/5xx halts crawling for 12 hours, then Google uses a cached copy for up to 30 days. A robots.txt 404 is fine.
- Serve robots.txt as a static edge file, exempt from the WAF and rate limits.
- Run `gsc robots` to check whether robots.txt is served as HTML or returns 5xx.

**CR5, by purpose:** open the Discovery examples to find parameters, `_rsc`, calendars or hacked sections. Low refresh on money pages → add links, `lastmod` and 304s.

**CR6, by Googlebot type:**
- A high page-resource-load share → heavy pages.
- An AdsBot share → talk to the PPC team (AdsBot must be named explicitly to restrict it).
- StoreBot is expected with Merchant Center.

**CR7, robots.txt rules:**
- Prefer named-parameter rules over `Disallow: /*?`.
- Never put Disallow and noindex on the same set: Google can't see the noindex.
- For indexed junk: noindex first, Disallow later.
- After a critical fix, use "Request a recrawl" in the robots report.

**CR8, 304/ETag:** only about 0.017% of Google's fetches are cacheable.
- Set ETag (preferred) and Last-Modified.
- Return an empty-body 304.
- Tie the ETag to a hash of the content.

**CR9, verify Googlebot:**
- Use reverse + forward DNS or Google's IP list. Never filter by user agent alone.
- Join the logs with Crawl Stats by date.
- "Page could not be reached" never appears in logs.

**CR11, Next.js soft 404s on valid pages:**
- Cause: deploy version skew between the HTML fetch and the JS render.
- Fixes: skew protection, keep old chunks, error boundaries, fewer rapid redeploys.
- Never block the chunks.

**CR12, status hygiene:**
- Google treats 404 and 410 alike (Koray prefers 410 for removals); don't convert them for crawl reasons.
- Cut redirect chains to one hop.
- Kill soft 404s.

**Myths to refuse:** see `../reference/myths.md`. They include blocking `/_next/static`, `*.js` or `*.json`; reading "Other" as CSR; noindex saving crawl budget; and using robots.txt or 503 to reshuffle budget.

Sources: Google Crawl Stats help, the large-site guide, the Crawling December series, the faceted-navigation doc, the Robots Refresher; Barry Adams; Next.js discussions #61850 and #78288; DBLScanner; Koray. Links are in the research report §4.1 U-D and §4.3.
