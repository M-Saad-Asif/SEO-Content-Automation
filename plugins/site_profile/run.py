"""Site voice profile: measured style of the client's own pages, so the writer
keeps the site's essence (person, sentence length, spelling, heading case)."""
import re
import time
from urllib.parse import urlparse

from seolib import common as C

TTL = 30 * 86400
PROMO = re.compile(r"(\bsave\b|% off|\boff\b.{0,20}\bprice|free (delivery|shipping)|sign up|subscribe|newsletter|"
                   r"cookie|terms (and|&) conditions|registered (in|office)|company (no|number)|©|all rights reserved|"
                   r"authorised and regulated|regulated by the|capital (is )?at risk|shop now|buy now|limited time|"
                   r"discount|voucher|promo code|t&cs apply)", re.I)


def run(ctx):
    dom = ctx.brief["domain"].replace("https://", "").replace("http://", "").strip("/")
    cache = C.CACHE / "clients" / f"{dom}.json"
    old = C.load_json(cache)
    if old and not ctx.refresh and time.time() - old.get("_ts", 0) < TTL:
        old["summary"] = "cached profile"
        return old
    lm = ctx.load("foundation")["link_map"]
    internal = lm.get("internal", [])
    home = f"https://{dom}"
    about = next((u for u in internal if re.search(r"/(about|our-story|who-we-are)", u)), None)
    art_re = r"/(blog|blogs|guides?|news|articles?|insights|post)/[^/]+"
    arts = [u for u in internal if re.search(art_re, urlparse(u).path)][:3]
    if len(arts) < 3:  # articles often sit in their own child sitemap (post-sitemap.xml, sitemap_blogs_1.xml)
        idx = C.cache_get(f"xml|https://{dom}/sitemap.xml", "sitemap") or {}
        maps = [m for m in idx.get("locs", []) if re.search(r"post|blog|article|news", m, re.I)][:2]
        if maps:
            sm = C.run_async(C.fetch_many([{"url": m, "kind": "sitemap", "parse": "xml"} for m in maps]))
            for m in maps:
                for u in (sm.get(m) or {}).get("locs", []):
                    if u not in arts and urlparse(u).path.strip("/").count("/") >= 1 and len(arts) < 3:
                        arts.append(u)
    urls = [u for u in [home, about] + arts if u]
    res = C.run_async(C.fetch_many([{"url": u, "kind": "page", "parse": "doc"} for u in urls], ctx.refresh))
    paras, heads = [], []
    for u in urls:
        r = res.get(u) or {}
        for t, x in r.get("blocks", []):
            # promotions, cookie and legal notices are not the brand's writing voice
            if t == "p" and len(x.split()) >= 12 and not PROMO.search(x):
                paras.append((u, x))
            if t in ("h2", "h3"):
                heads.append(x)
    text = " ".join(x for _, x in paras)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 2]
    n = max(1, len(sents))
    words = [len(s.split()) for s in sents]
    title_case = sum(1 for h in heads if len(h.split()) > 2 and sum(w[0].isupper() for w in h.split()[1:] if w[:1].isalpha()) >= 0.6 * (len(h.split()) - 1))
    uk = len(re.findall(r"\b\w+(?:our|ise|ised|ising|isation|tre)\b", text))
    us = len(re.findall(r"\b\w+(?:or|ize|ized|izing|ization|ter)\b", text))
    prof = {
        "domain": dom, "pages_read": [u for u in urls if (res.get(u) or {}).get("state") == "ok"],
        "sentences_measured": len(sents),
        "avg_sentence_words": round(sum(words) / n, 1) if sents else None,
        "you_share": round(sum(1 for s in sents if re.search(r"\byou(r|rs)?\b", s, re.I)) / n, 2),
        "we_share": round(sum(1 for s in sents if re.search(r"\b(we|our|us)\b", s)) / n, 2),
        "contractions_per_100_sentences": round(100 * len(re.findall(r"\b\w+'(s|re|ll|ve|t|d)\b", text)) / n),
        "exclamations": text.count("!"),
        "heading_case": "title case" if heads and title_case > len(heads) / 2 else "sentence case",
        "spelling_signals": {"uk_like": uk, "us_like": us},
        "excerpts": list(dict.fromkeys(x[:420] for _, x in paras[:6]))[:3],
    }
    prof["summary"] = f"{len(prof['pages_read'])} pages, avg {prof['avg_sentence_words']} words/sentence"
    loc = (ctx.brief.get("locale") or "").lower()
    if (loc.startswith("en-gb") and us > 2 * max(uk, 1)) or (loc.startswith("en-us") and uk > 2 * max(us, 1)):
        prof["decisions"] = [f"The site's own pages lean {'US' if us > uk else 'UK'} spelling but the brief says "
                             f"{ctx.brief['locale']}; the brief wins."]
    if not sents:
        prof["avg_sentence_words"] = None
        prof.setdefault("decisions", []).append("No readable prose on the client's pages: voice falls back to RULES defaults.")
    if len(prof["pages_read"]) < 2:
        prof.setdefault("decisions", []).append("Voice profile is thin (under 2 readable pages); RULES defaults apply.")
    C.save_json(cache, {**prof, "_ts": time.time()})
    return prof
