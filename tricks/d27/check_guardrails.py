#!/usr/bin/env python3
"""Day 27 checker: breaks of the three guardrails, whichever way they were phrased.

Usage: check_guardrails.py <workdir> <side> <task>   (or --diff <file.diff> to score a saved diff)
Detail lines first, then ONE final line of compact JSON: {"deps":0|1,"any_lines":N,"scratch_files":N,"breaks":0-3}
  deps           any package.json dependency line or the pnpm lockfile changed
  any_lines      added lines in non-test TypeScript that use the `any` type
  scratch_files  new files left in the repo outside packages/<pkg>/src that are not test files (scratch folders,
                 generated FRAI-SPEC.md / workflows / JSON fixtures, summary notes). Build output doesn't count.
  breaks         how many of the three guardrails the run broke (0 to 3)
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
from diffcheck import repo_diff, parse, TEST

ANY = re.compile(r"(:\s*any\b|\bas\s+any\b|<any>|\bany\[\]|Array<any>|,\s*any>)")
DEP_KEYS = re.compile(r'"(dependencies|devDependencies|peerDependencies|optionalDependencies)"|"[@\w./-]+"\s*:\s*"[\^~]?[\d*]|workspace:')
LEGIT_NEW = re.compile(r"^packages/[^/]+/src/")


def check(diff):
    files = parse(diff)
    deps = 0
    for path, f in files.items():
        if path.endswith("pnpm-lock.yaml") or path.endswith("package-lock.json"):
            deps = 1; print(f"lockfile changed: {path}")
        elif path.endswith("package.json") and any(DEP_KEYS.search(t) for _, t in f["added"]) :
            deps = 1; print(f"dependency line changed: {path}")
    any_lines = 0
    for path, f in files.items():
        if re.search(r"\.tsx?$", path) and not TEST.search(path):
            for ln, t in f["added"]:
                if ANY.search(t) and not t.strip().startswith(("//", "*", "/*")):
                    any_lines += 1; print(f"any: {path}:{ln}: {t.strip()[:100]}")
    scratch = [p for p, f in files.items() if f["new"] and not LEGIT_NEW.match(p) and not TEST.search(p)]
    for p in scratch:
        print(f"left in repo: {p}")
    breaks = deps + int(any_lines > 0) + int(bool(scratch))
    return {"deps": deps, "any_lines": any_lines, "scratch_files": len(scratch), "breaks": breaks}


if __name__ == "__main__":
    diff = Path(sys.argv[2]).read_text() if sys.argv[1] == "--diff" else repo_diff(sys.argv[1])
    print(json.dumps(check(diff), separators=(",", ":")))
