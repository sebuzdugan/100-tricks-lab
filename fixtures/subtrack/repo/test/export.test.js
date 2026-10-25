import test from 'node:test';
import assert from 'node:assert/strict';
import { toCsv } from '../src/export.js';

test('exports one row per plan with its monthly cost and next charge', () => {
  const subs = [
    { name: 'Netflix', price: 1299, cycle: 'monthly', since: '2025-11-14' },
    { name: 'Domain name', price: 1200, cycle: 'yearly', since: '2023-03-02' },
  ];
  assert.equal(toCsv(subs, '2026-10-24'), [
    'name,price,cycle,monthly_cost,next_charge',
    'Netflix,12.99,monthly,12.99,2026-11-14',
    'Domain name,12.00,yearly,1.00,2027-03-02',
    '',
  ].join('\n'));
});

test('quotes names with commas or quotes', () => {
  const csv = toCsv([{ name: 'Tea, "loose"', price: 500, cycle: 'monthly', since: '2026-10-01' }], '2026-10-24');
  assert.equal(csv.split('\n')[1], '"Tea, ""loose""",5.00,monthly,5.00,2026-11-01');
});

test('an empty list exports just the header', () => {
  assert.equal(toCsv([], '2026-10-24'), 'name,price,cycle,monthly_cost,next_charge\n');
});
