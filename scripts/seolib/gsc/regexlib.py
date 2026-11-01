"""RE2-safe regex library for Search Console filters (UI and API), with where each pattern comes from.

Search Console uses RE2: no lookahead, lookbehind or backreferences, at most 4,096 characters. Filter groups are AND
only, so "A but not B" is two filters (includingRegex A + excludingRegex B) and OR lives inside one pattern. Query
data is lowercase; page patterns take (?i) when case is uncertain. Python's `re` evaluates these patterns the same
way for the analyses here, so the agent gets the same rows locally as Search Console would return.
"""
from __future__ import annotations

import re

# id: (dimension, pattern, provenance)
PATTERNS: dict[str, tuple[str, str, str]] = {
    "R-Q1": ("query", r"^(who|what|when|where|why|how|which|whose|whom|is|are|can|could|should|would|will|do|does|did|was|were)\b",
             "SEOcrawl / SEOTesting base ^(who|what|when|where|why|how); extended list [synth]"),
    "R-Q2": ("query", r"\b(who|what|when|where|why|how|which)\b", "[synth] question word anywhere (noisier)"),
    "R-CONV": ("query", r"^(?:\S+\s+){9,}\S+$", "Chris Long / Nectiv: 10+ word conversational (AI-Mode-style) queries"),
    "R-LONG6": ("query", r"^(\S+\s){5,}\S+$", "[synth] 6+ words"),
    "R-LONG4": ("query", r"^\S+(\s+\S+){3,}$", "SEOcrawl 4+ words"),
    "R-SHORT": ("query", r"^\S+(\s\S+)?$", "[synth] 1-2 word head terms"),
    "R-INFO": ("query", r"\b(how to|guide|tutorial|step by step|tips|tricks|ways to|best way to|learn|help|explain|"
                        r"understand|instruction|methods|examples|meaning of|definition)\b", "Mark Williams-Cook"),
    "R-COMP": ("query", r"\b(best|vs|versus|compare|comparison|alternative|alternatives|better|cheaper|worse|cheapest|"
                        r"highest|lowest|top|difference|differences)\b", "Mark Williams-Cook"),
    "R-TRANS": ("query", r"\b(buy|purchase|price|prices|cost|costs|cheap|discount|deal|coupon|order|shop|store|near me|"
                         r"sale|best price|affordable|in stock|quote|hire)\b", "Mark Williams-Cook (+ quote, hire)"),
    "R-NAV": ("query", r"\b(review|reviews|rating|ratings|customer service|support|warranty|return policy|refund|"
                       r"complaint|scam|legit|trustworthy|login|log in|contact)\b", "Mark Williams-Cook (reputation/navigation)"),
    "R-SAAS": ("query", r"\b(?:tool|software|app|system|platform|application|program|solution|portal|suite|calculator)s?\b",
               "Pietro Mingotti via Mark Williams-Cook (+ calculator)"),
    "R-SERVICE": ("query", r"\b(near me|nearby|services?|company|agency|consultant|contractor|booking|book|appointment|hire|quote)\b",
                  "[synth]; echoes Edward Sturm's provider/local prompts"),
    "R-LOCAL": ("query", r"\b(near me|nearby|open now|closest)\b", "[synth]; add the client's cities"),
    "R-YEAR": ("query", r"\b20(2[4-9]|3[0-9])\b", "[synth] freshness intent"),
    "R-PROBLEM": ("query", r"\b(error|not working|fix|issue|problem|broken|won't|can't|cannot)\b", "[synth] troubleshooting"),
    "R-SITEOP": ("query", r"site:", "Chris Long: site: operator queries as LLM fan-out footprints"),
    "P-PARAMS": ("page", r"[?&](utm_|gclid|fbclid|sort|filter|order|sessionid|sid)=", "[synth] parameter leakage into Search"),
    "P-RSC": ("page", r"[?&]_rsc=", "[synth] Next.js RSC payload URLs earning impressions"),
    "P-DEPTH": ("page", r"^https?://[^/]+(/[^/]+){3,}/?$", "[synth] deep pages"),
}

