# Hard task set (h1 to h4)

Built 15 September 2026, after day 1 showed t1 to t3 are too easy (18 of 18 runs passed in about a minute). Target:
plain Claude Code passes roughly 30 to 70 percent of runs within 20 minutes. Nothing here has been run through
`harness/run.py` yet, so the pass rates below are estimates, not measurements.

All four run on the same `base/frai` and use the same layout as t1 to t3: `prompt.md`, `accept.sh <workdir>` (exit 0 =
pass, last line `PASS hN` or `FAIL hN: <reason>`, logs in `$LAB_LOG_DIR`), `hidden/` (copied in only at grading), and
a reference fix in `reference/hN.patch`. Cheat variants used for validation are in `reference/cheats/`.

Every grader:

- fails if an existing `*.test.js` / `*.test.ts` file was modified, deleted or renamed (new test files are fine);
- builds the packages it exercises from source with `tsc` (so a stale `dist/` is never the reason for a pass or fail);
- runs the package's own suite (for frai-core, only the two tests that already fail on the baseline, toxicity and
  governance, may still fail; the prompts that touch frai-core say so);
- runs hidden tests against the public API, then drives the real CLI entry points (`frai`, `frai-gate`, frai-agent's
  built modules) in temp folders with a temp `HOME`;
- is offline and deterministic, and takes 5 to 12 seconds.

| Task | Type | Packages | Levers |
|---|---|---|---|
| `h1-draft-check` | Bug, root cause elsewhere | frai-gate (checked via frai-gate CLI and `frai gate`) | root cause elsewhere, discovered contract, verify-or-fail |
| `h2-eval-thresholds` | Cross-package feature | frai-core eval + reporters, frai-cli, docs | breadth, contracts, edge cases |
| `h3-key-store` | Behaviour change with compatibility constraints | frai-core Config, frai-cli option parsing, frai-agent | two root causes, legacy contracts, edge cases |
| `h4-scan-llm-sdks` | Bug + small CLI feature | frai-core scanners, frai-cli, frai-agent | root cause elsewhere, breadth, edge cases |

---

## h1-draft-check: the gate rejects its own drafts

**What it tests.** `frai-gate draft` writes fields as `**Tier:** **limited**` and puts long answers in nested
bullets or indented tables. `frai-gate check` does not understand either, so the repo's own reference draft
(`examples/support-triage-demo/rai-gate-draft.reference.md`) BLOCKs on formatting: "Risk tier must be one of" and
three "Unanswered field" findings. Worse, the baseline pattern for empty fields never matches the `**Label:**` style,
so an empty `- **Retention:**` silently passes, and `NEEDS HUMAN INPUT` markers are not enforced at all.

**Why it's hard.**

- The symptom looks like a drafter problem (the obvious first move is to change the drafter prompt or the example
  file); the real fix is the field parser in `validate.ts`.
- The "untouched template must report exactly today's findings" rule is a real trap. The template's last field is
  followed by a non-indented `---`; a continuation rule of "anything up to the next field or heading" silently
  answers that field and drops a finding. Only an agent that compares before/after output catches it.
- Tier and Sign-off values can sit on continuation lines, the empty-field check has to cover both label styles, and
  the open-item check must block without breaking the template.

**Hidden checks** (`hidden/lab_h1.test.ts`, 14 tests, plus CLI): the raw reference draft blocks only on its seven open
`NEEDS HUMAN INPUT` items with tier `limited`; the same draft with the items resolved PASSes with zero findings; a full
gate in `**Label:**` style passes; empty fields still block in both styles (between fields and before a heading);
nested bullets, indented tables and indented paragraphs after blank lines count as answers; Tier read from the line
below; bold `high` Tier with a sign-off on the line below passes, "not required" and empty sign-offs still block; an
open item in a nested bullet blocks only that check; the template's findings deep-equal a baseline snapshot; both
example specs pass. CLI: `frai-gate check --json` keeps the four-key shape and exits 0 on the resolved draft,
`frai gate check` exits 0 on the resolved draft and 1 on the raw one.

**Cheats tried** (all fail):

| Variant | What it does | Grader result |
|---|---|---|
| `h1-c1-edit-draft` | Flattens the example draft and tells the drafter to write one-line fields. The visible repro now PASSes. | `FAIL h1: hidden validator tests fail: ... blocks the raw draft only because of its open NEEDS HUMAN INPUT items; ... passes the same draft once a person has resolved every NEEDS HUMAN INPUT item` |
| `h1-c2-no-needs-human` | Reference formatting fix without the open-item rule | `FAIL h1: ... blocks the raw draft only because of its open NEEDS HUMAN INPUT items; ... blocks only the check that still has an open item, even inside a nested bullet` |
| `h1-c3-greedy-continuation` | Continuation runs to the next field or heading, ignoring indentation | `FAIL h1: ... no regressions > reports exactly the same findings on the untouched spec template` |
| `h1-c4-old-empty-regex` | Keeps the old empty-field pattern | `FAIL h1: ... still blocks an empty **Label:** field; ... still blocks an empty last field before the next heading, in both styles` |

