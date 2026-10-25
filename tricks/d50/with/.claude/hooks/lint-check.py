#!/usr/bin/env python3
"""Day 50 check hook. The SAME file runs on both sides; only the hook event differs.

  with     PostToolUse on Edit|Write|MultiEdit: `lint-check.py post` runs after an edit to a JavaScript file
  without  Stop: `lint-check.py stop` runs when the agent tries to finish

The check (both modes): `node --check` on JavaScript files (.js .mjs .cjs; node_modules skipped), the file just
edited in post mode, every JavaScript file changed since HEAD in stop mode, then the project's own `npm test`.

On errors (a syntax error, or `npm test` failing):
  post  exit 2 with the errors on stderr (Claude Code shows them to the agent; the edit has already happened)
  stop  {"decision": "block", "reason": <errors>} so the agent continues, at most 8 times per session (Claude Code's
        own cap on Stop-hook continuations, enforced here too); the 9th attempt is let through
Output: at most 30 error lines (one per syntax error, one per failing test), then the last lines of the test output.
Every run is logged outside the repo copy, to <repo>-logs/lint-hook.log (override with LINT_HOOK_LOG):
<unix time>\t<session>\t<mode>\t<errors>\t<seconds>\t<ok|fail|block|cap>
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CAP = 8
JS = re.compile(r"\.(js|mjs|cjs)$")
SKIP = re.compile(r"(^|/)node_modules/")
FAILED_TEST = re.compile(r"^\s*(?:✖|not ok \d+ -)\s+(.*?)(?:\s+\([\d.]+m?s\))?\s*$")


def rel(root: Path, f: str) -> str:
    p = Path(f)
    p = p if p.is_absolute() else root / p
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return ""


def changed_files(root: Path):
    g = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True).stdout.split("\n")
    names = set(g("diff", "--name-only", "HEAD")) | set(g("ls-files", "--others", "--exclude-standard"))
    return sorted(n for n in names if n and (root / n).is_file())


def syntax_errors(root: Path, files):
    """'path: message' for each JavaScript file that `node --check` rejects."""
    out = []
    for f in files:
        if not f or not JS.search(f) or SKIP.search(f) or not (root / f).is_file():
            continue
        r = subprocess.run(["node", "--check", f], cwd=root, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            msg = next((l.strip() for l in r.stderr.splitlines() if re.match(r"\s*\w*Error\b", l)), r.stderr.strip()[:200])
            out.append(f"{f}: {msg}")
    return out


def run_tests(root: Path):
    """(failing test names, output tail, passed?) for `npm test`."""
    try:
        r = subprocess.run(["npm", "test"], cwd=root, capture_output=True, text=True, timeout=170,
                           env=dict(os.environ, CI="true", NO_COLOR="1", FORCE_COLOR="0"))
    except subprocess.TimeoutExpired:
        return ["npm test timed out after 170 seconds"], "", False
    out = r.stdout + r.stderr
    names = []
    for line in out.splitlines():
        m = FAILED_TEST.match(line)
        if m and m.group(1) and not m.group(1).startswith("failing tests"):
            n = f"failing test: {m.group(1)}"
            if n not in names:
                names.append(n)
    if r.returncode != 0 and not names:
        names = [f"npm test exited {r.returncode}"]
    return names, "\n".join(out.strip().splitlines()[-25:]), r.returncode == 0


def check(root: Path, files):
    """Errors (syntax errors, then failing tests) and the test output tail, for the given repo-relative files."""
    errors = syntax_errors(root, files)
    names, tail, ok = run_tests(root)
    if not ok:
        errors += names
    return errors, ("" if ok else tail)


def log_line(root: Path, sid, mode, n, secs, decision):
    log = Path(os.environ.get("LINT_HOOK_LOG") or f"{root.parent}/{root.name}-logs/lint-hook.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    blocks = 0
    if log.is_file() and decision == "block":
        blocks = sum(1 for l in log.read_text().splitlines() if l.split("\t")[1:3] == [sid, mode] and l.endswith("\tblock"))
        if blocks >= CAP:
            decision = "cap"
    with open(log, "a") as fh:
        fh.write(f"{time.time():.3f}\t{sid}\t{mode}\t{n}\t{secs:.1f}\t{decision}\n")
    return decision


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    try:
        inp = json.load(sys.stdin)
    except Exception:
        inp = {}
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or os.getcwd()).resolve()
    sid = inp.get("session_id", "?")
    t0 = time.time()
    if mode == "post":
        f = rel(root, (inp.get("tool_input") or {}).get("file_path") or "")
        if not f or not JS.search(f) or SKIP.search(f):
            return 0
        errs, tail = check(root, [f])
    else:
        errs, tail = check(root, changed_files(root))
    secs = time.time() - t0
    body = ("Check errors:\n" + "\n".join(errs[:30]) + (f"\n... and {len(errs) - 30} more" if len(errs) > 30 else "")
            + (f"\n\n`npm test` output (last lines):\n{tail}" if tail else ""))
    if not errs:
        log_line(root, sid, mode, 0, secs, "ok")
        return 0
    if mode == "post":
        log_line(root, sid, mode, len(errs), secs, "fail")
        print(body, file=sys.stderr)
        return 2
    if log_line(root, sid, mode, len(errs), secs, "block") == "block":
        print(json.dumps({"decision": "block", "reason": body}))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as e:  # a broken check must never wedge the agent
        print(f"lint-check hook error: {e}", file=sys.stderr)
        code = 0
    sys.exit(code)
