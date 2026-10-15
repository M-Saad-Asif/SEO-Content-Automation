"""Shared language helpers, niche-free: one way to turn text into comparable tokens and to spot places.

Every plugin and check that compares queries, headings or sentences uses these, so "backpacks"/"backpack",
"e-visa"/"evisa", "travelling"/"travel" and "British"/"UK" behave the same everywhere. Niche vocabulary
(e.g. "carry-on" = "cabin" for a luggage shop) never lives here: it comes from the client profile or brief as
`synonyms:` and is passed in.
"""
from __future__ import annotations

import re
import threading
from functools import lru_cache

_NLP = None
_LOAD = threading.RLock()


def import_spacy():
    """Import spaCy without its optional PyTorch backend: the small English model runs on spaCy's own CPU ops, and
    importing torch costs about ten seconds on every pipeline command where it happens to be installed."""
    import sys
    with _LOAD:  # plugins import in parallel threads: the torch stub must not be set and removed by two at once
        if "spacy" in sys.modules:
            return sys.modules["spacy"]
        if "torch" not in sys.modules:
            sys.modules["torch"] = None  # thinc then treats torch as absent
            try:
                import spacy
            finally:
                sys.modules.pop("torch", None)
            return spacy
        import spacy
        return spacy


def _nlp():
    """The model, loaded once. Plugins run in parallel threads: two loading at once can fail, and one failure would
    switch the whole run to plain rules, so loading is serialised and retried once."""
    global _NLP
    if _NLP is None:
        with _LOAD:
            if _NLP is None:
                try:
                    _NLP = import_spacy().load("en_core_web_sm", disable=["ner", "parser"])
                except Exception:
                    _NLP = import_spacy().load("en_core_web_sm", disable=["ner", "parser"])
    return _NLP


def normalise(text: str) -> str:
    """Lower-case and spelling-level unification that holds in every niche."""
    s = (text or "").lower().replace("’", "'")
    s = re.sub(r"\bu\.s\.(a\.)?|\bu\.s\b", "us", s)
    s = re.sub(r"\bu\.k\.?", "uk", s)
    s = re.sub(r"(?<=\w)[-‐–/](?=\w)", " ", s)               # carry-on, e-visa, 3-3-3
    s = re.sub(r"\b([b-hj-z])\s+(?=[a-z]{3,})", r"\1", s)     # "e visa" -> "evisa", "e mail" -> "email" (not a/i)
    s = re.sub(r"\b\d(?:\s+\d\b){2,}", lambda m: m.group(0).replace(" ", ""), s)  # 5 4 3 2 1 -> 54321
    # units: "100g" = "100 grams" = "100 g"; "1.6mm" = "1.6 millimetres"
    s = re.sub(r"(\d)(mg|kg|g|mm|cm|km|m|ml|l|kcal|lbs?|oz)\b", r"\1 \2", s)
    for words, unit in ((r"milligrams?|milligrammes?", "mg"), (r"kilograms?|kilogrammes?|kilos?", "kg"),
                        (r"grams?|grammes?", "g"), (r"millimet(?:re|er)s?", "mm"), (r"centimet(?:re|er)s?", "cm"),
                        (r"kilomet(?:re|er)s?", "km"), (r"millilit(?:re|er)s?", "ml"), (r"lit(?:re|er)s?", "l"),
                        (r"per cent|percent", "%")):
        s = re.sub(rf"(?<=\d)\s*(?:{words})\b", " " + unit, s)
    sp = _spelling()
    if sp:
        s = re.sub(r"[a-z]+", lambda m: sp.get(m.group(0), m.group(0)), s)
    return s


_SPELL = None


def _spelling() -> dict:
    """US -> UK single-word spellings from the lexicon, so both spellings match each other (never shown to readers)."""
    global _SPELL
    if _SPELL is None:
        try:
            from . import common as C
            _SPELL = {k: v for k, v in (C.lexicon().get("us_to_uk") or {}).items()
                      if " " not in k and " " not in v and k.isalpha() and v.isalpha() and k.islower()}
        except Exception:
            _SPELL = {}
    return _SPELL


_KEEP = {"news", "this", "his", "has", "was", "is", "us", "bus", "gas", "yes", "series", "species", "always", "less",
          "process", "access", "business", "address", "analysis", "basis", "crisis", "plus", "bonus", "status", "virus",
          "campus", "census", "thus", "during", "something", "nothing", "anything", "everything", "morning", "evening",
          "bring", "thing", "king", "ring", "spring", "string", "ceiling", "need", "seed", "feed", "speed", "bed", "red"}


