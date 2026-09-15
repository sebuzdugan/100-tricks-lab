# CLAUDE.md

FRAI (Framework of Responsible Artificial Intelligence) is a pnpm + Turborepo monorepo of Node tools for
responsible-AI work: documentation generation, code scanning for AI indicators, RAG indexing, evaluation reports,
fine-tuning governance, and a Responsible AI Gate for specs.

## Commands

Use pnpm (pinned to 8.15.4 in `package.json`). CI runs Node 20.

```bash
pnpm install                          # install workspace dependencies
pnpm build                            # turbo build (dependencies build first)
pnpm test                             # turbo test across packages
pnpm lint                             # turbo lint (eslint . in each package)

pnpm --filter <pkg> build             # one package: frai, frai-core, frai-gate, frai-agent
pnpm --filter <pkg> test              # frai, frai-core, frai-gate (frai-agent has no test script)
pnpm --filter <pkg> exec vitest run   # single non-watch pass, as the GitHub workflow does
pnpm --filter <pkg> exec vitest run src/path/to/file.test.ts   # one test file

pnpm cli                              # build the frai CLI and run dist/index.js
pnpm agent:frai                       # run the frai-agent CLI with tsx
node packages/frai-cli/dist/index.js <command>    # run the built frai CLI directly
node packages/frai-gate/dist/cli.js <command>     # run the built frai-gate CLI directly
```

Filter by the package `name`, not the folder: the `packages/frai-cli` package is called `frai`.

The `test` script in frai-core and frai-cli is plain `vitest`, which watches unless `CI` is set; frai-gate's is
`vitest run`. The root `frai.mjs` imports `packages/frai-cli/src/cli.mjs`, which does not exist; use the built
`dist/index.js` instead.

## Layout

```
packages/
  frai-cli/     npm package "frai": the CLI. One commander program in src/index.ts, compiled to dist/
  frai-core/    shared SDK in plain JavaScript ES modules, no build step (main is src/index.js)
  frai-gate/    FRAI Gate: spec template, deterministic validator and Claude Agent SDK pipeline, own CLI
  frai-agent/   LangChain agent that exposes frai-core scanning and docs as tools
examples/       sample AI code, an example spec, and support-triage-demo (a small app with a filled-in spec)
docs/           design notes and plans (architecture, eval harness, gate design, refactor plan)
.github/workflows/rai-check.yml   CI: install, build, scan, unit tests, gate check on the example spec
.claude/commands/rai-spec.md      project slash command for writing or reviewing a spec with the gate
```

Package dependencies: `frai` depends on `frai-core` and `frai-gate`; `frai-agent` depends on `frai-core`;
`frai-gate` depends only on `@anthropic-ai/claude-agent-sdk`.

### frai-core

`src/index.js` re-exports each module as a namespace: `Config`, `Questionnaire`, `Documents`, `Scanners`, `Rag`,
`Eval`, `Providers`, `Finetune`. Each module is a folder with an `index.js` entry, and usually `constants.js` plus
helper files. Consumers import namespaces: `import { Scanners, Documents } from 'frai-core'`.

- `config/`: OpenAI key storage, local `.env` or global `~/.config/frai/config`
- `providers/`: provider registry (`registerProvider`, `createProvider`), OpenAI implementation
- `questionnaire/`, `documents/`: question flow and checklist / model card / risk file templates
- `scanners/`: detectors for AI libraries, functions and files
- `rag/`, `eval/`, `finetune/`: indexing, metrics and reporters, governance schema and validation

### frai-cli

A single `src/index.ts`. Subcommands: default interactive flow, `generate`, `scan`, `setup`, `config`,
`docs list|clean|export`, `rag index`, `eval`, `finetune template|validate`, `gate`, `update`. Command handlers
call into frai-core; most output goes through the local `log` helper (`info`, `success`, `warn`, `error`).
`frai gate` runs frai-gate's built CLI, so frai-gate must be built for it to work.

### frai-gate

- `src/cli.ts`: the `frai-gate init | check | draft` commands
- `src/gate/`: schema (checks, severities, verdicts), validator, report rendering
- `src/pipeline/agent.ts`: Claude Agent SDK calls for `draft` and `check --smart`
- `assets/rai-spec-template.md`: the spec template `init` writes
- Exit codes: 0 PASS/WARN, 1 BLOCK, 2 usage or error

### frai-agent

`src/agent/` (executor, prompt), `src/tools/` (LangChain tools wrapping frai-core), `src/config/env.ts` (API key
resolution), `src/cli/run.ts` (entry for `pnpm agent:frai`).

## Conventions

- ES modules everywhere (`"type": "module"`). TypeScript uses `NodeNext` resolution, so relative imports in `.ts`
  files end in `.js` (`import { validateSpec } from './gate/validate.js'`).
- TypeScript packages (frai, frai-gate, frai-agent) compile with `tsc` from `src/` to `dist/`. `dist/` is committed,
  so rebuild the package after changing its `src/`.
- Tests are Vitest, colocated with the code as `*.test.js` (frai-core) or `*.test.ts` (frai-gate), using explicit
  `import { describe, expect, it } from 'vitest'`. Tests that need real files create temp dirs with
  `fs.mkdtempSync(path.join(os.tmpdir(), 'frai-...'))` and remove them afterwards.
- frai-core functions take options objects with defaults (for example `fs`, `embed`, `clock` in `Rag.indexDocuments`), so
  dependencies can be swapped in tests.
- ESLint uses the root flat config (`eslint.config.mjs`), which only targets `.js`, `.mjs` and `.cjs` files;
  `console` is allowed.
- Match the style of the file you are editing: frai-core, frai-cli and frai-gate use single quotes and semicolons,
  frai-agent uses double quotes.
- Generated artefacts (`checklist.md`, `model_card.md`, `risk_file.md`, `frai-index.json`, `frai-eval-report.*`,
  `.frai/`) are gitignored.

## Environment

- `OPENAI_API_KEY` (and optional `OPENAI_MODEL`, see `env.example`) for AI tips, evaluations and frai-agent.
- frai-gate's `draft` and `check --smart` need Claude Code authentication or `ANTHROPIC_API_KEY`;
  `FRAI_GATE_MODEL` overrides the model. The plain `check` and `init` commands need no key.
