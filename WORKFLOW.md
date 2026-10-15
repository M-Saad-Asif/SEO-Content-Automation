# WORKFLOW — one page, researched like a senior SEO

**How this file is used:** a run is driven by `python scripts/seo.py next <brief>`. It runs every script step itself and prints one task at a time, naming the section of this file to follow. Do that section's agent work only; the commands listed in the sections (research, outline, lint, review, validate, eval) are run by `next`, not by you. This file is the reference for what each step means.

You are the writer. Plugins (in `plugins/`) do the research and the checks. Run every command from the repository root, or call `scripts/seo.py` by its full path from anywhere. Use `python`, or `python3` where `python` is not on PATH.

**Input:** a brief path, for example `briefs/<page>.yaml`. There is one mode: every run does everything, in about five minutes.

## The flow (every run)

| # | Step | Who | Target |
|---|---|---|---|
| 1 | Research: every script plugin, including `serp_facts` (the page-one fact table, disagreements settled by majority) | script | ≤ 45 s |
| 2 | The page plan (`seolib/plan.py`): every heading and question the top 10 cover, merged, one H2 per searcher question, facts and links per heading, split into parts; written into `write_brief.md` | script | seconds |
| 3 | Draft: the plan's parts written at the same time by parallel writers (one writer in tools that can't run agents in parallel); `next` joins them | writers | ≤ 2½ min |
| 4 | One combined check: planned headings missing, lint blocks, claims no fact carries | script → writer | ≤ 60 s, at most two rounds |
| 5 | Validate (re-lint, live links), eval | script | ≤ 15 s |

What used to be separate agent stages is built in. The expert's judgement: the page job, the plan and the authority cautions in the brief. The fact-checker: every figure and claim checked against a fact by script. The internal linker: links planned per heading. So no step waits on another agent. Warnings are logged in the report, not sent back as fix rounds.

**Evidence (RULES section 1, rule 25):** page-one points are validated facts. Where ranking sites disagree, the value most of them state is the fact (seven against three); rank only breaks a tie; a verified authority fact beats any competitor. **Coverage:** nothing a top-10 page covers is left out. Every section, every one-site section and every People Also Ask, related and competitor question is a heading in the plan (merged with its duplicates); questions page one leaves unanswered are the information gain.

**Speed rules:** writers read only `RULES_CARD.md` and the run's `write_brief.md`, write in one go, and stop. No research, rereading or extra files. Never ask the operator anything; decisions are logged in the report.

Timing is automatic: the driver stamps each agent task and script check in `timing.json`.

The numbered sections below are the reference for what each part of the page must do. Sections 2, 2b, 3, 6b, 7a, 7b, 7c and 7d describe the older separate agent stages; their checks now run inside steps 2 to 5 above.

## 0. Page intake (when the request names a page)

Intake also accepts a keyword using a saved website context, a bare domain (homepage), or a website plus a keyword/page list. `seo-context.yaml` binds one client; otherwise a single saved profile is reused. Missing/ambiguous website context is asked for before research. `site` discovers same-site sitemaps/internal links, records the purpose and page catalog, and prepares selected/all known pages without starting articles. The queue resumes through `batch`, completing one page before advancing. Incomplete discovery and unread pages remain explicit. A keyword matching an existing page uses that page's type and retains the operator's keyword; ambiguous page matches require a URL.

`seo.py start` reads the page first and decides its type (service, product, category, home, location, guide, company) from its address, its offer (rates, prices, apply, quote, forms), its markup and its blog furniture, then takes the main keyword from its H1 (else its address). The page type sets how the page is built (RULES, "Fit the page type"); the keyword sets the research. Both are logged and can be overridden in the brief.

## 1. Research (one turn, two calls in parallel)

- `python scripts/seo.py research <brief>` (add `--mode quick` for quick)
- Read `RULES.md`.

The research step runs these plugins in dependency waves:

- **foundation:** the client page, sitemap, products, official facts and vertical checks.
- **site_profile:** the client's voice.
- **serp_intel:** intent, format, SERP make-up, People Also Ask and related searches for the brief's country.
- **query_map:** what goes in this article, what links to an existing page, and what deserves a separate page.
- **competitor_scrape:** the top pages' outlines and content.
- **semantic_graph:** entities, attribute-values, triples, consensus versus unique facts, and gaps.
- **info_gain:** forums, reviews and blogs (deep mode only).

Then read the `writer_pack.md` it prints. It is the only data file you need.

If it prints `BRIEF INVALID` or `BRIEF NOT FOUND`, stop and report it.

## 1b. Connectors (when the pack lists "Connectors not used")

If an MCP server for that connector is attached to you (GSC, DataForSEO, Microsoft Clarity, Reddit), fetch the raw data it describes in `plugins/<name>/SKILL.md`, save it to a file, and run `python scripts/seo.py ingest <run> <plugin> <file>`. Otherwise skip: the run works without connectors. Read a plugin's SKILL.md only when you need to judge an edge case its output raises.

