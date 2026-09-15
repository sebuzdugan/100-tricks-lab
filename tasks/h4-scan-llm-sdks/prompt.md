Bug: `frai scan` doesn't recognise LLM applications.

Inside `examples/support-triage-demo` (an OpenAI-backed service) `frai scan` prints "No AI indicators detected", and frai-agent's `scan_repository` tool says the same. A customer's TypeScript repo that uses `@anthropic-ai/sdk` and `@langchain/openai` from `.mts` files also scans clean.

Fix detection so every entry point reports these projects:

- Detect the LLM SDKs `openai`, `anthropic`, `@anthropic-ai/sdk`, `langchain` and any `@langchain/…` package, alongside the existing libraries.
- Recognise imports however they are written. JS/TS: `import … from '…'` (including `import type` and imports spread over several lines), `import '…'`, `export … from '…'`, `require('…')`, `import('…')`. Python: `import a, b as c`, `import pkg.sub` and `from pkg.sub import x`.
- A library matches its own module or a sub-module (`openai/resources`, `torch.nn`), but not a different module that starts with the same letters (`openai-mock`, `caretaker`), a relative import, or a commented-out line.
- Scan `.mjs`, `.cjs`, `.mts` and `.cts` files too.
- Keep the scan result shape: `aiLibraryMatches` maps each file to the matched library names, without duplicates; for `@langchain/…` modules the name is `@langchain`, like the existing `@tensorflow`. Custom library lists passed to `createLibraryDetector` keep working.
- `frai scan` should accept an optional directory (`frai scan services/api`), and a directory that doesn't exist is an error with a non-zero exit, not an empty scan.

Two frai-core tests already fail on main for unrelated reasons.
