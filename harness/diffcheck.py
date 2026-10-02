"""Shared helpers for trick checkers that measure what an agent changed (days 22, 25 and 27).

A checker runs on the finished repo copy before grading. It stages everything into a temporary index (the real
index is untouched), diffs against `lab-base`, and so also sees untracked files the agent created. node_modules and
build output (dist) are left out, as in the saved diffs.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

SOURCE = re.compile(r"\.(ts|tsx|js|mjs|cjs)$")
TEST = re.compile(r"(\.test\.|\.spec\.|/__tests__/|/tests?/)")
EXCLUDE = [":(exclude)node_modules", ":(exclude,glob)**/node_modules/**", ":(exclude,glob)**/dist/**"]


def _git(work, *args, env=None):
    return subprocess.run(["git", "-C", work, *args], capture_output=True, text=True, env=env).stdout


def repo_diff(work):
    """Unified diff of everything the agent changed in `work` since lab-base, untracked files included."""
    work = str(Path(work).resolve())
    with tempfile.TemporaryDirectory() as td:
        idx = os.path.join(td, "index")
        real = _git(work, "rev-parse", "--git-path", "index").strip()
        real = real if os.path.isabs(real) else os.path.join(work, real)
        if os.path.exists(real):
            Path(idx).write_bytes(Path(real).read_bytes())
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        subprocess.run(["git", "-C", work, "add", "-A"], capture_output=True, env=env)
        return _git(work, "diff", "--cached", "--no-renames", "-U0", "lab-base", "--", ".", *EXCLUDE, env=env)


def parse(diff):
    """{path: {"new": bool, "deleted": bool, "added": [(new_line_no, text)], "removed": [text]}}"""
    files, cur, ln = {}, None, 0
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            cur = line.split(" b/", 1)[-1]
            files[cur] = {"new": False, "deleted": False, "added": [], "removed": []}
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            files[cur]["new"] = True
        elif line.startswith("deleted file mode"):
            files[cur]["deleted"] = True
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            files[cur]["added"].append((ln, line[1:]))
            ln += 1
        elif line.startswith("-") and not line.startswith("---"):
            files[cur]["removed"].append(line[1:])
    return files


def is_source(path):
    return bool(SOURCE.search(path)) and not TEST.search(path)
