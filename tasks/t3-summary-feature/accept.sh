#!/usr/bin/env bash
# Acceptance for t3-summary-feature. Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; H="$(cd "$(dirname "$0")" && pwd)/hidden"; G="$W/packages/frai-gate"; fail(){ echo "FAIL t3: $*"; exit 1; }
(cd "$G" && npx tsc --project tsconfig.json >/dev/null 2>&1) || fail "frai-gate does not build"
(cd "$G" && npx vitest run >"$LOGDIR/t3-suite.log" 2>&1) || fail "frai-gate suite fails (see "$LOGDIR/t3-suite.log")"
cp "$H/lab_summary.test.ts" "$G/src/lab_summary.test.ts"
(cd "$G" && npx vitest run src/lab_summary.test.ts >"$LOGDIR/t3-hidden.log" 2>&1); rc=$?
rm -f "$G/src/lab_summary.test.ts"
[ $rc -eq 0 ] || fail "hidden renderSummary tests fail (see "$LOGDIR/t3-hidden.log")"
SPEC="$W/examples/support-triage-demo/FRAI-SPEC.md"
OUT=$(cd "$W" && node "$G/dist/cli.js" check "$SPEC" --summary 2>/dev/null); rc=$?
LINES=$(printf "%s" "$OUT" | grep -c .)
[ "$LINES" = "1" ] || fail "--summary printed $LINES lines"
echo "$OUT" | grep -Eq '^(PASS|WARN|BLOCK) [0-7]/7(: [a-z-]+(, [a-z-]+)*)?$' || fail "--summary output malformed: $OUT"
case "$OUT" in BLOCK*) [ $rc -eq 1 ] || fail "BLOCK summary exit code $rc";; *) [ $rc -eq 0 ] || fail "non-BLOCK exit code $rc";; esac
JSON=$(cd "$W" && node "$G/dist/cli.js" check "$SPEC" --summary --json 2>/dev/null)
echo "$JSON" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null || fail "--json no longer wins over --summary"
echo "PASS t3"
