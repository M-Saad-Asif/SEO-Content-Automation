# Rules map: every pipeline rule against Koray Tuğberk Gübür's rules

Where a pipeline rule conflicted with Koray's, Koray's won and the pipeline rule was changed (RULES.md section 7 says
so for any future conflict). Sources: Koray's "Holistic SEO Writing System" (rules 1–14) and his semantic content
writing rules (macro context, question headings, heading hierarchy, source before claim, structured data).

**Status**: *aligned* (the pipeline already said the same), *changed to Koray* (it said something else; now it says
Koray's rule), *added* (new, from Koray), *no Koray equivalent* (accuracy, client, locale or humanization rules Koray
doesn't cover; none of them contradicts his).

**How a rule is enforced, cheapest first** (so rules add quality without adding time):
1. *prevent*: the writer card (`RULES_CARD.md`) or the page plan makes the writer get it right first time;
2. *autofix*: `seolib/autofix.py` rewrites it by script before the check (no fix round);
3. *block*: lint sends the sentence back in the one combined fix task (at most 2 rounds);
4. *warn*: shown to the fixer only to judge; never a round on its own.

## 1. Koray's 14 writing rules

| # | Koray's rule | Pipeline rule | Enforced by | Status |
|---|---|---|---|---|
| 1 | Word sequence: main subject and its defining attributes first | RULES §7.1; card 5b | prevent | added |
| 2 | Be certain: declarations, no "should", "need to", "might", opinions | RULES §2 (judgement as declarations), §7.2; card 5b | prevent; block K10-hedge, K11-opinion | changed to Koray (was "we'd recommend" allowed) |
| 3 | Cut the fluff | RULES §3 (no teasers), §5, §7.3; card 7–8 | autofix ("in order to", "basically"…); block K13-fluff, H10-teaser, H05-meta-commentary, X01-banned-phrase | aligned + autofix added |
| 4 | Numeric values instead of "many", "several" | RULES §7.4; card 5b | block K12-vague-quantity | added |
| 5 | Qualify the instances ("the 3 severe symptoms") | RULES §1.7 (name the condition), §7.5 | prevent; block N04-count-check | aligned |
| 6 | Verbs that fit the context | RULES §3 (real verbs, no nominalisations), §7.6 | warn S07-nominalisation | aligned |
| 7 | Examples right after a plural noun | RULES §7.7; card 5b | block K12 passes when "such as A, B" follows | added |
| 8 | Same part of speech in list items | RULES §7.8; card 5b | block K14-list-mixed | added |
| 9 | First sentence under a heading answers it, in the heading's terms | RULES §3 (rewritten), §7.9, §8b; card 2 | block A03-answer-not-self-contained, H10-teaser; warn Q01, and H08 only for a bare restatement | changed to Koray (was "don't open by restating the heading"; H08 narrowed) |
| 10 | "If" goes second | RULES §2, §7.10; card 5b | autofix (plain "If A, B." flipped); block K04-if-opener | changed to Koray (was allowed) |
| 11 | Anchor text = the target page's title | RULES §6, §7.11; card 4 | block K09-anchor; U11 exempts title anchors | changed to Koray (was "2–6 descriptive words") |
| 12 | Don't delay the answer (~40 words) | RULES §3, §7.12, §8b; card 2 | block S02-snippet-length (over 50) | changed to Koray (was 40–60) |
| 13 | Bold the answer, not the search term | RULES §5, §7.13; card 5b | block K05-bold-search-term; warn K05-bold | changed to Koray (was "bold at most N phrases") |
| 14 | Relevant entities, specific words | RULES §7.14; plan gives each section its entities | warn Q03-entity-coverage; block HU01-could-be-any-page | aligned |

## 2. Koray's semantic content rules

| Koray's rule | Pipeline rule | Enforced by | Status |
|---|---|---|---|
| One macro context per page | RULES §0 (page job), plan.py (one query, one page type) | plan; warn Q02-belongs-elsewhere, Q04-off-topic-heading; block R02-hub-rebuilds-children | aligned |
| Macro to micro order | plan.py: ranking pages' own order, related question headings after their topic | plan | aligned |
| H2s as the reader's questions | RULES §6, card 2 | block H03-question-heading on every page type | changed to Koray (was warn, guides only) |
| One H1 with the central entity | RULES §6 | block H02-h1, K01-query-in-title | aligned |
| No skipped heading levels | RULES §7 | block K16-skipped-level | added |
| No "Introduction", "Overview", "Conclusion", FAQ blocks | RULES §6–7, card 2 | block K03-contextless-heading | changed to Koray (FAQ block allowance removed for guides) |
| Every question gets its own heading where it deserves one | plan.py (every page-one heading and PAA question planned; majority of sites wins) | plan check: missing planned heading blocks | aligned |
| Source before the claim, once per paragraph | RULES §2, §7 | warn K15-source-last; block H07-attribution-density | aligned |
| Contextual bridges between sections | RULES §7 | prevent (no "next, we'll look at": H05) | aligned |
| Facts over opinions and analogies | RULES §1, §2, §7.2 | block K11-opinion, N01-untraced-number, G01-ungrounded-rule | aligned |
| Short declarative sentences | RULES §3 (12–18 average), card 5 | block S01 (over 40), warn E03-rhythm (advice now Koray's) | changed to Koray (was 15–20 and "longer clause-rich sentences") |
| Internal links in main content, in context | RULES §6 | block U08-link-context, U24 warn (no link in the answer sentence), U09 density | aligned |
| Structured data naming the entities | `seolib/schema.py` | script writes schema.json at DONE (Article/Service, about = central entity, mentions = entities on the page) | added |

## 3. Conflicts resolved (Koray wins)

| Was | Now |
|---|---|
| "If you rent, …" openers allowed; RULES §2 example started with "If" | "If" goes second; autofix flips plain cases; K04 blocks the rest |
| "We'd recommend…", "you should…" judgement | Declarations with their condition (K10, K11) |
| Bold limited to a count of phrases | Bold the answer items only, never the search term (K05) |
| Anchors of 2–6 descriptive words | Anchor = target page's title or head phrase (K09; U11 exempts it) |
| Sentence average 15–20; E03 told writers to join sentences | 12–18 average; E03 says vary with conditions and reasons, keep sentences short |
| Snippet answer 40–60 words | About 40 words (35–45), 50 at most (S02) |
| Question headings a warning on guides | Question headings required on every type (H03 block) |
| Compact FAQ block allowed | No FAQ block; each question is its own heading or is answered in its section |
| "Don't open a section by restating its heading" | Answer in the heading's own terms, with the answer itself (H08 fires only on a bare restatement) |
| Site-profile skill: 15–20 average | 12–18 average |

## 4. Pipeline rules with no Koray equivalent (kept; none contradicts him)

| Group | What it covers | Lint IDs |
|---|---|---|
| Page job and client (RULES §0) | the client's offer first and last on commercial pages; never steer the reader elsewhere or write against the client | P01–P05, C01–C02, U14, U16 |
| Accuracy (RULES §1) | every figure from a fact; majority of page-one sites settles disagreements; scope and conditions travel with facts; no copied text | N01–N04, G01, A01–A03, C03, T01–T03, Q04-gsc-query-dropped |
| Links (RULES §6) | only URLs from the link map, no redirects, each page once, sources linked where credited | U01–U24 |
| Locale (RULES §1.13, §4) | the market's spelling, units, currency, authorities | L01–L03 |
| Voice and style (RULES §3–5) | named actors, no trailing ", making it…", no vague "This", no framework labels, no banned words, em-dash and exclamation limits | S03–S07, E01–E09, H01–H06, H09–H11, X01–X05, I01, R01 |
| Coverage (RULES §8) | query in title and opening, secondary queries, planned questions answered, entities | K01–K02, Q01–Q05, W01, M01–M02 |
| Humanization (RULES §5, `plugins/humanize/SKILL.md`) | the University of Maryland / Google DeepMind findings: specific, sourced, limited ideas; no perfect solutions, unconditional forecasts, unnamed experts, made-up examples, stated lessons or circular reasons | HU01–HU08 |

Humanization agrees with Koray throughout: his certainty-with-condition, numeric values, examples after plural nouns
and specific entities are the same signals the research found in human writing.

## 5. Every lint rule (128), by group

- **Page job / client**: P01-brand-late, P01-person-drift, P02-no-client-next-step, P02-no-closing-step, P03-steers-elsewhere, P04-warns-off-client, P05-another-sites-page, C01-banned-claim, C01-client-mention, C01-unapproved-claim, C02-client-positioning
- **Accuracy**: A01-absolute, A02-boundary, A03-answer-not-self-contained, C03-copied-text, G01-ungrounded-rule, N01-untraced-number, N02-hardcoded-price, N03-unsupported-superlative, N04-count-check, T01-check-date, T01-placeholder, T02-unlinked-portal, T03-table-without-source
- **Coverage**: K01-query-in-opening, K01-query-in-title, K02-secondary-query, Q01-question-not-answered, Q02-belongs-elsewhere, Q03-entity-coverage, Q03-planned-question-unanswered, Q04-gsc-query-dropped, Q04-off-topic-heading, Q05-title-misses-query, W01-word-count, M01-title-length, M02-meta-length
- **Headings and structure**: H01-heading-length, H01-title-case, H02-h1, H03-question-heading, H04-title, H06-link-dump, H08-heading-echo, H11-heading-number-unanswered, K03-contextless-heading, K16-skipped-level, R01-repeated-structure, R02-hub-rebuilds-children
- **Koray sentence rules**: K04-if-opener, K05-bold, K05-bold-search-term, K06-acronym, K07-trigram, K08-long-paragraph, K09-anchor, K10-hedge, K11-opinion, K12-vague-quantity, K13-fluff, K14-list-mixed, K15-source-last
- **Sentences and style**: S01-long-sentence, S02-snippet-length, S03-opener, S04-trailing-ing, S05-vague-opener, S06-noun-stack, S07-nominalisation, E01-em-dash, E02-exclamation, E03-rhythm, E04-fragments, E05-opener-monotony, E06-repeated-point, E07-closing-template, E08-bare-yes-no, E08-yes-no-template, E09-fragment-bullets, H01-contrast-framing, H02-self-answered-question, H03-colon-reveal, H04-punchline-closers, H05-meta-commentary, H07-attribution-density, H09-embedded-query, H10-teaser, X01-banned-phrase, X01-known-failure, X02-limited-phrase, X03-framework-label, X04-repeated-opener, X05-bold-label-bullets, I01-internal-code
- **Locale**: L01-locale-spelling, L02-dimension-symbol, L03-locale-units
- **Links**: U01-url-not-in-link-map, U02-redirecting-url, U03-product-to-collection, U04-bare-url, U05-repeated-link, U06-hub-no-children, U07-url-linked-twice, U08-link-context, U09-link-density, U10-link-closer, U11-long-anchor, U12-unlinked-forum-quote, U13-links-replaced-page, U14-commercial-first-link, U15-tracking-parameter, U16-competitor-prominence, U17-link-not-figure-source, U18-named-source-unlinked, U20-inherited-attribution, U21-empty-anchor, U22-anchor-repeated, U23-anchor-two-targets, U24-link-in-answer-sentence
- **Humanization**: HU01-could-be-any-page, HU02-perfect-solution, HU03-unconditional-forecast, HU04-vague-authority, HU05-made-up-example, HU06-stated-lesson, HU07-circular-reason, HU08-no-limits

## Calibration (16 Oct 2026, the 15 finished pages in runs/)

After autofix (0–10 rewrites a page), the Koray, heading and humanization checks left 0–9 blocking sentences a page, about 3 on most (mostly
"If…" sentences too complex to flip safely, "several" without examples, and one "Imagine…" example each on three
pages). No skipped heading levels and no false list (K14) flags after the classifier fix.
