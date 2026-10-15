"""What kind of site is a ranking URL? Used for SERP composition and for
picking information-gain sources. Heuristic, transparent, easy to extend."""
from __future__ import annotations

import re
from urllib.parse import urlparse

# National government portals whose domains don't say "gov" (world data, any topic).
GOV_PORTALS = {"u.ae", "canada.ca", "usa.gov", "service-public.fr", "bund.de", "mygov.scot", "admin.ch", "overheid.nl",
               "government.nl", "regeringen.se", "regjeringen.no", "valtioneuvosto.fi", "australia.gov.au"}
# Public-sector second-level domains (health services, police, parliaments, regulators' zones).
PUBLIC_SLD = (".nhs.uk", ".police.uk", ".parliament.uk", ".mod.uk", ".gc.ca", ".gv.at", ".govt.nz", ".nhs.scot",
              ".hscni.net", ".gov.wales")
UGC = ("reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com", "mumsnet.com", "tripadvisor.",
       "trustpilot.com", "facebook.com", "x.com", "twitter.com", "medium.com", "forum", "community.", "answers.",
       "boards.", "discord", "lemmy", "hotukdeals.com")
UGC_PATH = re.compile(r"/(forums?|community|communities|discussions?|threads?|boards?|topic)/", re.I)
VIDEO = ("youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "dailymotion.com")
IMAGE = ("pinterest.", "instagram.com", "flickr.com", "unsplash.com")
# marketplaces and big retailers, across markets (world data: every niche uses the same list)
MARKET = ("amazon.", "ebay.", "etsy.com", "argos.co.uk", "johnlewis.com", "walmart.com", "aliexpress.", "temu.com",
          "next.co.uk", "very.co.uk", "currys.co.uk", "debenhams.com", "asos.com", "zalando.", "target.com",
          "bestbuy.com", "homedepot.com", "lowes.com", "costco.", "wayfair.", "bunnings.com.au", "jbhifi.com.au",
          "harveynorman.", "kmart.com.au", "canadiantire.ca", "flipkart.com", "trademe.co.nz", "noon.com",
          "mercadolibre.", "rakuten.", "otto.de", "cdiscount.com", "bol.com", "allegro.pl")
APPS = ("play.google.com", "apps.apple.com")
REFERENCE = ("wikipedia.org", "britannica.com", "investopedia.com", "dictionary.", "merriam-webster.com")
AUTHORITY = ("bbc.co.uk", "bbc.com", "nhs.uk", "which.co.uk", "citizensadvice.org.uk", "theguardian.com",
             "telegraph.co.uk", "independent.co.uk", "forbes.com", "nytimes.com", "cnn.com", "reuters.com",
             "moneysavingexpert.com", "timeout.com", "cntraveler.com", "lonelyplanet.com", "which.com",
             "consumerreports.org", "wired.com", "theverge.com", "techradar.com", "tomsguide.com", "gq-magazine.co.uk",
             "vogue.co.uk", "esquire.com", "cosmopolitan.com",
             # the same kinds of publisher and consumer body in other markets
             "apnews.com", "npr.org", "washingtonpost.com", "wsj.com", "mayoclinic.org", "clevelandclinic.org",
             "webmd.com", "abc.net.au", "choice.com.au", "smh.com.au", "cbc.ca", "theglobeandmail.com",
             "rte.ie", "irishtimes.com", "rnz.co.nz", "consumer.org.nz", "thehindu.com", "indianexpress.com")


SECOND_LEVEL = {"co", "org", "ac", "gov", "net", "com", "nhs", "ltd", "plc", "me", "sch", "police", "mod", "edu"}


def org_domain(host_or_url: str) -> str:
    """The organisation behind a host: shop.bhf.org.uk and www.bhf.org.uk are both bhf.org.uk. Used wherever
    "how many independent sites say this" is counted."""
    h = domain(host_or_url) if "/" in host_or_url else host_or_url.lower().removeprefix("www.")
    parts = h.split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else h


def domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def kind(url: str) -> str:
    d = domain(url)
    path = urlparse(url).path.lower()
    full = d + path
    if re.search(r"(^|\.)gov(\.[a-z]{2})?$|\.gov\.|\.gouv\.|\.gob\.|\.govt\.|\.go\.[a-z]{2}$|europa\.eu$|\.mil$", d) or \
            d in GOV_PORTALS or any(d.endswith("." + p) for p in GOV_PORTALS) or \
            d in ("nhs.uk",) or d.endswith(PUBLIC_SLD):
        return "government"
    if re.search(r"\.int$", d) or d.endswith(("un.org", "oecd.org", "worldbank.org", "imf.org")):
        return "international"
    if re.search(r"\.(edu|ac\.[a-z]{2})$", d):
        return "education"
    if any(x in full for x in APPS):
        return "app_store"
    if d.startswith(("help.", "support.", "faq.", "customerservice.")) or "/help-centre/" in path or "/hc/" in path:
        return "help_centre"  # a company's own help pages: official for that company's rules
    if any(x in d for x in VIDEO):
        return "video"
    if any(x in d for x in IMAGE):
        return "image"
    def ugc(x):
        if x.endswith("."):  # a prefix or a brand stem: "community.", "tripadvisor."
            return d.startswith(x) or ("." + x) in ("." + d)
        if "." in x:  # a registered domain: match it exactly or as a subdomain
            return d == x or d.endswith("." + x)
        return x in d  # a word in the host: "forum", "discord"
    if any(ugc(x) for x in UGC) or UGC_PATH.search(path):
        return "forum_ugc"
    if any(x in d for x in MARKET):
        return "marketplace"
    if any(x in d for x in REFERENCE):
        return "reference"
    if any(x in d for x in AUTHORITY):
        return "major_publisher"
    if re.search(r"/(products?|collections?|shop|store|category|categories|c)/", path):
        return "ecommerce"
    # charities, professional bodies and other non-profits: independent sources, not authorities
    if re.search(r"\.(org\.uk|org\.au|org\.nz|org\.za|org\.in|ngo|charity)$", d) or (
            d.endswith(".org") and not re.search(r"/(shop|store|products?)/", path)):
        return "nonprofit"
    if re.search(r"/(blog|blogs|news|guides?|articles?|insights|learn|resources)/", path):
        return "article"
    return "business_site"


def page_shape(url: str, title: str) -> str:
    """Rough content format of a result from its URL and title."""
    t = (title or "").lower()
    k = kind(url)
    if k == "video":
        return "video"
    if k == "forum_ugc":
        return "discussion"
    if k in ("marketplace", "ecommerce") or re.search(r"\b(buy|shop|sale|price|£|\$)\b", t):
        return "product_listing"
    if re.search(r"\b(\d+|ten|five|seven)\s+(best|top|ways|tips|things)\b|\bbest\b|\btop \d", t):
        return "listicle"
    if re.search(r"\bvs\.?\b|versus|compared|comparison|review", t):
        return "comparison_review"
    if re.search(r"\b(how to|guide|step|what is|what are|why|explained)\b", t):
        return "guide"
    if re.search(r"\b(check|track|status|login|sign in|portal|apply|calculator|tool)\b", t):
        return "tool_or_service"
    return "article"
