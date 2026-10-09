#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
UI_TESTS_DIR="$PROJECT_ROOT/tests/ui"
FRONTEND_URL="${TEST_FRONTEND_URL:-http://127.0.0.1:5173}"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required to run the UI tests. Install uv, then retry." >&2
    exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to check the UI endpoint before starting Playwright." >&2
    exit 2
fi

if ! curl --fail --silent --show-error --max-time 5 "${FRONTEND_URL%/}/" >/dev/null; then
    echo "The UI is not reachable at $FRONTEND_URL." >&2
    echo "Start the application or set TEST_FRONTEND_URL to its UI URL." >&2
    exit 1
fi

export TEST_FRONTEND_URL="$FRONTEND_URL"
cd "$PROJECT_ROOT"

# uv creates and maintains this project's virtual environment; no global Python
# packages are installed. The pytest fixture installs Chromium on first use.
exec uv run --project "$UI_TESTS_DIR" python -m pytest -v "$UI_TESTS_DIR" "$@"
