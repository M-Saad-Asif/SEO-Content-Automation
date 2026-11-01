# Question, conversational and site: queries (U-C, PF4, PF5)

## U-C. The user's workflow: question regex → which question pages can rank from a content update

**When.** Monthly. Questions link query data, People Also Ask, FAQ sections and AI-feature fan-out. Quaid treats page-two question queries as "topical readiness".

**Steps** (`seo.py gsc data <client> questions`):
1. Pull `[query, page]` for 3–6 months, `includingRegex` R-Q1, which matches questions at the start:
   `^(who|what|when|where|why|how|which|whose|whom|is|are|can|could|should|would|will|do|does|did|was|were)\b`.
   Add R-Q2 (question word anywhere) for recall, and R-INFO (guides, how-to) for informational modifiers.
2. Aggregate each question with impression-weighted position.
3. **Content-update candidate** (`update`): an informational page serves the question at positions 5–30 [synth].
   - Add an H2 with the exact question, then a 40–60 word direct answer, then the detail.
   - Queue it with `/page-seo <site> | gsc queue questions`. The writers get the question as a planned heading.
4. **New-article candidate** (`new`): no page, or only a money page serves it.
   - Group questions that share entities into one article.
   - Queue with `queue new`. Each becomes a `/page-seo` new page whose research starts from the question.
5. Run R-CONV separately (PF4).

**Caveats.**
- Questions are long-tail, so anonymised loss is high and any regex segment undercounts. Compare segments with each other, not with totals.
- FAQ rich results ended on 7 May 2026. Question H2s are for ranking and AI answers, not FAQ snippets.

## PF4. Conversational queries (Chris Long, Nectiv)

1. Filter with R-CONV, `^(?:\S+\s+){9,}\S+$` (10+ words), with no minimums (`data conversational`).
2. Export the queries and cluster them by theme: brand and competitor mentions, product attributes, problems.
3. Feed the themes into H2s and FAQ topics, and into prompt-tracking candidates.

Nectiv's warning: there is no proof these are LLM prompts, and some contain personal data. Never publish them.

## PF5. `site:` queries

Queries containing `site:` (`data site_operator`) are footprints of LLM fan-out searches (Chris Long). Note which pages answer them, and keep those pages complete and current.

Sources: SEOcrawl, SEOTesting, Sturm and Quaid (E913), Surfer, Nectiv, Google's changelog. Links are in the research report §4.1 and §4.4.
