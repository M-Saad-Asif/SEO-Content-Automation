"""Which market (locale) a page is for, decided without asking.

Order of evidence: what the operator says ("for the US market", "UAE readers"), then the target page itself (its
<html lang>, og:locale, hreflang, currency and domain ending), then the client profile. The locale ("en-US", "de-DE")
drives every search (Google's country code and language), spelling, currency and which authorities are searched.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .nlp import places

# a country's usual locale: language first, then the country (world data)
COUNTRY_LOCALE = {
    "gb": "en-GB", "us": "en-US", "au": "en-AU", "ca": "en-CA", "ie": "en-IE", "nz": "en-NZ", "in": "en-IN",
    "ae": "en-AE", "sg": "en-SG", "za": "en-ZA", "pk": "en-PK", "ng": "en-NG", "ph": "en-PH", "my": "en-MY",
    "hk": "en-HK", "sa": "ar-SA", "qa": "en-QA", "kw": "en-KW", "de": "de-DE", "at": "de-AT", "ch": "de-CH",
    "fr": "fr-FR", "be": "fr-BE", "es": "es-ES", "mx": "es-MX", "it": "it-IT", "nl": "nl-NL", "pt": "pt-PT",
    "br": "pt-BR", "se": "sv-SE", "no": "nb-NO", "dk": "da-DK", "fi": "fi-FI", "pl": "pl-PL", "tr": "tr-TR",
    "jp": "ja-JP", "kr": "ko-KR", "cn": "zh-CN", "th": "th-TH", "vn": "vi-VN", "id": "id-ID",
}
TLD_COUNTRY = {"uk": "gb", "au": "au", "ca": "ca", "ie": "ie", "nz": "nz", "in": "in", "ae": "ae", "sg": "sg",
               "za": "za", "pk": "pk", "de": "de", "at": "at", "ch": "ch", "fr": "fr", "be": "be", "es": "es",
               "mx": "mx", "it": "it", "nl": "nl", "pt": "pt", "br": "br", "se": "se", "no": "no", "dk": "dk",
               "fi": "fi", "pl": "pl", "tr": "tr", "jp": "jp", "kr": "kr", "my": "my", "ph": "ph", "ng": "ng"}
MARKET_WORDS = re.compile(r"\b(market|readers?|audience|customers?|users?|visitors?|searchers?|buyers?|"
                          r"targeting|target|aimed at|for people in|based in|in the)\b", re.I)


def norm(locale: str) -> str:
    lang, _, region = (locale or "").replace("_", "-").partition("-")
    return lang.lower() + ("-" + region.upper() if region else "")


def from_text(text: str) -> str | None:
    """'for the US market', 'aimed at Australian readers', 'targeting the UAE': the operator's market, else None.
    A place in the keyword itself ("dubai visa for uk citizens") is a topic, not a market, so only places next to
    market words count."""
    if not text or not MARKET_WORDS.search(text):
        return None
    for m in MARKET_WORDS.finditer(text):
        window = text[max(0, m.start() - 40): m.end() + 40]
        codes = [p[4:] for p in sorted(places(window))]
        for c in codes:
            if c in COUNTRY_LOCALE:
                return COUNTRY_LOCALE[c]
    return None


def from_page(url: str, html: str) -> tuple[str | None, list[str]]:
    """The page's own market signals: (locale or None, evidence)."""
    ev = []
    h = html or ""
    lang = re.search(r"<html[^>]*\blang=[\"']([a-zA-Z]{2}(?:[-_][a-zA-Z]{2})?)", h)
    ogl = re.search(r'property=["\']og:locale["\']\s+content=["\']([a-zA-Z]{2}[-_][a-zA-Z]{2})', h)
    region = None
    for src, mm in (("og:locale", ogl), ("html lang", lang)):
        if mm and ("-" in mm.group(1) or "_" in mm.group(1)):
            region = norm(mm.group(1)).split("-")[1].lower()
            ev.append(f"{src} {mm.group(1)}")
            break
    tld = urlparse(url).netloc.lower().rsplit(".", 1)[-1]
    if tld in TLD_COUNTRY and (not region or region == "us"):
        region = TLD_COUNTRY[tld]  # a .co.uk site tagged lang="en-US" by its theme is still a UK site
        ev.append(f"domain ending .{tld}")
    text = re.sub(r"<[^>]+>", " ", h)[:200000]
    cur = {"£": len(re.findall(r"£\s?\d", text)), "$": len(re.findall(r"\$\s?\d", text)),
           "€": len(re.findall(r"€\s?\d", text))}
    top = max(cur, key=cur.get)
    if cur[top] >= 3:
        ev.append(f"prices in {top} ({cur[top]})")
        if not region:
            region = {"£": "gb", "$": "us", "€": None}[top]
    if not region:
        return None, ev
    lang_code = (norm(lang.group(1)).split("-")[0] if lang else "en") or "en"
    loc = COUNTRY_LOCALE.get(region, f"{lang_code}-{region.upper()}")
    if not loc.startswith(lang_code + "-"):
        loc = f"{lang_code}-{region.upper()}"
    return loc, ev
