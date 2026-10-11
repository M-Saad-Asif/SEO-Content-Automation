#!/usr/bin/env sh
# macOS / Linux: ./install.sh   (finds Python 3 and runs install.py)
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then exec python3 install.py "$@"; fi
if command -v python >/dev/null 2>&1; then exec python install.py "$@"; fi
echo "Python 3.10+ is needed: install it from https://www.python.org/downloads/ and run this again."
exit 1
