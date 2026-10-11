---
name: seo-info-gain
description: Find information gain beyond Google's top 10. First-hand experience, independent opinion and real-world detail from forums (through Reddit's official API when configured), review sites and independent blogs, kept with sources so it can be attributed. Use when a page needs lived experience, or alone to research what real people say about a topic.
---

# Information gain: what the top 10 doesn't tell the reader

**Script:** `run.py`, deep mode only. It runs Serper searches for `<query> reddit` and either `<query> reviews` (commercial or transactional intent) or `<query> experience forum` (other intents). It reads up to 5 non-top-10 results and merges first-hand Reddit excerpts from `reddit_voice` (official API) when configured.

**Output:** `research/info_gain.json`, a list of `items`, each with url, domain, kind, title, snippet, excerpts and read status.

## What counts as information gain (in order of value)
1. **The client's own data:** products, specs, prices, process, service details (from foundation). Nobody else has it.
2. **Unanswered PAA questions** (semantic_graph `paa_gaps`).
3. **First-hand experience:** "I waited three weeks", "we used the trolley strap". Only from text actually read (excerpts) or Google's snippet.
4. **Independent expert views:** specialist blogs, professional bodies, attributed.
5. **Edge cases and failure modes** competitors skip ("what to do when CEAC shows no record").

## Selection rules

| Keep | Reject |
|---|---|
| Excerpts of 12–90 words that mention the topic and contain first-hand markers (I, my, we, took, waited, got, tried, paid…) | Promotional posts, affiliate roundups, the brand's own forum self-promotion |
| Sources outside the top 10 (new perspective) | Pages already in the top 10 (no gain) |
| The most upvoted and most recent experience (Reddit score, last year) | Anything older than about 2 years for fast-changing rules (fees, policies) |
| Forum, review, independent-blog and specialist-site kinds | Content farms, scraped duplicates, AI-spun pages |

## Writing rules for these items
- **Attribute:** "people on r/ukvisa report…", "one reviewer on Trustpilot…". Never present an experience as a fact or a rule.
- **Paraphrase.** Never quote more than one short phrase.
- **Numbers:** an experience's number ("took 3 weeks") is the reporter's experience. Say so, and never let it stand in for an official processing time.
- **Privacy:** no usernames, no personal details. Subreddit or site name only.
- **Agreement:** one excerpt is an anecdote; several agreeing excerpts are a pattern ("several people report…"). Never invent a consensus.
- **Conflict with official facts:** the official fact stands. The experience may illustrate a caveat ("in practice some people wait longer; GOV.UK's published time is…").
- **Use 1–2 per page** where they genuinely help the reader. Don't decorate.

## Blocked sources
Reddit and many forums refuse scripts. Their data comes only through:
- the official Reddit Data API (`reddit_voice`)
- an MCP server's output ingested with `seo.py ingest`
- Google's snippet

They are never reached through stealth browsers or bypass tools. Without excerpts, use the snippet with clear attribution, or skip.

## Edge cases

| Situation | What to do |
|---|---|
| No usable items | Rely on client data and PAA gaps for gain. Log it |
| Experiences describe a different country or version | Don't use them, or flag the difference explicitly |
| Review site with suspected fake or incentivised reviews (all 5 stars, same week) | Don't use it |
| YMYL topic (health, legal, money, immigration) | Experiences only as context, never as guidance; always next to the official route |
