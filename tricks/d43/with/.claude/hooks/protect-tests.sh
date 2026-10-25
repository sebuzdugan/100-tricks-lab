#!/usr/bin/env bash
# PreToolUse hook (Edit|Write|MultiEdit): block edits to existing, git-tracked *.test.ts / *.test.js files.
# New test files are allowed. Each block is logged outside the repo copy, to <repo>-logs/protect-tests.log
# (override with PROTECT_TESTS_LOG), because hook blocks don't show up in Claude's JSON output.
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
[ -n "$file" ] || exit 0
case "$file" in
  *.test.ts|*.test.js) ;;
  *) exit 0 ;;
esac

project="${CLAUDE_PROJECT_DIR:-$(printf '%s' "$input" | jq -r '.cwd // empty')}"
project="${project:-$PWD}"
case "$file" in
  /*) ;;
  *) file="$project/$file" ;;
esac

dir="$(dirname "$file")"
[ -d "$dir" ] || exit 0                       # a new folder: the file can't be tracked yet
git -C "$dir" ls-files --error-unmatch -- "$(basename "$file")" >/dev/null 2>&1 || exit 0   # untracked or new: allowed

root="$(cd "$project" 2>/dev/null && pwd -P)"
log="${PROTECT_TESTS_LOG:-$(dirname "$root")/$(basename "$root")-logs/protect-tests.log}"
mkdir -p "$(dirname "$log")" 2>/dev/null
tool="$(printf '%s' "$input" | jq -r '.tool_name // "?"')"
printf '%s\t%s\t%s\n' "$(date +%s)" "$tool" "$file" >> "$log" 2>/dev/null

echo "Existing test files are protected. Put new tests in a new file." >&2
exit 2
