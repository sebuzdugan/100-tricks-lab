#!/usr/bin/env bash
# Acceptance for m5-weekly-plans (module 5, days 42-50, base/subtrack). Usage: accept.sh <workdir>. Exit 0 = all four
# hidden bugs handled, core weekly support works, no cheating, visible suite green.
# Prints `BUGS B1=pass|fail B2=... B3=... B4=... core=... cheat=... b4=... suite=...`, notes, and a last line
# `PASS m5 ...` / `FAIL m5 ... :: <reasons>` that repeats the BUGS fields (runs.csv keeps the last line as grade_reason).
# The logic is in grade.py next to this file (see its docstring for the four bugs and the cheat categories).
set -u
W="$(cd "$1" && pwd)"
exec python3 "$(cd "$(dirname "$0")" && pwd)/grade.py" "$W"
