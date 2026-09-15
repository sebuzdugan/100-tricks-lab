#!/usr/bin/env python3
"""Regrade saved runs after a grader fix, from each run's saved diff (the run folders are cleaned up).

  python3 harness/regrade.py d02 h2-eval-thresholds      # every run of that task, both sides
  python3 harness/regrade.py d02 --crashed               # list runs that crashed (no turns) to rerun

Applies runs/<id>/raw/<side>-<task>-r<n>.diff to a fresh copy of base/frai, runs tasks/<task>/accept.sh, and rewrites
the row in the raw json and runs.csv (old result kept as regraded_from). Then re-summarize with run.py --summarize-only.
"""
import csv, json, subprocess, sys
from pathlib import Path
LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "harness"))
import run as R

tid = sys.argv[1]
out = LAB / "runs" / tid
if "--crashed" in sys.argv:
    for f in sorted((out / "raw").glob("*.json")):
        d = json.loads(f.read_text())
        if not d["claude"].get("num_turns") and not d["row"].get("infra_error"):
            print(f.name, d["row"]["duration_min"], "min, no turns")
    sys.exit()
task = sys.argv[2]
rows = list(csv.DictReader(open(out / "runs.csv")))
changed = 0
for f in sorted((out / "raw").glob(f"*-{task}-r*.json")):
    d = json.loads(f.read_text()); row = d["row"]
    work = R.WORK_ROOT / tid / "_regrade" / f.stem
    R.clone_base(work)
    trick = json.loads((LAB / "tricks" / tid / "trick.json").read_text())
    R.apply_overlay(LAB / "tricks" / tid, trick["sides"][row["side"]], work)
    diff = f.with_suffix(".diff")
    if diff.exists() and diff.stat().st_size:
        a = subprocess.run(["git", "-C", str(work), "apply", "--whitespace=nowarn", str(diff)], capture_output=True, text=True)
        if a.returncode:
            print(f.stem, "diff did not apply:", a.stderr[:200]); continue
    passed, reason = R.grade(task, work)
    if passed != row["passed"] or reason != row["grade_reason"]:
        row.setdefault("regraded_from", {"passed": row["passed"], "grade_reason": row["grade_reason"]})
        row["passed"], row["grade_reason"] = passed, reason
        d["row"] = row; f.write_text(json.dumps(d, indent=2)); changed += 1
        for r in rows:
            if r["side"] == row["side"] and r["task"] == task and str(r["run"]) == str(row["run"]):
                r["passed"], r["grade_reason"] = str(passed), reason
    print(f.stem, "PASS" if passed else "FAIL", reason[:100])
with open(out / "runs.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=R.CSV_FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print("changed", changed)
