Bug report: `frai gate init --ci` does not create the GitHub Actions workflow.

Steps to reproduce, from any empty folder:
1. Run `node <repo>/packages/frai-cli/dist/index.js gate init --ci`
2. `FRAI-SPEC.md` is created, but `.github/workflows/rai-gate.yml` is not, and there is no error.

Running `frai-gate init --ci` directly (packages/frai-gate) does create the workflow, so the problem is in how the `frai` CLI passes the flag through.

Fix it in the source of the `frai` CLI (packages/frai-cli/src), rebuild that package with `pnpm --filter frai build`, and confirm the workflow file is now created. Do not change packages/frai-gate.
