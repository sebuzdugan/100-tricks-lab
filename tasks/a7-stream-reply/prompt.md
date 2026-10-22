This repo (helpdesk-ai) uses the Vercel AI SDK, `ai` 7.0.128 (AI SDK 7), pinned in package.json. Keep that version and don't add or change dependencies.

Add `src/stream-reply.js` exporting `streamReply(model, history, { onText } = {})`.

`history` is a chat as we store it in our database: an array of `{ role: 'system' | 'user' | 'assistant', content: string }`, oldest first. It usually starts with a system entry holding the instructions for that chat.

Stream the model's next assistant reply with `streamText`, sending the whole chat (its system instructions included). Call `onText(chunk)` for every piece of text as it arrives, in order. Resolve to `{ text, finishReason, inputTokens, outputTokens }` once the reply is complete.

`model` is any AI SDK language model; tests pass the scripted mock from `test/helpers/mock-model.js` (its `chunks` option splits a reply into streamed pieces).
