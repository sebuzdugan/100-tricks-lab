## packages/frai-gate

- TypeScript. Build: `pnpm --filter frai-gate build` (`tsc` to `dist/`, declarations in `dist/types`). Test: `pnpm --filter frai-gate test`.
- The tsconfig excludes `src/**/*.test.ts`, so tests never land in `dist/`.
- `src/cli.ts` is the `frai-gate` command (bin `dist/cli.js`); try it with `node packages/frai-gate/dist/cli.js help`.
- `src/gate/`: `schema.ts` (types and the gate checks), `validate.ts` (`validateSpec`, pure and offline), `report.ts` (text and JSON rendering).
- `src/pipeline/agent.ts` is the only code that calls Claude (Claude Agent SDK with read-only tools).
- `src/index.ts` re-exports the package's public API, built to `dist/index.js`.
- `frai-gate check <spec>` without `--smart` is deterministic and offline; `draft` and `check --smart` call Claude, so don't run them.
- `assets/rai-spec-template.md` is the spec template the package ships; `src/gate/validate.test.ts` reads it.
- Single quotes; Node built-ins use the `node:` prefix (`node:fs/promises`, `node:path`).
