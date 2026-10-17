"""The gaming niche: client profile `niche: gaming` (first client gta6coverage.com; owner's rules of 17 Oct 2026).

- Everything is used: official statements, leaks, rumours, insider reports and what players say. Each claim carries
  its label in its own sentence, and the article opens with its status (Official / Leak / Rumor / Insider report),
  so a reader never takes a rumour for an announcement.
- Titles are written for Google Discover and News: the game first, a concrete hook (a name, a date, a number),
  curiosity the article pays off, never a promise it doesn't keep.
- Who can be named: the publisher and platform holders (facts), the press (credited and linked for what they
  report), public platforms (Reddit, X, YouTube: "players on Reddit…", the post linked). GTA fan and coverage sites,
  and any site that is neither, are never named or linked: their claims are told as "a leak shared online".
- The views are the editorial desk's ("we"), as the site's About page signs its articles.
- The site's own records (database, named places) are verified facts; a blank stat means "not announced".
- Finished pages are written into the site's repository as its own Markdown (`export`).
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

OFFICIAL = ("rockstargames.com", "take2games.com", "take2.com", "playstation.com", "xbox.com", "nintendo.com",
            "store.steampowered.com", "epicgames.com", "esrb.org", "pegi.info", "usk.de", "classification.gov.au",
            "atlanticrecords.com")
PRESS = ("ign.com", "gamespot.com", "polygon.com", "kotaku.com", "eurogamer.net", "pcgamer.com", "gamesradar.com",
         "videogameschronicle.com", "theverge.com", "bloomberg.com", "reuters.com", "apnews.com", "bbc.co.uk", "bbc.com",
         "theguardian.com", "nytimes.com", "washingtonpost.com", "forbes.com", "wsj.com", "cnbc.com", "insider-gaming.com",
         "gameinformer.com", "rockpapershotgun.com", "dexerto.com", "gamerant.com", "thegamer.com", "screenrant.com",
         "windowscentral.com", "pushsquare.com", "purexbox.com", "techradar.com", "tomsguide.com", "gamesindustry.biz",
         "axios.com", "variety.com", "hollywoodreporter.com", "engadget.com", "digitaltrends.com", "vg247.com",
         "metro.co.uk", "independent.co.uk", "telegraph.co.uk", "usatoday.com", "cnet.com", "wired.com", "gamedeveloper.com")
PUBLIC = ("reddit.com", "x.com", "twitter.com", "youtube.com", "youtu.be", "twitch.tv", "tiktok.com", "instagram.com",
          "threads.net", "bsky.app", "discord.com", "resetera.com")
# banned AI-tell words a game uses literally ("unlock the Cheetah")
ALLOWED = {"unlock", "unlocks", "unlocking"}
# words a gaming page uses as labels, as often as it has claims: never capped as filler
LABEL_WORDS = {"official", "officially", "confirmed", "confirm", "confirms", "reportedly", "reported", "rumored",
               "rumoured", "leaked", "unconfirmed"}
# the game's own fan and coverage sites: never named, never linked
FAN = re.compile(r"(?i)gta|grand-?theft|rockstar(?!games\.)|fandom\.com|leonida|vicecity|vicountdown|\bvi-?countdown")

LABELS = {
    "leak": re.compile(r"(?i)\b(leak(?:s|ed|er|ers)?|data-?min(?:e|ed|er|ers|ing)|datamine\w*|files? (?:show|suggest))\b"),
    "insider": re.compile(r"(?i)\b(insiders?|sources? (?:close to|familiar with|at)|people familiar|according to "
                          r"(?:people|sources|a person)|told (?:bloomberg|kotaku|ign|reporters?)|(?:a |the )?report(?:s|ed)? (?:that|by|from|says))\b"),
    "rumor": re.compile(r"(?i)\b(rumou?r(?:s|ed)?|reportedly|allegedly|unconfirmed|unverified|speculat\w+|purported\w*|"
                        r"claims? (?:that|suggest)|(?:fan )?theor(?:y|ies)|could be|might be|hint(?:s|ed)? at)\b"),
    "community": re.compile(r"(?i)\b(fans?|players?|the community|redditors?|viewers?|commenters?)\b[^.]{0,40}\b(say|said|think|"
                            r"believe|noticed|spotted|point(?:ed)? out|react\w*|want|hope|asked|argue)\b"),
}
STATUS = {"official": "Official", "leak": "Leak", "rumor": "Rumor", "insider": "Insider report", "community": "Fan theory"}
# the status line a page opens with ("Status: Leak.", "Rumor:", "Official —")
STATUS_LINE = re.compile(r"(?i)^\W*(?:status\W+)?(official|confirmed|leak(?:ed)?|rumou?r(?:ed)?|insider(?: report)?|"
                         r"report(?:ed)?|unconfirmed|fan theory)\b")

CHEAT = re.compile(r"(?i)\b(cheats?|cheat codes?|codes?|secrets?|easter eggs?|glitch(?:es)?|money glitch|exploits?)\b")
TECH = re.compile(r"(?i)\b(pc|requirements?|specs?|system|ps5( pro)?|xbox|series [xs]|switch|performance|fps|frame ?rate|"
                  r"resolution|4k|storage|file size|download size|gb|patch(?:es)?|update size|graphics|ray tracing|"
                  r"controller|platforms?|cross-?play|crossplay|steam deck)\b")
NEWS = re.compile(r"(?i)\b(news|announce\w*|trailer\s*\d*|delay\w*|leak\w*|rumou?r\w*|confirm\w*|reveal\w*|price|"
                  r"pre-?orders?|preorders?|release date|launch\w*|countdown|earnings|insider|report\w*|reaction|"
                  r"showcase|extended look|new screenshots?|just dropped|today|this week)\b")


def on(brief: dict | None) -> bool:
    return str((brief or {}).get("niche") or "").lower() == "gaming"


def names_rx(brief: dict | None) -> re.Pattern:
    """The game's names: the profile's `game_names`, else its synonyms (both sides), else the query's first words."""
    b = brief or {}
    syn = b.get("synonyms") or {}
    names = list(b.get("game_names") or []) or (list(syn.keys()) + list(syn.values()))
    names = [str(n) for n in names if str(n).strip()] or [" ".join(str(b.get("target_query") or "x").split()[:2])]
    return re.compile(r"(?i)(?<![\w-])(?:" + "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True)) + r")(?![\w-])")


