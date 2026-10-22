// Hidden tests for a7-ticket-triage (copied in by accept.sh after the agent finishes).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scriptedModel } from './mock-model.js';
import { triageTicket } from '../src/triage.js';

const toolResults = (call) => call.prompt.filter((m) => m.role === 'tool').flatMap((m) => m.content).filter((p) => p.type === 'tool-result');
const outputValue = (part) => (part.output && 'value' in part.output ? part.output.value : part.output);
const answer = { category: 'billing', priority: 'high', reply: 'Sorry about the double charge, Dana. We are refunding it now.' };

test('triageTicket looks up the customer and returns the structured answer from one generateText call', async () => {
  const model = scriptedModel([
    { toolCalls: [{ name: 'getCustomer', input: { customerId: 'C1' } }] },
    { text: JSON.stringify(answer) },
  ]);
  const r = await triageTicket(model, { customerId: 'C1', text: 'I was charged twice this month!' });
  assert.deepEqual(r, answer);
  assert.equal(model.calls.length, 2, 'expected exactly two model steps (tool call, then the structured answer)');
  const results = toolResults(model.calls[1]).map(outputValue);
  assert.equal(results[0].plan, 'pro');
  assert.match(JSON.stringify(model.calls[0].prompt), /charged twice/);
});

test('every step asks the model for JSON matching the schema and offers getCustomer', async () => {
  const model = scriptedModel([
    { toolCalls: [{ name: 'getCustomer', input: { customerId: 'C404' } }] },
    { text: JSON.stringify({ category: 'other', priority: 'low', reply: 'Thanks, we will look into it.' }) },
  ]);
  const r = await triageTicket(model, { customerId: 'C404', text: 'Hello?' });
  assert.equal(r.category, 'other');
  assert.deepEqual(outputValue(toolResults(model.calls[1])[0]), { error: 'not found' });
  for (const call of model.calls) {
    assert.equal(call.responseFormat?.type, 'json', 'structured output not requested from the model');
    const schema = JSON.stringify(call.responseFormat.schema ?? {});
    for (const v of ['billing', 'shipping', 'bug', 'other', 'low', 'normal', 'high', 'reply']) assert.ok(schema.includes(v), `schema misses ${v}`);
    assert.ok((call.tools ?? []).some((t) => t.name === 'getCustomer'), 'getCustomer not offered');
  }
});

test('triageTicket answers directly when no lookup is needed', async () => {
  const model = scriptedModel([{ text: JSON.stringify({ category: 'bug', priority: 'normal', reply: 'We are on it.' }) }]);
  assert.deepEqual(await triageTicket(model, { customerId: 'C2', text: 'The app crashes on login.' }), { category: 'bug', priority: 'normal', reply: 'We are on it.' });
  assert.equal(model.calls.length, 1);
});

test('triageTicket rejects an answer that does not match the schema', async () => {
  const bad = scriptedModel([{ text: JSON.stringify({ category: 'sales', priority: 'high', reply: 'x' }) }]);
  await assert.rejects(triageTicket(bad, { customerId: 'C1', text: 'Do you sell gift cards?' }));
  const notJson = scriptedModel([{ text: 'I think this is billing.' }]);
  await assert.rejects(triageTicket(notJson, { customerId: 'C1', text: 'Refund?' }));
});
