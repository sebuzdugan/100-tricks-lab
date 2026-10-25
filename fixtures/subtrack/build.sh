#!/usr/bin/env bash
# Build base/subtrack: the module-5 fixture (days 42-50). subtrack is a small subscription-tracker CLI, plain Node ESM,
# no dependencies, `npm test` runs `node --test`, nothing to install, works offline in the sandbox. Single commit,
# tagged lab-base, no history.
#
# On purpose, the untouched baseline has exactly ONE failing visible test (B1, renewals listed soonest first): that is
# the "its own tests catch it" bug of tasks/m5-weekly-plans. The build checks that this is the only failure.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; LAB="$(cd "$HERE/../.." && pwd)"
DEST="${DEST:-$LAB/base/subtrack}"
rm -rf "$DEST" && mkdir -p "$DEST"
cp -R "$HERE/repo/." "$DEST/"
cd "$DEST"
git init -q -b main
git add -A
git -c user.name="100 Tricks Lab" -c user.email="lab@sebuzdugan.com" commit -qm "subtrack 0.3.0"
git tag lab-base
OUT=$(TZ=UTC node --test --test-reporter=tap 2>&1 || true)
FAILS=$(printf '%s\n' "$OUT" | grep -E '^\s*not ok ' || true)
[ "$(printf '%s\n' "$FAILS" | grep -c 'not ok')" = "1" ] && printf '%s' "$FAILS" | grep -q 'soonest first' \
  || { echo "expected exactly one failing test (renewals soonest first), got:"; printf '%s\n' "$FAILS"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "npm test left files behind"; exit 1; }
echo "subtrack fixture ready at $DEST (1 known failing visible test: B1)"
