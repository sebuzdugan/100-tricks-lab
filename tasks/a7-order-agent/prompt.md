This repo (helpdesk-ai) uses the Vercel AI SDK, `ai` 7.0.128 (AI SDK 7), pinned in package.json. Keep that version and don't add or change dependencies.

Add `src/order-agent.js` with two exports:

1. `getOrderStatus`: an AI SDK tool, defined once at module level with `tool()`. The model calls it with `{ orderId }`. It returns `{ orderId, status, eta }` for that order from `src/data/orders.js`, but only if the order belongs to the current customer; otherwise (unknown id or someone else's order) it returns `{ orderId, error: 'not found' }`. The current customer's id must reach the tool through AI SDK 7's per-tool context (`{ customerId }`), not through the model's input and not through a closure.

2. `answerOrderQuestion(model, question, { customerId })`: answers a customer's question with `generateText`. Give the model the instructions "You are Acme's order-status assistant. Answer in one short sentence." and the `getOrderStatus` tool, and let it call the tool as often as it needs, up to 5 model steps in total. Resolve to `{ answer, lookedUp, inputTokens, outputTokens }`: the model's final text, the order ids it looked up (in call order), and the input and output token totals across all steps.

`model` is any AI SDK language model; tests pass the scripted mock from `test/helpers/mock-model.js`.
