#!/usr/bin/env bash
# Acceptance for t1-flag-bug. Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; fail(){ echo "FAIL t1: $*"; exit 1; }
git -C "$W" diff --quiet lab-base -- packages/frai-gate || fail "packages/frai-gate was modified"
(cd "$W/packages/frai-cli" && npx tsc --project tsconfig.json >/dev/null 2>&1) || fail "frai-cli does not build"
T=$(mktemp -d)
(cd "$T" && node "$W/packages/frai-cli/dist/index.js" gate init --ci >/dev/null 2>&1)
[ -f "$T/FRAI-SPEC.md" ] || fail "FRAI-SPEC.md not created"
[ -f "$T/.github/workflows/rai-gate.yml" ] || fail "workflow not created with --ci"
T2=$(mktemp -d)
(cd "$T2" && node "$W/packages/frai-cli/dist/index.js" gate init >/dev/null 2>&1)
[ -f "$T2/FRAI-SPEC.md" ] || fail "plain init no longer creates FRAI-SPEC.md"
[ ! -e "$T2/.github" ] || fail "plain init (no --ci) now writes a workflow"
rm -rf "$T" "$T2"
echo "PASS t1"
