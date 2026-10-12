#!/usr/bin/env python3
"""Day 25 checker: comment lines the agent added to non-test source files.

Usage: check_comments.py <workdir> <side> <task>   (or --diff <file.diff> to score a saved diff)
Detail lines first, then ONE final line of compact JSON: {"comment_lines":N,"broke":0|1}
A comment line is an added line that starts with //, /*, * or */, or ends in a // comment after code. Test files,
build output and node_modules don't count. broke = 1 when the run added at least one comment line.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
from diffcheck import repo_diff, parse, is_source

START = re.compile(r"^\s*(//|/\*|\*/|\*(\s|$))")
TRAIL = re.compile(r"[;{})\],]\s*//\s")


def count(diff):
    n = 0
    for path, f in parse(diff).items():
        if not is_source(path):
            continue
        for ln, text in f["added"]:
            if START.match(text) or TRAIL.search(text):
                n += 1
                print(f"{path}:{ln}: {text.strip()[:100]}")
    return n


if __name__ == "__main__":
    diff = Path(sys.argv[2]).read_text() if sys.argv[1] == "--diff" else repo_diff(sys.argv[1])
    n = count(diff)
    print(json.dumps({"comment_lines": n, "broke": int(n > 0)}, separators=(",", ":")))
