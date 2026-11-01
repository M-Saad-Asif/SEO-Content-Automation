# Actions that always need the user's explicit yes

The agent proposes: what, why, the evidence, the test, the diff. Then it waits. One approval covers one action.

| Action | Why risky | Before proposing |
|---|---|---|
| Any robots.txt change | It can block rendering resources, hide a noindex, or leave "Indexed, though blocked". A `Googlebot` group replaces `*`. Disallowed budget evaporates | Cluster the examples → needed for rendering = no **and** earning impressions = no → `gsc robots --rule … --test …` against the important URLs → show the diff |
| Removals request | It can hide every protocol/host variant, and it is temporary | Emergencies only (legal, PII, hack), with a permanent fix |
| Sitemap submit/delete | Wrong URLs speed up discovery of junk; deleting loses the segmentation | Validate the URL mix (canonical, 200, indexable) and show the list |
| Request indexing / Indexing API | Unpublished quota; the Indexing API is officially for jobs and livestreams only | One materially changed, high-value URL; never in bulk |
| Validate fix | A fix that isn't live wastes a validation cycle | Live-test samples first; never for CCNI/DCNI |
| Site add/delete, user changes, verification tokens | Loss of access | The owner confirms |
| Disavow, reconsideration, security review | Irreversible signals, wasted reviews | Documented evidence |
| Generative AI opt-out | Removes the site from AI Overviews, AI Mode and Discover AI | A business decision only |
| Change of address, mass 301s or merges, noindex of sections, 503 load-shedding | Large traffic effects | Benchmark first; roll out in stages |
| MCP write scope, or a server's remote mode | Broad write access; open endpoints | Per session; an auth token on any remote endpoint |
