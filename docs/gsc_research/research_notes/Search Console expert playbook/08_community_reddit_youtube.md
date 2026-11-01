# Community field reports on Google Search Console (Reddit, Search Central Community, GitHub, HN, Indie Hackers, trade recaps)

**Source-access note (read first).** Reddit could not be read directly: the search tool refuses `reddit.com` as a domain ("not accessible to our user agent"), and general searches never returned Reddit threads. Reddit material below comes **second-hand** through Search Engine Roundtable (SER) write-ups that link the original thread. The direct practitioner evidence comes from GitHub discussions (Next.js maintainers and users), Hacker News, Indie Hackers, Shopify Community and the Google Search Central Community guide. **YouTube transcripts, X/Twitter threads, BlackHatWorld, Warrior Forum and Slack/Discord recaps were not reached** in this pass; they are listed under Gaps. Dates are given as reported. Today is 2026-11-01.

---

## 1. Page indexing: "Crawled – currently not indexed" (CCNI) and "Discovered – currently not indexed" (DCNI)

### Takeaway
Google's own people and the community mostly agree that **large-scale CCNI/DCNI is a site-level quality or crawl-demand signal, not a per-page bug**. The fixes people report working are content consolidation/expansion, hub-based internal linking, and pruning thin URLs from sitemaps. Request Indexing helps only at small scale. Migrations can bring CCNI back months later.

