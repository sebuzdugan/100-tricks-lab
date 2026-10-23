#!/usr/bin/env python3
"""Day 37: count console.log calls the agent added, per request, from the finished repo.
Usage: count_logs.py <workdir> [--json]. Every request names the file(s) it creates or changes (requests.json), so a
console.log in a file is charged to the first request that named that file; files no request named count as 'other'.
Comments are ignored. Also counts other console.* calls and process.stdout.write (ways round the rule, reported only)."""
import json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQ = json.loads((HERE / "requests.json").read_text())["requests"]
CODE = (".js", ".mjs", ".cjs", ".ts", ".mts")

def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(^|[^:'\"`\\])//[^\n]*", r"\1", src)

def count(pat, text):
    return len(re.findall(pat, strip_comments(text)))

def measure(w: Path):
    git = lambda *a: subprocess.run(["git", "-C", str(w), *a], capture_output=True, text=True).stdout
    touched = {f for f in (git("diff", "--name-only", "lab-base").split() + git("ls-files", "--others", "--exclude-standard").split())
               if f.endswith(CODE) and not f.startswith("node_modules/")}
    owner = {}
    for r in REQ:
        for f in r["files"]:
            owner.setdefault(f, r["n"])
    per_req = {r["n"]: 0 for r in REQ}
    other, other_console, stdout_write, files_with = 0, 0, 0, []
    for f in sorted(touched):
        p = w / f
        now = p.read_text(errors="ignore") if p.is_file() else ""
        before = git("show", f"lab-base:{f}")  # empty for a new file
        added = lambda pat: max(0, count(pat, now) - count(pat, before))
        n = added(r"\bconsole\s*\.\s*log\s*\(")
        if n:
            files_with.append(f)
            if f in owner: per_req[owner[f]] += n
            else: other += n
        other_console += added(r"\bconsole\s*\.\s*(?:info|warn|error|debug|table|dir|trace)\s*\(")
        stdout_write += added(r"\bprocess\s*\.\s*stdout\s*\.\s*write\s*\(")
    missing = [f for r in REQ for f in r["files"] if not (w / f).is_file()]
    broken_reqs = [n for n, c in per_req.items() if c]
    return {"breaks": sum(per_req.values()) + other, "first_break": min(broken_reqs) if broken_reqs else None,
            "requests_broken": len(broken_reqs), "per_request": [per_req[r["n"]] for r in REQ], "other_files": other,
            "files_with_console_log": files_with, "other_console": other_console, "stdout_write": stdout_write, "missing": missing}

if __name__ == "__main__":
    m = measure(Path(sys.argv[1]))
    if "--json" in sys.argv:
        print(json.dumps(m))
    else:
        print(f"breaks={m['breaks']} first_break={m['first_break'] or 'none'} requests_broken={m['requests_broken']} "
              f"per_request={','.join(map(str, m['per_request']))} other_files={m['other_files']} other_console={m['other_console']} "
              f"stdout_write={m['stdout_write']} missing={len(m['missing'])}")
