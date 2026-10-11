"""Vertical check: do the client's bags fit airline size limits?

Compares each product's listed dimensions with every `kind: bag_limit` fact
in the fact sheet. Both triples are sorted largest-first, so a bag may be
turned any way (standard box-fit test). Margins are per sorted dimension.
Only facts with a usable status are compared; others give "unknown".

The writer must use these results, not reason about fit itself.
"""
from __future__ import annotations

USABLE = {"verified", "captured", "operator"}


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def _dims(cm) -> str:
    return " × ".join(_fmt(x) for x in cm) + " cm"


def _parse_limit(value: str):
    import re
    s = value.replace("×", "x")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:cm)?\s*x\s*(\d+(?:\.\d+)?)\s*(?:cm)?\s*x\s*(\d+(?:\.\d+)?)", s)
    return [float(x) for x in m.groups()] if m else None


def run(sheet: dict, brief: dict) -> dict:
    limits = []
    for f in sheet.get("facts", []):
        if f.get("kind") != "bag_limit":
            continue
        cm = _parse_limit(f.get("value", ""))
        if not cm:
            continue
        limits.append({"id": f["id"], "carrier": f.get("carrier", ""), "allowance": f.get("allowance", f.get("claim")),
                       "cm": cm, "status": f.get("status"), "condition": f.get("condition", ""),
                       "source_url": f.get("source_url")})
    results, questions, lines = [], [], []
    for p in sheet.get("products", []):
        d = p.get("dims")
        name = p["display_name"]
        if not d:
            questions.append(f"{name} lists no dimensions, so it is left out of fit statements.")
            continue
        bag = sorted(d["cm"], reverse=True)
        doubtful = min(bag) < 5
        if doubtful:
            questions.append(f"{name} is listed as {d['raw']}; a side under 5 cm is implausible, so no fit claim is made for it.")
        if d.get("irregular"):
            questions.append(f"{name} has an irregular listed shape ({d['raw']}); fit uses its widest point.")
        for lim in limits:
            box = sorted(lim["cm"], reverse=True)
            margins = [round(b - x, 1) for x, b in zip(bag, box)]
            if doubtful:
                verdict = "dims_doubtful"
            elif lim["status"] not in USABLE:
                verdict = "unknown"
            else:
                verdict = "fits" if all(m >= 0 for m in margins) else "too_big"
            zero = [i for i, m in enumerate(margins) if m == 0]
            over = [i for i, m in enumerate(margins) if m < 0]
            r = {
                "product": name, "product_url": p["url"], "bag_cm": d["cm"], "bag_sorted": bag,
                "limit_id": lim["id"], "carrier": lim["carrier"], "allowance": lim["allowance"],
                "limit_cm": lim["cm"], "limit_status": lim["status"], "verdict": verdict,
                "margins_sorted_cm": margins, "zero_margin": bool(zero) and verdict == "fits",
                "expandable": d.get("expandable", False), "irregular": d.get("irregular", False),
                "condition": lim["condition"],
            }
            words = ["longest side", "middle side", "shortest side"]
            if verdict == "fits":
                spare = ", ".join(f"{_fmt(m)} cm spare on the {words[i]}" for i, m in enumerate(margins))
                note = f"fits ({spare})"
                if zero:
                    note += "; no room at all on the " + " and ".join(words[i] for i in zero)
                if d.get("expandable"):
                    note += "; measured unexpanded"
            elif verdict == "too_big":
                note = "too big: " + ", ".join(f"{words[i]} {_fmt(bag[i])} cm vs {_fmt(box[i])} cm" for i in over)
            elif verdict == "dims_doubtful":
                note = "no fit claim: the listed dimensions are implausible"
            else:
                note = f"unknown (limit status: {lim['status']})"
            r["note"] = note
            results.append(r)
            lines.append(f"{name} {_dims(d['cm'])} vs {lim['carrier']} {lim['allowance']} {_dims(lim['cm'])}"
                         f"{' ' + lim['condition'] if lim['condition'] else ''}: {note}")
    fits = sum(1 for r in results if r["verdict"] == "fits")
    big = sum(1 for r in results if r["verdict"] == "too_big")
    unk = sum(1 for r in results if r["verdict"] == "unknown")
    # Counts and rankings the writer copies instead of counting or ranking by eye.
    by_limit = {}
    for r in results:
        if r["verdict"] == "fits":
            by_limit.setdefault(f"{r['carrier']} {r['allowance']}", []).append(r["product"])
    fit_lists = {k: sorted(set(v)) for k, v in by_limit.items()}
    weights = sorted(((p["weight_kg"], p["display_name"]) for p in sheet.get("products", []) if p.get("weight_kg")))
    no_weight = [p["display_name"] for p in sheet.get("products", []) if not p.get("weight_kg")]
    attrs = {}
    for p in sheet.get("products", []):
        sp = {k.lower(): v for k, v in (p.get("specs") or {}).items()}
        attrs[p["display_name"]] = {"weight_kg": p.get("weight_kg"), "wheels": sp.get("wheels"),
                                    "material": sp.get("material"), "dims": p["dims"]["cm"] if p.get("dims") else None}
    return {
        "summary": f"{len(results)} comparisons: {fits} fit, {big} too big, {unk} unknown",
        "method": "sorted box fit using listed (manufacturer) dimensions; soft bags packed full can measure larger",
        "lines": lines,
        "results": results,
        "fit_lists": fit_lists,
        "weight_ranking": [{"product": n, "weight_kg": w} for w, n in weights],
        "weight_not_listed": no_weight,
        "attributes": attrs,
        "decisions": questions,
    }
