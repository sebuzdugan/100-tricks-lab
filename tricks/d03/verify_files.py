#!/usr/bin/env python3
"""Checks the day 3 files before the runs: python3 tricks/d03/verify_files.py

- the short file (with/CLAUDE.md) is about 50 lines
- the long file (without/CLAUDE.md) has 500+ lines
- every non-blank line of the short file appears in the long file, verbatim and in the same order
- the key lines are spread through the long file, including the two checkable rules
- neither file mentions anything the tasks are about (t1-t3 and the hard set h1-h4)
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
short = (HERE / "with" / "CLAUDE.md").read_text().splitlines()
long_ = (HERE / "without" / "CLAUDE.md").read_text().splitlines()
RULES = ("Don't add dependencies.", "Only change the packages the task needs.")
# Words that would point at t1 (--ci passthrough, init workflow), t2 (failing frai-core tests) or t3 (summary).
HINTS = [r"--ci\b", r"\bci flag", r"rai-gate\.yml", r"workflow file", r"passThroughOptions", r"enablePositionalOptions",
         r"allowUnknownOption", r"renderSummary", r"--summary", r"\bsummary line", r"DEFAULT_METRICS", r"bannedTerms",
         r"banned", r"APPROVAL_STATUSES", r"failing", r"known.*fail", r"references leak"]
# Words that would point at the hard set: h1 (field parser in validate.ts: label styles, empty fields, continuation
# lines, open items), h2 (thresholds in generateReport, null scores, repeated options, exit codes on thrown errors),
# h3 (.env parsing and overwriting in key-store.js, root options swallowing subcommand options), h4 (the import
# regex, library list and extensions in the scanners).
HINTS += [r"EMPTY_FIELD", r"\*\*Retention\*\*", r"field line", r"continuation", r"label style", r"threshold",
          r"NEEDS HUMAN INPUT.*(block|check)", r"parseAsync", r"exits? with code 1", r"CLI execution failed", r"null` when",
          r"repeatable", r"replaces the whole", r"overwrites? the whole", r"quotes are stripped", r"export prefix",
          r"checks that (the file|`?\.env`?) exists", r"positional", r"swallow", r"DEFAULT_CODE_EXTENSIONS",
          r"DEFAULT_AI_LIBRARIES", r"import, from or require", r"\.mts\b", r"sub-?module", r"@langchain/openai.*scan"]

errors = []
if not 40 <= len(short) <= 60:
    errors.append(f"short file has {len(short)} lines, expected about 50")
if len(long_) < 500:
    errors.append(f"long file has {len(long_)} lines, expected 500+")

key = [l for l in short if l.strip()]
positions, i = [], 0
for k in key:
    while i < len(long_) and long_[i] != k:
        i += 1
    if i == len(long_):
        errors.append(f"key line missing or out of order in long file: {k[:70]}")
        break
    positions.append(i + 1)
    i += 1

if len(positions) == len(key):
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    print(f"short: {len(short)} lines, {len(key)} key lines; long: {len(long_)} lines")
    print(f"key lines at long-file lines {positions[0]}..{positions[-1]}, largest gap {max(gaps)} lines")
    for r in RULES:
        n = next(p for k, p in zip(key, positions) if r in k)
        print(f"rule '{r}' at long-file line {n} of {len(long_)} ({100 * n // len(long_)}%)")
    if positions[-1] < len(long_) * 0.6:
        errors.append("key lines end before 60% of the long file")

for name, lines in (("short", short), ("long", long_)):
    text = "\n".join(lines)
    for h in HINTS:
        if re.search(h, text, re.I):
            errors.append(f"{name} file matches task-hint pattern {h!r}")

if errors:
    print("\n".join("ERROR " + e for e in errors))
    sys.exit(1)
print("OK")
