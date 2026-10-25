# Conventions

- ES modules, Node 20 or newer, no dependencies.
- Money is always whole cents (integers). Format with `formatEuros`, parse with `parseEuros` (src/money.js).
- Dates are plain `YYYY-MM-DD` strings in UTC; all date maths goes through src/dates.js.
- One module per file in `src/`, named exports only, a JSDoc comment on every exported function.
- Tests live in `test/<module>.test.js` and use `node:test` with `node:assert/strict`.
- Run the whole suite with `npm test` (it runs `node --test`).
- Two-space indentation, single quotes, semicolons.
