"""The client's own rates data: the numbers its calculators run on, kept by the site from official sources.

A client profile can point at the site's rate modules (`site_rates_dir`, e.g. Calcsite's src/data/rates, and
optionally `site_rates_registry`, the register naming each topic's search terms and pages). The modules are read
with Node (scripts/read_site_rates.mjs; TypeScript types are stripped), their comments give each value its meaning,
and every module that applies to the page becomes verified facts (`rates:<module>:<export>[:<year>]`, basis
`site_rates`) dated by the module's own `lastChecked`. They win any disagreement with page one. Anything the page
says that these files don't hold keeps the pipeline's own verification (official pages, quote checks, the fact-check
pass).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import common as C

READER = C.ROOT / "scripts" / "read_site_rates.mjs"
REGION = {"uk": ("gb", "UK"), "gb": ("gb", "UK"), "us": ("us", "US"), "ca": ("ca", "Canada"), "au": ("au", "Australia"),
          "ie": ("ie", "Ireland"), "nz": ("nz", "New Zealand"), "in": ("in", "India"), "eu": ("eu", "EU")}
YEAR = re.compile(r"^(?:19|20)\d\d(?:[-/](?:\d\d){1,2})?$")
PERCENT_KEY = re.compile(r"(?i)(rate|percent|surcharge|supplement)s?$")
BAND_LIMIT = ("upTo", "upto", "to", "limit", "max", "threshold")
TABLE_MAX = 40  # a lookup table (160 currencies) is a calculator's input, not something an article states
# a comment's notes for whoever maintains the file, not facts: "Check after every Budget", "upTo: Infinity"
UPKEEP = re.compile(r"(?i)^(check|refresh|update|change|add|move|keep|todo|note to)\b|\bupTo\b|`|\bInfinity\b|"
                    r"\btests?/|\.(?:ts|js)\b|\bthis file\b")


def load(dir_: str | Path) -> dict:
    """{module path: {export: value}} from the site's rate modules; {} when Node or the folder is missing."""
    node = shutil.which("node")
    d = Path(str(dir_)).expanduser()
    if not node or not d.is_dir():
        return {}
    try:
        r = subprocess.run([node, "--no-warnings", str(READER), str(d)], capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
        return json.loads(r.stdout or "{}")
    except (subprocess.SubprocessError, ValueError, OSError):
        return {}


def comments(src: str) -> tuple[str, dict[str, str]]:
    """The module's opening doc comment, and each export's or field's own doc comment (`/** ... */` right above
    `export const name` or `  name:`)."""
    docs, head = {}, ""
    for m in re.finditer(r"/\*\*(.*?)\*/\s*(?:export\s+(?:const|let|type|interface)\s+)?([A-Za-z_]\w*)?", src, re.S):
        text = " ".join(re.sub(r"^\s*\*\s?", "", ln) for ln in m.group(1).splitlines()).strip()
        text = re.sub(r"\s*\((?:decision|see) [^)]*\)", "", " ".join(text.split()))
        text = " ".join(x for x in re.split(r"(?<=[.!?])\s+", text) if not UPKEEP.search(x))
        if not head and m.start() == len(src) - len(src.lstrip()):
            head = text
        if m.group(2):
            docs.setdefault(m.group(2), text)
    return head, docs


def words(key: str) -> str:
    """`personalAllowance` → "personal allowance", `sdlt` → "SDLT", `plan2` → "plan 2"."""
    from .plan import ACRONYMS
    w = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Za-z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", key).replace("_", " ")
    return " ".join(ACRONYMS.get(x.lower(), x.upper() if not re.search(r"[aeiouy]", x, re.I) and x.isalpha() and len(x) <= 5
                                 else x.lower()) for x in w.split())


def _num(v, pct: bool = False) -> str:
    if v == "Infinity":
        return "no limit"
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,}".rstrip("0").rstrip(".")
    return s + ("%" if pct else "")


def _bands(rows: list) -> str | None:
    lim = next((k for k in BAND_LIMIT if all(isinstance(r, dict) and k in r for r in rows)), None)
    if not rows or not lim or not all("rate" in r for r in rows):
        return None
    out, prev = [], None
    for r in rows:
        if r[lim] == "Infinity":
            out.append(f"{_num(r['rate'], True)} above {_num(prev)}" if prev is not None else f"{_num(r['rate'], True)}")
        else:
            out.append(f"{_num(r['rate'], True)} up to {_num(r[lim])}")
            prev = r[lim]
    return ", ".join(out)