def _rule_lemma(w: str) -> str:
    """A plain-rules lemma for when spaCy is unavailable: plural and verb endings only, the cases that decide whether
    "bags"/"bag" or "planting"/"plant" compare equal. Both sides of every comparison use the same function."""
    if len(w) <= 3 or w in _KEEP or not w.isalpha():
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("sses", "shes", "ches", "xes", "zes")) or (w.endswith("oes") and len(w) > 5):
        return w[:-2]  # boxes -> box, tomatoes -> tomato (shoes, toes keep their "e")
    if w.endswith("s") and not w.endswith(("ss", "us", "is", "ous", "ics")):
        return w[:-1]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            stem = w[: -len(suf)]
            if len(stem) > 3 and stem[-1] == stem[-2] and stem[-1] not in "lsz":
                stem = stem[:-1]  # planned -> plan, stopping -> stop
            return stem
    return w


_NO_SPACY = False
_LEMMA: dict[str, tuple] = {}  # normalised string -> lemmas; filled one at a time or in batches by prime()
_LEMMA_LOCK = threading.Lock()


def _model():
    global _NO_SPACY
    if _NO_SPACY:
        return None
    try:
        return _nlp()
    except Exception:  # spaCy missing, or its compiled library blocked on this machine
        _NO_SPACY = True
        return None


def _from_doc(doc) -> tuple:
    out = []
    for t in doc:
        if t.is_space or t.is_punct:
            continue
        w = t.text
        if t.pos_ in ("NOUN", "VERB", "AUX") and t.lemma_ and t.lemma_ != "-PRON-":
            w = t.lemma_.lower()
        out.append(w)
    return tuple(out)


def _lemmas(s: str) -> tuple:
    hit = _LEMMA.get(s)
    if hit is not None:
        return hit
    model = _model()
    if model is None:
        res = tuple(_rule_lemma(w) for w in re.findall(r"[a-z0-9£$€%]+(?:'[a-z]+)?", s))
    else:
        res = _from_doc(model(s))
    with _LEMMA_LOCK:
        if len(_LEMMA) > 200000:
            _LEMMA.clear()
        _LEMMA[s] = res
    return res


def _prepared(text: str, synonyms: dict | None) -> str:
    s = normalise(text)
    for k, v in sorted((synonyms or {}).items(), key=lambda kv: -len(kv[0])):
        s = re.sub(rf"\b{re.escape(normalise(k))}\b", normalise(v), s)
    return s


def prime(texts, synonyms: dict | None = None) -> None:
    """Lemmatise many strings in one batched model pass. A model call per short string (URL slugs, headings,
    queries) costs ~6 ms of fixed overhead each; thousands of them dominated the research step. Same lemmas,
    same tokens: only the batching differs."""
    model = _model()
    if model is None:
        return
    todo = list(dict.fromkeys(s for s in (_prepared(t, synonyms) for t in texts if t) if s and s not in _LEMMA))
    if not todo:
        return
    docs = list(model.pipe(todo, batch_size=512))
    with _LEMMA_LOCK:
        for s, d in zip(todo, docs):
            _LEMMA[s] = _from_doc(d)


@lru_cache(maxsize=100000)
def _tokens(text: str, syn_key: tuple) -> tuple:
    toks = list(_lemmas(_prepared(text, dict(syn_key))))
    return tuple(geo_canon(w, " ".join(toks[max(0, i - 1): i + 3])) or w for i, w in enumerate(toks))


def tokens(text: str, synonyms: dict | None = None) -> list[str]:
    """Lemmatised tokens; `synonyms` maps a token (or phrase) to its canonical form for this client."""
    try:
        key = tuple(sorted((synonyms or {}).items()))
        hash(key)
    except TypeError:  # unhashable synonym values: no caching for this call
        toks = list(_lemmas(_prepared(text, synonyms)))
        return [geo_canon(w, " ".join(toks[max(0, i - 1): i + 3])) or w for i, w in enumerate(toks)]
    return list(_tokens(text or "", key))


def same_stem(a: str, b: str) -> bool:
    """clean/cleaner, pack/packing: same topic word for routing purposes."""
    return len(a) > 3 and len(b) > 3 and a[:5] == b[:5]


# ------------------------------------------------------------------ places (world data, not niche data)

