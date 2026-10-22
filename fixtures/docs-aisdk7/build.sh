#!/usr/bin/env bash
# Build base/docs-aisdk7: the day 36/38 docs fixture as a single-commit repo tagged lab-base, with node_modules installed.
# The installed `ai` package ships its own docs (docs/, src/, CHANGELOG.md); they are removed from node_modules so the
# no-docs side really has only the model's knowledge plus the package's code and type definitions. Needs git, pnpm, network.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; LAB="$(cd "$HERE/../.." && pwd)"
DEST="${DEST:-$LAB/base/docs-aisdk7}"
rm -rf "$DEST" && mkdir -p "$DEST"
cp -R "$HERE/repo/." "$DEST/"
cd "$DEST"
git init -q
git add -A
git -c user.name="100 Tricks Lab" -c user.email="lab@sebuzdugan.com" commit -qm "helpdesk-ai: AI SDK 7 docs fixture"
git tag lab-base
pnpm install --frozen-lockfile --reporter=silent
# strip the documentation that ships inside the AI SDK packages (node_modules is gitignored, so lab-base is unchanged)
find node_modules/.pnpm -type d \( -path '*/node_modules/ai' -o -path '*/node_modules/@ai-sdk/*' \) -prune -print | while read -r pkg; do
  rm -rf "$pkg/docs" "$pkg/src" "$pkg/CHANGELOG.md"
done
V=$(node -p "require('./node_modules/ai/package.json').version")
[ "$V" = "7.0.128" ] || { echo "wrong ai version installed: $V"; exit 1; }
[ ! -e node_modules/ai/docs ] || { echo "docs not stripped"; exit 1; }
pnpm test >/dev/null 2>&1 || { echo "fixture's own tests fail"; exit 1; }
echo "docs fixture ready at $DEST (ai $V)"
