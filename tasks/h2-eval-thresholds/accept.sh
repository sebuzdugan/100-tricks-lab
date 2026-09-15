#!/usr/bin/env bash
# Acceptance for h2-eval-thresholds. Usage: accept.sh <workdir>. Exit 0 = pass.
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; H="$(cd "$(dirname "$0")" && pwd)/hidden"; C="$W/packages/frai-core"; fail(){ echo "FAIL h2: $*"; exit 1; }
(cd "$W/packages/frai-cli" && npx tsc --project tsconfig.json >"$LOGDIR/h2-build.log" 2>&1) || fail "frai-cli does not build (see $LOGDIR/h2-build.log)"
# Editing or adding tests is allowed (the prompt doesn't forbid it), but the original frai-core tests must still hold:
# every existing test file that was changed, renamed or deleted also runs in its baseline version.
ORIG=$(git -C "$W" diff --name-only --diff-filter=MDR lab-base -- 'packages/frai-core/*.test.js')
for f in $ORIG; do mkdir -p "$(dirname "$W/$f")"; git -C "$W" show "lab-base:$f" >"$W/${f%.test.js}.lab-orig.test.js"; done
# The two tests that already fail on the baseline (toxicity, governance) may keep failing; nothing else may.
(cd "$C" && CI=true NO_COLOR=1 npx vitest run --reporter=json --outputFile="$LOGDIR/h2-suite.json" >"$LOGDIR/h2-suite.log" 2>&1)
for f in $ORIG; do rm -f "$W/${f%.test.js}.lab-orig.test.js"; done
python3 - "$LOGDIR/h2-suite.json" <<'PY' || fail "frai-core suite has new failures (see $LOGDIR/h2-suite.json)"
import json, sys
known = {"Evaluation harness runs default evaluations", "Fine-tuning governance module flags schema violations with descriptive errors"}
d = json.load(open(sys.argv[1]))
bad = [a["fullName"].strip() for f in d["testResults"] for a in f["assertionResults"] if a["status"] != "passed" and a["fullName"].strip() not in known]
bad += [f["name"] for f in d["testResults"] if f["status"] != "passed" and not f["assertionResults"]]
if bad: print(bad); sys.exit(1)
PY
cp "$H/lab_h2.test.js" "$C/src/lab_h2.test.js"
(cd "$C" && CI=true NO_COLOR=1 npx vitest run src/lab_h2.test.js >"$LOGDIR/h2-hidden.log" 2>&1); rc=$?
rm -f "$C/src/lab_h2.test.js"
[ $rc -eq 0 ] || fail "hidden frai-core threshold tests fail: $(grep -E '^ ?FAIL ' "$LOGDIR/h2-hidden.log" | sed -E 's/^ ?FAIL +[^>]*> //' | head -2 | paste -sd ';' -) (see $LOGDIR/h2-hidden.log)"
OUT=$(node "$H/lab_h2_cli.mjs" "$W" 2>"$LOGDIR/h2-cli.err"); rc=$?
echo "$OUT" >"$LOGDIR/h2-cli.log"
[ $rc -eq 0 ] || fail "CLI: $(echo "$OUT" | grep '^FAIL' | head -1 | sed 's/^FAIL //' | head -c 300)"
echo "PASS h2"
