---
name: seo-official-facts
description: Find the official sources for a topic automatically and extract their rule and number sentences verbatim as verified, citable facts. Government and education pages in the SERP, the brand's own site for brand queries, and the country's government domain for YMYL topics. Use so every page has primary-source facts without a hand-written source list.
---

# Official facts

**Script:** `run.py`. It adds facts with ids `auto:<domain>:<n>` to `fact_sheet.json` (status `verified`, basis `official_page_auto`), adds the sources to the link map, and writes `research/official_facts.json`.

## Which pages count as official

| Source | Counts when |
|---|---|
| Government (`.gov`, `.gov.uk`, `.gouv`, `.gob`, embassies) and education domains in the top 10 | Always |
| The brand's own domain | The query names that brand ("ryanair cabin bag" → ryanair.com) |
| `<query> site:<country gov domain>` (1 search) | `ymyl: true`, country from the locale |
| Brief `official_sources` | Always (handled by foundation, with declared values) |

**Never official:** law firms, agencies, resellers, forums, news sites, or the client itself. Their statements are claims, not rules.

## Which sentences become facts
- Main-content sentences of 6–45 words that state a rule or a number:
  - modals and limits: must, need to, cannot, only, at least, up to, within, maximum, minimum, valid for, takes
  - prices or fees
  - durations, sizes or percentages
- They must share a content word with the query or its PAA questions.
- Up to 15 per page, ranked by relevance (sentences with numbers first). Kept **verbatim**: the value is the official wording.

## Writer rules
- **Paraphrase freely, but keep the number, unit, condition and scope.** Cite the body ("GOV.UK says…") for rules people act on.
- **Watch scope.** A sentence from a page about one visa type, fare or product does not apply to another. Check the page title shown in the fact's claim.
- **Recency.** The page was fetched today, but the rule may change. For fast-changing fees or limits, tell the reader to check the linked page before acting.
- **Conflicts.** An auto fact versus a declared brief fact: the more specific page wins. Two official pages disagreeing: say what each covers, or leave it out.

## Edge cases

| Situation | What to do |
|---|---|
| Official page blocks scripts | Recorded under `blocked`. Verify the needed fact in step 2 (agent browser, another official page) |
| Official page is JS-only | Same as blocked |
| No official page in reach | Logged. The page relies on declared facts, client data and consensus (no numbers on YMYL pages) |
| A sentence mentions another country's rule | Use it only for that country, and say which |
| Tables (fees by type) | Table cells are read as sentences; keep row context when writing ("for a Standard Visitor visa…") |