# Demonyms and short names people type that pycountry doesn't carry. Irregular forms only; regular ones
# ("canadian", "italian", "pakistani") are matched by suffix below.
_IRREGULAR = {
    "uk": "GB", "britain": "GB", "british": "GB", "england": "GB", "english": "GB", "scotland": "GB", "scottish": "GB",
    "wales": "GB", "welsh": "GB", "us": "US", "usa": "US", "america": "US", "american": "US", "uae": "AE",
    "emirati": "AE", "ksa": "SA", "dutch": "NL", "holland": "NL", "swiss": "CH", "french": "FR", "irish": "IE",
    "greek": "GR", "thai": "TH", "turkish": "TR", "turkey": "TR", "danish": "DK", "swedish": "SE", "finnish": "FI",
    "polish": "PL", "spanish": "ES", "portuguese": "PT", "chinese": "CN", "japanese": "JP", "vietnamese": "VN",
    "filipino": "PH", "kiwi": "NZ", "south korean": "KR", "korean": "KR", "russian": "RU", "czech": "CZ",
    "schengen": "EU", "eu": "EU", "europe": "EU", "european": "EU",
    "german": "DE", "germany": "DE", "norwegian": "NO", "mexican": "MX", "brazilian": "BR", "saudi": "SA",
    "aussie": "AU", "australian": "AU", "nz": "NZ", "aus": "AU", "canadian": "CA", "emirates": "AE", "americans": "US", "brits": "GB",
}
# English words that are also country codes or names: only places when the context says so
_AMBIGUOUS = {"us", "in", "it", "is", "at", "be", "no", "to", "my", "me", "am", "an", "as", "by", "do", "go", "he",
              "hi", "id", "la", "so", "or", "of", "on", "ma", "mo", "pa", "co", "ca", "de", "es", "il", "ms", "mt",
              "chad", "jersey", "georgia", "guinea", "jordan", "turkey", "china", "chile", "niger", "cuba", "malta"}
# an ambiguous word ("us", "jersey") is a place only next to words that talk about places or people from them
_PLACE_CONTEXT = re.compile(r"\b(citizens?|nationals?|passports?|residents?|embassy|consulate|government|border|"
                            r"from|to|in|the|visit|visiting|travel|travelling|living|moving)\b")


@lru_cache(maxsize=1)
def _gazetteer() -> dict:
    g = dict(_IRREGULAR)
    try:
        import pycountry
    except ImportError:
        return g
    for c in pycountry.countries:
        for n in {c.name, getattr(c, "common_name", None), getattr(c, "official_name", None)}:
            if n:
                g.setdefault(normalise(re.sub(r",.*$", "", n)), c.alpha_2)
    # three-letter codes ("can", "and", "per") and local-script subdivision names cause more harm than good
    return g


def geo_canon(word: str, context: str = "") -> str | None:
    """'british' -> 'gb', 'indian' -> 'in', 'dubai' -> 'ae': a place token in canonical lower-case form, else None."""
    w = word.lower()
    g = _gazetteer()
    code = g.get(w)
    if code is None and len(w) > 4:
        for suf, rep in (("ian", "ia"), ("ian", "y"), ("ian", ""), ("an", "a"), ("an", ""), ("ese", ""), ("ese", "a"),
                         ("i", ""), ("i", "istan"), ("ish", ""), ("er", "")):
            if w.endswith(suf):
                code = g.get(w[: len(w) - len(suf)] + rep)
                if code:
                    break
    if code is None:
        return None
    if w in _AMBIGUOUS and not (context and _PLACE_CONTEXT.search(context)):
        return None
    return "geo:" + code.lower()


def places(text: str) -> set[str]:
    """Canonical place tokens in a text, including two-word names ("new zealand", "abu dhabi")."""
    s = normalise(text)
    words = re.findall(r"[a-z0-9]+", s)
    out = set()
    for i, w in enumerate(words):
        two = " ".join(words[i:i + 2])
        ctx = " ".join(words[max(0, i - 1): i + 3])
        hit = geo_canon(two, ctx) if len(words) > i + 1 and two in _gazetteer() else None
        hit = hit or geo_canon(w, ctx)
        if hit:
            out.add(hit)
    return out


def place_slugs(code: str) -> set[str]:
    """URL slug forms for a place: 'geo:gb' -> {'united-kingdom', 'uk', 'gb', 'great-britain'}."""
    c = code.split(":")[-1].upper()
    names = {k for k, v in _gazetteer().items() if v == c}
    return {re.sub(r"[^a-z0-9]+", "-", n).strip("-") for n in names} | {c.lower()}
