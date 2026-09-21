#!/usr/bin/env python3
"""100 Tricks Lab runner: run one trick on the fixed tasks, grade every run, summarise.

Run it from a normal terminal, not from inside another Claude Code session (a nested
`claude -p` can block on the macOS keychain prompt).

  python3 harness/run.py d01 --dry-run         # prepare 1 workdir per task, grade the untouched baseline, no agent calls
  python3 harness/run.py d01                   # runs × sides × tasks from tricks/d01/trick.json
  python3 harness/run.py d01 --runs 2 --parallel 3
  python3 harness/run.py d01 --summarize-only  # rebuild summary.json from finished runs

Isolation. Every run gets a fresh copy of base/frai (APFS clone) under /private/tmp/100-tricks-runs,
so no CLAUDE.md, skill or agent from your own setup leaks in. Set LAB_CLAUDE_CONFIG_DIR to a clean
Claude config folder (log in there once: `CLAUDE_CONFIG_DIR=~/.claude-lab claude`, then /login) so
your user hooks, plugins, agents and commands don't load either. No API key is used: runs go through
your normal Claude subscription. Cost figures are Claude Code's API-equivalent estimate.

Outputs in runs/<id>/: runs.csv (one row per run), raw/<side>-<task>-r<n>.json, summary.json,
result_fragment.json (the "results" block for test-result-crosspost).
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
BASE = LAB / "base" / "frai"
WORK_ROOT = Path("/private/tmp/100-tricks-runs")
ALLOWED_TOOLS = ",".join([
    "Read", "Edit", "Write", "Glob", "Grep",
    "Bash(pnpm *)", "Bash(npx *)", "Bash(node *)",
    "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)",
    "Bash(ls *)", "Bash(cat *)", "Bash(mkdir *)",
    # harmless shell glue agents chain into commands (day 1 logs: most denials were cd, echo, head, grep, find)
    "Bash(cd *)", "Bash(echo *)", "Bash(printf *)", "Bash(head *)", "Bash(tail *)", "Bash(grep *)",
    "Bash(find *)", "Bash(wc *)", "Bash(sort *)", "Bash(pwd)", "Bash(mktemp *)", "Bash(test *)",
])
# Best-effort guard: runs happen in /private/tmp, so nothing under ~/Personal (this lab's hidden tests and
# reference fixes, other frai checkouts) is needed. Built-in read tools are denied there; plain shell reads too.
DENIED_TOOLS = ",".join([
    "Read(~/Personal/**)", "Edit(~/Personal/**)", "Write(~/Personal/**)",
    "Bash(cat /Users/*)", "Bash(ls /Users/*)", "Bash(cat ~*)", "Bash(ls ~*)",
    "Bash(head /Users/*)", "Bash(tail /Users/*)", "Bash(grep * /Users/*)", "Bash(find /Users/*)", "Bash(wc /Users/*)",
    "Bash(cd /Users/*)", "Bash(cd ~*)", "Bash(find ~*)", "Bash(grep * ~*)",
])
INFRA_MARKERS = ("usage limit", "session limit", "weekly limit", "rate limit", "hit your", "not logged in", "please run /login", "overloaded", "api error", "credit balance")
CSV_FIELDS = ["trick", "side", "task", "run", "passed", "grade_reason", "infra_error", "timeout",
              "duration_min", "cost_usd", "turns", "input_tokens", "output_tokens", "cache_read_tokens",
              "models", "permission_denials", "files_changed", "insertions", "deletions", "extra", "started_at"]
lock = threading.Lock()


def load_trick(tid):
    p = LAB / "tricks" / tid / "trick.json"
    if not p.exists():
        sys.exit(f"No trick definition at {p}")
    t = json.loads(p.read_text())
    for side in ("with", "without"):
        if side not in t.get("sides", {}):
            sys.exit(f"trick.json needs sides.{side}")
    return t


def clone_base(dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["cp", "-cR", str(BASE), str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(["cp", "-R", str(BASE), str(dest)], check=True)


def ensure_fetched(trick: dict, trick_dir: Path):
    """Download third-party trick files at a pinned URL and hash instead of committing them (no licence to redistribute)."""
    import hashlib, urllib.request
    for f in trick.get("fetch", []):
        dest = trick_dir / f["dest"]
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(f["url"], timeout=60) as r:
                dest.write_bytes(r.read())
        got = hashlib.sha256(dest.read_bytes()).hexdigest()
        if got != f["sha256"]:
            sys.exit(f"hash mismatch for {dest}: expected {f['sha256']}, got {got}")


def apply_overlay(trick_dir: Path, side_cfg: dict, work: Path):
    ov = side_cfg.get("overlay")
    if ov:
        src = trick_dir / ov
        if not src.is_dir():
            sys.exit(f"overlay folder missing: {src}")
        shutil.copytree(src, work, dirs_exist_ok=True)
        # Fold the overlay into the copy's single baseline commit and move lab-base there, so graders, checkers,
        # diffs and files_changed see only the agent's own changes (an overlay CLAUDE.md inside packages/frai-gate
        # would otherwise fail t1's "frai-gate untouched" check). The copy still shows one commit, no history.
        git = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True, check=True)
        git("add", "-A")
        git("-c", "user.name=lab", "-c", "user.email=lab@localhost", "commit", "--amend", "--no-edit", "--allow-empty")
        git("tag", "-f", "lab-base")


def grade(task: str, work: Path):
    acc = LAB / "tasks" / task / "accept.sh"
    logdir = work.parent / f"{work.name}-logs"
    r = subprocess.run([str(acc), str(work)], capture_output=True, text=True, timeout=900,
                       env=dict(os.environ, LAB_LOG_DIR=str(logdir)))
    last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    return r.returncode == 0, last


def diffstat(work: Path):
    r = subprocess.run(["git", "-C", str(work), "diff", "--shortstat", "lab-base"], capture_output=True, text=True)
    s = r.stdout
    num = lambda word: next((int(x.split()[0]) for x in s.split(",") if word in x), 0)
    untracked = subprocess.run(["git", "-C", str(work), "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True).stdout.split()
    return num("file") + len(untracked), num("insertion"), num("deletion")


def agent_env(extra=None):
    # Drop every variable a parent Claude session sets (CLAUDE*, ANTHROPIC*): inherited ones made nested runs hang.
    env = {k: v for k, v in os.environ.items() if not (k.startswith("CLAUDE") or k.startswith("ANTHROPIC"))}
    if os.environ.get("LAB_CLAUDE_CONFIG_DIR"):
        env["CLAUDE_CONFIG_DIR"] = os.path.expanduser(os.environ["LAB_CLAUDE_CONFIG_DIR"])
    env["CI"] = "true"  # keeps vitest and similar tools out of watch mode
    env.update({k: os.path.expandvars(str(v)) for k, v in (extra or {}).items()})  # e.g. a side on a local Ollama model
    return env


def build_prompt(tdir: Path, side_cfg: dict, task: str) -> str:
    """Task prompt for one side: a full replacement file per task, or the task's prompt.md, plus prefixes."""
    by_file = (side_cfg.get("prompt_file_by_task") or {}).get(task)
    body = (tdir / by_file).read_text() if by_file else (LAB / "tasks" / task / "prompt.md").read_text()
    prefix = (side_cfg.get("prompt_prefix") or "") + ((side_cfg.get("prompt_prefix_by_task") or {}).get(task) or "")
    return prefix + body + (side_cfg.get("prompt_suffix") or "")


