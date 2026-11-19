#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Lint and tests. Uses .venv (created on first run) unless CLOCKODO_TEST_SYSTEM=1
# is set, which uses the system Python (Arch container, CI).
#   scripts/test.sh [pytest arguments]
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"

if [ "${CLOCKODO_TEST_SYSTEM:-0}" = 1 ]; then
    python=python3
else
    if [ ! -x .venv/bin/python ]; then
        python3 -m venv .venv
        .venv/bin/pip install -q -e '.[test]'
    fi
    python=.venv/bin/python
fi

if "$python" -m ruff --version >/dev/null 2>&1; then
    "$python" -m ruff check backend tests
    "$python" -m ruff format --check backend tests
fi

sh scripts/check-version.sh

# D-Bus tests need a private session bus.
dbus-run-session -- "$python" -m pytest -q "$@"
