#!/usr/bin/env python3
"""Day 37: per-request timeline from the saved events. Usage: turn_timeline.py runs/<day> [--json]
Each call (request) starts with an init event and ends with a result event. Per request it counts console.log calls the
agent wrote into files (Write content, Edit/MultiEdit new text; comments ignored), console.log typed in shell commands
(one-off `node -e` checks, heredocs; reported separately), and whether Claude Code auto-compacted the context."""
import json, re, sys
from pathlib import Path

PAT = re.compile(r"\bconsole\s*\.\s*log\s*\(")
def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(^|[^:'\"`\\])//[^\n]*", r"\1", s)

def timeline(path: Path):
    calls, cur = [], None
    for line in path.open():
        try: e = json.loads(line)
        except json.JSONDecodeError: continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            cur = {"file_logs": 0, "shell_logs": 0, "compacted": False, "log_imports": 0}; calls.append(cur)
        if cur is None: continue
        if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
            cur["compacted"] = True
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") != "tool_use": continue
                i = c.get("input") or {}
                texts = []
                if c["name"] == "Write": texts = [i.get("content", "")]
                elif c["name"] == "Edit": texts = [i.get("new_string", "")]
                elif c["name"] == "MultiEdit": texts = [x.get("new_string", "") for x in i.get("edits", [])]
                for t in texts:
                    cur["file_logs"] += len(PAT.findall(strip_comments(t)))
                    cur["log_imports"] += len(re.findall(r"from\s+['\"][./]*(?:src/)?log\.js['\"]", t))
                if c["name"] == "Bash":
                    cur["shell_logs"] += len(PAT.findall(i.get("command", "")))
    first = next((k + 1 for k, c in enumerate(calls) if c["file_logs"]), None)
    return {"run": path.name.replace(".events.jsonl", ""), "requests": len(calls), "first_break": first,
            "file_logs": [c["file_logs"] for c in calls], "shell_logs": [c["shell_logs"] for c in calls],
            "compacted_at": [k + 1 for k, c in enumerate(calls) if c["compacted"]]}

if __name__ == "__main__":
    rows = [timeline(p) for p in sorted(Path(sys.argv[1], "raw").glob("*.events.jsonl"))]
    for r in rows:
        print(json.dumps(r) if "--json" in sys.argv else
              f"{r['run']}: requests={r['requests']} first_break={r['first_break'] or 'none'} file_logs={','.join(map(str, r['file_logs']))} "
              f"shell_logs={','.join(map(str, r['shell_logs']))} compacted_at={r['compacted_at'] or 'never'}")
