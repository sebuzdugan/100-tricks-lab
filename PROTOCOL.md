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
