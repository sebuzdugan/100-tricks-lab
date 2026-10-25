#!/usr/bin/env python3
"""Days 42, 44 and 48 checker: did the run's FIRST call already pass, before the review / self-review / proof turn?

Usage (run.py's extra_check): check_step1.py <workdir> <side> <task>. Detail lines first, then ONE final line of
compact JSON (run.py keeps the last line, cut at 200 characters, in the row's `extra`):

  {"snaps":N,"chg":0|1,"c2":0|1|null,"s1":true|false|null,"s1_reason":"..."}

  snaps      Stop-hook snapshots logged for this repo copy (one per call that ended normally; the overlay
             tricks/d42/snap installs the hook on both sides). Only lines written after this copy was created are
             counted, so a stale log from an earlier run at the same path is ignored (same rule as day 10).
  chg        1 if the repo at the end differs from the first snapshot (the later calls changed something)
  c2         1 if the second snapshot differs from the first (day 42: the read-only reviewer call changed files,
             which should never happen; null with fewer than two snapshots)
  s1         the task's own accept.sh on a clone restored to the first snapshot (null: no snapshot, e.g. the first
             call timed out or crashed before its Stop hook ran)
  s1_reason  the grader's last line for that clone, shortened

The clone is an APFS copy of the finished repo (node_modules and built dist kept, as graders build from source),
reset to the first snapshot's tree with `git read-tree -u --reset`, graded with LAB_LOG_DIR=<repo>-logs/step1, then
deleted. The finished repo itself is not touched, so run.py's own grading afterwards is unchanged.

Read with the final grade: s1 false and passed true = a hidden failure fixed by the later calls; s1 true and
passed false = a passing first attempt broken by them.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent


def tree_of(work):
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(td, "index"))
        g = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True, env=env)
        g("read-tree", "lab-base")
        g("add", "-A")
        return g("write-tree").stdout.strip()


def snapshots(work: Path):
    log = Path(os.environ.get("LAB_SNAPSHOT_LOG") or f"{work}-logs/snapshots.log")
    st = os.stat(work)
    since = getattr(st, "st_birthtime", st.st_ctime) - 2
    out = []
    if log.is_file():
        for line in log.read_text().splitlines():
            parts = line.split("\t")
            try:
                if len(parts) == 3 and float(parts[0]) >= since and parts[2] != "?":
                    out.append(parts)
            except ValueError:
                pass
    return out


def main():
    work, side, task = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
    snaps = snapshots(work)
    res = {"snaps": len(snaps), "chg": None, "c2": int(snaps[1][2] != snaps[0][2]) if len(snaps) > 1 else None,
           "s1": None, "s1_reason": ""}
    if snaps:
        first = snaps[0][2]
        res["chg"] = int(tree_of(work) != first)
        clone = work.parent / f"{work.name}-step1"
        shutil.rmtree(clone, ignore_errors=True)
        if subprocess.run(["cp", "-cR", str(work), str(clone)], capture_output=True).returncode != 0:
            subprocess.run(["cp", "-R", str(work), str(clone)], check=True)
        try:
            g = lambda *a: subprocess.run(["git", "-C", str(clone), *a], capture_output=True, text=True)
            g("add", "-A")  # so files created after the first call are in the index and read-tree removes them
            r = g("read-tree", "-u", "--reset", first)
            if r.returncode != 0:
                res["s1_reason"] = "restore failed: " + r.stderr.strip()[:80]
            else:
                g("reset", "-q")  # index back to lab-base (HEAD); working tree stays at the first snapshot
                logdir = Path(f"{work}-logs") / "step1"
                acc = LAB / "tasks" / task / "accept.sh"
                p = subprocess.run([str(acc), str(clone)], capture_output=True, text=True, timeout=240,
                                   env=dict(os.environ, LAB_LOG_DIR=str(logdir)))
                last = (p.stdout.strip().splitlines() or ["(no output)"])[-1]
                res["s1"] = p.returncode == 0
                res["s1_reason"] = last
                print(f"first snapshot {first[:12]} graded: {last}")
        finally:
            shutil.rmtree(clone, ignore_errors=True)
    for ts, sid, tree in snaps:
        print(f"snapshot {ts} session {sid[:8]} tree {tree[:12]}")
    # keep the JSON line under run.py's 200-character cut
    base = json.dumps({k: v for k, v in res.items() if k != "s1_reason"}, separators=(",", ":"))
    room = 200 - len(base) - len(',"s1_reason":""') - 4
    reason = re.sub(r"\s*\(see [^)]*\)", "", res["s1_reason"]).replace('"', "'").replace("\\", "/")
    res["s1_reason"] = reason[:max(room, 0)]
    print(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
