# Multi-niche test round: pipeline findings

Collected from independent writer subagents (operators) and blind judges. Each finding is fixed with a rule
that holds in every niche, or explained if it is left alone.

## Writer reports

### what-is-a-crm-system (Capsule CRM, SaaS)
1. Pack lists client URLs without trailing slash; validate blocks them as redirects. "Never rebuild a URL" isn't enforced either (adding the slash passed).
2. All 12 facts came from one university article (excelsior.edu) shown as "Official sources"; two are its own adverts; one uses a banned word ("comprehensive"). Education domains are treated as authorities for any topic.
3. Client named Capsule CRM but pack says "(none: do not describe the client's services)" on a CRM vendor's blog.
4. existing_page mapped "what is a crm system and how does it work" to an unrelated "asana vs monday … crm systems" post.
5. Inconsistent routing: "top 5 CRM systems" cover vs "top 5 CRM software" separate; "in real estate" separate vs "in insurance" cover.
6. Junk graph triples ("CRM — be — What", "contact: one roof", "datum: 3,887 customers").
7. Competitor listicle titles appear as expected topics ("19 CRM Features That Will Benefit Your Business").
8. Pack header says "YMYL: auto" while decisions say "YMYL off".
9. --add-fact sources show as "Official sources" with empty titles "(; ok)".
10. --add-fact not_found when the writer's fetch tool paraphrased the page (value must be verbatim; tell the writer).
11. Lint false positives: S04 flags "by adding …, integrating … and tracking …" lists; K06 asks to expand "IBM" (a brand name).
12. WORKFLOW gaps: question-form H1 makes the intro a snippet (40-50 words) without saying so; says run --add-fact "in parallel" though all write one fact sheet.

