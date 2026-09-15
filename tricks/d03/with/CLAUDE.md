# frai

FRAI is a Responsible AI toolkit in a pnpm monorepo: a CLI, a core SDK, a spec gate and a LangChain agent.

## Commands

- Use pnpm (`packageManager` is pnpm@8.15.4), not npm or yarn. Install with `pnpm install`.
- Build one package: `pnpm --filter <name> build`. Test one package: `pnpm --filter <name> test`.
- Package names differ from folders for the CLI: `frai` is packages/frai-cli; `frai-core`, `frai-gate` and `frai-agent` match their folders.
- Run one test file from inside the package folder: `npx vitest run <path/to/file>`.
- Run only tests whose name matches: `npx vitest run -t "<part of the test name>"`.
- Tests exist in frai-core and frai-gate only; frai has no test files and frai-agent has no test script.
- Whole repo through turbo: `pnpm build` and `pnpm test`.
- frai-core has no build step (plain ES modules); frai, frai-gate and frai-agent compile `src/` to `dist/` with `tsc`.
- Try the CLIs after building: `node packages/frai-cli/dist/index.js --help` and `node packages/frai-gate/dist/cli.js help`.
- Running `frai` with no subcommand starts an interactive questionnaire that waits for keyboard input.

## Layout

- `packages/frai-cli/src/index.ts`: the whole `frai` CLI (commander), calling into frai-core.
- `packages/frai-core/src/`: one folder per module (config, questionnaire, documents, scanners, rag, eval, providers, finetune), re-exported as namespaces from `src/index.js`.
- `packages/frai-gate/src/`: `cli.ts` (the `frai-gate` command), `gate/` (schema, validator, report rendering), `pipeline/agent.ts` (Claude Agent SDK calls).
- `packages/frai-gate/assets/rai-spec-template.md`: the spec template that frai-gate ships.
- `packages/frai-agent/src/`: LangChain agent (`agent/`), its tools (`tools/`) and command-line entry (`cli/run.ts`).
- Workspace dependencies: `frai` uses `frai-core` and `frai-gate`; `frai-agent` uses `frai-core`; frai-core and frai-gate use no other workspace package.
- Only change the packages the task needs.
- `examples/` has sample AI code and filled-in specs; `docs/` has design notes, and `docs/architecture-target.md` is a plan, not the current layout.
- `.github/workflows/rai-check.yml` is this repo's CI: install, build, scan, unit tests, gate check on `examples/frai-spec-example.md`.
- Most `frai` commands call a `run...` helper (`runGenerateFlow`, `runRagIndexCommand` and others) defined above `main()`, where commander registers them.
- Most frai-core I/O is injectable: `fs` in scanners, rag and eval, `fetch` in providers, `prompt` in questionnaire.
- In frai-gate, `validateSpec` (`gate/validate.ts`) is pure and offline; only `pipeline/agent.ts` makes network calls.
- frai-agent needs `OPENAI_API_KEY` to run, and nothing else in the repo imports it.

## Conventions

- ES modules everywhere (`"type": "module"`); TypeScript uses NodeNext resolution, so relative imports end in `.js`.
- Node built-ins use the `node:` prefix in frai-gate and frai-agent, and bare names (`'fs'`, `'path'`) in frai-core and frai-cli.
- frai-core stays JavaScript: new code there is `.js`, no TypeScript.
- Don't add dependencies. Work with what the package already declares and Node built-ins; leave `package.json` dependency lists and `pnpm-lock.yaml` alone.
- Tests are Vitest files next to the code: `*.test.js` in frai-core, `*.test.ts` in frai-gate.
- Tests that touch files create temp directories under `os.tmpdir()` and remove them afterwards.
- `dist/` is committed build output: never edit it by hand, rebuild the package instead.
- Builds are deterministic: rebuilding a package whose source did not change leaves `git status` clean.
- Style in frai, frai-core and frai-gate: 2-space indent, single quotes, semicolons, no trailing commas.
- frai-agent uses double quotes; otherwise the same style.
- In frai-cli, status messages go through the `log` helper (`log.info`, `log.success`, `log.warn`, `log.error`).
- Never print, log or commit an API key.
- `frai-gate check` without `--smart` is deterministic and offline; `draft` and `--smart` call Claude, so don't run them.
- Generated files (`checklist.md`, `model_card.md`, `risk_file.md`, `frai-index.json`, `frai-eval-report.*`) are gitignored; don't commit them.