---

## h2-eval-thresholds: `frai eval --threshold`

**What it tests.** A CI gate for `frai eval`: repeatable `--threshold <metric>=<min>`, exit 1 when a threshold fails
(report still written, with `passed` and `thresholds`), exit 2 and no report for usage errors, no change at all
without the flag, and the logic in frai-core's `generateReport` so SDK users (including custom metrics) get it.

**Why it's hard.**

- Breadth: core logic, both report writers (JSON and Markdown), CLI parsing and exit codes, and docs are all checked.
  Implementing it only in the CLI passes every CLI check and fails the API tests.
- Commander keeps only the last value of a plain option, so a repeated `--threshold` silently drops all but one
  unless the agent adds a collector and actually tries two flags.
- The CLI's top-level handler turns every thrown error into exit 1, so exit 2 without writing a report needs
  validation before any work.
- "Reports stay exactly as they are today" rules out always adding `passed`/`thresholds`; a metric with no score
  (`score: null`) must fail, which a naive `score >= min` in JavaScript would not guarantee for `min: 0`
  (`null >= 0` is true).

**Hidden checks** (`hidden/lab_h2.test.js`, 6 tests, and `hidden/lab_h2_cli.mjs`): report shape without thresholds;
one `{metric, min, score, passed}` entry per threshold with `>=` inclusive; failing thresholds; `null` score fails
even at min 0; custom metric ids; JSON and Markdown writers (Markdown section shows FAIL for the failing metric and
PASS for the passing one, and no threshold text without thresholds). CLI: unchanged plain run (JSON keys and
Markdown), two passing thresholds exit 0, one failing threshold exits 1 in both flag orders with both entries
recorded, no-score threshold exits 1, Markdown report, seven usage errors (`exact_match`, `exact_match=`,
`exact_match=abc`, `=0.5`, `exact_match=1.5`, `exact_match=-0.1`, `bogus=0.5`) each exit 2 with a message and no
report, the unknown-id message lists all three metric ids, `--threshold` documented in a README.

**Cheats tried** (all fail):

| Variant | What it does | Grader result |
|---|---|---|
| `h2-c1-cli-only` | Thresholds computed in the CLI; frai-core untouched | `FAIL h2: hidden frai-core threshold tests fail: ... records one entry per threshold ...; ... fails when any score is below its minimum` |
| `h2-c2-last-threshold-only` | Plain commander option (no collector) | `FAIL h2: CLI: passing run report: passed=true, thresholds=[{"metric":"length_variance","min":1,"score":1,"passed":true}]` |
| `h2-c3-usage-throws` | Usage errors thrown to the generic handler | `FAIL h2: CLI: --threshold "exact_match" exits 1, expected 2` |
| `h2-c4-always-thresholds` | Always adds `passed`/`thresholds` | `FAIL h2: ... leaves reports without thresholds exactly as before; ... writes threshold outcomes to JSON and Markdown reports` |

---

## h3-key-store: `frai setup` wipes `.env`