def task_text(tdir: Path, side_cfg: dict, task: str) -> str:
    """The task's own prompt, without the side's prefix or suffix (for follow-up turn templates)."""
    by_file = (side_cfg.get("prompt_file_by_task") or {}).get(task)
    return (tdir / by_file).read_text() if by_file else (LAB / "tasks" / task / "prompt.md").read_text()


def call_claude(cmd, work, timeout_s, env_extra=None):
    """One headless call. Returns (json data, timed_out)."""
    try:
        r = subprocess.run(cmd, cwd=work, env=agent_env(env_extra), capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout_s)
        out, timed_out = r.stdout, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        r, timed_out = None, True
    # stream-json: one event per line (every tool call and result), the last "result" event is the summary.
    events = []
    for line in out.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None and not timed_out:
        # No result event at all: Claude Code itself crashed or never started (not the agent failing the task).
        result = {"is_error": True, "infra_crash": True, "result": (out + (r.stderr if r else ""))[-2000:]}
    data = dict(result or {})
    data["_events"] = events
    return data, timed_out


def save_diff(work: Path, dest: Path):
    subprocess.run(["git", "-C", str(work), "add", "-A"], capture_output=True)
    d = subprocess.run(["git", "-C", str(work), "diff", "--cached", "lab-base", "--", ".", ":(exclude)node_modules", ":(exclude,glob)**/dist/**"],
                       capture_output=True, text=True).stdout
    dest.write_text(d[:2_000_000])


