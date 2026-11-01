# Who teaches what, and the default where they disagree

## Experts

| Expert | Tactics in this suite | Evidence |
|---|---|---|
| Koray Tuğberk Gübür (Holistic SEO) | Query-count bands and new-query growth as the topical-coverage scoreboard (PF27); impressions momentum and a positive ranking state per subfolder (PF28); branded demand moving with non-brand (PF22); refreshes tied to initial ranking; crawl KPIs (<100 ms, 99% canonical HTML, 99% 200/304; interview only); 410 for removals | His case studies; the numeric KPIs come from an interview |
| Edward Sturm | Positions 3–20 router: expand the page, or create a new one and link it (U-B); the 1-hour update; folder segmentation; unique benefit-led titles for CCNI; AI-filter funnel prompts (→ regex here) | Primary 2026 articles |
| David Quaid (Primary Position) | CCNI = authority, not quality (U-A authority check); striking distance 8–17; page-level deltas; titles past page 1 rarely lift CTR; indexing APIs are a red flag | Video chapters and X; Reddit unreachable |
| Chris Long (Nectiv) | 10+ word conversational regex → theme mining (PF4); `site:` fan-out queries (PF5); AI Overview gap check | Primary Nectiv posts |
| Neil Patel | High-impression/low-CTR refresh: Pages by CTR ascending → Queries → retarget (PF2) | Snippet-level |
| Google (Mueller, Splitt, Illyes, Waisberg) | Pages report as trend lines; no index ratio; CCNI/DCNI sometimes quality; Mark as fixed samples; CDN detection; Request indexing only for urgent content; the drop-diagnosis sequence; faceted navigation; caching | Official transcripts and docs |
| Glenn Gabe | Delta reports (PF12); redirects report the destination's status; soft-404 analysis; LLM classification of AI-Mode queries | Primary posts |
| Barry Adams | Crawl Stats thresholds (CR1, CR5, CR6); disallowed budget evaporates | Primary |
| Mark Williams-Cook | Intent regex library (PF8); filters redact data; regex over AI filters | Primary |
| Onely (Góralewicz), Ahrefs (Stox), Brodie Clark, Kevin Indig, Suganthan, Aperghis, Ulku, Hawkins | CCNI fix steps; anonymised and AI Overview studies; AIO counting; data incompleteness; MCP and Gen-AI tooling; API archives; page–query alignment; ranking volatility | Mixed |

## Defaults where experts disagree

| Topic | Default |
|---|---|
| Cause of CCNI | Run both the quality and the authority checks. Rewrite if the page had impressions; authority + merge if it didn't; site-level pruning when the share is large |
| Request indexing | Once per materially changed, high-value URL, with approval; never in bulk |
| Impressions as a signal | Direction within clean windows; clicks for any before/after that crosses Sep 2025 or May 2025–Apr 2026 |
| Average position | Impression-weighted per query/page; never site-wide averages |
| AI filters vs regex | Regex (deterministic, and the AI filter has no API) |
| Striking band | A parameter: ≤20 by default (the user's rule), ≤30 wide, 8–17 tight |
| Title/CTR work | Only at position ≤10; below that, content and authority |
| Pruning | For quality consolidation, never "to free quota" |
| 404 vs 410 | Either; don't convert for crawl reasons |
| `_rsc` | Header noindex + `prefetch={false}` first; robots.txt last; never block `_next/static` |
| Cannibalisation | Flag with the PF9 thresholds; act only on money queries or flip-flopping |
| Discovery share | Context-dependent; >10% matters for established publishers |
