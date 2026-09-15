# Commands

- Use pnpm, not npm or yarn. This is a pnpm workspace; packages live in packages/*.
- The CLI package in packages/frai-cli is named `frai`: build it with `pnpm --filter frai build`.
- Build frai-gate with `pnpm --filter frai-gate build`.
- frai-core is plain ES modules and has no build step.
- Run a package's tests with `pnpm --filter <package> test`.
