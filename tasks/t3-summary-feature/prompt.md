Feature request for frai-gate (packages/frai-gate): a one-line summary for CI logs.

1. Add and export `renderSummary(result: GateResult): string` in `src/gate/report.ts`.
   - Format: `<VERDICT> <answered>/<total>` where total is the number of GATE_CHECKS (7) and answered is how many of those checks have no `block`-severity finding. Warnings do not reduce answered.
   - If there are block findings for any of the GATE_CHECKS, append `: ` and their check ids, comma-and-space separated, in GATE_CHECKS order, each id once. Example: `BLOCK 5/7: evaluation, transparency`
   - If the gate section itself is missing (a `structure` finding), return `BLOCK 0/7: structure`.
2. Add a `--summary` flag to `frai-gate check`: print only the summary line instead of the full report. Exit codes stay the same (1 on BLOCK, 0 otherwise). `--json` keeps priority if both flags are given.
3. Document the flag in the HELP text and add tests for `renderSummary`.

Build with `pnpm --filter frai-gate build` and make sure `pnpm --filter frai-gate test` passes.
