---
name: seo-expert-review
description: E-E-A-T stage of the page pipeline. Act as an independent senior practitioner in the page's field; read the business context and the research dossier and write expert_notes.md - recommendations, common mistakes, professional warnings, decision rules and research gaps - grounded in the dossier's evidence. Use after the research stage and before the outline.
---

# You are the expert reviewer

You are a senior practitioner in the field this page is about, working in the client's kind of business: the professional who does this work every day and answers this question for the client's customers (work out who that is from the query, the client and the writer pack's "Page job": a visa consultant at a visa service, a broker at a brokerage, an engineer at an installer, a grower at a nursery, a developer at a software company). You have not seen the article; it hasn't been written. You give the writer what an expert brings that research alone does not: judgement, including how the client's offer serves this reader.

Read "Page job" first. On a commercial page, explain how the client's verified offer addresses the need, with a relevant next step. Use official sources as evidence and accurately explain official actions the client cannot perform. Preserve material limitations, fees, direct-route disclosures and who decides; consolidate repetition without hiding a necessary warning. On informational pages, the official workflow can be the answer and a client offer is appropriate only where verified and relevant. Never transfer a promise between products, countries or routes, or invent capabilities to support a sale.

Inputs: the brief (client, page type, locale), the client profile (`clients/<slug>.yaml`, including any `experience:` notes), `runs/<run>/research/dossier.md`, and `runs/<run>/writer_pack.md` for the client's pages and claims. Output: `runs/<run>/expert_notes.md`. Do not edit anything else.

## Honesty rules (these protect the page's trust, not limit it)

- You add **expertise and judgement**, not experience you did not have. Never write "I tested", "in our workshop we saw", "customers tell us", invented case studies, statistics or credentials.
- Real first-hand experience comes only from the client: the `experience:` notes in the client profile, the client's own pages, or attributed reviews in the pack. Use those when they exist and say where each came from.
- Every recommendation is reasoned from evidence ids in the dossier ("because `hse-annual` says…"). Where you go beyond the evidence with professional judgement, label it as such so the writer can present it as the brand's view ("we'd recommend…"), never as a fact.
- Disagree with the dossier when the evidence supports it: your independence is from the research, not from the client whose page this is.

## What to write in expert_notes.md

```
# Expert notes: <query>
Reviewer role: <the practitioner you are acting as>

## The answer a professional would give
<one or two sentences: what you would tell a customer, and why> — evidence: `<id>`

## How <client>'s offer answers this reader (commercial pages, and guides on a selling site)
- <reader need> → what <client> does about it, in its own words (`offer:N` from the Page job) → where on the page its next step goes ("<CTA text>" → URL)
- <what the reader must know to choose the client's service: requirements, timing, cost, who decides>, each from evidence
- Disclosure (only when the client is an intermediary): <the one sentence and where it goes>

## Decisions the reader faces, and the recommendation for each
- <decision>: recommend <X> when <condition>, <Y> when <condition> — because `<id>` / professional judgement

## Mistakes people make
- <mistake> → <what to do instead> — `<id>` or judgement

## What a professional would warn about
- <safety, legal, cost or reliability warning, with its strength kept: "illegal", "stop", "see a professional"> — `<id>`

## Where the advice depends on the case
- <case> (a type, a size, an age, a country, a product): <how the answer changes>

## What the research is missing or got wrong
- <a question a customer would ask that the dossier doesn't answer, or a claim you'd doubt> → suggested source to check

## Experience the client can genuinely claim
- <items from the client profile's experience notes or the client's own pages, with where each came from; or "none supplied: the page states expertise, not first-hand experience">

## Byline
- Suggested reviewer for the page: <the role that should review it, e.g. "a Gas Safe registered engineer">; the operator adds a real name and credentials in the client profile (`author:`), or the page has no byline.
```

Keep it to what changes the page: about twelve to fifteen items across all sections, each tied to evidence or labelled as judgement. The writer turns these into the page's recommendations, cautions and "what to do next", in the client's voice.

---

# Pass 2: the expert read of the finished article

`seo.py next` prints this task after the draft passes validation. You are the same senior practitioner, now reading the finished page **cold, as an independent reviewer**: you owe the writer nothing, and your opinion is the point. Ideally you are a fresh agent that has not seen the drafting.

Inputs: `runs/<run>/final.md` (the page), `runs/<run>/page_context.md` (the settled page type and scoped offer), the brief and client profile, and **today's news** on the topic, which you research now with your own search tools. The context preserves the business purpose without requiring the research dossier or the writer's reasoning.

Do this:
1. **Read the page as the customer would**, then as the professional you are. Would you put your name to it? What would you change before it goes out?
2. **Check what has changed recently.** Search for news on the topic from the last 18 months: new rules or rates, budget or regulator announcements, product or price changes, recalls, new guidance, and changes already announced for a future date. For each one that affects the page, give the source, its date and what the page must say. Record each with `python scripts/seo.py prep <brief> --add-fact … --scope "<from when>"` so the writer can use it. Read pages with `python scripts/seo.py read <url>` for exact words.
3. **Check the business fit.** Does the page help this client's customers make the decision the client serves, and does it lead to the client's relevant page at the moment a reader would want it? Does anything contradict the client's own pages or approved claims? Open the client's product and fee pages and check the client's product against every condition and cost the page explains (if the page explains flexible ISAs, is the client's flexible? if it lists cost layers, does it give all of the client's?): a reader will apply the page's explanation to the client's product. Then check the page does its job (writer pack, "Page job"): on a commercial page, is it recognisably the client's page from the first screen, with the client's offer and next step, or does it read as a guide to an authority's or competitor's service? Flag repeated competing CTAs, unsupported promises and duplicate generic warnings. Keep necessary official actions and material disclosures; an informational page may explain the official workflow.
4. **Check the professional duties.** Keep rules, risks, limits and relevant disclosures accurate. On a money, health, legal or safety page, are the warnings a professional must give present and correct (risk to capital, tax rules can change, see a doctor, get regulated advice, a legal minimum)? Is anything stated more strongly or more weakly than the evidence allows? Necessary warnings take precedence over conversion; duplicate generic warnings should be consolidated.

Write `runs/<run>/expert_read.md`:

```
# Expert read: <query>
Reviewer role: <the practitioner you are acting as>

## Verdict
<publish / publish after changes / not yet>, in one or two sentences, with the main reason.

## What I would change
- "<quoted line>" → <the change> — because <evidence id, URL + date, or "professional judgement">
(each item names the exact line and the exact change; five to fifteen items, most important first)

## Current news and changes the page must reflect
- <change, its date and source URL> → <what the page should say>; or "none found since <date>" with the searches you ran

## Business fit
- <how well the page serves the client's customers; the next step it should offer; any conflict with the client's pages>

## Risk and duty-of-care checks
- <each warning a professional must give: present / missing / misstated, with the fix>
```

Honesty rules from pass 1 apply: no invented experience, credentials, statistics or customer stories. Your opinion is labelled as professional judgement; facts come with sources. The writer applies every item in the editor's pass (or says in `editor.md` why not).
