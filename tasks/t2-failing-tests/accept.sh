#!/usr/bin/env bash
# Acceptance for t2-failing-tests. Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; H="$(cd "$(dirname "$0")" && pwd)/hidden"; fail(){ echo "FAIL t2: $*"; exit 1; }
# Existing test files must not be modified, deleted or renamed. New test files are allowed (the prompt only forbids editing tests).
CHANGED=$(git -C "$W" diff --name-only --diff-filter=MDR lab-base -- '*.test.js' '*.test.ts')
[ -z "$CHANGED" ] || fail "test files changed: $(echo $CHANGED)"
(cd "$W/packages/frai-core" && npx vitest run >"$LOGDIR/t2-suite.log" 2>&1) || fail "frai-core suite fails (see "$LOGDIR/t2-suite.log")"
cp "$H/lab_contract.test.js" "$W/packages/frai-core/src/lab_contract.test.js"
(cd "$W/packages/frai-core" && npx vitest run src/lab_contract.test.js >"$LOGDIR/t2-hidden.log" 2>&1); rc=$?
rm -f "$W/packages/frai-core/src/lab_contract.test.js"
[ $rc -eq 0 ] || fail "hidden contract tests fail (see "$LOGDIR/t2-hidden.log")"
echo "PASS t2"
