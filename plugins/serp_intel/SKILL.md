---
name: seo-serp-intel
description: Read Google's results for a keyword in a specific country the way a senior SEO does. Search intent, the dominant content format, SERP composition (forums, government, video, image, marketplaces, big publishers), SERP features, People Also Ask (expanded), related searches and autocomplete, plus what each pattern means for the page you write. Use before planning any page, or alone for keyword intent analysis.
---

# SERP intelligence: what Google already rewards

**Script:** `run.py`, through Serper.dev (`SERPER_API_KEY`; 1 credit per search, cached 3 days).

**Output:** `research/serp_intel.json`. It contains:
- `organic`: the top 10, each with `kind` and `shape`
- `paa`, `paa_answers`, `related`, `autocomplete` and `question_autocomplete`
- `expansions`
- `intent`, `format` and `composition`
- `features`

## Country and language
`locale` in the brief (`en-GB`) maps to `gl=gb`, `hl=en`. Intent differs by country. "visa status check" in the UK leans towards eVisa status, while in the US it leans towards CEAC. Never reuse another country's SERP.

## How intent is decided

| Signal | Points to |
|---|---|
| Query words: buy, price, cheap, deal, order, shop | Transactional |
| best, top, vs, review, compare, alternatives | Commercial investigation |
| how, what, why, guide, meaning, tips | Informational |
| login, official, portal, account, contact | Navigational |
| near me, opening hours, local pack shown | Local |
| Result shapes: product or category pages | Transactional |
| Result shapes: listicles and comparisons | Commercial |
| Result shapes: guides, articles, forums, video | Informational |
| Result shapes: tools, portals, services | Navigational (0.7) plus informational (0.3) |
| 3+ government pages | Official-source/navigation signal; verify rules, but preserve the client offer and page purpose |
| Shopping results | Transactional |

The primary intent is the highest score. A secondary intent is kept when it scores at least half of the primary. Confidence is the primary's share of all points.

## What each SERP pattern means for the page

| Pattern | Page strategy |
|---|---|
| Official or government pages dominate | Use those sources for rules and necessary official actions. Follow the Page job: a commercial page explains the client's verified role and next step; an informational page may explain the official workflow. Preserve direct-route disclosures and limitations without repetitive competing CTAs. Never imitate a government page or imply official status |
| Forums or UGC rank (2+) | Google values lived experience. Add attributed real-world reports (info_gain, reddit_voice) |
| Video ranks (2+) | Use numbered, screen-by-screen steps. Mention a video only if the client has one |
| Listicles dominate | A clear shortlist with a reason each; scannable structure; a comparison table if facts allow |
| Product listings or marketplaces dominate | Products and specs first, short copy; link product pages. A long essay will not rank |
| High-authority publishers dominate | Win on specificity, unique data and the client's own facts, not breadth |
| Image sites (Pinterest, Instagram) rank | Visual intent: plan image placements in the outline, naming subject entities (alt text work is the client's) |
| Tool or service intent | Short page. The tool, link or selector comes first; explanation is supporting |
| Mixed intents (secondary present) | Lead with the page's job; cover relevant secondary intent in an appropriate section or FAQ, without forcing another H2 |
| Brief's `page_type` conflicts with the SERP format (hub versus listicle SERP) | Keep the client's page type (it's their architecture) and adopt the format's strengths inside it. Log a decision |

## People Also Ask and its fallbacks
1. PAA on the main SERP becomes candidate coverage. Guides may use question H2s; commercial pages may answer in offer/process sections or FAQ H3s. The Page job determines structure.
2. Deep mode follows the first 2 PAA questions one level down (their own SERPs' PAA).
3. No PAA anywhere: the PAA of the top 3 autocomplete variants.
4. Still none: question-prefixed autocomplete ("how / what / can i / why + query"), keeping only suggestions that start with a question word and have 4+ words. These are real searches; log that PAA was absent.
5. DataForSEO configured (keyword_research): its PAA with click depth 2 is added. It is deeper than Serper's.

Google's own PAA answer source is shown in the pack. It tells you which page currently owns that snippet, so beat it with a more direct 40–50-word answer.

## Edge cases

| Situation | What to do |
|---|---|
| Serper error or key missing | Plugin fails cleanly. Downstream plugins degrade (no SERP), and the run continues on foundation facts. Logged |
| Fewer than 10 organic results | Analyse what exists. Confidence is lower |
| The client ranks in the top 10 | Note its position. A rewrite must keep what ranks (gsc_insights) |
| SERP dominated by one domain (site links) | Navigational or brand query. Don't fight it; build supporting content |
| AI overview or answer box present | A short direct answer under the H1 matters even more |
| Country-ambiguous query | Trust the brief's locale. Never mix countries |
| Adult, illegal or dangerous query | Stop. That is outside this pipeline |

## Run it alone
`python scripts/seo.py research <brief> --mode quick`, then read "Search intent and what Google rewards" in the pack.

Deep mode also looks up up to two related searches in the expansion wave; each expansion records its source and locale. These lookups provide real URLs for bounded source scraping. Every related query remains in the JSON demand inventory.
