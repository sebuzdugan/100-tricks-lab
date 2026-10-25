#!/usr/bin/env python3
"""Day 49 checker (24 Oct rerun on base/subtrack, m5-weekly-plans): does the real command work?
v1 (frai, h2) original: tricks/d49-v1/check_cli.py.

Usage (run.py's extra_check): check_cli.py <workdir> <side> <task>. Detail lines, then ONE final line of JSON:

  {"cli":true|false|null,"export":true|false|null,"cli_reason":"..."}

  cli      the CLI stage of the task's own grader (tasks/m5-weekly-plans/grade.py cli_check, imported, unchanged):
           in a temp folder, `node bin/subtrack.js add` a monthly and a weekly plan, then `total`, `list` and
           `renewals` must show the weekly plan correctly. This is exactly the grader's B2, so `cli` equals the
           row's B2 field; it is repeated here so day 49's count reads the same way as v1's.
  export   the same two plans through `node bin/subtrack.js export`: the weekly plan's monthly_cost column must
           read 52.00 (€12 a week × 52 ÷ 12, the ticket's own example). The grader checks export only through a
           hidden unit test (B3); this is the real-command view of the same requirement, a user running export.
  null     the task has no subtrack CLI (anything but m5-weekly-plans)

m5's grader does not stop at its first failure (every trap is scored), so unlike v1 the grade reason already holds
the CLI result; the checker still runs on an APFS clone of the finished repo (deleted afterwards) so the repo run.py
grades is not touched. Day 49's count: graded runs with cli == false (and, reported next to it, export == false).
"""
import csv
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent
TASK = "m5-weekly-plans"


def grader():
    spec = importlib.util.spec_from_file_location("m5grade", LAB / "tasks" / TASK / "grade.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def export_check(g, w: Path):
    tmp = Path(tempfile.mkdtemp(prefix="m5-export-"))
    f = str(tmp / "subs.json")
    env = dict(g.node_env(), HOME=str(tmp))
    env.pop("SUBTRACK_FILE", None)
    run = lambda *a: subprocess.run(["node", str(w / "bin" / "subtrack.js"), *a, "--file", f], cwd=tmp, capture_output=True,
                                    text=True, timeout=20, env=env, stdin=subprocess.DEVNULL)
    try:
        for args in (("add", "Music", "9.99", "--since", "2026-10-01"), ("add", "Cleaner", "12", "--every", "week", "--since", "2026-10-20")):
            r = run(*args)
            if r.returncode != 0:
                return False, f"`subtrack {' '.join(args)}` exits {r.returncode}"
        r = run("export", "--today", "2026-10-24")
        if r.returncode != 0:
            return False, f"`subtrack export` exits {r.returncode}"
        rows = list(csv.DictReader(io.StringIO(r.stdout)))
        row = next((x for x in rows if x.get("name") == "Cleaner"), None)
        if row is None:
            return False, "export has no Cleaner row"
        if row.get("monthly_cost") != "52.00":
            return False, f"export shows the weekly plan's monthly_cost as {row.get('monthly_cost')!r}, expected 52.00"
        return True, "ok"
    except subprocess.TimeoutExpired:
        return False, "export timed out"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    work, side, task = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
    res = {"cli": None, "export": None, "cli_reason": "no subtrack CLI for this task"}
    if task == TASK:
        g = grader()
        clone = work.parent / f"{work.name}-cli"
        shutil.rmtree(clone, ignore_errors=True)
        if subprocess.run(["cp", "-cR", str(work), str(clone)], capture_output=True).returncode != 0:
            subprocess.run(["cp", "-R", str(work), str(clone)], check=True)
        try:
            ok, why = g.cli_check(clone)
            eok, ewhy = export_check(g, clone)
        finally:
            shutil.rmtree(clone, ignore_errors=True)
        res = {"cli": ok, "export": eok, "cli_reason": "PASS" if ok and eok else
               "; ".join(x for x in ((None if ok else why), (None if eok else "export: " + ewhy)) if x)}
        print(f"CLI stage (grader B2): {'PASS' if ok else 'FAIL'} {why}")
        print(f"export of a weekly plan: {'PASS' if eok else 'FAIL'} {ewhy}")
    res["cli_reason"] = " ".join(str(res["cli_reason"]).replace('"', "'").split())[:140]
    print(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
