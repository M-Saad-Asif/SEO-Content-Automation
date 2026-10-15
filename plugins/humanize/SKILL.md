---
name: humanize
description: Make the page read as written by a person, using what the University of Maryland / Google DeepMind research found separates human writing from AI writing. Prevention lives in the writer card; HU01-HU08 in lint catch what slips through.
---
# humanize: human ideas, not human-sounding words

## What the research found

Two studies from the University of Maryland with Google DeepMind looked past word choice and asked what AI text
*says* and *how it is built*.

- **StoryScope** (Russell et al., 2026, arXiv 2604.03136) compared human and AI stories on hundreds of narrative
  features. AI states its theme or lesson outright (77% of AI stories against 52% of human ones), alludes vaguely
  instead of naming real works, places and brands (72% against 50%; named references 24% against 47%), and keeps a
  tidy, linear, uniform structure. Rewriting the surface style barely changed detection (macro-F1 95.5 to 93.9):
  the signal is in the ideas and the structure, not in word swaps.
- **IdeaLens** (Rajendhran et al., 2026, arXiv 2610.06778, with Simon Fraser University) broke texts into their
  ideas. Human ideas carry sources a reader can look up, details that pin down one case and could change the
  conclusion, numbers with context, the limits of a claim (when it applies and when it does not), costs, open
  problems and mixed results. AI ideas carry details that could apply to any subject (the commonest AI feature,
  21.9% of AI ideas), made-up examples used as proof, sweeping claims from one case, every benefit at once,
  perfect or guaranteed solutions, forecasts that cannot be wrong, and reasons that restate the claim. Writing
  from a human outline cut detection to 6.8%: who decides the ideas decides how human the page reads.

## How the pipeline uses it

| Finding | Where it is applied | Check |
|---|---|---|
| A human outline is the strongest lever | `plan.py` builds the outline from the ranking pages' own headings, questions and majority facts, so the ideas come from people | plan check: every planned heading present |
| Details that could sit on any page | write brief gives each section its facts as notes (figures, qualifiers, entities) | HU01-could-be-any-page: block when over 12% of sentences have no figure, no name and none of the topic's entities |
| Perfect, all-needs or hassle-free solutions | card: say what it does, for whom, and what it costs or doesn't do | HU02-perfect-solution: block |
| Forecasts that cannot be wrong | card: state the condition | HU03-unconditional-forecast: block |
| Vague allusion instead of a named source | facts carry their source; link it | HU04-vague-authority ("experts say", "studies show" without a named, linked source): block |
| Made-up example as proof | worked examples from the brief's figures only | HU05-made-up-example ("Imagine…", "Meet Sarah, a…"): block |
| States the lesson outright | no closing moral; the facts make the point | HU06-stated-lesson ("The key takeaway…", "Ultimately,…"): block |
| A reason that restates the claim | give the reason the reader doesn't have | HU07-circular-reason: warn |
| No limits, costs or exceptions | card: say who it doesn't suit, when it doesn't apply, what it costs | HU08-no-limits: block on pages of 700+ words with no limit stated |
| Tidy, uniform structure | vary section shapes (paragraph, table, steps); sections follow the ranking pages' order, not a template | RULES section 5 |
| Surface style edits don't humanize | no synonym-swap fix rounds; fixes change the idea (add the figure, the name, the condition) or cut the sentence | every HU fix line says so |

## For the writer (already in the rules card)

Name the source, the place, the product and the figure. Give the case a detail decides, the condition under which
it holds, and the limit or cost. Never invent an example, a customer, a statistic or an authority. Never close a
section on its lesson. These are the same instructions Koray Tuğberk Gübür's rules give (certainty with a condition,
numeric values, examples after a plural noun, specific entities), so the two never pull against each other.

## Speed

Prevention costs nothing: the card states the rules before drafting, so the checks rarely fire. Each HU finding
names its sentence and one fix, and the mechanical rewrites (fluff, "if" first) are done by `autofix.py` before the
check, so humanization never adds a fix round on its own.
