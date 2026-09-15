# Architecture

This document describes the high-level architecture of frai. Read it to find where things live; use symbol
search for the names in backticks, since file contents change faster than this map.

## Bird's Eye View

FRAI is a Responsible AI toolkit for teams shipping AI features. It generates governance documents from a
questionnaire (checklist, model card, risk file), scans code for AI usage, builds a local RAG index, scores
model outputs, validates fine-tuning governance plans, and checks that a feature spec answers seven
responsible-AI questions (the "FRAI Gate") before implementation starts.

It is a pnpm workspace with four packages. `frai-core` is the library that does the work; `frai-cli` (npm name
`frai`) is the command line on top of it; `frai-gate` is the self-contained spec gate; `frai-agent` is a
LangChain chat front end over frai-core. Dependencies: `frai` -> `frai-core`, `frai-gate`;
`frai-agent` -> `frai-core`. frai-core and frai-gate depend on no other workspace package.

## Code Map

### `packages/frai-core`

Plain JavaScript ES modules, no build step, no runtime dependencies. `src/index.js` re-exports each module
folder as a namespace: `Config`, `Questionnaire`, `Documents`, `Scanners`, `Rag`, `Eval`, `Providers`,
`Finetune`. Every folder has an `index.js`, and its tests sit next to the code as `*.test.js`.

- `config/`: OpenAI key storage in a project `.env` or `~/.config/frai/config` (`key-store.js`, `paths.js`).
- `questionnaire/`: the question definitions (`questions.js`) and `runQuestionnaire({ prompt })`.
- `documents/`: `generateDocuments`, the Markdown templates (`templates.js`), `calculateRiskLevel`.
- `scanners/`: `scanCodebase` walks a folder and runs detectors (`detectors.js`); `createScanner`.
- `rag/`: `indexDocuments`, `findDocuments`, `chunkText`, and `simpleEmbed`, a deterministic local embedding.
- `eval/`: `loadDataset`, `runEvaluations`, `generateReport`, `writeReport`; metrics in `metrics.js`, JSON and
  Markdown output in `reporters.js`.
- `providers/`: a provider registry (`createProvider`, `registerProvider`) and the OpenAI chat client.
- `finetune/`: governance plan template, validation and readiness (`validateGovernancePlan`,
  `calculateReadiness`); `schema.js` describes the plan sections.

Architecture Invariant: module folders do not import each other; each depends only on Node built-ins and its
own files. Anything that touches the outside world is passed in where the tests need it: `prompt` for the
questionnaire, `fetch` for providers, `fs` for scanners, rag and eval. frai-core never prompts in a terminal.

### `packages/frai-cli` (npm name `frai`)

TypeScript, one file: `src/index.ts`. `main()` registers the commander commands (`generate`, `scan`, `setup`,
`config`, `docs`, `rag index`, `eval`, `finetune`, `gate`, `update`); most delegate to a `run...` function
above it (`runGenerateFlow`, `runRagIndexCommand`, ...), which calls frai-core. The terminal
side lives here: `inquirer` prompts, the `log` helper, writing generated files to the current folder. The
`gate` command delegates to frai-gate. Built with `tsc` to `dist/index.js`, the `frai` bin.

### `packages/frai-gate`

TypeScript. A spec is Markdown; the gate is its "Responsible AI Gate" (or "FRAI Gate") section with seven
subsections.

- `src/gate/schema.ts`: `GATE_CHECKS`, `Finding`, `GateResult`, `verdictFrom` (PASS, WARN or BLOCK).
- `src/gate/validate.ts`: `validateSpec` and `extractGateSection`, the deterministic checker.
- `src/gate/report.ts`: `renderText` and `renderJson`.
- `src/pipeline/agent.ts`: `draftGateSection` and `smartReview`, Claude Agent SDK sessions with read-only
  tools.
- `src/cli.ts`: the `frai-gate` command (`init`, `check`, `draft`), built to the `dist/cli.js` bin;
  `src/index.ts`: the library exports.
- `assets/rai-spec-template.md`: the spec template that `init` copies.

Architecture Invariant: `gate/` is pure (strings in, results out, no file or network access), so `check`
without `--smart` is deterministic and offline. Only `pipeline/agent.ts` talks to a model, and its sessions can
read the repository but not change it. frai-gate does not use frai-core.

### `packages/frai-agent`

TypeScript LangChain agent. `src/agent/executor.ts` (`createFraIAgentExecutor`) wires an OpenAI chat model to
two tools in `src/tools/`: `scan_repository` (frai-core `Scanners`) and `generate_responsible_ai_docs`
(frai-core `Documents`). `src/cli/run.ts` is the entry point (`pnpm agent:frai`). Nothing depends on this
package.

### Outside `packages/`

- `examples/`: sample AI code the scanner flags, and complete specs (`frai-spec-example.md`,
  `support-triage-demo/`).
- `docs/`: design notes and plans. `architecture-target.md` describes a planned layout (with packages such as
  `frai-rag` and `frai-eval` that do not exist), not the current code.
- `.github/workflows/rai-check.yml`: CI. `frai.mjs` at the root is a leftover of the old single-file CLI.

## Cross-Cutting Concerns

**Build.** `pnpm --filter <name> build`, or `pnpm build` for all packages through turbo (`^build` order).
frai, frai-gate and frai-agent compile `src/` to `dist/` with `tsc`, and `dist/` is committed, so it must be
rebuilt after a source change. frai-core ships `src/` directly.

**Modules.** ES modules everywhere; TypeScript uses NodeNext resolution, so relative imports end in `.js`.

**Tests.** Vitest, configured once in the root `vitest.config.ts`. Tests exist in frai-core and frai-gate:
`pnpm --filter <name> test`, or `npx vitest run <file>` inside the package. They use temp folders, a mocked
`fetch` and fake prompts, so no test needs a key, a network or a terminal. The scanner test reads
`examples/` and the gate test reads `assets/rai-spec-template.md`.

**Credentials.** OpenAI keys are needed only for AI tips in the CLI and for frai-agent; Claude credentials only
for `frai-gate draft` and `check --smart`. Generated documents, indexes and reports are gitignored.
