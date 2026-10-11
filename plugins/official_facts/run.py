"""Official facts: verbatim, citable sentences from the authorities for this topic."""
import re

from seolib import common as C
from seolib import serper
from seolib.domains import domain, kind
from seolib.lint import sentences
from seolib.nlp import places, tokens

# Where a country's government publishes, when the SERP itself doesn't show us (world data, not niche data).
# A country's public authorities (government plus its national health service), searched when the SERP itself
# doesn't show them. World data, not niche data: every topic in that country uses the same list.
GOV_SITES = {"gb": ["gov.uk", "nhs.uk"], "us": ["gov"], "au": ["gov.au"], "ca": ["canada.ca", "gc.ca"],
             "in": ["gov.in", "nic.in"], "ae": ["gov.ae", "u.ae"], "ie": ["gov.ie", "hse.ie"], "nz": ["govt.nz"],
             "pk": ["gov.pk"], "sa": ["gov.sa"], "fr": ["gouv.fr"], "jp": ["go.jp"], "th": ["go.th"],
             "eu": ["europa.eu"], "sg": ["gov.sg"], "za": ["gov.za"], "ng": ["gov.ng"], "ph": ["gov.ph"],
             "de": ["bund.de"], "es": ["gob.es"], "it": ["gov.it"], "nl": ["overheid.nl", "rijksoverheid.nl"]}
GOV_SITE = {k: v[0] for k, v in GOV_SITES.items()}
# The regulators and public bodies that set the rules in each YMYL sector, per country (world data, not niche data):
# for a money question the FCA is the authority, not a council report on gov.uk.
SECTOR_SITES = {
    "gb": {"money": ["fca.org.uk", "moneyhelper.org.uk", "fscs.org.uk", "bankofengland.co.uk", "gov.uk"],
           "health": ["nhs.uk", "nice.org.uk", "gov.uk"],
           "legal": ["legislation.gov.uk", "gov.uk", "citizensadvice.org.uk"],
           "safety": ["hse.gov.uk", "gov.uk", "gassaferegister.co.uk"]},
    "us": {"money": ["consumerfinance.gov", "sec.gov", "irs.gov", "fdic.gov"], "health": ["cdc.gov", "nih.gov", "fda.gov"],
           "legal": ["law.cornell.edu", "usa.gov"], "safety": ["osha.gov", "cpsc.gov"]},
    "ie": {"money": ["centralbank.ie", "ccpc.ie", "revenue.ie"], "health": ["hse.ie"], "legal": ["irishstatutebook.ie"]},
    "au": {"money": ["moneysmart.gov.au", "asic.gov.au", "ato.gov.au"], "health": ["health.gov.au"]},
    "ca": {"money": ["canada.ca", "fcac-acfc.gc.ca"], "health": ["canada.ca"]},
}
SECTOR_WORDS = {
    "money": r"\b(invest\w*|isas?|pensions?|retire\w*|tax(es|ed)?|mortgages?|loans?|lend\w*|credit|debt|insurance|"
             r"savings?|bank\w*|stocks?|shares|funds?|crypto\w*|bridging|finance|interest rates?)\b",
    "health": r"\b(symptoms?|diseases?|medic\w*|dosage|dose|pregnan\w*|vaccin\w*|treatment|diagnos\w*|health|nutrition|"
              r"protein|vitamin|diet)\b",
    "legal": r"\b(legal\w*|law|laws|lawyer|solicitor|visas?|immigration|tenan\w*|landlord|contract|divorce|regulat\w*)\b",
    "safety": r"\b(safety|carbon monoxide|gas|boiler|electrical|fire|tyres?|tread)\b",
}
# Rule-shaped language in any field: obligations, limits, costs, durations, outcomes.
RULE = re.compile(r"\b(must|need to|needs to|cannot|can't|can only|only|at least|up to|within|no more than|maximum|"
                  r"minimum|costs?|fee|free|valid for|lasts?|takes?|allowed|not allowed|required|working (day|week)s?|"
                  r"does not|do not|needs?|guarantee|refund|including|each|rejected|refused|delayed|deadline|"
                  r"before|after|should not|must not|recommended|advised|illegal|legal|penalty|fine)\b", re.I)
