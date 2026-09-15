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