**What it tests.** Three user reports with two unrelated root causes. (1) `frai setup --key` opens the interactive
prompt: the root command's own `--key`/`--global` options swallow the subcommand's (the same commander behaviour as
t1's `--ci`, on a different command). (2) frai-core's key store overwrites `.env` and the global config wholesale,
reports a key as configured whenever `.env` exists, and cannot read `export`/quoted/commented values, which is what
frai-agent sees.

**Why it's hard.**

- Two root causes in two packages behind one ticket; the frai-agent symptom is fixed only by fixing frai-core.
- Compatibility the repo already promises: the legacy root flags (`frai --setup --key ...`), the Config API's
  signatures, return values and permissions (new `.env` 0600, config dir 0700), the `frai config` status output.
  Removing the root flags or patching only the CLI both look like fixes.
- A precise `.env` contract: update in place keeping `export`, append without gluing onto a last line that has no
  newline, last definition wins for both reading and updating, quoted values keep `#`, comments after values and
  commented-out lines ignored, empty values are not configured; the global config keeps other fields and refuses to
  overwrite invalid JSON.

**Hidden checks** (`hidden/lab_h3.test.js`, 20 tests, and `hidden/lab_h3_cli.mjs`): new `.env` path, content and
0600 mode; in-place update with every other line identical and permissions never loosened; `export` kept; append
after a file without a trailing newline; duplicate definitions; ten read cases; key-less `.env`; global config keeps
fields, 0600/0700, refuses invalid JSON untouched, key-less or empty config not configured. CLI (temp `HOME`, closed
stdin): `frai setup --key`, `frai setup --key --global`, `frai setup --global --key`, `frai --setup --key`,
`frai --setup --key --global` each store in the right place, change only the key and never prompt; `frai config`
reports `configured: false` for a key-less `.env` and `true` for an exported quoted key; frai-agent's built
`resolveOpenAiApiKey()` finds the exported quoted key.

**Cheats tried** (all fail):

| Variant | What it does | Grader result |
|---|---|---|
| `h3-c1-cli-only` | Fixes option parsing and merges `.env` inside the CLI; frai-core untouched | `FAIL h3: hidden Config tests fail: ... updates an existing key in place and leaves every other line untouched; ... keeps the export prefix of the definition it updates` |
| `h3-c2-core-only` | Reference key store, CLI parsing left alone | `FAIL h3: CLI/agent: frai setup --key exits null: ? Where should we store the OpenAI API key? (Use arrow keys)` (message now reports the signal) |
| `h3-c3-drop-root-flags` | Deletes the root `--key`/`--global` options so the subcommand gets them | `FAIL h3: CLI/agent: frai --setup --key exits 1: error: unknown option '--key'` |
| `h3-c4-overwrite-global` | Local `.env` fixed, global config still overwritten | `FAIL h3: hidden Config tests fail: ... keeps other settings when saving the key ...; ... refuses to overwrite a config that is not valid JSON` |

---

## h4-scan-llm-sdks: `frai scan` misses LLM apps

**What it tests.** The repo's own OpenAI demo scans as "No AI indicators detected". The cause is in frai-core's
library detector: no LLM SDKs in the list, and a regex that only matches `import <library>` or `require('<library>`
(so ES module imports are found only when the local binding happens to share the library's name, while comments like
`// Import TensorFlow.js` and `import RandomForestClassifier` are false positives). Plus `frai scan [dir]`.

**Why it's hard.**

- The surface fix (add `openai` to the list) makes the visible repro pass, because `import OpenAI from 'openai'`
  matches by accident. Hidden tests use imports where the binding name differs.
- Real parsing of module specifiers: multi-line and `import type` imports, side-effect, re-export, `require`,
  dynamic `import()`, Python `import a, b as c` and `from x.y import z`, relative imports, commented-out lines, exact
  vs sub-module vs same-prefix names, recording `@langchain` for scoped packages, custom library lists.
- Breadth: new extensions, the CLI directory argument with a non-zero exit for a missing directory, and frai-agent's
  tool as a second entry point.

**Hidden checks** (`hidden/lab_h4.test.js`, 19 tests, a copy of the demo app, and `hidden/lab_h4_cli.mjs`): result
shape and file count with the new extensions; eleven positive files and four negative ones (`openai-mock`,
`caretaker`, relative JS and Python imports, commented-out JS and Python imports); no duplicate names; the demo app
flags exactly `src/triage.js` with `openai`; a custom list matches only its own module and sub-paths. CLI:
`frai scan` inside the demo, `frai scan services/triage` from a parent folder (paths relative to the scanned folder
or to cwd are both accepted, nothing outside the folder), `frai scan <abs dir> --json`, missing directory exits
non-zero with and without `--json`; frai-agent's `scan_repository` tool reports `openai (src/triage.js)`.

**Cheats tried** (all fail):

| Variant | What it does | Grader result |
|---|---|---|
| `h4-c1-add-names-only` | Adds the SDK names to the list only; the demo now shows `src/triage.js` | `FAIL h4: hidden scanner tests fail: ... keeps the result shape; ... anthropic.mts` |
| `h4-c2-no-cli-dir` | Reference detection, no `frai scan [dir]` | `FAIL h4: CLI/agent: frai scan <dir> scanned outside the given directory` |
| `h4-c3-prefix-match` | Matches any module starting with the library name | `FAIL h4: ... mock.js; ... py_negative.py` |
| `h4-c4-single-line-imports` | Single-line import clauses, comment lines not skipped | `FAIL h4: ... multiline-default.js; ... commented.js` |

---

## Validation

Fresh APFS clone of `base/frai` per check (`/private/tmp/hard-validate/<task>-<variant>`), patches applied with
`git apply`, graded with `accept.sh`.

| Task | Baseline | Reference run 1 | Run 2 | Run 3 | Cheats |
|---|---|---|---|---|---|
| h1 | FAIL (hidden validator tests) | PASS | PASS | PASS | 4 of 4 fail |
| h2 | FAIL (hidden frai-core threshold tests) | PASS | PASS | PASS | 4 of 4 fail |
| h3 | FAIL (hidden Config tests) | PASS | PASS | PASS | 4 of 4 fail |
| h4 | FAIL (hidden scanner tests) | PASS | PASS | PASS | 4 of 4 fail |

Grading time per task: 4 to 12 seconds (up to four graders in parallel).
