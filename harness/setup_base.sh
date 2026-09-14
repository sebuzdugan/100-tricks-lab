#!/usr/bin/env bash
# Rebuild base/frai: frai at the commit before the --ci fix, with the governance test aligned,
# as a single-commit repo (no history an agent could copy the real fix from). Needs git, pnpm.
set -euo pipefail
LAB="$(cd "$(dirname "$0")/.." && pwd)"
BASE_DIR="${BASE_DIR:-$LAB/base/frai}"
SRC="${FRAI_REPO:-https://github.com/sebuzdugan/frai.git}"
BEFORE=f3c86240b41c5ec15e060b7a6d08f7ebbcdb6aeb
FIX=902ec19a3aed66674629ce7c2dd570e0be59e6a9
TMP="$(mktemp -d)"
git clone -q "$SRC" "$TMP/src"
rm -rf "$BASE_DIR" && mkdir -p "$BASE_DIR"
git -C "$TMP/src" archive "$BEFORE" | tar -x -C "$BASE_DIR"
git -C "$TMP/src" show "$FIX" -- packages/frai-core/src/finetune/governance.test.js > "$TMP/gov.patch"
(cd "$BASE_DIR" && git apply "$TMP/gov.patch")
rm -rf "$TMP"
cd "$BASE_DIR"
git init -q
git add -A
git -c user.name="100 Tricks Lab" -c user.email="lab@sebuzdugan.com" commit -qm "Lab baseline: frai before the --ci fix, governance test aligned"
git tag lab-base
pnpm install --frozen-lockfile
echo "base ready at $BASE_DIR"