def host(url_or_domain: str) -> str:
    h = re.sub(r"^https?://", "", str(url_or_domain or "").lower()).split("/")[0].split(":")[0]
    return h[4:] if h.startswith("www.") else h


def _match(h: str, names) -> bool:
    return any(h == n or h.endswith("." + n) for n in names)


def kind(url_or_domain: str, brief: dict | None = None) -> str:
    """official / press / public / client / rival (a GTA fan or coverage site: never named, its items dropped) /
    other (a site that is neither, such as a small gaming news site: its claims are used with their label, the site
    is never named or linked)."""
    b = brief or {}
    h = host(url_or_domain)
    if not h:
        return "rival"
    if b.get("domain") and _match(h, [host(b["domain"])]):
        return "client"
    if _match(h, list(OFFICIAL) + [host(x) for x in b.get("official_sites") or []]):
        return "official"
    if _match(h, [host(x) for x in b.get("competitor_sites") or []]):
        return "rival"
    if _match(h, list(PRESS) + [host(x) for x in b.get("press_sites") or []]):
        return "press"
    if _match(h, PUBLIC):
        return "public"
    return "rival" if FAN.search(h) else "other"


def nameable(url_or_domain: str, brief: dict | None = None) -> bool:
    return kind(url_or_domain, brief) in ("official", "press", "public", "client")


SAID = re.compile(r"(?i)\b(rockstar(?: games)?|take-two|strauss zelnick|sony|microsoft|playstation|xbox)\b[^.]{0,50}"
                  r"\b(confirm\w*|announc\w*|said|says|lists?|listed|revealed|stated|published|released)\b")


def label(sentence: str, source_kind: str = "") -> str:
    """The claim's label: official (said by the publisher or a platform, or a report of what they said), leak,
    insider, rumor, community, or report (a press sentence with no label of its own: still a report, never an
    announcement)."""
    s = str(sentence or "")
    for k in ("leak", "insider", "rumor", "community"):
        if LABELS[k].search(s):
            return k
    if source_kind == "official" or SAID.search(s):
        return "official"
    return "report" if source_kind in ("press", "other") else "rumor"


