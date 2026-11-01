# Rendering: does Google see the content? (U-E)

**When to run it:**
- U-A step 4.4;
- "Page indexed without content";
- soft 404s on valid JavaScript pages;
- suspected CDN challenges;
- a big gap between the browser view and Google's snippet.

The API has **no rendered HTML, screenshot, console or resources**. Those exist only in the UI, under View crawled page / View tested page. The screenshot comes only from a successful live test of the mobile version.

## Steps

1. Run `seo.py gsc render <url>`. It compares four things:
   - the raw HTML a browser gets;
   - the raw HTML Googlebot's user agent gets;
   - a rendered copy (Spider, when `SPIDER_API_KEY` is set).

   It flags:
   - a status difference between Googlebot and a browser (a WAF/CDN rule);
   - a 200 bot-challenge page (the worst case);
   - noindex served to Googlebot;
   - main content or an H1 that exists only after JavaScript;
   - almost no words in the HTML.
2. URL Inspection (`gsc data <client> page --page <url>`): check `pageFetchState`, `indexingState`, `googleCanonical` and `lastCrawlTime`.
3. **Ask the user** to open URL Inspection → View crawled page → HTML (and a live test screenshot) and paste the HTML into a file. Diff Google's HTML against the render.
4. Diagnose against Google's list of JavaScript failures:
   - SPA soft 404s;
   - `#/` routing;
   - content that depends on storage or cookies;
   - the renderer (WRS) ignoring cache headers;
   - unsupported APIs;
   - shadow DOM without slots;
   - JavaScript paywalls;
   - a CDN challenge served with 200;
   - Next.js version skew (`crawl.md` CR11).
5. Fix by server-rendering or pre-rendering the main content, H1, links and canonical. Retest.

**Limits.** The live test can't reproduce CCNI, DCNI or "Page indexed without content", and doesn't check canonical selection.

Sources: Google URL Inspection help; Google's JavaScript SEO fixes; Crawling December (CDNs); Next.js #78288; Patrick Rice's "HTML as Google sees it".
