// B1 (its own tests catch it): renewals are listed soonest first. The visible test for this fails on the baseline.
import test from 'node:test';
import assert from 'node:assert/strict';
import { upcoming } from '../src/renewals.js';

const plan = (name, cycle, since) => ({ name, price: 1000, cycle, since });
const dates = (rows) => rows.map((r) => r.date);

test('[B1] soonest first across a month boundary', () => {
  const subs = [plan('A', 'monthly', '2026-08-01'), plan('B', 'monthly', '2026-07-28'), plan('C', 'monthly', '2026-09-12')];
  assert.deepEqual(dates(upcoming(subs, '2026-10-26', 20)), ['2026-10-28', '2026-11-01', '2026-11-12']);
});

test('[B1] soonest first inside one month (9th before 12th before 25th)', () => {
  const subs = [plan('X', 'monthly', '2026-01-25'), plan('Y', 'monthly', '2026-02-12'), plan('Z', 'monthly', '2026-03-09')];
  assert.deepEqual(dates(upcoming(subs, '2026-11-01', 30)), ['2026-11-09', '2026-11-12', '2026-11-25']);
});

test('[B1] soonest first across a year boundary', () => {
  const subs = [plan('New year', 'yearly', '2025-01-02'), plan('Old year', 'monthly', '2026-10-30')];
  assert.deepEqual(dates(upcoming(subs, '2026-12-20', 30)), ['2026-12-30', '2027-01-02']);
});