### Cited Findings
- **Mueller and Splitt (Search Off the Record, covered 16 Jul 2026):** CCNI and DCNI only *sometimes* point to quality. When Google seriously doubts a site's quality, it crawls and indexes fewer of its pages and comes back once the concern eases. If many pages are unindexed with no technical cause, review the whole site's quality instead of fixing pages one by one. Sites built mostly from generic AI text may look like they add little unique value, though Mueller said not all AI content is bad. — [SER](https://www.seroundtable.com/google-crawled-not-indexed-quality-ai-content-41701.html)
- **Mueller on DCNI duration:** the status "can be forever", because Google does not crawl and index every page. — [Search Engine Journal](https://www.searchenginejournal.com/google-says-discovered-currently-not-indexed-status-can-last-forever/439104/)
- **Google Search Central Community guide (written by community members, not official docs):** persistent DCNI points to a site-wide capacity problem and/or low crawl demand, meaning Google does not yet see the page as a priority. Google's help page adds that Google may have postponed the crawl because it expected to overload the site. — [Search Central Community guide](https://support.google.com/webmasters/community-guide/354590602/why-isn-t-google-indexing-pages-in-discovered-currently-not-indexed-status?hl=en); [Page indexing report help](https://support.google.com/webmasters/answer/7440203?hl=en)
- **Official text quoted widely:** for CCNI, the URL "may or may not be indexed in the future; no need to resubmit this URL for crawling." — quoted via [SER](https://www.seroundtable.com/crawled-currently-not-indexed-google-quality-issue-31677.html)
- **Indie Hackers founders (programmatic SEO, 2025–2026, self-reported):**
  - Google flagged 962 programmatic "fix" pages as too thin. Expanding each to about 900 words of specific data reportedly broke the bottleneck.
  - On a site of about 24k generated pages, the indexed count fell. The fix was to keep the strongest page in each cluster indexable and noindex or merge the rest.
  - A 750-URL sitemap turned out to hold 560 thin tag/category pages.
  - "500 pages with no hub = orphans": build one category hub per pattern that links to every variation, with each variation linking back.
  - A 200-page batch was filtered out partly because each keyword had under 50 searches a month.
  - Rule of thumb: if none of the first 10 pages of a pattern index within 4–6 weeks, the pattern is too thin.
  - Diagnostic order offered: sitemap → live URL test → canonical → robots/noindex → then read the status. Once a page is "crawled not indexed", stop treating it as technical.
  - All of these are anecdotal, and some threads are promotional. — [IH search cluster incl. "indexed exactly ZERO of my pages after 2 weeks"](https://www.indiehackers.com/post/google-indexed-exactly-zero-of-my-pages-after-2-weeks-is-this-normal-or-am-i-doing-something-stupid-8fed9e8d9b); [IH pSEO case studies thread](https://www.indiehackers.com/post/looking-for-programmatic-seo-case-studies-and-success-stories-9439e1f9e7); [IH "Google went cold… my own fault"](https://www.indiehackers.com/post/four-weeks-of-my-steam-game-finder-google-went-cold-and-it-was-my-own-fault-a3e080ac15) (the last returned 403 when fetched; only its search snippet was seen)
- **Shopify Community (900+ CCNI URLs, store asked for bulk request-indexing):** the main reply said not everything crawled should be indexed, and non-indexed pages often add no unique value over other versions on the site. The thread was never resolved. A separate collection-page thread recommended unique collection descriptions, URL Inspection checks and internal linking. — [Shopify Community 255140](https://community.shopify.com/t/gsc-1000-pages-affected-by-crawled-currently-not-indexed/255140); [Shopify Community 312491](https://community.shopify.com/t/how-we-can-resolved-crawled-currently-not-index-issues/312491)
- **Hacker News (2025) mass-deindex reports:** one blogger saw traffic fall about 95% on 25 Aug 2025 (about 1000 visits a month down to about 50). Another long-standing site found almost all entries suddenly not indexed. Commenter theories, none confirmed: repeated manual Request Indexing triggering a spam or quality signal; AI-content load on Google's indexing budget; back-button-hijacking spam policy. One commenter pushed back that "Google defaults to not indexing" has no hard data behind it. — [HN 46239752 (Bear Blog de-indexed)](https://news.ycombinator.com/item?id=46239752); [HN 40970987](https://news.ycombinator.com/item?id=40970987); [HN 36195600](https://news.ycombinator.com/item?id=36195600)
- **GSC reporting glitch:** SER reported a short bug that briefly showed indexed pages as CCNI, which Mueller called a "short blip". — [SER](https://www.seroundtable.com/google-confirmed-indexing-reporting-bug-from-last-night-42051.html)
- **Report-freshness war story (r/TechSEO, covered 27 Oct 2026):** the Page Indexing report had not updated since 16 Oct. Mueller said not to worry much about report freshness, that each report shows its own dates, and that **changes usually show up first in the Performance report**. — [SER](https://www.seroundtable.com/google-downplays-importance-of-fresh-index-reporting-42381.html), original [r/TechSEO](https://www.reddit.com/r/TechSEO/comments/1xe0wum/comment/19rkkkfgm39qa/); SEJ also reported delays in both the indexing and performance reports from late 2025 into 2026 — [SEJ](https://www.searchenginejournal.com/what-search-console-can-still-tell-you-when-indexing-data-lags/595016/)

### Inferences
- The automation should sort CCNI/DCNI by **share of the site** affected. A few URLs: check internal links and request indexing. A large share or a sudden jump: run a site-quality and pruning workflow (consolidate clusters, noindex thin facets/tags, pull them from sitemaps, add hub links) rather than mass re-submission.
- Before acting on Page Indexing data, check the report's "last updated" date. Use Performance-report impressions on the affected URLs as the leading indicator.

### Gaps
- None of the CCNI fix claims I found had a controlled before/after with dates (Reddit threads, the likely best source, were unreachable).
- No authoritative timeframe exists for how long DCNI is "normal" on a new site. Google says "a week or so" to start crawling; community claims of 3–8 weeks are unverified.

---

## 2. Next.js / framework crawl waste: `_rsc`, `_next/static`, "Other" file type, soft 404s

### Takeaway
This is the richest field evidence found. Next.js App Router `?_rsc=` prefetch requests can dominate Crawl Stats (one 2026 site: 87% "Other file type") and create duplicate URLs in GSC. The community has moved from "robots.txt disallow `_rsc`" toward **noindex the RSC payload only (match on the `RSC: 1` header), keep clean canonicals, and turn off prefetch on large link grids**. Soft 404s on valid Next.js pages are widely blamed on deploy "version skew" between Google's HTML fetch and its later JS render.

### Cited Findings
- **Crawl Stats war story (PR merged 21 Oct 2026; Next.js on Vercel; local-services site whose town pages carry about 100 links each, described as demoted and rarely recrawled):**
  - 90-day Crawl Stats: 18.1k Googlebot requests, 96% returned 200, **only 8% HTML, 87% "Other file type"**, which the author identified as RSC prefetch payloads (`text/x-component`).
  - Fix: robots.txt `Disallow: /*?_rsc=` and `/*&_rsc=`, plus `prefetch={false}` on the three largest link grids (footer town links, service-hub lists, nearby towns).
  - No post-change results were reported. The author's link between the payloads and pages not being re-read is a hypothesis.
  - — [GitHub PR #76](https://github.com/galaxyinfomkt-svg/am-painter-inc/pull/76)
- **Next.js discussion #61850 (opened 9 Feb 2024, still active in 2026):** `?_rsc=` URLs pile up in GSC, mostly as "Alternative page with proper canonical tag". Reported outcomes:
  - **robots.txt disallow:** one user (Aug 2024) said it worked. Another (Oct 2024) found Google moved the URLs to "Indexed, though blocked by robots.txt". A third (Jan 2025) saw no effect.
  - **`next.config.js` redirects conditioned on `_rsc`:** cut errors from 1300+ to 402 and some pages began indexing, but those pages still did not appear in results (Feb 2025).
  - **Middleware stripping the param:** failed because `NextRequest` does not expose `_rsc` to middleware.
  - **`prefetch={false}`:** stopped the requests (Feb 2025).
  - **`X-Robots-Tag: noindex` on `_rsc` responses:** reported to resolve indexing (Jun 2026). A refinement (Aug 2026, verified on next@16.2.9) added a `has` header condition `RSC: 1`, because a query-only rule also noindexes the HTML. This stops indexing, not crawling.
  - — [GitHub discussion #61850](https://github.com/vercel/next.js/discussions/61850)
- **Recommended fix order (DBLScanner, 28 Sep 2026):**
  1. curl the URL with and without the RSC header.
  2. Add noindex only to the RSC payload, matching both the query and the header.
  3. Keep a clean canonical on the HTML, never with `_rsc`.
  4. Keep `_rsc` out of sitemaps and internal links.
  5. Vary CDN cache keys on the RSC header and query.
  6. Recrawl, and request indexing on the clean URL only.

  Expected GSC path: "Alternate page with proper canonical", then the URL drops out. Warnings: robots.txt before the HTML is correct can leave `_rsc` URLs "Indexed, though blocked". Do not 301 real prefetches, do not strip all query strings, and do not replace `<Link>` sitewide. — [DBLScanner](https://dblscanner.com/blog/nextjs-rsc-query-param-indexed)
- **Next.js soft 404s on valid pages (discussion #78288, late 2024 to May 2026):**
  - Most accepted cause: Google renders the JS later than it fetches the HTML. If a deploy changes hashed chunk names in between, the render requests chunks that no longer exist.
  - **Disallowing `/_next/static/chunks/app/` in robots.txt** stopped the flags for some users but broke rendering for others (e.g. Swiper content). Vercel staff and Google Product Expert Barry Hunter reportedly advised against it.
  - Reported mitigations: Vercel Skew Protection; `GracefullyDegradingErrorBoundary`; keeping the last few deployments' chunks and returning 410 for missing ones; a `?dpl=` deployment parameter plus Cloudflare cache purge (one self-hosted site recovered fully after being deindexed); `htmlLimitedBots`; fewer rapid redeploys.
  - A prerender service (Seorender) cut soft 404s from 93 to 17 in about 3 weeks; prerender.io did nothing for another user.
  - Another case: "404"/"Page not found" strings leaked into the RSC payload, fixed with a client-only not-found component.
  - Upgrading to Next 15/16 alone did not help. Recovery takes weeks to months. Not confirmed by Google or Vercel.
  - — [GitHub discussion #78288](https://github.com/vercel/next.js/discussions/78288)
- **Sitemap "Couldn't fetch" on Next.js** was traced to middleware intercepting the sitemap route; excluding that route fixed it. — [GitHub issue #75836](https://github.com/vercel/next.js/issues/75836)

### Inferences
- The automation should flag Crawl Stats when "Other" file type exceeds HTML on a JS-framework site, then check for `_rsc`, `text/x-component` and `_next/static` chunk 404s.
- Recommended order: (1) correct the canonical and noindex on the payload; (2) turn off prefetch on large link grids; (3) only then consider robots.txt for `_rsc`. Never block `_next/static` wholesale.

### Gaps
- No public before/after Crawl Stats numbers after the `_rsc` fixes. The 2026 PR reported no outcome yet.
- No field reports found on OG-image routes (`/opengraph-image`) eating crawl budget.

---

## 3. URL Inspection & Request Indexing

### Takeaway
Request Indexing does not scale, does not change which URL is canonical, and heavy use is suspected (not proven) of hurting. Google is unlikely to raise the quota.

### Cited Findings
- Mueller (LinkedIn, covered 20 Feb 2026): he "strongly recommend[s] not relying on trying to force indexing". It makes no sense for a reasonably large site. Use normal discovery, and Merchant Center for products. — [SER](https://www.seroundtable.com/google-force-indexing-40963.html); [LinkedIn source](https://www.linkedin.com/feed/update/urn:li:activity:7429518169867804672)
- Mueller (5 Jul 2024): requesting indexing of a 301'd old URL to speed its removal won't work. Request Indexing does not change canonicalization and if anything signals the URL should stay indexed. Use the Removals tool for speed and align canonical signals instead. — [SER](https://www.seroundtable.com/google-request-indexing-does-not-change-canonicalization-37676.html)
- Google said it is unlikely to raise the Request Indexing quota because of spam submissions (older report). — [SER](https://www.seroundtable.com/google-unlikely-to-increase-request-indexing-quota-34742.html)
- **Contradicting anecdotes:**
  - An Indie Hackers founder claimed 5x search traffic after manually feeding pages into the crawler pipeline. — [IH cluster](https://www.indiehackers.com/post/google-indexed-exactly-zero-of-my-pages-after-2-weeks-is-this-normal-or-am-i-doing-something-stupid-8fed9e8d9b)
  - The Bear Blog author reportedly requested indexing manually for every new post before the site was de-indexed, and HN commenters speculated this looked spammy (unconfirmed). — [HN 46239752](https://news.ycombinator.com/item?id=46239752)

### Inferences
- Limit Request Indexing to a handful of high-value, newly fixed URLs a day. Never use it to influence canonicals or to remove URLs.

### Gaps
- No evidence either way that heavy Request Indexing use causes a penalty.

---

## 4. Sitemaps

### Takeaway
"Couldn't fetch" is usually a property mismatch (http vs https, www vs non-www), a wrong path, middleware or robots.txt interference, or an HTML response. Sitemaps stuffed with thin tag/category URLs are a common hidden cause of indexing trouble.

### Cited Findings
- **Property mismatch:** a user had verified the http property while the site ran on https; adding the https property fixed it. — [Medium](https://thomaspet.medium.com/couldnt-fetch-sitemap-error-on-google-search-console-solved-e0dc466a3fa7)
- **Separate properties and re-fetching:** www and http/https are separate properties. Resubmitting under a slightly different URL or a new sitemap name can trigger a fresh fetch. — [AIOSEO](https://aioseo.com/docs/troubleshooting-the-couldnt-fetch-error-in-google-search-console/); [DEV](https://dev.to/chocoscoding/sitemap-couldnt-fetch-in-google-search-console-fix-4983)
- **Can clear by itself:** the status often clears within days or weeks without action (Wix); in a GitHub thread it stayed stuck for weeks. — [Wix](https://support.wix.com/en/article/google-search-console-couldnt-fetch-error); [GitHub #75836](https://github.com/vercel/next.js/issues/75836)
- **Google stops fetching:** an HN commenter said Google stopped fetching their sitemap and validation sat stuck for weeks, while Bing Webmaster Tools processed the same sitemap fine. — [HN 46239752](https://news.ycombinator.com/item?id=46239752)
- **Thin URLs in the sitemap:** 560 of 750 sitemap URLs were thin tag/category pages (Indie Hackers). — [IH cluster](https://www.indiehackers.com/post/google-indexed-exactly-zero-of-my-pages-after-2-weeks-is-this-normal-or-am-i-doing-something-stupid-8fed9e8d9b)

### Inferences
- The automation should confirm the property type, fetch the sitemap as Googlebot (status code, content-type, redirects, robots), and audit the URL mix (share of thin, parameter or noindexed URLs).

### Gaps
- No reliable account of why Google sometimes stops fetching a valid sitemap.

---

## 5. Crawl stats, crawl budget, faceted navigation & robots.txt

### Takeaway
robots.txt saves crawl budget but cannot remove pages and hides noindex from Google. noindex removes pages but still costs crawls. Practitioners use layers: canonical for duplicates, noindex for crawlable low-value pages, robots.txt for zero-value parameters (sort, session, add-to-cart, compare).

### Cited Findings
- **Layered approach:**
  - noindex does not save crawl budget; only a robots.txt disallow stops the fetch.
  - Googlebot ignores `crawl-delay`.
  - Some filter combinations match real search demand and should become static indexable pages.
  - A rule of thumb from one guide: if "Discovery" is over 30% of crawl purpose, you are minting URLs faster than Google can keep up.
  - — [1Digital](https://www.1digitalagency.com/blog/faceted-navigation-seo-in-2026-the-definitive-guide-to-indexing-and-crawl-budget-mtii5tln/); [Nico Digital](https://www.nicodigital.com/technical-seo/faceted-navigation-seo-crawl-budget/); [SEOEngico](https://seoengico.com/blog/faceted-navigation-pagination-crawl-budget-2026)
- **Anonymised audit:** 22% of crawl requests hit "Add to Cart" and "Compare" parameters, which were then blocked via robots.txt. No before/after metrics were given. — [SearchEngineZine](https://searchenginezine.com/technical/crawl-index/mastering-robots-txt/)
- **Unverified numbers:** a "73% crawl waste reduction" case on LinkGraph has no client, source or date (looks illustrative, so don't rely on it). Gary Illyes' "faceted nav ≈ 50% of crawl issues" is repeated second-hand; no primary source was found. — [LinkGraph](https://www.linkgraph.com/blog/crawl-budget-optimization-2/)
- **Indexed, though blocked:** pages blocked in robots.txt can stay indexed ("Indexed, though blocked by robots.txt"), as the Next.js `_rsc` cases show. — [GitHub #61850](https://github.com/vercel/next.js/discussions/61850); [Stan Ventures on Mueller](https://www.stanventures.com/news/pages-indexed-though-being-blocked-by-robots-txt-insights-from-john-mueller-779/)

### Inferences
- When "Other" or parameter URLs dominate Crawl Stats, the agent should propose robots.txt rules **only for URLs that are not indexed** and are zero-value. Already-indexed junk needs noindex or canonical first, with robots.txt added later.

### Gaps
- No verified, dated before/after crawl-budget case studies with GSC screenshots or logs were found.

---

## 6. Removals, deindexing & canonical/duplicate issues

### Takeaway
Removals hides URLs only temporarily (about 6 months). Permanent removal needs noindex, 404/410 or a redirect, **while the URL stays crawlable**. Request Indexing does not move canonicals; consistent signals do.

### Cited Findings
- **noindex, not robots.txt:** to unindex pages, use noindex rather than a robots.txt block. A blocked page's noindex is never seen. — [SER](https://www.seroundtable.com/unindex-pages-google-search-31050.html); [SEJ on Mueller](https://www.searchenginejournal.com/googles-john-mueller-clarifies-how-to-remove-pages-from-search/551424/)
- **Removals is temporary:** use it for speed, paired with a permanent noindex or removal. — [Patrick Stox](https://patrickstox.com/technical-seo/how-search-works/indexing/how-to-deindex/); [SER 2024](https://www.seroundtable.com/google-request-indexing-does-not-change-canonicalization-37676.html)
- **HN canonical/duplicate field tips:**
  - Google chose a different canonical across similar blog, service and tag URL patterns.
  - Check for unnamed-SNI or second-domain serving of your content, and use absolute canonicals.
  - Noindex internal search results and user-generated pages that spammers can get linked.
  - — [HN 46239752](https://news.ycombinator.com/item?id=46239752)

### Inferences
- The agent should refuse to recommend robots.txt as a removal method, and should pair any Removals request with a permanent fix that it then verifies.

### Gaps
- No community data on how often Google ignores declared canonicals in ways that hurt traffic.

---

## 7. Validate Fix

### Takeaway
"Validate Fix" re-checks the affected URLs; it is not a ranking lever. It commonly takes about 1–2 weeks or longer. A quick "Failed" usually means the fix is not live on the URLs Google sampled.

### Cited Findings
- **Google's help page:** validation fails when a threshold of pages still shows the issue; it can take "several days or even longer"; wait for success or failure before restarting. — [Google help](https://support.google.com/webmasters/answer/9216203?hl=en)
- **Practitioners:** a fast fail means the fix isn't live, so live-test a URL first. The 2–3 day data lag makes fixes look ignored. — [ShahidAli](https://www.shahidali.co/blog/search-console-validation-started/); [Koval SEO](https://kovalseo.com/blog/search-console-validation-failed/); [ClickFlow](https://blog.clickflow.com/validation-failed-in-google-search-console-what-it-means-and-what-to-fix-first)
- **Validation stuck for weeks** (HN commenter). — [HN 46239752](https://news.ycombinator.com/item?id=46239752)
- **Validation on CCNI/DCNI:** Mueller said these statuses usually aren't individual technical bugs, so "Validate Fix" there tends to disappoint. — [SER 2026](https://www.seroundtable.com/google-crawled-not-indexed-quality-ai-content-41701.html)

### Gaps
- A claim that Mueller explained the validation sampling mechanics appears only on one blog ([Digital Applied](https://www.digitalapplied.com/blog/search-console-validate-fix-when-to-use-mueller-2026)) and was not verified.

---

## 8. Performance report: regex, brand split, striking distance, average position

### Takeaway
Regex works only on Query and Page filters, one filter of each type, and is case-insensitive in practice (the sources disagree on this). Google added a native branded-queries filter in late 2025. The biggest interpretation trap of the period is the **September 2025 `&num=100` removal**: impressions fell and average position "improved" without any real ranking change.

### Cited Findings
- **Regex mechanics:**
  - Only Query and Page filters support regex, with one query filter and one page filter at a time.
  - Brand: pipe-joined variants including misspellings (e.g. `mcdonalds|macdonalds|maccies`), with "Doesn't match regex" for non-brand.
  - Questions: `^(who|what|when|where|why|how)`.
  - Rare (anonymised) queries are hidden, so regex segments undercount.
  - — [SEOTesting](https://seotesting.com/google-search-console/regex/); [Aubrey Yung](https://aubreyyung.com/google-search-console-regex/); [KairoxBuild](https://kairoxbuild.com/blog/gsc-regex-examples); [DataCraft 45 filters](https://datacraftdigital.com/blogs/45-search-console-regex-filters-we-use/)
- **Native brand filter:** a Branded Queries filter rolled out natively in late 2025. — [12AM Agency](https://12amagency.com/blog/filter-brand-keywords/)
- **`&num=100` (11–14 Sep 2025):**
  - Search Engine Land analysed 319 properties: 87.7% lost impressions, mostly on desktop, and average position rose sharply.
  - Explanation: rank-tracker scrapers had been creating deep (positions 50–100) impressions. Their loss raised the average without any real ranking change.
  - One analyst won't attribute the change solely to num=100. Another source cites a separate GSC impressions logging error running from 13 May 2025 to 27 Apr 2026.
  - — [SEL data](https://searchengineland.com/google-num100-impact-data-462231); [SEL interpretation](https://searchengineland.com/why-google-search-console-impressions-dropped-interpret-data-463677); [Locomotive](https://locomotive.agency/blog/google-removes-num100-parameter-what-this-means-for-your-website/); [Swap Biswas](https://swapbiswas.com/blog/google-search-console-impressions-drop/)
  - An HN commenter separately noted that Google changed impression counting around September, so before/after data isn't comparable while clicks stay reliable. — [HN 46239752](https://news.ycombinator.com/item?id=46239752)
- **Striking distance:** no field-tested results with numbers were found in this pass.

### Inferences
- Any period comparison crossing mid-September 2025 should use **clicks** and per-query position, not site-wide impressions or average position. The agent should annotate that date automatically.

### Gaps
- Striking-distance (positions 8–20) wins with reported results were not found; Reddit/YouTube would be the source.

---

## 9. AI Overviews / AI Mode impact on impressions & CTR

### Takeaway
AI Mode data counts inside the Web search type. AI Overview links share one position. A newer Generative AI report shows impressions only. The community pattern is "impressions up, clicks down" (the "great decoupling"), with large CTR losses on queries that show an AI Overview.

### Cited Findings
- **AI Mode in GSC:** Google confirmed GSC counts AI Mode, grouped with "Web". Clicks on external links count, and position follows the normal SERP methodology. All links in an AI Overview get that block's position, and AI Mode follow-up questions reset positions. — [SER](https://www.seroundtable.com/google-search-console-counting-ai-mode-39599.html); [Glenn Gabe/GSQI](https://www.gsqi.com/marketing-blog/ai-mode-tracking-google-search-console/); [Brodie Clark experiment](https://brodieclark.com/ai-mode-google-search-console/); [JC Chouinard](https://www.jcchouinard.com/google-search-console-ai-mode-click-tracking/)
- **Dedicated AI report:** a separate Generative-AI report shows impressions only, combining AI Overviews and AI Mode with no clicks. — [CrawlRaven](https://crawlraven.com/blog/gsc-ai-performance-reports); [DEV](https://dev.to/shanzysaleem/search-console-now-shows-your-ai-overviews-impressions-here-is-what-id-actually-do-with-that-316d)
- **Same-URL counting:** the same URL in an AI Overview and a blue link counts as one impression. — [ALM Corp](https://almcorp.com/blog/google-search-console-ai-overviews-blue-links-same-url-impression-counting/)
- **CTR impact (Ahrefs):** about 34.5% lower CTR for the #1 result when an AI Overview shows (mid-2025), and 58% in the December 2025 re-run. AI Overviews let several cited URLs "share" impressions, which inflates impressions. BrightEdge claimed +49% impressions. — [Ahrefs](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update); [Ahrefs decoupling](https://ahrefs.com/blog/the-great-decoupling)
- **Dynamic link placement** inside AI Overviews makes GSC tracking tricky. — [SER](https://www.seroundtable.com/google-ai-overviews-search-console-tracking-tricky-40433.html)

### Gaps
- No direct Reddit or YouTube practitioner case data was read. A DEV post's claim that Mueller (Sep 2026) said AI-surface position tracking is hard was not verified.

---

## 10. Site migrations & core-update drops

### Takeaway
Migrations can look done and then fail months later, with the new domain turning into CCNI and the old domain being re-indexed. Core-update diagnosis in the community is "compare windows by clicks per page/query", with care around GSC glitches.

### Cited Findings
- **r/SEO war story (covered 13 Oct 2026):**
  - Domain moved at the start of 2026 with redirects and Change of Address. By April the new domain was recovered at about 5k impressions a day.
  - About 4 months later, over 5,000 new-domain pages went to CCNI and impressions fell to about 20 a week, while Google re-indexed the **old** domain.
  - Mueller: things "sometimes… take a particularly long time" to process; set Change of Address for **both www and non-www**. Barry Schwartz doubted the www advice explained it.
  - Marie Haynes: a migration triggers a fresh quality assessment. Glenn Gabe and Barry have also heard of migrations going wrong months later.
  - — [SER](https://www.seroundtable.com/google-search-old-domain-42279.html); [r/SEO original](https://www.reddit.com/r/SEO/comments/1x2wm8u/google_search_randomly_started_indexing_posts/)
- **Core-update diagnosis:**
  - Compare 28 days (or 3 months) before vs after, and rank affected pages by **lost clicks, not lost position**.
  - Steep drops seen on 15 Sep 2025 were reportedly a GSC reporting glitch, not an update.
  - The December 2025 core update rolled out over 18 days from 11 Dec. Hit-rate figures vary between sources (unverified).
  - — [Dataslayer](https://www.dataslayer.ai/blog/google-core-update-december-2025-what-changed-and-how-to-fix-your-rankings); [ALM Corp](https://almcorp.com/blog/google-december-2025-core-update-complete-guide)

### Gaps
- No Glenn Gabe primary case study was retrieved, and no dated, numbered core-update recovery stories from Reddit or X. CWV, Links, Enhancements and Manual-action field stories were **not found** in this pass (beyond HN mentioning the back-button-hijacking spam policy, [HN 47760764](https://news.ycombinator.com/item?id=47760764)).

---

## 11. Common myths & mistakes, with the corrective consensus

### Takeaway
The recurring errors are treating GSC statuses as per-URL bugs, using the wrong removal tool, and misreading aggregate metrics after Google-side counting changes.

### Cited Findings
- **Myth: spam "Request Indexing" to fix indexing.** Correction: it doesn't scale and doesn't change canonicals; fix quality, links and sitemaps. — [SER 2026](https://www.seroundtable.com/google-force-indexing-40963.html); [SER 2024](https://www.seroundtable.com/google-request-indexing-does-not-change-canonicalization-37676.html)
- **Myth: robots.txt removes indexed pages.** Correction: use noindex while the page stays crawlable. Blocking can produce "Indexed, though blocked". — [SER](https://www.seroundtable.com/unindex-pages-google-search-31050.html); [GitHub #61850](https://github.com/vercel/next.js/discussions/61850)
- **Myth: the Removals tool deindexes permanently.** Correction: it is temporary; pair it with noindex, 404/410 or a redirect. — [Patrick Stox](https://patrickstox.com/technical-seo/how-search-works/indexing/how-to-deindex/)
- **Myth: "Validate Fix" makes Google index pages, or "Failed" means the fix was wrong.** Correction: it samples URLs, takes days to weeks, and fails fast if the fix isn't live. CCNI/DCNI are rarely fixed this way. — [Google help](https://support.google.com/webmasters/answer/9216203?hl=en); [Koval SEO](https://kovalseo.com/blog/search-console-validation-failed/)
- **Myth: higher average position after Sep 2025 means rankings improved.** Correction: the `num=100` removal took deep scraper impressions out of the average. — [SEL](https://searchengineland.com/why-google-search-console-impressions-dropped-interpret-data-463677)
- **Myth: impressions up means visibility up.** Correction: AI Overview impressions are shared and inflated while CTR drops. — [Ahrefs](https://ahrefs.com/blog/the-great-decoupling)
- **Myth: CCNI/DCNI are technical errors to fix one by one.** Correction: at scale they reflect site quality or crawl demand. — [SER 2026](https://www.seroundtable.com/google-crawled-not-indexed-quality-ai-content-41701.html)
- **Mistake: blocking `/_next/static` in robots.txt** to stop soft 404s. Correction: it breaks rendering; use skew protection and error boundaries. — [GitHub #78288](https://github.com/vercel/next.js/discussions/78288)
- **Mistake: query-only noindex on `_rsc`.** Correction: it also noindexes the HTML; add the `RSC: 1` header condition. — [GitHub #61850](https://github.com/vercel/next.js/discussions/61850); [DBLScanner](https://dblscanner.com/blog/nextjs-rsc-query-param-indexed)
- **Myth: an unfrozen Page Indexing report is the first signal.** Correction: the Performance report shows indexing changes first. — [SER Oct 2026](https://www.seroundtable.com/google-downplays-importance-of-fresh-index-reporting-42381.html)

### Inferences
- Each of these should be a guardrail in the automation: refuse or flag the action, and explain why to the user.

### Gaps
- No quantified evidence on the harm from over-using Request Indexing.

---

## 12. Recurring questions the community can't answer (the automation should explain these)

### Takeaway
The same unanswered questions keep coming back. The agent should give users Google's stated position and say plainly what is uncertain.

### Cited Findings
- **"Why did my whole site drop out of the index suddenly, with no manual action?"** Unresolved in the 2025 HN threads; all causes offered there are speculation. — [HN 46239752](https://news.ycombinator.com/item?id=46239752); [HN 48210263](https://news.ycombinator.com/item?id=48210263)
- **"Why do `_rsc` URLs exist and what's the canonical fix?"** Asked again in Apr 2025 and Feb 2026 with no definitive answer. — [GitHub #61850](https://github.com/vercel/next.js/discussions/61850)
- **"Why are valid Next.js pages soft 404s?"** Unresolved at framework level as of May 2026. — [GitHub #78288](https://github.com/vercel/next.js/discussions/78288)
- **"How long should DCNI/CCNI last, and can I bulk request indexing?"** No bulk option; status "can be forever". — [Shopify Community](https://community.shopify.com/t/gsc-1000-pages-affected-by-crawled-currently-not-indexed/255140); [SEJ](https://www.searchenginejournal.com/google-says-discovered-currently-not-indexed-status-can-last-forever/439104/)
- **"Why is my report stale?"** Google won't commit to freshness timings. — [SER](https://www.seroundtable.com/google-downplays-importance-of-fresh-index-reporting-42381.html)
- **"How many of my clicks or impressions come from AI Overviews?"** Not separable in GSC: the AI report shows impressions only. — [Ahrefs](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update); [CrawlRaven](https://crawlraven.com/blog/gsc-ai-performance-reports)
- **"Why did a finished migration unravel months later?"** Unanswered. — [SER](https://www.seroundtable.com/google-search-old-domain-42279.html)

### Gaps
- **Sources not reached in this pass:**
  - Reddit, read directly (blocked to the tool).
  - YouTube transcripts.
  - X/Twitter threads.
  - BlackHatWorld and Warrior Forum.
  - Slack/Discord recaps.
  - Individual Google Search Central Help Community threads with Product Expert answers (only a community guide was found).
- **Features with little or no field evidence found:** Core Web Vitals, the Links report, Enhancements/structured data, Manual actions, OG-image routes, striking-distance results.
- A follow-up pass using a browser or an approved Reddit/YouTube data source would be needed to fill these gaps.
