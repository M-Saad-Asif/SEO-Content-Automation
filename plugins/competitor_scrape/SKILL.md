---
name: seo-competitor-scrape
description: Read the pages ranking in Google's top 10 for a keyword. Their outlines (H1–H4), main-content paragraphs, lists and tables, and word counts, with navigation, footers, ads, forms and boilerplate stripped. Pages that block scripts are recorded and skipped, never worked around. Use when building a content brief or knowledge graph.
---

# Competitor scrape: what the ranking pages actually say

**Script:** `run.py`. It sends eligible top-ten organic result URLs to Spider in deep mode (five in quick), plus up to four PAA source URLs and two related-search source URLs in the same bounded wave (quick: two PAA, no related sources). All question/query text remains available even when a supplement exceeds the budget. Unavailable rendering falls back to one direct HTTP attempt; refresh propagates to both paths.

**Output:** `research/competitor_scrape.json`, containing `pages` (url, domain, position, kind, title, outline, words, tables, blocks), `skipped` (with reasons) `median_words`, and `acquisition` (requested URLs, mode and supplement budget). Read pages carry final_url, via and source_role. Not every SERP result is guaranteed readable; all omissions are explicit in article_context.json.

## What is taken
- Headings H1–H4 in order: the outline.
- Main-content blocks: paragraphs, list items, table cells, definition lists, blockquotes, figure captions.
- When a page marks up `<main>` or `<article>`, only blocks inside it, provided that holds 30%+ of the text. Otherwise the whole body minus chrome.
- Word count from body blocks; table count.

## What is never taken

| Excluded | Why |
|---|---|
| `<nav>`, `<header>`, `<footer>`, `<aside>`, `<form>`, buttons, iframes, scripts, styles | Boilerplate. It pollutes entities and facts |
| The client's own pages | Not competitors. Their data comes from foundation and current_page |
| Video, app store and image results, and PDFs | No article text. Their presence is recorded in the SERP composition instead |
| Pages under 80 words of content (`needs_js`) | JS-rendered shells. Recorded; use another readable page |

## Blocked pages
A page answering 403, 429, a challenge page or a timeout is recorded as skipped with its reason. It is **not** fetched through stealth browsers, rotating proxies, CAPTCHA solving or any other bot-detection bypass. That includes Scrapling's stealth modes. Sites that block scripts get no automated access. The run continues with the readable pages, and the pack lists what wasn't read.

If a blocked page is essential (the dominant top-3 result), the agent may open it in its own browser like a normal visitor and work from what it reads, noting that in the decisions.

## Edge cases

| Situation | What to do |
|---|---|
| Fewer than 3 readable pages | The knowledge graph will be thin. Rely more on official facts. Note it in decisions |
| Page is a forum thread | Kept. Its replies are experiences: attribute them, never treat them as facts |
| Page is a list of links (directory, aggregator) | Kept for outline signals; its text adds little |
| Page is a product or category listing | Outline and specs only; prices aren't used |
| Paywalled or cookie-walled content | Only what's visible counts. Partial reads are noted |
| Multiple pages from one domain | Count them as one domain for consensus (the semantic graph does this) |
| Very long page (5,000+ words) | Kept in full here; the semantic graph caps analysis at 2,500 words a page |
| Table of contents block ("In this article") | Excluded from facts downstream (TOC noise) |
| Dated content ("2023 guide") | Kept, but treat its numbers as possibly stale; official facts win |

## Run it alone
`python scripts/seo.py research <brief> --mode quick`, then read `research/competitor_scrape.json`.
