# frai

FRAI is a Responsible AI toolkit in a pnpm monorepo with four packages under `packages/`: frai-cli, frai-core, frai-gate and frai-agent.

## Repo-wide

- Use pnpm (`packageManager` is pnpm@8.15.4), not npm or yarn. Install with `pnpm install`.
- Run a package script with `pnpm --filter <package name> <script>`; the package name is the `name` in its package.json.
- Whole repo through turbo: `pnpm build` and `pnpm test`.
- Tests use Vitest (root `vitest.config.ts`). Run one file with `npx vitest run <path>` from inside the package folder.
- ES modules everywhere (`"type": "module"`); TypeScript uses NodeNext resolution, so relative imports end in `.js`.
- Style everywhere: 2-space indent, semicolons, no trailing commas.
- `dist/` folders are committed build output: never edit them by hand, rebuild the package instead.
- Workspace dependencies: `frai` uses `frai-core` and `frai-gate`; `frai-agent` uses `frai-core`; frai-core and frai-gate use no other workspace package.
- `examples/` has sample AI code and filled-in specs; `docs/architecture-target.md` describes a planned layout, not the current one.
- Generated files (`checklist.md`, `model_card.md`, `risk_file.md`, `frai-index.json`, `frai-eval-report.*`) are gitignored; don't commit them.
- Never print, log or commit an API key.

## packages/frai-cli (package name `frai`)

- The package name is `frai`, not `frai-cli`: build with `pnpm --filter frai build`.
- The whole CLI is `src/index.ts` (commander); `tsc` builds it to `dist/index.js`, which is the `frai` bin.
- Try it after building: `node packages/frai-cli/dist/index.js --help`; `<command> --help` shows one command's options.
- Running `frai` with no subcommand starts an interactive questionnaire that waits for keyboard input.
- Most commands call a `run...` helper (`runGenerateFlow`, `runRagIndexCommand` and others) defined above `main()`, where commander registers them.
- frai-core is used through its namespaces: `import { Scanners } from 'frai-core'`, then `Scanners.scanCodebase(...)`.
- Status messages go through the `log` helper (`log.info`, `log.success`, `log.warn`, `log.error`); raw output such as JSON uses `console.log`.
- This package has no test files.
- Single quotes; Node built-ins are imported by bare name (`'fs'`, `'path'`).

## packages/frai-core

- Plain JavaScript ES modules: no build step, no runtime dependencies, and `main` is `src/index.js`.
- `src/index.js` re-exports one namespace per module folder: Config, Questionnaire, Documents, Scanners, Rag, Eval, Providers, Finetune.
- Each module folder has an `index.js`; config, providers, questionnaire, rag and scanners also keep shared constants in `constants.js`.
- New code here stays `.js`; no TypeScript in this package.
- Test: `pnpm --filter frai-core test`, or `npx vitest run src/<module>/<file>.test.js` inside the package folder.
- Tests sit next to the code as `*.test.js` and import `describe`, `it` and `expect` from `'vitest'`.
- I/O is injectable: `fs` in scanners, rag and eval, `fetch` in providers, `prompt` in questionnaire.
- Provider tests mock `fetch` and questionnaire tests pass a fake `prompt`, so no test needs the network or a terminal.
- Tests that touch files create temp directories under `os.tmpdir()` and remove them afterwards.
- The scanner test scans the repo's `examples/` folder.
- Single quotes; Node built-ins are imported by bare name (`'fs'`, `'path'`).

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

## packages/frai-agent

- TypeScript LangChain agent. Build: `pnpm --filter frai-agent build`. There is no test script.
- Run it from the repo root with `pnpm agent:frai "<instruction>"`; it needs `OPENAI_API_KEY`.
- `src/agent/executor.ts` builds the agent (`createFraIAgentExecutor`); `src/agent/prompt.ts` holds the system prompt.
- `src/tools/` wraps frai-core as LangChain tools: `scan_repository` (Scanners) and `generate_responsible_ai_docs` (Documents).
- `src/cli/run.ts` is the command-line entry: one turn when given an instruction, a REPL without one.
- Nothing else in the repo imports frai-agent.
- Double quotes; Node built-ins use the `node:` prefix (`node:path`, `node:fs`).
