"""The page's job: what this page must do for the business, decided before a word is written.

Every page answers its searcher. A commercial page (service, product, category, location, home, company) also
sells the client's offer: the reader should leave knowing what the client does about their problem and how to
start. Official or third-party sources establish rules, fees and times; the page type determines whether an
official action or the client's verified service is the reader's main next step.
A client that acts for the reader before someone else who decides (an intermediary: visa or licence filing, a
broker, a reseller) owes the reader one honest disclosure, placed where they choose the service, never a page of
directions elsewhere or warnings against itself.

Used by the writer pack (the "Page job" section the writer reads first), the expert's and writer's tasks, and lint
(P-rules: brand late, no client next step, steering readers elsewhere, warning readers off the client).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from . import common as C
from .pagetype import CTA_WORDS, CART

COMMERCIAL = {"service", "product", "category", "location", "home", "company"}
STRUCTURE = {
    "service": [
        "Answer the searcher's question in the first two or three sentences, then say what {client} does about it, "
        "with its main next step (first screen).",
        "How it works with {client}: the steps, what the reader provides, what {client} does, what happens next.",
        "Who it is for and what is needed (eligibility, documents, conditions), from verified facts.",
        "Time and cost: the authority's or market's figures as cited facts; {client}'s own figures as {client}'s.",
        "The rules that matter, briefly, each cited where it is used (not a guide to doing it elsewhere).",
        "Why {client}: only what its own pages say (the offer lines below), never invented proof.",
        "Relevant questions searchers ask (article_context.json), answered inside the sections or as FAQ H3s; use a main H2 only when the question warrants it.",
        "Close with {client}'s next step.",
    ],
    "location": [
        "The service and the place in the first sentences, with {client}'s next step.",
        "What {client} does there, areas covered, local specifics (rules, times, prices) from verified facts.",
        "How it works, who it is for, questions searchers ask, and the next step to close.",
    ],
    "product": [
        "What it is and who it suits, in the first two sentences, with the buy or choose step.",
        "Key specifications from the product data only; fit and use cases; how it compares within the range.",
        "Delivery, returns, care or warranty facts; questions searchers ask; the buy step to close.",
    ],
    "category": [
        "What the range covers and how to choose (the criteria that matter), with a way into the range.",
        "Highlights from the product data only (names, specifications), linked to their pages.",
        "Questions searchers ask; the browse or filter step to close.",
    ],
    "home": [
        "Who {client} is and what it offers, in the first sentences, with the main next step.",
        "Its main services or ranges, each linked to its page; proof only from its own pages; the next step to close.",
    ],
    "company": [
        "Who {client} is, what it does and for whom; credentials only from verified facts; how to contact it.",
    ],
}


def offer(sheet: dict) -> dict:
    return ((sheet.get("client") or {}).get("offer")) or {}


def selling(sheet: dict) -> bool:
    o = offer(sheet)
    return bool(o.get("offers") or o.get("ctas"))


def brand_terms(sheet: dict) -> list[str]:
    b = sheet.get("brief") or {}
    names = [b.get("client") or ""] + list(b.get("client_aliases") or []) + list(offer(sheet).get("brands") or [])
    return sorted({n for n in names if n and len(n) > 2}, key=len, reverse=True)


def is_client_url(url: str, sheet: dict) -> bool:
    b = sheet.get("brief") or {}
    base = b.get("page_url") or "https://" + (b.get("domain") or "") + "/"
    candidate = urljoin(base, url)
    domain = b.get("domain") or C.host(base)
    host = C.host(domain if "://" in domain else "https://" + domain)
    return bool(host) and C.host(candidate) == host


def next_steps(blocks: list[dict], sheet: dict) -> list[tuple[dict, str]]:
    """A useful action or known conversion target, not any internal blog link."""
    b = sheet.get("brief") or {}
    base = b.get("page_url") or "https://" + (b.get("domain") or "") + "/"
    targets = {C.clean_url(urljoin(base, c["url"])).rstrip("/") for c in offer(sheet).get("ctas", [])}
    targets |= {C.clean_url(urljoin(base, u)).rstrip("/") for u in b.get("conversion_targets") or []}
    out = []
    for block in blocks:
        for label, url in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", block.get("raw", "")):
            resolved = C.clean_url(urljoin(base, url)).rstrip("/")
            own_action = is_client_url(url, sheet) and (CTA_WORDS.search(label) or CART.search(label))
            if resolved in targets or own_action:
                out.append((block, resolved))
    return out


def lines(sheet: dict) -> list[str]:
    """The writer pack's "Page job" section."""
    b = sheet.get("brief") or {}
    pt = b.get("page_type") or "guide"
    client = b.get("client") or "the client"
    o = offer(sheet)
    commercial = pt in COMMERCIAL
    L = ["", "## Page job (read this first: it decides what the page is for and how it is built)"]
    if commercial:
        L.append(f"- This is a **{pt} page** of {client}. It answers \"{b.get('target_query')}\" AND makes {client}'s "
                 f"offer: the reader should leave knowing what {client} does about their need and how to start.")
    elif selling(sheet):
        L.append(f"- This is a **{pt}** on {client}'s site, which sells a service or product. Answer the question "
                 f"fully and accurately; where the reader's task meets {client}'s offer, a brief relevant passage may explain how "
                 f"{client} helps, with its next step. No hard sell elsewhere.")
    else:
        L.append(f"- This is a **{pt}**: answer the question fully. No relevant client offer has been verified; "
                 "do not infer that the client sells nothing, or invent a service to fill the gap.")
    if o.get("offers"):
        L.append(f"- What {client} offers, in its own words (verified client facts `offer:N`; use them in {client}'s voice, "
                 "never stretch them):")
        L += [f"  - `offer:{i}` \"{x['text'][:220]}\" — {x['url']} — {x.get('scope') or 'only the product, market and conditions stated in this passage'}"
              for i, x in enumerate(o["offers"][:8], 1)]
    if o.get("ctas"):
        placement = ("link the most specific one near the top and again at the end" if commercial else
                     "use only where relevant to the reader's task; no compulsory opening or closing sales pitch")
        L.append(f"- {client}'s next steps (its own buttons; {placement}):")
        L += [f"  - \"{c['text']}\" → {c['url']}" for c in o["ctas"][:5]]
    if commercial:
        L += ["- Official and third-party sources are the evidence for rules, fees and times: cite each where its fact "
              "is used. Build the page around the client's verified offer and next step. Include necessary official "
              "actions (identity checks, viewing granted status, statutory payments) accurately; never imply the client can perform them without evidence.",
              f"- Explain {client}'s value from verified capabilities. Avoid repeated directions to buy or apply elsewhere. "
              "Preserve material limitations, fees, optional-service disclosures and who makes the decision; never hide them to protect a sale.",
              ]
        if o.get("role") == "intermediary":
            L.append(f"- {client} acts for the reader before an authority or provider that decides. Say so once, plainly, "
                     f"where the reader chooses the service: that {client} is an independent service, who makes the "
                     "decision, and the direct route when verified. Keep the disclosure in one place, unless distinct risks require more detail.")
    if not commercial:
        L.append("- On an informational, support, hub or comparison page, official instructions may be the main answer. "
                 "A selling site alone does not justify an opening sales pitch or a compulsory brand section. "
                 "Mention the client's offer only where verified and relevant to this task.")
    st = STRUCTURE.get(pt)
    if st:
        L.append(f"- Structure for a {pt} page (adapt the headings to the searcher's words and article_context.json):")
        L += [f"  {i}. {x.format(client=client)}" for i, x in enumerate(st, 1)]
    return L


# ---------------------------------------------------------------- checks used by lint

STEER = re.compile(r"(?i)\b(apply|pay|book|submit|order|buy|renew|register)\b")


def external_names(domain: str) -> list[str]:
    """How a page names another site: "GOV.UK" for gov.uk, "USCIS" for uscis.gov, "Which?" for which.co.uk."""
    d = (domain or "").lower().removeprefix("www.")
    parts = d.split(".")
    names = [d]
    if parts and len(parts[0]) >= 4 and parts[0] not in ("blog", "help", "support", "docs"):
        names.append(parts[0])
    return names
ANTI = re.compile(r"(?i)\b(ours|us) included\b|\bincluding (ours|us)\b|\byou (don't|do not) need (a|an|our|any) "
                  r"(agent|agency|service|third[- ]party|intermediary|broker)\b")
