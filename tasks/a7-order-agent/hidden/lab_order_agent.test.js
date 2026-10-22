// Hidden tests for a7-order-agent (copied in by accept.sh after the agent finishes).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scriptedModel } from './mock-model.js';
import { getOrderStatus, answerOrderQuestion } from '../src/order-agent.js';

const toolResults = (call) => call.prompt.filter((m) => m.role === 'tool').flatMap((m) => m.content).filter((p) => p.type === 'tool-result');
const outputValue = (part) => (part.output && 'value' in part.output ? part.output.value : part.output);

test('getOrderStatus is a module-level tool with an input schema and a per-tool context schema', () => {
  assert.equal(typeof getOrderStatus, 'object');
  assert.ok(getOrderStatus.inputSchema, 'tool has no inputSchema');
  assert.ok(getOrderStatus.contextSchema, 'tool declares no contextSchema (AI SDK 7 per-tool context)');
  assert.equal(typeof getOrderStatus.execute, 'function');
});

test('getOrderStatus reads the customer from its tool context', async () => {
  const opts = (customerId) => ({ toolCallId: 't1', messages: [], context: { customerId } });
  assert.deepEqual(await getOrderStatus.execute({ orderId: 'A100' }, opts('C1')), { orderId: 'A100', status: 'shipped', eta: '2026-10-09' });
  assert.deepEqual(await getOrderStatus.execute({ orderId: 'A100' }, opts('C2')), { orderId: 'A100', error: 'not found' });
  assert.deepEqual(await getOrderStatus.execute({ orderId: 'Z999' }, opts('C1')), { orderId: 'Z999', error: 'not found' });
  assert.deepEqual(await getOrderStatus.execute({ orderId: 'B201' }, opts('C2')), { orderId: 'B201', status: 'cancelled', eta: null });
});

test('answerOrderQuestion runs the tool loop and totals usage across steps', async () => {
  const model = scriptedModel([
    { toolCalls: [{ name: 'getOrderStatus', input: { orderId: 'A100' } }], usage: [100, 7] },
    { toolCalls: [{ name: 'getOrderStatus', input: { orderId: 'B200' } }], usage: [200, 8] },
    { text: 'Your order A100 has shipped and arrives on 9 October.', usage: [300, 9] },
  ]);
  const r = await answerOrderQuestion(model, 'Where are my orders A100 and B200?', { customerId: 'C1' });
  assert.equal(r.answer, 'Your order A100 has shipped and arrives on 9 October.');
  assert.deepEqual(r.lookedUp, ['A100', 'B200']);
  assert.equal(r.inputTokens, 600);
  assert.equal(r.outputTokens, 24);
  assert.equal(model.calls.length, 3);
  const results = toolResults(model.calls[2]).map(outputValue);
  assert.deepEqual(results[0], { orderId: 'A100', status: 'shipped', eta: '2026-10-09' });
  assert.deepEqual(results[1], { orderId: 'B200', error: 'not found' }, "another customer's order leaked to the model");
});

test('answerOrderQuestion sends the instructions and offers the tool', async () => {
  const model = scriptedModel([{ text: 'Hi.' }]);
  const r = await answerOrderQuestion(model, 'Hello', { customerId: 'C2' });
  assert.equal(r.answer, 'Hi.');
  assert.deepEqual(r.lookedUp, []);
  const first = model.calls[0];
  const system = first.prompt.filter((m) => m.role === 'system').map((m) => m.content).join('\n');
  assert.match(system, /order-status assistant/);
  assert.ok((first.tools ?? []).some((t) => t.name === 'getOrderStatus'), 'getOrderStatus not offered to the model');
  const user = JSON.stringify(first.prompt.filter((m) => m.role === 'user'));
  assert.match(user, /Hello/);
});

test('answerOrderQuestion stops after 5 model steps', async () => {
  const model = scriptedModel([{ toolCalls: [{ name: 'getOrderStatus', input: { orderId: 'A101' } }] }]);
  const r = await answerOrderQuestion(model, 'Keep checking A101', { customerId: 'C1' });
  assert.equal(model.calls.length, 5);
  assert.equal(r.lookedUp.length, 5);
  assert.equal(r.inputTokens, 50);
});
