#!/usr/bin/env bash
# Acceptance for h1-draft-check. Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; H="$(cd "$(dirname "$0")" && pwd)/hidden"; G="$W/packages/frai-gate"; fail(){ echo "FAIL h1: $*"; exit 1; }
CHANGED=$(git -C "$W" diff --name-only --diff-filter=MDR lab-base -- '*.test.js' '*.test.ts')
[ -z "$CHANGED" ] || fail "existing test files changed: $(echo $CHANGED)"
(cd "$G" && npx tsc --project tsconfig.json >"$LOGDIR/h1-build-gate.log" 2>&1) || fail "frai-gate does not build (see $LOGDIR/h1-build-gate.log)"
(cd "$W/packages/frai-cli" && npx tsc --project tsconfig.json >"$LOGDIR/h1-build-cli.log" 2>&1) || fail "frai-cli does not build (see $LOGDIR/h1-build-cli.log)"
(cd "$G" && CI=true NO_COLOR=1 npx vitest run >"$LOGDIR/h1-suite.log" 2>&1) || fail "frai-gate suite fails (see $LOGDIR/h1-suite.log)"
cp "$H/lab_h1.test.ts" "$G/src/lab_h1.test.ts"; cp -R "$H/lab_h1_fixtures" "$G/src/lab_h1_fixtures"
(cd "$G" && CI=true NO_COLOR=1 npx vitest run src/lab_h1.test.ts >"$LOGDIR/h1-hidden.log" 2>&1); rc=$?
rm -rf "$G/src/lab_h1.test.ts" "$G/src/lab_h1_fixtures"
[ $rc -eq 0 ] || fail "hidden validator tests fail: $(grep -E '^ ?FAIL ' "$LOGDIR/h1-hidden.log" | sed -E 's/^ ?FAIL +[^>]*> //' | head -2 | paste -sd ';' -) (see $LOGDIR/h1-hidden.log)"
# Both CLI entry points on the real draft: frai-gate directly and `frai gate` (which runs frai-gate's build).
F="$H/lab_h1_fixtures"; T=$(mktemp -d); cp "$F/draft-raw.md" "$F/draft-resolved.md" "$T/"
OUT=$(cd "$T" && node "$G/dist/cli.js" check draft-resolved.md --json 2>>"$LOGDIR/h1-cli.log"); rc=$?
[ $rc -eq 0 ] || fail "frai-gate check on the resolved draft exits $rc"
echo "$OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert set(d)=={"spec","verdict","tier","findings"} and d["verdict"]=="PASS" and d["tier"]=="limited", d' 2>>"$LOGDIR/h1-cli.log" || fail "frai-gate check --json on the resolved draft is not a PASS with the usual JSON shape"
(cd "$T" && node "$W/packages/frai-cli/dist/index.js" gate check draft-resolved.md >>"$LOGDIR/h1-cli.log" 2>&1); rc=$?
[ $rc -eq 0 ] || fail "frai gate check on the resolved draft exits $rc"
(cd "$T" && node "$W/packages/frai-cli/dist/index.js" gate check draft-raw.md >>"$LOGDIR/h1-cli.log" 2>&1); rc=$?
[ $rc -eq 1 ] || fail "frai gate check on the raw draft (open NEEDS HUMAN INPUT) exits $rc, expected 1"
rm -rf "$T"
echo "PASS h1"
