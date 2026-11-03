#!/usr/bin/env bash
# Run the test suite. Needs no credentials and no network.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ] && command -v python3 >/dev/null; then
  echo "No .venv found. Run ./scripts/dev.sh first, or set VENV=0 to use your active interpreter." >&2
fi

if [ -f .venv/bin/activate ] && [ "${VENV:-1}" = "1" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec pytest "${@:--q}"
