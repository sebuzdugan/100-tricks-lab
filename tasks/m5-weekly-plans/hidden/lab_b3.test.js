// B3 (a file it never opened): the CSV export has its own months-per-charge table and must handle weekly plans too.
import test from 'node:test';
import assert from 'node:assert/strict';
import { toCsv } from '../src/export.js';
import { WEEKLY } from './_weekly.js';

test('[B3] export shows a weekly plan with its monthly cost and next charge', () => {
  const csv = toCsv([
    { name: 'Cleaner', price: 1200, cycle: WEEKLY, since: '2026-10-20' },
    { name: 'Netflix', price: 1299, cycle: 'monthly', since: '2025-11-14' },
  ], '2026-10-24');
  const rows = csv.trim().split('\n').map((l) => l.split(','));
  assert.deepEqual(rows[0], ['name', 'price', 'cycle', 'monthly_cost', 'next_charge']);
  assert.deepEqual(rows[1], ['Cleaner', '12.00', WEEKLY, '52.00', '2026-10-27']);
  assert.deepEqual(rows[2], ['Netflix', '12.99', 'monthly', '12.99', '2026-11-14']);
});
