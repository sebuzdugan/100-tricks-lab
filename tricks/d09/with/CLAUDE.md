# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FRAI (Framework of Responsible AI) is a CLI toolkit that generates responsible-AI documentation (checklist, model card, risk file), scans codebases for AI/ML usage, builds a local RAG index from policy docs, runs baseline evaluation metrics, and validates fine-tuning governance plans. It is a pnpm + Turborepo monorepo; the published npm package is `frai` (`packages/frai-cli`).

## Commands

Package manager is pnpm (`packageManager: pnpm@8.15.4`). Run from the repo root:

```bash
pnpm install
pnpm build            # turbo build (only frai-cli actually compiles; frai-core's build is a no-op)
pnpm test             # turbo test
pnpm lint             # turbo lint

pnpm --filter frai run build                      # compile CLI: src/index.ts -> dist/index.js via tsc
node packages/frai-cli/dist/index.js --help       # run the CLI from source
```

Tests use Vitest with a shared root `vitest.config.ts` (globals on, matches `**/*.test.{js,ts}`). Package `test` scripts invoke bare `vitest`, which starts watch mode — use `run` for one-shot:

```bash
pnpm exec vitest run                                          # all tests, once
pnpm exec vitest run packages/frai-core/src/rag/index.test.js # single file
pnpm exec vitest run -t "detects AI libraries"                # single test by name
```

All current tests live in `packages/frai-core`; the CLI has none.

## Architecture

**Dependency direction:** `frai-cli` → `frai-core`. Core must stay free of CLI/UX concerns (no `inquirer`, no `commander`, no console-formatting). Longer-term target layout (separate `frai-rag`, `frai-eval`, plugins, Python bindings) is described in `docs/architecture-target.md`; today those live as modules inside `frai-core`.

**`packages/frai-core`** — plain ESM JavaScript, no build step (`main`/`exports` point directly at `src/index.js`). `src/index.js` re-exports each module as a namespace (`Config`, `Questionnaire`, `Documents`, `Scanners`, `Rag`, `Eval`, `Providers`, `Finetune`), and the CLI consumes them that way. Recurring design patterns across modules:
- **Dependency injection for testability**: functions accept injectable `fs`, `fetch`, `prompt`, `cwd`/`homeDir` options rather than importing side-effectful globals directly. Tests rely on this (e.g. mocked `fetch` in `providers/openai.test.js`, fake `prompt` in questionnaire tests). Preserve this when adding functions.
- **Registries / pluggable strategies**: `providers/index.js` keeps a `Map` of provider factories (`registerProvider`, `createProvider`; only OpenAI is implemented); `scanners` takes a `detectors` array (`createScanner` for custom detectors with an `analyze({ filePath, content, result })` hook); `eval.runEvaluations` accepts metrics as functions or `{ evaluate }` objects; `documents.generateDocuments` accepts `templates` overrides for each artefact.
- Each module keeps defaults in a sibling `constants.js`.

Module notes:
- `config/key-store.js` — OpenAI key lives either in local `./.env` (`OPENAI_API_KEY=...`) or global `~/.config/frai/config` (JSON). `setLocalApiKey` **overwrites the whole `.env` file**.
- `questionnaire` — `runQuestionnaire({ prompt })` asks question groups in sequence and branches on answers (impact questions depend on `core.purpose`; data-protection vs data-source questions depend on `core.dataType`). Returns `{ core, impact, data, performance, monitoring, bias }`, which is the input shape for `documents`.
- `documents` — builds a context (risk level, summaries, description helpers) from answers, then renders markdown via template functions `(context, tips) => string`.
- `rag` — local, dependency-free: chunks text by words and uses a toy 8-dim `simpleEmbed` hash; writes a JSON "vector store" (default `frai-index.json`). Not real embeddings.
- `eval` — baseline metrics (exact match, keyword toxicity, length variance) + JSON/Markdown reporters.
- `finetune` — governance plan schema, template, validation (returns `{ valid, errors: [{ path, message }] }`), readiness scoring. Spec in `docs/finetune-governance.md`.
- `scanners` tests run against the `examples/` fixtures directory — changing those files can break scanner tests.

**`packages/frai-cli`** — a single TypeScript file `src/index.ts` using `commander`, compiled with `tsc` to `dist/index.js` (the `bin`). `dist/index.js` is committed to git, so rebuild after editing `src/index.ts`. The CLI supports both legacy flag style (`frai --scan`, `--setup`, `--list-docs`, ... routed through `handleCompatibilityOptions`) and subcommands (`generate`, `scan`, `setup`, `config`, `docs list|clean|export`, `rag index`, `eval`, `finetune template|validate`, `update`) — keep both paths working when changing commands. Core is untyped JS, so the CLI casts core functions (`as unknown as ...`) at call sites.

Main generate flow (`runGenerateFlow`): optional scan → questionnaire via inquirer → OpenAI tips via `Providers.createProvider` (skipped gracefully if no key) → `extractTips` splits the LLM markdown by "Checklist Tips" / "Model Card Tips" / "Risk File Tips" headings → `Documents.generateDocuments` → writes `checklist.md`, `model_card.md`, `risk_file.md` to cwd.

## Environment

- `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, see `env.example`); default chat model is in `packages/frai-core/src/providers/constants.js`.
- Generated artefacts (`checklist.md`, `model_card.md`, `risk_file.md`, `frai-index.json`, `.frai/`, `frai-eval-report.*`) are gitignored.

## Known stale pieces

- Root `frai.mjs` imports `packages/frai-cli/src/cli.mjs`, which was removed when the CLI moved to `src/index.ts`; it no longer works.
- `.github/workflows/rai-check.yml` still runs `npm ci` and `node ./ai-responsible.mjs` (nonexistent) on Node 16; there is no working lint/test CI.
- `eslint.config.mjs` only targets `.js/.mjs/.cjs`; TypeScript in `frai-cli/src` is not linted.

Roadmap and task status: `TODO.md` and `docs/refactor-plan.md`.
