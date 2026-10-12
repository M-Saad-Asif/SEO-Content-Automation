# Article evaluation rubric (100 points)

The standard is an article a senior SEO and a senior content writer would sign off without edits. Scores come from evidence:

- the automated measures from `seo.py eval <run>`
- quoted lines from the article for every deduction

A deduction without a quoted line doesn't count.

The perception baseline is the operator's own documented failures (from the Antigravity runs), Google's helpful-content and quality-rater guidance, the Koray authorship rules, and Wikipedia's "Signs of AI writing".

| # | Criterion | Points | Full marks when |
|---|---|---:|---|
| 1 | Intent and SERP fit | 10 | The first screen answers the query and fits the declared page type; SERP intent informs coverage, without replacing the client's page purpose with a competitor's format |
| 2 | Coverage and responsiveness | 15 | Every H2 question answered in its first 40–50 words; must-cover entities and expected topics covered; nothing that belongs on another page |
| 3 | Accuracy and sourcing | 15 | Every number, rule and claim traces to a verified fact or the client's data; YMYL costs and conditions stated; official sources linked where their rule or figure is used |
| 4 | Information gain | 10 | Clear value beyond the top 10: client data, computed comparisons, unanswered questions, attributed experience, a reasoned recommendation |
| 5 | Humanization | 15 | Reads as written by an experienced person; no AI tells (deduction table below; cap the total deduction at 15) |
| 6 | Language quality | 10 | No dangling modifiers, noun stacks, nominalisations, vague "this", tense or person drift, or locale errors; sentences are clear on first read |
| 7 | Structure and on-page SEO | 10 | Title (about 60 characters, query), meta (140–160), one H1, logical sections for the page type; guide question headings and commercial FAQ H3s where useful; tables only where facts fill them; descriptive links |
| 8 | Page job: brand and conversion | 10 | Commercial pages explain the client's scoped offer and verified next step near the opening and close, with appropriate process and proof. Sources support facts; necessary official actions, limitations and disclosures remain accurate without repetitive competing CTAs. Guides, hubs and comparisons answer their task, with a client offer only where verified and relevant |
| 9 | Trust and E-E-A-T signals | 5 | Who it's for, limitations, sources and dates visible in the prose; experience attributed; no fake first-hand claims |

## Humanization deductions (from 15)

| Tell | Deduction | Example (from earlier runs) |
|---|---:|---|
| Banned AI vocabulary or construction (lexicon, negative parallelism) | −2 each | "seamless", "It's not just X, it's Y" |
| Framework label or template phrase | −2 each | "Reversal Condition", "One trade-off to consider" |
| Repeated section template (same shape in 3+ sections) | −3 | answer → paragraph → bullets → caveat, every H2 |
| Meta-commentary about the article | −1 each (after the first) | "This guide checks…", "below", "in this section" |
| Keyword stuffing (exact query forced into sentences) | −2 | "A visa status check runs through…" |
| Rhythm too even (sentence-length SD under 80% of the human top-page median) | −3 | every sentence 14–18 words |
| Opener monotony (one first word starts 25%+ of sentences) | −2 | "The…", "The…", "The…" |
| Generic sentence (concrete-noun test: could sit on any page) | −1 each | "Choosing the right bag matters." |
| Rule-of-three padding (a triplet that isn't a real enumeration) | −1 each | "fast, simple and reliable" |
| Stiff or legalistic register | −1 each | "Substantive legal adjudications remain…" |
| No judgement where a reader expects one (no recommendation or "choose X if") | −2 | a comparison with no verdict |
| Colon or em-dash habit (over 1.5 per 100 words) | −1 | "Cost: …", "The catch: …" |
| Over-hedging (hedge words over 2.5 per 100 words) | −1 | "may typically often" |
| Mechanical link placement (link dumps, repeated anchors) | −1 | a list of six bare links |

## Language deductions (from 10)
- Dangling or illogical opener: −2 each.
- Noun stack of 3+ modifiers: −1 each.
- Nominalisation: −1 each.
- Vague "This/It" with an unclear referent: −1 each.
- Person or tense drift: −1 each.
- Locale spelling error: −1 each.
- Grammatical error or unclear sentence: −1 each.

## Accuracy deductions (from 15)
- Any invented fact, URL, feature or claim: **−15 (fail)**.
- A number not traceable: −5.
- A rule attributed to the wrong body: −3.
- A missing cost or condition on a YMYL action: −2.
- A competitor claim stated as fact: −3.

## Pass bar
A score of **95+**, with criteria 3 and 5 each at full marks or at most 1 point off. Anything lower goes back through the automation (rules, plugins or lint), not just the one article.