def category(query: str, page_type: str = "", said: str = "") -> str:
    """The site section a page belongs in: cheats, tech, news or guides."""
    if said in ("news", "guides", "cheats", "tech"):
        return said
    q = str(query or "")
    if CHEAT.search(q):
        return "cheats"
    if page_type == "news" or NEWS.search(q):
        return "news"
    if TECH.search(q):
        return "tech"
    return "guides"


def page_type(query: str, current: str = "guide") -> str:
    """A gaming site has no tools or services: news or a guide."""
    return "news" if category(query) == "news" else ("guide" if current in ("tool", "service", "product", "category",
                                                                             "location", "company", "home", "") else current)


def tag(f: dict, brief: dict | None = None) -> str:
    """How the writer sees a fact's status and who may be credited: "[leak · IGN]", "[rumor · unnamed site]"."""
    lab = f.get("label") or ""
    if not lab:
        return ""
    url = f.get("source_url") or ""
    k = f.get("source_kind") or kind(url, brief)
    who = _source_name(url) if k in ("official", "press") else (
        "a public platform: name the platform, not the user" if k == "public" else
        "a gaming news site: never name it" if k == "other" else "unnamed site: never name it")
    return f"[{STATUS.get(lab, lab)} · {who}] "


def status_of(facts: list[dict], query: str) -> str:
    """The label the article opens with: the query's own (a leak, a rumor), else Official when the publisher's word
    carries the topic, else the commonest label of the page-one claims."""
    for k in ("leak", "insider", "rumor"):
        if LABELS[k].search(query or ""):
            return STATUS[k]
    labs = [f.get("label") for f in facts if f.get("label")]
    if "official" in labs:
        return "Official"
    rest = [x for x in labs if x != "official"]
    return STATUS.get(max(set(rest), key=rest.count), "Report") if rest else "Official"


def brief_lines(b: dict, facts: list[dict], today: str | None = None) -> list[str]:
    """The gaming rules, as the write brief's section 0 (they override RULES_CARD.md where they differ)."""
    today = today or date.today().strftime("%B %d, %Y").replace(" 0", " ")
    st =status_of(facts, b.get("target_query") or "")
    return [
        "## 0. Gaming page rules (they override RULES_CARD.md where they differ)",
        f"- Status first: the opening's first words are the article's status in bold, then the news: \"**{st}:** …\" "
        "(one of **Official**, **Leak**, **Rumor**, **Insider report**, **Fan theory**; \"**Official, with leaks:**\" when "
        "both). In the same paragraph, say plainly what is confirmed and what is not.",
        "- Every claim carries its label in its own sentence: official (\"Rockstar lists…\", \"Take-Two confirmed…\"); "
        "report (\"IGN reports…\"); insider (\"Bloomberg's Jason Schreier reports, citing people familiar with…\"); leak "
        "(\"leaked footage appears to show…\"); rumor (\"an unconfirmed rumor claims…\"); fan theory (\"players on Reddit "
        "think…\"). Each fact below shows its label. Never state a leak, rumor or report as fact, and never upgrade one "
        "to \"confirmed\". The rules card's \"be certain\" applies to official facts and the site's own records only.",
        "- Who you may name and link: the publisher and platform holders, press outlets, and public platforms (Reddit, "
        "X, YouTube; the platform, never a private user). A fact marked \"unnamed site\" came from a GTA fan or coverage "
        "site: use the claim with its label (\"a leak shared online\"), never the site's name or link.",
        "- Title (front matter `title`, also the page's H1 on the site): written for Google Discover and News: "
        "\"GTA 6\" first, then the hook: a concrete name, date, number or thing shown; curiosity the opening pays off; "
        "55-70 characters; title case like the site's own headlines. A leak or rumor title carries its label "
        "(\"Leak:\", \"reportedly\", \"rumored\"). Never ALL CAPS, \"!\", \"you won't believe\", or a promise the "
        "article doesn't keep. The H1 is the same words.",
        "- Front matter also takes `quick_answer` (2-3 sentences, at most 60 words, only what the article states, with "
        "its labels) and `tags` (3-6 short tags, e.g. [trailer, release date, leaks]).",
        f"- Dates: a time-sensitive fact carries its date (\"as of {today}\"); the newest development leads. A blank "
        "stat in the site's records means Rockstar hasn't published it: write \"not announced\", never a figure.",
        "- Database items (vehicles, weapons): name them exactly as the site's record does; don't link them, the site "
        "links their first mention itself. Unnamed items are described as the record describes them.",
        "- Cheats, codes and button inputs: only ones in the facts; never recycle codes from older GTA games as GTA 6 "
        "codes. Story spoilers beyond the official trailers get a one-line warning before them.",
        "",
    ]


