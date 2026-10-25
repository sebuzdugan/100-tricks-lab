#!/usr/bin/env python3
"""Days 46 and 49 (24 Oct rerun on base/subtrack, m5-weekly-plans): which runs actually ran the tests and the real
CLI, from the saved events (read-only). v1 (frai) original: tricks/d46-v1/count_commands.py.

  python3 tricks/d46/count_commands.py d46            # JSON summary to stdout
  python3 tricks/d46/count_commands.py d46 --runs     # plus one line per run

Reads runs/<id>/raw/<side>-<task>-r<n>.events.jsonl (every tool call, PROTOCOL 15 Sep) and the graded row next to
it. Shell commands are the Bash tool calls the agent made (denied ones included: a denied attempt still shows
intent, and is counted separately). Patterns:
  test   harness/evidence.py's TEST_RE, unchanged (vitest/jest, `pnpm|npm|yarn [run] test`, `node --test`)
  build  `tsc` or a `build` script (harness/evidence.py's BUILD_RE; subtrack has no build step, kept for the
         same row shape)
  cli    subtrack's real entry point run as a user would: `node [flags] [./]bin/subtrack.js <command>` (any path
         ending in bin/subtrack.js), `./bin/subtrack.js <command>`, or `subtrack` / `npx subtrack` followed by one of
         its commands (add, list, total, renewals, export, remove); a command that only greps or cats for these
         words is not counted. cli_cmds counts which subtrack commands were run (a chained call counts each)
Per side, graded runs only (infra errors left out):
  ran_tests            runs with at least one test command (day 46's pre-registered count)
  tests_after_last_edit  runs whose last test command came after their last file edit (verified the final code)
  ran_cli / built      runs with at least one CLI run / build (day 49's measures)
  ran_<command>        runs that ran that subtrack command at least once (add, list, total, renewals, export,
                       remove); total, list and export are where a weekly plan's monthly cost shows
  passed_*             the same, among passing runs
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location("evidence", LAB / "harness" / "evidence.py")
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)
TEST_RE, BUILD_RE = evidence.TEST_RE, evidence.BUILD_RE
CMDS = ("add", "list", "total", "renewals", "export", "remove")
_ENTRY = (r"(?:\bnode\s+(?:--\S+\s+)*[\"']?\S*bin/subtrack\.js[\"']?|(?:^|[;&|(]\s*|\bexec\s+)\.?/?\S*bin/subtrack\.js"
          r"|(?:^|[;&|(]\s*|\bexec\s+|\bnpx\s+)subtrack)")
CLI_RE = re.compile(_ENTRY + r"\s+(?:--?\S+(?:\s+\S+)?\s+)*?[\"']?(" + "|".join(CMDS) + r")\b")
LOOKUP = re.compile(r"^\s*(?:grep|cat|head|tail|find|ls|wc|echo|printf)\b")
EDITS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def run_info(ev_path: Path):
    calls, denied = [], set()
    for line in ev_path.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = e.get("message") if isinstance(e.get("message"), dict) else {}
        for b in msg.get("content") if isinstance(msg.get("content"), list) else []:
            if not isinstance(b, dict):
                continue
            if e.get("type") == "assistant" and b.get("type") == "tool_use":
                calls.append((b.get("id"), b.get("name"), (b.get("input") or {}).get("command") or ""))
            elif e.get("type") == "user" and b.get("type") == "tool_result" and b.get("is_error"):
                c = b.get("content")
                text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                if "permission" in text.lower() or "denied" in text.lower():
                    denied.add(b.get("tool_use_id"))
    idx = lambda pred: [i for i, (cid, name, cmd) in enumerate(calls) if pred(cid, name, cmd)]
    is_bash = lambda name: name == "Bash"
    test = idx(lambda cid, n, c: is_bash(n) and cid not in denied and bool(TEST_RE.search(c)))
    cli = idx(lambda cid, n, c: is_bash(n) and cid not in denied and not LOOKUP.match(c) and bool(CLI_RE.search(c)))
    build = idx(lambda cid, n, c: is_bash(n) and cid not in denied and not LOOKUP.match(c) and bool(BUILD_RE.search(c)))
    edits = idx(lambda cid, n, c: n in EDITS)
    cmds = {c: 0 for c in CMDS}
    for i in cli:
        for m in CLI_RE.finditer(calls[i][2]):
            cmds[m.group(1)] += 1
    return {"test_runs": len(test), "cli_runs": len(cli), "builds": len(build), "cli_cmds": cmds,
            "denied_test_or_cli": len(idx(lambda cid, n, c: is_bash(n) and cid in denied and bool(TEST_RE.search(c) or CLI_RE.search(c)))),
            "tests_after_last_edit": bool(test) and (not edits or test[-1] > edits[-1])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trick")
    ap.add_argument("--runs", action="store_true")
    a = ap.parse_args()
    rdir = LAB / "runs" / a.trick / "raw"
    evs = sorted(rdir.glob("*.events.jsonl"))
    if not evs:
        sys.exit(f"no events under {rdir}")
    sides, lines = {}, []
    for ev in evs:
        raw = ev.with_name(ev.name.replace(".events.jsonl", ".json"))
        row = json.loads(raw.read_text())["row"] if raw.exists() else {}
        if row.get("infra_error"):
            continue
        info = run_info(ev)
        s = sides.setdefault(row.get("side", "?"), {"graded": 0, "passed": 0, "ran_tests": 0, "tests_after_last_edit": 0,
                                                   "ran_cli": 0, "built": 0, "passed_ran_tests": 0, "passed_ran_cli": 0,
                                                   "test_runs_total": 0, "cli_runs_total": 0, "denied_test_or_cli": 0,
                                                   **{f"ran_{c}": 0 for c in CMDS}})
        p = bool(row.get("passed"))
        s["graded"] += 1
        s["passed"] += p
        s["ran_tests"] += info["test_runs"] > 0
        s["tests_after_last_edit"] += info["tests_after_last_edit"]
        s["ran_cli"] += info["cli_runs"] > 0
        s["built"] += info["builds"] > 0
        s["passed_ran_tests"] += p and info["test_runs"] > 0
        s["passed_ran_cli"] += p and info["cli_runs"] > 0
        s["test_runs_total"] += info["test_runs"]
        s["cli_runs_total"] += info["cli_runs"]
        s["denied_test_or_cli"] += info["denied_test_or_cli"]
        for c, n in info["cli_cmds"].items():
            s[f"ran_{c}"] += n > 0
        lines.append(f"{ev.name.replace('.events.jsonl', '')}\t{'PASS' if p else 'FAIL'}\t{json.dumps(info)}")
    print(json.dumps({"trick": a.trick, "sides": sides}, indent=1))
    if a.runs:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
