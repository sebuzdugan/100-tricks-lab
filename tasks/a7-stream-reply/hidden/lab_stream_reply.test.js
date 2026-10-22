// Hidden tests for a7-stream-reply (copied in by accept.sh after the agent finishes).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scriptedModel } from './mock-model.js';
import { streamReply } from '../src/stream-reply.js';

const history = [
  { role: 'system', content: 'You are the Acme support bot. Reply in plain English.' },
  { role: 'user', content: 'My parcel is late.' },
  { role: 'assistant', content: 'Sorry to hear that. What is the order id?' },
  { role: 'user', content: 'A101' },
];

test('streamReply streams text chunks in order and resolves the full reply', async () => {
  const model = scriptedModel([{ text: 'Order A101 is still processing.', chunks: ['Order A101 ', 'is still ', 'processing.'], usage: [42, 6] }]);
  const seen = [];
  const r = await streamReply(model, history, { onText: (c) => seen.push(c) });
  assert.deepEqual(seen, ['Order A101 ', 'is still ', 'processing.']);
  assert.equal(r.text, 'Order A101 is still processing.');
  assert.equal(r.finishReason, 'stop');
  assert.equal(r.inputTokens, 42);
  assert.equal(r.outputTokens, 6);
  assert.equal(model.calls.length, 1);
});

test('the stored system entry reaches the model as system instructions, with the rest of the chat', async () => {
  const model = scriptedModel([{ text: 'Checking now.' }]);
  await streamReply(model, history);
  const prompt = model.calls[0].prompt;
  const system = prompt.filter((m) => m.role === 'system');
  assert.equal(system.length, 1);
  assert.equal(system[0].content, 'You are the Acme support bot. Reply in plain English.');
  const rest = prompt.filter((m) => m.role !== 'system').map((m) => [m.role, JSON.stringify(m.content)]);
  assert.deepEqual(rest.map((x) => x[0]), ['user', 'assistant', 'user']);
  assert.match(rest[0][1], /parcel is late/);
  assert.match(rest[2][1], /A101/);
});

test('streamReply works without a system entry and without onText', async () => {
  const model = scriptedModel([{ text: 'Hello!', chunks: ['Hel', 'lo!'], usage: [3, 2] }]);
  const r = await streamReply(model, [{ role: 'user', content: 'Hi' }]);
  assert.equal(r.text, 'Hello!');
  assert.equal(r.inputTokens, 3);
  assert.equal(model.calls[0].prompt.filter((m) => m.role === 'system').length, 0);
});
