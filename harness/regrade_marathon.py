#!/usr/bin/env python3
"""Regrade finished marathons after a grader fix, from their saved per-request diffs (no agent calls).

  python3 harness/regrade_marathon.py <trick>

For every runs/<trick>/raw/<side>-m<n>/ with a marathon.json: rebuild the repo copy request by request (base repo at
lab-base + the overlay + rNN.diff applied in order), grade after each request exactly as the runner does, and rewrite
the rows (passed, kept, final, regressed_later, grade_reason, earlier_failing). The old values are kept in each row as
regraded_from. runs.csv and summary.json are rebuilt from all marathon.json files. Time, cost and tokens don't change.
"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402
import marathon  # noqa: E402


def regrade(tid):
    trick = run.load_trick(tid)
    out_dir = run.LAB / "runs" / tid
    tdir = run.LAB / "tricks" / tid
    all_rows = []
    for md in sorted(p for p in (out_dir / "raw").iterdir() if p.is_dir() and not p.name.startswith("_")):
        mj = md / "marathon.json"
        if not mj.exists():
            continue
        m = json.loads(mj.read_text())
        side = m["side"]
        work = run.WORK_ROOT / f"regrade-{tid}" / md.name
        run.clone_base(work, run.LAB / "base" / trick.get("base", "invoicekit"))
        run.apply_overlay(tdir, trick["sides"][side], work)
        ids = [r["request"] for r in m["rows"]]
        grades_after = {}
        for i, row in enumerate(m["rows"]):
            rid = row["request"]
            diff = md / f"{rid}.diff"
            if diff.exists() and diff.stat().st_size:
                r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(diff)], cwd=work, capture_output=True, text=True)
                if r.returncode:
                    sys.exit(f"{md.name} {rid}: diff does not apply: {r.stderr[:300]}")
            g = marathon.grade(work, ids[: i + 1])
            grades_after[rid] = {k: v["pass"] for k, v in g.items()}
            old = {k: row.get(k) for k in ("passed", "grade_reason")}
            passed = g[rid]["pass"] and not row.get("timeout")
            reason = "PASS" if passed else ("FAIL timeout " if row.get("timeout") else "FAIL ") + "; ".join(g[rid]["failed"][:4])
            if str(row.get("grade_reason", "")).startswith("FAIL marathon time cap"):
                passed, reason = False, row["grade_reason"]
            row.update(passed=passed, grade_reason=reason[:400], earlier_failing=" ".join(k for k in ids[:i] if not g[k]["pass"]))
            if old["passed"] != passed:
                row["regraded_from"] = old
        final = grades_after[ids[-1]]
        for row in m["rows"]:
            rid = row["request"]
            later = [grades_after[k][rid] for k in ids[ids.index(rid):]]
            row["final"] = final[rid]
            row["kept"] = bool(row["passed"] and final[rid])
            row["regressed_later"] = bool(row["passed"] and not all(later))
        m["grades_after"] = grades_after
        mj.write_text(json.dumps(m, indent=1))
        shutil.rmtree(work, ignore_errors=True)
        all_rows += m["rows"]
        flips = sum(1 for r in m["rows"] if "regraded_from" in r)
        print(f"{md.name}: {sum(r['passed'] for r in m['rows'])}/{len(ids)} passed, {sum(r['kept'] for r in m['rows'])} kept, {flips} changed")
    with open(out_dir / "runs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=marathon.FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in all_rows:
            w.writerow(row)
    marathon.summarize(trick, tid, out_dir)


if __name__ == "__main__":
    regrade(sys.argv[1])
