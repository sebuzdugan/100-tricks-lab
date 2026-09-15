# 100 Tricks Lab: test protocol

Written 14 September 2026, before any run. The verdict rule below is fixed for all 100 days. If it ever has to
change, the change and the date go in the change log at the bottom, and earlier results are not rescored silently.

## What is being tested

Each day tests one popular AI coding trick by running the same tasks **with** and **without** it and comparing
how many runs pass, how long they take and what they cost.

## The fixed tasks

All tasks run on `base/frai`: the open-source [frai](https://github.com/sebuzdugan/frai) repository at commit
`f3c8624`, the state just before the real fix in `902ec19`, rebuilt as a single commit with no history (so an agent
can't read the fix from `git log`). One test file is pre-aligned so every remaining failure has one right answer.

| Task | Type | The agent is asked to | Graded by (`tasks/<task>/accept.sh`) |
|---|---|---|---|
| `t1-flag-bug` | Real bug | Fix `frai gate init --ci` silently not creating the workflow | Builds the CLI, runs `init --ci` and plain `init` in empty folders, checks `frai-gate` was not modified |
| `t2-failing-tests` | Real failing tests | Make the frai-core suite pass without touching tests | Suite passes, no existing test file modified or deleted (new test files are allowed), hidden contract tests (toxicity still works, references don't leak, exports exist) |
| `t3-summary-feature` | Feature | Add `renderSummary` and a `--summary` flag to `frai-gate check` | Builds, suite passes, hidden `renderSummary` tests, one-line CLI output, exit codes, `--json` priority |

Every task was validated before day 1: each **fails** on the untouched baseline and **passes** with the reference
fix in `reference/`. Cheating variants (editing a test, disabling the toxicity metric, touching `frai-gate` in t1,
implementing the function without the flag in t3) all **fail**.

## A run

- Fresh copy of the baseline per run (APFS clone), under `/private/tmp/100-tricks-runs`, outside any folder with a
  CLAUDE.md.
- Headless Claude Code: `claude -p <task prompt> --output-format json --permission-mode acceptEdits`, allowed tools
  limited to file tools plus `pnpm`, `npx`, `node`, read-only `git`, `ls`, `cat`, `mkdir`. Anything else is denied.
- Isolated from Sebi's own setup: a separate Claude config folder (`LAB_CLAUDE_CONFIG_DIR`), user setting sources
  off, no MCP servers, skills off unless the trick is about skills.
- Nothing outside the run folder is needed, so file reads under the lab's parent folder are denied (best effort: it
  blocks the built-in file tools and plain `cat`/`ls` there). Hidden tests are copied in only after the agent finishes.
- Model and effort: Claude Code defaults unless the trick is about models. The model actually used is recorded per run.
- Timeout: 20 minutes. A timeout counts as a failed run.
- No API keys. Runs use the Claude subscription; cost is Claude Code's API-equivalent estimate.

## Default size

3 tasks × 3 runs × 2 sides = **18 runs per trick**, up to 3 in parallel. Some days differ and say so in `plan/days.json` (`runs_per_side`, `task_note`): bug-only tricks use t1 and t2 (12 runs), some use their own fixture, long autonomous runs use one run per side. Days 47 and 49 are measurement days with no verdict.

If the first test block shows that 18 runs per trick won't fit the subscription's usage limits across two blocks a
week, drop to **2 runs per side (12 runs)** from then on. The post always states the real run count.

## Verdict rule (pre-registered)

Using graded runs only (infrastructure errors excluded):

1. **Inconclusive**: two or more runs on either side hit an infrastructure error (usage limit, login, API outage).
   Rerun before posting.
2. **Works**: the trick side passes at least 2 more runs.
3. **Hurts**: the trick side passes at least 2 fewer runs.
4. **Works**: pass counts are equal or the trick side is 1 ahead, and it is at least 25% faster or cheaper without
   being 25% slower or costlier.
5. **Hurts**: pass counts are equal or the trick side is 1 behind, and it is at least 25% slower **and** costlier.
6. Otherwise **no difference**. If nothing passed on either side, say the tasks were too hard for that setup.

`harness/run.py` applies this rule automatically (`decide()`).

## Reporting rules

- Post the numbers exactly as the summary shows them. Every verdict is posted, including "hurts" and "no difference".
- Say it is a small sample: 9 runs a side on 3 tasks is evidence, not proof.
- Link the raw runs (`runs/<day>/runs.csv` and `summary.json`).
- Test the trick the way its author described it and link the original.
- Sponsored days: the sponsor buys the slot, never the result.

## Run modes

Not every trick can run headless. Each day in the Notion scorecard has a **Run mode**:

- **Headless**: `harness/run.py` as above.
- **Two-step script**: two headless calls in sequence (for example plan first, then execute from the plan).
- **Interactive**: Sebi runs the sessions by hand with a fixed script and answer sheet, same tasks, same grading
  scripts (for tricks that need a human reply, or features that only exist interactively, such as checkpoint rewind).
- **Special fixture**: the trick needs its own small repo or setup (safety tests, long runs, disclosure checks). The
  fixture is added to `tasks/` and validated the same way (fails before, passes with a reference) before its day.

## Change log

- 2026-09-14: protocol written, tasks validated, day 1 trick defined.
- 2026-09-15: runner denies reads outside the run folder; repo published at github.com/sebuzdugan/100-tricks-lab.
- 2026-09-15: before any run. t2 grader now fails only modified, deleted or renamed existing test files; adding a new test file is allowed, because the prompt only forbids editing tests. Revalidated: baseline fails, reference passes, edited test fails, reference plus a new test passes.
- 2026-09-15: runner sets `CI=true` (keeps vitest out of watch mode), saves each run's diff, and supports per-task prompts, follow-up turns in the same session, per-side environment (local models through Ollama), extra allowed tools, a trick-specific check, and third-party trick files fetched at a pinned URL and hash.
- 2026-09-15: all 100 days reviewed against live sources (`plan/briefs.json`). Day 1 uses the original viral CLAUDE.md unchanged instead of a paraphrase. One-run-per-side days (91, 92, 94, 95) will get a grading-unit rule in this log before 13 Dec.
- 2026-09-15: before any run. A side with zero passes can't "work" by being cheaper: if nothing passes on either side the verdict is no difference (tasks too hard), checked before the time and cost rules. Previously rule 4 could fire first.
- 2026-09-15: before any run. Runs use `--output-format stream-json --verbose` instead of `json`, and every event (tool calls, command output, edits) is saved to `raw/<run>.events.jsonl`, so posts can show what the agent actually did. The final result event carries the same fields as before, so grading, cost and the verdict are unchanged. The runner also drops all inherited `CLAUDE*`/`ANTHROPIC*` variables so runs started from another Claude session don't hang.
- 2026-09-15: before any run. A side's overlay files (CLAUDE.md, hooks, commands) are folded into the run copy's baseline commit and `lab-base` moves with them, so graders, trick checkers, saved diffs and `files_changed` count only the agent's own changes. Without this, an overlay file inside `packages/frai-gate` (day 5) would have failed t1's untouched-package check on its own.
- 2026-09-15: after day 1's first attempt (all 18 runs passed, see below). Allowed shell glue commands that agents chain into their commands: `cd`, `echo`, `printf`, `head`, `tail`, `grep`, `find`, `wc`, `sort`, `pwd`, `mktemp`, `test` (reads under /Users and ~ stay denied). Day 1's logs showed about 3.5 denied commands per run on both sides, nearly all harmless glue, which wasted turns and would muddy days that count denials.
- 2026-09-15: day 1 first attempt on the original three tasks: with 9/9, without 9/9, about one minute and $0.50 a run on both sides. The default model (Opus 5) solves all three tasks every time, so no trick can show a difference. A harder task set is being built and piloted before any day is posted; the original tasks stay in the repo, and day 1's first attempt stays in `runs/d01-core3/` as a published result.
- 2026-09-15: pilots before any posted day. Hard tasks h1 to h4 on the default model (Opus 5): 23 of 24 passed (`runs/pilot-hard`). Sonnet 5: 7 of 8, Haiku 4.5: 0 of 8 (`runs/pilot-models`). A Haiku pilot on t1 to t3 hit the subscription session limit and was discarded; the runner now also treats "session limit", "weekly limit" and any API error status (429, 5xx) as infrastructure errors, which rule 1 reruns instead of grading.
- 2026-09-15: before any posted day. Haiku 4.5 on t1 to t3 passed 10 of 12 (`runs/pilot-haiku-core`), against 0 of 8 on the hard tasks. From day 1, every day runs **t1, t2, t3 and h2 on Haiku 4.5, both sides** (3 runs per task, 24 per day). Reason: on the default model (Opus 5) and on Sonnet 5 nearly every run passes, so no trick can move the pass rate; on Haiku this mixed set sits in the middle, so a trick can help or hurt. Posts say the model plainly. h1, h3 and h4 stay in the repo for later days. Day 7's command-free prompts are restored for t1 to t3 (h2 names no commands).
- 2026-09-15: before any posted day. **h2 grader fix:** the prompt says "Document the option with the other frai eval options"; those options are listed only in `frai eval --help` (the READMEs just name the command), but the grader accepted only the READMEs. It now also accepts the help text. The four h2 cheat variants still fail, the reference still passes. Runs already graded are regraded from their saved diffs with `harness/regrade.py` (old result kept in the raw row as `regraded_from`): day 1 without-side h2 run 3 and day 2 with-side h2 run 2 and without-side runs 1 to 3 flip to pass, all of which had failed only on that check. **Crashed runs:** a run with no result event at all (Claude Code crashed, e.g. a Bun segfault on day 2) is now an infrastructure error instead of a failed run; day 2's crashed run was rerun. Day 1 is now 7/12 vs 7/12 and day 2 10/12 vs 10/12, both no difference.
- 2026-09-15: the runner now applies the timeout rule itself: a run that hits the 20-minute limit is failed even if the repo it left behind passes the grader. Day 3's without-side t1 run 2 timed out with a working fix on disk and had been graded pass; it is now a fail (day 3: 8/12 vs 8/12).
