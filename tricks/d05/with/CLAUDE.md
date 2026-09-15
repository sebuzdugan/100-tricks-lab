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
