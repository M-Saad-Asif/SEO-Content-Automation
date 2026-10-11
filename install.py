#!/usr/bin/env python3
"""Set up the page-SEO pipeline on this machine with one command, after `git clone`:

    python install.py          # Windows      (or double-click install.cmd)
    python3 install.py         # macOS, Linux (or ./install.sh)

It installs the Python packages and the spaCy English model, asks for the API keys and writes them to .env (never
committed), installs the /page-seo command into every coding agent it finds (Claude Code, Cursor, Codex,
Antigravity, Gemini CLI, Windsurf, GitHub Copilot) pointing at this folder, and runs the setup check.

    python install.py --keys        # only (re)enter the API keys
    python install.py --yes         # no questions: keys come from SERPER_API_KEY / SPIDER_API_KEY in the environment
    python install.py --no-agents   # skip installing the /page-seo command

Run it again after moving this folder or pulling a new version: everything it does is safe to repeat.
"""
from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
KEYS = [
    ("SERPER_API_KEY", "Google results for the right country: rankings, People Also Ask, related searches",
     "https://serper.dev (free credits when you sign up)", True),
    ("SPIDER_API_KEY", "renders competitor pages that block plain fetching, so every ranking page is read",
     "https://spider.cloud", False),
]


def say(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def run(cmd: list[str]) -> int:
    return subprocess.call(cmd, cwd=str(ROOT))


def check_python() -> None:
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10 or newer is needed; this is {sys.version.split()[0]}. Install it from "
                 "https://www.python.org/downloads/ and run this again with the new one.")
    print(f"Python {sys.version.split()[0]} at {sys.executable}")


def packages() -> bool:
    say("Python packages")
    req = str(ROOT / "scripts" / "requirements.txt")
    if run([sys.executable, "-m", "pip", "--version"]) != 0:
        run([sys.executable, "-m", "ensurepip", "--upgrade"])
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", req]
    if run(cmd) == 0:
        return True
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not in_venv and run(cmd + ["--user"]) == 0:
        return True
    print("Could not install the packages. Try in a virtual environment:\n"
          f"  {Path(sys.executable).name} -m venv .venv  then activate it and run install.py again")
    return False


def spacy_model() -> None:
    say("spaCy English model (sharper entities and matching; the pipeline still runs without it)")
    have = run([sys.executable, "-c", "import spacy, sys; sys.exit(0 if spacy.util.is_package('en_core_web_sm') else 1)"])
    if have == 0:
        print("en_core_web_sm already installed")
        return
    if run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"]) != 0:
        print("Could not download it now; run later: "
              f"{Path(sys.executable).name} -m spacy download en_core_web_sm")


def read_env() -> list[str]:
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


def env_value(lines: list[str], name: str) -> str:
    for ln in lines:
        if ln.startswith(name + "="):
            return ln.split("=", 1)[1].strip()
    return ""


def set_env(lines: list[str], name: str, value: str) -> list[str]:
    out, done = [], False
    for ln in lines:
        if ln.startswith(name + "="):
            out.append(f"{name}={value}")
            done = True
        else:
            out.append(ln)
    if not done:
        out.append(f"{name}={value}")
    return out


def keys(ask: bool, force: bool) -> None:
    say("API keys (stored only in .env in this folder; .env is never committed)")
    lines = read_env()
    if not lines and (ROOT / ".env.example").exists():
        lines = [ln for ln in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()]
    interactive = ask and sys.stdin.isatty()
    for name, what, where, needed in KEYS:
        current = env_value(lines, name)
        if current and not force:
            print(f"{name}: set")
            continue
        if os.environ.get(name, "").strip():
            lines = set_env(lines, name, os.environ[name].strip())
            print(f"{name}: taken from the environment")
            continue
        if not interactive:
            print(f"{name}: not set ({'needed' if needed else 'optional'}). Run `install.py --keys`, or set it in .env")
            continue
        print(f"\n{name}: {what}.\n  Get one at {where}.")
        try:
            val = getpass.getpass(f"  Paste {name} (hidden; Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            val = ""
        if val:
            lines = set_env(lines, name, val)
            print(f"  {name} saved")
        else:
            print(f"  skipped ({'the pipeline needs it to search' if needed else 'optional'})")
    ENV.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(ENV, 0o600)


def folders() -> None:
    for d in ("clients", "briefs", "runs"):
        (ROOT / d).mkdir(exist_ok=True)


def agents() -> None:
    say("The /page-seo command, in every coding agent on this machine")
    run([sys.executable, str(ROOT / "scripts" / "install_adapters.py"), "--apply"])


def doctor() -> int:
    say("Setup check")
    return run([sys.executable, str(ROOT / "scripts" / "seo.py"), "doctor"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Set up the page-SEO pipeline on this machine.")
    ap.add_argument("--keys", action="store_true", help="only (re)enter the API keys")
    ap.add_argument("--yes", action="store_true", help="no questions; keys from the environment")
    ap.add_argument("--no-agents", action="store_true", help="do not install the /page-seo command")
    a = ap.parse_args()
    check_python()
    if a.keys:
        keys(ask=True, force=True)
        doctor()
        return
    ok = packages()
    if ok:
        spacy_model()
    keys(ask=not a.yes, force=False)
    folders()
    if not a.no_agents:
        agents()
    rc = doctor()
    py = Path(sys.executable).stem if os.name == "nt" else Path(sys.executable).name
    print(f"""
Ready{'' if rc == 0 and ok else ' (fix the FAIL lines above, then run install.py again)'}. Restart any open agent, then type in it:

  /page-seo <client name or domain>: <keyword> | <optional instructions>
      e.g. /page-seo example.com: how to grow tomatoes in pots | for beginners, UK
      (Codex: $page-seo ...; a new domain is profiled automatically)

Or give it a page to improve:   /page-seo https://example.com/some-page/
From a terminal:                {py} scripts/seo.py start "example.com: how to grow tomatoes in pots"

Each run ends with DONE and the paths to final.md (the page), report.md and eval.md, in runs/.""")


if __name__ == "__main__":
    main()