ATTRIB = re.compile(r"(?i)\b(reports?|reported|reporting|according to|says|said|claims?|claimed|told|citing|appears? to|"
                    r"seems? to|suggests?|spotted|believes?|think|thinks|expects?|points? to|not (?:yet )?confirmed|"
                    r"hasn't confirmed|has not confirmed|unannounced|not announced)\b")
HYPE_TITLE = re.compile(r"(?i)you won'?t believe|will blow your mind|shocking|insane|this changes everything|must see|"
                        r"\bfinally\b.*\bconfirmed\b(?!.*\b(?:rockstar|take-two)\b)")


def check(lint) -> None:
    """A gaming page's own checks: it opens with its status, every claim that isn't official carries its label, the
    title is a Discover headline that doesn't oversell, and the site's front matter is there."""
    from .lint import strip_md
    from .review import _toks
    meta = lint.meta or {}
    paras = [b for b in lint.blocks if b["type"] == "p"]
    h2 = next((i for i, b in enumerate(lint.blocks) if b["type"] == "h2"), len(lint.blocks))
    first = next((b for b in lint.blocks[:h2] if b["type"] == "p"), None)
    opening = strip_md(first.get("raw") or first["text"]) if first else ""
    m = STATUS_LINE.match(opening)
    if not m:
        lint.add("G10-status-label", "block", first, opening[:160], "the opening doesn't start with the article's status",
                 "start the first paragraph with its status in bold: \"**Official:**\", \"**Leak:**\", \"**Rumor:**\", "
                 "\"**Insider report:**\" or \"**Fan theory:**\", then the news")
    status = (m.group(1).lower() if m else "")
    # a claim from a leak, rumor or report is told as one, wherever it is used
    claims = [(f, _toks(str(f.get("value") or ""), {})) for f in lint.sheet.get("facts") or []
              if f.get("label") and f["label"] != "official"]
    for b in paras + [x for x in lint.blocks if x["type"] == "li"]:
        for s in re.split(r"(?<=[.!?])\s+", strip_md(b.get("raw") or b["text"])):
            st = _toks(s, {})
            if len(st) < 5 or any(x.search(s) for x in LABELS.values()) or ATTRIB.search(s) or STATUS_LINE.match(s):
                continue
            for f, ft in claims:
                if ft and len(st & ft) / ((len(st) * len(ft)) ** 0.5 or 1) >= 0.45:
                    lint.add("G11-unlabelled-claim", "block", b, s[:200], f"states a {STATUS.get(f['label'], f['label']).lower()} "
                             f"(`{f['id']}`) as fact", "give it its label in the sentence: \"reportedly\", \"according to "
                             "a leak\", \"IGN reports\", \"players think\"")
                    break
    title = str(meta.get("title") or "")
    if title:
        if "!" in title or HYPE_TITLE.search(title) or len(re.findall(r"\b[A-Z]{4,}\b", title)) > 1:
            lint.add("G12-title-bait", "block", None, title, "the title oversells (\"!\", capitals or bait wording)",
                     "a concrete hook instead: the name, date, number or thing shown, in title case")
        if not re.search(r"(?i)\bGTA\s?(?:6|VI)\b|grand theft auto", title):
            lint.add("G12-title-game", "warn", None, title, "the title doesn't name the game", "start it with \"GTA 6\"")
        if status and status not in ("official", "confirmed") and not (
                any(x.search(title) for x in LABELS.values()) or re.search(r"(?i)\b(report\w*|claims?|could|may|might)\b", title)):
            lint.add("G13-title-label", "block", None, title, f"a {status} page whose title reads as confirmed",
                     "put the label in the title: \"Leak:\", \"reportedly\", \"rumored\", \"insiders say\"")
    qa = str(meta.get("quick_answer") or meta.get("quickAnswer") or "")
    if not qa:
        lint.add("G14-quick-answer", "block", None, "(front matter)", "no quick_answer for the site's Quick answer box",
                 "add quick_answer: 2-3 sentences, at most 60 words, only what the article states, with its labels")
    elif len(qa.split()) > 70:
        lint.add("G14-quick-answer", "block", None, qa[:160], f"quick_answer is {len(qa.split())} words", "cut it to 60 words")
    if not meta.get("tags"):
        lint.add("G15-tags", "warn", None, "(front matter)", "no tags", "add 3-6 short tags")