def render(v, docs: dict, key: str = "", pct: bool = False) -> str:
    """A value as the plain words a writer reads: bands as "20% up to 37,700, 40% up to 125,140, 45% above
    125,140", a field with its comment in brackets."""
    pct = pct or bool(PERCENT_KEY.search(key))
    if isinstance(v, list):
        return _bands(v) or "; ".join(render(x, docs, key, pct) for x in v)
    if isinstance(v, dict):
        parts = []
        for k, x in v.items():
            note = f" ({docs[k].rstrip('.')})" if docs.get(k) else ""
            body = render(x, docs, k, pct)
            parts.append(f"{words(k)}{note}: {body}" if not isinstance(x, dict) else f"{words(k)}{note}: [{body}]")
        return "; ".join(parts)
    return _num(v, pct)


def _sources(exports: dict) -> list[dict]:
    out = []
    for k, v in exports.items():
        if re.search(r"Sources?$", k):
            out += [s for s in (v if isinstance(v, list) else [v]) if isinstance(s, dict) and s.get("url")]
    return out


def _stems(text: str) -> set[str]:
    return {w[:4] for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) >= 3 or w.isdigit()}


def _pick_source(sources: list[dict], name: str, year: str = "", note: str = "") -> dict:
    """The source a value was checked against: the one sharing the export's rarest words (its name, its comment, its
    year), so "studentLoanInterest" finds the interest announcement, not the write-off page beside it."""
    want = _stems(f"{words(name)} {note}")
    if year:
        a, _, b = year.partition("-")
        want |= {a[:4], ((a[:2] + b) if len(b) == 2 else b)[:4]}
    toks = [_stems(f"{s.get('name')} {s.get('url')}") for s in sources]
    df = {w: sum(w in t for t in toks) for w in want}
    score = lambda i: sum(1 / df[w] for w in want & toks[i])
    return sources[max(range(len(sources)), key=score)] if sources else {}


def registry(path: str | Path | None) -> dict[str, dict]:
    """{module path: {"terms": [...], "pages": [...]}} from a rate register: `### topic` sections whose "Lives in"
    names src/data/rates/<module>, with quoted search terms and calculator page slugs."""
    p = Path(str(path or "")).expanduser()
    if not path or not p.is_file():
        return {}
    out: dict[str, dict] = {}
    for sec in re.split(r"\n(?=### )", p.read_text(encoding="utf-8")):
        mods = re.findall(r"rates/([\w/.-]+\.(?:ts|mts|js|mjs))", sec)
        if not mods:
            continue
        find = " ".join(re.findall(r"\*\*Find in articles:\*\*([^\n]*)", sec))
        terms = [t for t in re.findall(r"\"([^\"]+)\"", find) if re.search(r"[A-Za-z]{3}", t)]
        pages = re.findall(r"\b([a-z0-9]+(?:-[a-z0-9]+)*-calculator)\b", sec)
        for m in mods:
            e = out.setdefault(m, {"terms": [], "pages": []})
            e["terms"] = list(dict.fromkeys(e["terms"] + terms))
            e["pages"] = list(dict.fromkeys(e["pages"] + pages))
    return out


def _terms(module: str, exports: dict, reg: dict) -> tuple[list[str], list[str]]:
    """(names, all terms): the module's own names (its file, its exports, the register's multi-word or capitalised
    terms such as "Personal Allowance" or "SDLT") name the topic in a query; a plain word from the register
    ("interest") only counts in the page's own text."""
    stem = Path(module).stem.replace("-", " ")
    t = [stem] + ([stem[:-1]] if stem.endswith("s") else [])
    t += [words(k).lower() for k in exports if len(words(k).split()) >= 2 and not re.search(r"(?i)sources?$|names?$", k)]
    reg_t = [x for x in (reg.get("terms") or []) if x.strip()]
    names = t + [x for x in reg_t if len(x.split()) >= 2 or re.search(r"[A-Z]", x)]
    return list(dict.fromkeys(names)), list(dict.fromkeys(t + reg_t))


def applies(module: str, exports: dict, reg: dict, strong: str, slug: str, live: str) -> bool:
    """The page is about this module when one of its names is in the page's query, H1, title, headings or address,
    the register names its page, or its live text uses the module's terms (two different ones, or one three times)."""
    names, terms = _terms(module, exports, reg)
    hit = lambda t, s: len(re.findall(rf"(?i)(?<![\w-]){re.escape(t)}(?![\w-])", s))
    if slug and slug in (reg.get("pages") or []):
        return True
    if any(hit(t, strong) for t in names):
        return True
    counts = [hit(t, live) for t in terms if len(t) >= 4]
    return sum(1 for c in counts if c) >= 2 or max(counts, default=0) >= 3