## 2. Research (its own role)

Research is done by a researcher, not by the writer. Where your host can start a separate agent (Claude Code: the `seo-researcher` agent; any host with subagents), start one with the run folder and brief and let it work. Otherwise do it yourself as a separate pass before you think about the article.

The researcher follows `plugins/deep_research/SKILL.md`: it works `runs/<run>/research_plan.md` (written by the research step) like a professional fact-checker, records every usable finding with

```
python scripts/seo.py prep <brief> --add-fact <id> "<claim with its condition>" "<exact words from the page>" <final URL> --scope "<who/what/when it applies to>"
```

for an isolated late fact. For the main research pass, save findings as a list in `research/facts.yaml` and call `prep <brief> --add-facts <file>` once; retry only rejected entries. Write `runs/<run>/research/dossier.md`: the main answer, an evidence-backed answer per question, conflicts and how they resolve, a "do not say" list and the gaps. Nothing reaches the page that is not in the pack's facts or the dossier.

## 2b. Expert review (deep mode; its own role)

An expert reviewer (Claude Code: the `seo-expert` agent; otherwise a separate pass) follows `plugins/expert_review/SKILL.md` and writes `runs/<run>/expert_notes.md`: the answer a practitioner would give, a recommendation for each decision the reader faces, common mistakes, professional warnings, where the answer depends on the case, what the research missed, and the experience the client can genuinely claim. If it lists research gaps, run one more research pass on them.

The writer turns the expert notes into the page's recommendations and cautions, in the client's voice ("we'd recommend…"), and never as first-hand experience the client hasn't supplied.

## 3. Outline (deep mode)

Write `runs/<run>/outline.md`:

- on commercial pages, start with `Page job: <type>; offer facts: <scoped ids>; next step: <verified target or not verified>`. This is a planning note, not page copy. Put offer, process, proof and the next step in their appropriate places for the type; omit sections the product or service does not need

- one H1 (the live H1 when the page exists), then H2s and H3s from macro to micro
- shaped by the writer pack's "Page job": on a service, product, category, location, home or company page the sections follow its structure for that type (the client's offer and next step in the opening, how it works with the client, the rules as cited evidence, the client's step to close); `article_context.json`'s sections and questions fill that structure, they don't replace it
- built from `article_context.json`: its sections prioritise the main task and entity relevance for this page type; competitor order is supporting evidence. Use H2/H3, paragraphs, tables or FAQs as appropriate. Retain all relevant coverage; one-site angles remain available when useful and verified
- resolve every required `coverage_requirements` id: `Coverage: S1,Q003 — body under <heading>, table or FAQ placement` or `Exclude: Q004 — <specific relevance/evidence reason>`. These are planning notes, never publish them. Other questions also need a relevance decision; a question does not automatically require a separate heading on any page type. A question with no verifiable answer or another intent gets a `Skip: <question> — <reason>` line too
- a PAA question that restates the H1 is answered in the opening paragraph: record a `Skip:` line instead of an H2
- an "answer lead" under a question is a source to check, not a fact: verify any number in it with `--add-fact` against its link before using it, and answer for this page's locale (the leads may come from the US SERP)
- prefer a contextual link for a query already served by a client page. Query-map routing is a suggestion: check it against the source context and main task before excluding detail. Record placements or exclusions; the main task is always covered here
- the main task or answer first, in the order the top pages answer it; background and edge cases after
- the expected topics that fit the page type
- one line under each heading naming its fact ids and relevant semantic items: `article_context.json` contains the sections, usable facts, entity/attribute/value inventory, relationships, definitions and source references. Raw parser blocks remain indexed in `research/competitor_scrape.json`; open them only when evidence needs inspection

`next` then runs the outline check and prints any `B` lines to fix.

## 4. Draft (one write)

Write `runs/<run>/draft.md` in a single pass, following RULES.md in full:

- front matter with `title` and `meta_description`, then one H1
- the job the writer pack's "Page job" gives the page (RULES section 0): on a commercial page the client's scoped offer and verified next step near the opening and close; official sources cited as evidence, necessary official actions explained accurately, and material limitations and disclosures retained without repetition
- the dossier's main answer first; its answers per question, its conflict resolutions and its "do not say" list followed exactly
- the expert notes' recommendations, mistakes and warnings, as the brand's view, each resting on the evidence the notes cite
- use the scoped facts, products/checks, verified semantic items, attributed experience and listed links under `article_context.json` usage rules. Repeated competitor claims are evidence leads, not independent verification
- fulfil the coverage plan across the page, including body/table/FAQ answers. Check optional search demand for relevant omissions too. Define unfamiliar entities at the point of use; keep facts and conditions together
- the client's measured voice, written as the page's expert author (RULES section 2): facts in your own words with the source linked, a recommendation for each decision the reader faces, and the client's relevant pages linked where they are the natural next step
- Markdown only (headings, paragraphs, lists, tables); no HTML

