# Page optimiser and quick wins (U-B, PF1, PF2, PF3, PF6, PF7)

## U-B. The user's workflow: position ≤20 (or ≤30) → pages → queries → H2s → same-country competitors

**When.** Weekly or monthly. These pages are already tested on pages 1–3, so they are the cheapest wins.

**Position band.** The band is a parameter: ≤20 by default, ≤30 for a wider net, 8–17 as the tight preset. Experts differ:
- Sturm uses 3–20;
- Quaid uses 8–17;
- ContextBolt uses 8–20.

**Steps** (`seo.py gsc data <client> optimizer`; the audit adds the heading check):
1. **Choose the pages.**
   - Data: page rows, 90 days, `byPage`, final data, non-brand.
   - Keep pages with impression-weighted position ≤ the band and ≥500 impressions in 90 days [synth; scale to the site].
2. **Bucket each page's queries:**
   - **ranking:** position ≤ band, ≥20 impressions;
   - **should_rank:** position band–50;
   - **question:** matches R-Q1;
   - plus modifiers already earning impressions (materials, variants, urgency; Ulku).
3. **Route each query** (Sturm's router):
   - Relevant and missing from the page → add it in a heading or section.
   - Not relevant enough → a dedicated page, linked from the ranking page.
   - Two or more client pages share it → PF9 cannibalisation.
4. **Anonymised gap.** If more than 60% of the page's clicks are on unlisted queries [synth], optimise for topic coverage, not individual keywords.
5. **Competitors in the same country.** Search the exact head query in the client's country; the pipeline's `serp_intel` and `competitor_scrape` do this. Compare:
   - sections and depth;
   - author and E-E-A-T pages;
   - internal and external links;
   - schema and SERP features;
   - whether an AI Overview shows and cites them.
6. **Queue it.**
   - Run `/page-seo <site> | gsc queue optimizer 10`.
   - Each page's instructions carry its ranking, should-rank and question queries. `gsc_insights` → `query_map` turn them into H2s or in-section answers, and lint blocks the draft if a striking query with 100+ impressions is dropped.
   - The title leads with the primary query.
   - Past page 1, titles rarely lift CTR (Quaid), so position comes first.
7. **Optional "1-hour update"** (Sturm), for top pages:
   - add 2–3 H2s for under-covered clusters;
   - link from the updated page to one weak page;
   - refresh the intro and the date;
   - request indexing once, with approval.

**Decision rule.** Act on the strongest signal per page:
- band position (Sturm);
- CTR deficit (PF2);
- under-covered clusters, i.e. top queries missing from the title, H1 and H2s (`missing_from_headings`).

**Validate.** PF26: compare 28 days before with the 28 days starting 7 days after, using final data, against unchanged pages in the same folder (`data impact` gives the direction).

## PF1. Striking distance by query

`data striking`: queries at positions 4–20 (or 8–20) with ≥100 impressions, non-brand.
- One page holding ≥80% of the query's impressions [synth] → on-page H2 or section, plus 2–5 internal links with the query's words as anchors.
- Several pages → PF9.

## PF2. CTR deficit → title and meta (Neil Patel)

`data ctr`.
- **The curve** is the site's own, built from non-brand queries: the impression-weighted median CTR per position (Botify's method). Positions without enough data use a conservative fallback.
- **Candidates:** position ≤10, ≥500–1,000 impressions in 90 days, CTR below 0.6× expected [synth], ranked by missed clicks.
- **Check the live SERP** before rewriting. Competitor rich results, video or an AI Overview can explain the gap. AI Overviews cut position-1 CTR about 58% where they show (Ahrefs, Dec 2025).
- **Patel's UI version:** Pages sorted by CTR ascending → Queries → retarget the title and meta.

## PF3. Zero-click, high-impression queries

`data zero_click`: ≥1,000 impressions, ≤5 clicks, position ≤5 [synth].
- **Definitional queries** (often AI Overviews): aim to be cited. Impressions are the KPI; add a reason to click (data, tool, visual).
- **Commercial queries:** PF2.

## PF6. New and emerging keywords

`data emerging`: queries with impressions now and none in the previous 90 days.
- Within the band and the same intent → expand an existing page.
- Distinct intent → a new page (`queue new`).

## PF7. Page–query alignment

`data alignment` finds:
- a commercial query landing on a blog post;
- a question landing on a product or service page.

Fix by pointing internal anchors to the right page, strengthening it, and de-optimising the wrong one.

Sources: Sturm (Pareto SEO, 1-hour update), Quaid, Neil Patel, Caleb Ulku, ContextBolt, SEOTesting, Botify, Ahrefs. Links are in the research report §4.1 and §4.4.