# ---- the site's own records -----------------------------------------------------------------------------------
STAT = re.compile(r"(?i)(speed|acceleration|braking|handling|price|drivetrain|seats|weaponized|damage|fire ?rate|"
                  r"accuracy|range|magazine|capacity)")
VERIFIED = {"official-name": "named by Rockstar in its official material",
            "official-visual": "shown in Rockstar's official material, not named by Rockstar",
            "visual-only": "seen in official images only; Rockstar hasn't named it"}


def _words(key: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", key).lower()


def record_facts(brief: dict, strong: str = "", live: str = "") -> list[dict]:
    """The site's database records and named places as verified facts, for the pages about them: a record named in
    the query, title or live text, or every record of a kind the page is about (vehicles, weapons, places)."""
    repo = brief.get("site_repo")
    if not repo:
        return []
    root = Path(str(repo)).expanduser()
    text = f"{strong} {live}".lower()
    out = []
    for rel in brief.get("site_data_files") or []:
        p = root / rel
        if p.suffix == ".json":
            try:
                rows = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
        elif p.suffix in (".ts", ".js", ".mjs"):
            from .siterates import load
            data = load(p).get(p.name) or {}
            rows = next((v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])
            for r in rows:
                r.setdefault("type", "places")
        else:
            continue
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict) or not r.get("name"):
                continue
            typ = str(r.get("type") or p.stem)
            word = {"vehicles": r"vehicles?|cars?|bikes?|boats?|motorcycles?|rides?", "weapons": r"weapons?|guns?|pistols?|rifles?|smgs?|arsenal",
                    "places": r"map|places?|locations?|regions?|cities|city|areas?|leonida|world"}.get(typ, re.escape(typ))
            named = re.search(rf"(?<![\w']){re.escape(str(r['name']).lower())}(?![\w'])", text)
            if not named and not re.search(rf"\b(?:{word}|database)\b", text):
                continue
            unknown = [_words(k) for k, v in r.items() if v is None and STAT.search(k)]
            known = [f"{_words(k)}: {v}" for k, v in r.items() if v not in (None, "") and STAT.search(k)]
            kind_ = r.get("class") or r.get("category") or ""
            ver = VERIFIED.get(str(r.get("verification") or ""), "")
            value = (f"{r['name']}" + (f" ({kind_}" + (f", made by {r['manufacturer']}" if r.get("manufacturer") else "") + ")" if kind_ else "")
                     + (f": {ver}" if ver else "") + ". " + str(r.get("description") or r.get("note") or "").strip()
                     + (f" Known: {'; '.join(known)}." if known else "")
                     + (f" Not announced: {', '.join(unknown)}." if unknown else ""))
            page = f"https://{host(brief.get('domain') or '')}/database/{typ}/{r['id']}" if typ in ("vehicles", "weapons") and r.get("id") else ""
            out.append({"id": f"site:{typ}:{r.get('id') or len(out) + 1}", "claim": f"{brief.get('client')}'s own {typ} record"
                        + (" (the site links its first mention by itself: name it exactly, don't link it)"
                           if r.get("verification") == "official-name" else " (unnamed by Rockstar: describe it as the record does)"),
                        "value": " ".join(value.split()), "status": "verified", "basis": "site_rates", "verified": True,
                        "source_url": r.get("sourceUrl") or brief.get("official_page") or "",
                        "retrieved_at": r.get("lastUpdated") or "", "record_page": page, "label": "official"})
    return out


