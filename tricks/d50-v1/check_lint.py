#!/usr/bin/env python3
"""Day 50 checker: lint and type errors left at the end, and what the hook cost.

Usage (run.py's extra_check): check_lint.py <workdir> <side> <task>. Detail lines, then ONE final line of JSON:

  {"lint":N,"type":N,"new":N,"hook_runs":N,"hook_fails":N,"hook_s":X}

  lint, type   ESLint errors / tsc errors left at the end in the files changed since lab-base, found with the very
               same check the hooks run (tricks/d50/with/.claude/hooks/lint-check.py, identical on both sides)
  new          errors the agent added: lint errors minus the lint errors those same files had at lab-base (ESLint on
               `git show lab-base:<file>` via --stdin), plus all type errors (tsc is clean on the baseline for
               frai-cli, frai-gate and frai-agent, measured 23 Oct). The pre-registered count is `new`.
  hook_runs    times the hook ran in this run (PostToolUse on the with side, Stop on the without side)
  hook_fails   times it reported errors to the agent (post: exit 2; stop: a block, the cap included)
  hook_s       seconds spent inside the hook, summed (part of the run's minutes)

Same stale-log rule as day 10: only log lines written after this repo copy was created count.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location("lintcheck", LAB / "tricks/d50/with/.claude/hooks/lint-check.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)


def base_lint_errors(work: Path, f: str) -> int:
    src = subprocess.run(["git", "-C", str(work), "show", f"lab-base:{f}"], capture_output=True, text=True)
    if src.returncode != 0:
        return 0  # new file
    r = subprocess.run([str(work / "node_modules/.bin/eslint"), "--no-warn-ignored", "-f", "json", "--stdin", "--stdin-filename", f],
                       cwd=work, input=src.stdout, capture_output=True, text=True, timeout=120)
    try:
        return sum(1 for fr in json.loads(r.stdout or "[]") for m in fr.get("messages", []) if m.get("severity") == 2)
    except json.JSONDecodeError:
        return 0


def main():
    work = Path(sys.argv[1]).resolve()
    g = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True).stdout.split("\n")
    files = sorted(n for n in set(g("diff", "--name-only", "lab-base")) | set(g("ls-files", "--others", "--exclude-standard"))
                   if n and (work / n).is_file())
    errs = lc.check(work, files)
    type_errs = [e for e in errs if "error TS" in e]
    lint_errs = [e for e in errs if "error TS" not in e]
    js = [f for f in files if lc.JS.search(f) and not lc.SKIP.search(f)]
    base = sum(base_lint_errors(work, f) for f in js)
    for e in errs:
        print("left:", e)
    st = os.stat(work)
    since = getattr(st, "st_birthtime", st.st_ctime) - 2
    log = Path(os.environ.get("LINT_HOOK_LOG") or f"{work}-logs/lint-hook.log")
    runs = fails = 0
    secs = 0.0
    if log.is_file():
        for line in log.read_text().splitlines():
            p = line.split("\t")
            try:
                if len(p) == 6 and float(p[0]) >= since:
                    runs += 1
                    fails += p[5] in ("fail", "block", "cap")
                    secs += float(p[4])
            except ValueError:
                pass
    print(json.dumps({"lint": len(lint_errs), "type": len(type_errs), "new": max(0, len(lint_errs) - base) + len(type_errs),
                      "hook_runs": runs, "hook_fails": fails, "hook_s": round(secs, 1)}, separators=(",", ":")))


if __name__ == "__main__":
    main()
