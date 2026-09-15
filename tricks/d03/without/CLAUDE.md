# frai

FRAI is a Responsible AI toolkit in a pnpm monorepo: a CLI, a core SDK, a spec gate and a LangChain agent.

This file is the working guide for this repository. It covers the commands, the layout of every package in
detail, the coding conventions, and a glossary of the terms that appear in the code. Everything here describes
the code as it is today.

## Commands

- Use pnpm (`packageManager` is pnpm@8.15.4), not npm or yarn. Install with `pnpm install`.

### Toolchain

- The workspace is defined by `pnpm-workspace.yaml`, which lists `packages/*`. The root `package.json` also
  declares `"workspaces": ["packages/*"]`.
- The root package is `frai-monorepo` (private, version 0.0.2). It holds tooling; the code lives in `packages/`.
- Root devDependencies: `@eslint/js`, `@types/node`, `eslint`, `eslint-config-prettier`, `eslint-plugin-import`,
  `prettier`, `turbo`, `typescript` and `vitest`.
- CI runs on Node 20. The `engines` fields ask for Node >= 16 in `frai` and Node >= 18 in `frai-gate` and
  `frai-agent`.
- Workspace packages are linked, not downloaded: `packages/frai-cli/node_modules/frai-core` is a symlink to
  `packages/frai-core`, even though `frai`'s `package.json` lists it with a version range (`^0.0.1`).
- The lockfile is `pnpm-lock.yaml` at the root. CI installs with `pnpm install --frozen-lockfile`.

- Build one package: `pnpm --filter <name> build`. Test one package: `pnpm --filter <name> test`.

### Package scripts

Every package has its own scripts in its `package.json`:

- `frai` (packages/frai-cli):
  - `build`: `tsc --project tsconfig.json`
  - `start`: `pnpm run build && node dist/index.js`
  - `dev`: `tsc --project tsconfig.json --watch`
  - `lint`: `eslint .`
  - `test`: `vitest`
- `frai-core` (packages/frai-core):
  - `build`: `echo "No build step needed - ES modules"`
  - `lint`: `eslint .`
  - `test`: `vitest`
- `frai-gate` (packages/frai-gate):
  - `build`: `tsc --project tsconfig.json`
  - `dev`: `tsx --watch src/cli.ts`
  - `start`: `tsx src/cli.ts`
  - `lint`: `eslint .`
  - `test`: `vitest run`
- `frai-agent` (packages/frai-agent):
  - `build`: `tsc --project tsconfig.json`
  - `dev`: `tsx --watch src/cli/run.ts`
  - `start`: `tsx src/cli/run.ts`
  - `lint`: `eslint .`

- Package names differ from folders for the CLI: `frai` is packages/frai-cli; `frai-core`, `frai-gate` and `frai-agent` match their folders.

### Root scripts

- `pnpm dev`: `pnpm --filter frai run start`, which builds the CLI and then runs `node dist/index.js`.
- `pnpm cli`: `pnpm --filter frai run build && pnpm --filter frai exec node dist/index.js`.
- `pnpm agent:frai`: `pnpm --filter frai-agent exec pnpm start`, which runs the agent from source with `tsx`.
- `pnpm build`, `pnpm test` and `pnpm lint` run `turbo build`, `turbo test` and `turbo lint`.

- Run one test file from inside the package folder: `npx vitest run <path/to/file>`.

### Vitest

- The root `vitest.config.ts` sets `globals: true`, `environment: 'node'`, includes `**/*.test.{js,ts}`,
  excludes `node_modules`, `dist` and `.pnpm`, and sets `passWithNoTests: true`.
- Test files still import `describe`, `it` and `expect` (and `vi` or hooks when needed) from `'vitest'`
  explicitly. Keep doing that in new tests.
- `vitest run` runs the suite once and exits. Plain `vitest` watches for changes in an interactive terminal
  and runs once when `CI` is set.

- Run only tests whose name matches: `npx vitest run -t "<part of the test name>"`.

- Tests exist in frai-core and frai-gate only; frai has no test files and frai-agent has no test script.

### Where the tests are

- frai-core has one `*.test.js` file in each of its eight module folders (config, documents, eval, finetune,
  providers, questionnaire, rag, scanners).
- frai-gate has `src/gate/validate.test.ts`.
- Some tests read real files from the repo: the scanner test scans `examples/`, and the gate validator test reads
  `packages/frai-gate/assets/rai-spec-template.md`. Moving those files breaks the tests.

- Whole repo through turbo: `pnpm build` and `pnpm test`.

### Turbo

