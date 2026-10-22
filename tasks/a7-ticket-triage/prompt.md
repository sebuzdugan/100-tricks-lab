This repo (helpdesk-ai) uses the Vercel AI SDK, `ai` 7.0.128 (AI SDK 7), pinned in package.json. Keep that version and don't add or change dependencies.

Add `src/triage.js` exporting `triageTicket(model, { customerId, text })`.

In a single `generateText` call, the model gets a `getCustomer` tool (it calls it with `{ customerId }`; the tool returns that customer's record from `src/data/customers.js`, or `{ error: 'not found' }`) and must answer with a structured result that matches this schema:

- `category`: one of `billing`, `shipping`, `bug`, `other`
- `priority`: one of `low`, `normal`, `high`
- `reply`: a string (a short first reply to the customer)

The tool lookup and the structured answer must happen in that one `generateText` call (no second call to the model), allowing up to 4 steps. `triageTicket` resolves to the validated object. If the model's final answer doesn't match the schema, `triageTicket` must reject.

`model` is any AI SDK language model; tests pass the scripted mock from `test/helpers/mock-model.js`.
