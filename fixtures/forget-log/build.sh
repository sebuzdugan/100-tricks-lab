#!/usr/bin/env bash
# Build base/forget-log: the day 37 fixture (shopstats, no dependencies) as a single-commit repo tagged lab-base.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; LAB="$(cd "$HERE/../.." && pwd)"
DEST="${DEST:-$LAB/base/forget-log}"
rm -rf "$DEST" && mkdir -p "$DEST"
cp -R "$HERE/repo/." "$DEST/"
cd "$DEST"
git init -q
git add -A
git -c user.name="100 Tricks Lab" -c user.email="lab@sebuzdugan.com" commit -qm "shopstats: day 37 fixture"
git tag lab-base
node -e "import('./src/data.js').then(m => { if (m.loadOrders().length !== 32) process.exit(1) })"
echo "forget-log fixture ready at $DEST"
