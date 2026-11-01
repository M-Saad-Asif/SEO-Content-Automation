# Regex library (RE2-safe; generated from scripts/seolib/gsc/regexlib.py, which is the source of truth)

Search Console uses RE2: no lookahead, lookbehind or backreferences, max 4,096 characters. Filter groups are AND only:
"A but not B" = an includingRegex filter plus an excludingRegex filter; OR lives inside one pattern. Query data is lowercase;
use (?i) on page patterns. Check a pattern with regexlib.validate() before calling. The client brand regex (R-BRAND) is built
from the client profile (name, aliases, proper nouns, domain stem): seo.py gsc data <client> brand shows it.

In the table, `\|` stands for `|` (escaped for Markdown); copy patterns from regexlib.py or `seo.py gsc data` output.

| Id | Dimension | Pattern | Source |
|---|---|---|---|
| R-Q1 | query | `^(who\|what\|when\|where\|why\|how\|which\|whose\|whom\|is\|are\|can\|could\|should\|would\|will\|do\|does\|did\|was\|were)\b` | SEOcrawl / SEOTesting base (6 question words); extended list [synth] |
| R-Q2 | query | `\b(who\|what\|when\|where\|why\|how\|which)\b` | [synth] question word anywhere (noisier) |
| R-CONV | query | `^(?:\S+\s+){9,}\S+$` | Chris Long / Nectiv: 10+ word conversational (AI-Mode-style) queries |
| R-LONG6 | query | `^(\S+\s){5,}\S+$` | [synth] 6+ words |
| R-LONG4 | query | `^\S+(\s+\S+){3,}$` | SEOcrawl 4+ words |
| R-SHORT | query | `^\S+(\s\S+)?$` | [synth] 1-2 word head terms |
| R-INFO | query | `\b(how to\|guide\|tutorial\|step by step\|tips\|tricks\|ways to\|best way to\|learn\|help\|explain\|understand\|instruction\|methods\|examples\|meaning of\|definition)\b` | Mark Williams-Cook |
| R-COMP | query | `\b(best\|vs\|versus\|compare\|comparison\|alternative\|alternatives\|better\|cheaper\|worse\|cheapest\|highest\|lowest\|top\|difference\|differences)\b` | Mark Williams-Cook |
| R-TRANS | query | `\b(buy\|purchase\|price\|prices\|cost\|costs\|cheap\|discount\|deal\|coupon\|order\|shop\|store\|near me\|sale\|best price\|affordable\|in stock\|quote\|hire)\b` | Mark Williams-Cook (+ quote, hire) |
| R-NAV | query | `\b(review\|reviews\|rating\|ratings\|customer service\|support\|warranty\|return policy\|refund\|complaint\|scam\|legit\|trustworthy\|login\|log in\|contact)\b` | Mark Williams-Cook (reputation/navigation) |
| R-SAAS | query | `\b(?:tool\|software\|app\|system\|platform\|application\|program\|solution\|portal\|suite\|calculator)s?\b` | Pietro Mingotti via Mark Williams-Cook (+ calculator) |
| R-SERVICE | query | `\b(near me\|nearby\|services?\|company\|agency\|consultant\|contractor\|booking\|book\|appointment\|hire\|quote)\b` | [synth]; echoes Edward Sturm's provider/local prompts |
| R-LOCAL | query | `\b(near me\|nearby\|open now\|closest)\b` | [synth]; add the client's cities |
| R-YEAR | query | `\b20(2[4-9]\|3[0-9])\b` | [synth] freshness intent |
| R-PROBLEM | query | `\b(error\|not working\|fix\|issue\|problem\|broken\|won't\|can't\|cannot)\b` | [synth] troubleshooting |
| R-SITEOP | query | `site:` | Chris Long: site: operator queries as LLM fan-out footprints |
| P-PARAMS | page | `[?&](utm_\|gclid\|fbclid\|sort\|filter\|order\|sessionid\|sid)=` | [synth] parameter leakage into Search |
| P-RSC | page | `[?&]_rsc=` | [synth] Next.js RSC payload URLs earning impressions |
| P-DEPTH | page | `^https?://[^/]+(/[^/]+){3,}/?$` | [synth] deep pages |
