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