- `turbo.json` uses the turbo 1.x `pipeline` format.
- `build` depends on `^build` (a package's workspace dependencies build first) and caches `dist/**`.
- `test` and `lint` are cached and declare no outputs.
- Turbo's cache means a repeated `pnpm build` with no source changes replays the previous logs instead of
  rebuilding.

- frai-core has no build step (plain ES modules); frai, frai-gate and frai-agent compile `src/` to `dist/` with `tsc`.

### TypeScript

- The root `tsconfig.json` sets `target` ES2020, `module` and `moduleResolution` NodeNext, `allowJs`,
  `checkJs: false`, `esModuleInterop`, `resolveJsonModule`, `skipLibCheck` and `baseUrl: "."`.
- Each TypeScript package extends it with `outDir: dist`, `rootDir: src`, `include: ["src/**/*.ts"]` and
  `noEmitOnError: true`, so a type error means nothing is written to `dist/`.
- `frai-gate` and `frai-agent` also emit declaration files to `dist/types`. `frai` does not
  (`declaration: false`).
- `frai-gate`'s tsconfig excludes `src/**/*.test.ts`, so its tests never land in `dist/`; Vitest runs them from
  source.
- To type-check a package, run its build script, or `npx tsc --project tsconfig.json` inside the package folder.

- Try the CLIs after building: `node packages/frai-cli/dist/index.js --help` and `node packages/frai-gate/dist/cli.js help`.

### Entry points and other commands

- The `frai` bin points to `packages/frai-cli/dist/index.js`. The `frai-gate` bin points to
  `packages/frai-gate/dist/cli.js`.
- Commander subcommands print their options with `--help`, for example
  `node packages/frai-cli/dist/index.js eval --help`.
- `frai-agent` runs from source: `pnpm agent:frai "<instruction>"`. It needs an OpenAI API key.
- `frai.mjs` at the repo root imports `packages/frai-cli/src/cli.mjs`, which does not exist. It is a leftover
  from the old single-file CLI and is not used by any script.
- Lint: `pnpm --filter <name> lint` runs `eslint .` with the root `eslint.config.mjs` (flat config:
  `@eslint/js` recommended rules, module globals for `.js`, `.mjs` and `.cjs` files, `no-console` off).
- ESLint already reports errors on the current code in some packages, so a lint failure on its own does not
  mean a change broke something.
- CLI commands write their output (docs, indexes, reports, specs) into the current folder. When trying them
  out, run them from a temporary folder so the repo stays clean.

- Running `frai` with no subcommand starts an interactive questionnaire that waits for keyboard input.

## Layout

The top level of the repository:

- `packages/`: the four workspace packages, described one by one below.
- `examples/`: sample AI code and specs used by the scanner, the tests and CI.
- `docs/`: design notes and plans.
- `assets/`: `frai-gate-demo.gif` and `frai_cc_screenshot.png`, used by the README.
- `.claude/commands/rai-spec.md`: the `/rai-spec` project command for writing or reviewing a spec with the
  FRAI Gate.
- `.github/workflows/rai-check.yml`: CI.
- `env.example`: placeholder values for `OPENAI_API_KEY` and `OPENAI_MODEL`.
- `README.md` (user guide for all packages), `TODO.md` (roadmap), `LICENSE` (MIT).
- Root config: `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `turbo.json`, `tsconfig.json`,
  `vitest.config.ts`, `eslint.config.mjs`, `.gitignore`.

The packages:

- `packages/frai-cli/src/index.ts`: the whole `frai` CLI (commander), calling into frai-core.
- `packages/frai-core/src/`: one folder per module (config, questionnaire, documents, scanners, rag, eval, providers, finetune), re-exported as namespaces from `src/index.js`.
- `packages/frai-gate/src/`: `cli.ts` (the `frai-gate` command), `gate/` (schema, validator, report rendering), `pipeline/agent.ts` (Claude Agent SDK calls).
- `packages/frai-gate/assets/rai-spec-template.md`: the spec template that frai-gate ships.
- `packages/frai-agent/src/`: LangChain agent (`agent/`), its tools (`tools/`) and command-line entry (`cli/run.ts`).
- Workspace dependencies: `frai` uses `frai-core` and `frai-gate`; `frai-agent` uses `frai-core`; frai-core and frai-gate use no other workspace package.

### Third-party dependencies by package

- `frai`: `commander` ^11.1.0, `dotenv` ^16.5.0, `inquirer` ^8.2.6, `node-fetch` ^3.3.2. Dev: `eslint`, `vitest`.
- `frai-core`: no runtime dependencies at all. Dev: `eslint`, `vitest`.
- `frai-gate`: `@anthropic-ai/claude-agent-sdk` ^0.3.0. Dev: `tsx`, `eslint`, `vitest`.
- `frai-agent`: `langchain` ^0.1.34, `@langchain/openai` ^0.0.12, `zod` ^3.22.4. Dev: `tsx`, `eslint`, `vitest`.

- Only change the packages the task needs.

### Package boundaries

- Each package folder is self-contained: its own `package.json`, `README.md` and `src/`, plus `tsconfig.json`
  and `dist/` for the TypeScript packages.
- A package's public surface is what its `package.json` points to:
  - `frai-core`: `main` and `exports` are `src/index.js`.
  - `frai-gate`: `exports` has `.` (`dist/index.js`, built from `src/index.ts`) and `./package.json`.
  - `frai-agent`: `main` and `exports` are `dist/index.js`.
  - `frai`: the `frai` bin, `dist/index.js`.
- Packages that use a TypeScript package load its `dist/`, so they only see its changes after it is rebuilt.
- Nothing in the repo depends on `frai-agent`.

- `examples/` has sample AI code and filled-in specs; `docs/` has design notes, and `docs/architecture-target.md` is a plan, not the current layout.

### examples/

- `examples/ai_classifier.js` and `examples/ai_model.py`: small sample AI programs (TensorFlow.js,
  scikit-learn) that the scanner should flag.
- `examples/frai-spec-example.md`: a complete "Policy Chatbot" spec with a `## FRAI Gate` section. It passes the
  deterministic gate check.
- `examples/support-triage-demo/`: the project from the frai-gate demo video. An Express service where an LLM
  triages support tickets (`src/index.js`, `src/triage.js`), with a completed `FRAI-SPEC.md` and the agent's
  reference draft `rai-gate-draft.reference.md`.
- The demo has its own `package.json` (`openai`, `express`), but it is not a workspace package and its
  dependencies are not installed.

### docs/

- `docs/analysis.md`: the day 1 analysis of the old single-package CLI (`frai.mjs`). Historical.
- `docs/architecture-target.md`: the target architecture. It names packages such as `frai-rag`, `frai-eval`
  and `frai-plugins` that do not exist; RAG and evaluation live inside frai-core today.
- `docs/refactor-plan.md`: the phase 0 refactor checklist.
- `docs/ai_feature_backlog.md`, `docs/eval_harness_design.md`, `docs/finetune-governance.md`,
  `docs/langchain_agent.md` and `docs/rai-gate-design.md`: design notes for the backlog, the evaluation
  harness, fine-tuning governance, the LangChain agent and the gate.

- `.github/workflows/rai-check.yml` is this repo's CI: install, build, scan, unit tests, gate check on `examples/frai-spec-example.md`.

### CI details

- Triggers: push and pull request on `main` and `master`. Permissions: `contents: read`.
- Runs on `ubuntu-latest` with `pnpm/action-setup` (pnpm 8.15.4) and `actions/setup-node` (Node 20, pnpm cache).
- Steps: `pnpm install --frozen-lockfile`, `pnpm build`, the frai scanner on the repository, Vitest for
  frai-core and frai-gate, then `node packages/frai-gate/dist/cli.js check examples/frai-spec-example.md`.

### frai (packages/frai-cli) in detail

- Most `frai` commands call a `run...` helper (`runGenerateFlow`, `runRagIndexCommand` and others) defined above `main()`, where commander registers them.
- Version 1.1.4. Published files: `README.md`, `LICENSE`, `dist/` and the generated doc names.
- `src/index.ts` is one file of about 770 lines: types and helper functions first, then `main()`, which builds
  the commander `program`, then `void main()` at the bottom.
- It imports the frai-core namespaces `Config`, `Documents`, `Eval`, `Finetune`, `Providers`, `Questionnaire`,
  `Rag` and `Scanners`, plus `commander` and `inquirer`.
- It reads its own version from `../package.json` through `createRequire(import.meta.url)`.
- Commands registered in `main()`:
  - `frai` with no command runs the interactive documentation workflow.
  - `frai generate`: the same documentation workflow as an explicit command.
  - `frai scan [--json]`: runs `Scanners.scanCodebase` on the current folder and lists AI-related files, or
    prints the raw result as JSON.
  - `frai setup [--key <apiKey>] [--global]`: stores an OpenAI API key locally or globally.
  - `frai config`: shows whether a local or global key is configured.
  - `frai docs list`, `frai docs clean`, `frai docs export`: list, delete or PDF-export the generated docs.
  - `frai rag index [--input <path>] [--output <path>] [--chunk-size <words>] [--extensions <list>]`.
  - `frai eval --outputs <file> [--references <file>] [--report <path>] [--format json|markdown]`.
  - `frai finetune template [--output <path>]` and `frai finetune validate <plan> [--readiness]`.
  - `frai gate ...`: the Responsible AI Gate commands, provided by the frai-gate package.
  - `frai update`: compares the installed version with `npm view frai version`.
- The documentation workflow (`runGenerateFlow`): stores a key if one was passed, resolves the configured key
  (local `.env` first, then global), optionally scans, runs `Questionnaire.runQuestionnaire` with
  `inquirer.prompt` as the prompt function, asks OpenAI for tips when a key exists, calls
  `Documents.generateDocuments`, and writes `checklist.md`, `model_card.md` and `risk_file.md`.
- AI tips (`generateAITips`): `Providers.createProvider({ apiKey, fetch })`, one chat completion with
  temperature 0.3 and 800 max tokens. `extractTips` splits the reply at lines reading "Checklist Tips",
  "Model Card Tips" and "Risk File Tips". Any failure is logged as a warning and the docs are written without
  tips.
- `fetch`: the global `fetch` when present, otherwise a dynamic import of `node-fetch`.
- PDF export shells out to `npx markdown-pdf` with the existing doc files.
- Logging: `formatLog` produces `[<ISO timestamp>] LEVEL message {json meta}`. `info` and `success` go to
  stdout, `warn` and `error` to stderr.
- `frai docs list` and `frai docs clean` only look at the three generated doc files in the current folder;
  `clean` deletes the ones it finds.
- `showConfigStatus` reports only whether a key is configured and where, never the key itself.

### frai-core (packages/frai-core) in detail

- Most frai-core I/O is injectable: `fs` in scanners, rag and eval, `fetch` in providers, `prompt` in questionnaire.
- Version 0.0.1. `main` and `exports` point at `src/index.js`; the published files are `README.md`, `LICENSE`
  and `src/`. There is no `dist/`.
- `src/index.js` re-exports eight namespaces: `Config`, `Questionnaire`, `Documents`, `Scanners`, `Rag`,
  `Eval`, `Providers`, `Finetune`. Callers write `import { Scanners } from 'frai-core'` and then
  `Scanners.scanCodebase(...)`.
- Each module folder has an `index.js`; config, providers, questionnaire, rag and scanners also have a
  `constants.js`.

#### config

- `constants.js`: `LOCAL_ENV_FILENAME` (`.env`), `GLOBAL_CONFIG_DIR` (`.config/frai`), `GLOBAL_CONFIG_FILE`
  (`config`).
- `paths.js`: `resolveLocalEnvPath(cwd)`, `resolveGlobalConfigDir(homeDir)`, `resolveGlobalConfigPath(homeDir)`.
- `key-store.js`: the local key functions `hasLocalApiKey`, `getLocalApiKey` and `setLocalApiKey`, which work
  on the project's `.env`.
- The global key functions `hasGlobalApiKey`, `getGlobalApiKey` and `setGlobalApiKey` work on the JSON file
  at `~/.config/frai/config`.
- `index.js` re-exports everything from `constants.js`, `paths.js` and `key-store.js`.
- Every function takes an optional `cwd` or `homeDir`, which is how the tests point them at temporary
  folders.

#### questionnaire

- `runQuestionnaire({ prompt })`: `prompt` is any async function that takes inquirer-style question objects and
  returns an answers object. It throws a `TypeError` when `prompt` is not a function.
- Order: core (`purpose`, `modelType`, `dataType`), then impact (a question set chosen by purpose, with a
  default set), then data (`dataProtection` when the data type is sensitive or personal, otherwise
  `dataSource`), then performance (`primaryMetric`), monitoring (`monitoring`) and bias
  (`biasConsiderations`).
- It resolves to `{ core, impact, data, performance, monitoring, bias }`.
- `QUESTION_COUNT` is 8, and question messages are numbered `n/8`. `CORE_PURPOSE` values are `user-facing`,
  `internal`, `automation`, `content` and `other`.
- The tests pass a fake `prompt` that returns queued answers, so no terminal is involved.

#### documents

- `generateDocuments({ answers, tips, templates })` returns `{ checklist, modelCard, riskFile, context }` and
  throws when `answers` is missing.
- Templates are functions `(context, tips) => string`: `defaultChecklistTemplate`, `defaultModelCardTemplate`,
  `defaultRiskFileTemplate`. Pass `templates.checklist`, `templates.modelCard` or `templates.riskFile` to
  override one.
- `context` holds the answers, the risk level, per-document summaries and the label helpers.
- `calculateRiskLevel(answers)` returns `{ level, score, factors }`. Points: sensitive data 3 or personal data 2;
  critical, high or medium impact 4, 3 or 2; no monitoring 2 or basic logging 1; bias not considered 2 or only
  planned 1; user-facing 1. Level: Critical at 7 or more, High at 5, Medium at 3, otherwise Low.
- `helpers.js` maps answer values to readable labels (`getPurposeDescription` and friends); unknown values pass
  through unchanged.
- `buildContextForAITips(answers)` builds the plain-text feature context sent with the AI tips request.
- Empty tips render as "No specific tips available for this section.", and every document ends with the
  footer "Generated by FRAI - Responsible AI in Minutes".

#### scanners

- `scanCodebase(options)` walks `root` (default: the current folder) recursively.
- It skips `DEFAULT_EXCLUDED_DIRS` (`node_modules`, `.git`, `.venv`, `__pycache__`, `.idea`, `.vscode`, `dist`,
  `build`) at any depth, so installed dependencies, build output and editor folders never show up in a
  scan result.
- Result: `{ aiFiles, totalFiles, aiLibraryMatches, aiFunctionMatches }`. Both match maps are keyed by file
  path, with an array of matched names per file.
- A detector is an object `{ id, analyze({ content, filePath, result, config }) }` that calls
  `result.markAiFile(filePath)` when it finds something.
- Default detectors: `libraries` (AI libraries a file uses) and `functions` (AI-style calls such as `fit(`,
  `predict(` or `generate(`).
- Read errors and detector errors are logged with `console.error` and the scan continues.
- Options also accept `excludedDirs`, `extensions`, `detectors` and `fs`. `createScanner(config)` returns a
  scan function with those options preset.

#### rag

- `indexDocuments({ input, output, chunkSize, extensions, fs, embed, clock })` finds documents, splits them into
  chunks, embeds each chunk and writes the JSON index to `output` (default `frai-index.json` in the current
  folder). It returns the payload `{ metadata, entries }` and throws when no documents are found.
- Defaults: extensions `.md`, `.markdown`, `.txt`, `.json`, `.yaml`, `.yml`; chunk size 800 words.
- `findDocuments(inputs, { extensions, fs })` recurses into folders and returns sorted, de-duplicated paths.
- `chunkText(text, { chunkSize })` splits on whitespace into chunks of that many words.
- `simpleEmbed(text)` is a deterministic 8-number vector built from character codes and normalised. There is
  no model and no network call.
- Entry ids are the SHA-1 of `<source>:<chunkIndex>`.

#### eval

- `loadDataset({ outputsPath, referencesPath, fs })` reads JSON files and returns the parsed data together with
  absolute paths. References are optional.
- `runEvaluations({ outputs, references, metrics })` runs every metric (a function, or an object with an
  `evaluate` method) and returns the list of results.
- `generateReport({ evaluations, outputsPath, referencesPath, generatedAt })` returns `{ metadata, metrics }`.
- `writeReport({ report, format, reportPath, fs })` writes JSON or Markdown through `reporters.js` (`toJson`,
  `toMarkdown`). Default paths are `frai-eval-report.json` and `frai-eval-report.md`; a path with no extension
  gets one added.
- The built-in metrics in `metrics.js` are exact match (case-insensitive), a keyword toxicity scan and length
  variance. Each returns an object with its `id`, a readable `label`, a `score` and the number of samples
  (`total`).
- Samples may be strings or objects with a `text` or `output` field.

#### providers

- `createProvider({ provider = 'openai', ...options })` looks the factory up in a registry;
  `registerProvider(id, factory)` adds one. Unknown ids throw.
- `createOpenAIProvider({ apiKey, baseUrl, organization, fetch })` requires an API key and a fetch
  implementation (passed in, or the global one).
- Its `chatCompletion({ messages, model, temperature, maxTokens, responseFormat, seed, signal })` posts to
  `<baseUrl>/chat/completions` and returns `{ content, model, usage, raw }`.
- Defaults: base URL `https://api.openai.com/v1`, model `gpt-4.1-nano-2025-04-14`. A non-OK response throws an
  `Error` carrying `status` and, when the body parses, `payload`.
- The provider tests mock `fetch` with `vi.fn`; no test calls the real API.

#### finetune

- A governance plan is a JSON object with the sections `dataset`, `training`, `evaluation`, `approvals`,
  `monitoring` and `audit`. `docs/finetune-governance.md` documents the schema.
- `createGovernanceTemplate(overrides)` deep-merges overrides into the default template; arrays are replaced,
  not merged.
- `validateGovernancePlan(plan)` returns `{ valid, errors }`, where each error is `{ path, message }` with a
  path such as `dataset.sensitivity.level`.
- `calculateReadiness(plan)` returns `{ status, score, checkpoints }` over the checkpoints dataset, evaluation,
  approvals, monitoring and audit. `summarizeGovernance(plan)` turns that into a short text summary.
- From the CLI: `frai finetune template` writes `frai-finetune-plan.json`; `frai finetune validate <plan>`
  validates it.

### frai-gate (packages/frai-gate) in detail

- In frai-gate, `validateSpec` (`gate/validate.ts`) is pure and offline; only `pipeline/agent.ts` makes network calls.
- Version 0.0.1. The `frai-gate` bin is `dist/cli.js`. Published files: `dist/`, `src/`, `assets/`.
- The gate: a spec (a Markdown file) must contain a gate section with seven answered subsections: Risk tier,
  Data & privacy, Human oversight, Evaluation plan, Bias & fairness, Monitoring & rollback, Transparency &
  incidents.
- `src/gate/schema.ts`: the types `Severity` (`'block' | 'warn'`), `GateCheck`, `Finding`, `Verdict`,
  `GateResult` and `RiskTier`; the constants `GATE_HEADING`, `RISK_TIERS` and `GATE_CHECKS`; and
  `verdictFrom(findings)`.
- `GATE_HEADING` matches both the long heading "Responsible AI Gate" and the branded "FRAI Gate".
- `src/gate/validate.ts`: `validateSpec(markdown)` returns a `GateResult`, and `extractGateSection(markdown)`
  returns the gate section text or `null`. Both are pure functions with no file or network access.
- Validation rules:
  - HTML comments are ignored.
  - The gate section runs from its heading to the next heading of the same or a higher level.
  - Each check finds its subsection by a heading pattern; a missing or empty subsection is a block finding.
  - Placeholder text (TBD, TODO, FIXME, XXX, "fill in") is a block finding.
  - Every finding carries the check's id, a severity, a message and its source (`validator`).
  - An evaluation plan or monitoring answer without any number is a warning.
  - The risk tier must be one of prohibited, high, limited or minimal; prohibited always blocks, and high needs
    a named sign-off.
- `src/gate/report.ts`: `renderText(result, specPath)` prints the human report with verdict icons;
  `renderJson(result, specPath)` prints `spec`, `verdict`, `tier` and `findings` as JSON.
- `src/cli.ts`: `init [--out <file>]` copies `assets/rai-spec-template.md` to `FRAI-SPEC.md` (or the given
  name) and refuses to overwrite an existing file; `check <spec.md> [--smart] [--json]`;
  `draft [--out <file>] [--print]`; and `help`.
- Exit codes: 0 for PASS or WARN, 1 for BLOCK, 2 for usage errors and thrown errors.
- `src/pipeline/agent.ts`: `draftGateSection(cwd)` and `smartReview(specMarkdown, cwd)` run the Claude Agent
  SDK `query` with read-only tools (`Read`, `Glob`, `Grep`), and the model from `FRAI_GATE_MODEL` (default
  `claude-opus-5`).
- They parse the agent's answer between `<!-- RAI-GATE:BEGIN -->` and `<!-- RAI-GATE:END -->`, or
  `<!-- RAI-FINDINGS:BEGIN -->` and `<!-- RAI-FINDINGS:END -->`. Both prompts include a guard telling the agent
  never to read secrets such as `.env` files and private keys.
- `src/index.ts` re-exports `validateSpec`, `extractGateSection`, `renderText`, `renderJson`,
  `draftGateSection`, `smartReview` and the schema types and constants.
- `validate.test.ts` builds specs with a `fullSpec(overrides)` helper, which swaps in replacement text for
  individual subsections.

### frai-agent (packages/frai-agent) in detail

- frai-agent needs `OPENAI_API_KEY` to run, and nothing else in the repo imports it.
- Version 0.0.1. `main` and `exports` point at `dist/index.js`; `src/index.ts` re-exports `agent/executor.ts`
  and `tools/index.ts`.
- `createFraIAgentExecutor({ model, temperature, verbose })` requires an OpenAI key, creates `ChatOpenAI`
  (default model `gpt-4o-mini`, temperature 0), and builds an OpenAI tools agent with `SYSTEM_PROMPT` from
  `agent/prompt.ts` and two tools.
- `runFraIAgent({ input, history })` runs one request with a fresh executor.
- Tool `scan_repository` (`tools/scan-tool.ts`): optional `root`; wraps `Scanners.scanCodebase` and returns a
  text summary with relative paths.
- Tool `generate_responsible_ai_docs` (`tools/docs-tool.ts`): takes `answersJson` (a JSON string), optional
  `outputDir` and `overwrite` (default true); wraps `Documents.generateDocuments` and writes the three docs.
- `config/env.ts`: `resolveOpenAiApiKey` returns the OpenAI key to use, or null, and `requireOpenAiApiKey`
  throws when there is none. `resolveWorkingDirectory` turns the tools' optional `root` into an absolute
  path.
- `cli/run.ts`: with no instruction it starts a REPL (`frai-agent>` prompt; `exit`, `quit` or `:q` leaves);
  with an instruction it runs one turn. Flags: `--model <name>`, `--interactive`/`-i`, `--verbose`/`-v`,
  `--help`/`-h`.
- LangChain 0.1 entry points are imported by subpath: `langchain/prompts`, `langchain/agents`,
  `langchain/schema`, `langchain/tools`.

## Conventions

- ES modules everywhere (`"type": "module"`); TypeScript uses NodeNext resolution, so relative imports end in `.js`.

### Modules and imports

- File paths relative to a module come from `import.meta.url` with `fileURLToPath` (for example
  `TEMPLATE_PATH` in frai-gate's `cli.ts`, and `__dirname` in the scanner test).
- frai-cli loads its `package.json` through `createRequire(import.meta.url)` instead of a JSON import.
- Examples of the two import styles: `import fs from 'node:fs/promises'` in frai-gate's `cli.ts`, `import fs from 'fs'`
  in frai-core's scanner.

- Node built-ins use the `node:` prefix in frai-gate and frai-agent, and bare names (`'fs'`, `'path'`) in frai-core and frai-cli.

- frai-core stays JavaScript: new code there is `.js`, no TypeScript.

### frai-core code shape

- Small helpers are usually `const` arrow functions (`const asArray = (value) => ...`); public functions are
  either `export function` or `export const` arrows.
- Options are passed as an object, with defaults set in the destructuring
  (`{ chunkSize = DEFAULT_CHUNK_SIZE } = {}`).
- Constants are named in UPPER_SNAKE_CASE (`DEFAULT_CHUNK_SIZE`, `DEFAULT_EXCLUDED_DIRS`).
- There is no JSDoc in frai-core; frai-gate uses short `/** ... */` comments on exported functions and fields.

- Don't add dependencies. Work with what the package already declares and Node built-ins; leave `package.json` dependency lists and `pnpm-lock.yaml` alone.

### Why the dependency list is enough

- frai-core has no runtime dependencies on purpose: everything in it uses Node built-ins (`fs`, `path`, `os`,
  `crypto`) and injected functions (`prompt`, `fetch`).
- The CLI already has `commander` for commands and `inquirer` for prompts; frai-gate already has the Claude
  Agent SDK; frai-agent already has LangChain and `zod` for tool schemas.
- Node 18+ provides a global `fetch`; frai-cli only falls back to `node-fetch` on older Node.
- If something seems to need a new package, write the small piece with Node built-ins, or explain the need
  instead of installing it.

- Tests are Vitest files next to the code: `*.test.js` in frai-core, `*.test.ts` in frai-gate.

### Test style

- One `describe` per unit under test, with `it` names that state the behaviour in plain words
  ("requires an API key", "blocks a missing subsection").
- External calls are replaced through injection: a `vi.fn` fetch for the OpenAI provider, a queued fake
  `prompt` for the questionnaire, custom detectors for the scanner.
- Assertions use `expect(...).toBe`, `toEqual`, `toThrow` and `expect.objectContaining`. No snapshot files are
  used.

- Tests that touch files create temp directories under `os.tmpdir()` and remove them afterwards.

### Temporary files in tests

- The pattern: `fs.mkdtempSync(path.join(os.tmpdir(), 'frai-rag-'))`, push the folder to a list, and delete it
  in `afterEach` with `fs.rmSync(dir, { recursive: true, force: true })`.
- The key-store tests create a temporary `cwd` and `homeDir` in `beforeEach` so real keys are never touched.

- `dist/` is committed build output: never edit it by hand, rebuild the package instead.

### Build output

- `dist/` is tracked in git for `frai`, `frai-gate` and `frai-agent`. frai-core has none.
- After changing a TypeScript package's `src/`, run its build so `dist/` matches the source.
- Builds are deterministic: rebuilding a package whose source did not change leaves `git status` clean.

- Style in frai, frai-core and frai-gate: 2-space indent, single quotes, semicolons, no trailing commas.

### More style

- Template literals for any string with interpolation.
- `const` by default, `let` only when the value is reassigned.
- `async`/`await` rather than promise chains; early returns for invalid input.
- Optional chaining (`?.`) and nullish defaults (`??`) are used throughout.
- Prettier is a root devDependency, but there is no Prettier config and the code does not follow Prettier's
  defaults (which use double quotes). Don't run Prettier over existing files.
- frai-agent uses double quotes; otherwise the same style.
- In frai-cli, status messages go through the `log` helper (`log.info`, `log.success`, `log.warn`, `log.error`).

### Output and errors

- In frai-cli, raw output meant for the user or for piping (JSON from `scan --json`, file lists) uses
  `console.log` directly.
- frai-gate prints with `console.log` and `console.error` and reports failure through `process.exitCode`.
- Library code in frai-core throws `Error` with a specific message (for example `Unknown provider "x"`) and
  never exits the process.

- Never print, log or commit an API key.

- `frai-gate check` without `--smart` is deterministic and offline; `draft` and `--smart` call Claude, so don't run them.

### Credentials

- The Claude Agent SDK commands need Claude Code authentication or `ANTHROPIC_API_KEY`.
- frai-cli's AI tips and frai-agent need `OPENAI_API_KEY`. No test needs any key.

- Generated files (`checklist.md`, `model_card.md`, `risk_file.md`, `frai-index.json`, `frai-eval-report.*`) are gitignored; don't commit them.

### Other ignored files

- `.gitignore` also covers `.frai/`, `.env` and its variants, `node_modules/`, `coverage`, logs and editor
  folders.
- `frai-finetune-plan.json`, written by `frai finetune template`, is not ignored.

## Glossary

- **FRAI**: Framework of Responsible Artificial Intelligence, the project name. Website frai.cc.
- **Responsible AI Gate / FRAI Gate**: the seven questions an AI feature spec must answer before it is built.
  Implemented by frai-gate.
- **Spec**: a Markdown feature specification, `FRAI-SPEC.md` by default, created from
  `assets/rai-spec-template.md`.
- **Gate section**: the part of a spec under a "Responsible AI Gate" or "FRAI Gate" heading.
- **Gate check**: one of the seven required subsections, defined in `GATE_CHECKS` with an id, a title and a
  heading pattern.
- **Finding**: one problem reported by the gate: `checkId`, `severity`, `message` and `source`.
- **Severity**: `block` (must be fixed) or `warn` (should be tightened).
- **Source**: `validator` for deterministic findings, `agent` for smart-review findings.
- **Verdict**: `BLOCK` if any finding blocks, `WARN` if any finding warns, otherwise `PASS`.
- **Risk tier**: the EU AI Act-aligned class of a feature: prohibited, high, limited or minimal.
- **Sign-off**: the named human approval that a high-risk tier requires.
- **Smart review**: `frai-gate check --smart`, an agent review of the gate answers against the code.
- **Draft**: `frai-gate draft`, an agent that reads the repo and writes a proposed gate section, marking gaps as
  "NEEDS HUMAN INPUT".
- **Questionnaire**: the eight interactive questions whose answers drive document generation.
- **Answers**: the object `{ core, impact, data, performance, monitoring, bias }` produced by the questionnaire.
- **Artefacts / docs**: the generated `checklist.md`, `model_card.md` and `risk_file.md`.
- **Checklist**: the implementation checklist document (data & privacy, model development, deployment &
  monitoring, governance & compliance).
- **Model card**: the document covering intended use, training data, evaluation, ethical considerations and
  monitoring.
- **Risk file**: the risk and compliance document: the risk summary from `calculateRiskLevel`, mitigation
  strategies, and monitoring and alerting.
- **Risk level**: Low, Medium, High or Critical, computed from the answers. Not the same thing as a gate risk
  tier.
- **AI tips**: optional OpenAI-generated recommendations inserted into each document.
- **Scan**: a static pass over source files looking for AI libraries and AI-style function calls.
- **Detector**: a plug-in object with `id` and `analyze` used by the scanner.
- **AI file**: a file at least one detector flagged.
- **RAG index**: the JSON file of chunks and embeddings written by `frai rag index`.
- **Chunk**: a slice of a document of up to `chunkSize` words.
- **Embedding**: here, the 8-number vector from `simpleEmbed`, not a model embedding.
- **Outputs / references**: model outputs to evaluate and the expected answers, both JSON arrays.
- **Metric**: a function returning `{ id, label, score, total, ... }` for a set of outputs.
- **Evaluation report**: the JSON or Markdown file written by `frai eval`.
- **Governance plan**: the fine-tuning plan JSON validated by `Finetune.validateGovernancePlan`.
- **Readiness checkpoint**: one of dataset, evaluation, approvals, monitoring and audit in `calculateReadiness`.
- **Provider**: an LLM client created through the providers registry; only OpenAI exists today.
- **Local key / global key**: an OpenAI key in the project's `.env`, or in `~/.config/frai/config`.
- **Namespace export**: a frai-core module exposed as one object from `src/index.js`, such as `Scanners`.
- **Workspace package**: one of the four folders under `packages/`, linked by pnpm.
- **Pipeline (turbo)**: the task graph in `turbo.json`.
- **Pipeline (frai-gate)**: `src/pipeline/agent.ts`, the Claude Agent SDK part of the gate.
- **tsx**: the TypeScript runner used by the `start` and `dev` scripts of frai-gate and frai-agent.
- **Claude Agent SDK**: `@anthropic-ai/claude-agent-sdk`, used only by frai-gate.
- **LangChain tools**: `DynamicStructuredTool` instances with `zod` schemas, used only by frai-agent.
