Feature request: let `frai eval` fail a CI job when a metric is too low.

Today `frai eval` always exits 0, so a pipeline can't gate on it. Add a `--threshold <metric>=<min>` option to `frai eval` (for example `--threshold exact_match=0.9`) that can be given more than once.

- A threshold passes when the metric's score is at least the minimum. A metric with no score (such as exact match without references) fails its threshold instead of crashing or passing.
- Exit 1 if any threshold fails, 0 if all pass. The report is written either way and records the outcome: JSON reports gain a top-level `passed` and a `thresholds` list with one `{ metric, min, score, passed }` entry per threshold; Markdown reports gain a "Thresholds" section showing PASS or FAIL for each.
- A malformed threshold (not `<metric>=<number>`, or a minimum outside 0 to 1) or an unknown metric id is a usage error: exit 2 with a message saying what is wrong (list the valid metric ids for an unknown one), and write no report.
- Without `--threshold`, reports and exit codes stay exactly as they are today.

SDK users need this too, so the logic belongs in frai-core: `generateReport` accepts an optional `thresholds` object (`{ exact_match: 0.9 }`) and adds the same fields, and it must work for custom metrics passed to `runEvaluations`. Document the option with the other `frai eval` options.

Two frai-core tests already fail on main for unrelated reasons; they're tracked separately.
