# Research principles

The research layer (`scripts/seolib/prep.py`, `clientpages.py`, `domains.py`, `nlp.py` and the plugins in `plugins/`) applies the same rules to every query, client and country. None of them names a topic, a niche or a client. Every threshold is either world data (country codes, government domains, units, US↔UK spelling), plain English (question words, modifiers, task verbs) or a ratio computed from the live SERP for this query.

Niche knowledge lives in exactly one place: the client profile (`clients/<slug>.yaml`): synonyms, reader nouns, banned phrases. The pipeline never needs it to run.

## 1. Sources: who may be believed, and for what

| Tier | How it is recognised | How the writer may use it |
|---|---|---|
| Authority | Government and public-sector domains of the page's country (world list), international bodies, national before local | States rules, limits and figures; wins any conflict |
| Independent organisation | Charities, professional bodies, universities (`.org`, `.org.uk`, `.ac.*`, `.edu` …) | Facts and guidance, attributed |
| Publisher / trade / brand | Other businesses that don't sell what the client sells | Facts with attribution |
| Competitor | A business in this SERP, or one whose fact is about the client's own product category (query words that also appear in the client's claims) | Context only: attributed, limited to its product, never the main answer or the first link |
| Client | The client's own pages and homepage claims | The client's method, offer and figures, in the client's voice; an authority still wins |
| Forum / social | Domain or forum-path match | Quoted experience only, linked, never on YMYL as support |

## 2. Relevance: a page must be about the query

- A searched authority page must contain most of the query's content words; a local one (a council, a trust) must also name them in its title or headings.
- Re-hosted pages (`/viewer/`, `/proxy/`, `/mirror/`), booking and careers subdomains, and keyword-stuffed slug clusters are spam, not sources.
- Scraped clones of a ranking page (over half its text repeated on another domain) count once.
- Client pages: same-topic pages are those whose slug words are all in the query (task verbs aside); location or catalogue template families are never guides; the client's site is also searched for the query directly.

## 3. Facts keep their context

- A fact is a whole sentence with a verb, never a title or heading.
- A sentence that refers back ("this", "if this is the case", "if so", "in that case") keeps the sentence it refers to; follow-on rules keep the whole chain.
- Every fact carries the source page's title and section, and a label when the page is written for one group (patients, professionals, members).
- Values added by hand must sit next to the claim's own words on the page, numbers included; values that point back to an unstated case are rejected, and stale ones are skipped when a run reloads saved facts.
- Sources are cited at their final URL with tracking parameters removed; PDFs are read as PDFs.

## 4. Freshness and locale

- YMYL topics get a "this year / last year changes" search on the authorities; a change already in force belongs in the answer, a future one in a sentence.
- Questions borrowed from another locale's SERP are filtered for that locale's units, money, places and institutions; answer leads are looked up in the page's own locale and never come from forums, social sites or adverts.
- A client claim in another market's currency is dropped; a client figure that isn't on the visible homepage is removed from the claim (the offer stays).

## 5. What the page must cover

- Topics shared by 40% or more of the readable ranking pages (clones removed) must be covered or explicitly skipped; one-word structural topics ("Method") are a reminder, not a heading.
- Figures that several independent pages state (consensus figures) must sit in a sentence with the query's words.
- Length follows the SERP both ways: the target moves toward the ranking pages' median, never into padding.
- Questions: questions naming another brand, format words ("explain", "chart"), seasons and "near me" never become separate pages or sections on their own.

## 6. Conflicts are surfaced, not resolved silently

- A client-page figure that differs from an authority figure on the same subject is flagged in the pack.
- Client claims whose counts disagree across the client's own pages are flagged.
- When sources disagree, RULES requires the writer to say which applies and why.

## How these rules were found

Each rule came from a blind judge's finding or a writer's report on one of ten test niches (visas, luggage, tyres, CRM software, dog food, protein, pensions, phone repair, sourdough, boilers, fences, bulbs; see `docs/TEST_FINDINGS.md`), then was written as the general principle behind the defect and checked against the other niches. Rules that only fitted one niche, or flagged correct text elsewhere, were removed (for example a "number context" check and an authority-vs-authority conflict flag).
