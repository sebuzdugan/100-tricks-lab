#!/usr/bin/env python3
"""Day 63 batch runner (private/m7/DESIGN.md day 63, gap G3): three agents in three git worktrees at once vs the
same three tasks one after another in one folder. run.py can't do this (one task per run, per-run minutes).

  python3 tricks/d63/batch.py --dry-run     # P5: worktrees, offline installs, baseline grades, merge check; no agent calls, writes nothing
  python3 tricks/d63/batch.py --smoke       # 1 real batch per arm into runs/d63-smoke/
  python3 tricks/d63/batch.py               # the day: N batches per arm into runs/d63/
  python3 tricks/d63/batch.py --summarize-only

Arms. with = parallel: one APFS copy of the base, `git worktree add` x3 from lab-base, `pnpm install --offline` in
each worktree (the three at once), then t1, t2 and t3 headless at the same time, one per worktree. without =
sequential: one APFS copy, t1 then t2 then t3 in the same folder, a fresh session per task, an APFS snapshot after
each task. Batches alternate arms (with b1, without b1, with b2, ...) and never overlap: the machine is the variable.

Time. batch_minutes = wall clock from the start of the copy to the last agent exit, grading excluded (sequential
snapshots are subtracted). Each task is graded with its own accept.sh after the batch: on its worktree (parallel) or
on the snapshot taken right after it (sequential). Then the three parallel branches are merged with
`git merge-tree` (no working-tree changes) and conflicts recorded; dist/ and node_modules are left out of the trees.

Settings come from tricks/d63/trick.json when it exists (tasks, batches, timeout_min, model, effort, skills,
sides.with / sides.without: prompt_prefix, allowed_tools_extra, disallowed_tools_extra, env, extra_args, overlay,
permission_mode); otherwise Core 3, 3 batches per arm (DESIGN.md and RISKS.md: "3 batches a side"), Haiku 4.5,
20 min per task. Outputs follow run.py: runs.csv (run.py's columns plus batch_minutes; `run` = batch number),
raw/<side>-<task>-r<batch>.{json,diff,events.jsonl}, raw/batch-<side>-r<batch>.json, summary.json,
result_fragment.json. The verdict in summary.json uses decide() with mean batch minutes and mean batch cost in place
of per-run means; it stands only once the wall-time rule is written in PROTOCOL.md before the run.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent
sys.path.insert(0, str(LAB / "harness"))
import run  # noqa: E402  (clone_base, apply_overlay, build_prompt, call_claude, grade, side flags, CLAUDE_BIN)

TID = "d63"
CORE3 = ["t1-flag-bug", "t2-failing-tests", "t3-summary-feature"]
DEFAULTS = {"tasks": CORE3, "batches": 3, "timeout_min": 20, "model": "claude-haiku-4-5-20251001", "skills": False}
ARM = {"with": "parallel", "without": "sequential"}
CSV_FIELDS = run.CSV_FIELDS + ["batch_minutes"]
EXCLUDE = [".", ":(exclude)node_modules", ":(exclude,glob)**/node_modules/**", ":(exclude,glob)**/dist/**"]


def load():
    p = HERE / "trick.json"
    t = dict(DEFAULTS)
    if p.exists():
        t.update({k: v for k, v in json.loads(p.read_text()).items() if v is not None})
    t.setdefault("sides", {})
    for s in ("with", "without"):
        t["sides"].setdefault(s, {})
    return t


def cp_clone(src: Path, dest: Path):
    shutil.rmtree(dest, ignore_errors=True)
    if subprocess.run(["cp", "-cR", str(src), str(dest)], capture_output=True).returncode != 0:
        subprocess.run(["cp", "-R", str(src), str(dest)], check=True)


def git(work, *a, env=None):
    return subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True, env=env)


def clean_tree(work: Path) -> str:
    """Tree object of the working copy now (untracked included, dist and node_modules left out), via a temporary
    index: no commit, no ref, the agent-visible index untouched."""
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(td, "index"))
        git(work, "read-tree", "lab-base", env=env)
        git(work, "add", "-A", "--", *EXCLUDE, env=env)
        return git(work, "write-tree", env=env).stdout.strip()


def shortstat(work, a, b):
    s = git(work, "diff", "--shortstat", a, b).stdout
    num = lambda word: next((int(x.split()[0]) for x in s.split(",") if word in x), 0)
    return num("file"), num("insertion"), num("deletion")


def merge_check(repo: Path, trees: dict) -> dict:
    """Merge the parallel branches (one dangling commit per task tree on top of lab-base) with merge-tree."""
    base = git(repo, "rev-parse", "lab-base^{commit}").stdout.strip()
    env = dict(os.environ, GIT_AUTHOR_NAME="lab", GIT_AUTHOR_EMAIL="lab@localhost", GIT_COMMITTER_NAME="lab",
               GIT_COMMITTER_EMAIL="lab@localhost")
    commits = {t: git(repo, "commit-tree", tr, "-p", base, "-m", t, env=env).stdout.strip() for t, tr in trees.items()}
    steps, cur, conflicts = [], None, []
    for t, c in commits.items():
        if cur is None:
            cur, name = c, t
            continue
        r = git(repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", cur, c)
        lines = [x for x in r.stdout.strip().splitlines() if x.strip()]
        tree, files = (lines[0] if lines else ""), lines[1:]
        clean = r.returncode == 0
        steps.append({"merge": f"{name}+{t}", "clean": clean, "conflicted_files": files})
        conflicts += files
        if not tree:
            break
        cur = git(repo, "commit-tree", tree, "-p", cur, "-p", c, "-m", f"merge {t}", env=env).stdout.strip()
        name = f"{name}+{t}"
    return {"clean": all(s["clean"] for s in steps), "conflicts": len(conflicts), "conflicted_files": conflicts, "steps": steps}


class MemPeak(threading.Thread):
    """Peak used memory (active + wired + compressed pages from vm_stat) while a batch runs; 24 GB machine."""
    def __init__(self):
        super().__init__(daemon=True); self.peak = 0.0; self.stop = threading.Event()

    def run(self):
        while not self.stop.is_set():
            try:
                out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
                page = int(re.search(r"page size of (\d+)", out).group(1))
                val = lambda k: int(re.search(rf"{k}:\s+(\d+)", out).group(1))
                used = (val("Pages active") + val("Pages wired down") + val("Pages occupied by compressor")) * page / 2**30
                self.peak = max(self.peak, used)
            except Exception:
                pass
            self.stop.wait(2)


def cmd_for(trick, side, cfg, task, work):
    prompt = run.build_prompt(HERE, cfg, task)
    allowed = ",".join([run.ALLOWED_TOOLS] + list(cfg.get("allowed_tools_extra") or []))
    cmd = [run.CLAUDE_BIN, "-p", prompt, "--output-format", "stream-json", "--no-session-persistence", "--verbose",
           "--permission-mode", cfg.get("permission_mode", "acceptEdits"), "--allowedTools", allowed,
           "--disallowedTools", run.denied_for(cfg), "--setting-sources", "project,local", "--strict-mcp-config"]
    cmd += run.side_flags(TID, side, HERE, cfg, work)
    if not trick.get("skills"):
        cmd.append("--disable-slash-commands")
    model = cfg.get("model") or trick.get("model")
    if model:
        cmd += ["--model", model]
    effort = cfg.get("effort") or trick.get("effort")
    if effort:
        cmd += ["--effort", effort]
    return cmd + run.fill_work(cfg.get("extra_args"), work)


def env_for(cfg):
    return {"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", **(cfg.get("env") or {})}


def agent(trick, side, cfg, task, work, dry):
    """One headless call; returns (data, timed_out, cmd)."""
    cmd = cmd_for(trick, side, cfg, task, work)
    if dry:
        print("DRY", " ".join(c if len(c) < 60 else c[:57] + "..." for c in cmd), f"(cwd {work})")
        return {}, False, cmd
    data, timeout = run.call_claude(cmd, work, int(trick["timeout_min"]) * 60, env_for(cfg))
    return data, timeout, cmd


def row_for(side, task, n, data, timeout, t_start, t_end, trick):
    row = {"trick": TID, "side": side, "task": task, "run": n, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t_start))}
    text = str(data.get("result", "")).lower()
    infra = ""
    if data.get("is_error") and (data.get("infra_crash") or any(m in text for m in run.INFRA_MARKERS) or data.get("terminal_reason") == "api_error"
                                 or str(data.get("api_error_status") or "") in ("429", "500", "502", "503", "529")):
        infra = text[:160] or "infrastructure error (no message)"
    usage = data.get("usage") or {}
    row.update(duration_min=round((data.get("duration_ms") or (t_end - t_start) * 1000) / 60000, 2),
               cost_usd=round(float(data.get("total_cost_usd") or 0), 4), turns=data.get("num_turns") or 0,
               input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
               cache_read_tokens=usage.get("cache_read_input_tokens", 0),
               models="|".join((data.get("modelUsage") or {}).keys()),
               permission_denials=len(data.get("permission_denials") or []), infra_error=infra, timeout=timeout)
    return row


def install(wt: Path, main: Path):
    t0 = time.time()
    r = subprocess.run(["pnpm", "install", "--offline"], cwd=wt, capture_output=True, text=True,
                       env=dict(os.environ, CI="true"), timeout=900)
    info = {"ok": r.returncode == 0, "minutes": round((time.time() - t0) / 60, 3)}
    if r.returncode != 0:  # DESIGN kill-switch fallback: APFS-clone node_modules, install cost excluded (say so)
        info["error"] = (r.stderr or r.stdout).strip()[-300:]
        for nm in [main / "node_modules", *main.glob("packages/*/node_modules")]:
            cp_clone(nm, wt / nm.relative_to(main))
        info["fallback"] = "node_modules cloned from the main copy"
    return info


def parallel_batch(trick, n, root, dry):
    side, cfg = "with", trick["sides"]["with"]
    bdir = root / TID / side / f"b{n}"
    shutil.rmtree(bdir, ignore_errors=True)
    main, wts = bdir / "main", {t: bdir / f"wt-{t}" for t in trick["tasks"]}
    t0 = time.time()
    run.clone_base(main, LAB / "base" / trick.get("base", "frai"))
    run.apply_overlay(HERE, cfg, main)
    for t, wt in wts.items():
        r = git(main, "worktree", "add", "-q", "-b", f"lab-{t}", str(wt), "lab-base")
        if r.returncode != 0:
            sys.exit(f"git worktree add failed for {t}: {r.stderr}")
    with ThreadPoolExecutor(len(wts)) as ex:
        installs = dict(zip(wts, ex.map(lambda wt: install(wt, main), wts.values())))
    t_setup = time.time()
    with ThreadPoolExecutor(len(wts)) as ex:
        futs = {t: ex.submit(lambda t=t: (time.time(), *agent(trick, side, cfg, t, wts[t], dry), time.time())) for t in wts}
        results = {t: f.result() for t, f in futs.items()}
    t_end = max(r[-1] for r in results.values())
    batch_min = (t_end - t0) / 60
    trees = {t: clean_tree(wt) for t, wt in wts.items()}  # before grading, so grader output never enters a tree
    merge = merge_check(main, trees)
    rows, raws = [], []
    for t, (ts, data, timeout, cmd, te) in results.items():
        row = row_for(side, t, n, data, timeout, ts, te, trick)
        f, i, d = shortstat(main, "lab-base", trees[t])
        passed, reason = (False, "infra error, not graded") if row["infra_error"] else run.grade(t, wts[t])
        if timeout and not row["infra_error"]:
            passed, reason = False, f"FAIL timeout after {trick['timeout_min']} min (grader alone said: {reason})"
        row.update(passed=passed, grade_reason=reason, files_changed=f, insertions=i, deletions=d,
                   batch_minutes=round(batch_min, 2),
                   extra=json.dumps({"arm": "parallel", "install_min": installs[t]["minutes"], "install_ok": installs[t]["ok"],
                                     "merge_clean": merge["clean"]}, separators=(",", ":")))
        diff = git(main, "diff", "lab-base", trees[t], "--", *EXCLUDE).stdout
        rows.append(row); raws.append((t, data, cmd, diff))
    batch = {"side": side, "arm": "parallel", "batch": n, "batch_minutes": round(batch_min, 2),
             "setup_minutes": round((t_setup - t0) / 60, 3), "installs": installs, "merge": merge}
    return rows, raws, batch, bdir


def sequential_batch(trick, n, root, dry):
    side, cfg = "without", trick["sides"]["without"]
    bdir = root / TID / side / f"b{n}"
    shutil.rmtree(bdir, ignore_errors=True)
    work = bdir / "work"
    t0 = time.time()
    run.clone_base(work, LAB / "base" / trick.get("base", "frai"))
    run.apply_overlay(HERE, cfg, work)
    snap_s, prev, done = 0.0, "lab-base", []
    for pos, t in enumerate(trick["tasks"], 1):
        ts = time.time()
        data, timeout, cmd = agent(trick, side, cfg, t, work, dry)
        te = time.time()
        s0 = time.time()
        cur = clean_tree(work)
        snap = bdir / f"after-{pos}-{t}"
        cp_clone(work, snap)
        snap_s += time.time() - s0
        done.append((t, ts, te, data, timeout, cmd, prev, cur, snap))
        prev = cur
    t_end = done[-1][2]
    batch_min = (t_end - t0 - snap_s) / 60
    rows, raws = [], []
    for t, ts, te, data, timeout, cmd, a, b, snap in done:
        row = row_for(side, t, n, data, timeout, ts, te, trick)
        f, i, d = shortstat(work, a, b)
        passed, reason = (False, "infra error, not graded") if row["infra_error"] else run.grade(t, snap)
        if timeout and not row["infra_error"]:
            passed, reason = False, f"FAIL timeout after {trick['timeout_min']} min (grader alone said: {reason})"
        row.update(passed=passed, grade_reason=reason, files_changed=f, insertions=i, deletions=d,
                   batch_minutes=round(batch_min, 2), extra=json.dumps({"arm": "sequential"}, separators=(",", ":")))
        rows.append(row); raws.append((t, data, cmd, git(work, "diff", a, b, "--", *EXCLUDE).stdout))
    batch = {"side": side, "arm": "sequential", "batch": n, "batch_minutes": round(batch_min, 2),
             "snapshot_minutes_excluded": round(snap_s / 60, 3)}
    return rows, raws, batch, bdir


def save(out_dir, rows, raws, batch):
    rawdir = out_dir / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    for row, (t, data, cmd, diff) in zip(rows, raws):
        raw = rawdir / f"{row['side']}-{t}-r{row['run']}.json"
        raw.with_suffix(".diff").write_text(diff[:2_000_000])
        with open(raw.with_suffix(".events.jsonl"), "w") as fh:
            for e in data.get("_events") or []:
                fh.write(json.dumps(e) + "\n")
        keep = {k: v for k, v in data.items() if k != "_events"}
        raw.write_text(json.dumps({"row": row, "claude": keep, "cmd": cmd[:2] + ["<prompt>"] + cmd[3:], "batch": batch}, indent=2))
    batch = dict(batch, cost_usd=round(sum(float(r["cost_usd"]) for r in rows), 4),
                 passed=sum(1 for r in rows if r["passed"]), infra_errors=sum(1 for r in rows if r["infra_error"]))
    (rawdir / f"batch-{batch['side']}-r{batch['batch']}.json").write_text(json.dumps(batch, indent=2))
    new = not (out_dir / "runs.csv").exists()
    with open(out_dir / "runs.csv", "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def summarize(trick, out_dir):
    path = out_dir / "runs.csv"
    if not path.exists():
        sys.exit("No runs.csv yet.")
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        r["passed"] = r["passed"] == "True"
        r["timeout"] = r["timeout"] == "True"
    batches = [json.loads(p.read_text()) for p in sorted((out_dir / "raw").glob("batch-*.json"))]
    res = {}
    for side in ("with", "without"):
        st = run.side_stats([r for r in rows if r["side"] == side])
        bs = [b for b in batches if b["side"] == side]
        k = len(bs) or 1
        st.update(arm=ARM[side], batches=len(bs),
                  avg_batch_minutes=round(sum(b["batch_minutes"] for b in bs) / k, 2),
                  avg_batch_cost_usd=round(sum(b["cost_usd"] for b in bs) / k, 4))
        if side == "with":
            st["merge_conflicts"] = sum(b["merge"]["conflicts"] for b in bs)
            st["batches_merged_clean"] = sum(1 for b in bs if b["merge"]["clean"])
            ins = [i["minutes"] for b in bs for i in b["installs"].values()]
            st["avg_install_minutes"] = round(sum(ins) / (len(ins) or 1), 3)
            st["install_fallbacks"] = sum(1 for b in bs for i in b["installs"].values() if not i["ok"])
        st["peak_used_gb_max"] = max((b.get("peak_used_gb") or 0 for b in bs), default=0)
        res[side] = st
    # Wall-time form of the standard rule: batch means in place of per-run means (ratios are unchanged by counts).
    wv = dict(res["with"], avg_minutes=res["with"]["avg_batch_minutes"], avg_cost_usd=res["with"]["avg_batch_cost_usd"])
    ov = dict(res["without"], avg_minutes=res["without"]["avg_batch_minutes"], avg_cost_usd=res["without"]["avg_batch_cost_usd"])
    verdict, why = run.decide(wv, ov)
    per_task = {s: {t: sum(1 for r in rows if r["side"] == s and r["task"] == t and r["passed"]) for t in trick["tasks"]} for s in ("with", "without")}
    summary = {"trick": TID, "day": trick.get("day", 63), "name": trick.get("trick"), "with": res["with"], "without": res["without"],
               "per_task_passes": per_task, "verdict": verdict, "verdict_reason": why,
               "verdict_rule": "decide() with mean batch wall minutes and mean batch cost; valid only if pre-registered in PROTOCOL.md",
               "batches_per_side": trick.get("batches"), "cost_note": "API-equivalent estimate reported by Claude Code"}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    frag = {"verdict": verdict, "results": {s: {"passed": st["passed"], "total": st["graded"], "batch_minutes": st["avg_batch_minutes"],
                                                "avg_cost_usd": st["avg_batch_cost_usd"]} for s, st in res.items()}}
    (out_dir / "result_fragment.json").write_text(json.dumps(frag, indent=2))
    print(f"\n{TID} · {trick.get('trick') or 'parallel worktrees vs sequential'}")
    for s, st in res.items():
        print(f"  {s:<8} ({st['arm']}) {st['passed']}/{st['graded']} passed · {st['avg_batch_minutes']} min/batch · "
              f"${st['avg_batch_cost_usd']}/batch · infra {st['infra_errors']}" + (f" · merge conflicts {st['merge_conflicts']}" if s == "with" else ""))
    print(f"  VERDICT (wall-time rule): {verdict} ({why})")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, help="batches per arm (default: trick.json `batches`, else 3)")
    ap.add_argument("--smoke", action="store_true", help="1 batch per arm into runs/d63-smoke/")
    ap.add_argument("--dry-run", action="store_true", help="no agent calls, nothing written to runs/ (pilot P5)")
    ap.add_argument("--summarize-only", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the batch folders under /private/tmp")
    a = ap.parse_args()
    trick = load()
    out_dir = LAB / "runs" / (TID + ("-smoke" if a.smoke else ""))
    if a.summarize_only:
        return summarize(trick, out_dir)
    if not a.dry_run:
        if not shutil.which(run.CLAUDE_BIN):
            sys.exit(f"claude CLI not found: {run.CLAUDE_BIN}")
        if not os.environ.get("LAB_CLAUDE_CONFIG_DIR"):
            print("WARNING: LAB_CLAUDE_CONFIG_DIR is not set, so your user-level agents and commands may load into runs.")
        out_dir.mkdir(parents=True, exist_ok=True)
    root = run.WORK_ROOT / ("_smoke" if a.smoke else "_dry" if a.dry_run else "")
    n_batches = 1 if (a.smoke or a.dry_run) else (a.batches or int(trick.get("batches") or 3))
    for n in range(1, n_batches + 1):
        for side in ("with", "without"):
            if not a.dry_run and (out_dir / "raw" / f"batch-{side}-r{n}.json").exists():
                print(f"skip {side} b{n}: already done")
                continue
            mem = MemPeak(); mem.start()
            rows, raws, batch, bdir = (parallel_batch if side == "with" else sequential_batch)(trick, n, root, a.dry_run)
            mem.stop.set(); mem.join()
            batch["peak_used_gb"] = round(mem.peak, 2)
            for r in rows:
                print(f"{'PASS' if r['passed'] else 'FAIL'} {side:<7} {r['task']:<20} b{n}  {r['duration_min']} min  ${r['cost_usd']}  {r['grade_reason']}")
            print(f"BATCH {side} ({ARM[side]}) b{n}: {batch['batch_minutes']} min wall"
                  + (f", installs {[(t, i['minutes'], i['ok']) for t, i in batch['installs'].items()]}, merge clean={batch['merge']['clean']}"
                     f" conflicts={batch['merge']['conflicted_files']}" if side == "with" else "")
                  + f", peak used {batch['peak_used_gb']} GB")
            if not a.dry_run:
                save(out_dir, rows, raws, batch)
            if not a.keep:
                shutil.rmtree(bdir, ignore_errors=True)
                for f in bdir.parent.glob(f"{bdir.name}*.mcp.json"):
                    f.unlink()
            else:
                print(f"  kept {bdir}")
    if not a.dry_run:
        summarize(trick, out_dir)


if __name__ == "__main__":
    main()
