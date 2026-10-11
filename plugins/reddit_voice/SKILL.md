---
name: seo-reddit-voice
description: Collect first-hand experience from Reddit through Reddit's official Data API (or a Reddit MCP server's output), never by scraping or bypassing blocks. Finds relevant recent threads and their top comments, keeps short excerpts attributed to the subreddit, and feeds info_gain. Use for lived experience on a topic.
---

# Reddit voice (official API only)

**Routes:**
- **Script:** set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` and `REDDIT_USER_AGENT`, from a "script" app at reddit.com/prefs/apps. It uses application-only OAuth and is rate-limited by Reddit. **Commercial use of Reddit data requires Reddit's approval:** check their Data API terms for your use.
- **MCP:** save the threads as `{"threads": [{"url": "...", "subreddit": "...", "title": "...", "comments": [{"text": "...", "score": 0}]}]}`, then run `seo.py ingest <run> reddit_voice <file>`.

**Why not scrape:** Reddit blocks unauthenticated scripts. Getting around that with stealth browsers, proxies or anti-bot tools (Scrapling's stealth modes included) breaks Reddit's access controls and terms. This pipeline uses only the API or the MCP route.

## Selection
1. Search the target query (relevance, past year, posts with 2+ comments, no NSFW). Take the top 5 threads.
2. For each thread, take the top comments by score (score 2+), excluding AutoModerator and deleted comments.
3. Keep excerpts of 12–120 words with first-hand markers (I, my, we, waited, applied, paid, used…) and no links. Up to 3 per thread.

## Use in the article
- **Attribute** to the subreddit ("people on r/ukvisa report…"). Never name users.
- **Paraphrase,** and keep the reporter's numbers as their experience.
- **Never** let an anecdote replace an official rule; place it next to the official route.
- **One anecdote is an anecdote.** Several agreeing comments are a pattern ("several people…").
- **Discard** jokes, venting without information, and advice that contradicts official sources (or mention the contradiction only if it helps the reader avoid a mistake).
