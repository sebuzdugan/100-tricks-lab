import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findOrder, findCustomer } from '../src/index.js';

test('findOrder returns an order or null', () => {
  assert.equal(findOrder('A100').status, 'shipped');
  assert.equal(findOrder('Z999'), null);
});

test('findCustomer returns a customer or null', () => {
  assert.equal(findCustomer('C1').plan, 'pro');
  assert.equal(findCustomer('C404'), null);
});