Before you lint, reread the draft once as the reader: any two statements that contradict each other, any number given twice with different values, any rule stated more than once, and any sentence that only announces the next one. Fix them in the same pass.

## 5. Lint

`next` runs `seo.py lint` on the draft and prints the blocking lines.

- **B** (block) must be fixed.
- **w** (warn) flags something to judge: fix it when the rule really applies, leave it when the sentence is already clear.

## 6. Humanize (one turn)

Rewrite **only** the flagged sentences, cells or headings, in place, one edit per item, all batched together. Never regenerate the article.

## 6b. Editor's review (one turn)

`next` writes `review.md`: each claim beside the fact it rests on, what the page says about the client beside the approved claims, how each section opens and ends, and what the top pages cover that the page may miss.

- Every **CHECK** line: make the sentence say what the fact says (same group, same condition, same strength, same numbers), add the fact with `--add-fact`, or cut the claim. A CHECK on a number you worked out from facts (RULES 1.3) only needs the arithmetic confirmed and the inputs present in the paragraph.
- Client lines: each matches an approved claim with its conditions.
- Section shapes: if openings or endings repeat a pattern, rewrite some.
- Gaps: cover a missing topic or figure only when it answers this reader and you can verify it.

Then lint again.

## 7. Final verify

`next` runs `seo.py validate`. This re-lints the draft, checks every link is live, and writes `final.md` and `report.md` on PASS. On FAIL, do another round of step 6 and validate again. Stop after three rounds.

## 7a. Expert read (deep mode; its own role, after the first PASS)

An independent senior practitioner (Claude Code: the `seo-expert` agent; elsewhere a fresh chat or pass) follows "Pass 2" of `plugins/expert_review/SKILL.md`: reads `final.md` cold with the business context, searches today's news on the topic, and writes `expert_read.md`: a verdict, the exact lines to change and why, current changes the page must reflect, business fit and duty-of-care warnings. It does not edit the draft; the editor's pass applies it.

## 7b. Editor's pass (one turn, after the first PASS)

Read `docs/EVAL_RUBRIC.md` and read `final.md` once as a hostile senior editor who has the top pages open beside it. Write `runs/<run>/editor.md` with:

- for each rubric criterion, the points you would deduct and the quoted line that costs them
- every sentence that could sit on any page, every sentence whose only job is to carry a link or announce the next one, and every section that ends the same way as another
- every claim that says more than its source (dropped condition, wrong group, softened or strengthened), checked against `review.md`
- a claim ledger: every sentence that states a fact (not your advice or arithmetic) with the fact id it rests on, and a yes/no for "this fact is about the same case" (same process, group, product, vehicle class, tax year). A sentence with no fact id, or a "no", is cut or verified with `--add-fact` before you finish. One unsupported sentence fails the whole page, so this list is not optional
- every limit or threshold written with "or less", "or more", "below", "above": does it match how the fact words it ("at least N" means N itself is allowed)?
- every topic the top pages share that the page leaves out (pack topics, review §4), and every place where a reader would want your recommendation and gets a summary of sources

Then fix `draft.md` in place for each item (cut, rewrite, or add a verified fact), then run `next`, which validates again. One pass only: the goal is the defects a reader would notice, not new content for its own sake.

The editor also writes a `## Coverage` section: every required article-context id with its final-page heading/body/table/FAQ placement or a specific evidence/relevance exclusion. Check that the main task and necessary decision conditions precede background. `done editor` rejects missing required ids.

## 7c. Fact-check (its own role, after the editor's pass)

An independent fact-checker (Claude Code: the `seo-fact-checker` agent; elsewhere a fresh chat, or a pass that does not open the dossier, writer pack or outline) follows `plugins/fact_check/SKILL.md`. `next` writes `verify_sheet.md`: every sentence of `final.md` that may state a fact, numbered C1..Cn, with its links and the closest verified fact. The checker opens the page each claim credits, rewrites or cuts what the source does not say (same number, group, condition, strength and page), and writes `verify.md` with one verdict per sentence: SUPPORTED, ADVICE, FIXED or CUT. `next` then validates the page again.

## 7d. Internal links (the last writing stage)

`next` ranks the client's pages against each paragraph of the finished page (`internal_links_plan.md`). The internal linker follows `plugins/internal_links/SKILL.md` (Koray Tuğberk Gübür's interlinking rules): 3 to 6 contextual links in the main content, each anchored on the target page's main term, no anchor more than 3 times, none in the first sentence under a heading, and logs every decision in `internal_links.md` (links added, not linked, anchors waiting).

## Finish

`seo.py next` prints `DONE` with the paths to `final.md`, `report.md` and `eval.md`. Reply with those paths. Nothing else, and no questions: the decisions are in `report.md`.
