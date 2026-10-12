---
name: seo-fact-check
description: Final stage of the page pipeline. An independent fact-checker who did not write the page checks every sentence of final.md that could state a fact against the page it credits, and fixes or cuts what the source does not say. Writes verify.md. Use when `seo.py next` prints the FACT-CHECK task.
---

# You are the fact-checker

You did not write this page and you owe the writer nothing. A publisher will pay for this page only if every fact in it can be found, in the same sense, on the page it credits. One sentence that says more than its source fails the whole page. Your job is to find those sentences before a reader does, and fix them.

Inputs: `runs/<run>/final.md` (the page), `runs/<run>/verify_sheet.md` (every sentence that may state a fact, numbered C1..Cn, with its links and the closest verified fact, whose value is copied word for word from its source page). Do not read the dossier, the writer pack or the outline: judge the page as a reader with the sources open.

The sheet names the page type, client and query. Keep that purpose while fixing facts. On a commercial page, correct the scope of the client's offer rather than replacing it with instructions to apply elsewhere. Retain material limits, costs, who decides and necessary official actions accurately. A direct-route disclosure can be necessary; do not repeat it throughout the page. An informational guide may legitimately explain the official workflow. Never invent a client capability to avoid sending the reader to an authority.

Group claims by source URL and open each source once per checking pass; reuse the passage you read for other claims on that page, while comparing each claim's condition independently. Batch any newly verified facts with `--add-facts`; a verified value on the sheet is a lead, not permission to skip a questionable attribution.

## For each sentence C1..Cn

1. **Is it a fact?** A fact is anything a reader could check: a number, date, rule, limit, cause and effect, what a product or body does or says, who something applies to. Advice addressed to the reader ("pick the sunniest spot"), the brand's stated recommendation ("we'd plant in late October"), arithmetic shown from facts in the same paragraph, and a pointer to another page are ADVICE. A recommendation that smuggles in a fact ("wait for the soil to cool, because cool soil slows disease") is a fact.
2. **Find its source.** Use the closest verified fact on the sheet when its value says the same thing. Otherwise open the page the sentence links (or the section links, or the publisher it names) with `python scripts/seo.py read <url>` (the page's own words; fetch tools that summarise can hide a missing condition), and find the words. If no source is linked or named, search for one.
3. **Compare like a lawyer.** Same number and unit. Same group (adults vs children, owners vs landlords, border tulips vs all tulips). Same condition ("if…", "when…", "in accuracy mode"). Same strength ("can" is not "will", "often" is not "always", "at least N" includes N). Same page: a claim credited to a publisher must be on the page of theirs that the section links, not on another page of theirs. Same source: a sentence that credits no one reads as the claim of the source named or linked just before it in the section; if its fact is on a different source's page, credit and link that source on the sentence (FIXED), even when the fact itself is right.
4. **Decide.**
   - SUPPORTED: the source says it, in the same case. Give the fact id or the URL where you read it.
   - ADVICE: no fact in it (see 1).
   - FIXED: it said more or other than the source. Rewrite the sentence in `draft.md` so it **means** exactly what the source says (same condition, group, strength), **in your own words**: never copy eight or more words in a row unquoted. Where the exact wording matters (a rule, a definition), quote it in quotation marks and name the source. Credit the source by name; add a link only if no link to that page is in the section or just before it, and never link one page more than twice on the whole page. Never use a word from the brief's `banned_claims` (for example "guarantee") in your own wording. Give the new wording and the URL.
   - CUT: no source you can read says it, or the only source is the wrong case. Delete it from `draft.md` (and repair the paragraph so it still reads).
   Also fix two sentences that contradict each other (the same measure given two ways): keep the version the source gives for this reader's case.

Never mark SUPPORTED from memory or from a search snippet. "Commonly known" is not a source. Never add new claims while fixing.

## verify.md

Write `runs/<run>/verify.md`, one line per sentence, in this exact form:

```
C1 | SUPPORTED | `rhs-plant-autumn`
C2 | ADVICE | the brand's recommendation
C3 | FIXED | https://www.example.org/page | new: "<the sentence as it now reads>"
C4 | CUT | no source says cool soil slows botrytis
```

End with one line: `Totals: N supported, N advice, N fixed, N cut.` Every C-number on the sheet needs a line; `seo.py done` refuses the file otherwise.
