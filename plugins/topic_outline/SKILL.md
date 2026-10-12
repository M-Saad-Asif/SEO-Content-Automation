---
name: seo-topic-outline
description: Build the full question and topic map of a page from what ranks and what people search. The sections the ranking pages share, macro to micro in the order they put them, with every People Also Ask question, related search, Search Console query and competitor question (headings and FAQ entries) placed in the section that answers it, plus the entities, figures, relationships and verified facts each section needs. Use before writing an outline, or alone as a content brief.
---

# Topic outline: every question, in the sections the ranking pages share

**Script:** `run.py`. **Needs:** `serp_intel`, `query_map`, `competitor_scrape`, `semantic_graph`.
**Output:** `research/topic_outline.json`, incorporated into `article_context.json` with fresh scoped facts and coverage ids before outlining/drafting.

## Sections
1. Every H2 and H3 of every ranking page in this market, with the text under it. Page furniture (widgets, calls to action, "why choose us", testimonials), a competitor talking about itself ("our", "we", "us"), other brands and another market's headings are left out of this shared topical research. This does not remove commercial sections from the client's page: the writer adds its own verified offer, process, proof and next step according to the Page job. A page that hangs seven or more topics under one H2 uses H3 as its section level.
2. Headings cluster across sites when they share their own words (the topic's words are in all of them and say nothing), when related words come with similar text, or when two sites ask the same sort of question (eligibility, cost, process, risk, comparison, how it works, why use, definition) over related text. The sort of question is read without the topic's own words.
3. H3 clusters that mostly sit under one section's H2s become its sub-sections (macro to micro).
4. A section is kept when two or more ranking pages share it, or when a searcher's question needs it (an H2 question, People Also Ask, Search Console, question searches). Others are listed as one-site angles.
5. Competitor median position is an observation. The article-context builder prioritises the main query task, related entities and source support for the actual page purpose. The writer applies that purpose: costs first for a cost query, the offer/action early on commercial pages, necessary warnings beside the affected decision, background later. Scores are editorial hints, not crawler weights.

## Questions
- From the query map, with its routing (H2, in section, link, separate page, dropped) and Google's answer lead; the phrasings it merged stay visible as "also asked as".
- Every question heading and FAQ entry on the ranking pages, not only shared ones; ones that match a planned question add their page count to it.
- Each goes to the section whose headings it shares words with (text refines the choice), else the shared section of the same sort; a search phrasing that is not a question is never a section of its own.
- Separate-page, dropped and other-brand questions are listed with the reason, so the writer sees what was left out and why.

## Per section
The entities the ranking pages use in it, the attribute values from its text, the relationships stated there, and the verified facts whose words match it.
