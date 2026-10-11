---
name: seo-clarity-ux
description: Use Microsoft Clarity behaviour data (scroll depth, engagement time, dead clicks, rage clicks, quickbacks, excessive scrolling) for a page being rewritten, and turn it into concrete structural changes. Use for rewrites, or alone for a page UX review.
---

# Clarity UX

**Routes:**
- **Script:** set `CLARITY_API_TOKEN`, or the variable named in `brief.clarity_token_env` when you have one token per client project. Get it from Clarity project → Settings → Data Export → Generate new API token (admin only). The Data Export API allows **10 requests per day per project**, covers the last 1–3 days only, and takes up to 3 dimensions. Results are cached for 20 hours.
- **MCP:** use Microsoft's official Clarity MCP server (`@microsoft/clarity-mcp-server`) with dimension URL for the last 3 days, then `seo.py ingest <run> clarity_ux <file>` with `{"metrics": <the metrics array the API or MCP returns>}`.

Runs only for `task: rewrite`. A new page has no behaviour yet.

## How metrics become changes

| Signal | Threshold | Change |
|---|---|---|
| Average scroll depth | Under 50% | Answer in the first screen; move the most-searched answers (GSC top and striking queries) higher; cut the intro |
| Dead clicks | 5%+ of sessions, or 5+ | Something looks clickable but isn't (bold text, table cells, icons). Link the obvious targets or stop styling plain text like links |
| Rage clicks | 5%+ | Frustration with an element: check broken links, slow selectors, tables that look interactive |
| Quickbacks | 5%+ | Visitors bounce and return quickly, so the top of the page or a link promise doesn't match intent. Tighten the opening to the exact query |
| Excessive scrolling | 5%+ | People are hunting: add a short contents list or move the key answer up |
| Low engagement time with high traffic | Relative | The page doesn't hold attention: more direct answers, fewer generic paragraphs |

## Edge cases

| Situation | What to do |
|---|---|
| No sessions for the URL in 3 days | No behaviour-based changes. Logged |
| Low sessions (under 30) | Treat signals as hints, not rules |
| URL variants (trailing slash, query strings, www) | Normalised before matching |
| Daily request limit reached | Use the cached result, or skip. Never retry in a loop |
| Problems are design or JS issues (broken selector) | Report them in decisions for the developer; copy can't fix them |

Clarity numbers steer structure; they never appear in the article copy.
