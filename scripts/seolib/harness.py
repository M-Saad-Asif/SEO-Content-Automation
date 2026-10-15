"""Plugin harness: every pipeline stage is a plugin in plugins/<name>/.

A plugin folder holds plugin.yaml (the manifest) and one or both of:
  run.py    def run(ctx) -> dict      (script stage; deterministic)
  SKILL.md  instructions             (agent stage; the host agent does it)

Manifest fields: name, kind (script|agent), description, needs [plugins],
modes [deep, quick], budget_s, outputs [files]. The harness runs script
stages in dependency waves (stages in one wave run in parallel), saves each
result to runs/<run>/research/<name>.json, and records timing and Serper credits.
Swap a stage by editing or replacing its folder; nothing else changes.
"""
from __future__ import annotations

import importlib.util
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import common as C

PLUGINS = C.ROOT / "plugins"


def manifests() -> dict[str, dict]:
    out = {}
    for p in sorted(PLUGINS.glob("*/plugin.yaml")):
        m = C.load_yaml(p)
        m["_dir"] = p.parent
        out[m["name"]] = m
    return out


class Ctx:
    def __init__(self, brief: dict, rd: Path, mode: str, refresh: bool = False):
        self.brief, self.rd, self.mode, self.refresh = brief, rd, mode, refresh
        self.dir = rd / "research"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.decisions: list[str] = []
        self.credits = 0

    def deep(self) -> bool:
        return True  # one mode: every run reads as widely as the old deep mode did

    @property
    def task(self) -> str:
        return self.brief.get("task") or "new"

    def connector_on(self, name: str) -> bool:
        """Connectors run when the brief lists them, or when `connectors: auto` (the default) and they are configured."""
        c = self.brief.get("connectors", "auto")
        return c == "auto" or (isinstance(c, list) and name in c)

    def load(self, name: str) -> dict:
        if name == "foundation":
            return {"sheet": C.load_json(self.rd / "fact_sheet.json") or {},
                    "link_map": C.load_json(self.rd / "link_map.json") or {}}
        return C.load_json(self.dir / f"{name}.json") or {}

    def decide(self, text: str) -> None:
        self.decisions.append(text)

    def raw(self, name: str) -> dict | None:
        """Raw data the agent fetched through an MCP server and stored with `seo.py ingest`."""
        return C.load_json(self.dir / "raw" / f"{name}.json")


def applies(m: dict, brief: dict, mode: str) -> bool:
    if m.get("kind") != "script" or "deep" not in m.get("modes", ["deep", "quick"]):
        return False
    w = m.get("when") or {}
    return not w.get("task") or (brief.get("task") or "new") in ([w["task"]] if isinstance(w["task"], str) else w["task"])


