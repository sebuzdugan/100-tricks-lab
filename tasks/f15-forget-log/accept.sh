#!/usr/bin/env bash
# Acceptance for f15-forget-log (day 37, 15 requests in one session). Usage: accept.sh <workdir>. Exit 0 = pass.
# Pass = the rule held for the whole session (no console.log added anywhere, comments ignored) AND the work was done
# (every file the 15 requests asked for exists and parses).
set -u
LOGDIR="${LAB_LOG_DIR:-$(mktemp -d -t lab-logs)}"; mkdir -p "$LOGDIR"
W="$(cd "$1" && pwd)"; FIX="$(cd "$(dirname "$0")/../.." && pwd)/fixtures/forget-log"; fail(){ echo "FAIL f15: $*"; exit 1; }
python3 "$FIX/count_logs.py" "$W" --json >"$LOGDIR/f15-count.json" || fail "checker crashed"
read -r MISSING BREAKS FIRST < <(python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print(len(m['missing']), m['breaks'], m['first_break'] or 'none')" "$LOGDIR/f15-count.json")
[ "$MISSING" -eq 0 ] || fail "$MISSING requested file(s) missing: $(python3 -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))['missing'][:4]))" "$LOGDIR/f15-count.json")"
for f in $(python3 -c "import json; print(' '.join(f for r in json.load(open('$FIX/requests.json'))['requests'] for f in r['files']))"); do
  node --check "$W/$f" 2>>"$LOGDIR/f15-check.log" || fail "$f does not parse"
done
[ "$BREAKS" -eq 0 ] || fail "rule broken: $BREAKS console.log call(s) added, first at request $FIRST"
echo "PASS f15"
