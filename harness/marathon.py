#!/usr/bin/env python3
"""Marathon mode: one long, scripted coding session per run (module 4 redesign, days 31-35, 39, 40).

  python3 harness/marathon.py d31 --dry-run            # print the calls of one marathon per side, no agent calls
  python3 harness/marathon.py d31                      # trick.json "runs" marathons per side
  python3 harness/marathon.py d31 --runs 1 --parallel 2
  python3 harness/marathon.py pilot-m4b-d32 --max-requests 7 --side with   # smoke pilot: first 7 requests only
  python3 harness/marathon.py d31 --summarize-only

A marathon is the fixture's backlog (fixtures/marathon/requests.json: 25 dependent requests in 5 groups of 5) sent one
request per `claude -p` call, in order, in one repo copy. Calls resume the same session unless the side's `boundary`
resets it. After every call the repo is cloned (APFS) and the clone graded against the hidden tests of EVERY request so
far (fixtures/marathon/grade.py), so each request gets an immediate result and earlier requests are re-checked after
every call (regressions). It reuses run.py's isolation (clean config dir, allowed/denied tools, no MCP, CLAUDE*/ANTHROPIC*
env dropped, overlays folded into lab-base) and adds nothing to run.py's own code path.

trick.json: "marathon": {"requests": "fixtures/marathon/requests.json"}, "base": "invoicekit", "runs", "timeout_min"
(per call), "marathon_timeout_min" (whole marathon; requests left after it count as failed), "model", and per side the
usual overlay / allowed_tools_extra / env / extra_args plus:
  boundary             what happens before the first request of groups 2..N:
                         "none"    nothing (one long session; Claude Code auto-compacts when the window is full)
                         "compact" a `/compact` call in the same session (slash commands on for that call only)
                         "fresh"   a new session (what /clear amounts to in headless runs)
                         "handoff" a call that writes HANDOFF.md (handoff_prompt), then a new session
  after_reset_prefix   text before the first request of a new session made by "fresh"/"handoff"
  group_prefix         text before the first request of every group (group 1 too)
  group_hook           script in the trick folder run before every group's first request:
                         <hook> <workdir> <group> <side> <comma-separated request ids of the group>
                       its stdout goes before the request (day 40 pastes files; day 35 regenerates a Repomix pack)
  mention_files        true: "Relevant files: @a @b" before each request, from the request's `mention` list
                       (files that exist in the repo copy at that moment) (day 34)
Each row of runs.csv is one request of one marathon; `passed` is the immediate result (graded right after its call),
`kept` = passed right after its call AND still passing at the end of the marathon. An infrastructure error (usage limit,
login, API error, crash) aborts that marathon: its rows are not written, its raw folder moves to raw/_infra/, and a
rerun starts it again from request 1.
"""
import argparse
import csv
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402  (shared helpers: clone_base, apply_overlay, call_claude, compactions, tree_of, tool lists)

LAB = run.LAB
FIELDS = ["trick", "side", "run", "request", "group", "passed", "kept", "final", "regressed_later", "grade_reason",
          "infra_error", "timeout", "duration_min", "cost_usd", "turns", "input_tokens", "output_tokens",
          "cache_read_tokens", "cache_creation_tokens", "ctx_first", "ctx_peak", "ctx_last", "compacts",
          "auto_compacts", "boundary", "boundary_ok", "boundary_cost_usd", "boundary_min", "prefix_chars",
          "npm_test_calls", "files_changed", "insertions", "deletions", "models", "permission_denials",
          "earlier_failing", "started_at"]
lock = threading.Lock()
HANDOFF_PROMPT = ("Write HANDOFF.md in the repo root for a fresh agent who will continue this work in a new session: "
                  "the goal of the project, every rule and decision so far, what has been built and where, anything "
                  "unfinished, and how to run the tests. Change no other file.")


def load_requests(trick):
    d = json.loads((LAB / trick["marathon"]["requests"]).read_text())
    return d["requests"]


def ctx_sizes(events):
    """Context size (input + cache read + cache write tokens) of every model call in a call's stream."""
    out = []
    for e in events:
        if e.get("type") == "assistant":
            u = (e.get("message") or {}).get("usage") or {}
            out.append(int(u.get("input_tokens") or 0) + int(u.get("cache_read_input_tokens") or 0)
                       + int(u.get("cache_creation_input_tokens") or 0))
    return out


