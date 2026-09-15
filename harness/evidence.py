#!/usr/bin/env python3
"""What the agent actually did, run by run, from the saved event logs.

  python3 harness/evidence.py d01          # writes runs/d01/evidence.json and prints a readable digest

Reads runs/<id>/raw/<side>-<task>-r<n>.events.jsonl (stream-json events: every tool call and result) plus the
graded row. Per run: the sequence of actions (reads, searches, edits, shell commands), tests and builds it ran,
denied commands, files it changed, errors it hit, how it described its own result, and whether the hidden tests
agreed. Per side: totals and averages. Then "moments": concrete, checkable things worth showing in a post, such
as a run that said it was done but failed the hidden tests, or a side that kept trying a denied command.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
TASK_PKGS = {"t1": {"frai-cli"}, "t2": {"frai-core"}, "t3": {"frai-gate"}, "h1": {"frai-gate"}, "h2": {"frai-core", "frai-cli"},
             "h3": {"frai-core", "frai-cli", "frai-agent"}, "h4": {"frai-core", "frai-cli", "frai-agent"}}
TEST_RE = re.compile(r"\b(test|vitest|jest)\b")
BUILD_RE = re.compile(r"\b(build|tsc)\b")
DONE_RE = re.compile(r"\b(all (tests|checks) pass|tests pass|passing|fixed|implemented|done|complete[ds]?)\b", re.I)


def short(s, n=90):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def run_evidence(ev_path: Path, raw_path: Path):
    row = json.loads(raw_path.read_text())["row"] if raw_path.exists() else {}
    events = [json.loads(l) for l in ev_path.read_text().splitlines() if l.strip()]
    steps, errors, results = [], [], {}
    for e in events:
        msg = e.get("message") if isinstance(e.get("message"), dict) else {}
        content = msg.get("content") if isinstance(msg.get("content"), list) else []
        for block in content:
            if not isinstance(block, dict):
                continue
            if e.get("type") == "assistant" and block.get("type") == "tool_use":
                name, inp = block.get("name"), block.get("input") or {}
                target = inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("path") or inp.get("description") or ""
                steps.append({"id": block.get("id"), "tool": name, "target": short(target, 140)})
            elif e.get("type") == "user" and block.get("type") == "tool_result":
                content = block.get("content")
                text = content if isinstance(content, str) else " ".join(c.get("text", "") for c in content or [] if isinstance(c, dict))
                results[block.get("tool_use_id")] = {"error": bool(block.get("is_error")), "text": short(text, 200)}
    for s in steps:
        r = results.get(s["id"], {})
        s["error"] = r.get("error", False)
        if s["error"]:
            errors.append(f"{s['tool']}: {s['target']} -> {r.get('text', '')}")
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    bash = [s["target"] for s in steps if s["tool"] == "Bash"]
    edits = [s["target"] for s in steps if s["tool"] in ("Edit", "Write", "MultiEdit", "NotebookEdit")]
    task = row.get("task", "")[:2]
    pkgs = TASK_PKGS.get(task, set())
    pkg_of = lambda f: f.split("/packages/", 1)[1].split("/", 1)[0] if "/packages/" in f else None
    outside = sorted({f for f in edits if pkgs and pkg_of(f) and pkg_of(f) not in pkgs})
    first_edit = next((i for i, s in enumerate(steps) if s["tool"] in ("Edit", "Write", "MultiEdit")), None)
    denials = [short(json.dumps(d.get("tool_input", d)), 120) for d in (final.get("permission_denials") or [])]
    claim = short(final.get("result", ""), 300)
    return {
        "side": row.get("side"), "task": row.get("task"), "run": row.get("run"), "passed": row.get("passed"),
        "grade_reason": row.get("grade_reason"), "minutes": row.get("duration_min"), "cost_usd": row.get("cost_usd"),
        "turns": row.get("turns"), "timeout": row.get("timeout"), "extra": row.get("extra"),
        "steps": len(steps), "reads": sum(s["tool"] in ("Read", "Grep", "Glob", "LS") for s in steps),
        "edits": len(edits), "files_edited": sorted(set(edits)), "edits_outside_task_package": outside,
        "shell": len(bash), "test_runs": sum(bool(TEST_RE.search(c)) for c in bash),
        "builds": sum(bool(BUILD_RE.search(c)) for c in bash), "first_edit_at_step": first_edit,
        "denied": denials, "tool_errors": errors[:8], "said_done": bool(DONE_RE.search(claim)), "final_message": claim,
        "sequence": [f"{s['tool']}: {s['target']}" + (" [error]" if s["error"] else "") for s in steps][:60],
    }


def main():
    tid = f"d{int(sys.argv[1]):02d}" if sys.argv[1].isdigit() else sys.argv[1]
    rdir = LAB / "runs" / tid / "raw"
    runs = []
    for ev in sorted(p for p in rdir.glob("*.events.jsonl") if not p.name.startswith("crashed-")):
        runs.append(run_evidence(ev, ev.with_name(ev.name.replace(".events.jsonl", ".json"))))
    if not runs:
        sys.exit(f"no event logs in {rdir} (runs before 15 Sep 2026 saved only the final result)")
    sides = {}
    for side in ("with", "without"):
        rs = [r for r in runs if r["side"] == side]
        if not rs:
            continue
        avg = lambda k: round(sum(float(r[k] or 0) for r in rs) / len(rs), 2)
        sides[side] = {
            "runs": len(rs), "passed": sum(bool(r["passed"]) for r in rs), "avg_steps": avg("steps"), "avg_reads": avg("reads"),
            "avg_edits": avg("edits"), "avg_test_runs": avg("test_runs"), "avg_first_edit_step": avg("first_edit_at_step") if all(r["first_edit_at_step"] is not None for r in rs) else None,
            "runs_without_running_tests": sum(r["test_runs"] == 0 for r in rs), "denied_total": sum(len(r["denied"]) for r in rs),
            "denied_examples": Counter(d for r in rs for d in r["denied"]).most_common(5),
            "runs_editing_outside_package": sum(bool(r["edits_outside_task_package"]) for r in rs),
            "said_done_but_failed": sum(r["said_done"] and not r["passed"] for r in rs),
            "fail_reasons": Counter(r["grade_reason"] for r in rs if not r["passed"]).most_common(5),
        }
    moments = []
    for r in runs:
        tag = f"{r['side']} {r['task']} run {r['run']}"
        if r["said_done"] and not r["passed"]:
            moments.append(f"{tag}: said '{short(r['final_message'], 110)}' but the hidden tests failed ({r['grade_reason']})")
        if r["edits_outside_task_package"]:
            moments.append(f"{tag}: edited outside the task's package: {', '.join(r['edits_outside_task_package'][:3])}")
        if r["denied"]:
            moments.append(f"{tag}: {len(r['denied'])} denied command(s), e.g. {r['denied'][0]}")
        if r["test_runs"] == 0 and r["passed"] is False:
            moments.append(f"{tag}: never ran the tests, and failed")
        if r["timeout"]:
            moments.append(f"{tag}: hit the 20-minute limit")
    out = {"trick": tid, "sides": sides, "moments": moments, "runs": runs}
    (LAB / "runs" / tid / "evidence.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"# {tid} evidence\n")
    for side, s in sides.items():
        print(f"## {side}: {s['passed']}/{s['runs']} passed · {s['avg_steps']} steps · {s['avg_reads']} reads · {s['avg_edits']} edits · "
              f"{s['avg_test_runs']} test runs per run · first edit at step {s['avg_first_edit_step']}")
        print(f"   no tests run: {s['runs_without_running_tests']} · denied: {s['denied_total']} {s['denied_examples'][:2]} · "
              f"outside package: {s['runs_editing_outside_package']} · said done but failed: {s['said_done_but_failed']}")
        print(f"   fail reasons: {s['fail_reasons']}")
    print("\n## Moments")
    for m in moments[:30]:
        print("-", m)


if __name__ == "__main__":
    main()
