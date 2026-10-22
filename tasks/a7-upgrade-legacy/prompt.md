This repo (helpdesk-ai) was upgraded from AI SDK 6 to the Vercel AI SDK 7: `ai` is now 7.0.128, pinned in package.json. Keep that version and don't add or change dependencies.

`src/legacy/assistant.js` was written for AI SDK 6 and no longer works correctly on AI SDK 7. Migrate it to AI SDK 7 so that every exported function keeps the behaviour its JSDoc documents. Keep the exported names and signatures.

Tests can use the scripted mock model in `test/helpers/mock-model.js`.
