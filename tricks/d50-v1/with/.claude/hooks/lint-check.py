#!/usr/bin/env python3
"""Day 50 lint and typecheck hook. The SAME file runs on both sides; only the hook event differs.

  with     PostToolUse on Edit|Write|MultiEdit: `lint-check.py post` checks the file just edited
  without  Stop: `lint-check.py stop` checks every file changed since HEAD when the agent tries to finish

The check (both modes): ESLint (the repo's own eslint.config.mjs, errors only, warnings ignored) on JavaScript files
(.js .mjs .cjs) and `tsc --noEmit -p packages/<pkg>/tsconfig.json` for TypeScript files (.ts .mts .cts) in a package
that has a tsconfig; node_modules and dist are skipped. On the untouched baseline tsc is clean for frai-cli,
frai-gate and frai-agent, and ESLint finds 3 errors in frai-core source (key-store.js, documents/helpers.js,
providers/openai.js: unused variables), which this hook reports if the agent edits one of those files.

On errors:
  post  exit 2 with the errors on stderr (Claude Code shows them to the agent; the edit has already happened)
  stop  {"decision": "block", "reason": <errors>} so the agent continues, at most 8 times per session (Claude Code's
        own cap on Stop-hook continuations, enforced here too, as on day 43); the 9th attempt is let through
Output is capped at 30 error lines. Every run is logged outside the repo copy, to <repo>-logs/lint-hook.log
(override with LINT_HOOK_LOG): <unix time>\t<session>\t<mode>\t<errors>\t<seconds>\t<ok|fail|block|cap>
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
TS = re.compile(r"\.(ts|mts|cts)$")
SKIP = re.compile(r"(^|/)(node_modules|dist)/")


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


def check(root: Path, files):
    """Errors as 'path:line:col message (rule)' strings, for the given repo-relative files."""
    files = [f for f in files if f and not SKIP.search(f) and (root / f).is_file()]
    errors = []
    js = [f for f in files if JS.search(f)]
    if js:
        r = subprocess.run([str(root / "node_modules/.bin/eslint"), "--no-warn-ignored", "-f", "json", *js],
                           cwd=root, capture_output=True, text=True, timeout=120)
        try:
            for fr in json.loads(r.stdout or "[]"):
                for m in fr.get("messages", []):
                    if m.get("severity") == 2:
                        errors.append(f"{rel(root, fr['filePath'])}:{m.get('line', 0)}:{m.get('column', 0)} "
                                      f"{m.get('message', '').strip()} ({m.get('ruleId') or 'parse'})")
        except json.JSONDecodeError:
            errors.append("eslint failed to run: " + (r.stderr or r.stdout).strip()[:300])
    pkgs = sorted({f.split("/")[1] for f in files if TS.search(f) and f.startswith("packages/") and f.count("/") >= 2
                   and (root / "packages" / f.split("/")[1] / "tsconfig.json").is_file()})
    for pkg in pkgs:
        r = subprocess.run([str(root / "node_modules/.bin/tsc"), "--noEmit", "-p", f"packages/{pkg}/tsconfig.json"],
                           cwd=root, capture_output=True, text=True, timeout=180)
        for line in (r.stdout + r.stderr).splitlines():
            if re.search(r"error TS\d+", line):
                errors.append(line.strip() if line.startswith("packages/") else f"packages/{pkg}/{line.strip()}")
    return errors


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
        if not f or not (JS.search(f) or TS.search(f)) or SKIP.search(f):
            return 0
        errs = check(root, [f])
    else:
        errs = check(root, changed_files(root))
    secs = time.time() - t0
    body = "Lint/typecheck errors:\n" + "\n".join(errs[:30]) + (f"\n... and {len(errs) - 30} more" if len(errs) > 30 else "")
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
