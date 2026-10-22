#!/usr/bin/env python3
"""Days 36 and 38: docs-tool use per run from the saved events. Usage: count_calls.py runs/<day> [--csv]
Per run: Context7 calls (resolve / query), Context7 errors (e.g. rate limit), WebFetch / WebSearch calls and errors,
the MCP server status at start, permission denials (from the result event), and which Context7 library ids were read."""
import json, sys
from pathlib import Path

def scan(path: Path):
    c7 = res = q = c7err = wf = ws = weberr = 0
    status, libs, denials, results = "none", [], 0, {}
    pending = {}
    for line in path.open():
        try: e = json.loads(line)
        except json.JSONDecodeError: continue
        if e.get("type") == "system" and e.get("subtype") == "init":
            st = [s.get("status") for s in e.get("mcp_servers") or [] if s.get("name") == "context7"]
            if st: status = st[0]
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") != "tool_use": continue
                n = c["name"]; pending[c["id"]] = n
                if n.startswith("mcp__context7__"):
                    c7 += 1
                    if n.endswith("resolve-library-id"): res += 1
                    else:
                        q += 1; libs.append(c["input"].get("libraryId", "?"))
                elif n == "WebFetch": wf += 1
                elif n == "WebSearch": ws += 1
        if e.get("type") == "user" and isinstance(e.get("message", {}).get("content"), list):
            for c in e["message"]["content"]:
                if c.get("type") != "tool_result": continue
                n = pending.get(c.get("tool_use_id"), "")
                text = c["content"] if isinstance(c.get("content"), str) else " ".join(x.get("text", "") for x in c.get("content") or [])
                bad = c.get("is_error") or "rate limit" in text.lower() or "429" in text
                if n.startswith("mcp__context7__") and bad: c7err += 1
                if n in ("WebFetch", "WebSearch") and c.get("is_error"): weberr += 1
        if e.get("type") == "result":
            denials += len(e.get("permission_denials") or [])
    return {"run": path.name.replace(".events.jsonl", ""), "c7_status": status, "c7_calls": c7, "c7_resolve": res, "c7_query": q,
            "c7_errors": c7err, "c7_libs": "|".join(dict.fromkeys(libs)), "webfetch": wf, "websearch": ws, "web_errors": weberr,
            "permission_denials": denials}

if __name__ == "__main__":
    rows = [scan(p) for p in sorted(Path(sys.argv[1], "raw").glob("*.events.jsonl"))]
    if "--csv" in sys.argv:
        import csv
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    else:
        for r in rows: print(" ".join(f"{k}={v}" for k, v in r.items()))
