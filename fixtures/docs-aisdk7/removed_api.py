#!/usr/bin/env python3
"""Flag AI SDK names that no longer exist in AI SDK 7 in the given source files (comments stripped).
Usage: removed_api.py <file>... (the grader passes the src/ files the agent added or changed).
Exit 1 and print the first hit if any. Deprecated-but-working aliases (system, stepCountIs, onFinish, fullStream,
totalUsage) are not flagged: they still work in 7.0."""
import re, sys
from pathlib import Path

REMOVED = {
    r"\bmaxSteps\b": "maxSteps (AI SDK 4; use stopWhen)",
    r"\bexperimental_output\b": "experimental_output (removed in 7; use output)",
    r"\bexperimental_context\b": "experimental_context (renamed in 7: tool context / runtimeContext)",
    r"\bexperimental_activeTools\b": "experimental_activeTools (removed in 7)",
    r"\bexperimental_prepareStep\b": "experimental_prepareStep (removed in 7)",
    r"\bcachedInputTokens\b(?!\s*:)": "usage.cachedInputTokens (removed in 7)",
    r"\btextDelta\b": "textDelta (AI SDK 4 stream part field)",
    r"\bpromptTokens\b|\bcompletionTokens\b": "promptTokens/completionTokens (AI SDK 4 usage)",
    r"\bToolCallOptions\b": "ToolCallOptions (removed in 7)",
    r"\bparameters\s*:\s*z\.": "tool parameters: (AI SDK 4; use inputSchema)",
}

def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(^|[^:'\"`])//[^\n]*", r"\1", src)

hits = []
for f in map(Path, sys.argv[1:]):
    if not f.is_file() or f.suffix not in (".js", ".mjs", ".cjs", ".ts", ".mts"):
        continue
    code = strip_comments(f.read_text(errors="ignore"))
    for pat, why in REMOVED.items():
        m = re.search(pat, code)
        if m:
            hits.append(f"{f.name}: {why}")
for h in dict.fromkeys(hits):
    print(h)
sys.exit(1 if hits else 0)
