# serp_facts — the points page one has already validated

## Why

Google already ranks ten pages for this query in this market. A point those pages make is validated evidence for
this page: it does not need a separate research trip, and leaving it out loses information the reader (and Google)
already expects. Information gain comes on top of that baseline (People Also Ask, related searches, the client's own
experience), never instead of it.

## What it does

1. Reads every page competitor_scrape rendered (pages written for another market are left out on YMYL topics,
   as the knowledge graph decides).
2. Takes the sentences that state something: a figure (number with a unit or currency), a rule or instruction
   ("must", "avoid", "water every…"), or a definition. Promotions, author boxes, comments, a site's claims about
   itself ("we", "our") and questions are skipped. A sentence that points back ("This takes…") is joined to the
   one before it.
3. Clusters statements of the same point (shared content words; figures of the same unit) and counts the distinct
   ranking sites that make it.
4. **Conflicts:** when sites give different figures for the same point, the statement from the higher-ranked page
   is the fact; the others are kept in `conflicts` (not usable).
5. **Authorities:** when a verified authority fact (official_facts, or one the researcher added) gives a different
   figure for the same point, the competitor point becomes `serp_overridden` (not usable) and the authority stands.
6. Writes each point to `fact_sheet.json` as `serp:<n>` with `status: serp`, its source page, `rank`, `domains` and
   `consensus` (number of sites). Up to ~110 points; every ranking page keeps up to four of its own.

## How the writer uses them

- `serp` facts are usable like verified facts: state them in your own words. A competitor's wording is never copied,
  and the page never links a competitor as its source (link an authority where one exists).
- The writer's own knowledge is the sanity check: a point that is plainly wrong or outdated is left out and noted
  in the report; it is not "researched".
- A point made by 2+ sites (`consensus` ≥ 2) belongs on the page unless it is irrelevant to this page's job.

## Edge cases

- No readable page one (all blocked): no points; the run relies on authority and client facts.
- A figure stated only by a low-ranked page and contradicted by a higher one: the higher one is used.
- YMYL: authority facts still win; a competitor figure on money/health/legal/safety without an authority match is
  usable but is stated with its condition and never as personal advice.

## Run alone

`python scripts/seo.py research <brief>` runs it with the other plugins; output in `research/serp_facts.json`.
