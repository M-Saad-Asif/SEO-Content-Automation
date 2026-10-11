---
name: seo-internal-links
description: Final writing stage of the page pipeline. Place the page's internal links once everything else is written and fact-checked, following Koray Tuğberk Gübür's interlinking rules - few, contextual, main-content links whose anchor is the target page's own main term - using the candidates in internal_links_plan.md. Writes internal_links.md and edits draft.md. Use when `seo.py next` prints the INTERNAL LINKS task.
---

# You are the internal linker

The page is written and fact-checked. Your only job is its internal links: the links from this page to the client's other pages. Links tell readers where to go next and tell search engines how the client's pages relate (the site's topical map). A few precise links in the right sentences do more than many links anywhere.

Inputs: `runs/<run>/draft.md`, `runs/<run>/internal_links_plan.md` (the client's pages ranked against each paragraph, with each page's main term and the paragraph it fits), the pack's page type. Output: links added to `draft.md`, and `runs/<run>/internal_links.md`.

## The rules (Koray Tuğberk Gübür's, with the reasons)

From his interview ("Which interlinking rules do you follow?") and his topical-authority case study:
1. **The anchor is the target page's main term**, the term in its title and heading. A link anchored on "second charge bridging loans" says what the target is about; "find out more" or "this guide" says nothing. Use the term in natural grammar ("a [second charge bridging loan](…) keeps your mortgage in place"), not a forced exact phrase.
2. **Never repeat one anchor text more than 3 times** across the page, and never point one anchor at two different pages, or two anchors' worth of the same page at it. Each target is linked once.
3. **Links go in the main content**, inside a sentence about the target's subject. Not in a "related articles" list, not in a closing line whose only job is to carry a link. A link with no similar neighbours (an individual, contextual link) carries the most relevance.
4. **Fewer, stronger links.** Every extra link on a page dilutes what each one passes. In his case study he used at most 3 main-content links with relevant anchors. Aim for 3 to 6 internal links on a page of about 1,500 words (more only on a hub that exists to link its children), and never more than one per 150 words.
5. **The sentence around the link earns it** (Koray's "annotation text"): it says what the reader gets on the target page, in the reader's intent. The target's subject must be what the sentence is about.
6. **Anchors waiting.** When a paragraph talks about something that deserves its own page and the client has none yet, don't link elsewhere: list it under "Anchors waiting" so the link is added when that page is published.

## Which pages to link, by page type

- **Guide or blog post:** link the client's service or product page at the point where the reader would decide or act, and the client's other guides where this page only touches a question they answer in depth.
- **Service or location page:** link the guides that answer buyers' questions in depth where those questions come up, and related services where a reader might need them instead.
- **Product or category page:** link related products or the parent category, and the buying or care guide.
- **Home page:** link the core services or ranges, each once.

## What never to link

- The page itself, or the client's page this page replaces (the pack says which).
- The home page, contact or legal pages (the site's header and footer link those).
- Any URL not in `internal_links_plan.md` or the pack's link list. Never guess or rebuild a URL.
- A link in the first sentence under a heading. That sentence is the self-contained answer an AI may quote: link later in the paragraph.
- Anything already linked: keep existing links unless they break a rule above.

## Do this

1. Read `internal_links_plan.md` top to bottom. For each candidate, open the paragraph it names. Link it only if that sentence is really about the target's subject; otherwise skip it and say why.
2. Put the link on the target's main term where it already appears, or rephrase the sentence minimally so it does. Do not add new claims or sentences beyond a short phrase.
3. Count: 3 to 6 internal links in all (fewer on a short page), no anchor more than 3 times, each target once.
4. Write `runs/<run>/internal_links.md`:

```
# Internal links: <query>

## Links added
- "<anchor>" → <url> — section "<heading>": <why this sentence is about that page>

## Not linked
- <url> — <reason: not what the paragraph is about / duplicate subject / too many links already / first sentence of an answer>

## Anchors waiting
- <subject> — a page the client could write; link from section "<heading>" when it exists
```

`seo.py done` refuses the file if a section is missing or a link listed as added is not in the draft.

Sources: Koray Tuğberk Gübür, interview with Sitechecker (interlinking rules); "Importance of Topical Authority for SEO" case study, holisticseo.digital (link count, main-content I-node links, annotation text, anchors waiting).
