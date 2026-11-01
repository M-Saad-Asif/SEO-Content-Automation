# Crawl Stats, Crawl Budget and robots.txt: an expert diagnostic playbook (GSC Settings → Crawl stats / robots.txt report)

Research date: 2026-11-01. Tag legend used throughout:
- **[API/MCP-automatable]**: an agent can do it without the GSC UI, through the Search Console API (Search Analytics, Sitemaps, Sites, URL Inspection) or by fetching the live site over HTTP (robots.txt, headers, status codes, redirects).
- **[needs logs/crawler]**: needs server or CDN logs, or a site crawler such as Screaming Frog, Sitebulb, Lumar or Botify.
- **[UI-only/manual]**: only visible in the Search Console UI (Crawl Stats and the robots.txt report have no API), or needs the site owner or a developer to act.
- **⚠ HARM RISK**: harmful if applied blindly.

---

## 1. Report scope and the three headline metrics (total requests, download size, average response time). How does response time drive crawl rate?

### Takeaway
Crawl Stats is a 90-day, root-property-only, UI-only report. It counts *requests* (including failed and duplicate ones), not URLs. Average response time is the main lever an SEO controls: Google says slow responses or rising errors make Googlebot "throttle back," and stable, fast responses raise the crawl capacity limit. Google publishes no millisecond threshold. Barry Adams uses ≤600 ms as his practical target and ≤200 ms as the ideal.

