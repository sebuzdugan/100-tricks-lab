import test from 'node:test';
import assert from 'node:assert/strict';
import { upcoming } from '../src/renewals.js';

const plan = (name, cycle, since, price = 1000) => ({ name, price, cycle, since });

test('lists the charges inside the window, a charge today included', () => {
  const subs = [plan('Today', 'monthly', '2026-09-24'), plan('In a week', 'monthly', '2026-08-31'), plan('Later', 'yearly', '2025-12-01')];
  const rows = upcoming(subs, '2026-10-24', 7);
  assert.deepEqual(rows.map((r) => [r.name, r.date, r.inDays]), [['Today', '2026-10-24', 0], ['In a week', '2026-10-31', 7]]);
});

test('each row carries a short label for people', () => {
  const [row] = upcoming([plan('Netflix', 'monthly', '2026-09-27', 1299)], '2026-10-24', 7);
  assert.deepEqual(row, { name: 'Netflix', date: '2026-10-27', when: '27 Oct', inDays: 3, price: 1299, cycle: 'monthly' });
});

test('lists upcoming charges soonest first, across a month boundary', () => {
  const subs = [plan('Gym', 'monthly', '2026-09-02'), plan('Music', 'monthly', '2026-09-30')];
  const rows = upcoming(subs, '2026-10-25', 14);
  assert.deepEqual(rows.map((r) => r.date), ['2026-10-30', '2026-11-02']);
});

test('nothing in the window gives an empty list', () => {
  assert.deepEqual(upcoming([plan('Domain', 'yearly', '2026-03-02')], '2026-10-24'), []);
});
