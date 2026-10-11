---
name: seo-site-profile
description: Measure a client website's voice and essence from its own pages (homepage, about page, up to three articles). Sentence length, you/we balance, contractions, heading case, spelling locale and sample passages, so new content sounds like the site. Use before writing for a client, or alone to document a site's style.
---

# Site profile: the client's voice and essence

**Script:** `run.py`. **Output:** `research/site_profile.json`, cached per domain for 30 days at `cache/clients/<domain>.json`.

## What it reads
1. The homepage.
2. An about page (`/about`, `/our-story`, `/who-we-are`).
3. Up to 3 articles: `/blog|/blogs|/guides|/news|/articles|/insights|/post` URLs from the link map, or from the site's post and blog child sitemaps when the link map has none.

Only main-content paragraphs of 12+ words count. Navigation, footers and forms are excluded by the document parser.

## What it measures

| Measure | How the writer uses it |
|---|---|
| Average sentence length | Aim near it, within RULES (15–20 average, cap about 30). A site averaging 11 words reads punchy, so keep sentences shorter |
| Share of sentences with "you" | High means address the reader directly (the default). Low means a more neutral register |
| Share with "we/our" | On service pages, "we" is fine if the site uses it. Elsewhere, use the client name |
| Contractions per 100 sentences | Zero or low means avoid contractions. High means natural contractions are fine |
| Heading case | Our pages use sentence case regardless. An existing live H1 is kept as is |
| UK versus US spelling signals | A cross-check on `brief.locale`. If they disagree, the brief wins, and the mismatch is noted |
| 2–3 sample passages | Match rhythm and directness; never copy their wording or marketing claims |

## Rules and edge cases

| Situation | What to do |
|---|---|
| Fewer than 2 pages readable | The profile is weak. Use RULES defaults (plain, direct, "you") and say so in the decisions |
| Samples are marketing-heavy ("we're dedicated to…") | Take the tone (warmth, directness), not the claims or the banned words |
| Site uses Title Case headings | Still write sentence case, except the live H1, which is kept |
| Site voice conflicts with RULES (exclamation marks, hype) | RULES win. Voice affects rhythm and register, never accuracy or de-AI rules |
| Multi-author blog with mixed styles | Profile the homepage and service pages. Note the mix |
| New site with no content | Defaults, plus the brief's `notes` field if the operator described the tone |

**Never:** invent a brand persona, borrow a competitor's voice, or treat profile samples as facts about the client's services. Services come only from approved claims.

## Run it alone
`python scripts/seo.py research <brief> --mode quick`, then read `research/site_profile.json` or the "client's voice" section of the pack.