def facts_for(brief: dict, page_info: dict | None = None, live_text: str = "", data: dict | None = None,
              sources: dict | None = None) -> list[dict]:
    """The site's rates that apply to this page, as verified facts. `data` and `sources` (module path → TS source
    text) are for tests; a run reads the folder named in the client profile."""
    root = brief.get("site_rates_dir")
    if not root and data is None:
        return []
    data = data if data is not None else load(root)
    reg = registry(brief.get("site_rates_registry"))
    pi = page_info or {}
    url = str(brief.get("page_url") or pi.get("url") or "")
    slug = url.rstrip("/").rsplit("/", 1)[-1].lower() if url else ""
    strong = " | ".join(str(x) for x in [brief.get("target_query"), brief.get("h1"), pi.get("h1"), pi.get("title"),
                                         slug.replace("-", " ")] + list(pi.get("h2") or []) if x)
    scope = str(brief.get("scope") or "global").lower()
    out = []
    for module, exports in sorted(data.items()):
        if not isinstance(exports, dict) or "__error" in exports:
            continue
        region = REGION.get(module.split("/")[0].lower()) if "/" in module else None
        if region and scope not in ("global", "", region[0]):
            continue  # a UK rate never reaches a page written for the US
        if not applies(module, exports, registry_entry(reg, module), strong, slug, live_text):
            continue
        src = (sources or {}).get(module)
        if src is None and root:
            try:
                src = (Path(str(root)).expanduser() / module).read_text(encoding="utf-8")
            except OSError:
                src = ""
        head, docs = comments(src or "")
        srcs = _sources(exports)
        current = next((v for k, v in exports.items() if re.match(r"(?i)current", k) and isinstance(v, str)), "")
        topic = words(Path(module).stem.replace("-", "_"))
        where = f"{region[1]}, " if region else ""
        for name, v in exports.items():
            if re.search(r"Sources?$", name) or isinstance(v, (str, int, float)) and re.match(r"(?i)current", name):
                continue
            if isinstance(v, dict) and sum(1 for x in v.values() if not isinstance(x, (dict, list))) > TABLE_MAX:
                continue
            if isinstance(v, dict) and v and all(isinstance(x, str) for x in v.values()):
                continue  # display labels ("plan4": "Plan 4 (Scotland)"), not figures
            note = docs.get(name, "")
            years = [k for k in v if YEAR.match(k)] if isinstance(v, dict) else []
            parts = [(k, v[k]) for k in years] if years and len(years) == len(v) else [("", v)]
            for year, val in parts:
                s = _pick_source(srcs, name, year, note) or {}
                label = words(name) + (f" {year}" + (" (the current year)" if year == current else "") if year else "")
                lead = label if _stems(topic) <= _stems(label) else f"{topic}, {label}"
                value = f"{lead}: {render(val, docs, name)}" + (f". {note}" if note else "")
                out.append({"id": f"rates:{Path(module).stem}:{name}" + (f":{year}" if year else ""),
                            "claim": f"{brief.get('client') or 'the site'}'s own rates data ({where}{topic}; what its "
                                     f"calculators use, checked against {s.get('name') or 'the official source'} on "
                                     f"{s.get('lastChecked') or 'the date in the file'})"
                                     + (f". {head}" if head and head != note else ""),
                            "value": value, "status": "verified", "basis": "site_rates", "verified": True,
                            "source_url": s.get("url"), "retrieved_at": s.get("lastChecked") or C.now_iso(),
                            **({"scope": region[1]} if region else {}),
                            **({"meaning": head} if head and head != note else {}),
                            **({"condition": f"tax or academic year {year}"} if year else {})})
    return out


def registry_entry(reg: dict, module: str) -> dict:
    return reg.get(module) or next((v for k, v in reg.items() if k.endswith(module) or module.endswith(k)), {})


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    """Every figure as a bare number: "£12,570" and "12,570" are both "12570"."""
    out = set()
    for m in NUM.findall(str(text or "")):
        n = m.replace(",", "").rstrip(".")
        out.add(n[:-2] if n.endswith(".0") else n)
    return out
