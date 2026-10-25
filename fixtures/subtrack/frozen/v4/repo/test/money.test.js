import test from 'node:test';
import assert from 'node:assert/strict';
import { formatEuros, parseEuros, plainEuros } from '../src/money.js';

test('parseEuros reads what people type', () => {
  assert.equal(parseEuros('12'), 1200);
  assert.equal(parseEuros('12.5'), 1250);
  assert.equal(parseEuros('12.99'), 1299);
  assert.equal(parseEuros('1,299.00'), 129900);
  assert.equal(parseEuros(' 7 '), 700);
});

test('parseEuros rejects what is not an amount', () => {
  for (const text of ['', 'abc', '12.345', '-5', '1,29', '12,99']) assert.equal(parseEuros(text), null, text);
});

test('formatEuros adds the sign, thousands separators and two decimals', () => {
  assert.equal(formatEuros(123456), '€1,234.56');
  assert.equal(formatEuros(5), '€0.05');
  assert.equal(formatEuros(0), '€0.00');
  assert.equal(formatEuros(-250), '-€2.50');
});

test('plainEuros writes a plain decimal', () => {
  assert.equal(plainEuros(129900), '1299.00');
  assert.equal(plainEuros(5), '0.05');
});