NUM = re.compile(r"(£|\$|€|\b\d[\d,]*(\.\d+)?\s?(%|cm|mm|m\b|km|kg|g\b|mg|ml|l\b|litres?|liters?|days?|weeks?|months?|"
                 r"years?|hours?|minutes?|working days|pence|p\b|°c|degrees)|\b(one|two|three) litres?\b)")
PHONE = re.compile(r"\+?\d[\d\s()-]{6,}\d")
CHANGELOG = re.compile(r"^(added|updated|removed|changed|amended|corrected|first published|last updated|page updated|"
                       r"published|this (page|guidance) (was|has been)|\d{1,2} [A-Z][a-z]+ \d{4}\b)|"
                       r"\b(added|removed|updated|amended|withdrawn)\.?$|\bhave been updated to\b", re.I)
HISTORY = re.compile(r"^(updates to this page|document history|change history|page history|full page history|"
                     r"print this page|related content|explore the topic)\b", re.I)
OFFICIAL = ("government", "international")  # universities and colleges are sources, not authorities
COMMENTS = re.compile(r"^(\d+\s+)?(comments?|responses?|replies|leave a (reply|comment)|join the (conversation|discussion)|"
                      r"sharing and comments|what (you|people) said|discussion)\b", re.I)
PROMO = re.compile(r"(we use (essential |optional |analytics )?cookies|cookie (policy|settings|preferences|notice)|"
                   r"accept (all )?cookies|your privacy choices|"
                   r"apply now|enrol|our (program|programme|course|degree)s?|ideal for (working )?adults|sign up|"
                   r"subscribe|request (more )?info|learn more|contact (us|an advisor)|call (us|now)|\bsave\b.*%|% off)", re.I)
ANAPHOR = re.compile(r"^(this|that|these|those|it|they|such|you must do this|you do not need to|you don't need to|"
                     r"in this case|if so|otherwise)\b", re.I)
# a condition that refers back from inside the sentence: the rule only holds in the case the previous sentence names
BACKREF = re.compile(r"\b(if|when|where) (this|that|so) (is|was|are|happens|applies)( the case)?\b|\bif so\b|"
                     r"\bin (this|that|which|such) case\b|\bwhen this happens\b|\bin these cases\b", re.I)
# pages written for one group of readers (patients with a condition, staff, professionals, one scheme's members)
AUDIENCE = re.compile(r"\b(patients?|carers?|clinicians?|professionals?|practitioners?|staff|employers?|employees|members|"
                      r"students|children|parents|veterans?|landlords?|tenants?|homeowners?|home owners?|drivers|motorists|"
                      r"residents|applicants|businesses|traders|contractors|installers|engineers|"
                      r"people with [a-z ]{3,30}|information for [a-z ]{3,30})\b", re.I)
BLOGLIKE = re.compile(r"/(blog|blogs|news|press|stories|story|media|insights)/|(^|\.)blog\.", re.I)


def spam_hosts(urls):
    """Hijacked public-sector subdomains (SEO spam on a council booking site) and non-content subdomains."""
    by_host = {}
    for u in urls:
        by_host.setdefault(domain(u), []).append(u.rstrip("/").rsplit("/", 1)[-1].lower())
    bad = set()
    for h, slugs in by_host.items():
        if re.match(r"(bookings?|forms?|events?|shop|store|portal|apply|login|account|careers?|jobs?|recruit\w*|"
                    r"vacanc\w+)\.", h):
            bad.add(h)
        long = [s for s in slugs if len(s) > 60 or len(s.split("-")) > 9]
        if any(re.search(r"/(viewer|proxy|mirror|cache|redirect|out|go)/", u) for u in urls if domain(u) == h):
            bad.add(h)
        if len(long) >= 2:  # many long keyword-stuffed slugs for one query on one host
            bad.add(h)
    return bad


