#!/usr/bin/env python3
"""Days 42, 44 and 48: first call vs end of run, per side, from a finished run folder (read-only).

  python3 tricks/d42-v1/count_steps.py d44-v1                      # JSON summary to stdout
  python3 tricks/d42-v1/count_steps.py d42-v1 --review-step 1 --sheet /path/review_sheet.csv

Reads runs/<id>/raw/<side>-<task>-r<n>.json: the graded row (passed, cost, minutes, infra error) and the row's
`extra`, written by tricks/d42-v1/check_step1.py ({"s1": first call passed?, "chg": later calls changed the repo?}).
Per side, graded runs only (infra errors left out, as in the verdict rule):

  first_call_passes  runs whose first call alone passed the hidden tests
  fixed_by_later     first call failed, end of run passed   (day 44: "hidden failures fixed by the review turn";
                                                            day 48: "... by the proof turn"; day 42: by review+fix)
  broken_by_later    first call passed, end of run failed
  later_changed      runs where the later calls changed the repo at all
  cost_per_pass / minutes_per_pass   total cost (minutes) over all graded runs / passes (E6 receipts)

--sheet writes one CSV row per issue in the reviewer's message (day 42: step_results[1], the fresh reviewer's
final message; calls are writer, reviewer, fixer) for hand labelling, the same way private/v3/false-done was
labelled. Label column, one of:
  real-bug     the issue names a line or behaviour that a hidden test the FIRST call's code fails on checks
               (s1_reason and the step1 logs under <repo>-logs/step1 name the failing tests)
  false-alarm  the issue claims a defect that isn't one (the code does what the task asks there)
  nit          style, naming, docs or a suggestion with no claim that behaviour is wrong
The pre-registered day-42 count is real-bug vs false-alarm per side; nits are reported, not counted.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent
# a top-level item: "1." / "1)" / "### 2." / "**3." / "Issue 4:" anywhere at the start, or an unindented bullet;
# indented sub-bullets and other lines are continuation lines of the current item
ITEM = re.compile(r"^(?:\s{0,1}(?:#{1,4}\s*)?(?:\*\*)?(?:\d+[.)]|Issue\s*\d+[:.]?)|[-*•])\s+", re.I)


def load(tid):
    rows = []
    for p in sorted((LAB / "runs" / tid / "raw").glob("*.json")):
        d = json.loads(p.read_text())
        row, claude = d.get("row", {}), d.get("claude", {})
        try:
            extra = json.loads(row.get("extra") or "{}")
        except json.JSONDecodeError:
            extra = {}
        rows.append({"file": p.name, "row": row, "claude": claude, "extra": extra if isinstance(extra, dict) else {}})
    return rows


def issues(text):
    """Split a review into list items (numbered, bulleted or '### 1.' headings); continuation lines stay with their item."""
    out, cur = [], None
    for line in (text or "").splitlines():
        if ITEM.match(line):
            if cur:
                out.append(cur.strip())
            cur = ITEM.sub("", line, count=1)
        elif cur is not None and line.strip():
            cur += " " + line.strip()
    if cur:
        out.append(cur.strip())
    return out or ([text.strip()] if text and text.strip() else [])


def side_summary(runs):
    g = [r for r in runs if not r["row"].get("infra_error")]
    passed = [r for r in g if r["row"].get("passed")]
    s1 = [r for r in g if r["extra"].get("s1") is not None]
    cost = sum(float(r["row"].get("cost_usd") or 0) for r in g)
    mins = sum(float(r["row"].get("duration_min") or 0) for r in g)
    return {
        "graded": len(g), "passed": len(passed), "with_first_call_grade": len(s1),
        "first_call_passes": sum(1 for r in s1 if r["extra"]["s1"]),
        "fixed_by_later": sum(1 for r in s1 if not r["extra"]["s1"] and r["row"].get("passed")),
        "broken_by_later": sum(1 for r in s1 if r["extra"]["s1"] and not r["row"].get("passed")),
        "later_changed": sum(1 for r in g if r["extra"].get("chg") == 1),
        "cost_per_pass": round(cost / len(passed), 3) if passed else None,
        "minutes_per_pass": round(mins / len(passed), 2) if passed else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trick")
    ap.add_argument("--review-step", type=int, help="index into claude.step_results holding the review (day 42: 1)")
    ap.add_argument("--sheet", help="write the hand-labelling CSV here")
    a = ap.parse_args()
    rows = load(a.trick)
    if not rows:
        sys.exit(f"no raw rows under runs/{a.trick}/raw")
    out = {"trick": a.trick, "sides": {s: side_summary([r for r in rows if r["row"].get("side") == s]) for s in ("with", "without")}}
    if a.sheet and a.review_step is not None:
        n = 0
        with open(a.sheet, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["file", "side", "task", "run", "first_call_passed", "first_call_reason", "final_passed", "issue_no", "issue", "label"])
            for r in rows:
                if r["row"].get("infra_error"):
                    continue
                steps = r["claude"].get("step_results") or []
                review = steps[a.review_step] if len(steps) > a.review_step else ""
                for i, t in enumerate(issues(review), 1):
                    w.writerow([r["file"], r["row"].get("side"), r["row"].get("task"), r["row"].get("run"), r["extra"].get("s1"),
                                r["extra"].get("s1_reason", ""), r["row"].get("passed"), i, t[:1500], ""])
                    n += 1
        out["sheet"] = {"path": a.sheet, "issues": n}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
