# AI Overviews, AI Mode and generative-AI citations (AI1–AI5)

## What Search Console counts

- **Since 16 Jun 2025,** AI Mode data is counted in the normal Web search type:
  - every link inside an AI Overview shares the Overview's one position;
  - an AI Mode follow-up counts as a new query;
  - an impression counts only when it is scrolled or expanded into view;
  - Search Labs is excluded.
- **The Generative AI report** (announced 3 Jun 2026, worldwide 31 Aug 2026):
  - covers Search (AI Overviews + AI Mode) and Discover generative features;
  - shows **impressions only**, with Pages, Countries, Devices and Dates tabs;
  - is **not in the API or BigQuery** (re-tested 11 Aug 2026);
  - is already included in Web totals, so never add it to them.
- **No AIO/AI Mode filter exists** in the Performance report. Any claim otherwise is contradicted by Google's help page.

## AI1. "Cited but not visited"

1. Monthly, the user exports the Generative AI report's Pages tab (`../ui_checklists.md`).
2. Run `seo.py gsc ingest <client> ui_genai <file>` and join it with the page clicks (`data page`).
3. Sort by AI impressions and trend them weekly; read ratios, not absolutes.
4. Pages with high AI impressions but low clicks need a reason to click: original data, tools, visuals.
5. Keep pages snippet-eligible: no blanket `nosnippet` or `max-snippet:0`.

## AI2. Decoupling score

`data decoupling`: impressions up ≥20%, CTR down ≥25% year on year, and a stable position or one in the top 3 [synth]. These pages are likely cited in AI Overviews. A related fingerprint: long-tail queries with average position improving to about 1–2 while CTR collapses.
- Route them to AI1 or PF3, not to a title rewrite.
- In the rewrite queue they carry the AI2 reason.

## AI3. AI Overview presence join

Quarterly, use a SERP API to flag which queries show an AI Overview. Compare CTR with and without one; this segments the PF2 curve. Ahrefs (Dec 2025): position-1 CTR is about 1.6% on keywords with an AI Overview, against 7.3% two years earlier.

## AI4. Eligibility hygiene

- AI features need an indexed page that is eligible for a snippet.
- No special schema or llms.txt is needed. "AI optimisation is still SEO" (Google, May 2026).
- Structured data must match the visible text.

## AI5. The Generative AI opt-out control

- It is set per property.
- It removes the site from AI Overviews, AI Mode and Discover AI.
- It is separate from Google-Extended.
- It is a business decision only: **never** change it without the user's explicit yes.

## Proxies for AI-driven demand

| Proxy | Method | Source |
|---|---|---|
| Conversational queries | 10+ words, R-CONV | `questions.md` PF4 |
| `site:` queries | queries containing `site:` | PF5 |
| Brand demand | brand-query trends (`data brand`) | Aleyda Solis's proxy for AI influence |
| AI-Mode-style queries | LLM classification of API query rows | Glenn Gabe |

Every proxy undercounts: anonymised queries reached 57.7% of impressions on one site (Suganthan).

Sources: Google's help on Performance data and the Gen-AI report; Search Engine Journal (Suganthan); Brodie Clark; Ahrefs (Great Decoupling, AIO CTR); Nectiv. Links are in the research report §4.5.
