#!/usr/bin/env python3
"""Day 40 group hook: paste.py <all|focused> <workdir> <group> <side> <request ids>.

Prints a 'Project files:' block for the first request of a group (both sides start every group in a fresh session):
  all      every text file in the repo copy as it is now (tracked and untracked, .gitignore respected)
  focused  only the files the group's requests touch (their `mention` lists in requests.json) that exist now
Same block format on both sides: <file path="...">...</file>, then a blank line; the request follows."""
import json, subprocess, sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
if not (LAB / "fixtures").exists():
    LAB = Path(__file__).resolve().parents[4]
mode, work, group, side, ids = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5].split(",")
files = subprocess.run(["git", "-C", str(work), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True).stdout.split()
files = sorted(f for f in files if not f.startswith(".lab-") and f not in ("repomix-output.xml",))
if mode == "focused":
    reqs = {r["id"]: r for r in json.loads((LAB / "fixtures" / "marathon" / "requests.json").read_text())["requests"]}
    want = []
    for i in ids:
        for f in reqs[i].get("mention") or []:
            if f not in want:
                want.append(f)
    files = [f for f in want if (work / f).is_file()]
out = ["Project files:\n"]
for f in files:
    try:
        text = (work / f).read_text()
    except (UnicodeDecodeError, OSError):
        continue
    out.append(f'<file path="{f}">\n{text.rstrip()}\n</file>\n')
print("\n".join(out) + "\n", end="")
print(f"group {group} {mode}: {len(files)} files, {sum(len(x) for x in out)} chars", file=sys.stderr)
