---
name: seo-semantic-graph
description: Build the knowledge graph of a topic in one market from the pages that rank there. Typed entities with aliases and definitions, entity attribute values with the sites that state each value, subject-predicate-object relationships with the sentence that states them, the figures most pages agree on, the heading topics Google expects, and People Also Ask questions no competitor answers. Every node and edge carries its sources. Use to give the writer what to say, or alone for semantic gap analysis.
---

# Semantic graph: the knowledge graph of the topic, in this market

**Script:** `run.py`, calling `scripts/seolib/graph.py`. Plain rules, so the graph is the same with or without spaCy; when spaCy loads, its part-of-speech tags keep verbs and adjectives out of entity names and its entity labels sharpen the types. Up to 4,000 words a page.

**Inputs:** every page `competitor_scrape` read (Spider renders them), the People Also Ask questions, related searches and autocomplete from `serp_intel`, and the query map.

**Output:** `research/semantic_graph.json` (`graph` holds the full graph; the older keys `entities`, `must_cover_entities`, `attributes`, `triples_consensus`, `triples_unique`, `contradictions`, `heading_topics`, `consensus_figures` and `paa_gaps` are derived from it for lint, the outline check and the review). The writer reads it as `knowledge_graph.md`, rendered by `seolib/kgdoc.py` with the verified facts attached to each entity.

## This market only
- A page written for another market (most of its amounts in another currency, or mostly about another country) is left out whole, and named in the decisions.
- A sentence in another currency or about another country is left out.

## Entities
- Noun runs of 1–4 words that two or more sites use near the topic, standing on their own (not only inside a longer name). Plurals merge ("lenders"/"lender"); hyphenated and spaced forms merge ("loan to value"/"loan-to-value"); acronyms written in brackets become aliases ("loan-to-value (LTV)").
- Never verbs, adjectives or adverbs ("required", "flexible"), generic nouns alone ("option", "people"), or page furniture (reviews, calls to action, phone numbers).
- Ranked by share of sites, mentions, appearance in searches and in headings. The query itself is always the central entity.
- Types: central, kind (same head noun: "first charge bridging loan" on a "second charge bridging loan" page), broader class, party (lender, broker), organisation or named thing, rule or document, measure, place, concept.
- Definitions: "X is a / means / refers to …" sentences; the wording most sites share wins.

## Attribute values
A figure (money, percentage, duration, quantity, ranges such as "between £50k and £750k") and the measure it belongs to, found in this order: a label ("Loan Term: 1 to 18 months"); the measure named before it with only verbs and linking words between ("a decision is usually made within 24 hours"); the measure right after it ("75% loan to value"); a share of something ("75% of the property value"); a rate ("1.5% per month"). Each value keeps its qualifier (up to, from, about, range) and its sites. Names of one measure merge ("term", "loan term"). An attribute needs two sites; one site's numbers are leads for the fact-check.

## Relationships
Two entities in one clause with only a verb phrase between them ("loan — secured against — property"). Two or more sites make it consensus; one site's link is kept only when it is specific or touches the topic, and is labelled a claim to check.

## How the writer uses it
Consensus may be said in the writer's own words. Numbers come only from verified facts on YMYL pages; elsewhere a value three or more sites state may be used. Where sites differ, the verified fact decides.