def npm_test_calls(events):
    n = 0
    for e in events:
        if e.get("type") == "assistant":
            for c in (e.get("message") or {}).get("content") or []:
                if c.get("type") == "tool_use" and c.get("name") == "Bash":
                    cmd = str((c.get("input") or {}).get("command") or "")
                    n += ("npm test" in cmd) or ("npm run test" in cmd) or ("node --test" in cmd)
    return n


def is_infra(data):
    text = str(data.get("result", "")).lower()
    return bool(data.get("is_error") and (data.get("infra_crash") or any(m in text for m in run.INFRA_MARKERS)
                                          or data.get("terminal_reason") == "api_error"
                                          or str(data.get("api_error_status") or "") in ("429", "500", "502", "503", "529")))


def grade(work: Path, ids):
    """Grade a clone of the copy against the hidden tests of `ids`; the copy the agent works in is never touched."""
    snap = work.parent / f"{work.name}-grade"
    shutil.rmtree(snap, ignore_errors=True)
    if subprocess.run(["cp", "-cR", str(work), str(snap)], capture_output=True).returncode != 0:
        subprocess.run(["cp", "-R", str(work), str(snap)], check=True)
    r = subprocess.run([sys.executable, str(LAB / "fixtures" / "marathon" / "grade.py"), str(snap), "--only", ",".join(ids)],
                       capture_output=True, text=True, timeout=900)
    shutil.rmtree(snap, ignore_errors=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {i: {"pass": False, "failed": [f"(grader crashed) {r.stderr[-200:]}"]} for i in ids}


def flags_for(trick, side_cfg, slash=False):
    allowed = ",".join([run.ALLOWED_TOOLS] + list(side_cfg.get("allowed_tools_extra") or []))
    f = ["--output-format", "stream-json", "--verbose", "--permission-mode", side_cfg.get("permission_mode", "acceptEdits"),
         "--allowedTools", allowed, "--disallowedTools", run.DENIED_TOOLS, "--setting-sources", "project,local",
         "--strict-mcp-config"]
    if not trick.get("skills") and not slash:
        f.append("--disable-slash-commands")
    model = side_cfg.get("model") or trick.get("model")
    if model:
        f += ["--model", model]
    effort = side_cfg.get("effort") or trick.get("effort")
    if effort:
        f += ["--effort", effort]
    return f + list(side_cfg.get("extra_args") or [])


def run_marathon(trick, tid, side, n, out_dir, dry, max_requests=None):
    tdir = LAB / "tricks" / tid
    side_cfg = trick["sides"][side]
    reqs = load_requests(trick)[: max_requests or None]
    ids = [r["id"] for r in reqs]
    rawdir = out_dir / "raw" / f"{side}-m{n}"
    if (rawdir / "marathon.json").exists() and not dry:
        return
    shutil.rmtree(rawdir, ignore_errors=True)
    work = run.WORK_ROOT / tid / side / f"m{n}"
    run.clone_base(work, LAB / "base" / trick.get("base", "invoicekit"))
    run.apply_overlay(tdir, side_cfg, work)
    boundary = side_cfg.get("boundary", "none")
    per_call = int(trick.get("timeout_min", 15)) * 60
    cap = int(trick.get("marathon_timeout_min", 150)) * 60
    t_start = time.time()
    session, reset_pending, prev_tree = None, False, "lab-base"
    rows, grades_after = [], {}
    started = time.strftime("%Y-%m-%dT%H:%M:%S")

    def call(prompt, resume, slash=False, timeout_s=per_call):
        cmd = ["claude", "-p", prompt] + (["--resume", resume] if resume else []) + flags_for(trick, side_cfg, slash)
        if dry:
            print("DRY", f"[{side} m{n}]", ("resume " + resume[:8]) if resume else "new session",
                  ("/compact" if slash else repr(prompt[:90])), f"(cwd {work})")
            return {"session_id": resume or "dry-session"}, False
        return run.call_claude(cmd, work, timeout_s, side_cfg.get("env"))

    for i, req in enumerate(reqs):
        rid, group = req["id"], req["group"]
        first_of_group = i == 0 or reqs[i - 1]["group"] != group
        b_info = {"boundary": "", "boundary_ok": "", "boundary_cost_usd": 0.0, "boundary_min": 0.0}
        left = cap - (time.time() - t_start)
        if first_of_group and i > 0 and boundary != "none" and left > 0:
            b_info["boundary"] = boundary
            if boundary == "compact" and session:
                d, _ = call("/compact", session, slash=True, timeout_s=min(per_call, left))
                comp = run.compactions(d.get("_events") or [])
                b_info.update(boundary_ok=any(c.get("trigger") == "manual" for c in comp) or dry,
                              boundary_cost_usd=float(d.get("total_cost_usd") or 0), boundary_min=float(d.get("duration_ms") or 0) / 60000)
                if is_infra(d):
                    return abort(out_dir, rawdir, side, n, f"/compact before {rid}: {str(d.get('result'))[:160]}", work)
                if not dry:
                    save_events(rawdir / f"{rid}-boundary.events.jsonl", d)
            elif boundary == "fresh":
                session, reset_pending = None, True
                b_info["boundary_ok"] = True
            elif boundary == "handoff" and session:
                d, _ = call(side_cfg.get("handoff_prompt") or HANDOFF_PROMPT, session, timeout_s=min(per_call, left))
                if is_infra(d):
                    return abort(out_dir, rawdir, side, n, f"handoff before {rid}: {str(d.get('result'))[:160]}", work)
                hp = work / "HANDOFF.md"
                b_info.update(boundary_ok=(hp.exists() and hp.stat().st_size > 200) or dry,
                              boundary_cost_usd=float(d.get("total_cost_usd") or 0), boundary_min=float(d.get("duration_ms") or 0) / 60000)
                if not dry:
                    save_events(rawdir / f"{rid}-boundary.events.jsonl", d)
                    if hp.exists():
                        (rawdir / f"{rid}-HANDOFF.md").write_text(hp.read_text()[:200_000])
                session, reset_pending = None, True
        prefix = ""
        if reset_pending:
            prefix += side_cfg.get("after_reset_prefix") or ""
            reset_pending = False
        if first_of_group:
            prefix += side_cfg.get("group_prefix") or ""
            if side_cfg.get("group_hook"):
                gids = ",".join(r["id"] for r in reqs if r["group"] == group)
                h = subprocess.run([str(tdir / side_cfg["group_hook"]), str(work), str(group), side, gids],
                                   capture_output=True, text=True, timeout=300)
                if h.returncode != 0:
                    sys.exit(f"group_hook failed ({side} m{n} group {group}): {h.stderr[-500:]}")
                prefix += h.stdout
        if side_cfg.get("mention_files"):
            have = [f for f in req.get("mention") or [] if (work / f).exists()]
            if have:
                prefix += "Relevant files: " + " ".join("@" + f for f in have) + "\n\n"
        prompt = prefix + req["prompt"]
        row = {"trick": tid, "side": side, "run": n, "request": rid, "group": group, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "prefix_chars": len(prefix), **b_info}
        left = cap - (time.time() - t_start)
        data, timeout = ({}, True) if left <= 0 else call(prompt, session, timeout_s=min(per_call, left))
        if left <= 0:
            row["grade_reason"] = "FAIL marathon time cap reached before this request"
        if not dry and data and is_infra(data):
            return abort(out_dir, rawdir, side, n, f"{rid}: {str(data.get('result'))[:160]}", work)
        events = data.get("_events") or []
        session = data.get("session_id") or next((e.get("session_id") for e in events if e.get("session_id")), session)
        ctx = ctx_sizes(events)
        comp = run.compactions(events)
        usage = data.get("usage") or {}
        row.update(timeout=timeout, duration_min=round(float(data.get("duration_ms") or 0) / 60000, 2),
                   cost_usd=round(float(data.get("total_cost_usd") or 0), 4), turns=data.get("num_turns") or 0,
                   input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                   cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                   cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                   ctx_first=ctx[0] if ctx else 0, ctx_peak=max(ctx) if ctx else 0, ctx_last=ctx[-1] if ctx else 0,
                   compacts=len(comp), auto_compacts=sum(1 for c in comp if c.get("trigger") == "auto"),
                   npm_test_calls=npm_test_calls(events), models="|".join((data.get("modelUsage") or {}).keys()),
                   permission_denials=len(data.get("permission_denials") or []), infra_error="")
        # per-call diff (what this call changed), graded on a clone: this request and every earlier one
        cur_tree = run.tree_of(work) if not dry else prev_tree
        st = subprocess.run(["git", "-C", str(work), "diff", "--shortstat", prev_tree, cur_tree], capture_output=True, text=True).stdout
        num = lambda word: next((int(x.split()[0]) for x in st.split(",") if word in x), 0)
        row.update(files_changed=num("file"), insertions=num("insertion"), deletions=num("deletion"))
        g = {k: {"pass": False, "failed": ["(dry run)"]} for k in ids[: i + 1]} if dry else grade(work, ids[: i + 1])
        grades_after[rid] = {k: v["pass"] for k, v in g.items()}
        passed = g[rid]["pass"] and not timeout
        reason = "PASS" if passed else ("FAIL timeout " if timeout else "FAIL ") + "; ".join(g[rid]["failed"][:4])
        if row.get("grade_reason"):
            reason = row["grade_reason"]
        row.update(passed=passed, grade_reason=reason[:400],
                   earlier_failing=" ".join(k for k in ids[:i] if not g[k]["pass"]))
        rows.append(row)
        if not dry:
            rawdir.mkdir(parents=True, exist_ok=True)
            d = subprocess.run(["git", "-C", str(work), "diff", prev_tree, cur_tree, "--", "."], capture_output=True, text=True).stdout
            (rawdir / f"{rid}.diff").write_text(d[:2_000_000])
            save_events(rawdir / f"{rid}.events.jsonl", data)
            keep = {k: v for k, v in data.items() if k != "_events"}
            keep["compactions"] = comp
            keep["context_sizes"] = ctx
            (rawdir / f"{rid}.json").write_text(json.dumps({"row": row, "claude": keep, "grades": g, "prompt_prefix": prefix[:20000]}, indent=1))
        prev_tree = cur_tree
        print(f"{'PASS' if passed else 'FAIL'} {side:<7} m{n} {rid} g{group} {row['duration_min']} min ${row['cost_usd']} "
              f"ctx {row['ctx_first']//1000}k->{row['ctx_peak']//1000}k compacts {row['compacts']} {b_info['boundary']}"
              f"{'' if passed else '  ' + reason[:120]}", flush=True)
    if dry:
        shutil.rmtree(work, ignore_errors=True)
        return
    final = grades_after[ids[-1]]
    for row in rows:
        rid = row["request"]
        later = [grades_after[k][rid] for k in ids[ids.index(rid):]]
        row["final"] = final[rid]
        row["kept"] = bool(row["passed"] and final[rid])
        row["regressed_later"] = bool(row["passed"] and not all(later))
    (rawdir / "marathon.json").write_text(json.dumps({"trick": tid, "side": side, "run": n, "started_at": started,
                                                      "minutes_wall": round((time.time() - t_start) / 60, 2),
                                                      "grades_after": grades_after, "rows": rows}, indent=1))
    extra = {}
    if trick.get("marathon", {}).get("end_check"):  # trick-specific measurement on the finished repo (NOTES.md etc.)
        chk = subprocess.run([str(tdir / trick["marathon"]["end_check"]), str(work), side], capture_output=True, text=True, timeout=300)
        extra = {"end_check": (chk.stdout.strip().splitlines() or [""])[-1][:500]}
        (rawdir / "end_check.json").write_text(json.dumps(extra))
    with lock:
        new = not (out_dir / "runs.csv").exists()
        with open(out_dir / "runs.csv", "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            if new:
                w.writeheader()
            for row in rows:
                w.writerow(row)
    shutil.rmtree(work, ignore_errors=True)


def save_events(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for e in data.get("_events") or []:
            fh.write(json.dumps(e) + "\n")


def abort(out_dir, rawdir, side, n, why, work):
    """Infrastructure error: the marathon is not graded; keep its raw files aside and log it, so a rerun starts over."""
    print(f"INFRA {side} m{n}: {why}", flush=True)
    dest = out_dir / "raw" / "_infra" / f"{rawdir.name}-{time.strftime('%Y%m%d-%H%M%S')}"
    if rawdir.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(rawdir), str(dest))
    with lock:
        with open(out_dir / "infra.csv", "a", newline="") as fh:
            csv.writer(fh).writerow([time.strftime("%Y-%m-%dT%H:%M:%S"), side, n, why])
    shutil.rmtree(work, ignore_errors=True)


def trick_fired(side_cfg, rawdir: Path, rows):
    """Pre-registered manipulation check for one marathon (PROTOCOL 2026-10-07): did the side's trick actually happen?
    compact/handoff: every boundary shows a manual compaction / a HANDOFF.md over 200 bytes; fresh: a new session at
    every boundary; mention_files: the @ list on the requests; pack hook (day 35): the pack read with content at >= 3
    of the 5 group starts; end_check notes (day 39): NOTES.md exists at the end. Sides with no trick: True."""
    b = side_cfg.get("boundary", "none")
    bound = [r for r in rows if r["boundary"]]
    if b in ("compact", "handoff", "fresh") and (len(bound) < 4 or not all(str(r["boundary_ok"]) == "True" for r in bound)):
        return False
    if side_cfg.get("mention_files") and not any(int(r["prefix_chars"] or 0) > 0 for r in rows):
        return False
    if side_cfg.get("group_hook") == "pack.sh":
        starts = [r["request"] for r in rows if r["request"] in ("r01", "r06", "r11", "r16", "r21")]
        ok = 0
        for rid in starts:
            ids, hit = {}, False
            p = rawdir / f"{rid}.events.jsonl"
            for line in (open(p) if p.exists() else []):
                e = json.loads(line)
                msg = e.get("message") if isinstance(e.get("message"), dict) else {}  # some events carry a plain-text message
                for c in msg.get("content") if isinstance(msg.get("content"), list) else []:
                    if c.get("type") == "tool_use" and str((c.get("input") or {}).get("file_path", "")).endswith("repomix-output.xml"):
                        ids[c.get("id")] = True
                    if c.get("type") == "tool_result" and ids.get(c.get("tool_use_id")) and not c.get("is_error"):
                        txt = c.get("content") if isinstance(c.get("content"), str) else json.dumps(c.get("content"))
                        hit = hit or (len(txt) > 2000 and "exceeds maximum" not in txt)
            ok += hit
        if ok < 3:
            return False
    if (rawdir / "end_check.json").exists() and side_cfg.get("overlay"):
        ec = json.loads(json.loads((rawdir / "end_check.json").read_text())["end_check"] or "{}")
        if "notes" in ec and not ec["notes"]:
            return False
    return True


# ---------- summary and the pre-registered marathon verdict rule (PROTOCOL change log, drafted 2026-10-07) ----------

GAP_PP = 8.0      # minimum gap in kept-request rate, percentage points, for works/hurts on passes
NOISE_PP = 4.0    # |gap| below this counts as "same pass rate" for the time/cost rules
ALPHA = 0.10      # two-sided run-level permutation p-value needed for works/hurts on passes
MIN_MARATHONS = 5  # complete marathons per side needed for a verdict


def permutation_p(a, b):
    """Exact two-sided p-value of the difference in means, relabelling whole marathons (the unit that is independent)."""
    pool, k = a + b, len(a)
    obs = abs(statistics.mean(a) - statistics.mean(b))
    hits = total = 0
    for idx in combinations(range(len(pool)), k):
        s = set(idx)
        x = [pool[i] for i in idx]
        y = [pool[i] for i in range(len(pool)) if i not in s]
        total += 1
        hits += abs(statistics.mean(x) - statistics.mean(y)) >= obs - 1e-12
    return hits / total


def decide_marathon(w, o):
    if w["marathons"] < MIN_MARATHONS or o["marathons"] < MIN_MARATHONS:
        return "inconclusive", f"fewer than {MIN_MARATHONS} complete marathons on a side (rerun the infrastructure errors)", None, None
    if w.get("manipulation_failed", 0) >= 2:
        return "inconclusive", "the trick did not fire in two or more marathons (manipulation check)", None, None
    gap = 100 * (w["kept_rate"] - o["kept_rate"])
    p = permutation_p(w["kept_by_marathon"], o["kept_by_marathon"])
    if gap >= GAP_PP and p <= ALPHA:
        return "works", f"{gap:+.1f} points of requests kept with the trick (p={p:.3f})", gap, p
    if gap <= -GAP_PP and p <= ALPHA:
        return "hurts", f"{gap:+.1f} points of requests kept with the trick (p={p:.3f})", gap, p
    if w["kept_rate"] == 0 and o["kept_rate"] == 0:
        return "no difference", "nothing kept on either side: the backlog is too hard for this setup", gap, p
    ratio = lambda a, b: a / b if b else 1.0
    t, c = ratio(w["avg_minutes"], o["avg_minutes"]), ratio(w["avg_cost_usd"], o["avg_cost_usd"])
    if abs(gap) < NOISE_PP and (t <= 0.75 or c <= 0.75) and t < 1.25 and c < 1.25:
        return "works", f"same pass rate ({gap:+.1f} points), at least 25% faster or cheaper per marathon", gap, p
    if abs(gap) < NOISE_PP and t >= 1.25 and c >= 1.25:
        return "hurts", f"same pass rate ({gap:+.1f} points), at least 25% slower and costlier per marathon", gap, p
    return "no difference", f"{gap:+.1f} points (p={p:.3f}): under {GAP_PP:.0f} points or not clear of noise, and no 25% time or cost gap", gap, p


def side_summary(rows, reqs, fired=None):
    by_m = {}
    for r in rows:
        by_m.setdefault(r["run"], []).append(r)
    ms = [v for v in by_m.values()]
    n_req = len(reqs)
    kept = [sum(r["kept"] for r in m) / len(m) for m in ms]
    imm = [sum(r["passed"] for r in m) / len(m) for m in ms]
    mins = [sum(float(r["duration_min"]) + float(r["boundary_min"] or 0) for r in m) for m in ms]
    cost = [sum(float(r["cost_usd"]) + float(r["boundary_cost_usd"] or 0) for r in m) for m in ms]
    curve = {}
    for q in reqs:
        rr = [r for r in rows if r["request"] == q["id"]]
        if rr:
            curve[q["id"]] = {"passed": sum(r["passed"] for r in rr), "kept": sum(r["kept"] for r in rr), "n": len(rr),
                              "ctx_last_median": int(statistics.median(int(r["ctx_last"]) for r in rr)),
                              "ctx_peak_median": int(statistics.median(int(r["ctx_peak"]) for r in rr)),
                              "compacted_in": sum(int(r["compacts"]) > 0 for r in rr),
                              "auto_compacted_in": sum(int(r["auto_compacts"]) > 0 for r in rr)}
    tags = {}
    for r in rows:
        # each reason reads "FAIL [tag] text; [tag] text": strip the "FAIL " prefix so the first tag is counted too
        for t in [x for x in str(r["grade_reason"]).removeprefix("FAIL ").split("; ") if x.startswith("[")]:
            k = t[1:t.index("]")]
            tags[k] = tags.get(k, 0) + 1
    # memory probes: for each house rule / decision, how often the requests that check it (without restating it) held it
    probes = {}
    by_id = {q["id"]: q for q in reqs}
    for r in rows:
        for t in by_id[r["request"]].get("probes") or []:
            if t in (by_id[r["request"]].get("states") or []):
                continue
            p = probes.setdefault(t, {"checked": 0, "held": 0})
            p["checked"] += 1
            p["held"] += f"[{t}]" not in str(r["grade_reason"])
    manip = [r for r in rows if r["boundary"] and r["boundary"] != "fresh"]
    return {
        "marathons": len(ms), "requests_per_marathon": n_req, "graded_requests": len(rows),
        "passed": sum(r["passed"] for r in rows), "kept": sum(r["kept"] for r in rows),
        "pass_rate": round(statistics.mean(imm), 4) if ms else 0, "kept_rate": round(statistics.mean(kept), 4) if ms else 0,
        "kept_by_marathon": [round(x, 4) for x in kept],
        "regressions": sum(r["regressed_later"] for r in rows),
        "timeouts": sum(r["timeout"] for r in rows),
        "avg_minutes": round(statistics.mean(mins), 2) if ms else 0, "avg_cost_usd": round(statistics.mean(cost), 3) if ms else 0,
        "auto_compactions": sum(int(r["auto_compacts"]) for r in rows),
        "first_auto_compaction_at": sorted({r["request"] for r in rows if int(r["auto_compacts"]) > 0})[:3],
        "boundary_actions": len(manip), "boundary_misses": sum(1 for r in manip if str(r["boundary_ok"]) not in ("True", "true", "1")),
        "manipulation_failed": sum(1 for f in (fired or {}).values() if not f), "trick_fired_by_marathon": fired or {},
        "npm_test_calls_per_request": round(statistics.mean(int(r["npm_test_calls"]) for r in rows), 2) if rows else 0,
        "failed_test_tags": dict(sorted(tags.items())),
        "memory_probes": dict(sorted(probes.items())),
        "curve": curve,
    }


def summarize(trick, tid, out_dir):
    path = out_dir / "runs.csv"
    if not path.exists():
        sys.exit("No runs.csv yet.")
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        for k in ("passed", "kept", "final", "regressed_later", "timeout"):
            r[k] = r[k] == "True"
    reqs = load_requests(trick)
    fired = {}
    for side in ("with", "without"):
        for n in sorted({r["run"] for r in rows if r["side"] == side}):
            fired[(side, n)] = trick_fired(trick["sides"][side], out_dir / "raw" / f"{side}-m{n}",
                                           [r for r in rows if r["side"] == side and r["run"] == n])
    w = side_summary([r for r in rows if r["side"] == "with"], reqs, {f"m{n}": f for (sd, n), f in fired.items() if sd == "with"})
    o = side_summary([r for r in rows if r["side"] == "without"], reqs, {f"m{n}": f for (sd, n), f in fired.items() if sd == "without"})
    verdict, why, gap, p = decide_marathon(w, o)
    summary = {"trick": tid, "day": trick.get("day"), "name": trick.get("trick"), "mode": "marathon",
               "with": w, "without": o, "gap_points": gap, "permutation_p": p, "verdict": verdict, "verdict_reason": why,
               "rule": {"gap_pp": GAP_PP, "noise_pp": NOISE_PP, "alpha": ALPHA, "min_marathons": MIN_MARATHONS},
               "cost_note": "API-equivalent estimate reported by Claude Code"}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    with open(out_dir / "curve.csv", "w", newline="") as fh:  # the staleness curve: pass rate by request index per side
        wcsv = csv.writer(fh)
        wcsv.writerow(["request", "group", "side", "n", "passed", "kept", "ctx_last_median", "ctx_peak_median", "auto_compacted_in"])
        for q in reqs:
            for s, st in (("with", w), ("without", o)):
                c = st["curve"].get(q["id"])
                if c:
                    wcsv.writerow([q["id"], q["group"], s, c["n"], c["passed"], c["kept"], c["ctx_last_median"], c["ctx_peak_median"], c["auto_compacted_in"]])
    print(f"\n{tid} · {trick.get('trick')} (marathon)")
    for s, st in (("with", w), ("without", o)):
        print(f"  {s:<8} kept {st['kept']}/{st['graded_requests']} ({100*st['kept_rate']:.1f}%) · passed {st['passed']} · "
              f"{st['marathons']} marathons · {st['avg_minutes']} min · ${st['avg_cost_usd']} per marathon · regressions "
              f"{st['regressions']} · auto-compactions {st['auto_compactions']} · trick not fired in {st['manipulation_failed']} marathons")
    print(f"  VERDICT: {verdict} ({why})")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trick")
    ap.add_argument("--runs", type=int)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--side", choices=["with", "without"])
    ap.add_argument("--max-requests", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summarize-only", action="store_true")
    a = ap.parse_args()
    trick = run.load_trick(a.trick)
    if not trick.get("marathon"):
        sys.exit(f"{a.trick} is not a marathon trick (no 'marathon' key); use harness/run.py")
    out_dir = LAB / "runs" / a.trick
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.summarize_only:
        return summarize(trick, a.trick, out_dir)
    if not a.dry_run and not os.environ.get("LAB_CLAUDE_CONFIG_DIR"):
        print("WARNING: LAB_CLAUDE_CONFIG_DIR is not set, so your user-level agents and commands may load into runs.")
    runs = 1 if a.dry_run else (a.runs or trick.get("runs", 6))
    sides = [a.side] if a.side else ["with", "without"]
    jobs = [(s, n) for n in range(1, runs + 1) for s in sides]
    with ThreadPoolExecutor(max_workers=1 if a.dry_run else a.parallel) as ex:
        futs = [ex.submit(run_marathon, trick, a.trick, s, n, out_dir, a.dry_run, a.max_requests) for s, n in jobs]
        for f in as_completed(futs):
            f.result()
    if not a.dry_run:
        summarize(trick, a.trick, out_dir)


if __name__ == "__main__":
    main()