### how-to-check-tyre-tread-depth (Blackcircles, automotive)
13. Most of 87 "verified" official facts were reader COMMENTS on a gov.uk blog ("Stop moaning .. its illegal to have stretched tyres"). Comment sections must never be official facts.
14. The core legal rule (1.6 mm, central three-quarters) and the obvious official page (Highway Code) were missing; official discovery picked gov blogs instead of the rule pages. Facts lose their qualifier (the 1 mm limit belongs to another vehicle class).
15. All 8 PAA came from the en-US SERP fallback (5/32", penny test); 6 skipped. US-borrowed PAA should be filtered/marked when they assume another country's units/rules, and outline "2/8 covered" passed.
16. Autocomplete for other countries (ireland, australia) marked cover_in_section with no facts to cover them.
17. Client voice sample picked a promo banner ("Today save £25 or more OFF…").
18. Lint false positives: E02 flags brand "THINK!"; K06 flags "THINK"; P01 flags "passenger-carrying vehicles" (a legal category); S06 parsed "r/car"; K07 flags the legal term "central three quarters".
19. WORKFLOW: unclear whether council/campaign sites count as official; "add facts in parallel" again.

## Judge verdicts

### how-to-check-tyre-tread-depth — 52/100, rewrite (blind judge)
Systemic causes (each general, not tyre-specific):
J1. Attribution tic: "According to the blog… The blog says… GOV.UK's testing blog adds…" in nearly every paragraph reads as a research paste. Cause: rules push per-sentence attribution of verified facts. Fix: state verified facts in the page's own voice; attribute only opinions, contested or single-source claims; cite sources once (sources line / inline link).
J2. Client invisible: no brand, no internal links, no next step, ends by sending readers to GOV.UK; and the client ALREADY has a page on this exact topic (cannibalisation). Fix: (a) detect an existing client page for the query (site search + sitemap slug match) and switch to rewrite/flag; (b) always surface the client's relevant commercial pages (products/services/collections) as link targets and a closing next step, even when no approved claims exist.
J3. Industry-consensus guidance missing (replace at ~3 mm, said by nearly every top result) because the pack only offers official facts; numeric consensus from competitors isn't surfaced. Fix: compute numeric consensus (same figure+unit on 3+ independent domains) with context sentences and list it as usable "consensus figures".
J4. Missing conditions on actions (20p test: says what failing looks like, not passing). Fix: rule — every check/test gives both outcomes; outline step names them.
J5. Weak/off-locale sources: Reddit r/CarsAustralia and Irish/Australian hedges on a UK page; Reddit used as authority. Fix: filter forum threads whose community or text names another country than the page's locale; rule — forums for experience only, never for rules or numbers.
J6. Section order buries what the SERP leads with (methods) under legal detail. Fix: pack states the order the top pages answer in; outline check warns when the main task H2 isn't first or second.
J7. Meta-commentary "below"/"covered above"/"More … appear on the same blog" passed lint. Fix: lint blocks signposting phrases.
J8. Unverifiable product claim slipped in ("Continental's UK site adds…") — writer claim not traced to a fact. Fix: lint flags "X's site/guide says/adds" attributions whose source isn't in the fact sheet.
J9. Dated sources with no dates; primary sources (regulations, inspection manual, sector body) missing. Fix: official discovery prefers rule pages (legislation, manuals, guidance) over blogs; carry publication dates.

### what-is-a-crm-system — 56/100, rewrite (blind judge)
Repeats J1 (attribution template in every H2), J2 (brand absent; ends in a link-dump H2), J3 (no expertise/data). New:
J10. Near-verbatim copying of a source's sentence as the opening definition, unattributed ("a set of tools that helps you manage interactions with potential, current and past customers" = Excelsior). Fix: lint blocks 8+-word runs copied from any fact/competitor text unless quoted.
J11. Forced PAA answers produce non-sequiturs ("Operational CRM also answers which CRM is most commonly used" — the question meant which product). Cause: rule that every PAA/keyword variant gets an explicit answer sentence. Fix: PAA answered only where the page can answer it truthfully; variants of the same question share one answer; no keyword-variant sentences.
J12. Core coverage every top page has (features list, how it works with an example, pricing, examples, cloud vs on-prem, AI) missing. Expected topics in the pack were competitor titles/odd headings, not a clean topic list. Fix: cluster competitor H2/H3s into topics with coverage counts; outline check blocks when a topic covered by most top pages is absent.
J13. Named authorities can't be linked (IBM, Microsoft, Salesforce named, not linked) because only pack URLs are linkable; --add-fact sources become linkable but aren't labelled. Fix: every verified fact's source is a linkable citation with its page title.
J14. A misattributed/unfindable quote ("Salesforce frames CRM for beginners as a strategy"). Fix: same as J8 — attributions in prose must match a fact source.
J15. Source quality: a university marketing article treated as "Official source" with adverts. Fix: education domains are official only for rules they set (admissions etc.); otherwise ordinary sources; drop advert/promo sentences from facts.

### how-much-should-i-feed-my-dog (Butternut Box, pets) — writer report
20. Client internal links were all Danish/German locale pages (/da-dk/, /de-de/) plus junk (/da-dk/split-url-test, /da-dk/nay-data-entry); no UK blog pages. Fix: filter the client's sitemap to the brief's locale path (or no locale prefix) and drop test/utility URLs.
21. Pack had 0 facts; writer verified 16. Non-official sources added with --add-fact (a competitor brand, a US site) are labelled "Official sources". Fix: label sources by kind.
22. Off-topic PAA passed ("What words do dogs love to hear the most?" sold as information gain).
23. Contradictory routing: a query marked cover_in_section, but the outline check blocks the H3 that covers it because a near-variant is separate_page; "cups a day" cover vs "cups per day" separate.
24. PAA question whose topic is an existing client page: WORKFLOW doesn't say which rule wins.
25. Imperial units ("pounds") must-cover on an en-GB page; nav-string junk entity ("ALL NEWS SUPERFANS CHARITY…").
26. pdsa.org.uk verified, then validate blocked the redirect to www. Fix: store the final URL after redirects when verifying a fact.
27. N01 checks only the fact's value, not its claim text ("100g" in the claim not counted).
28. Lint FPs: C01 blocks a sentence that only links the client's guide; S04 on a list with no -ing clause; N04 on the reader's own question ("Two cups … a day can be enough?"); A01 on a quoted official "Never …"; rhythm says "write longer" while S01 fires at 36 words.
29. Word count disagrees: lint 1320 vs eval 1079 (eval counts p only).

### how-much-protein-do-i-need-a-day (Bulk, nutrition, YMYL on) — writer report
30. en-GB page but every official figure was US (Harvard/Stanford); the UK reference (RNI 0.75 g/kg) only appeared as a single-source graph item. Fix: official discovery prefers authorities of the page's locale country (data: gov/health bodies of that country); pack groups facts by country and warns when none match the locale.
31. Contradicting sources not flagged (Harvard "RDA 0.8 g" vs Stanford "revised 1.2–1.6"). Fix: detect conflicting figures for the same quantity across facts and list them as contradictions.
32. Junk facts ("Salmonella, E. coli, Cyclospora…", "placental,,", "140 pounds woman"); doubled site name in titles ("Food labels - NHSNHS").
33. Routing contradiction again: "…to lose weight" cover vs "…for weight loss" separate (same intent, different words).
34. Near-duplicate PAA each forced into its own H2 ("Is 100 grams of protein too much?" / "Is it okay to eat 100 grams of protein?").
35. Links marked ok in pack failed validate as redirects (3 sites) → 3 validate rounds against a 2-round limit. Fix: resolve redirects when building the link map/facts (same as #1, #26).
36. --source-text-file crashed on non-UTF-8 input. Fix: read with encoding fallback.
37. PDFs can't be read by the writer's fetch tool; pipeline has no PDF text capture. Fix: fetch/parse PDFs in --add-fact.
38. WORKFLOW "one verification batch" impossible when URLs come from searches in the same batch.
39. Lint FPs: C01 on a sentence that doesn't mention the client; S03 on a gerund subject ("Eating 100 g of protein a day sits…"); N04 on "Two eggs" where the heading is about 2 eggs.

### how-does-pension-tax-relief-work (PensionBee, finance, YMYL on) — writer report
40. ~25 US IRS facts and IRS links offered on a UK page (same as #30: locale-country authorities first; other countries' authorities excluded unless the query names that country).
41. Facts cut from their context: "1% up to… 21%" without "Scotland"; "You must do this within 30 days." / "You do not need to pay the difference." unusable alone. Fix: a fact carries its nearest heading and the previous sentence when it starts with an anaphor (this/that/it/you must do this…).
42. --add-fact verifies only the value; numbers in the writer's claim text go unchecked. Fix: every number in the claim must also appear on the source.
43. PAA H2 vs separate_page contradiction (backdating vs "previous years"); outline counted it as covered when skipped.
44. Voice section: "Measured on 0 of its pages" yet reports averages; samples are legal boilerplate.
45. "Contradictions" lists unrelated numbers (60,270 vs £60,000 vs 100 per cent): contradiction detection must compare the same quantity.
46. Must-cover noise words ("source", "money", "future", "value"); "pension tax credit" routed as same topic though Pension Credit is a different benefit (ambiguous term; SERP overlap should decide).
47. Sentence splitter misses a lower-case sentence start ("… nidirect …") → false 72-word sentence. N04 fired on a count whose members follow a colon.

### how-much-should-i-feed-my-dog — 57/100, rewrite (blind judge)
Repeats J1 (Dogs Trust named 10 times), J2 (brand absent; a competitor is the main source; Danish-locale internal links #20), J3/J12 (no gram-by-size figures the SERP leads with), J7 (meta "table below/above", closing link dump). New:
J16. Exact query forced into the first sentence produces broken grammar ("The question of how much should I feed my dog has no single answer"). Cause: exact-match rule. Fix: the first sentence answers; the query wording appears naturally in title/H1, never forced as an embedded question.
J17. "Answer the H2 in its first sentence" applied mechanically = every section opens by restating its heading as a statement (a template readers notice). Fix: answer directly, but vary: lead with the number, the condition, or the action; lint warns when 3+ sections open with a restatement of their heading.
J18. "X, not Y" negative parallelism habit and generic moralising closers. Fix: H01 counts it once per page already; make it per-article cap 1 and add closing-moral detector (paragraph ending in "matter(s) more than", "is a useful reminder").
J19. Unsourced rules placed beside attributed ones (non-YMYL lint doesn't ground). Fix: G01 grounding check runs for all pages on sentences that state rules/numbers, warn when not YMYL.

### how-much-protein-do-i-need-a-day — 54/100, rewrite (blind judge)
Repeats J1 (34% of sentences open with a source or "Dr"; Stanford named 22 times), J2 (brand absent, no internal links), #30 (US sourcing on a UK page, incl. a "150 lb woman" PAA heading), J7 (meta lines), J11/#34 (four consecutive H2s from one PAA cluster repeating the same figures). New:
J20. No judgement: sets the UK figure against the US figure and never tells the reader which to aim for. Cause: writer relays sources instead of concluding (rules reward attribution, not recommendations). Fix: RULES require a clear recommendation per decision the reader faces, reasoned from the facts (the reasoning may be the writer's; the numbers must be sourced).
J21. YMYL safety condition missing (upper limits, kidney disease) where top results state it. Fix: pack lists "safety/caution" sentences from authorities and top pages; outline step must place them for YMYL topics.
J22. Mislabelled source relationship (RDA "previous" vs Dietary Guidelines) — facts lacked which instrument a number belongs to. Fix: as #41 (facts carry heading/context).

### how-to-clear-cache-on-iphone (iSmash, tech) — writer report
48. "250 verified facts" in research but "Facts you may use" empty: they were all product facts. Products list = ~250 irrelevant repair SKUs incl. "DUMMY SKU", "None Diagnostics", mojibake. Fix: products are listed only when relevant to the query (token overlap with title/type) and capped; drop dummy/placeholder SKUs; fix encoding.
49. Bad existing-page links: "clear cache on iphone 17 pro max" → /collections/iphone-11-pro-max-repairs; Android query → a phone-security post. Fix: existing_page needs the task word too (already in), plus no collections/product pages for informational queries.
50. Apple support page 404 to scripts but readable by the writer; --source-text-file capture then shows the source as "(; error)" and not linkable. Fix: a captured source is linkable and labelled "captured".
51. Uncontradicted contradiction (Proton vs Apple on automatic cache purge).
52. Lint FPs: "Block All Cookies" setting name flagged as overgeneralisation; "addresses" limited-word cap 0 hits the plain noun "saved addresses"; C01 on a link to the client's own guide (again, #28); N04 on a count whose members follow a colon (again, #47); S03 on a gerund subject (again, #39).
53. Timing: --add-fact calls book under "research"; lint takes 10–15 s.
54. WORKFLOW: settings/menu labels — do they need a verified fact? Can a capture be the passages read rather than the full page?

### how-does-pension-tax-relief-work — 57/100, rewrite (blind judge)
Repeats J1 (23 GOV.UK/nidirect attributions in ~1,350 words), J2 (client's own product never described; link-dump final H2), J5 (vague Reddit crowd lines as "experience"), J20 (no worked band table/recommendation). New:
J23. Outdated YMYL guidance: the only source predated a 2024-25 change (low earner top-up). Fix: YMYL research adds a "recent changes" search (query + current/last year + changes/new rules) on the official sites and flags facts older than the newest change.
J24. Compressing two systems into one answer-first sentence made it wrong ("provider calculates basic rate relief…" is only true for one scheme type). Fix: RULES — when the answer depends on a condition, the first sentence names the condition.
J25. Invented urgency ("check it before the tax year closes") contradicting a 4-year backdating rule. Fix: deadlines and time limits are numbers → must be sourced (lint: "before …/by …/within …" deadline phrasing on YMYL needs grounding).
J26. Coverage of the decision-driving subtopics missing (limits, carry forward, taper, salary sacrifice). Same as J12: clustered competitor topics + numeric consensus.

### how-to-clear-cache-on-iphone — 63/100, fix first (blind judge)
Repeats J1 (Apple named 15 times), J16 (query forced in as subject), J17 (heading-restating openers 6+ times), J5 (Reddit crowd lines), J7 (meta "steps below"), J24 (offload and delete lumped into one wrong rule). New:
J27. Client's own expertise unused: the client publishes related guides (restart, free up space) that are first-hand client advice, but the pack only offers them as links. Fix: pull short factual passages from the client's related pages as "client says" facts the writer may use in the client's voice.
J28. Interface paths without version context ("Settings > Apps" exists only on recent iOS). Fix: RULES — UI paths name the version/platform they apply to when the source does.

## Score summary (blind)
tyre 52 · CRM 56 · dog 57 · protein 54 · pension 57 · iPhone 63 — mean 56.5. None pass.

## Round 1 → round 2: general fixes applied (no niche rules)
- RULES.md rewritten niche-neutral: write as the expert (facts in own words, source linked on the claim, ~1 named attribution per section); a recommendation for each decision; worked examples allowed with shown arithmetic; both outcomes for checks; conditions named; locale units/authorities; no 8-word copying; no meta-commentary, colon reveals, link-dump endings; natural-grammar answers (no pasted query); varied section openings; forums = quoted experience only.
- WORKFLOW.md: verification in rounds, add-fact one at a time, verbatim values, PDFs, "official" defined, `Linked:` lines, separate_page beats PAA H2, main task first, 3 validate rounds.
- Client: profile settings now reach lint; sitemap discovery via robots.txt/alternates/homepage links; locale-filtered and junk-free client URLs; homepage self-description usable as client claims; client's own guide passages as facts; same-topic (cannibalisation) detection; next-step pages listed; products filtered for relevance (operator-chosen collections kept).
- Official facts: authorities only (gov/international; universities are sources); authorities from the page's country or a named place; country authority sets (e.g. gov.uk + nhs.uk); comment sections, adverts, fragments dropped; facts carry section heading and the sentence an anaphor needs; rule pages before blogs; spam/booking subdomains filtered; recent-changes search on YMYL.
- SERP/query map: borrowed US PAA filtered for US units/money/places; questions deduped on shared words incl. numbers; near-variant keywords share one SERP verdict; second-hop questions must match a top-page heading; unit normalisation (100g = 100 grams).
- Knowledge graph: consensus figures (number+unit on 35%+ of pages, block-level incl. tables); competitor backfill to 6+ readable pages; foreign forum communities filtered; expert-attribution patterns general.
- Lint: H05 meta, H06 link dump, C03 copied text, H07 attribution density, H08 heading echo, H09 embedded query, G01 on all pages (warn), worked-example arithmetic, ~15 false-positive fixes.
- Tooling: add-fact checks claim numbers, follows redirects, reads PDFs, any text encoding; validate accepts cosmetic redirects; YMYL auto settled once; voice samples skip promos/legal text.

## Round 2 writer reports

### what-is-a-crm-system (R2)
R2-1. Sibling pages list = 876 URLs on one 54 KB line; pack exceeded the writer's read limit; includes the target page itself.
R2-2. existing_page still loose: "how does it work" → asana-vs-monday-do-they-work-as-crm-systems; better matches existed (how-to-implement-a-crm, crm-vs-excel). Fix: slug must not carry many words the query lacks.
R2-3. Source listed at a redirecting URL (Microsoft) — facts' source URLs should be resolved to their final URL at research time too.
R2-4. Salesforce URL rewritten with ?bc=OTH → K06 flagged "OTH" from a URL. Fix: K06 ignores URLs.
R2-5. RULES 1.3 allows shown arithmetic but N01 blocked "$8.71 minus $5.60 is a rise of $3.11" (money path skipped the worked-example check).
R2-6. H08 heading-echo conflicts with RULES 7 "declaration first" and fires on reworded openers. Fix: only near-verbatim restatement, 4+ sections.
R2-7. FPs: S04 on "sales, marketing and service teams"; S06 on "companies run project management tools"; C02 on "Capsule CRM is built to manage…" (passive product description, not a maker claim).
R2-8. Report says "No fact values matched verbatim" (expected now that facts are paraphrased); link line "3/16 return 200" counts cosmetic redirects as failures.
R2-9. KG junk triples persist ("CRM — be — What", "the story CRM — stand for").

### how-to-check-tyre-tread-depth (R2) — validate PASS 0 block / 3 warn, 1,390 words
R2-10. Off-topic authority facts: once the regulated trigger fires, unrelated pages on the same authority (NHS bedroom temperature, falls prevention, a job advert on a careers subdomain, a vision leaflet) become facts. Fix: an authority fact must share topic words with the query/subject (relevance gate on page title+heading+claim), and careers/jobs subdomains are spam hosts.
R2-11. Client guide passages admitted breadcrumbs/headings as "facts" and one wrong paraphrase of the law. Fix: client passages must be full declarative sentences (finite verb, ≥8 words, not a question); label them "client says — check against an authority" so they never outrank an authority.
R2-12. Approved claim vs voice sample disagree (2,300 vs 2,200). Fix: pack flags conflicting numbers in client claims/voice samples; writer uses the approved claim.
R2-13. Pack lists `client_related` URLs but lint's C01 only allows link_map internal list → blocked links the pack offered. Fix: C01 accepts every URL the pack offers (client_related, next steps, guides).
R2-14. Local branch/location pages listed as "guides". Fix: guides exclude URL families that repeat one template with place names (location pages).
R2-15. US-only PAA still reached H2 list (32nds of an inch, US mileage). Fix: foreign() also checks imperial-only measurement words (inch/inches/32nds/miles-per-gallon etc. when the locale uses metric for that quantity) — general unit-system check, not a topic rule. "Numbered screen-by-screen steps" advice must come only for software/UI tasks.
R2-16. Outline cover() missed "How many 32nds…"/"How much tread does a new tyre have" (different wording, same question). Fix: cover() with lemmatised synonyms + 0.5 threshold when the heading shares the subject and the question's head noun.
R2-17. eval "meta-commentary x7" and word count disagree with lint. Fix: eval uses lint's detectors and counts.
R2-18. WORKFLOW says read only RULES + pack, but RULES refers to brief fields → the pack must show banned phrases, reader nouns and banned claims.
R2-19. Same-topic decision left open ("different angle … or rewrite"). Fix: pack states one decision.

### how-much-should-i-feed-my-dog (R2) — validate PASS on 2nd attempt, 0 block / 6 warn, 1,286 words
R2-20. Client URLs in the pack redirect (locale-prefixed /en-gb/ → no prefix); brief page_url 404. Fix: resolve client_related/next-step URLs to their final URL at prep (HEAD with redirects, cap ~40), and drop locale prefixes the live site doesn't use.
R2-21. Duplicate facts in the pack (same claim on www/non-www or two source rows). Fix: dedupe facts by normalised claim text.
R2-22. Dogs Trust / PDSA labelled business_site; YMYL off. Fix: registered charities/non-profits (.org.uk/.org with charity markers) → "nonprofit" kind, counted as authority-adjacent sources (not authorities).
R2-23. Approved claims include page titles ("Fresh Dog Food Delivery | Brand"); client facts are intro boilerplate. Fix: site_says keeps only meta description sentences, not titles with "|".
R2-24. Same-entity client pages irrelevant (dog-ear-positions). Fix: same_topic needs ≥2 query content words beyond the generic entity word.
R2-25. KG junk ("one remedy: one remedy (1)", "meal: the day"), navigation text as a single-source detail.
R2-26. US units in PAA answers and Reddit quotes for an en-GB page → same unit-system check as R2-15 for answer leads and forum quotes.
R2-27. FPs: N01 on "20 kg" present in a verified claim (table cell); A01 on a paraphrase of an approved claim ("all life stages" vs "lifestages"); E03 message "SD 7.3 … target ≥ 7.3" (rounding); K07 "g to g".
R2-28. N01 flags derived numbers whose arithmetic is in the next sentence → _worked() must look at the neighbouring sentence. G01 flags "cut the daily amount slightly and check again" although RULES asks for both outcomes of a check → G01 exempts conditional next-step advice that carries no number/deadline.

### what-is-a-crm-system (R2) — blind judge 64/100, fix first (R1: 56)
Scores: intent 9, coverage 10/15, accuracy 12/15, info_gain 5/10, humanization 8/20, language 6/10, structure 8, brand 3, trust 3.
J29. Answer-first openers forced into object-fronted inversions that restate the H2 entity ("One accurate record … is the main benefit of a CRM system"), query term 13×. Cause: answer-first + heading-echo rules applied mechanically. Fix: RULES — answer in natural word order, subject first; lint flags "<noun phrase> is the <superlative/main> <H2 noun>" inversions in 3+ sections; H08 only near-verbatim.
J30. Link-closer template: "Capsule's guide to X shows how…" ends almost every section; 12 internal links in ~1,230 words, one page linked twice. Fix: lint caps internal links (1 per ~150 words), blocks the same URL twice, and flags the same link-sentence shape (brand possessive + guide/walkthrough + shows/covers/explains) in 3+ sections.
J31. Decade-old statistic presented as current (secondary source repeated an undated study). Fix: RULES — a statistic carries its original source and year; older than 5 years only as history; pack marks stats from non-authority pages "secondary: find the original"; lint warns on % / money statistics with no year nearby when the source is not an authority.
J32. Brand claim cited to the wrong client page (homepage meta quoted, product page linked). Fix: site claims carry their source URL; the claim's link must be that URL.
J33. Client quotes its own tagline in the third person. Fix: RULES — on the client's own site, describe the product directly; never "X's site invites you to…".
J34. Coverage gaps vs SERP (features, pricing, AI, deployment, examples, how to choose). Fix: outline gate blocks on topics shared by 40%+ of top pages (was 60%); pack shows competitor median length as the floor.
J35. A competitor-brand PAA question ("Is Salesforce a CRM system?") got its own H2 on the client's page. Fix: query_map — questions naming a competitor brand (an organic-result brand that isn't the client) become a mention, not an H2.
J36. Language: redundancy ("walkthrough … walks through"), spelling variants mixed in one page (set-up/setup). Fix: lint flags hyphen/space variants of the same word in one page.

### how-to-check-tyre-tread-depth (R2) — blind judge 72/100, fix first (R1: 52)
intent 9, coverage 12, accuracy 8, info_gain 8, humanization 13, language 8, structure 7, brand 3, trust 4.
J37. Client count in the CTA (2,300) disagrees with the live site (2,200 / 2,000). → pack flags conflicting client counts; approved claims re-checked on the live homepage.
J38. Softened a safety consequence: the source says level-with-indicator = illegal/replace; article said "have it checked". → RULES: keep the strength the source gives a consequence (illegal, replace, stop using).
J39. Cannibalisation: the client already has two pages on the exact intent; the article linked them on the first screen. → same-topic decision: this page is written as the consolidated page; the report recommends merging/redirecting the old one; don't link the old one near the top.
J40. Internal contradiction ("lowest reading decides" vs "don't judge by the shallowest groove"). → WORKFLOW self-check: reread for statements that contradict each other.
J41. Local/peripheral authorities (a council press release, an ambulance trust) used as the main authorities when national ones exist. → official_facts ranks national authority domains before local/sub-organisation ones; local pages capped.
J42. Teaser/filler lines: "The coin has one limit worth knowing.", "The legal risk is real as well." (dog: "The chart has one clear limit.", "Here is a worked example."). → lint teaser pattern + "here is a/an … example" signpost.
J43. Arithmetic parentheticals ("(7 minus 3)", "(10 ÷ 1.5 × 85 g)") read robotic; false precision ("80.5 g" from a rough guide). → RULES: worked numbers in natural prose, round to the source's precision; lint accepts a derived number when two numbers in the same paragraph produce it (no operator word needed).
J44. Coverage gaps vs top pages (uneven wear, MOT/insurance, coin orientation). → outline gate at 40%.
J45. Anchor promises a different page than its title. → pack lists client URLs with their page titles.

### how-much-should-i-feed-my-dog (R2) — blind judge 68/100, fix first (R1: 57)
intent 8, coverage 11, accuracy 10, info_gain 6, humanization 13, language 7, structure 7, brand 2, trust 4.
J46. A rival brand's product chart is the page's backbone and its first link (competitor data on the client's page). → sources whose domain is a commercial result for the same query are labelled "competitor": context only, attributed as theirs and limited to their product, never the main answer or the first link; prefer independent sources.
J47. A product-specific rule (one maker's adjustment for its own food) stated as universal. → RULES 1.7: a rule from a product guide applies to that product; say so.
J48. Source with a commercial stake not disclosed (institute owned by the rival's parent). → folded into J46: say whose data it is.
J49. Table covers only part of the reader range (stops at 20 kg; no puppy amounts). → RULES: a table covers the range readers bring, or says where it stops.
J50. Client guides named but not linked (writer removed redirecting links) → fixed by resolving client URLs at prep (R2-20).
J51. Yes/no heading answered with an opening "No" when the answer is yes. → RULES: a yes/no question gets the true yes/no first.
J52. Near-duplicate H2s carrying query variants, I/you drift in headings. → outline gate blocks an H2 that repeats the H1's content words; headings use one person consistently.
J53. Brand line bolted on at the end with no link/next step.

### how-much-protein-do-i-need-a-day (R2) — validate PASS 0 block / 6 warn, 1,562 words
R2-29. Pack facts mostly off-topic (label thresholds, fibre, vitamin D; a dialysis leaflet as the protein source); a top-3 charity with all the figures absent. → relevance gate (R2-10) + charities as sources (R2-22).
R2-30. Pack shows redirecting source URLs as ok; validate fails them. → resolve fact source URLs to final URLs at research (R2-3).
R2-31. Bot-block page ("Pardon Our Interruption") scraped as a source; a hospital site classed as forum_ugc. → classify() treats bot-interstitial titles as blocked; domains kind fix.
R2-32. KG junk ("45 g: 45 g", "Related Topics" as a topic).
R2-33. PAA "how do I calculate…" vs separate_page on the same task → the main query's own task is never a separate page.
R2-34. Client voice "we/our 50%" vs RULES "we only on service pages". → RULES: follow the client's measured voice when its guides use "we".
R2-35. Approved claims are taglines only → product descriptions block C01. → client products' own page text counts as client facts (already for shops); pack says so.
R2-36. FPs: '80 kg' in a table row "80 × 0.75 = 60 g"; "two to three times" vs "2-3 times"; an official body's name flagged as copied text.
R2-37. add-fact accepts very short values ("Protein 50 g") without context. → values need ≥4 words or a claim whose words are on the page near the value.
R2-38. eval meta-commentary count disagrees with lint (also R2-17).

### how-much-protein-do-i-need-a-day (R2) — blind judge 69/100, fix first (R1: 54)
intent 9, coverage 11, accuracy 10, info_gain 6, humanization 12, language 6, structure 8, brand 3, trust 4.
J54. Stretched a source into a comparative claim ("timing matters as much as the total"). → RULES: comparisons ("as much as", "more than", "the main") need a source that makes the comparison.
J55. A source written for a specific group (kidney/dialysis patients) used as general advice. → RULES: a source written for a group (patients, a condition, professionals, one product's buyers) applies to that group; pack shows each source page's title so the audience is visible; official_facts flags audience-specific pages ("patients", "for people with …").
J56. Inline arithmetic everywhere (strongest AI tell across three judges). → RULES 1.3 rewritten (natural prose, no formulas); N01 now accepts derived numbers within the paragraph without operator words.
J57. Untraceable generalisation contradicted by its own maths ("100 g is enough for most people"); forced "yes" to a PAA question. → RULES: answer a PAA question truthfully even when the answer is "it depends"; check a general claim against the page's own numbers.
J58. Coverage: source table stopped (no 11–18 figures) and writer dodged; no grams per food. → RULES 1.17 (table range); research: when a fact table stops short of the reader range, add-fact the rest.
J59. Locale term: "family doctor" on an en-GB page (GP). → lexicon us_to_uk gets general locale terms.
J60. Internal inconsistency (20 g plateau vs 25 g servings); person drift third→second. → WORKFLOW self-check (added).
J61. Missing blank line before a heading (Markdown) and a definitional section last. → lint: heading must be preceded by a blank line; RULES: background sections go early, never last.

## Score summary (blind, round 2)
tyre 72 · CRM 64 · dog 68 · protein 69 — mean 68.3 (same four in R1: 54.75).

## Round 2 → round 3: general fixes applied (no niche rules)
- RULES: statistics carry original source + year (≤5 years unless history); keep a source's consequence strength; tables cover the reader range or say where they stop; sources written for one group apply to that group; comparisons need a comparing source; answer truthfully even when "it depends"; product-specific rules stay product-specific; prefer independent sources over competitors (competitor data attributed, never the backbone or first link); client product described directly (no third-person tagline quotes; claim linked to its source page); competitor-brand questions are not sections; natural word order (no inversions); worked numbers in prose, rounded to source precision, no bracket formulas; no teasers; yes/no answered truthfully first; one spelling per word; link each URL once, links on useful sentences (no link-only closers), ~1 internal link per 150 words; no H2 restating the H1; one person in headings; never end on a background section; client "we" when its measured voice does.
- WORKFLOW: self-check reread before lint (contradictions, duplicated numbers/rules, announcing sentences); the target query's own task is never skipped as a separate page.
- Client pages: offered URLs resolved to final URLs (dead ones dropped) and listed with their titles; template families (one page per town/model) never offered as guides; sibling list capped to the 15 closest; same-entity pages must share 2+ query words beyond the site's generic words; same-topic decision is now "write the consolidated page; operator merges/redirects the old one"; homepage title with a brand separator is not a claim; client claims carry their source URL; conflicting client counts flagged; client passages must be full declarative sentences and are labelled "authority wins"; reader nouns shown in the pack.
- Sources: official_facts requires searched authority pages to contain most of the query's content words; careers/jobs subdomains are spam hosts; national authorities rank before local ones; facts cite final URLs; audience-specific pages labelled; .org/.org.uk/.ngo → nonprofit ("independent organisations" group); forum detection by domain or forum path only; bot-interstitial pages ("Pardon our interruption" etc.) classed as blocked; competitor brands in the SERP grouped separately in the pack; duplicate fact values shown once.
- Query map: questions naming another brand in the results → mention only; format words (explain, calculate, chart, guide…) don't make a separate page; existing_page match rejects slugs carrying 3+ unrelated words.
- Outline gate: topic coverage block at 40% of top pages (was 60%); H2 restating the H1 blocked; I/you heading drift warned.
- Lint: H10 teaser (block), U07 URL linked twice, U09 internal-link density, U10 link-only closer template; N01 accepts numbers derived within the paragraph/table row and worked money sums; S04/S06/A01/C02/K06/K07/N04/E03/H08/G01/C03 false positives fixed; locale vocabulary (GP, A&E, fibre, litre, ageing, maths, flat, postcode…) added to the locale table.
- add-fact: values under 4 words must sit next to the claim's own words on the page.
- KG: wh-word/self-referencing triples, valueless dates, "45 g: 45 g" attributes and "Related topics"-style headings dropped.
- eval uses lint's meta-commentary detector.

## Round 2b writer reports (pipeline after the round-2 → round-3 fixes)

### how-to-clear-cache-on-iphone (R2) — validate PASS 0 block / 3 warn, 1,070 words
R2-39. The maker's support page (help_centre, positions 1–2) returns 404 to the script but loads in a browser; validate blocked the main source link; add-fact failed until text was passed with --source-text-file. → link check: a URL whose text the agent captured with its own browser is "captured", a warn not a block; WORKFLOW names --source-text-file as the step when a fetch fails.
R2-40. The product maker's help centre is not treated as authoritative ("No official page in reach", grouped as "other sources"). → help_centre results in the top 5 = the maker's own documentation: authority for that product's settings (pack group "authorities and the product's maker"), official_facts candidates.
R2-41. existing_page mappings: a model-number variant query → a repair collection for another model; an Android query → a post not in the link list. → existing_page targets must be in the pack's offered links and must not be commercial collections for informational questions.
R2-42. The only PAA restated the H1 → skipped. WORKFLOW "every PAA as H2" vs RULES "no H2 repeating the H1". → WORKFLOW: a PAA that restates the H1 is answered in the opening (Skip line).
R2-43. Outline FP: "How to clear the Safari cache on iPhone" blocked as repeating the H1 (it narrows it). → the H1-repeat block fires only when the extra words are time/quantity filler (per day, daily, exactly, really…).
R2-44. Lint FPs: T02 "unlinked portal" on a UI button label in a table; G01 on a sentence whose number and subject are in a fact ("Chrome's default covers only the last 15 minutes"). → T02 skips quoted/Title Case UI labels when the page is a how-to with UI steps; G01 grounded when a fact shares the sentence's number and a content word.
R2-45. Client voice "we" at 8%: RULES threshold unclear. → pack states the decision ("use the client's name" below 20%).
R2-46. Products listed are unrelated repairs. → product relevance filter applies whenever the products' words don't match the query, chosen collections included only when they match.

### how-does-pension-tax-relief-work (R2) — validate PASS 0 block / 1 warn, 1,576 words
R2-47. Copyright boilerplate and formula definitions listed as authority facts; duplicates (gov-uk:9/:10). → official_facts drops legal/copyright boilerplate ("third party copyright", "Open Government Licence", "© Crown") and dedupes values.
R2-48. Two authority facts disagree (threshold income £260,000 in an older helpsheet vs £200,000 on the current rates page). → pack flags conflicting figures for the same term across facts; prefer the page with the current tax year/date.
R2-49. The only worked example came from an older year's page; current-year bands missing. → YMYL: official_facts searches "<query> <current year>" rates pages; facts mention which year they describe.
R2-50. Voice block "Measured on 0 of its pages: average 14.5 words" with a disclaimer as its sample. → no voice line when 0 pages were measured; disclaimers filtered.
R2-51. "how does pension tax credit work" routed cover_in_section; it's a different product. → a distinct term that changes the entity (credit vs relief) counts as distinct even when the rest matches (already: distinct terms → separate unless SERP overlap ≥3; here overlap check said same page?).
R2-52. N01: "£3,600" verified in a fact's claim but blocked (money read from value only). → money/nums also taken from verified claims.
R2-53. N04: "three cases set out by GOV.UK:" followed by a three-item list blocked. → _enumerates looks at the following list items.
R2-54. add-fact persists facts into the brief's extra_facts, which carried old-year facts into a new run. → persisted facts carry retrieved_at; prep re-verifies them (already) and drops those older than the newest change on YMYL.
R2-55. Scratch files collided across parallel writer sessions (shared temp folder). → writer prompt: scratch files inside the run folder.

### how-often-should-a-boiler-be-serviced (R2) — validate PASS 0 block / 4 warn, 1,195 words
R2-56. Client passages off-topic (air-conditioning lines on a boiler query) and intro meta text ("In the following guide, we'll answer…"). → client passages need half the query's content words (min 2) and no meta-commentary.
R2-57. No authority facts on a safety topic because no government page ranked. → official_facts always runs one site search on the locale's own authority domains (the relevance gate keeps only pages about the query).
R2-58. Answer leads from US forums/Facebook quoting dollars; "Book your boiler service in Bristol today" as an expected topic; "reddit" treated as a brand; a "10 year" consensus figure from an unrelated statistic. → answer leads from forums/social or with foreign currency dropped; CTA/promo headings filtered; brand detection only for business/ecommerce results; consensus figures must share a sentence with a query content word.
R2-59. FPs: C01 banned claim "guarantee" on a third party's (manufacturer's) guarantee; C01 unapproved claim on "We recommend…"/"Our advice is…"; N01 on "11 months" (a judgement figure). → banned claims only in sentences about the client; recommendations are not service claims.
R2-60. info_gain listed a question "no top-10 page answers" that top pages do answer.

### how-to-clear-cache-on-iphone (R2) — blind judge 70/100 (R1: 63)
intent 9, coverage 12, accuracy 6, info_gain 7, humanization 14, language 7, structure 9, brand 3, trust 3.
J62. A method presented as doing what its source says it doesn't (offloading an app "frees app cache"); real per-app options missing. → RULES: a step does only what its source says it does; if no source method exists, say so.
J63. Client claims with dropped conditions ("lifetime warranty" is screen repairs only*) and a stale count (38 vs 30 shops). → RULES: a client claim keeps its conditions (asterisks, "on screen repairs"); counts only from the homepage/approved claim; pack conflict flag (added).
J64. The same fact repeated three times across sections. → lint: near-duplicate sentences across sections (content overlap ≥ 0.7) warned.
J65. Same closing caveat template in each procedure ("Check … before …") and one-word "No." / "Yes." openers. → lint: sections ending on the same two opening words in 3+ sections; RULES: yes/no inside the first sentence ("No, you can't…"), never a one-word sentence.
J66. The main source (maker's support page) not linked; no iOS version. → R2-39 (captured pages count) + RULES UI paths name the version.

### how-does-pension-tax-relief-work (R2) — blind judge 71/100 (R1: 57)
intent 9, coverage 11, accuracy 10, info_gain 6, humanization 14, language 6, structure 8, brand 3, trust 4.
J67. Unlinked, unfindable forum quote on a YMYL page. → RULES: a forum quote is used only with its link from the pack, and never on YMYL pages as support; lint blocks a quoted forum/commenter line without a link.
J68. Outdated statement (a 2024-25 statutory top-up for low earners missed) despite the recent-changes search. → YMYL: recent-changes search uses the query's subject + "changes"/"new" + years, results feed facts flagged "newer rule".
J69. Imprecise rule order (carry-forward order) and a dodged time limit. → writer verification; RULES 9 "say what the reader should check" kept.
J70. Template slots: "The cost of claiming is the time spent…" (from RULES 1.8 "say what it costs") and a boilerplate sources footer. → RULES 1.8 applies only when there is a real cost (money, a fee, lost benefit).
J71. Whole-clause link anchors. → lint: anchors over 8 words warned; RULES: anchors of 2–6 words naming the target.
J72. Client product never tied in (the client claims the relief for its customers). → RULES: say in one sentence how the client's own product handles the thing the page explains, from approved claims/client pages.

## Score summary (blind, round 2 so far)
tyre 72 · CRM 64 · dog 68 · protein 69 · iPhone 70 · pension 71 — mean 69.0 (same six in R1: 56.5).

### how-often-should-a-boiler-be-serviced (R2) — blind judge 73/100 (not judged in R1)
intent 10, coverage 11, accuracy 11, info_gain 6, humanization 14, language 7, structure 7, brand 4, trust 3.
J73. Linked the client's old page on the same query (which this page replaces) as a "source", calling it "earlier guide". → lint U13 blocks links to same-topic client pages; RULES.
J74. Cost missing although the client's own old page gives a price range. → the client's same-query page is harvested richly (12 passages, figures kept).
J75. "When" used for conditions where "if" belongs (writers dodging the K04 "If opener" warning). → K04 only for conditions over 12 words; RULES: state conditions with "if".
J76. Legal duty credited to the regulator's guidance instead of the regulation. → RULES 1.23.
J77. One manufacturer's warranty as the rule row. → RULES 1.7 (product-specific rules).
J78. Unlinked forum quote again (2 of 7 articles) → lint U12 now blocks.
J79. No author/byline → operator action in the report (author from the client profile when set).

## Round 3 additions (from R2b reports)
- `seo.py review <run>` (WORKFLOW step 6b): every claim beside its closest fact with match score and numbers not in that fact; client lines beside approved claims; each section's first and last sentence; topics/figures the top pages share that the page misses.
- Lint: E06 repeated point across sections, E07 closing template, E08 one-word yes/no, U11 long anchors, U12 unlinked forum quote, U13 link to the replaced page; banned claims only bind the client; recommendations aren't service claims; K04 relaxed.
- Research: answer leads looked up in the page's own locale, never forums/social/foreign; CTA headings filtered from topics; consensus figures must sit with a query word; brands only from business/shop results; client passages need half the query's words; one site search on the locale's authority domains always; validate accepts a 404 page the agent captured live.
- RULES 1.21–1.23 (steps do only what the source says; client claims keep conditions; legal duties credited to the law), yes/no inside the first sentence, forum quotes linked and never as YMYL support, client tie-in sentence, "if" for conditions, 2–6 word anchors, never link the replaced page, cost lines only for real costs.

## Score summary (blind, round 2 complete for 7 of 10)
tyre 72 · CRM 64 · dog 68 · protein 69 · iPhone 70 · pension 71 · boiler 73 — mean 69.6.
Note: HoV fixture failures are environmental (houseofvelorien.com rate-limits product pages with HTTP 429 after repeated tests).

### how-to-paint-a-fence (R2) — blind judge 76/100 (best so far)
intent 9, coverage 11, accuracy 14, info_gain 5, humanization 17, language 5, structure 8, brand 4, trust 3.
Brief error (operator, not pipeline): the brief and profile say en-US for a UK brand. Pipeline effects: UK vocabulary ("tin", "dust sheets") and metric-first units on an en-US page. → RULES 1.13 units/vocabulary; lint L03 locale units; lexicon gains UK↔US vocabulary.
J80. Coverage limited to the client's own pages (primer for new wood, repairs, safety gear, rain window, painting order). → outline gate 40% (done); review §4 lists gaps.
J81. Numbered list for alternatives; circular "because". → RULES (Koray section).
J82. Link at the end of nearly every section. → U09/U10 (done).
Writer-reported: town volunteer notice as an "authority" fact (→ local authority pages need the query in title/headings); verified client-page facts blocked by C01 (→ client's own published words count as approved wording); "we make" blocked for a manufacturer with no client_facts (→ client-page facts affirm a role); spelling variants missed by review (→ colours/colors normalised in matching); outline blocked "What you need to…" (→ "need" no longer filler); voice "0 pages, we 100%" (→ no voice line from 0 pages); truncated autocomplete ("… without") (→ dropped).

### how-to-make-a-sourdough-starter (R2) — blind judge 66/100 (rewrite)
intent 9, coverage 10, accuracy 12, info_gain 4, humanization 12, language 8, structure 7, brand 1, trust 3.
J83. The client's own method page and products never reached the pack: the client site answered 429 during research ("written as a new page") and at validate (all client links removed). → fetch waits Retry-After and retries 429 once; validate treats a 429 on a sitemap-listed client page as a warning.
J84. Page built on third-party recipes (one source named 11 times; competitor flour mill linked). → RULES competitor rule (done); H07 attribution density.
J85. Planning quantity copied from a source's ingredient list contradicts its own method. → RULES 1.21 + review claim map.
J86. Contradiction within the page (feed weekly vs 2 weeks unfed). → WORKFLOW self-check + review.
J87. No safety/troubleshooting section that all top pages have. → outline gate 40%.
Writer-reported: running totals in a table blocked (→ N01 reads the whole table plus its intro); one-word structural topic ("Method") forced as a heading (→ warn only); existing_page targets off-topic (→ slug may carry at most one unrelated word); prices and past-dated courses in product names (→ stripped/dropped); "near me" kept (→ dropped unless service page); review flagged sentences combining two facts (→ numbers checked against the two closest facts and any fact).

### when-to-plant-tulip-bulbs (R2) — validate PASS 0 block / 7 warn, 1,241 words
Writer-reported: research found no timing facts (0 official pages; writer added 36 RHS/NGS facts); approved claim was a superlative homepage title (→ superlative taglines dropped); existing_page link 404 at validate (→ pack checks existing_page targets live); "Is it too late to plant … now" blocked as a separate page (→ seasons/months/late/early are modifiers, not new topics); US state/zone variants on an en-GB page (→ US states and hardiness zones are US marks); KG junk "30 cent: 30 per cent" and a video heading as a topic (→ filtered); voice sample printed twice (→ deduped); C03 on PAA wording (→ the reader's own question wording is exempt); "we'd aim for…" blocked as a claim (→ "we'd" recognised as advice).

### when-to-plant-tulip-bulbs (R2) — blind judge 78/100 (best so far)
intent 9, coverage 11, accuracy 14, info_gain 7, humanization 15, language 7, structure 8, brand 3, trust 4.
J88. Both recommended products were out of stock in peak season. → product records carry stock (Shopify variant availability); sold-out products dropped when 3+ others are in stock, otherwise flagged "don't recommend or link".
J89. Opening led with the widest source window (September) though the consensus says later. → RULES: the first sentence gives the answer to act on; range and exceptions after.
J90. A PAA heading the research couldn't answer ("what not to plant next to tulips" never names a plant). → RULES 1.20 + Skip lines.
J91. One fact repeated in three consecutive sections; three identical five-step lists. → E06/E07 (added this round).
J92. Coverage gaps (feeding, pH, flowering groups, lasagne planting, pests). → outline gate 40%, review §4.

## Score summary (blind, round 2 complete: 10 niches)
tyre 72 · CRM 64 · dog 68 · protein 69 · iPhone 70 · pension 71 · boiler 73 · sourdough 66 · fence 76 · tulip 78 — mean 70.7.
Round 1 (6 judged): mean 56.5. Later-written articles (fence, tulip: written after the round-3 fixes) score highest.
Round 3 reruns started: CRM, sourdough, dog (lowest three).

## Round 3 writer reports

### what-is-a-crm-system (R3) — validate PASS 0 block / 2 warn, 1,199 words (median of top pages 1,984)
R3-1. A fact source persisted in the brief from an earlier run had moved (redirect); the pack showed it "ok", validate blocked it. → prep cites every source at its final URL when the page has moved within the same site.
R3-2. A vendor that sells the same product but doesn't rank in the top 10 is not labelled a competitor (only SERP businesses are). Open: needs a product-category signal.
R3-3. A page title alone as an authority fact; an advert as a PAA answer lead. Open (minor).
R3-4. review.md flagged the approved client claim and imperative advice lines as CHECK; G01 warned on imperative advice. → approved claims count as sources in review; imperative advice without numbers is the author's judgement (review and G01).
R3-5. Copied-text (C03) and grounding (G01) pull in opposite directions on one short authority sentence: only a verbatim quote satisfies both. → by design: quote it or paraphrase with the fact's key words; noted.

### Round 3 blind judges (rerun on the round-3 pipeline)
- what-is-a-crm-system: 65 (R2 64). humanization 8/20: imperative + "because" closers in every H3, fragment bullets ("Admin shrinks."), source relaying ("X says / Y describes"); first link to a competitor (Microsoft, not labelled a competitor because it doesn't rank top 10); tracking parameter left in a URL; example question answered with a hypothetical instead of named products; pricing/AI/deployment gaps.
- how-to-make-a-sourdough-starter: 68 (R2 66). Still a compilation of third-party recipes (one source named 9 times); the client's own starter page linked as a "first bake" (wrong) and contradicting; plain-flour answer reasoned from absence; no spoilage/mould guidance; sold-out dated course linked; meta repeats the title.
- how-much-should-i-feed-my-dog: 60 (R2 68). Competitor (Pedigree) chart again the backbone: the pack had no independent numeric source and no client portion data; "small breeds need more calories" dropped "per kg"; a contested seasonal claim stated as fact; title promises age portions it doesn't give.
Reading: run-to-run variance is about ±5–8 points; the round-3 rule/lint changes did not lift these three. The binding constraint is research content (independent numeric sources, the client's own expertise, full topic coverage), not wording.

### Round 3 → round 4 fixes
- Research: one site search on the client's domain for the query (client pages explaining their own method reach the pack); same-topic detection ignores task verbs ("make", "check"…), so the client's existing guide is found and mined (12 passages, figures kept).
- WORKFLOW step 2: main-answer numbers only from a competitor → find an independent source first, else teach the method with the competitor as an attributed example; read the client's own pages for this query before writing and never contradict them.
- Length: guides aim at 80–115% of the top pages' median (within 1.5–2× of the brief range); lint uses that range.
- Lint: U14 first outbound link to a business (warn), U15 tracking parameters, H07 attribution density warn >10% / block >20%, E09 fragment bullets, E07 "do X, because Y" closers, C01 "our guide" is navigation, rounded "about" figures accepted, client homepage always linkable; add-fact strips tracking parameters; pack resolves redirecting existing-page targets; official_facts drops viewer/proxy/mirror re-hosted pages; review counts approved claims and skips imperative advice; report counts paraphrased facts, shows outline skips and the real mode.

## Round 4

### how-to-make-a-sourdough-starter (R4) — blind judge 72/100 (R3 68, R2 66)
intent 9, coverage 11, accuracy 12, info_gain 5, humanization 13, language 7, structure 8, brand 3, trust 4.
The client's own method now reaches the page (client site search), trust up. Remaining:
J93. The client's own method sits second, after a third-party method; competitor flour brand linked. → RULES: when the client publishes its own method, lead with it in the client's voice; sources only where they add weight.
J94. The client's other starter pages linked as "a second method" (cannibalisation): pages found by searching the client's site skipped the same-topic test (the sitemap was rate-limited). → site-search results go through the same-topic classifier.
J95. Two sources disagree (5 days vs 2 weeks) and the page leaves the reader to choose. → RULES: say which you recommend and why.
J96. Research leaks into copy ("Most of the top recipes…"). → lint H05 blocks talk about top results/ranking pages; RULES.
J97. "X rather than Y" three times. → lint warns past two; RULES counts it with negative parallelism.
J98. Still missing: mould/spoilage (safety), temperature range, day-by-day table. → outline gate/review gaps (writer coverage).
Writer-reported fixed: tracking codes (srsltid) in client URLs from search; C01 on a captured client fact (facts from the client's own site count as its wording); E06 on the intro summary repeated by sections (intro exempt); review gap missing "seven days" (number words normalised).

### Round 4 writer reports (dog, CRM) and fixes
- Spam page on a council subdomain (`/viewer/` re-hosting a pet-food brand's chart, with an author bio as a "fact") still listed as an authority because it ranked (not searched). → re-hosting paths dropped for every candidate; local authority pages must name the query in title/headings whether ranked or searched.
- Client pages found by site search were offered at redirecting /en-gb/ addresses. → site search now runs before the redirect/dead-link resolution, so its pages are resolved too.
- Same source listed twice in the pack's links; approved-claims wording ignored the client-page facts. → links deduped; pack says client-page facts count with approved claims.
- N01 false positives: "800 g drops by 10% to 720 g" and "100 g = 22–23 g, so 700 g ≈ 154 g". → derived numbers accept percentage changes and per-100/per-1000 conversions within the paragraph.
- S03 on "Neutering lowers…" (gerund subject). → -ing word directly followed by a verb is a subject.
- review read "1,200" as 200 → thousands separators normalised.
- Outline: "What does a dog food chart by weight say?" didn't cover "How much food should I feed my dog chart?" → much/many/should/need/say carry no topic.
- CRM: the client's own "What is a CRM?" page (slug without "system") not recognised as the same query. → same-topic also when every slug word is in the query and it lacks at most one.
- C03 blocked a long quotation that was in quotation marks and named its source. → quotations up to 400 characters are quotations.
- H08 on H3s that name their type ("Collaborative CRM" → "In collaborative CRM, …"). → headings of 3+ content words only.
- N04 on a hypothetical ("If two colleagues have ever called…"). → conditional sentences skipped.
- PAA answer leads that are adverts ("Start learning with free online training"). → filtered.
- Pack header showed the brief's length while lint used the median-based range. → header shows the range lint enforces.
- Open: competitor detection for vendors that don't rank top 10 (Microsoft for a CRM query); timing table shows a negative outline+draft time.

### how-much-should-i-feed-my-dog (R4) — blind judge 71/100 (R3 60, R2 68)
intent 8, coverage 11, accuracy 12, info_gain 6, humanization 14, language 7, structure 7, brand 2, trust 4.
The client's own calculator and portion guide now reach the page (client site search). Remaining:
J99. A rival brand's chart and calculator are still the centrepiece (named 10 times). → lint U16 warns when a business competing in the SERP is named more than 3 times.
J100. srsltid tracking codes in client links (run predates the cleanup) → U15 now knows srsltid.
J101. Like-for-unlike example (puppy vs adult food), a link promising content the page doesn't have, coverage stops at 20 kg. → RULES 1.17/1.21 (writer).

### what-is-a-crm-system (R4) — blind judge 67/100 (R3 65, R2 64)
intent 9, coverage 11, accuracy 11, info_gain 6, humanization 11, language 5, structure 7, brand 3, trust 4.
J102. A client-attributed paraphrase that can't be traced to the client page (passage drift) — accuracy risk. → review claim map + editor pass.
J103. Approved homepage-meta count ("10,000") not in the visible site text ("thousands"). Open: approved claims from meta descriptions should be confirmed in visible text.
J104. Coverage gaps persist across rounds (cost, AI, cloud, features, named examples): the SERP for this query is full of scraped clones, so the competitor topic list is weak. Open: detect clone/mirror pages (near-duplicate text across domains) and backfill from the next real pages.
J105. Facts stitched in for coverage; link-wrapper sentences; even rhythm.

## Round summary (blind)
| topic | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| sourdough | – | 66 | 68 | 72 |
| dog | 57 | 68 | 60 | 71 |
| CRM | 56 | 64 | 65 | 67 |
Other R2: tulip 78, fence 76, boiler 73, tyre 72, pension 71, iPhone 70, protein 69.

## Round 4 → 5
- WORKFLOW 7b editor's pass: after the first PASS the writer scores its own page against the rubric as a hostile editor (quoted deductions, generic sentences, link-only sentences, repeated endings, claims beyond their source, missing shared topics, missing recommendations), writes editor.md, fixes, re-validates. The independent judge stays separate and blind.
- Lint U16 competitor prominence; U15 knows srsltid.

## Round 5 writer reports (CRM, dog) and fixes
- BUG: forum detection matched substrings, so "butternutbox.com" (contains "x.com") was classed forum_ugc. → domains match exactly or as subdomains; prefixes and stems only where meant.
- Page titles/headings accepted as authority facts ("Tool: Customer Relationship Management Systems…"). → a paragraph fact needs a verb and isn't a question.
- Facts verified on the client's site filed under "other sources"; the replaced page listed under "Sources". → grouped with the client's pages; replaced page removed from sources.
- Facts persisted from earlier runs kept tracking parameters and duplicates. → cleaned and deduped at prep.
- validate's link line counted cosmetic redirects as failures ("6/13 return 200"). → reports links that are fine vs unconfirmed-but-accepted.
- H08 fired on the required "No, …" yes/no answer. → yes/no openers exempt.
- N01 on "Two cups of each give 812 kcal" (2 × 406). → number words take part in worked sums.
- S03 called "Feed for their target weight" a past participle. → a bare verb first (spaCy VB) is an instruction.
- review matched sentences to the wrong facts (short facts favoured); "10,000" vs "10000". → match score normalised by both sizes; thousands separators normalised; imperative advice detected by spaCy.
- Rhythm: lint target 85% of the human median vs the rubric's 80%. → both use 80%.
- WORKFLOW listed only RULES and the pack as inputs although steps 6b/7b read review.md and the rubric. → stated.
- Open: no independent portion figures exist for the dog query in the pack (the writer taught the method instead, as WORKFLOW now says).

### how-much-should-i-feed-my-dog (R5, with editor's pass) — blind judge 78/100 (R4 71, R3 60, R2 68)
intent 8, coverage 11, accuracy 13, info_gain 7, humanization 16, language 8, structure 8, brand 3, trust 4.
Remaining: the only portion table is still a competitor's (the client publishes no gram/kcal-by-weight figures; the pack has no independent ones) → needs client data or an independent calorie method (RER) sourced from a vet body; title promises "by age" portions not given (→ RULES: the title promises only what the page delivers); cups heading on en-GB; uniform answer-then-expand template in all H2s; transition schedule unsourced; no author/date.

### what-is-a-crm-system (R5, with editor's pass) — blind judge 69/100 (R4 67, R3 65, R2 64)
intent 9, coverage 11, accuracy 11, info_gain 6, humanization 12, language 7, structure 8, brand 2, trust 3.
Remaining: two rival vendors linked (Salesforce, Microsoft — Microsoft not labelled a competitor because it doesn't rank top 10); a client-attributed phrase not on the client's pages; a third-party migration tool the client doesn't recommend; ERP question not answered in its first sentence; every H2 closes with an imperative tip; title promises "examples" (no named products); AI/cost/deployment gaps (SERP clones).
Fixes: a business source whose fact is about the client's product category (query words ∩ the client's own claims) is labelled a competitor whether it ranks or not; a business as the page's first outbound link now blocks (U14); RULES: title/meta promise only what the page delivers; supporting detail adds, never restates the answer as a list.

## Score summary (blind)
| topic | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| dog | 57 | 68 | 60 | 71 | 78 |
| sourdough | – | 66 | 68 | 72 | (running) |
| CRM | 56 | 64 | 65 | 67 | 69 |
R2 others: tulip 78, fence 76, boiler 73, tyre 72, pension 71, iPhone 70, protein 69.

### Sourdough R5 writer report → fixes
- U16 counted the ordinary word "sourdough" as the rival site sourdough.co.uk. → rivals named after a query word are not counted by that word.
- E06 flagged two different feeding steps (different quantities). → sentences with different numbers are different points.
- N01 blocked a computed figure whose inputs sat in neighbouring list items. → list items are read with their whole list and its intro.
- Outline blocked "What you need to make a sourdough starter" as repeating the H1 ("need" had been added to the outline's stop words). → reverted.
- add-fact calls were timed as "research" (1,166 s over budget) and made the draft time negative. → logged as "verify" (counted, not timed into research); draft time never negative.
- Open: the client site rate-limits scripts (429), so client links are accepted as "rate-limited" without a real check, and the client page was misread as new (it was a 404). Client pages that only an agent can read are captured with --source-text-file.

### how-to-make-a-sourdough-starter (R5, with editor's pass) — blind judge 77/100 (R4 72, R3 68, R2 66)
intent 9, coverage 11, accuracy 11, info_gain 7, humanization 15, language 8, structure 9, brand 3, trust 4.
Remaining: five timing benchmarks with a wrong reconciliation (warmer ≠ slower); no mould/food-safety section; details added to a source's method that the source doesn't contain (sensory notes inserted into the client's steps; "away from windows" credited to a brand that only says "draughts"); a competitor flour brand linked and no link to the client's named flour; plain-flour answer misleading; client's own guides contradict each other (5 days vs 2 weeks).

## Score summary (blind) after round 5
| topic | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| dog | 57 | 68 | 60 | 71 | 78 |
| sourdough | – | 66 | 68 | 72 | 77 |
| CRM | 56 | 64 | 65 | 67 | 69 |
R2 others (pre-editor-pass pipeline): tulip 78, fence 76, boiler 73, tyre 72, pension 71, iPhone 70, protein 69.
Editor's pass (WORKFLOW 7b) added +2 to +7 on all three.
Ceiling factors no rule can remove: no named author/reviewer or first-hand client experience in the client data (trust/brand), and SERPs where the only numeric data is a competitor's.
Next: round 6 on three other niches (protein, tyre, pension) to check the gains generalise.

## Round 6 (generalisation check: protein, tyre, pension)
First attempt (Opus subagents) stopped on the account session limit; partial runs moved to runs/_stale_prefix (*-r6-ratelimited).
From here on all test writers and blind judges run on Haiku 5.5 (operator decision: cheaper, and closer to the model the automation will run on in production). Note for comparisons: R1–R5 scores came from Opus writers and Opus judges, so R6 onward also measures how the pipeline holds up with a smaller model.

### Round 6 results (Haiku writers, Haiku blind judges)
| topic | score | accuracy | the single slip that zeroed accuracy |
|---|---|---|---|
| pension | 63 | 0/15 | "you must confirm within 30 days" — a 30-day rule from another context (auto-enrolment) |
| tyre | 62 | 0/15 | "1.6 mm or less is illegal" — the law says "at least 1.6 mm" (boundary flipped) |
| protein | 56 | 0/15 | a shake comparison judged unsupported (an earlier Opus judge verified the same BHF line: judge variance) |
Without the single −15 each would score about 71–78: humanization 11–17/20 holds up on Haiku.
Haiku writers follow the pipeline (all PASS, editor pass done) but carry claims across contexts more often. Haiku judges also disagree with Opus judges on borderline facts.
Fixes from R6:
- Lint A02 boundary: a fact that sets a floor ("at least N", "minimum N") or ceiling ("no more than N", "up to N") blocks the page wording "N or less/below" (floor) or "N or more/above" (ceiling).
- Client claims: a figure in a homepage meta claim must appear in the visible homepage text, else the claim is dropped (stale meta: "over 2,300 garages" vs visible 2,200).
- Length: when the ranking pages are shorter than the brief's floor, the floor comes down (max(60% of brief min, 1.3× median)).
- N01 skips numbers in question headings (the reader's question); P01 skips hyphenated compounds ("passenger-carrying"); L03 doesn't flag miles on en-GB; derived figures accept one-decimal and whole-number rounding; tax-year ranges ("2026-27") are dates.
- Client passages drop unfilled template placeholders ("_annual_allowance"); a client claim in another market's currency is flagged; review prefers facts carrying the sentence's numbers and skips the sources line.
- Tried and removed: a "number context" check (a number must sit in a fact sharing the sentence's subject words). On the three R6 drafts it flagged correct worked examples and figures and still missed the real 30-day error, so it was taken out. Context errors stay with review.md and the editor's pass.

## Round 7 (Haiku writers + claim ledger in the editor's pass)
### how-to-check-tyre-tread-depth (R7) — Haiku judge 69/100 (R6 62)
intent 7, coverage 10, accuracy 12, info_gain 5, humanization 12, language 8, structure 8, brand 4, trust 3.
No accuracy fail this time (the claim ledger caught it). Remaining: the coin test stated generally though it is calibrated to the car limit (meta promised motorcycles); one-paragraph method for a procedural query; unsourced frequency recommendation; no client next step (the only client claim had been dropped for a stale figure).
Fixes: a client claim keeps its offer and loses only the figure not on the visible homepage; RULES: "how to" queries give the method as numbered steps (prepare, act, read the result) and the title/meta only name cases the method covers.
Writer-reported (R7 tyre, pension) fixed: A01 on "not always"; N01 on percentages derived from two figures; Title Case flag on place names (England, Wales, Northern Ireland) in lint and outline; N04 on "the same two routes"; the 40–50-word snippet rule applies to question headings only (task headings warn past 90 words).

### how-does-pension-tax-relief-work (R7) — Haiku judge 51/100 (R6 63)
Root cause of the repeated "within 30 days" error (two different writers): GOV.UK says the provider "will let you know if this is the case and ask you to confirm your details… You must do this within 30 days" — the rule applies only in the case the sentence before names (HMRC records don't match). The pipeline stored it without that condition twice: official_facts kept the sentence but not its back-reference, and an R2 writer's --add-fact value began mid-sentence ("ask you to confirm…"), which was persisted in the brief and inherited by every later run.
Fixes (general): official_facts carries the previous sentence for mid-sentence back-references ("if this is the case", "if so", "in that case") and keeps the chain for follow-on rules; --add-fact rejects values that start mid-sentence or point back to a case they don't include; saved facts that start mid-sentence are skipped when re-loaded; the stripped fact was removed from the pension brief.
Other judge findings: a citation attached to a client page that doesn't say it; "the remaining £2,000" without a referent; salary-sacrifice 2029 section judged off-topic; coverage gaps (four-year claim window, net-cost examples, tapered allowance, MPAA).
- Guard calibration: a first version rejected any saved/added value starting mid-sentence; a scan of all briefs showed most saved values are short verbatim quotes that start mid-sentence and are correct (their claim carries the subject). The guard now rejects only values that point back to an unstated case ("do this", "if this is the case", "if so", "in that case"); across all briefs it matches only the stripped 30-day fact (already removed).

### how-much-protein-do-i-need-a-day (R7) — writer report → fixes
- Saved facts whose source is a PDF were re-verified as HTML and marked "not found in its text" though the PDF contains them. → prep reads PDF sources as PDFs during re-verification.
- review.md flagged worked arithmetic ("37.5", "80") as numbers missing from facts. → numbers the paragraph derives from sourced numbers are accepted.
- N01 on "roughly 13 g" with its 6.4 g input in the previous paragraph. → a paragraph's numbers are read with the paragraph before it.
- Noted: the 0.75 g/kg UK reference (COMA 1991) is old guidance; RULES 1.15 asks the writer to give its year.

### how-much-protein-do-i-need-a-day (R7) — Haiku judge 53/100 (R6 56)
accuracy 0/15, but the deductions are mostly verification failures, not errors: the activity table and "15–20 g within an hour" are BHF figures (an Opus judge verified them in R2), and several figures come from government/BNF PDFs the judge could not read. The article made checking hard: the activity table had no source link next to it.
Fixes: lint T03 warns on a numeric table with no source linked in the table, its intro sentence or the sentence after; RULES: link a table's source in its intro sentence; JUDGE_PROMPT: before marking a claim wrong/invented, open the source the article links or names for it; "could not read the source" is unverifiable, never invented; the −15 fail is for a claim checked against its source and found absent or contradicted.
Real defects also found: "uptake levels off at 20 g" generalised from a single study; the 50 g label point attributed via a link that doesn't say it; repeated "Yes/No" openers; no client next step (no client claims in the pack).
Judge reliability note: Haiku judges differ from Opus judges mainly on accuracy — they score unreadable sources as untraceable. Scores from R6 on are not directly comparable to R1–R5.

### Pension R8 writer report → fixes
- A client claim in another market's currency ("over $7 billion" on an en-GB page) was listed as approved and then contradicted by a note. → dropped at prep.
- RULES conflict "link each URL once" vs "link the source on the claim". → link a source on its first use; later claims name it without linking.
- WORKFLOW 6b vs RULES 1.3: a review CHECK on a number worked out from facts only needs the arithmetic confirmed and its inputs present.
- Open: client-page facts that contradict the authority (client page "25% and 31%" vs GOV.UK "20% and 25%"; "four tax years" vs HS345 "three") are not flagged in the pack; the writer followed the authority as RULES says.
- Fixed the open item: a client-page fact whose figures differ from an authority fact on the same subject (3+ shared words, same unit, no shared number) is flagged in the pack "⚠ differs from authority <id>: use the authority's figure". On the pension pack it flags the client's "25% and 31%" and "25% top up" lines against GOV.UK.

### how-does-pension-tax-relief-work (R8, after the back-reference fix) — Haiku judge 73/100 (R7 51, R6 63)
intent 7, coverage 11, accuracy 11, info_gain 6, humanization 14, language 8, structure 9, brand 4, trust 3. No accuracy fail: the 30-day context error is gone.
Remaining: a full section on a change that starts in 2029 (off-topic for how relief works now); sections closing on an instruction in 4+ sections; net vs gross limits in adjacent sentences without saying which is which; "HMRC's example" attributed without a link; no effective-rate headline (£60/£55 per £100).
Fixes: WORKFLOW — a change already in force goes into the answer, a future one gets a sentence where it matters, never its own section; lint E07 warns when most sections close on an instruction.

## Score summary — Haiku series (Haiku writers, Haiku judges)
| topic | R6 | R7 | R8 |
|---|---|---|---|
| tyre | 62 | 69 | – |
| pension | 63 | 51 | 73 |
| protein | 56 | 53 | – |

## Generalisation pass (operator request: every rule general, no babysitting)
- RULES and WORKFLOW examples drawn from the test niches (dog portions, tyre coin test, sourdough timings, screen-repair warranty, fence painting, a luggage brief path) were rewritten as neutral placeholders; the rules themselves were already niche-free.
- Code: no topic-specific logic. Two leftovers generalised: the product-ranking lines in the pack ("bag", "wheeled") now say "product"/"that feature"; the US-units detector lost its "pound dog" special case. Remaining niche words in code are comments explaining why a general check exists.
- docs/RESEARCH_PRINCIPLES.md: the research layer's rules written as one set of general principles (source tiers, relevance, context, freshness/locale, coverage, conflicts).
- Tried and reverted: flagging any two authority facts with different figures (41 warnings on the pension pack, all legitimate different rules). The client-vs-authority flag stays.
- Operator data fix: the fence brief and Ronseal profile were en-US by mistake; set to en-GB.
- Final round: iPhone, boiler, fence, tulip (not tuned against since R2) with Haiku writers and Haiku judges.

### Final round — iPhone writer report → fixes
- The pack header showed the brief's 1000–1600 words while the median-based range (top pages' median 426) is set later; the length target is now settled before the header is written.
- A maker's help-centre pages (Apple, Google) were labelled competitors of a repair business by the category rule; help centres are excluded from it (they document their own product).
- validate's note on an accepted 404 claimed this run's agent read the page; it now says a saved capture exists.
- Noted, not changed: the client's own guide gives an older settings path than the maker's current one; RULES already say the maker sets its own settings' names and UI paths name their version.

### Final round — how-to-clear-cache-on-iphone — Haiku judge 71/100 (R2 70)
intent 7, coverage 9, accuracy 10, info_gain 4, humanization 17, language 8, structure 9, brand 4, trust 3.
Remaining: client store count differs across the client's own pages (30 homepage / 38 About) and the article linked the page with the other figure; "iOS clears caches itself" unsourced; a heading promises app-cache clearing the section doesn't deliver; in-app cache controls, Firefox and the restart fallback missing.

### Final round — fence writer report → fixes
- E07 flagged sections ending on an instruction on a how-to page, where the next action is the genre. → E07's instruction-closer check skips how-to queries.
- review showed a match score above 100% (number bonus). → capped at 100%.
- Noted: facts saved by earlier writers carry claim wording with conditions the verbatim value lacks ("with the fence completely dry"); the review shows claim and value together so the writer checks the value, which is what lint verifies.

### Final round — boiler and tulip writer reports
- N04 flagged "five to seven bulbs" although a fact says "Five to seven". → a count whose number word (or digit) appears in a fact is accepted.
- Noted, not changed: the outline gate's PAA coverage is word-based, so a reader-words heading with different vocabulary ("How long does a boiler last?" for "average lifespan") needs the PAA's words or a Skip line; related PAA variants can be skipped as "same question as <heading>".
- Pack length header now matches lint (fixed earlier in this round, after these runs started).

### Final round results (Haiku writers, Haiku judges; niches not tuned against since R2)
| topic | R2 (Opus) | final (Haiku) | accuracy | the deciding defect |
|---|---|---|---|---|
| iPhone cache | 70 | 71 | 10/15 | client store count differs across the client's own pages; one unsourced claim |
| tulip bulbs | 78 | 68 | 7/15 | a window attributed to the wrong RHS page (the figure was on its sister page); "around February" unsourced |
| fence painting | 76 | 55 | 0/15 | "15 colours" linked to a page that doesn't state it (the figure is real, on another Ronseal page) |
| boiler servicing | 73 | 53 | 0/15 | "you don't have to give records to tenants": the source's qualifier (maintenance records, not the safety record) was dropped |
Every Haiku accuracy failure in the final round is the same class: a real figure or rule attached to the wrong page, or stated without the qualifier its source gives. Lint U17 (link must be the figure's source page), added after the fence judgement, would have flagged the fence and tulip cases; dropped qualifiers remain a writer-model limit that the claim ledger reduces but does not remove.
Fence/U17 fixes: lint U17 warns when a sentence states a figure and links a page other than the one the figure came from; "Pass/Fail/Result/Outcome" are framework labels; RULES: outcomes of a check in plain sentences.

## Overall summary
- Opus series (R1→R5, writers and judges on Opus): mean 56.5 (R1) → 70.7 (R2, 10 niches); three iterated topics reached 69–78 by R5; best single articles 78 (dog R5, tulip R2).
- Haiku series (R6→final): 51–73; humanization holds (11–17/20); accuracy is the swing factor — one mis-attributed or de-qualified claim fails the criterion under the rubric (−15).
- No article reached the 95 pass bar. The remaining gap is (1) single accuracy slips by the writer model, (2) missing client E-E-A-T inputs (named author, first-hand experience), (3) research that sometimes lacks independent data for the main answer, and (4) judge variance on what can be verified.

## Research stage rebuilt as its own role (operator request)
Grounding: professional fact-checking (SIFT: Stop, Investigate the source, Find better coverage, Trace claims to the original; lateral reading — Caulfield; Wineburg & McGrew 2019), multi-perspective question asking (STORM, Stanford), deep-research agent loops (plan → search → read → extract → verify → gap loop), Google's E-E-A-T guidance (experience = real first-hand use; cannot be generated).
- plugins/research_plan (script): research_plan.md from the run's own data: questions (search demand), five reader perspectives, shared topics, figures to trace upstream, facts to scope-check, client pages to read, where to look first.
- plugins/deep_research (agent, SKILL = the researcher's system prompt): plan; expert search (operators, locale, refutation searches, saturation); source tiers A–D + client; lateral reading and upstream tracing; whole-passage extraction with scope/date; two-source rule for main-answer numbers; conflict resolution; competitor-only numbers → method; client-claim checks; gap loops; access etiquette (no CAPTCHA/stealth; alternative routes, capture files); dossier format (main answer, per-question answers with evidence ids and scope, conflicts, do-not-say, gaps).
- plugins/expert_review (agent): an independent senior practitioner writes expert_notes.md (professional answer, recommendations per decision, mistakes, warnings, case dependencies, research gaps, experience the client can genuinely claim, suggested reviewer role). Honesty rules: no invented first-hand experience, case studies, statistics or credentials; judgement labelled as the brand's view.
- Claude Code agents: .claude/agents/seo-researcher.md, seo-expert.md; AGENTS.md documents the three roles for Codex/Cursor/Antigravity.
- `--add-fact ... --scope "<who/when>"`: scope stored, persisted, shown in the pack and review; RULES 1.24: a fact's scope travels with it.
- WORKFLOW: step 2 = research (own role), 2b = expert review (own role); the writer drafts from the dossier's main answer, follows its conflicts and do-not-say list, and uses the expert notes as the brand's view.
- Client profiles gain `author:` and `experience:` (the only E-E-A-T inputs the pipeline can't produce).
Test: boiler, fence, protein (the three weakest Haiku articles: 53, 55, 53) with Haiku researcher → Haiku expert → Haiku writer → Haiku blind judge.

## Spider integration (operator request: replace Serper with Spider for SERP and content)
Tests on "how often should a boiler be serviced" (en-GB):
- Spider /search returns organic results only (title, url, description): no People Also Ask, related searches or answer box; results are not localised to the UK even with country=gb, location or London coordinates (US boiler sites in a UK query).
- Spider /scrape on a Google results URL returned only a redirect (no results page); not pursued further (no anti-bot or stealth options are used).
- Spider /scrape (and /search with fetch_page_content) returns clean rendered markdown for pages the direct fetcher missed (UK authority and retailer pages), ~$0.0001 per page; Spider's default crawls whole sites, so every call sets limit 1 (one unbounded call crawled 1,011 pages for ~$0.23).
Implementation (scripts/seolib/spider.py):
- competitor_scrape reads every organic result through Spider first (rendered, cached 3 days), the direct fetcher only as fallback: fence run read all 6 readable articles (DIY.com, Cuprinol, Little Greene, Saga, Wickes, Travis Perkins); skips were videos and social posts only.
- official_facts retries authority pages that block scripts or need JavaScript through Spider.
- serp_intel lists organic results from the configured provider: SERP_PROVIDER=spider uses Spider; the default keeps Serper for the ranking list while a Serper key exists, because Spider's list isn't localised.
- query_map: when there is no People Also Ask for the locale, question headings shared by 2+ ranking pages become the H2 questions (search demand seen from the pages that rank).
- Key stored as SPIDER_API_KEY in the git-ignored .env. Research and expert agents use the host's own search tools, never Spider.
- Speed: every pipeline command spent ~8–10 s importing PyTorch, which spaCy's backend (thinc) pulls in when it is installed; the small English model doesn't use it. spaCy is now imported without torch (nlp.import_spacy, used by nlp, lint, evaluate, semantic_graph): the pack rebuild that follows each --add-fact went from ~11 s to ~4.7 s.

### Research-stage test chains (Haiku researcher → Haiku expert → Haiku writer → Haiku judge)
- protein: researcher added 2 facts (pack already held 103), resolved two conflicts (1991 RNI vs 2025 consensus; post-workout window), one gap; expert (UK dietitian role) 10 items and 9 research gaps.
- boiler: researcher added 5 facts incl. regulation 36 (the landlord duty the previous article got wrong); expert (heating engineer role) 9 items, 3 case notes, 7 gaps.
- fence: researcher added 7 scoped facts (temperature, humidity, wood moisture, dark-colour heat); several sites blocked (403) and were not bypassed; expert (painter and decorator role) 11 items, 8 gaps.
- Protein writer (research-stage chain): validate PASS, 1,338 words. Found: consensus figures labelled "2 sites" when both quotes came from one organisation's subdomains → sites are now counted by organisation (org_domain: shop.bhf.org.uk = www.bhf.org.uk = bhf.org.uk). Saved PDF-table facts that fail re-verification drop silently from the pack (they are listed under decisions as omitted); open.

### Research-stage chain results (Haiku researcher → expert → writer → Haiku blind judge)
| topic | before (Haiku, final round) | with research + expert stages | accuracy |
|---|---|---|---|
| boiler | 53 (accuracy 0) | 68 | 10/15 — no fail; the dossier carried regulation 36 and the landlord duty the earlier article got wrong |
| protein | 53 (R7) | 57 | 0/15 — one mis-citation: the 50 g label reference (from the BNF labelling guide) linked to the NHS page that doesn't state it |
| fence | 55 | (pending) | |
Fixes from these judgements (general):
- U17 (link must be the figure's source page) now blocks: the protein failure is exactly this class, and lint had only warned.
- U18 warns when a figure is credited to a named body with no link anywhere in its paragraph.
- E08: "Yes,"/"No," section openers limited to two per page (Haiku applied the yes/no rule as a template in four sections); RULES updated.
- Research skill: read the law itself for legal duties (guidance pages talk about one document or group at a time; the law's text wins); record each nation/region where rules differ inside the page's market.
- official_facts: everyday audience roles (landlords, tenants, homeowners, drivers, employees, residents, applicants, businesses, contractors, engineers…) set a fact's scope automatically.
- Fence writer (research-stage chain): validate PASS, 1,152 words. Found: a cookie notice stored as an authority fact (→ cookie/consent text filtered from facts); script code ("AdvertiserConsent = false; </script>") and "Image credit:" lines in rendered content (→ Spider markdown parser drops code, consent and credit lines); the dossier cited a 12% figure no fact holds and a source it said it couldn't read (researcher slips the writer caught); expert notes added unsourced safety warnings (the skill already requires them to cite or be labelled judgement; the writer cut them).
| fence | 55 | 56 | 0/15 — the writer added spraying steps ("move horizontally… step down") and credited them to the client's spray guide, which doesn't contain them |

Summary of the research-stage test: boiler +15 (accuracy fail removed), protein +4, fence +1. The research stage removed the research-side failure classes (missing regulation, wrong scope, competitor backbone); every remaining accuracy fail is writer-side: a detail added to, or a figure linked to, a source that doesn't contain it.
- Tried and removed: a lint check requiring every attributed, linked sentence to match a fact from that page. On the three finals it blocked a correct sentence and missed the real fence failure (the invented detail sat in the sentence after the link). Embellishment of a cited source stays with the claim ledger, review.md and the editor's pass, and is the main remaining limit of a Haiku writer.

## 9 October 2026: runs as a program in any agent (audit)

- New entry point `seo.py next <brief>`: a state machine (runs/<run>/state.json) that runs every script step itself (research, outline check, lint, review sheet, validate, eval) and prints exactly one agent task, naming the role, files and WORKFLOW section. `seo.py done <brief> research|expert|review|editor` confirms an agent task and refuses outputs that miss the skill's sections or cite fact ids that are not in the fact sheet. Lint/validate fix rounds are capped (5/3 edited drafts), then the run prints STOPPED instead of looping. `seo.py doctor` checks the setup; `seo.py read <url>` gives agents without a fetch tool a plain page reader (no rendering service, no stealth).
- One trigger contract in every adapter (Claude Code command + skill, Cursor command + rule, Codex/`.agents` skill + prompt, Antigravity workflow + skill, global skill, AGENTS.md, GEMINI.md): run `next`, do the printed task only, `done` when asked, repeat until DONE/STOPPED. `.claude/settings.json` allows `python scripts/seo.py` and web tools so the loop does not stop for approvals.
- Fixtures: live checks against a site that rate-limits us are reported as SKIP, not FAIL.
- Cold start (Haiku, given only the Cursor command text, tulip brief): DONE in 15 min, validate PASS, 0 lint blocks. Friction it reported, all fixed: it ran lint/validate itself because WORKFLOW sections mention them (every task now says `next` runs the checks), it assumed final.md was missing before the editor pass (the task now says it was just validated), and the brief's word range conflicted with the pack's (the draft task now prints the one range to aim for).

## 9 October 2026: fact-check stage, Sonnet writer, attribution checks

- New agent stage `fact_check` (7c): `next` builds `verify_sheet.md` (every sentence of final.md that may state a fact, with its links and closest verified fact); a fresh agent gives each a verdict (SUPPORTED/ADVICE/FIXED/CUT) in `verify.md`; `done verify` refuses a sheet with missing rows or SUPPORTED without a source. Claude Code agents: `seo-writer` and `seo-fact-checker` run on Sonnet.
- Sonnet runs (judged blind on Haiku): CRM 51 (accuracy 8/15, no fail; humanization 2/20; Microsoft page linked 6 times after the first U18 version), tulip 52 (accuracy fail). Fact-check totals: CRM 36 supported / 7 advice / 11 fixed / 2 cut; tulip 52 / 15 / 8 / 1.
- Root cause of both tulip accuracy fails (first and second run): every "wrong" claim was verbatim on the RHS growing guide, but placed where the reader takes it as another source's claim ("The RHS says…" after a link to a different RHS page; John Innes compost and 18–20°C storage right after "Gardeners' World says…"). The judge checks the source it is pointed to.
- Lint, general: U18 now blocks a sentence that credits a publisher when the nearest link to that publisher is a different page than the one its claim is on, or when none is linked; U20 (new) blocks an uncredited sentence whose fact belongs to a different publisher than the one credited last in its section (a sentence naming a person, firm or document resets the credit; one government's sites count as one source); U07 blocks a page linked more than three times; E07 blocks a third section that ends on the brand's verdict. Banned: streamline, simple yet powerful, empower.
- Fixes from operator friction: list markers stripped from `--add-fact` values; tracking parameters stripped after redirects (`?bc=OTH`); researchers and checkers copy exact words from `seo.py read`, not summarising fetch tools; review.md refreshed before the editor's pass; WORKFLOW sections no longer tell agents to run checks `next` runs.
- After resuming both runs with the new checks (Sonnet writer, Haiku blind judges): CRM 51 → 58 (accuracy 9/15, no fail), tulip 52 → 55. The tulip page's remaining −15 is a judge error: both "wrong" claims are verbatim on the RHS bulb-planting page the sentence links (`rhs-first-year`, `rhs-missed`); a previous judge verified them. The judge read through a summarising fetch tool. JUDGE_PROMPT now requires `seo.py read` for verbatim source text.
- U18/U20/U07 interlocked on the tulip resume (STOPPED after 5 rounds): U20 demanded links that U07 capped. Fixed: U20 asks for the source to be named, not linked; U18 accepts a link later in the same section; the U07 and U18 messages name the page to keep/link. E07 verdict check widened to any "We'd <verb>", "For X, we'd…" and verdicts that open a section's last paragraph.
- Remaining gap to 95, by the judges: repeated "we'd" verdict per section (now blocked from the third), coverage the research didn't gather (CRM: pricing, AI, a fourth CRM type on the linked Salesforce page; tulip: flowering months, frozen-ground step), and trust (no byline/experience: needs the client's `author:` and `experience:`).
- Verbatim judge (reads sources with `seo.py read`) on the unchanged CRM page: 44 (the earlier summarising judge gave 58). It found one real attribution error the others missed: "Salesforce reports IDC data…" linked CX Foundation, not Salesforce. U18 missed it because sentence-initial names were ignored; fixed (names are matched only against publisher labels, so the first word is safe). Single Haiku judges vary by ±10 on the same page; compare like with like.
- Coverage: Spider writes headings as a bare "##" line with the text on the next line, so every Spider-rendered competitor (Salesforce, IBM, DutchGrown) had an empty outline and shared topics were computed from half the SERP. Fixed in `spider.md_blocks` (cache key bumped). Heading clustering now ignores the query's own words ("CRM", "tulips") that merged unrelated sections; a heading that is only the query plus a question word clusters on that word ("Where to plant tulips"). Competitor pages in another language than the locale are skipped. The plan lists shared topics on 30%+ of pages as T1..Tn with example headings, and `done research` refuses a dossier without a line per T-number. Recomputed topics now include CRM types (4/6, incl. Salesforce's fourth type), benefits, features, who uses CRM; tulip where/how/buying/watering/flowering times/deadheading/propagation.
- Verbatim judge on the resumed tulip page: 67 (accuracy 12/15, no fail; was 52 → 55). The judge found `seo.py read` dropping RHS sentences: a glossary tooltip (`<button>` with its own `<p>` popup) mid-sentence closed the surrounding paragraph, so "Dry bulbs are planted in autumn (September to November)…" and "On wetter soils…" were lost from every parsed page with inline tooltips. Fixed in `_Doc`: end tags inside skipped chrome are ignored, and a button keeps its own label while its popup is dropped. Parsed-page cache key versioned (PARSER_VERSION) so old parses are redone.
- Fresh end-to-end runs of both briefs started with all fixes (Sonnet operator; runs from round b archived to backups/old-test-runs/2026-10-09-round-b).
- Fresh end-to-end runs (all fixes, Sonnet operator, verbatim Haiku judges): tulip 70 (accuracy 12/15, no fail; one misattribution: a blog author's habit credited to the seller that hosts the blog), CRM 45 (accuracy fail on one ambiguous word: "the 2025 figure is a slip", meant as a dip, read as an error; humanization 6/20). Fact-check totals: tulip 56/6/7/0, CRM 45/17/9/1.
- Fixes from these runs: H07 had been silently replaced by U18's looser ATTRIB (same class attribute name) so "sales calls" counted as attribution; renamed. H07 verbs now include rates/gives/sets out/cautions/agrees/argues/observes, blocks above 15% (tulip had 17/86 source-first sentences), and its fix tells the writer to credit once per paragraph. H01 contrast now catches the "…, not Y" tail and blocks from the third use. Tracking parameters cleaned where every fact is created and in the brief's official_sources. Research console notes go to research_log.txt so the operator only sees `next`'s task. Glossary tooltips: full-page text (`_Extract`) drops popups too, and `--add-fact` also checks the reading text, so real sentences ("If the pH of your soil…") verify; parse cache versioned. HoV luggage-fit fixtures SKIP when the shop rate-limits product pages.

## 10 October 2026: full audit and a new finance run ("what is a stocks and shares isa", Nutmeg)

- Clean-up: the 1.4.6 Antigravity plugin (5 skills, 23 scripts, legacy workflow, Scrapling runtime pointer) moved from ~/.gemini/config to `SEO automation backups/antigravity-asdivigitals-1.4.6`; current adapters installed for Antigravity, Cursor and Codex (`install_adapters.py`, which now lists only page-seo). Retired to `backups/retired-2026-10-10`: five descriptive plugins nobody ran (outline, write, humanize, authorship_lint, final_verify, whose SKILLs told agents to run checks by hand), `references/` (1.x SOPs incl. duplicate -v1.0 copies), docs/INVENTORY.md and docs/REPORT.md. ARCHITECTURE.md rewritten to the real 10-stage run and the observed plugin waves.
- Windows Application Control now blocks spaCy's compiled library on this machine. Every comparison crashed. Fixed: `nlp.tokens` falls back to plain-rules lemmas; semantic_graph skips entities/triples without spaCy; `doctor` reports it as a warning with the reason.
- Research scripts, 56 s first run (24 s cached). Waves: foundation + serp_intel → competitor_scrape, site_profile, reddit_voice, gsc_insights → info_gain, keyword_research, official_facts → query_map → semantic_graph → research_plan. Defects found and fixed, all general: YMYL was off for an investing page (no gov result in the top 10) — serp_intel now also decides YMYL by topic (money, health, legal, safety words in the query and titles); consensus figures missed every money amount ("£20,000" has no unit) and dropped short topic words ("ISA") — fixed; the £20,000 allowance now reaches the plan.
- Researcher (Sonnet): 51 facts (GOV.UK/HMRC, FCA, FSCS, DMO, NS&I, Moneyfacts), all 8 shared topics accounted for, the "6.79% average return" traced and qualified, 2027 cash-ISA change found. It also found the client rebranded (nutmeg.com → J.P. Morgan Personal Investing). Foundation now detects a homepage that redirects to another organisation and tells the writer to name the business as the live site does ("formerly …").
- New: AEO/GEO rules (RULES 8b: self-contained 40–60-word answers, one-sentence definition, a sourced figure in the first 300 words, quotes where wording matters, dates on anything that changes, YMYL duty-of-care warnings); `updated:` date stamped into final.md; expert read (pass 2) of the finished page with today's news and business fit, applied by the editor's pass.
- Full run of the new finance keyword, stage by stage (Sonnet agents as in Claude Code; I operated `next`): research scripts 56 s → researcher 51 facts, dossier gated → expert notes (FCA-regulated adviser perspective) → outline (1 Skip: the US "7% rule") → draft → lint 18 → 5 → 1 → 0 blocks → review sheet → validate → **expert read** (new): verdict "publish after changes", found the 2027 ISA regulations had been laid on 14 Sept 2026 (the page said "still to be laid"), two April-2027 rules the page lacked, the 28 Oct 2026 Budget, a stamp-duty error; 5 news facts recorded → editor applied 12 of 15 items, declined 3 with reasons in editor.md → fact-check: 44 supported, 4 advice, 20 fixed, 2 cut → lint after fact-check 15 → 2 → 2 → 0 → DONE with `updated:` stamp.
- Fixes from this run (general): C01 recognised client facts only on the brief's domain, so after a rebrand the client's live-site facts were "unapproved" — now the redirect target counts as the client's site; the pack's "do NOT state prices" read as a ban on fee rates — now "no product prices; a verified fee, rate or charge may be stated with source and date"; table rows copied from `seo.py read` ("Basic rate | 10.75%") failed exact-text checks — pipes ignored in matching; fact-check fixes copied source wording (C03), over-linked (U07) and used a banned word — the fact_check skill now requires own wording or a marked quote, at most two links a page and the brief's banned_claims; new lint A03 blocks a first sentence under a heading that opens with a back-reference ("It…", "This…"), for AI-answer extraction.
- Blind verbatim judge on the ISA page (pass 1): 53 (accuracy 6/15 with no invented claim: a heading said "over 10 years" over 15 years of data, and two client-product conditions were missing — the client's ISA is not flexible, and its fund costs and spread; humanization 8/20: claim → "X says/adds" → caveat in every section and three disclaimer lines). Every sourced figure verified word for word, including the 2027 rules the expert read added.
- Fixes (general): H07 now recognises "The HMRC factsheet says", "the Debt Management Office (DMO) says", "FCA guidance on investing says" (it caught 6 of the page's 12 attributions; it now blocks the ISA, tulip and fence pages, which judges marked down for it); RULES: a heading promises exactly what its evidence answers; when a page explains a condition or cost, say how the client's product stands on it and give every cost layer; YMYL warnings once each, in the section and concretely, no stand-alone disclaimer lines (three boilerplate patterns now block); the expert read checks the client's product against every condition the page explains. Late stages of the ISA run re-run with these (pass-1 files in backups/old-test-runs/2026-10-10-isa-pass1).
- Pass 2 blind judge: 49. Every claim verified again and the client's non-flexible ISA is now stated, but the "over 10 years" heading over a 15-year average survived and the judge gave it the full −15. Cause: number tracing skipped question headings. New H11 blocks a question heading whose number-with-unit ("10 years", "7%") no fact carries; it fires on exactly that heading and nowhere else in the ten finished pages. U07 now blocks a page linked more than twice, matching RULES and the fact-check skill.
- Judge variance stays large (same CRM page 58 / 44; ISA 53 / 49 with different deductions). Single Haiku judges rank the same defects differently; compare like with like and read the deductions, not only the total.

## 10 October 2026: one command everywhere

- `seo.py start "<request>"`: one entry point that takes free text — a brief, or `<client>: <keyword> | <instructions>` in any order ("what is a lifetime isa for nutmeg -- keep it short", "\"how to paint a fence\" ronseal, aimed at beginners", "best running shoes for example.com"). It finds the client by profile name, slug or domain (onboards an unknown domain), reuses an existing brief for the keyword, writes the brief with `instructions:`, and continues straight into `next`. The only question it can raise is NEED A CLIENT / NEED A KEYWORD. Instructions travel in the fact sheet and appear in the writer pack as operator instructions (angle, audience, tone; accuracy rules still win).
- `install_adapters.py --apply` writes the same `/page-seo` contract, with the absolute path, at user level into every agent present: Claude Code (command + the four role agents), Cursor (command), Codex (prompt + skill), Antigravity (workflow + plugin skill), Gemini CLI (TOML command), Copilot in VS Code (prompt file), Windsurf when installed. Project-level duplicates (.claude/commands, .claude/skills, .cursor, .agents, antigravity/, codex/, global/) retired to backups; AGENTS.md and GEMINI.md carry the same `start` contract for agents that read them.
- Verified from outside the project folder: `start "pensionbee: how much should i save for retirement | for people in their 30s, plain English"` created the brief, ran research (50 s) and printed the researcher's task with absolute paths.
- Fixture: MasterFastVisas' live site no longer shows its "under 48 hours" claim, so the pipeline rightly refuses it; good.md blocks on such lines now report as SKIP.

## 10 October 2026: question coverage (Antigravity's "bridging loans in uk" page)

- User: wording good, but too few People Also Ask, related and competitor questions. Cause, all in query_map: (1) Google's PAA drifted with the place word ("…in the UK" → "differences between the UK, Great Britain and England") and PAA skipped the topic check, so a geography H2 reached the page; (2) "separate page" was decided from SERP overlap alone, so rates, alternatives, bad credit and interest rates were left out although competitor guides answer them in-page; (3) competitors' question headings were used only when no PAA existed, and clustered on the topic words every heading shares ("bridging loan"), so all merged into one.
- Fixes (general): PAA that never mentions the topic is dropped; competitors' shared question headings are always candidates, clustered on their own words; a "separate page" query that a ranking page answers under a heading becomes "answer it here briefly"; lint Q03 blocks a PAA/competitor question planned inside a section that no paragraph answers (its own words together), warns for related/autocomplete ones; Q04 blocks a heading for a drifted question. Bridging plan: 2 H2 (one off-topic) → 7 H2 + 14 in-section, 2 separate (Martin Lewis).
- New Spider key stored in .env (SPIDER_API_KEY).
- First resume of the bridging page: geography H2 removed, "How much can I borrow?" and approval time added; the fresh fact-check rewrote 43 sentences and cut 6 of Antigravity's page (only 33 of 87 original sentences survive verbatim). Alternatives, best rates and bad credit were still missing although the new plan required them: the outline (written under the old plan) had `Skip: … — deserves its own page` lines, and lint/outline honoured them. Fix: a Skip whose reason is "its own page" no longer exempts a question the current plan says to answer here (other reasons still count). Second resume running to add those sections.

## 11 October 2026: page type first, internal links, and why PAA was missing

- The user's request "content for this client and page https://taptoncapital.co.uk/second-charge-bridging/" became the keyword "content for this client and page https:// /second-charge-bridging", a /blog/ URL, page type guide, task new. Google was searched for that, so PAA/related/autocomplete were empty. Fix: `start` treats a page address as "this page": new `seolib/pagetype.py` intake reads the page and scores type signals (path, offer wording, forms, Product/Service/BlogPosting markup, blog furniture, question H1) → service/product/category/home/location/guide/company, takes the main keyword from the H1's head phrase (else the slug) without the brand or "your complete guide", sets task rewrite when the page exists, logs the evidence. Tapton's page → service, "second charge bridging loans", rewrite. RULES gained build rules per page type.
- Root cause of thin PAA on every UK run: we sent Serper `gl=gb`; Google's UK code is `uk`. With gb: organic only, no PAA, no related. With uk: 4 PAA + 8 related. Fixed in serper.locale_params.
- Question quality: UK SERPs still leak US questions ("$100,000", "Dave Ramsey", "Bank of America"): query_map now drops another market's currency and names Google describes as another country's (knowledge panel/snippets → nationality); "Martin Lewis" stays. Competitors' questions now include body FAQ lines; brand pitches ("Why choose Commercial Trust?", two-word brands) and CTAs ("Ready to get started?", "…with us?") are dropped.
- official_facts searched only gov.uk/nhs.uk and downloaded council committee PDFs and NHS board papers for 311 s. Now YMYL topics search their sector's regulators per country (UK money: FCA, MoneyHelper, FSCS, Bank of England; health: NHS, NICE; legal: legislation.gov.uk; safety: HSE), and local PDFs are skipped unread: 25 s, 35 FCA facts.
- New internal-links stage (9c), from Koray Tuğberk Gübür's interlinking rules (Sitechecker interview; Holistic SEO topical-authority case study): `seolib/links.py` ranks the client's pages against each paragraph by phrase match of each page's main term; `plugins/internal_links/SKILL.md`; `done internal_links` checks the log against the draft; lint U21–U24 (empty anchors, an anchor more than 3 times, one anchor to two pages, a link in the answer sentence).
- report.md now has "Searcher questions and where the page answers them": every planned PAA/related/competitor question with the heading or sentence that answers it, or "not answered". Bridging page: 18 of 21.
- Markets (user: "what if the article targets another market?"): new `seolib/market.py` decides the locale from the operator's words ("for the US market", "Australian readers"), else the page's own signals (og:locale, html lang, domain ending, currency; a .co.uk site whose theme says en_US stays en-GB), else the client profile; `start` prints MARKET with its source. Serper self-check: rankings without PAA/related retry the alternative Google code and hl=en. Probed AU, DE, IN, AE with every parameter (gl, location, city): Serper returns organic but never PAA or related outside UK/US. Spider's Google page scrape returned Google's block page; pushing past it would be evading Google's bot detection, so it isn't used. Instead: English markets borrow PAA from UK then US results (filtered), and every deep run collects the market's own question searches (autocomplete with each language's question words: en, de, fr, es, it, nl, pt); when PAA is borrowed, local questions lead. Clients match on a distinctive first word ("tapton").
- Verified en-AU end to end: AU rankings (ANZ, Canstar, CommBank, NAB…), all 9 competitor pages rendered via Spider into the knowledge graph (60 entities, 17 topics), H2 plan led by "how does bridging finance work in australia".

## 11 October 2026: knowledge graph and topic outline for the writer

- User: the writer should get a full knowledge graph (entities, attribute values, facts, semantic triples, per market and topic) and, separately, a full outline holding every PAA, related and competitor question.
- Old graph was thin: spaCy triples like "loan — be — expensive", "speed — be of — essence"; entities mostly generic nouns; nothing when spaCy was blocked.
- New `seolib/graph.py` (plain rules; spaCy only sharpens): entities from noun runs two+ sites use near the topic (plurals, hyphen/space forms and bracketed acronyms merged: "loan-to-value (LTV)"), typed (kind, party, measure, rule, organisation, concept); definitions (wording most sites share); attribute values from labels ("Loan Term: 1 to 18 months"), the measure before or after the figure, shares ("75% of the property value"), rates ("1.5% per month"), ranges joined ("between £50k and £750k"); relationships between entities and to plain noun phrases ("tomatoes — need — loose rich soil"), never from questions or qualified subjects ("dwarf tomatoes").
- Market: on YMYL topics a page written for another market is left out whole (rocketmortgage.com in the UK bridging SERP); on other topics only its other-currency, Fahrenheit and US-gallon sentences go (US gardening guides still teach tomatoes).
- Task queries: "how to grow tomatoes in pots" is about "tomatoes" (central entity), with kinds determinate/indeterminate/cherry.
- New `topic_outline` plugin: every H2/H3 of every ranking page with its text, clustered across sites (own words, related text, or the same sort of question read without the topic's words), wrappers with 7+ H3s split, self-promotion ("our", "us"), widgets, store locators dropped; every question placed (PAA leads used to group search-only questions: "What not to do" + "9 common mistakes"); other countries' variants (nz, india, australia) dropped.
- Rendered by `seolib/kgdoc.py` as `knowledge_graph.md` (7 KB) and `topic_outline.md` (9 KB); re-rendered before the outline and draft tasks so researcher facts attach to entities and sections; the writer pack points to both; WORKFLOW 3/4 require them.
- Bug found on the way: plugins load spaCy in parallel threads; the torch stub in `import_spacy` raced and one failure switched the run to plain rules (subject "tomatoe"). Loading is now serialised; plain-rule lemma handles "-oes".
- Results: second charge bridging (UK, 8 pages): 12 sections (definition 5/8, how it works 5/8 with its steps, criteria 5/8, costs 4/8, risks…), 32 questions placed; LTV up to 75% (2 sites), loans £25k–£500k (2), consensus definition (4 sites), FCA facts under the topic. Tomatoes in pots (UK, 6 pages): 11 sections (planting 4/6 with three PAA, soil, support, pot size, mulch, watering, mistakes), 17 questions placed, 7 dropped with reasons. Fixtures: ALL PASS.
