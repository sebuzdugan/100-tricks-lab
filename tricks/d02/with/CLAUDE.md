# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FRAI (Framework of Responsible AI) is a pnpm + Turborepo monorepo (pnpm 8.15.4, Node 20 in CI) that ships four npm packages:

| Dir | npm name | Language | Build output |
|---|---|---|---|
| `packages/frai-core` | `frai-core` | plain JS ESM | none, consumed straight from `src/` |
| `packages/frai-cli` | **`frai`** (not `frai-cli`) | TypeScript | `dist/index.js` (bin `frai`) |
| `packages/frai-agent` | `frai-agent` | TypeScript | `dist/` + `dist/types` |
| `packages/frai-gate` | `frai-gate` | TypeScript | `dist/` + `dist/types` (bin `frai-gate`) |

`dist/` directories are **committed**. CI and the `/rai-spec` command run `dist/*.js` directly, so rebuild after changing TS sources.

## Commands

```bash
pnpm install
pnpm build                     # turbo build (all packages)
pnpm test                      # turbo test
pnpm lint                      # turbo lint

pnpm --filter frai run build   # build only the CLI (filter by npm name)
node packages/frai-cli/dist/index.js --help
node packages/frai-cli/dist/index.js scan --ci

node packages/frai-gate/dist/cli.js check examples/frai-spec-example.md
pnpm agent:frai "Scan the repository and summarize AI risks."   # frai-agent via tsx, needs OPENAI_API_KEY
```

Tests use Vitest (root `vitest.config.ts`: globals on, matches `**/*.test.{js,ts}`). The `test` scripts in `frai-core` and `frai-cli` run bare `vitest`, which starts watch mode. Use `vitest run` for a single pass:

```bash
pnpm --filter frai-core exec vitest run
pnpm --filter frai-gate exec vitest run src/gate/validate.test.ts   # single file
pnpm --filter frai-core exec vitest run -t "test name"              # single test
```

CI (`.github/workflows/rai-check.yml`) runs: install → build → `frai scan --ci` → tests → gate check on `examples/frai-spec-example.md`. frai-core test failures only produce a warning ("known, tracked"). frai-gate tests must pass.

ESLint (`eslint.config.mjs`) only configures `*.js/*.mjs/*.cjs`, so TypeScript sources are not linted in practice.

## Architecture

**Dependency direction:** `frai` (CLI) → `frai-core` + `frai-gate`; `frai-agent` → `frai-core`. `frai-core` must not import CLI code. Workspace deps use semver ranges (`^0.0.1`) rather than `workspace:*`, and pnpm links them locally.

**frai-core** (`src/index.js`) exposes namespaces `Config`, `Questionnaire`, `Documents`, `Scanners`, `Rag`, `Eval`, `Providers`, `Finetune`, each a folder under `src/` with `index.js` + `constants.js`. The shared convention is dependency injection through option objects, which keeps the code testable without mocks:
- I/O modules take an `fs` option (`scanCodebase({ root, fs, detectors })`, `Rag.findDocuments(..., { fs })`, `Eval.loadDataset({ fs })`).
- `Questionnaire.runQuestionnaire({ prompt })` takes the prompt function, so the CLI passes `inquirer.prompt`.
- Scanners are a list of detector objects (`createLibraryDetector`, `createFunctionDetector` in `scanners/detectors.js`).
- Providers use a registry/factory (`registerProvider(id, factory)`, `createProvider({ provider })`). Only OpenAI exists and it uses `fetch`.
- `Documents.generateDocuments({ answers, tips, templates })` produces `checklist.md` / `model_card.md` / `risk_file.md` content. `templates` overrides the defaults.
- Config stores the OpenAI key in a project `.env` or globally in `~/.config/frai/config` (`OPENAI_API_KEY`, `OPENAI_MODEL`, see `env.example`).

**frai-cli** is a single Commander program in `src/index.ts`. Subcommands are thin wrappers over frai-core. The root command keeps legacy flags (`--scan`, `--ci`, `--setup`, …) for backward compatibility with v1.1.x through `handleCompatibilityOptions`. `frai gate ...` doesn't import frai-gate. It resolves `frai-gate/package.json` and **spawns** `frai-gate/dist/cli.js` as a child process, passing args and exit code through.

**frai-gate** (Responsible AI Gate for spec markdown; design in `docs/rai-gate-design.md`) has two layers:
- Deterministic (`src/gate/`, no API key): `schema.ts` defines the seven `GATE_CHECKS` (matched by subsection heading regex under a `## Responsible AI Gate` / `FRAI Gate` heading), `validate.ts` parses and flags missing, placeholder (`TBD`), or non-numeric answers and high-risk tiers without sign-off, and `report.ts` renders text/JSON. Verdicts are PASS/WARN/BLOCK. CLI exit codes: 0 = PASS/WARN, 1 = BLOCK, 2 = usage error.
- Smart (`src/pipeline/agent.ts`): Claude Agent SDK `query()` restricted to read-only `Read/Glob/Grep` tools with a secrets guard. It powers `frai-gate draft` and `check --smart`. Model comes from `FRAI_GATE_MODEL` (default `claude-opus-5`). Auth is Claude Code or `ANTHROPIC_API_KEY`.
- `assets/rai-spec-template.md` is the template that `frai-gate init` writes. The canonical skill lives in the external `sebuzdugan/frai-skills` repo. Keep the seven checks in sync with `schema.ts`, the template, and `.claude/commands/rai-spec.md`.

**frai-agent** is a LangChain + OpenAI agent (`src/agent/executor.ts`) with two tools that wrap frai-core: `scan_repository` and `generate_responsible_ai_docs`. It is deliberately separate from frai-gate's Claude Agent SDK pipeline.

## Gotchas

- Root `frai.mjs` imports `packages/frai-cli/src/cli.mjs`, which no longer exists. It is a leftover from the pre-monorepo CLI. Use `packages/frai-cli/dist/index.js`.
- `examples/` holds scanner fixtures and demo specs (`support-triage-demo/` is the gate demo app). Scanning the repo root picks them up as AI files.
- `docs/` holds design and roadmap notes (`architecture-target.md`, `refactor-plan.md`, `TODO.md` at root). Parts describe planned packages (`frai-rag`, `frai-eval`, VS Code extension) that don't exist yet. RAG and eval live inside frai-core.
- Publishing: bump versions, build, then publish `frai-core` **before** `frai` (see README "Publishing").