# ---- export into the site --------------------------------------------------------------------------------------
def _front(md: str) -> tuple[dict, str]:
    import yaml
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", md, re.S)
    return ((yaml.safe_load(m.group(1)) or {}) if m else {}), (md[m.end():] if m else md)


def _yaml_str(s) -> str:
    return json.dumps(" ".join(str(s or "").split()), ensure_ascii=False)


def export(rd: Path, brief: dict, today: str | None = None) -> Path | None:
    """final.md as the site's own article: content/<category>/<slug>.md with its frontmatter (title, excerpt,
    quickAnswer, dates, tags, author, sources). The H1 becomes the title; links to the site become paths; links to
    officially named database items are left to the site, which links first mentions itself."""
    repo = brief.get("site_repo")
    exp = brief.get("site_export") or {}
    final = rd / "final.md"
    if not repo or not final.exists():
        return None
    meta, body = _front(final.read_text(encoding="utf-8"))
    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    title = meta.get("title") or (h1.group(1).strip() if h1 else brief.get("target_query"))
    body = re.sub(r"^#\s+.+\n+", "", body.lstrip(), count=1) if h1 else body
    dom = host(brief.get("domain") or "")
    body = re.sub(rf"\]\(https?://(?:www\.)?{re.escape(dom)}(/[^)\s]*)?\)", lambda m: f"]({m.group(1) or '/'})", body)
    body = re.sub(r"\[([^\]]+)\]\((/database/(?:vehicles|weapons)/[^)\s]+)\)", r"\1", body)  # the site links these
    sources, seen = [], set()
    for text, url in re.findall(r"\[([^\]]+)\]\((https://[^)\s]+)\)", body):
        k = kind(url, brief)
        if k in ("official", "press") and url not in seen:
            seen.add(url)
            sources.append((f"{_source_name(url)} — {text.strip()}"[:110], url))
    cat = category(brief.get("target_query"), brief.get("page_type"), str(meta.get("category") or brief.get("site_category") or ""))
    slug = re.sub(r"[^a-z0-9]+", "-", str(brief.get("slug") or title).lower()).strip("-")[:80]
    dest = Path(str(repo)).expanduser() / "content" / cat / f"{slug}.md"
    today = today or date.today().isoformat()
    old = _front(dest.read_text(encoding="utf-8"))[0] if dest.exists() else {}
    author = exp.get("author") or {"id": "editorial-desk", "name": f"{brief.get('client')} Editorial Desk", "role": "Editorial desk"}
    tags = meta.get("tags") or [t for t in [brief.get("target_query")] if t]
    L = ["---", f"title: {_yaml_str(title)}", f"excerpt: {_yaml_str(meta.get('meta_description') or meta.get('excerpt') or '')}"]
    if meta.get("quick_answer") or meta.get("quickAnswer"):
        L.append(f"quickAnswer: {_yaml_str(meta.get('quick_answer') or meta.get('quickAnswer'))}")
    L.append(f"publishedAt: \"{old.get('publishedAt') or today}\"")
    if old.get("publishedAt"):
        L.append(f"updated: \"{today}\"")
    L.append("tags: [" + ", ".join(_yaml_str(t) for t in tags[:6]) + "]")
    L += ["author:", f"  id: {author['id']}", f"  name: {author['name']}", f"  role: {author['role']}"]
    if sources:
        L.append("sources:")
        for lab, u in sources[:8]:
            L += [f"  - label: {_yaml_str(lab)}", f"    url: {u}"]
    L.append("---")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(L) + "\n\n" + body.strip() + "\n", encoding="utf-8")
    return dest


def _source_name(url: str) -> str:
    h = host(url)
    known = {"rockstargames.com": "Rockstar Games", "take2games.com": "Take-Two Interactive", "playstation.com": "PlayStation",
             "xbox.com": "Xbox", "esrb.org": "ESRB", "pegi.info": "PEGI", "bloomberg.com": "Bloomberg", "ign.com": "IGN"}
    for d, n in known.items():
        if h == d or h.endswith("." + d):
            return n
    return h.split(".")[-2].capitalize() if "." in h else h
