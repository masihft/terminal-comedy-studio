#!/usr/bin/env bash
# Set up a development environment and install the comedian in editable mode.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in one provider, or leave it offline."
fi

echo
echo "Ready. Try:"
echo "  comedian              # the stage, offline show"
echo "  ./scripts/demo.sh     # a scripted two-minute tour"
echo "  pytest                # the tests"