def _run_one(m: dict, ctx: Ctx) -> tuple[str, dict, float]:
    t0 = time.time()
    spec = importlib.util.spec_from_file_location(f"plugin_{m['name']}", m["_dir"] / "run.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        res = mod.run(ctx) or {}
    except Exception as e:
        res = {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
    if m["name"] != "foundation":
        C.save_json(ctx.dir / f"{m['name']}.json", res)
    return m["name"], res, time.time() - t0


def run_research(brief_path: str, mode: str = "deep", refresh: bool = False, mark_start: bool = True) -> Path:
    from .prep import load_brief, run_dir
    from .timing import mark
    brief = load_brief(brief_path)
    mode = "deep"  # one mode: every research plugin, every run
    rd = run_dir(brief)
    rd.mkdir(parents=True, exist_ok=True)
    if mark_start:  # a background run was marked by `next` when it started it
        mark(rd, "prep", "start", fresh=True)
    from . import serper
    serper.start_run()  # at most 3 paid searches this run (seolib/serper.py); cached answers are free
    ctx = Ctx(brief, rd, mode, refresh)
    ms = {n: m for n, m in manifests().items() if applies(m, brief, mode)}
    done, times = _run_waves(ms, ctx)
    s = serper.spent()
    if s["refused"]:
        ctx.decide(f"Serper credit cap ({s['cap']} a run): {len(s['refused'])} search(es) skipped: "
                   + "; ".join(s["refused"][:5]))
    _finish(rd, ctx, done, times, mode)
    return rd


def _run_waves(ms: dict, ctx: Ctx, done: dict | None = None) -> tuple[dict, dict]:
    """Each plugin starts as soon as its own dependencies have finished, not when a whole wave has: a slow source
    fetch in one plugin (official_facts) no longer holds back the plugins that never needed it."""
    from concurrent.futures import FIRST_COMPLETED, wait
    done = dict(done or {})
    times: dict[str, float] = {}
    pending = {n: m for n, m in ms.items() if n not in done}
    running = {}
    with ThreadPoolExecutor(max_workers=max(1, len(pending))) as ex:
        while pending or running:
            ready = [m for n, m in pending.items() if all(d in done or d not in ms for d in m.get("needs", []))]
            for m in ready:
                running[ex.submit(_run_one, m, ctx)] = m["name"]
                pending.pop(m["name"])
            if not running:
                raise SystemExit(f"plugin dependency cycle among {list(pending)}")
            finished, _ = wait(running, return_when=FIRST_COMPLETED)
            for fut in finished:
                running.pop(fut)
                name, res, secs = fut.result()
                done[name], times[name] = res, round(secs, 1)
    return done, times


def rerun_dependents(rd: Path, brief: dict, name: str) -> None:
    """After `seo.py ingest`, re-run every script plugin downstream of `name` and rebuild the pack."""
    sheet = C.load_json(rd / "fact_sheet.json") or {}
    mode = (sheet.get("research") or {}).get("mode", "deep")
    ctx = Ctx(brief, rd, mode)
    ms = {n: m for n, m in manifests().items() if applies(m, brief, mode)}
    down, grew = {name}, True
    while grew:
        grew = False
        for n, m in ms.items():
            if n not in down and set(m.get("needs", [])) & down:
                down.add(n)
                grew = True
    keep = {n: ctx.load(n) for n in ms if n not in down}
    done, times = _run_waves(ms, ctx, keep)
    _finish(rd, ctx, done, times, mode, mark_timing=False)


def _finish(rd: Path, ctx: Ctx, done: dict, times: dict, mode: str, mark_timing: bool = True) -> None:
    from .timing import mark
    from .pack import research_pack
    sheet = C.load_json(rd / "fact_sheet.json")
    errors = {n: r["error"] for n, r in done.items() if isinstance(r, dict) and r.get("error")}
    for n, e in errors.items():
        ctx.decide(f"Plugin {n} failed ({e}); the run continues without it.")
    for n, r in done.items():
        if isinstance(r, dict) and r.get("not_configured"):
            ctx.decide(f"Connector {n} not configured ({r['not_configured']}); its MCP route or a later run can add it.")
    found = (sheet.get("decisions") or []) + ctx.decisions + \
        [d for r in done.values() if isinstance(r, dict) for d in r.get("decisions", [])]
    sheet["decisions"] = list(dict.fromkeys(found))
    prev = sheet.get("research") or {}
    sheet["research"] = {"mode": mode, "plugin_seconds": {**prev.get("plugin_seconds", {}), **times},
                         "serper_credits": prev.get("serper_credits", 0) * (not mark_timing) + ctx.credits,
                         "errors": errors, "task": ctx.task}
    C.save_json(rd / "fact_sheet.json", sheet)
    research_pack(rd)
    if mark_timing:
        mark(rd, "prep", "end")
    _summary(rd, sheet, done, times, ctx)


def _summary(rd: Path, sheet: dict, done: dict, times: dict, ctx: Ctx) -> None:
    seo = (C.ROOT / "scripts" / "seo.py").as_posix()
    print(f"RUN {rd.resolve().as_posix()}  mode={ctx.mode}  serper credits={ctx.credits}")
    for n in done:
        r = done[n] or {}
        if n not in times:
            continue
        status = r.get("error") or (f"not configured: {r['not_configured']}" if r.get("not_configured") else None) \
            or (f"skipped: {r['skipped']}" if isinstance(r.get("skipped"), str) else None) \
            or ("from MCP (ingested)" if r.get("source") == "mcp" else r.get("summary", ""))
        print(f"  {n:18s} {times[n]:5.1f}s  {status}")
    print(f"decisions logged: {len(sheet.get('decisions') or [])}")
    print(f"next: read {(rd / 'writer_pack.md').resolve().as_posix()}"
          + (f", write {(rd / 'outline.md').resolve().as_posix()} and run `python \"{seo}\" outline \"{rd.resolve().as_posix()}\"`"
             if ctx.mode == "deep" else "")
          + f", then write {(rd / 'draft.md').resolve().as_posix()}")
