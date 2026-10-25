#!/usr/bin/env python3
"""Stop hook (days 42, 44, 48, both sides): record the repo state at the end of every call. Never blocks, prints
nothing, always exits 0, so the agent sees no difference.

Each time a call ends, the working copy (untracked files included, .gitignore'd files such as node_modules and dist
left out) is written as a git tree object through a temporary index, exactly like harness/run.py's tree_of(): no
commit, no ref, the real index untouched, so `git status` / `git diff` show nothing new. One line per call goes to
<repo copy>-logs/snapshots.log (outside the copy; override with LAB_SNAPSHOT_LOG):

    <unix time>\t<session id>\t<tree sha>

The day's checker (tricks/d42/check_step1.py) restores the first tree logged for a run into a clone and grades it,
so a two- or three-call run reports whether its FIRST call already passed (before review, self-review or proof).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    try:
        inp = json.load(sys.stdin)
    except Exception:
        inp = {}
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or os.getcwd()).resolve()
    log = Path(os.environ.get("LAB_SNAPSHOT_LOG") or f"{root.parent}/{root.name}-logs/snapshots.log")
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(td, "index"))
        g = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, env=env)
        if g("read-tree", "lab-base").returncode != 0:
            g("read-tree", "HEAD")
        g("add", "-A")
        tree = g("write-tree").stdout.strip() or "?"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as fh:
        fh.write(f"{time.time():.3f}\t{inp.get('session_id', '?')}\t{tree}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