def gov_country(url):
    """Which country's authority a domain is: gov.uk -> gb, nhs.uk -> gb, .gov -> us, gov.in -> in, .int -> intl."""
    d = domain(url)
    if d.endswith(".int") or d.endswith(("un.org", "oecd.org", "worldbank.org", "imf.org")):
        return "intl"
    if d.endswith("europa.eu"):
        return "eu"
    if d.endswith((".gov", ".mil")) or d in ("usa.gov",):
        return "us"
    last = d.rsplit(".", 1)[-1]
    if d.endswith(".ca") or d == "canada.ca":
        return "ca"
    return {"uk": "gb"}.get(last, last if len(last) == 2 else "")


def clean_title(title, url):
    """Drop the site name tacked onto a page title ("Food labels - NHSNHS", "Topic – Site", "Visa | GOV.UK")."""
    parts = [x.strip() for x in re.split(r"\s[–\-|:]\s", title or "") if x.strip()]
    if len(parts) > 1 and len(parts[0].split()) >= 2:
        title = parts[0]
    t = re.sub(r"(\s*-\s*GOV\.UK)+.*$|\s+\|\s+.*$", "", title or "")
    root = domain(url).split(".")[0].lower()
    t = re.sub(r"\s+[-–]\s+([A-Za-z.]{2,30})+$", lambda m: "" if root[:3] in m.group(0).lower().replace(" ", "") else m.group(0), t)
    return re.sub(r"\b(\w{2,})\1\b", r"\1", t).strip()
STOP = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "from", "at", "is", "are", "be",
        "how", "what", "why", "when", "where", "which", "who", "can", "do", "does", "you", "your", "my", "best",
        "online", "check", "it", "this", "that", "will", "i", "s"}


