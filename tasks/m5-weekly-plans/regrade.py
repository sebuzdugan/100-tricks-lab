#!/usr/bin/env python3
"""Regrade saved m5-weekly-plans runs after a grader fix, from each run's saved diff. Same as harness/regrade.py, but
on the trick's own base (harness/regrade.py always clones base/frai). Old result kept in the raw row as regraded_from.

  python3 tasks/m5-weekly-plans/regrade.py pilot-m5fix && python3 harness/run.py pilot-m5fix --summarize-only
"""
import csv, json, shutil, subprocess, sys
from pathlib import Path
LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB / "harness"))
import run as R

TASK = "m5-weekly-plans"
tid = sys.argv[1]
out = LAB / "runs" / tid
trick = json.loads((LAB / "tricks" / tid / "trick.json").read_text())
rows = list(csv.DictReader(open(out / "runs.csv")))
for f in sorted((out / "raw").glob(f"*-{TASK}-r*.json")):
    d = json.loads(f.read_text()); row = d["row"]
    if row.get("infra_error"):
        continue
    work = R.WORK_ROOT / tid / "_regrade" / f.stem
    R.clone_base(work, LAB / "base" / trick.get("base", "frai"))
    R.apply_overlay(LAB / "tricks" / tid, trick["sides"][row["side"]], work)
    diff = f.with_suffix(".diff")
    if diff.exists() and diff.stat().st_size:
        a = subprocess.run(["git", "-C", str(work), "apply", "--whitespace=nowarn", str(diff)], capture_output=True, text=True)
        if a.returncode:
            print(f.stem, "diff did not apply:", a.stderr[:200]); continue
    passed, reason = R.grade(TASK, work)
    if row.get("timeout") in (True, "True"):
        passed, reason = False, f"FAIL timeout (grader alone said: {reason})"
    if passed != row["passed"] or reason != row["grade_reason"]:
        row.setdefault("regraded_from", {"passed": row["passed"], "grade_reason": row["grade_reason"]})
        row["passed"], row["grade_reason"] = passed, reason
        f.write_text(json.dumps(d, indent=2))
        for r in rows:
            if r["side"] == row["side"] and r["task"] == TASK and str(r["run"]) == str(row["run"]):
                r["passed"], r["grade_reason"] = passed, reason
        print("regraded", f.stem, "->", reason[:150])
    shutil.rmtree(work, ignore_errors=True)
with open(out / "runs.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=R.CSV_FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
