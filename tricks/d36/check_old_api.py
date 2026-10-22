#!/usr/bin/env python3
"""Day 36/38 extra measure: old AI SDK names left in the agent's code. Usage: check_old_api.py <workdir> <side> <task>.
Scans the src/ files the agent added or changed (plus src/legacy/assistant.js on the upgrade task), comments stripped.
'removed' = names AI SDK 7 no longer has (the grader fails these); 'deprecated' = pre-7 names that still work in 7.0.
Last line: old_api=<n> removed=<n> deprecated=<n> [names]"""
import re, subprocess, sys
from pathlib import Path

REMOVED = ["maxSteps", "experimental_output", "experimental_context", "experimental_activeTools", "experimental_prepareStep",
           "cachedInputTokens", "textDelta", "promptTokens", "completionTokens", "ToolCallOptions"]
DEPRECATED = {"system:": r"\bsystem\s*:", "stepCountIs": r"\bstepCountIs\b", "onFinish": r"\bonFinish\b", "onStepFinish": r"\bonStepFinish\b",
              "fullStream": r"\bfullStream\b", "totalUsage": r"\btotalUsage\b", "generateObject": r"\bgenerateObject\b",
              "streamObject": r"\bstreamObject\b", "needsApproval": r"\bneedsApproval\b", "toTextStreamResponse": r"\btoTextStreamResponse\b"}

def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(^|[^:'\"`])//[^\n]*", r"\1", src)

w, side, task = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
git = lambda *a: subprocess.run(["git", "-C", str(w), *a], capture_output=True, text=True).stdout.split("\n")
files = {f for f in git("diff", "--name-only", "--diff-filter=AM", "lab-base", "--", "src") + git("ls-files", "--others", "--exclude-standard", "--", "src") if f}
if task == "a7-upgrade-legacy":
    files.add("src/legacy/assistant.js")
removed, deprecated = [], []
for f in sorted(files):
    p = w / f
    if not p.is_file() or p.suffix not in (".js", ".mjs", ".cjs", ".ts"):
        continue
    code = strip_comments(p.read_text(errors="ignore"))
    removed += [n for n in REMOVED if re.search(rf"\.{n}\b" if n == "cachedInputTokens" else rf"\b{n}\b", code)]
    deprecated += [n for n, pat in DEPRECATED.items() if re.search(pat, code)]
removed, deprecated = sorted(set(removed)), sorted(set(deprecated))
names = ",".join(removed + deprecated)
print(f"old_api={len(removed) + len(deprecated)} removed={len(removed)} deprecated={len(deprecated)}" + (f" [{names}]" if names else ""))
