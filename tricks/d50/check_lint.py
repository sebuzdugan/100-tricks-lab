#!/usr/bin/env python3
"""Day 50 checker (24 Oct rerun on base/subtrack, m5-weekly-plans): check errors left at the end, and what the hook
cost. v1 (frai: ESLint + tsc) original: tricks/d50-v1/check_lint.py.

Usage (run.py's extra_check): check_lint.py <workdir> <side> <task>. Detail lines, then ONE final line of JSON:

  {"syntax":N,"tests":N,"new":N,"hook_runs":N,"hook_fails":N,"hook_s":X}

  syntax       JavaScript files changed since lab-base that `node --check` rejects (the very same check the hooks
               run: tricks/d50/with/.claude/hooks/lint-check.py, identical on both sides)
  tests        visible tests failing at the end (`node --test` with the TAP reporter, parsed by
               tasks/m5-weekly-plans/grade.py's run_tap; same tests `npm test` runs)
  new          errors the agent added: syntax errors plus failing tests that do NOT fail on lab-base (lab-base
               already fails one visible test, so a run that leaves it red adds nothing). The pre-registered count.
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
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


lc = load("lintcheck", LAB / "tricks/d50/with/.claude/hooks/lint-check.py")
grade = load("m5grade", LAB / "tasks/m5-weekly-plans/grade.py")


def failing(w: Path):
    code, res, _ = grade.run_tap(w, [], timeout=120)
    # file-level TAP lines ("test/x.test.js") are summaries of the tests inside them, not tests
    return {t for t, s in res if s == "fail" and not t.startswith("test/") and not t.endswith(".test.js")}, code


def base_failing(work: Path):
    with tempfile.TemporaryDirectory() as td:
        arch = subprocess.run(["git", "-C", str(work), "archive", "lab-base"], capture_output=True)
        subprocess.run(["tar", "-x", "-C", td], input=arch.stdout, capture_output=True)
        return failing(Path(td))[0]


def main():
    work = Path(sys.argv[1]).resolve()
    g = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True).stdout.split("\n")
    files = sorted(n for n in set(g("diff", "--name-only", "lab-base")) | set(g("ls-files", "--others", "--exclude-standard"))
                   if n and (work / n).is_file())
    syn = lc.syntax_errors(work, files)
    now, code = failing(work)
    if code != 0 and not now:
        now = {f"(suite exit {code}, no test named)"}
    added = now - base_failing(work)
    for e in syn:
        print("left:", e)
    for t in sorted(now):
        print("failing test:", t, "(new)" if t in added else "(fails on lab-base too)")
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
    print(json.dumps({"syntax": len(syn), "tests": len(now), "new": len(syn) + len(added),
                      "hook_runs": runs, "hook_fails": fails, "hook_s": round(secs, 1)}, separators=(",", ":")))


if __name__ == "__main__":
    main()
