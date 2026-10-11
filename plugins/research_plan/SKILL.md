---
name: seo-research-plan
description: Script stage that turns the research step's data into research_plan.md, the question tree the deep_research agent works through. Runs automatically inside `seo.py research`; read this only to understand or change what the plan contains.
---

# Research plan (script stage)

`run.py` writes `runs/<run>/research_plan.md` and `research/research_plan.json` after the other research plugins finish. It adds no knowledge of its own: every line comes from this run's data, so the plan has the same shape for any query, client or country.

## What the plan contains

1. **Questions the page must answer.** The target query plus the People Also Ask questions that `query_map` kept as headings. These come from search demand, not from a topic list.
2. **Questions from five readers.** A beginner, a practitioner, an authority, a skeptic and a buyer. The researcher writes two or three questions for each, the multi-perspective questioning that makes research go deeper than the obvious "what" and "when" questions.
3. **Topics most ranking pages cover.** Heading topics shared by 40% or more of the readable ranking pages (scraped clones removed). The page covers each with evidence or records why not.
4. **Figures several pages state.** Consensus figures from `semantic_graph`. The researcher traces each one upstream to whoever measured or set it, because ranking pages often repeat one another.
5. **Facts already gathered.** Grouped by source kind, with a reminder to check each one's scope: who, what and when it applies to, and whether the extract dropped a condition from its sentence.
6. **The client's own pages on this subject.** Read first, so the page leads with the client's sound method and never contradicts it.
7. **Where to look first.** The authorities and independent organisations that rank for this query, then the maker's own documentation for any product the page names.
8. **Already decided or flagged.** The scripts' decisions (same-topic pages, missing authors, dropped claims).

## When to change it

Change `run.py` when the researcher keeps missing a kind of question that the run's data could have pointed to. Keep it data-driven: no topic words, no client names, no country-specific lists beyond what `seolib.domains` already holds as world data.
