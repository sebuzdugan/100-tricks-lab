# helpdesk-ai

AI helpers for the Acme support desk, built on the Vercel AI SDK. The `ai` package is pinned to **7.0.128 (AI SDK 7)**;
keep that version.

- Every helper takes the language model as its first argument. Production passes a real provider model; tests pass a
  scripted mock (`test/helpers/mock-model.js`), so no API key or network is needed to test.
- `src/data/` holds the in-memory orders and customers the helpers look up.
- `src/legacy/assistant.js` was written for AI SDK 6 and has not been migrated to AI SDK 7 yet.

Run the tests with `pnpm test` (Node's built-in test runner, Node 22 or newer).
