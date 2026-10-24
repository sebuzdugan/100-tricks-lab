#!/usr/bin/env python3
"""Day 49 checker: does the real command work, whatever the unit tests say?

Usage (run.py's extra_check): check_cli.py <workdir> <side> <task>. Detail lines, then ONE final line of JSON:

  {"cli":true|false|null,"cli_reason":"..."}

Each hard task's grader stops at its first failure, so a run that fails the hidden unit tests never reaches the
CLI checks and the grade reason alone can't say whether the command worked. This checker runs ONLY the CLI stage
of the task's own grader, on an APFS clone of the finished repo (deleted afterwards; the repo run.py grades is not
touched): it builds the packages that stage needs with tsc, exactly as accept.sh does, then runs the same hidden
CLI script or commands. null = the task has no CLI stage (t2, t2x: frai-core is a library).

  h1  frai-gate and frai-cli built; frai-gate check --json and frai gate check on the hidden resolved/raw drafts
  h2  frai-cli built; tasks/h2-eval-thresholds/hidden/lab_h2_cli.mjs
  h3  frai-cli and frai-agent built; hidden/lab_h3_cli.mjs
  h4  frai-cli and frai-agent built; hidden/lab_h4_cli.mjs with the hidden demo copy

Day 49's count is CLI-level hidden failures per side: graded runs with cli == false.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent
BUILDS = {"h1": ["frai-gate", "frai-cli"], "h2": ["frai-cli"], "h3": ["frai-cli", "frai-agent"], "h4": ["frai-cli", "frai-agent"]}


def first_fail(out):
    return next((l[5:] for l in out.splitlines() if l.startswith("FAIL")), out.strip().splitlines()[-1] if out.strip() else "")


def cli_stage(key, task, w: Path):
    H = LAB / "tasks" / task / "hidden"
    for pkg in BUILDS[key]:
        r = subprocess.run(["npx", "tsc", "--project", "tsconfig.json"], cwd=w / "packages" / pkg, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return False, f"{pkg} does not build"
    if key == "h1":
        F, G, C = H / "lab_h1_fixtures", w / "packages/frai-gate/dist/cli.js", w / "packages/frai-cli/dist/index.js"
        with tempfile.TemporaryDirectory() as T:
            for f in ("draft-raw.md", "draft-resolved.md"):
                shutil.copy(F / f, T)
            r = subprocess.run(["node", str(G), "check", "draft-resolved.md", "--json"], cwd=T, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return False, f"frai-gate check on the resolved draft exits {r.returncode}"
            try:
                d = json.loads(r.stdout)
                ok = set(d) == {"spec", "verdict", "tier", "findings"} and d["verdict"] == "PASS" and d["tier"] == "limited"
            except Exception:
                ok = False
            if not ok:
                return False, "frai-gate check --json on the resolved draft is not a PASS with the usual JSON shape"
            r = subprocess.run(["node", str(C), "gate", "check", "draft-resolved.md"], cwd=T, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return False, f"frai gate check on the resolved draft exits {r.returncode}"
            r = subprocess.run(["node", str(C), "gate", "check", "draft-raw.md"], cwd=T, capture_output=True, text=True, timeout=60)
            if r.returncode != 1:
                return False, f"frai gate check on the raw draft exits {r.returncode}, expected 1"
        return True, "PASS"
    args = {"h2": [str(w)], "h3": [str(w)], "h4": [str(w), str(H / "lab_h4_demo")]}[key]
    r = subprocess.run(["node", str(H / f"lab_{key}_cli.mjs"), *args], capture_output=True, text=True, timeout=240)
    return (True, "PASS") if r.returncode == 0 else (False, first_fail(r.stdout) or f"exit {r.returncode}")


def main():
    work, side, task = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
    key = task.split("-")[0]
    res = {"cli": None, "cli_reason": "no CLI stage for this task"}
    if key in BUILDS:
        clone = work.parent / f"{work.name}-cli"
        shutil.rmtree(clone, ignore_errors=True)
        if subprocess.run(["cp", "-cR", str(work), str(clone)], capture_output=True).returncode != 0:
            subprocess.run(["cp", "-R", str(work), str(clone)], check=True)
        try:
            ok, why = cli_stage(key, task, clone)
        except subprocess.TimeoutExpired as e:
            ok, why = False, f"timed out: {' '.join(map(str, e.cmd))[:60]}"
        finally:
            shutil.rmtree(clone, ignore_errors=True)
        res = {"cli": ok, "cli_reason": why}
        print(f"CLI stage for {task}: {'PASS' if ok else 'FAIL'} {why}")
    res["cli_reason"] = " ".join(str(res["cli_reason"]).replace('"', "'").split())[:150]
    print(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
