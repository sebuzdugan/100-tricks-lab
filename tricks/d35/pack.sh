#!/usr/bin/env bash
# Day 35 group hook: <workdir> <group> <side> <request ids>. Packs the repo copy as it is now into repomix-output.xml
# (Repomix 1.18.1, --compress: structure and signatures, so the pack stays far under Claude Code's Read limits) and
# prints the line that goes before the group's first request. The pack is listed in .git/info/exclude, so it never
# counts as an agent change, never shows in `git status`, and Grep (ripgrep) skips it; the agent reads it with Read.
set -euo pipefail
W="$1"; G="$2"
LAB="$(cd "$(dirname "$0")/../.." && pwd)"
[ -d "$LAB/base/_tools" ] || LAB="$(cd "$(dirname "$0")/../../../.." && pwd)"
RX="$LAB/base/_tools/repomix-1.18.1/node_modules/.bin/repomix"
[ -x "$RX" ] || { echo "run setup_repomix.sh first" >&2; exit 1; }
grep -qx "repomix-output.xml" "$W/.git/info/exclude" 2>/dev/null || echo "repomix-output.xml" >> "$W/.git/info/exclude"
rm -f "$W/repomix-output.xml"
(cd "$W" && "$RX" --compress --quiet -o repomix-output.xml >/dev/null 2>&1) || { echo "repomix failed" >&2; exit 1; }
B=$(wc -c < "$W/repomix-output.xml" | tr -d ' ')
echo "group $G pack: $B bytes" >&2
if [ "$G" = "1" ]; then
  printf 'repomix-output.xml in the repo root is the whole repository packed into one file. Read it before you start.\n\n'
else
  printf 'repomix-output.xml in the repo root is the whole repository packed into one file (regenerated just now). Read it before you start.\n\n'
fi
