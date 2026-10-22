// Hidden tests for a7-upgrade-legacy (copied in by accept.sh after the agent finishes).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scriptedModel } from './mock-model.js';
import { summarizeThread, answerAboutOrders, classifyTicket, continueChat } from '../src/legacy/assistant.js';

const toolResults = (call) => call.prompt.filter((m) => m.role === 'tool').flatMap((m) => m.content).filter((p) => p.type === 'tool-result');
const outputValue = (part) => (part.output && 'value' in part.output ? part.output.value : part.output);

test('summarizeThread summarises with the summary rules and reports token use', async () => {
  const model = scriptedModel([{ text: 'Customer wants a refund for A100. Agent asked for the order id.', usage: [57, 12] }]);
  const r = await summarizeThread(model, [{ from: 'customer', text: 'I want a refund' }, { from: 'agent', text: 'Which order?' }, { from: 'customer', text: 'A100' }]);
  assert.deepEqual(r, { summary: 'Customer wants a refund for A100. Agent asked for the order id.', inputTokens: 57, cachedInputTokens: 0 });
  const prompt = model.calls[0].prompt;
  const system = prompt.filter((m) => m.role === 'system');
  assert.equal(system.length, 1);
  assert.match(system[0].content, /next agent on shift/);
  assert.deepEqual(prompt.filter((m) => m.role !== 'system').map((m) => m.role), ['user', 'assistant', 'user', 'user']);
});

test('answerAboutOrders only shows the current customer\'s orders and caps the loop at 4 calls', async () => {
  const model = scriptedModel([
    { toolCalls: [{ name: 'orderLookup', input: { orderId: 'A100' } }] },
    { toolCalls: [{ name: 'orderLookup', input: { orderId: 'B200' } }] },
    { text: 'A100 has shipped.' },
  ]);
  const r = await answerAboutOrders(model, 'Where are A100 and B200?', { customerId: 'C1' });
  assert.deepEqual(r, { text: 'A100 has shipped.', toolsUsed: ['orderLookup', 'orderLookup'] });
  const results = toolResults(model.calls[2]).map(outputValue);
  assert.deepEqual(results, [{ orderId: 'A100', status: 'shipped', eta: '2026-10-09' }, { orderId: 'B200', error: 'not found' }]);
  assert.match(model.calls[0].prompt.filter((m) => m.role === 'system').map((m) => m.content).join(''), /order assistant/);
  const loop = scriptedModel([{ toolCalls: [{ name: 'orderLookup', input: { orderId: 'B200' } }] }]);
  const r2 = await answerAboutOrders(loop, 'B200?', { customerId: 'C2' });
  assert.equal(loop.calls.length, 4);
  assert.equal(r2.toolsUsed.length, 4);
  assert.deepEqual(outputValue(toolResults(loop.calls[1])[0]), { orderId: 'B200', status: 'delivered', eta: '2026-10-02' });
});

test('classifyTicket returns the validated object', async () => {
  const model = scriptedModel([{ text: JSON.stringify({ category: 'bug', urgent: true }) }]);
  assert.deepEqual(await classifyTicket(model, 'The app crashes when I pay.'), { category: 'bug', urgent: true });
  assert.equal(model.calls[0].responseFormat?.type, 'json');
  await assert.rejects(classifyTicket(scriptedModel([{ text: JSON.stringify({ category: 'sales', urgent: false }) }]), 'Gift cards?'));
});

test('continueChat returns the whole history including this turn\'s tool calls and results', async () => {
  const model = scriptedModel([
    { toolCalls: [{ name: 'orderLookup', input: { orderId: 'A101' } }] },
    { text: 'A101 is processing, ETA 14 October.' },
  ]);
  const history = [{ role: 'user', content: 'Hi' }, { role: 'assistant', content: 'Hello! How can I help?' }];
  const out = await continueChat(model, history, 'Status of A101?', { customerId: 'C1' });
  assert.deepEqual(out.slice(0, 3), [...history, { role: 'user', content: 'Status of A101?' }]);
  assert.deepEqual(out.slice(3).map((m) => m.role), ['assistant', 'tool', 'assistant']);
  const toolMsg = out[4];
  const part = toolMsg.content.find((p) => p.type === 'tool-result');
  assert.deepEqual(outputValue(part), { orderId: 'A101', status: 'processing', eta: '2026-10-14' });
  assert.match(model.calls[0].prompt.filter((m) => m.role === 'system').map((m) => m.content).join(''), /order assistant/);
  // the returned history is valid input for the next turn
  const next = scriptedModel([{ text: 'Anything else?' }]);
  const out2 = await continueChat(next, out, 'Thanks', { customerId: 'C1' });
  assert.equal(out2.at(-1).role, 'assistant');
  assert.equal(out2.length, out.length + 2);
});