QUESTION = re.compile(PATTERNS["R-Q1"][1])
CONVERSATIONAL = re.compile(PATTERNS["R-CONV"][1])
INTENTS = ("R-TRANS", "R-SERVICE", "R-COMP", "R-INFO", "R-NAV", "R-SAAS", "R-PROBLEM", "R-LOCAL")
BLOG_PATH = re.compile(r"(?i)/(blog|news|guides?|articles?|learn|resources|insights|advice|tips|help|knowledge|"
                       r"how-to|faq|magazine|journal|stories)(/|$)")
MONEY_PATH = re.compile(r"(?i)/(services?|products?|shop|store|collections?|category|categories|pricing|buy|plans?|"
                        r"solutions?|locations?|book|quote|hire|tools?|calculators?)(/|$)")


def validate(pattern: str) -> str | None:
    """Why Search Console would reject the pattern (RE2 rules), or None."""
    if len(pattern) > 4096:
        return "longer than 4,096 characters"
    if re.search(r"\(\?<?[=!]", pattern):
        return "lookahead/lookbehind is not RE2: use an includingRegex plus an excludingRegex filter instead"
    if re.search(r"\\[1-9]", pattern):
        return "backreferences are not RE2"
    if re.search(r"\(\?[>|]|\(\?\(|[*+?}][+]", pattern):
        return "atomic groups, conditionals and possessive quantifiers are not RE2"
    try:
        re.compile(pattern)
    except re.error as e:
        return f"invalid regex: {e}"
    return None


def get(pid: str) -> str:
    return PATTERNS[pid][1]


def matches(pid_or_pattern: str, text: str) -> bool:
    pat = PATTERNS[pid_or_pattern][1] if pid_or_pattern in PATTERNS else pid_or_pattern
    return bool(re.search(pat, (text or "").lower() if not pat.startswith("(?i)") else text or ""))


def intent(query: str) -> str:
    """The first intent class the query matches, in commercial-first order; 'question' or 'other' otherwise."""
    q = (query or "").lower()
    for pid in INTENTS:
        if re.search(PATTERNS[pid][1], q):
            return pid
    return "R-Q1" if QUESTION.search(q) else "other"


def brand_terms(profile: dict, domain: str = "") -> list[str]:
    """The client's own names: profile name, aliases, proper nouns, domain stem, with and without spaces."""
    names = [profile.get("client") or "", *(profile.get("client_aliases") or []), *(profile.get("proper_nouns") or [])]
    dom = (domain or profile.get("domain") or "").lower().removeprefix("www.")
    if dom:
        names.append(dom.split(".")[0])
    out = []
    for n in names:
        n = re.sub(r"\.(com|co\.uk|net|org|io|ai|co)$", "", str(n).lower()).strip()
        n = re.sub(r"[^a-z0-9 &'-]", " ", n)
        n = " ".join(n.split())
        if len(n) < 3:
            continue
        out += [n, n.replace(" ", ""), n.replace("-", " "), n.replace("-", "")]
    return sorted({x for x in out if len(x) >= 3}, key=len, reverse=True)


def brand_regex(profile: dict, domain: str = "") -> str | None:
    """R-BRAND for this client: pipe-joined name variants (misspellings can be added as client_aliases)."""
    terms = brand_terms(profile, domain)
    if not terms:
        return None
    return r"\b(" + "|".join(re.escape(t).replace(r"\ ", r"\s?") for t in terms) + r")\b"


def is_brand(query: str, brand_re: str | None) -> bool:
    return bool(brand_re and re.search(brand_re, (query or "").lower()))


def page_kind(url: str) -> str:
    """'blog' (informational), 'money' (service/product/category) or 'other', from the address."""
    if BLOG_PATH.search(url or ""):
        return "blog"
    if MONEY_PATH.search(url or ""):
        return "money"
    return "other"