def run(ctx):
    serp = ctx.load("serp_intel")
    if not serp or serp.get("error"):
        return {"error": "no SERP data"}
    syn = ctx.brief.get("synonyms") or {}

    def toks(s):
        return {w for w in tokens(s, syn) if w not in STOP and (len(w) > 2 or w.startswith("geo:"))}
    q = serp["query"]
    # Relevance comes from what people actually ask around this query (PAA, question searches, related), not
    # from a hand-made topic list.
    asked = [q] + serp.get("paa", []) + serp.get("question_autocomplete", [])[:6] + serp.get("related", [])[:6]
    qt = set().union(*(toks(x) for x in asked))
    region = (ctx.brief.get("locale") or "en-GB").partition("-")[2].lower()
    client = ctx.brief["domain"].replace("www.", "")
    proper = {p.lower() for p in ctx.brief.get("proper_nouns") or []}
    cands, searched = [], set()

    def add(link, from_search=False):
        if link and client not in link and link not in cands:
            cands.append(link)
            if from_search:
                searched.add(link)
    for o in serp.get("organic", []):
        d = o["domain"]
        # A brand's own site counts only when the brand is named in the query and is a proper noun in the brief.
        root = d.split(".")[0] if not d.startswith(("help.", "www.", "m.")) else d.split(".")[1]
        brand = root in toks(q) and root in proper
        if o["kind"] in OFFICIAL or brand or (o["kind"] == "help_centre" and root in proper):
            add(o["link"])
    # Google's own answers to the PAA questions often come from the authority that sets the rule
    for a in (serp.get("paa_answers") or {}).values():
        if a.get("link") and kind(a["link"]) in OFFICIAL:
            add(a["link"])
    # Is this a topic an authority rules on? Ask the data: authorities in the SERP or in Google's answers,
    # or a YMYL brief. Then search the authorities that showed up, or the government of the place the query names.
    seen_gov = {domain(u) for u in cands if kind(u) == "government"}
    if not (ctx.brief.get("ymyl") is True or seen_gov) and GOV_SITES.get(region):
        # nothing official ranked, but the reader's own government may still publish on it (safety, legal duties):
        # one search; the relevance gate below keeps only pages that are about the query
        res, cr = serper.batch([("search", f"{q} site:{GOV_SITES[region][0]}")], ctx.brief["locale"])
        ctx.credits += cr
        for r in res.values():
            for o in r.get("organic", [])[:3]:
                if o.get("link"):
                    add(o["link"], True)
    if ctx.brief.get("ymyl") is True or seen_gov:
        sites = sorted(seen_gov)[:2]
        # the sector's own regulators first: a lending question goes to the FCA and MoneyHelper
        for sector, rx in SECTOR_WORDS.items():
            if re.search(rx, q, re.I):
                for s in SECTOR_SITES.get(region, {}).get(sector, []):
                    if s not in sites:
                        sites.append(s)
                break
        for code in [p[4:] for p in sorted(places(q))] + [region]:
            for site in GOV_SITES.get(code, []):
                if not any(s.endswith(site) for s in sites):
                    sites.append(site)
        if sites:
            from datetime import date
            yr = date.today().year
            searches = [("search", f"{x} site:{s}") for s in sites[:4] for x in asked[:2]]
            if ctx.brief.get("ymyl") is True:  # rules change: find this year's and last year's changes too
                searches += [("search", f"{q} changes {yr} OR {yr - 1} site:{s}") for s in sites[:2]]
            res, cr = serper.batch(searches, ctx.brief["locale"])
            ctx.credits += cr
            hits = [o.get("link") for r in res.values() for o in r.get("organic", [])[:6] if o.get("link")]
            spam = spam_hosts(hits)
            for r in res.values():
                kept = 0
                for o in r.get("organic", [])[:6]:
                    u = o.get("link")
                    if u and domain(u) not in spam and kept < 3:
                        add(u, True)
                        kept += 1
    allowed = {region, "intl", {"gb": "gb"}.get(region, region)} | {p[4:] for p in places(q)}
    if region in ("ie", "fr", "de", "es", "it", "nl", "be", "pt", "at", "dk", "se", "fi", "pl", "cz", "gr"):
        allowed.add("eu")
    off_country = [u for u in cands if kind(u) == "government" and gov_country(u) and gov_country(u) not in allowed]
    cands = [u for u in cands if u not in off_country]
    def tier(u):
        """National authority (gov.uk, nhs.uk, a .gov root) first; councils, trusts and other sub-organisations after:
        a council press release is not where a national rule is set."""
        d = domain(u)
        national = any(d == s or d == "www." + s for ss in GOV_SITES.values() for s in ss) or d.count(".") <= 1
        return (0 if national else 1) + (2 if BLOGLIKE.search(u) else 0)
    # a council's committee papers or a trust's board pack (local PDFs) never set a national rule: skip them unread
    cands = [u for u in cands if not (tier(u) >= 1 and (u.lower().split("?")[0].endswith(".pdf") or "/documents/" in u.lower()))]
    cands = sorted(cands, key=tier)[:7]
    known = {p["url"]: p for p in (ctx.load("competitor_scrape") or {}).get("pages", [])}
    need = [u for u in cands if u not in known]
    fetched = C.run_async(C.fetch_many([{"url": u, "kind": "official", "parse": "doc"} for u in need],
                                       ctx.refresh, timeout=8, attempts=1)) if need else {}
    from seolib import spider
    retry = [u for u in need if not (fetched.get(u) or {}).get("blocks") and not u.lower().split("?")[0].endswith(".pdf")]
    if retry and spider.api_key():
        fetched.update({u: r for u, r in spider.scrape_many(retry).items() if r.get("state") == "ok"})
    facts, sources, blocked = [], [], []
    for u in cands:
        page = known.get(u) or fetched.get(u) or {}
        blocks = page.get("blocks") or []
        if not blocks:
            blocked.append({"url": u, "state": page.get("state"), "status": page.get("status")})
            continue
        if "comment-page" in u or "#comment" in u or re.search(r"/(viewer|proxy|mirror|cache)/", u):
            continue
        if page.get("final_url") and domain(page["final_url"]) == domain(u):
            u_final = C.clean_url(page["final_url"].split("#")[0])
        else:
            u_final = u
        title = clean_title(page.get("title") or "", u)
        # A site search returns whatever that authority publishes, on topic or not (a heating tip, a job advert,
        # an eye leaflet for "tread depth"). A searched page must name the query's own subject: most of the
        # query's content words somewhere on the page.
        core = toks(q)
        page_words = set().union(*(toks(x) for _, x in blocks[:400])) | toks(title)
        if u in searched and core and len(core & page_words) < min(2, len(core)):
            blocked.append({"url": u, "state": "off_topic", "status": page.get("status")})
            continue
        head_words = toks(title) | set().union(*(toks(x) for t_, x in blocks[:400] if t_ in ("h1", "h2", "h3")))
        if tier(u) % 2 == 1 and len(core & head_words) < min(2, len(core)):
            # a town's volunteer notice that mentions "paint" and "fence" is not where the rule is set
            blocked.append({"url": u, "state": "off_topic_local", "status": page.get("status")})
            continue
        on_topic = len(toks(title) & qt) >= 1 and kind(u) == "government"
        scored, header, units = [], "", []
        skipping, in_list, heading, in_comments = False, False, "", False
        rows_of = {}  # header -> row label tokens, to find words every row shares ("visa" in a list of visas)
        for i, (t, x) in enumerate(blocks):
            if t in ("h2", "h3", "h4"):
                # page history, "related content" and footer sections are not rules; skip until the next heading.
                # Reader comments are never facts: once they start, the rest of the page is comments.
                in_comments = in_comments or bool(COMMENTS.match(x))
                skipping = bool(HISTORY.match(x))
                heading = x
            if skipping or in_comments:
                continue
            if t != "li":
                in_list = False
            if t == "trh":
                header = x
            elif t == "tr":
                # a table row keeps its column names: "Standard Visitor | 3 weeks (Visa type | Processing time)"
                units.append(("row", f"{x} ({header})" if header else x, header))
                rows_of.setdefault(header, []).append(toks(x.split(" | ")[0]))
            elif t in ("p", "li", "dd") and x.rstrip().endswith(":"):
                # a lead-in is only a fact together with the list it introduces
                items = []
                for t2, x2 in blocks[i + 1:i + 9]:
                    if t2 != "li":
                        break
                    items.append(x2.rstrip(".;"))
                units.append(("list", f"{x} {'; '.join(items)}." if items else "", heading))
                in_list = bool(items)
            elif t in ("p", "li", "dd") and not (t == "li" and in_list):
                units.append(("p", x, heading))
        shared = {}
        for h, rows in rows_of.items():
            cnt = {}
            for r in rows:
                for w in r:
                    cnt[w] = cnt.get(w, 0) + 1
            common = {w for w, c in cnt.items() if len(rows) >= 4 and c > len(rows) / 2}
            # a table whose shared words are the topic itself ("Standard Visitor visa" rows on a visitor-visa page) is
            # wholly relevant; one that only shares a generic word ("visa" in a list of every visa) is judged row by row
            shared[h] = set() if len(common & qt) >= 2 else common
        context, last_sent = {}, ""
        for kind_, x, hdr in units:
            if not x:
                continue
            for s in ([x] if kind_ in ("row", "list") else sentences(x)):
                raw = s
                if kind_ == "p" and (ANAPHOR.match(s) or BACKREF.search(s)) and last_sent:
                    # "You must do this within 30 days." means nothing without the sentence before it
                    s = last_sent + " " + s
                    raw = s  # the next sentence that points back needs this whole chain
                last_sent = raw if kind_ == "p" else last_sent
                n = len(s.split())
                if CHANGELOG.match(s) or "has been updated" in s.lower():  # page history, not rules
                    continue
                if PROMO.search(s) or ",," in s or "..." in s or len(re.findall(r"[a-z]{4,}", s)) < 3:
                    continue  # adverts, fragments and lists of names are not facts
                if kind_ == "p" and (s.rstrip().endswith("?") or not re.search(
                        r"\b(is|are|was|were|be|been|has|have|had|do|does|did|can|could|will|would|should|must|may|might|"
                        r"need|needs|take|takes|cost|costs|\w+s)\b", s.lower())):
                    continue  # a title or heading ("Tool: Customer Relationship Management Systems") states nothing
                if kind_ != "row" and hdr:
                    context[s] = hdr
                rel = len(toks(s) & qt)
                ruleish = RULE.search(s) or NUM.search(s) or PHONE.search(s)
                # keep rules and numbers that touch the topic, and procedure sentences that are squarely on it
                if kind_ == "row":
                    # the row's own label must be on topic: not its column names, not a word every row shares
                    rel = len((toks(s.split(" | ")[0]) - shared.get(hdr, set())) & qt)
                    if rel and (NUM.search(s) or RULE.search(s)):
                        scored.append((rel + 1, s))
                    continue
                # on the topic's own official page, a rule needs no keyword to be relevant ("You cannot get a refund")
                if not (6 <= n <= (90 if kind_ == "list" else 45)) or not (ruleish and (rel or on_topic) or rel >= 2):
                    continue
                scored.append((rel + (1 if NUM.search(s) or PHONE.search(s) else 0), s))
        scored.sort(key=lambda x: -x[0])
        kept = list(dict.fromkeys(s for _, s in scored))[:15 if BLOGLIKE.search(u) else 40]
        slug = re.sub(r"[^a-z0-9]+", "-", domain(u))[:20]
        if any(f["id"].startswith(f"auto:{slug}:") for f in facts):  # second page on a domain: ids must stay unique
            seg = re.sub(r"[^a-z0-9]+", "-", u.rstrip("/").rsplit("/", 1)[-1].lower())[:24].strip("-")
            slug = f"{slug}-{seg}"
        audience = AUDIENCE.search(title + " " + u)
        for i, s in enumerate(kept, 1):
            sec = context.get(s, "")
            claim = f"{title[:70]} ({domain(u)})" + (f", section \"{sec[:70]}\"" if sec and sec.lower() not in title.lower() else "")
            if audience:
                claim += f" [written for {audience.group(0).lower()}: applies to that group]"
            facts.append({"id": f"auto:{slug}:{i}", "claim": claim, "value": s,
                          "status": "verified", "basis": "official_page_auto", "verified": True,
                          **({"scope": audience.group(0).lower()} if audience else {}),
                          "source_url": u_final, "retrieved_at": page.get("fetched_at") or C.now_iso()})
        sources.append({"url": u_final, "title": title, "facts": len(kept), "kind": kind(u)})
    if facts:
        with C.file_lock(ctx.rd / "fact_sheet.json"):
            sheet = C.load_json(ctx.rd / "fact_sheet.json")
            sheet["facts"] = [f for f in sheet["facts"] if not f["id"].startswith("auto:")] + facts
            C.save_json(ctx.rd / "fact_sheet.json", sheet)
            lm = C.load_json(ctx.rd / "link_map.json")
            have = {o["url"] for o in lm["official"]}
            lm["official"] += [{"url": s["url"], "state": "ok", "status": 200, "captured": False,
                                "label": s["title"][:60]} for s in sources if s["url"] not in have]
            C.save_json(ctx.rd / "link_map.json", lm)
    decisions = []
    if off_country:
        decisions.append(f"Left out {len(off_country)} authority page(s) from another country than this page's "
                         f"({', '.join(sorted({domain(u) for u in off_country}))}): their rules don't apply to this reader.")
    if not facts:
        decisions.append("No official page in reach for this topic; the copy relies on declared facts, client data and consensus.")
    return {"sources": sources, "blocked": blocked, "facts_added": len(facts), "decisions": decisions,
            "summary": f"{len(sources)} official pages, {len(facts)} verbatim facts, {len(blocked)} unreadable"}