def run_one(trick, tid, side, task, n, out_dir, dry):
    tdir = LAB / "tricks" / tid
    side_cfg = trick["sides"][side]
    raw = out_dir / "raw" / f"{side}-{task}-r{n}.json"
    if raw.exists() and not dry:
        return json.loads(raw.read_text())
    work = WORK_ROOT / tid / side / task / f"r{n}"
    clone_base(work)
    apply_overlay(tdir, side_cfg, work)
    prompt = build_prompt(tdir, side_cfg, task)
    turns = side_cfg.get("turns") or []
    allowed = ",".join([ALLOWED_TOOLS] + list(side_cfg.get("allowed_tools_extra") or []))
    base_flags = ["--output-format", "stream-json", "--verbose", "--permission-mode", side_cfg.get("permission_mode", "acceptEdits"),
                  "--allowedTools", allowed, "--disallowedTools", DENIED_TOOLS,
                  "--setting-sources", "project,local", "--strict-mcp-config"]
    if not turns:
        base_flags.insert(2, "--no-session-persistence")
    cmd = ["claude", "-p", prompt] + base_flags
    if not trick.get("skills"):
        cmd.append("--disable-slash-commands")
    model = side_cfg.get("model") or trick.get("model")
    if model:
        cmd += ["--model", model]
    effort = side_cfg.get("effort") or trick.get("effort")
    if effort:
        cmd += ["--effort", effort]
    cmd += side_cfg.get("extra_args", [])
    timeout_s = int(trick.get("timeout_min", 20)) * 60

    row = {"trick": tid, "side": side, "task": task, "run": n, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    data, timeout, infra = {}, False, ""
    if dry:
        row.update(duration_min=0, cost_usd=0, turns=0)
        print("DRY", " ".join(c if len(c) < 60 else c[:57] + "..." for c in cmd), f"(cwd {work})")
    else:
        t0 = time.time()
        data, timeout = call_claude(cmd, work, timeout_s, side_cfg.get("env"))
        calls = [data]
        # Follow-up turns resume the same session (plan -> execute, review -> fix, /compact, retries).
        for turn in turns:
            fresh = bool(turn.get("fresh"))  # a new session in the same repo copy (spec -> fresh build), not --resume
            if timeout or data.get("is_error") or (not fresh and not data.get("session_id")):
                break
            left = timeout_s - (time.time() - t0)
            if left <= 0:
                timeout = True
                break
            tp = turn.get("prompt") or (tdir / turn["prompt_file"]).read_text()
            tp = (tp.replace("{task_prompt}", prompt).replace("{task}", task_text(tdir, side_cfg, task))
                    .replace("{prev_result}", str(data.get("result") or "").strip()))
            tflags = list(base_flags)
            if turn.get("permission_mode"):  # e.g. plan mode for the first call, acceptEdits to implement
                i = tflags.index("--permission-mode"); tflags[i + 1] = turn["permission_mode"]
            tcmd = ["claude", "-p", tp] + ([] if fresh else ["--resume", data["session_id"]]) + tflags
            if not trick.get("skills") and not turn.get("slash_commands"):
                tcmd.append("--disable-slash-commands")
            if turn.get("model") or model:
                tcmd += ["--model", turn.get("model") or model]
            if effort:
                tcmd += ["--effort", effort]
            tcmd += turn.get("extra_args", [])
            nxt, timeout = call_claude(tcmd, work, left, side_cfg.get("env"))
            calls.append(nxt)
            data = nxt or data
        if len(calls) > 1:
            data = dict(data)
            data["total_cost_usd"] = sum(float(c.get("total_cost_usd") or 0) for c in calls)
            data["duration_ms"] = sum(float(c.get("duration_ms") or 0) for c in calls)
            data["num_turns"] = sum(int(c.get("num_turns") or 0) for c in calls)
            data["calls"] = len(calls)
            # token counts summed over every step too (a plan step or a chat step is part of the cost of the trick)
            data["usage"] = {k: sum(int((c.get("usage") or {}).get(k) or 0) for c in calls)
                             for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
            data["step_results"] = [str(c.get("result") or "")[:4000] for c in calls[:-1]]
        wall = (time.time() - t0) / 60
        text = str(data.get("result", "")).lower()
        if data.get("is_error") and (data.get("infra_crash") or any(m in text for m in INFRA_MARKERS) or data.get("terminal_reason") == "api_error"
                                     or str(data.get("api_error_status") or "") in ("429", "500", "502", "503", "529")):
            infra = text[:160]
        usage = data.get("usage") or {}
        row.update(duration_min=round((data.get("duration_ms") or wall * 60000) / 60000, 2),
                   cost_usd=round(float(data.get("total_cost_usd") or 0), 4), turns=data.get("num_turns") or 0,
                   input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                   cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                   models="|".join((data.get("modelUsage") or {}).keys()),
                   permission_denials=len(data.get("permission_denials") or []))
    files, ins, dels = diffstat(work)
    extra = ""
    if trick.get("extra_check"):  # trick-specific measurement on the finished repo, before grading touches it
        chk = subprocess.run([str(tdir / trick["extra_check"]), str(work), side, task], capture_output=True, text=True, timeout=300)
        extra = (chk.stdout.strip().splitlines() or [""])[-1][:200]
    passed, reason = (False, "infra error, not graded") if infra else grade(task, work)
    if timeout and not infra:  # PROTOCOL: a timeout counts as a failed run, whatever state the repo was left in
        passed, reason = False, f"FAIL timeout after {trick.get('timeout_min', 20)} min (grader alone said: {reason})"
    row.update(passed=passed, grade_reason=reason, infra_error=infra, timeout=timeout,
               files_changed=files, insertions=ins, deletions=dels, extra=extra)
    if not dry:
        raw.parent.mkdir(parents=True, exist_ok=True)
        save_diff(work, raw.with_suffix(".diff"))
        events = [e for c in calls for e in (c.get("_events") or [])]
        with open(raw.with_suffix(".events.jsonl"), "w") as fh:
            for e in events:
                fh.write(json.dumps(e) + "\n")
        data = {k: v for k, v in data.items() if k != "_events"}
        raw.write_text(json.dumps({"row": row, "claude": data, "cmd": cmd[:2] + ["<prompt>"] + cmd[3:]}, indent=2))
        with lock:
            new = not (out_dir / "runs.csv").exists()
            with open(out_dir / "runs.csv", "a", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
                if new:
                    w.writeheader()
                w.writerow(row)
        shutil.rmtree(work, ignore_errors=True)
    print(f"{'PASS' if passed else 'FAIL'} {side:<7} {task:<20} r{n}  {row.get('duration_min', 0)} min  ${row.get('cost_usd', 0)}  {reason}")
    return {"row": row}


def side_stats(rows):
    graded = [r for r in rows if not r["infra_error"]]
    k = len(graded) or 1
    return {
        "runs": len(rows), "graded": len(graded), "infra_errors": len(rows) - len(graded),
        "passed": sum(1 for r in graded if r["passed"]),
        "timeouts": sum(1 for r in graded if r["timeout"]),
        "edited_tests": sum(1 for r in graded if "test files changed" in r["grade_reason"]),
        "avg_minutes": round(sum(float(r["duration_min"]) for r in graded) / k, 2),
        "avg_cost_usd": round(sum(float(r["cost_usd"]) for r in graded) / k, 4),
        "avg_turns": round(sum(int(r["turns"]) for r in graded) / k, 1),
    }


def decide(w, o):
    """Pre-registered verdict rule. Written in PROTOCOL.md before any run; do not change mid-challenge."""
    if w["infra_errors"] >= 2 or o["infra_errors"] >= 2 or not w["graded"] or not o["graded"]:
        return "inconclusive", "two or more runs on a side hit infrastructure errors"
    dp = w["passed"] - o["passed"]
    if dp >= 2:
        return "works", f"{dp} more passing runs with the trick"
    if dp <= -2:
        return "hurts", f"{-dp} fewer passing runs with the trick"
    if w["passed"] == 0 and o["passed"] == 0:
        return "no difference", "nothing passed on either side: the tasks may be too hard for this setup"
    ratio = lambda a, b: a / b if b else 1.0
    t, c = ratio(w["avg_minutes"], o["avg_minutes"]), ratio(w["avg_cost_usd"], o["avg_cost_usd"])
    if dp >= 0 and (t <= 0.75 or c <= 0.75) and t < 1.25 and c < 1.25:
        return "works", "same or better pass count, at least 25% faster or cheaper"
    if dp <= 0 and t >= 1.25 and c >= 1.25:
        return "hurts", "same or worse pass count, at least 25% slower and costlier"
    return "no difference", "pass counts within 1 and no 25% time or cost gap"


def summarize(trick, tid, out_dir):
    path = out_dir / "runs.csv"
    if not path.exists():
        sys.exit("No runs.csv yet.")
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        r["passed"] = r["passed"] == "True"
        r["timeout"] = r["timeout"] == "True"
    by = lambda side: [r for r in rows if r["side"] == side]
    w, o = side_stats(by("with")), side_stats(by("without"))
    verdict, why = decide(w, o)
    tasks = trick["tasks"]
    per_task = {side: {t: sum(1 for r in by(side) if r["task"] == t and r["passed"]) for t in tasks} for side in ("with", "without")}
    summary = {"trick": tid, "day": trick.get("day"), "name": trick.get("trick"), "with": w, "without": o,
               "per_task_passes": per_task, "verdict": verdict, "verdict_reason": why,
               "runs_per_side_task": trick.get("runs"), "cost_note": "API-equivalent estimate reported by Claude Code"}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    frag = {"verdict": verdict, "results": {
        s: {"passed": st["passed"], "total": st["graded"], "avg_minutes": st["avg_minutes"], "avg_cost_usd": st["avg_cost_usd"]}
        for s, st in (("with", w), ("without", o))}}
    (out_dir / "result_fragment.json").write_text(json.dumps(frag, indent=2))
    print(f"\n{tid} · {trick.get('trick')}")
    for s, st in (("with", w), ("without", o)):
        print(f"  {s:<8} {st['passed']}/{st['graded']} passed · {st['avg_minutes']} min · ${st['avg_cost_usd']} · "
              f"{st['avg_turns']} turns · timeouts {st['timeouts']} · edited tests {st['edited_tests']} · infra {st['infra_errors']}")
    print(f"  per task: {per_task}")
    print(f"  VERDICT: {verdict} ({why})")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trick")
    ap.add_argument("--runs", type=int)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summarize-only", action="store_true")
    ap.add_argument("--only-task")
    a = ap.parse_args()
    trick = load_trick(a.trick)
    ensure_fetched(trick, LAB / "tricks" / a.trick)
    out_dir = LAB / "runs" / a.trick
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.summarize_only:
        return summarize(trick, a.trick, out_dir)
    if not shutil.which("claude") and not a.dry_run:
        sys.exit("claude CLI not found on PATH")
    if not a.dry_run and not os.environ.get("LAB_CLAUDE_CONFIG_DIR"):
        print("WARNING: LAB_CLAUDE_CONFIG_DIR is not set, so your user-level agents and commands may load into runs.")
    runs = 1 if a.dry_run else (a.runs or trick.get("runs", 3))
    tasks = [a.only_task] if a.only_task else trick["tasks"]
    jobs = [(side, task, n) for n in range(1, runs + 1) for task in tasks for side in ("with", "without")]
    with ThreadPoolExecutor(max_workers=1 if a.dry_run else a.parallel) as ex:
        futs = [ex.submit(run_one, trick, a.trick, s, t, n, out_dir, a.dry_run) for s, t, n in jobs]
        for f in as_completed(futs):
            f.result()
    if not a.dry_run:
        summarize(trick, a.trick, out_dir)


if __name__ == "__main__":
    main()
