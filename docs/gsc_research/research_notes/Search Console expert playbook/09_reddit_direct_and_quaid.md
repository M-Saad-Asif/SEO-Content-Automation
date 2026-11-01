# Reddit direct (r/SEO, r/TechSEO, r/bigseo, r/juststart, r/nextjs) and David Quaid (u/WebLinkr) on Google Search Console

Status: NOT RESEARCHED. Reddit refused all direct access from this machine on 2026-11-01, so these notes contain no Reddit findings. Do not cite this file as evidence for any GSC tactic or for any David Quaid view.

## Could Reddit be read directly via its public JSON endpoints?

### Takeaway
No. www.reddit.com blocks unauthenticated JSON requests from this network with HTTP 403, and old.reddit.com redirects them to a login page. As instructed, the research stopped at that point and did not attempt any further workaround.

### Cited Findings
- Request: `GET https://www.reddit.com/r/TechSEO/search.json?q=crawled+currently+not+indexed&restrict_sr=1&sort=top&t=all&limit=5` with User-Agent `gsc-research/1.0 (personal research)`. Result: HTTP 403 and an HTML block page saying the request was "blocked by network security", with an offer to file a ticket if the block was a mistake. — [reddit.com search endpoint](https://www.reddit.com/r/TechSEO/search.json?q=crawled+currently+not+indexed&restrict_sr=1&sort=top&t=all&limit=5)
- Same request on old.reddit.com. Result: HTTP 302 Temporary Redirect to `https://old.reddit.com/login/?reason=lor2&dest=...`, which means the endpoint requires a login. — [old.reddit.com search endpoint](https://old.reddit.com/r/TechSEO/search.json?q=crawled+currently+not+indexed&restrict_sr=1&sort=top&t=all&limit=5)
- User endpoint `GET https://www.reddit.com/user/WebLinkr/comments.json?limit=5`. Result: the same HTTP 403 "blocked by network security" page. — [u/WebLinkr comments endpoint](https://www.reddit.com/user/WebLinkr/comments.json?limit=5)
- 4 requests were made in total, 2 seconds apart. No package installs, proxies, header spoofing or login attempts were used.

### Inferences
- The block covers the whole site and is not specific to the query: both search and user-profile JSON were refused. Retrying the remaining 19 topic queries from this environment would almost certainly fail in the same way, so they were not attempted.
- An earlier researcher found that the web search tool also refuses reddit.com, so this research pipeline currently has no route to Reddit content at all.

### Gaps
- None of the 20 assigned topic queries could be run. These include crawled/discovered not indexed, Google choosing a different canonical, soft 404, regex filters, striking distance, CTR title tests, content refresh, cannibalization, crawl stats "other file type", `_rsc` Googlebot requests, crawl budget, robots.txt blocking RSC, request indexing, the num=100 impressions drop, AI Overview impressions and CTR, core update drops, migrations, "sitemap couldn't fetch" and the Indexing API.
- No field-tested tactics were collected: no step-by-step accounts, site types, results, timeframes, upvote counts or pushback.
- None of David Quaid's (u/WebLinkr) views were collected. That includes his views on crawled/discovered-not-indexed, impressions, average position, request indexing and authority, his "trick" for stuck URLs, and how he reads GSC. None of these should be attributed to him from memory.
- Legitimate ways to fill this gap (each needs the user's decision and none was tried):
  - (a) The user creates a Reddit "script" app and supplies OAuth credentials, then the research uses `oauth.reddit.com`.
  - (b) The user exports the relevant threads manually as saved HTML or JSON for offline reading.
  - (c) Quaid's own published, non-Reddit material is used instead (Primary Position SEO blog and podcast/YouTube). Its claims would need to be labelled as coming from his site, not his Reddit comments.
  - (d) The research is run from a different network that Reddit does not block.