### Cited Findings
- The report is "available only for root-level properties", meaning Domain properties or URL-prefix properties at the root. It covers http and https. Child hosts appear under a Hosts list showing the top 20 hosts with traffic in the past 90 days. — [Google, Crawl Stats report help](https://support.google.com/webmasters/answer/9679690)
- **Total crawl requests** counts all crawl attempts, successful or not, including duplicates. It also counts attempts never made because robots.txt was unavailable, DNS failed, the server could not be reached, or a redirect loop was abandoned. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- **Total download size**: a resource that is cached and reused is counted once, when first cached. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- **Average response time** is averaged over all resources fetched, and each linked resource counts as a separate response. Page resources (JS, CSS, images) therefore feed into the average. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- Google says that if a site responds slowly or its server error rate rises, "Googlebot will throttle back its requests". Crawl rate should be fairly stable over a week or two. A sudden drop can come from broad new robots.txt rules, slow responses, rising errors, or lower perceived content quality. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- Crawl capacity limit (hostload): stable or improving response times mean "more connections can be used to crawl". Slowdowns, 5xx errors or 429s mean "the limit goes down and Google crawls less". The limit is shared across all Google crawlers. — [Google, Large site owner's guide to managing crawl budget](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- If URL Inspection shows "Hostload exceeded", Google suggests adding server resources. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Barry Adams: "Idealistic targets are 200ms or faster", but "you should aim for a response time of 600ms or faster". Anything over 600 ms needs fixing, through server-side caching, more hosting capacity or a CDN. — [Barry Adams in WTF is SEO? / SEO for Journalism, 13 Mar 2023](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Google's crawling infrastructure allows higher crawl rates on CDN-backed sites, which it infers from the serving IP. — [Google, Crawling December: CDNs and crawling (Dec 2024)](https://developers.google.com/search/blog/2024/12/crawling-december-cdns)
- Google says the report is aimed at advanced users, and sites under about 1,000 pages generally do not need it. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- Numbers can differ slightly from server logs because some requests go uncounted. If robots.txt has been unavailable for a long time, report totals can be far higher than the requests in your logs, because Google counts crawls it might have made. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)

### Inferences
- Diagnostic: **requests ↓ while avg response time ↑** points to a capacity-limit problem (server or hosting); fix performance. **Requests ↓ with flat response time** points to lower demand (quality, popularity, new robots.txt rules) or a robots.txt or availability incident. **Requests ↑ sharply** points to a new URL space (facets, parameters, RSC payloads, a spam or hacked section), a sitemap or launch event, or spoofed bots (see §11). [UI-only/manual]
- **Download size ↑ with flat requests** means heavier pages or resources, such as uncompressed HTML, big inline JSON hydration blobs, or large images fetched as page resources. Compare bytes per request across periods. [UI-only/manual]
- Response time in this report blends HTML and resources. A slow CDN-hosted image or a slow API endpoint can inflate it, so read the "By file type" examples before blaming the origin HTML server.
- An agent can measure TTFB of key templates directly with timed HTTP fetches using a Googlebot-like UA to corroborate the trend. [API/MCP-automatable]

### Gaps
- Google publishes no numeric response-time threshold. The 200/600 ms figures are Barry Adams's opinion and not Google policy.
- I found no Google statement on how much crawl rate rises per X ms of improvement.

---

## 2. Host status (robots.txt fetching, DNS resolution, server connectivity) and the robots.txt report

### Takeaway
Host status should be green. Each of its three sub-charts has a red threshold line, and a day above the line counts as an issue. robots.txt availability is the critical one. A 429 or 5xx on robots.txt halts crawling for 12 hours, after which Google falls back to a cached copy for up to 30 days. A 404 on robots.txt is fine and means "crawl everything". The robots.txt report, a separate page in Settings, shows fetch status and parse errors for up to 20 hosts. It is UI-only, but an agent can replicate most of it by fetching `/robots.txt` live.

### Cited Findings
- Host status levels: green ("No significant issues… Nothing else to do here"); some issues in the last 90 days but more than a week ago; a recent issue in the last week. "Ideally your host status should be Green." A metric above the red dotted line on a day counts as an issue. Google's example is DNS failing on more than 5% of requests in a day. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- **robots.txt fetching**: these count as successful: 200 (valid, invalid or empty file) and 403, 404 or 410 (treated as no file). These count as unsuccessful: 429 and 5xx. Google uses a robots.txt fetched successfully in the last 24 h. If fetches fail, it stops crawling for the first 12 hours, then uses the last good copy from 12 h to 30 days. After 30 days it crawls without restriction if the homepage is up, or stops if it is not. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- **DNS resolution**: your DNS server did not recognise the hostname or did not respond. **Server connectivity**: the server was unresponsive or gave an incomplete response. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- In By response, "robots.txt not available" is a *bad* status: one day of unavailability halts crawling. This differs from a robots.txt 404, which counts as good. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- The **robots.txt report** shows the robots.txt files for the top 20 hosts in a Domain property, with up to 2 origins (http and https) per host, so up to 40 rows. For each it shows path, fetch status, check time, size and the number of parse issues. Statuses: *Not Fetched – Not found (404)*, *Not Fetched – Any other reason*, *Fetched*. Google "ignores the lines with issues and uses those that it can parse". "Errors prevent a rule from being used. Warnings do not." It keeps 30 days of version history, and you can "Request a recrawl" after fixing a critical error, though this "doesn't guarantee an immediate recrawl". It is available only for domain-level properties. Robots.txt files are not inherited by subdomains or parent domains. — [Google, robots.txt report help](https://support.google.com/webmasters/answer/6062598)
- "Not having a robots.txt file is fine, and means that Google can crawl all URLs on your site." — [Google robots.txt report help](https://support.google.com/webmasters/answer/6062598)
- A CDN or WAF can block Googlebot through 503/429 responses, network timeouts, or 200 responses carrying error text. "Network timeouts from the CDN will cause the affected URLs to be removed from Google's search index." — [Google, Crawling December: CDNs (Dec 2024)](https://developers.google.com/search/blog/2024/12/crawling-december-cdns)

### Inferences
- **Fix, robots.txt fetching red**: make `/robots.txt` a static file served from the edge or CDN, never through an app route that can 5xx. In Next.js `app/robots.ts` this means it should be static or prerendered. Exclude it from WAF challenges and rate limits. Return 200 or 404, never 5xx or 429, and never a 200 HTML error page. Verify with the robots.txt report Fetched status and green host status after 1 to 7 days. Fetch status and headers can be checked [API/MCP-automatable] with repeated live fetches. The report itself is [UI-only/manual].
- **⚠ HARM RISK**: a robots.txt served as an HTML 200 page, such as an SPA catch-all route or a CDN maintenance page, gets parsed as an invalid file. Google ignores lines it cannot parse, so you lose your intended Disallow rules. A robots.txt returning 5xx for longer than 30 days with the homepage down stops crawling entirely.
- **DNS red**: check authoritative DNS uptime and TTLs, plus rate limiting by the DNS provider. Moving to an anycast DNS provider usually fixes it. Confirm against the DNS provider's logs. [needs logs/crawler]
- **Server connectivity red**: look for origin overload, connection limits, firewall drops of Google IPs, or keep-alive and timeout settings. Correlate the date of the red bar with CDN and origin logs. [needs logs/crawler]

### Gaps
- Google does not publish the exact red-line thresholds for robots.txt fetching or connectivity. DNS at 5% is given only as an example.

---

## 3. "By response" breakdown: what is healthy, red flags, causes, fixes, verification

### Takeaway
Percentages are of *requests*, not URLs. Healthy means 200 is the dominant share, with 301 and 304 also acceptable. 404s are often fine. robots.txt not available, 401/407, 5xx, other 4xx, DNS, fetch, unreachable, timeout and redirect errors are all "bad". Google ranks the categories itself but publishes no percentage thresholds. Practitioners treat a large 3xx share and any persistent 5xx as crawl-efficiency problems.

### Cited Findings: Google's own classification
- **Good**: 200 OK (should be the majority); 301/308 permanent; 302/307 temporary (change to 301 if the move is permanent); "Moved (other)" (meta refresh); 304 Not modified. **Possibly good**: 404, where "fixing every 404 is not necessary". **Bad**: robots.txt not available; 401/407 (block in robots.txt or decide whether they should be crawlable); 5xx; other 4xx; DNS unresponsive; DNS error; fetch error (bad port, IP or unparseable response); page could not be reached ("never got to your server, so it will not appear in your logs"); page timeout; redirect error (too many redirects, empty redirect, circular); other error. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- Example URLs "are not comprehensive" and are a weighted sample. A URL missing from the examples does not mean Google did not request it. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)

### Cited Findings: how Google processes each status
- 301/308 are a "strong signal" that the target should be canonical. 302/307/303 are a weak signal. Googlebot follows "up to 10 redirect hops". Content of the redirecting URL is ignored. — [Google, HTTP status codes, network and DNS errors](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- 304 tells the indexing pipeline nothing changed. Indexing signals may be recalculated, but otherwise it has no effect. — [Google HTTP status doc](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- All 4xx except 429 are treated the same, and the doc does not separate 410 from 404. Indexed URLs that return 4xx drop out over time, and crawl frequency for 404s gradually decreases. "Don't use 401 and 403 status codes for limiting the crawl rate." 429 is treated as a server error. — [Google HTTP status doc](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- "5xx and 429 server errors prompt Google's crawlers to temporarily slow down." URLs that keep returning errors are eventually dropped from the index. The crawl rate recovers gradually once 2xx returns. — [Google HTTP status doc](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- If you shed load with 503 or 429, don't do it for more than 2 to 3 days, or Google may crawl less over the long term. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- "A 404 status code is a strong signal not to crawl that URL again." "Soft 404 pages will continue to be crawled, and waste your budget." Avoid long redirect chains. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Barry Adams: most responses should be 200. A large share of 301/302 and 5xx signals crawl problems. Redirects consume crawl budget, so internal links should point at the final URL. 4xx "barely affect crawl budget" but are still worth fixing for users. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Glenn Gabe case study: crawl-stat spikes full of 404s turned out in the logs to come from many non-Google IPs, meaning spoofed "Googlebot". Real Googlebot activity was normal. — [Glenn Gabe, Search Engine Land](https://searchengineland.com/brace-benefit-shock-analyzing-googlebot-crawl-spikes-via-log-files-case-study-278521)

### Per-status playbook (diagnose → fix → verify)
These rows are a synthesis of the sources above. Each row's source is in the cited findings.
| Status | Healthy | Red flag (practitioner heuristic) | Root causes | Fix | Verify | Tag |
|---|---|---|---|---|---|---|
| 200 | Dominant share | 200s whose examples are non-pages (`?_rsc=`, search, facets, OG-image routes, feeds, `wp-json`) | Crawlable URL spaces | Remove link sources first, then robots.txt Disallow (§8). Return 404 for empty facet combos | Examples change after 2 to 6 weeks; logs show fewer hits | Examples: UI-only. Pattern test: API/MCP |
| 301/308 | Small, stable share | Large or rising share (Adams flags "large share") | Internal links to old URLs, http→https and slash/case normalisation, chains | Update internal links, canonicals, sitemaps and hreflang to final URLs. Collapse chains to one hop | Crawler shows 0 internal redirects; 3xx share falls | needs logs/crawler; redirect chains API/MCP via HTTP |
| 302/307 | Rare | Permanent moves served as 302; geo/login/cart 302 loops | Framework defaults, middleware, auth walls | 301/308 for permanent moves; robots.txt block on auth-wall paths | Live fetch shows 301 | API/MCP |
| 304 | Present on large or static sites | 0% on a large, rarely changing site | No ETag or Last-Modified support, or always-changing ETags | Enable ETag and Last-Modified with conditional-request handling (§10) | `curl` with If-None-Match returns 304 with an empty body | API/MCP |
| 404 | Some is normal | Sudden spike; 404s linked internally; spoofed bots | Deleted content, broken internal links, malformed JS-built URLs, hacked or spam URLs | Fix internal links; 301 only where an equivalent exists; leave genuine 404s | Crawler shows 0 internal 404s; log IP verification | needs logs/crawler |
| 410 | Like 404 | n/a | Deliberate removal | Optional. Google says 4xx are treated alike (§10) | n/a | API/MCP |
| 401/407 | ~0 | Any persistent share | Staging, admin or account areas linked publicly | Disallow in robots.txt or remove links | Share drops | UI-only + API/MCP |
| Other 4xx (403, 405, 429…) | ~0 | Any 403 or 429 to Googlebot | WAF or bot rules, rate limiting, geo-blocking | Allowlist verified Googlebot IPs (§11) | URL Inspection live test OK; logs | needs logs/crawler |
| 5xx | ~0 | Any recurring day; correlates with crawl dips | Overload, deploys, timeouts, cold serverless starts | Capacity, caching, error budgets; 503 only for short maintenance (<2 to 3 days) | Host status returns to green | needs logs/crawler |
| DNS / fetch / unreachable / timeout | ~0 | Any | DNS outage, firewall drop, bad IP or port, slow origin | Infra fix; CDN | Host status green | needs logs/crawler. Unreachable requests won't show in logs |
| Redirect error | 0 | Any | Loops (http↔https, slash, locale, consent cookies), empty Location headers | Fix rules; test with a cookie-less client | Redirect checker | API/MCP |
| robots.txt not available | 0 | Any day | §2 | §2 | §2 | UI-only + API/MCP |

### Inferences
- "Page could not be reached" never reaches your logs, so a log-only audit misses it. The Crawl Stats example URLs are the only evidence. [UI-only/manual]
- ⚠ HARM RISK: mass-redirecting 404s to the homepage creates soft 404s, which Google keeps crawling. Only redirect where there is a true equivalent.
- ⚠ HARM RISK: returning 503 or 429 site-wide to "save crawl budget" for more than a couple of days reduces long-term crawling.

### Gaps
- Google gives no percentage thresholds for 3xx, 404 or 5xx shares. No practitioner I found published a sourced numeric threshold for these, other than Adams's qualitative "large share".

---

## 4. "By file type": what "Other" really means (critical for the user's rendering hypothesis)

### Takeaway
File-type percentages are shares of *responses*, not bytes. Google defines **"Other file type" as anything not listed, *including redirect responses*.** A dominant "Other" share is therefore not automatically a client-side-rendering symptom. It can be redirects, fonts, or framework payloads such as Next.js RSC `text/x-component` responses (my inference). The agent must open the "Other" example URLs and classify them before recommending a rendering change. Healthy: HTML should be the largest single type on a content site.

### Cited Findings
- Types: HTML; Image; Video (supported formats only); JavaScript; CSS; PDF; Other XML (XML that is not RSS or KML); JSON; Syndication (RSS/Atom); Audio; Geographic data (KML etc.); **Other file type ("anything else, including redirect responses")**; **Unknown (Failed)** (failed requests). The shares are percentages of responses, not bytes. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- One Search Engine Land writer found every "Other file type" example on their site was a font file, and says it is unclear what the category contains. — [Search Engine Land, "Decoding Googlebot crawl stats data in Google Search Console"](https://searchengineland.com/google-search-console-googlebot-crawl-stats-447267) (as described in search results; the page returned 403 to my fetch, so the author is unverified)
- Barry Adams: HTML should be the most-requested type on news sites. Heavy crawling of JavaScript, JSON or fonts ("Other") leaves less budget for pages, so keep page resources lean. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Resource fetches made during rendering "chip away from the crawl budget of the hostname that's hosting the resource". WRS caches JS and CSS for "up to 30 days", unaffected by HTTP caching directives. Advice: "use as few resources as feasible". Cache-busting URLs force refetches. Hosting non-critical heavy resources on another hostname moves their cost off the main host, but this is "not recommended for critical resources" such as JS and CSS. — [Google, Crawling December: The how and why of Googlebot crawling (Dec 2024)](https://developers.google.com/search/blog/2024/12/crawling-december-resources)
- Next.js App Router: in one site's self-reported Crawl Stats, about 87% of 18.1k Googlebot requests over 90 days were RSC payloads rather than HTML. — [GitHub PR "Stop spending crawl budget on RSC prefetch payloads"](https://github.com/galaxyinfomkt-svg/am-painter-inc/pull/76) (one site, unverified)

### Diagnostic decision tree for a dominant share (Inference, built on the cited definitions)
1. **"Other" dominant** → open the examples:
   - `?_rsc=`, URLs fetched with an `RSC: 1` header, or `text/x-component` responses → Next.js App Router prefetch/RSC waste (§8). The site already uses SSR; the waste comes from prefetching. "Make it SSR" is the wrong fix here.
   - Redirect URLs → treat as a 3xx problem (§3): internal links, http/https, trailing slash.
   - `.woff2` and similar fonts → normal in small amounts. Self-host and use fewer font files or weights; never block them.
   - `/opengraph-image`, `/twitter-image`, `/icon`, `/apple-icon` generated routes, especially with hash or query variants → OG-image route waste (§8).
   - API-like or extensionless endpoints → CSR data calls (see the JSON bullet).
2. **JSON dominant** → CSR or hydration data fetches (`/api/*`, `_next/data/*.json`, Nuxt `_payload.json`, `wp-json`). If these power the *initial* render, the page content depends on client JS. Push for SSR or SSG of primary content (ask the site owner). Do not block these endpoints if they are needed for rendering.
3. **JavaScript dominant** → many chunks, or cache-busted chunk URLs. Reduce bundles and keep chunk hashes stable between deploys where possible. Do not block `/_next/static/` or other JS.
4. **Image dominant** → can be fine for image-search sites. Otherwise check image CDN parameter permutations (`?w=…&q=…`), responsive `srcset` explosion, and Next.js `/_next/image?url=…&w=…&q=…`.
5. **Unknown (Failed)** → cross-reference with By response failures (§3).
6. **Syndication high** → feeds per tag, category, author or comments (WordPress). Consider removing feed links (§8).
- Tags: reading examples is [UI-only/manual]. Classifying a pasted or exported example list and testing whether rules match is [API/MCP-automatable]. Measuring true type shares needs logs. [needs logs/crawler]

### Inferences
- ⚠ HARM RISK: concluding "Other = no SSR" and asking for a framework rewrite without checking the examples can waste a lot of engineering effort. In Google's definition, redirects alone can make up the "Other" share.
- A healthy content site typically shows HTML as the top type, with JS, CSS and images as secondary page resources. No source gives a numeric healthy ratio, so present any ratio target as a heuristic only.

### Gaps
- No Google source confirms which bucket `text/x-component` (RSC) responses fall into. "Other" is my inference from the definition.
- No authoritative numeric "healthy HTML %" exists.

---

## 5. "By purpose": Discovery vs Refresh

### Takeaway
Discovery means a URL Google has never crawled before. Refresh means a recrawl of a known URL. For an established site, refresh should dominate. Barry Adams flags a Discovery share above 10% (refresh below 90%) as a concern for established publishers, because it often means crawl waste on newly generated junk URLs.

### Cited Findings
- Definitions: Discovery means "Google has never crawled this URL before". Refresh is a recrawl of a known URL. If fast-changing pages are recrawled too rarely, include them in a sitemap. A rise in discovery is expected after adding a lot of content or submitting a sitemap. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- "a Discovery rate of more than 10 per cent" (with refresh below 90%) is a cause for concern for established publishers, and a high discovery rate can signal crawl waste. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Google reads sitemaps regularly, and `<lastmod>` helps for updated content. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)

### Inferences
- **High discovery without a matching publishing spike**: open the Discovery examples (filter By purpose → Discovery) and look for parameter permutations, `_rsc`, search URLs, calendar pages, session IDs, or a hacked or spam section. The fix is in §8. [UI-only/manual] and [needs logs/crawler]
- **Very low discovery on a site that publishes a lot**: new URLs are not linked prominently or missing from sitemaps. Add them to sitemaps with an accurate `lastmod` (Sitemaps API submit is [API/MCP-automatable]). Check indexing with the URL Inspection API. [API/MCP-automatable]
- **Very low refresh of key money pages**: the URLs are seen as stale or low-value. Improve internal links and lastmod, and support 304 so refreshes are cheap.

### Gaps
- Adams's 10% figure is for established news publishers. I found no sourced threshold for ecommerce or SaaS.

---

## 6. "By Googlebot type"

### Takeaway
Smartphone should lead (mobile-first indexing). Desktop takes a secondary share. "Page resource load" is rendering fetches, so a high share means heavy pages. AdsBot spikes come from Ads (Dynamic Search Ads). Image and Video bots matter only on media sites. All crawlers share one capacity limit, so a surge from AdsBot or another agent can take capacity from Googlebot.

### Cited Findings
- Types: Smartphone, Desktop, Image, Video. Images or videos loaded as page resources are counted under Page resource load. **Page resource load** covers secondary fetches of resources needed to render the page. **AdsBot** crawls about every two weeks, and spikes usually come from new Dynamic Search Ads targets. **StoreBot** is the product shopping crawler. **Other agent type** covers any other Google crawler. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- The crawl capacity limit is shared across all crawlers. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Barry Adams: Smartphone should be most active and Desktop takes a meaningful share. A high Page resource load share means pages need to be lighter. If AdsBot takes a large share, work with the ads team to tighten campaigns. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Special-case crawlers such as AdsBot "may or may not respect robots.txt rules". Common crawlers "always respect robots.txt rules for automatic crawls". User-triggered fetchers "ignore robots.txt rules". — [Google, Verifying Googlebot and other Google crawlers](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot)

### Inferences
- **Desktop ≥ Smartphone** on a site that has moved to mobile-first: check whether the property is still being crawled mainly by desktop, which is unusual today, and whether mobile templates differ. [UI-only/manual]
- **Page resource load very high**: reduce JS and CSS files, stop cache-busting query strings that change every deploy, and lazy-load below-the-fold media. Do not block resources. [needs logs/crawler]
- **StoreBot high** (ecommerce): this is expected with Merchant Center. Check that `?variant=` and filter URLs are not inflating it (§8).
- ⚠ HARM RISK: `User-agent: AdsBot-Google` must be named explicitly to be restricted, because AdsBot ignores the `*` group. Blocking it can break Ads landing-page checks. Coordinate with PPC before touching it.

### Gaps
- No sourced numeric healthy ratios exist for smartphone vs desktop or for page-resource-load share.

---

## 7. When does crawl budget actually matter? (Google's thresholds)

### Takeaway
Google's guide is aimed at sites with roughly **1M+ unique pages changing about weekly**, **10k+ pages changing daily**, or a large "Discovered – currently not indexed" count. For small sites, Crawl Stats is mostly a *health and anomaly* monitor: errors, robots.txt, WAF blocks, rendering waste. It is not a budget-allocation tool there.

### Cited Findings
- The guide targets "Large sites (1 million+ unique pages) with content that changes moderately often (once a week)", "Medium or larger sites (10,000+ unique pages) with very rapidly changing content (daily)", and sites with a large share of URLs in "Discovered – currently not indexed". These are rough estimates. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Crawl budget is "the set of URLs that Google can and wants to crawl", made up of capacity limit and demand. Demand depends on perceived inventory, popularity and staleness. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Sites under about 1,000 pages generally don't need the Crawl Stats report. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)
- Barry Adams: monitor crawl budget regularly once a site exceeds 100,000 URLs, and more strictly above 1M. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Gary Illyes: "If search demand goes down, then that also correlates to the crawl limit going down." — [Search Engine Journal coverage of Search Off the Record](https://www.searchenginejournal.com/google-explains-when-to-worry-about-crawl-budget/512876/)

### Inferences
- Agent rule: if a site has fewer than about 10k indexable URLs and a healthy host status, frame findings as "crawl hygiene", meaning wasted requests, errors and rendering cost, rather than "crawl budget". Still block obvious infinite spaces, because even small sites can generate millions of facet or search URLs.

### Gaps
- None material.

---

## 8. Crawl-waste pattern library (framework-specific) with robots.txt patterns and risks

### Takeaway
Google's own 2025 data says about **50% of crawling problems come from faceted navigation** and about **25% from action parameters**, followed by irrelevant parameters, calendar parameters and other "weird" URLs. The preferred order of fixes is: (1) stop generating or linking the URLs; (2) make empty or invalid combinations return 404; (3) Disallow in robots.txt for URLs that should never be crawled; (4) canonical or nofollow as weaker, slower aids. Never block resources needed for rendering.

### Cited Findings: Google
- Gary Illyes and Martin Splitt (Search Off the Record, Google's 2025 year-end crawling report): faceted navigation ~50% and action parameters ~25% of crawling challenges. Irrelevant parameters, calendar parameters and other "weird" parameters are also listed. — [Search Engine Land coverage](https://searchengineland.com/googles-biggest-crawling-challenges-are-faceted-navigation-action-parameters-and-more-468186) (secondary sources disagree on the smaller percentages, so use only the 50/25 figures)
- Faceted navigation doc (last updated 2025-12-18; published as part of Crawling December 2024): "there's no good reason to allow crawling of filtered items" if they are not needed in Search. Allow item pages and one unfiltered listing. The example disallows `products=`, `color=` and `size=` while allowing `products=all`. URL fragments are not used in crawling, so fragment-based filters have no crawl impact. Canonical "may, over time, decrease the crawl volume". For nofollow, "every anchor pointing to a specific URL must have" it. If facets must stay crawlable: use the `&` separator (not commas, semicolons or brackets), keep a consistent filter order, prevent duplicate filters, and return **404 for empty, duplicate or nonsensical combinations and non-existent pagination**. Don't redirect them to a generic not-found page. — [Google, Managing crawling of faceted navigation URLs](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation); series post: [Crawling December: Faceted navigation](https://developers.google.com/search/blog/2024/12/crawling-december-faceted-nav)
- Gary Illyes (LinkedIn, 2024): block action URLs such as `?add_to_cart` and `?add_to_wishlist` in robots.txt (e.g. `Disallow: /*?add_to_cart`). Switching them to POST alone isn't enough because crawlers can still issue POST requests. — [Search Engine Journal](https://www.searchenginejournal.com/google-reminds-websites-to-use-robots-txt-to-block-action-urls/519215)
- John Mueller: "You don't need the add-to-cart URLs indexed. Blocking them with robots.txt is fine." — [Search Engine Journal (same article)](https://www.searchenginejournal.com/google-reminds-websites-to-use-robots-txt-to-block-action-urls/519215)

### Cited Findings: Next.js
- vercel/next.js Discussion #61850 (Feb 2024 to Aug 2026, no confirmed full fix, no visible Vercel staff answer): `?_rsc=` URLs show in GSC as "Alternative page with proper canonical tag". What people tried:
  - `Disallow: /*?_rsc=*`: reported to work by Refrezsh (Aug 2024). Another user then saw "Indexed, though blocked by robots.txt" (Oct 2024).
  - Middleware cannot see `_rsc`, because Next strips it from NextRequest.
  - `next.config` redirects with a `has` query condition cut errors from 1,300+ to 402.
  - `prefetch={false}` on `<Link>` stopped the requests.
  - `X-Robots-Tag: noindex` via `headers()` with a `_rsc` condition. A later comment (Aug 2026) warns this also hits the HTML document. It suggests conditioning on the `RSC: 1` request header, because `_rsc` is only a client cache-buster and the server decides an RSC request by the header. That stops indexing but not crawling.
  — [GitHub vercel/next.js Discussion #61850](https://github.com/vercel/next.js/discussions/61850)
- One site's PR: about 87% of Googlebot requests were RSC payloads. It recommends `Disallow: /*?_rsc=` plus `Disallow: /*&_rsc=`, and `prefetch={false}` on large link lists. — [GitHub PR #76](https://github.com/galaxyinfomkt-svg/am-painter-inc/pull/76) (self-reported)
- Next.js official robots docs cover `app/robots.ts` generation but say nothing about `_rsc`. — [Next.js docs: robots.txt](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots)
- ⚠ A tutorial recommends blocking `/*.json$` and `/*.js$` for Next.js to save crawl budget. — [Makerkit](https://makerkit.dev/blog/tutorials/sitemap-nextjs). This conflicts with Google: "disallowing crawling of resources usually causes issues", and content may not be extracted. — [Google Crawling December: resources](https://developers.google.com/search/blog/2024/12/crawling-december-resources). **Do not follow the Makerkit advice.**

### Cited Findings: Nuxt, WordPress, Shopify
- Nuxt writes a `_payload.json` per prerendered or ISR route, which is fetched during client-side navigation. The Nuxt SEO guide says never block `.js`, `.css` or `/assets/`. — [Nuxt prerendering docs](https://nuxt.com/docs/getting-started/prerendering); [Nuxt SEO robots.txt guide](https://nuxtseo.com/learn-seo/nuxt/controlling-crawlers/robots-txt)
- WordPress / Yoast: the crawl optimization settings (free since Yoast 20.4) can remove feed links (global, comments, author, category, tag, taxonomy, search, post type, Atom/RDF). The REST API toggle removes only the `<link>` in the head; it doesn't block `wp-json`. Removing the global feed redirects the feed to the homepage. — [Yoast: Crawl optimization settings](https://yoast.com/help/yoast-seo-settings-crawl-optimization/)
- Shopify's default robots.txt already disallows collection `sort_by` and tag-combination URLs (`/collections/*+*`). Filter URLs (`?filter.v.option…`, `filter.p.…`) canonicalise to the base collection but stay crawlable unless added via `robots.txt.liquid`. `?variant=` is handled by canonical, not robots.txt. A reported bug: the documented `robots.default_groups` can output an older rule set than the live default, so customising can drop current defaults. — [Shopify Community thread](https://community.shopify.com/t/why-does-shopify-disallow-collections-and-blogs-when-i-check-robots-txt/148889); [Shopify dev forum bug report](https://community.shopify.dev/t/robots-default-groups-returns-an-older-rule-set-than-the-robots-txt-shopify-serves-by-default/38352); [Visionary Marketing, Shopify robots.txt deep-dive](https://visionary-marketing.co.uk/blog/shopify-robots-txt)

### Pattern library (synthesis: each row's evidence is cited above or marked as inference)
| Pattern (how it shows in Crawl Stats) | Detect | Safe-ish robots.txt / fix | Risk ⚠ | Tag |
|---|---|---|---|---|
| Next.js RSC prefetch `?_rsc=` (Other/200, high Discovery) | Examples, logs with `RSC: 1` header | `Disallow: /*?_rsc=` and `Disallow: /*&_rsc=`; `prefetch={false}` on mega-menus and long lists | May surface "Indexed, though blocked" (cosmetic). Confirm with a URL Inspection live test that the rendered HTML is unaffected | API/MCP (rule test) + UI |
| Next.js `/_next/static/*` chunks (JavaScript) | Examples | **Do not block.** Reduce chunks; keep build hashes stable | Blocking breaks rendering | n/a |
| Next.js `/_next/data/<buildId>/*.json` (Pages Router, JSON) | Examples, logs | Usually leave allowed. Inference: if logs show heavy volume, reduce prefetch. Block only after a rendering test | Page props may be needed for rendering | needs logs/crawler |
| Next.js `/_next/image?url=…&w=…&q=…` (Image) | Examples | Inference: limit `deviceSizes`/`imageSizes`; consider blocking only if images are not needed in Image search | Blocks image indexing | API/MCP |
| `/opengraph-image`, `/twitter-image`, `/icon` route permutations (Other/Image) | Examples with hash or query loops | Inference: ensure stable URLs without query permutations; Disallow `/*/opengraph-image*` only if not needed (OG scrapers like Facebook don't use Googlebot rules) | Low | API/MCP |
| Nuxt `/_payload.json`, `/_nuxt/*` | Examples | Do not block `_nuxt` assets. Payload blocking unverified, so test rendering first | Rendering | needs logs/crawler |
| Internal site search `/search?q=`, `?s=` (WordPress) (HTML 200, Discovery) | Examples, logs | `Disallow: /search` / `Disallow: /*?s=` plus remove crawlable links to search results | Low, unless search pages are SEO landing pages | API/MCP |
| Faceted filters `?color=&size=`, `?filter.*` (Shopify) | Examples, logs | Google pattern: Disallow facet params, allow one unfiltered listing; 404 empty combos | Blocking facets that have search demand (e.g. "red dresses") loses rankings; whitelist those as static paths | needs logs/crawler |
| Sort/order/view `?sort_by=`, `?order=`, `?view=` | Examples | Disallow (Shopify does `sort_by` by default) | Low | API/MCP |
| Action URLs `?add_to_cart`, `?add_to_wishlist`, `/cart`, `/checkout`, compare, login | Examples | Disallow (Illyes) | Low | API/MCP |
| Session IDs / tracking `?sessionid=`, `?sid=`, `?utm_*`, `?gclid`, `?fbclid` | Examples, logs | Fix the source (don't put UTMs on internal links); canonical; Disallow `/*?*utm_` is possible | ⚠ Blocking UTM URLs prevents Google seeing their canonical, and external links to them lose consolidation (inference) | needs logs/crawler |
| WordPress `?replytocom=` | Examples | Disable threaded-reply links or use the Yoast option; Disallow `/*?replytocom=` | Low | API/MCP |
| WordPress feeds `/feed/`, `/comments/feed/`, `/tag/*/feed/` (Syndication) | Examples | Remove feed links (Yoast). Keep the main feed if it's used for discovery or news | Global-feed removal redirects to the homepage (Yoast) | UI-only |
| WordPress `wp-json` (JSON) | Examples | Yoast only removes the `<link>`. Inference: Disallow `/wp-json/` only if no front-end rendering depends on it (headless or blocks may) | ⚠ Breaks headless or JS-rendered content | API/MCP |
| Tag / author / date archives (HTML) | Crawler | Noindex thin archives, or consolidate; don't Disallow if you want noindex seen | Disallow + noindex conflict (§9) | needs logs/crawler |
| Calendar or date traps `?month=2099-01`, infinite next links | Examples, high Discovery | Cap the range; 404 out-of-range; nofollow plus Disallow on param | Low | needs logs/crawler |
| Infinite scroll `?page=9999` | Examples | 404 non-existent pagination (Google faceted doc) | Don't block valid pagination that links to products | API/MCP |
| Shopify `?variant=` | Examples | Canonical (default); avoid linking variant URLs in collections | Blocking variants can hide variant-specific Shopping data | UI-only |
| Shopify `/collections/x/products/y` duplicate paths | Crawler | Link to `/products/y` in themes | Low | needs logs/crawler |
| Cache-busting params on assets `?v=123` changing per deploy (JS/CSS) | Examples | Stable versioning; Google warns that changing resource URLs forces recrawl | n/a | API/MCP |
| Spoofed-bot "spikes" | Logs vs IP ranges | Verify IPs (§11); block fakes at the WAF | Blocking real Googlebot | needs logs/crawler |

### Inferences
- The OG-image, `_next/image`, calendar, `replytocom`, `wp-json` and UTM rows are partly practitioner synthesis. Their robots.txt lines are not quoted from a named source and must be validated per site.
- Agent workflow: (1) collect example URLs per category (user pastes them or exports from the UI); (2) cluster by path and parameter; (3) for each cluster decide *needed for rendering?* (test with URL Inspection live test / rendered HTML) and *needed in Search?* (check GSC Search Analytics for clicks on that pattern via API); (4) only clusters with "no / no" get Disallow; (5) test the new robots.txt against a sample of important URLs with a RFC 9309 parser before deploying.

### Gaps
- No Google or Vercel official statement on blocking `_rsc` exists. Evidence is community-only.
- No source covers Googlebot and `_next/data` or Nuxt `_payload.json` behaviour.
- I found no primary writing from Koray Tuğberk Gübür defining "cost of retrieval". Only a Kalicube interview title and secondary posts exist ([Kalicube](https://kalicube.com/learning-spaces/knowledge-nuggets/seo/learn-to-balance-the-cost-of-retrieving-pages-versus-not-retrieving-for-google/)), so treat that framing as unverified.
- I found nothing usable from Jes Scholz, Aleyda Solis, Tomek Rudzki/Onely, Dan Taylor, Kristina Azarenko or Botify/Lumar/Oncrawl in the tool budget. A Scholz SEJ "crawl efficacy" URL returned 404.

---

## 9. robots.txt correctness and risks: Disallow vs noindex, resource blocking, "evaporating" budget

### Takeaway
robots.txt controls crawling, not indexing. Disallowed URLs can still be indexed, without content, if linked. A blocked page's `noindex` is never seen. Blocking JS, CSS or data needed for rendering damages indexing. Disallowing a section doesn't move crawl budget to other sections; it "evaporates". Google advises against using robots.txt to temporarily reshuffle budget.

### Cited Findings
- "Blocking URLs with robots.txt prevents Google from crawling them." Don't use noindex to save crawl, because Google still has to request the page. "Don't use robots.txt to temporarily reallocate crawl budget." — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- robots.txt controls crawling, not indexing. "Use noindex if you want to prevent content from appearing in search results." — [Google robots.txt report help](https://support.google.com/webmasters/answer/6062598)
- "disallowing crawling of resources usually causes issues". If rendering-critical resources can't be fetched, Google "may have trouble extracting content of the page". — [Google Crawling December: resources](https://developers.google.com/search/blog/2024/12/crawling-december-resources)
- Barry Adams quotes Google that disallowed crawl budget "basically evaporates" and isn't reassigned. Google may take weeks or months to adjust after a new Disallow. Test changes before deploying. — [Barry Adams, SEO for Journalism](https://www.seoforjournalism.com/p/crawl-budget-barry-adams-seo)
- Google: disallowed URLs do not affect crawl budget. — [SEJ](https://www.searchenginejournal.com/google-disallowed-urls-do-not-affect-crawl-budget/313449/)
- Blocked URLs can still be indexed. — [SEJ, "Google explains why URLs blocked by robots.txt can still be indexed"](https://www.searchenginejournal.com/google-explains-why-urls-blocked-by-robots-txt-can-still-be-indexed/579634/)
- Google's 2025 "Robots Refresher" series: introduction on 24 Feb 2025, robots.txt basics in March 2025, page-level granularity (meta robots and X-Robots-Tag) on 14 Mar 2025, and "Future-proof Robots Exclusion Protocol" on 28 Mar 2025, which references RFC 9309. — [Google, Robots Refresher intro](https://developers.google.com/search/blog/2025/02/intro-robots-refresher); [page-level post](https://developers.google.com/search/blog/2025/03/robots-refresher-page-level)
- Google's robots.txt tester was retired in favour of the robots.txt report. The report shows parse errors and warnings. — [Google robots.txt report help](https://support.google.com/webmasters/answer/6062598)

### Inferences (agent guard-rails)
- ⚠ Never Disallow: `/_next/static/`, `/_nuxt/`, `/wp-content/`, `/wp-includes/*.js`, `*.css`, `*.js`, `/assets/`, fonts, or API endpoints the initial render depends on.
- ⚠ Never Disallow a URL set and noindex it at the same time. Removing already-indexed junk needs noindex first, then Disallow after it drops out, or a 404/410.
- ⚠ `Disallow: /*?` (all parameters) is a blunt instrument. It can block pagination, legitimate filtered landing pages and tracking-tagged inbound links. Prefer named-parameter rules.
- ⚠ Google uses the most specific (longest) matching rule. A broad `Allow` can override a Disallow and the reverse, so test every rule against a list of important URLs before shipping. [API/MCP-automatable] with a RFC 9309 parser
- ⚠ A `User-agent: Googlebot` group replaces the `*` group for Googlebot entirely. Rules in `*` no longer apply to it, so duplicate them.
- Verify: robots.txt report "Fetched" with 0 errors; URL Inspection on sample blocked and allowed URLs ("Blocked by robots.txt" where expected); Crawl Stats examples for the pattern disappear within weeks.

### Gaps
- I did not fetch Google's robots.txt specification page in this pass. The 5xx handling details above come from the Crawl Stats help page.

---

## 10. Status-code efficiency: 404 vs 410, redirect chains, soft 404s, 304 / ETag / Last-Modified

### Takeaway
404 and 410 are treated alike by Google's documented processing; either is a strong do-not-recrawl signal. Collapse redirect chains to one hop (Googlebot gives up after 10). Kill soft 404s because they keep getting crawled. Implement ETag (preferred) plus Last-Modified with correct 304 handling. Only about 0.017% of Google's fetches are currently cacheable, so most sites are leaving refresh efficiency unused.

### Cited Findings
- 4xx (except 429) are all treated the same, and the doc does not distinguish 410. — [Google HTTP status doc](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- 404 or 410 is a strong signal; soft 404s keep being crawled and waste budget; avoid long redirect chains; support 304. — [Google large-site guide](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget)
- Up to 10 redirect hops are followed. — [Google HTTP status doc](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- Crawling December: HTTP caching (9 Dec 2024): Google's crawlers support ETag/If-None-Match and Last-Modified/If-Modified-Since per the HTTP standard. About 0.026% of fetches were cacheable 10 years ago, versus about 0.017% now. "We strongly recommend using ETag because it's less prone to errors and mistakes"; "if you have the option, set them both". If the value matches, return "an HTTP 304 (Not modified) status code with no HTTP body". Require a cache refresh only on *significant* changes; a copyright-year update is "probably not significant". With Last-Modified, also set `Cache-Control: max-age` to the expected number of seconds the content stays unchanged. — [Google, Crawling December: HTTP caching](https://developers.google.com/search/blog/2024/12/crawling-december-caching)
- Gary Illyes (2 Apr 2024) said his mission is to "crawl even less, and have fewer bytes on wire", with smarter "caching and internal cache sharing among user agents". — [Search Engine Roundtable](https://www.seroundtable.com/google-forum-qa-markup-robots-meta-documentation-37156.html), citing [his LinkedIn post](https://www.linkedin.com/feed/update/urn:li:activity:7180832169156562945/)

### Inferences
- Verification is [API/MCP-automatable]. Fetch a URL, capture the `ETag` and `Last-Modified` values, re-request with `If-None-Match` and `If-Modified-Since`, and expect `304` with an empty body. Repeat after a deploy: if the ETag changes with no content change (for example per-request nonces or a build ID in the HTML), the ETag is useless. In Crawl Stats, a non-zero 304 share should appear over the following weeks. [UI-only/manual]
- ⚠ HARM RISK: returning 304 when content *did* change, because of a stale ETag after an edit, freezes Google's copy. Tie ETags to a content hash.
- 410 vs 404: 410 is fine for deliberate mass removals for clarity, but Google's documentation gives no crawl advantage for it. Don't spend engineering time converting 404s to 410s for crawl reasons.
- Soft 404 detection: GSC Page indexing report "Soft 404", which the URL Inspection API exposes per URL. [API/MCP-automatable] Fix by returning a real 404/410 or adding real content.

### Gaps
- I found no recent Google statement quantifying 410's removal speed versus 404.

---

## 11. CDN/WAF blocking, verifying Googlebot, and combining logs with Crawl Stats

### Takeaway
WAFs and bot managers often block, challenge or rate-limit Googlebot. Google wants 503 or 429 for temporary blocks and calls 200-with-error the worst case. Verify Googlebot by reverse plus forward DNS, or by matching against Google's published IP-range JSON files. Crawl Stats is a sample of Google's view that includes requests that never reach you. Logs are the complete server view but can include spoofed bots. Use both.

### Cited Findings
- WAF and CDN blocklists can catch legitimate crawlers. Hard blocks include 503/429, timeouts, and 200 with error text. Soft blocks are bot-challenge interstitials. Use 503 for interstitials; 200 error pages are "particularly bad". Use URL Inspection to check the rendered page; if it shows "an empty page, an error, or a page with a bot challenge," talk to your CDN. Recheck blocklists periodically, since IPs "may end up on a blocklist automatically". Big launches mean "the crawl rate will likely be high for a few days", and cold caches still hit the origin. — [Google, Crawling December: CDNs](https://developers.google.com/search/blog/2024/12/crawling-december-cdns)
- Verification: reverse DNS on the IP must resolve to `googlebot.com`, `google.com` or `googleusercontent.com`, then a forward DNS lookup must match the IP. Or match automatically against JSON range files at `https://developers.google.com/static/crawling/ipranges/` (`common-crawlers.json`, `special-crawlers.json`, `user-triggered-fetchers-google.json`, `user-triggered-fetchers.json`, `user-triggered-agents.json`). Other Google IPs are in `https://www.gstatic.com/ipranges/goog.json`. — [Google, Verifying Googlebot](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot)
- Glenn Gabe: crawl-stats spikes investigated with logs revealed spoofed Googlebot traffic from many IPs. — [Search Engine Land case study](https://searchengineland.com/brace-benefit-shock-analyzing-googlebot-crawl-spikes-via-log-files-case-study-278521)
- Crawl Stats can differ from logs. "Page could not be reached" requests never appear in logs, and robots.txt outages inflate report counts. — [Google Crawl Stats help](https://support.google.com/webmasters/answer/9679690)

### Inferences (how to combine)
- Logs give **full URL-level counts per pattern, real content-types (e.g. `text/x-component`), response times per template, and verified-vs-spoofed split**. Crawl Stats gives **Google-side failures (DNS, unreachable, robots.txt), purpose (discovery or refresh) and Googlebot-type classification**. Join them by date: a spike in Crawl Stats with no matching verified-Googlebot spike in logs means a failure upstream of your server or spoofing. [needs logs/crawler]
- Agent automation: an IP-verification step that downloads the JSON ranges and does CIDR matching is [API/MCP-automatable]. Parsing logs needs access to CDN log exports (Cloudflare Logpush, Fastly, Akamai DataStream, Vercel log drains). [needs logs/crawler]
- ⚠ HARM RISK: blocking by user-agent string alone can block real Googlebot or let spoofers through. Always verify by IP.

### Gaps
- Bot-management vendor docs (Cloudflare, Akamai and others) are linked from Google's post but were not fetched here.

---

## 12. Google's 2024–2026 statements on crawling (timeline)

### Takeaway
Google's direction is to crawl smarter and less, with fewer bytes and more caching. Its guidance has been formalised: the Crawling December 2024 series (resources, caching, CDNs, faceted navigation), the faceted-navigation doc promoted to an official guideline, the Robots Refresher series in 2025, and a 2025 year-end report naming facets (~50%) and action parameters (~25%) as the top crawl problems.

### Cited Findings
- 2 Apr 2024: Illyes wants to "crawl even less, and have fewer bytes on wire", and says Google is crawling about as much as before but with smarter scheduling focused on URLs more likely to deserve crawling. — [SER](https://www.seroundtable.com/google-forum-qa-markup-robots-meta-documentation-37156.html)
- 2024 Search Off the Record: search demand correlates with the crawl limit. — [SEJ](https://www.searchenginejournal.com/google-explains-when-to-worry-about-crawl-budget/512876/); podcast episode "Crawling smarter, not harder" — [libsyn](https://search-off-the-record.libsyn.com/crawling-smarter-not-harder)
- Dec 2024 Crawling December series: [resources](https://developers.google.com/search/blog/2024/12/crawling-december-resources), [HTTP caching](https://developers.google.com/search/blog/2024/12/crawling-december-caching), [CDNs](https://developers.google.com/search/blog/2024/12/crawling-december-cdns), [faceted navigation](https://developers.google.com/search/blog/2024/12/crawling-december-faceted-nav), [recap](https://developers.google.com/search/blog/2024/12/crawling-out-of-december)
- Feb–Mar 2025 Robots Refresher series — [intro](https://developers.google.com/search/blog/2025/02/intro-robots-refresher)
- Faceted navigation doc last updated 2025-12-18 — [Google](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation); see also [SEJ, "Google formalizes decade-old faceted navigation guidelines"](https://beta.searchenginejournal.com/google-formalizes-decade-old-faceted-navigation-guidelines/535586/)
- 2025 year-end crawling report: facets ~50%, action parameters ~25% — [Search Engine Land](https://searchengineland.com/googles-biggest-crawling-challenges-are-faceted-navigation-action-parameters-and-more-468186)
- Google's crawling docs now also live under `developers.google.com/crawling` (for example the faceted-navigation doc at [developers.google.com/crawling/docs/faceted-navigation](https://developers.google.com/crawling/docs/faceted-navigation)) and the IP-range files under `/static/crawling/ipranges/` — [Google, Verifying Googlebot](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot)

### Inferences
- Implication for the agent: Google keeps rewarding sites that make crawling cheap through fast 200s, 304s, few resources and no infinite spaces. Crawl efficiency is increasingly self-service through robots.txt and status codes. The legacy URL Parameters tool is gone, so robots.txt and 404s are now the main controls.

### Gaps
- I did not verify any 2026-specific Google crawling announcements beyond the faceted-doc update date and the Aug 2026 GitHub comments.

---

## 13. Is any of this available via API/MCP? Workarounds for automation

### Takeaway
No. The Search Console API exposes only Search Analytics, Sitemaps, Sites and URL Inspection. There is no Crawl Stats endpoint and no robots.txt report endpoint. An agent therefore needs the user to paste or export Crawl Stats charts and example URLs, or a browser session, and it reconstructs the rest from logs, live HTTP checks and the URL Inspection API.

### Cited Findings
- The Search Console API includes Search Analytics `query`; Sitemaps `delete`/`get`/`list`/`submit`; Sites `add`/`delete`/`get`/`list`; URL Inspection `index.inspect`. There is no crawl stats or robots.txt report endpoint. — [Google, Search Console API reference](https://developers.google.com/webmaster-tools/v1/api_reference_index)

### Inferences (workaround map)
| Need | Workaround | Tag |
|---|---|---|
| Crawl Stats totals, charts, examples | User exports or pastes from the UI (each table has an export option), or browser automation with the user's consent | UI-only/manual |
| robots.txt status | Live fetch `/robots.txt` for every host and protocol, plus status, content-type, size and parse with a RFC 9309 parser | API/MCP-automatable |
| Per-URL last crawl time, crawl allowed, page fetch state, robots.txt state, Google canonical, soft 404 | URL Inspection API (`index.inspect`) on sampled URLs and patterns | API/MCP-automatable |
| Do junk URL patterns get clicks? | Search Analytics API filtered by page regex (e.g. `_rsc`, `?s=`) | API/MCP-automatable |
| New-URL discovery speed | Sitemaps API submit plus URL Inspection "last crawl" polling | API/MCP-automatable |
| Full crawl distribution, content types, spoof detection | Server or CDN logs with IP verification against Google's JSON ranges | needs logs/crawler |
| Redirect chains, internal 404s, internal links to junk params | Site crawler (Screaming Frog, Sitebulb, Lumar, Botify) or a scripted crawl | needs logs/crawler |
| 304 support, TTFB, WAF behaviour toward Googlebot UA | Scripted HTTP requests. Note that a WAF may treat a fake-UA request from a non-Google IP differently, so confirm with a URL Inspection live test | API/MCP-automatable |

### Gaps
- I did not verify current URL Inspection API quotas in this pass. Check the [API usage limits page](https://developers.google.com/webmaster-tools/limits) before designing sampling.
