---
name: seo-current-page
description: For page rewrites, read the existing page (outline, main content, word count, title, meta) so the rewrite keeps what already works and fixes what doesn't. Use at the start of any rewrite or refresh.
---

# Current page (rewrite mode)

**Script:** `run.py`. Runs only for `task: rewrite`. **Output:** `research/current_page.json` with outline, words, title, meta and text.

## Rewrite rules
- **Keep what ranks.** Sections and phrases matching GSC top and striking queries stay, improved rather than removed (lint Q04).
- **Keep the URL, and the H1** unless the brief sets `h1`. A changed H1 on a ranking page is a deliberate decision, not a default.
- **Fix what fails:**
  - weak-CTR queries → title and meta
  - Clarity signals → structure
  - query gaps → new coverage
  - lint findings → sentences
- **Remove** outdated facts (re-verified by foundation), duplicated sections, sections answering `separate_page` topics (link them instead) and filler.
- **Length** follows intent and the brief's range, not the old length.

## Edge cases

| Situation | What to do |
|---|---|
| Page not readable (404 or blocked) | Treated as a new page. Logged |
| Page is mostly a tool or selector (little text) | Support the tool; don't bury it under copy |
| Page has structured data or FAQ schema | Copy changes may invalidate it. Tell the developer in decisions |
| Page has user comments or reviews | They aren't the client's copy. Leave them out of analysis |
