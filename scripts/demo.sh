#!/usr/bin/env bash
# A scripted tour of the stage, safe to paste in a README or record.
# Runs the offline show: no keys, no network, no provider.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .venv/bin/activate ]; then
  echo "Run ./scripts/dev.sh first." >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

LANGUAGE="${LANGUAGE:-fa}" \
AI_PROVIDER=offline \
comedian --plain <<'DEMO'
/joke
خسته‌ام، یه چیزی بگو
/standup
/roast git merge conflict
/story
/random
/character sarkash
/joke
/provider
/settings
/reset
/exit
DEMO
