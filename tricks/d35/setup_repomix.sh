#!/usr/bin/env bash
# Install Repomix 1.18.1 once into base/_tools (gitignored), so the day-35 group hook packs the repo offline in ~1 s.
set -euo pipefail
LAB="$(cd "$(dirname "$0")/../.." && pwd)"
[ -d "$LAB/base" ] || LAB="$(cd "$(dirname "$0")/../../../.." && pwd)"   # also works from private/m4b/tricks/d35
T="$LAB/base/_tools/repomix-1.18.1"
if [ ! -x "$T/node_modules/.bin/repomix" ]; then
  mkdir -p "$T" && npm install --prefix "$T" --no-audit --no-fund --silent repomix@1.18.1
fi
"$T/node_modules/.bin/repomix" --version
