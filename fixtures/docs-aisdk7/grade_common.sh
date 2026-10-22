# Shared grading steps for the docs-fixture tasks (a7-*). Sourced by tasks/a7-*/accept.sh with W, H, TASK, LOGDIR set.
fail(){ echo "FAIL $TASK: $*"; exit 1; }
FIX="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 1. The pinned version stays: package.json and the lockfile untouched, ai 7.0.128 actually installed.
git -C "$W" diff --quiet lab-base -- package.json pnpm-lock.yaml || fail "package.json or pnpm-lock.yaml changed (version pin or dependencies)"
V=$(cd "$W" && node -p "require('ai/package.json').version" 2>/dev/null)
[ "$V" = "7.0.128" ] || fail "installed ai is '$V', not the pinned 7.0.128"
# 2. Existing tests and the mock helper are not edited or deleted (new test files are fine).
CHANGED=$(git -C "$W" diff --name-only --diff-filter=MDR lab-base -- test)
[ -z "$CHANGED" ] || fail "existing test files changed: $(echo $CHANGED | tr '\n' ' ')"
# 3. No API that AI SDK 7 removed, in the src files the agent added or changed (comments ignored).
TOUCHED=$( (git -C "$W" diff --name-only --diff-filter=AM lab-base -- src; git -C "$W" ls-files --others --exclude-standard -- src) | sort -u | sed "s#^#$W/#")
python3 "$FIX/removed_api.py" $TOUCHED >"$LOGDIR/$TASK-removed-api.log" || fail "uses an API removed in AI SDK 7: $(head -1 "$LOGDIR/$TASK-removed-api.log")"
# 4. Hidden behaviour tests, with the lab's own copy of the mock helper.
run_hidden(){
  local dir="$W/.lab-hidden"; rm -rf "$dir"; mkdir -p "$dir"
  cp "$FIX/repo/test/helpers/mock-model.js" "$dir/mock-model.js"
  cp "$H"/*.test.js "$dir/"
  (cd "$W" && node --test --test-reporter=spec .lab-hidden/*.test.js >"$LOGDIR/$TASK-hidden.log" 2>&1); local rc=$?
  rm -rf "$dir"
  [ $rc -eq 0 ] || fail "hidden tests fail: $(grep -E '^\s*✖ ' "$LOGDIR/$TASK-hidden.log" | grep -v 'failing tests' | head -2 | sed -E 's/^\s*✖ //; s/ \([0-9.]+ms\)//' | paste -sd ';' -) (see $LOGDIR/$TASK-hidden.log)"
}
