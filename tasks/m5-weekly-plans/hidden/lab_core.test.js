// core: weekly plans exist in the library (cost and next charge). Exact-cent prices only, so rounding never matters here.
import test from 'node:test';
import assert from 'node:assert/strict';
import { monthlyCents, nextCharge } from '../src/cycles.js';
import { validate } from '../src/store.js';
import { WEEKLY } from './_weekly.js';

test('[core] a weekly plan costs price x 52 / 12 a month', () => {
  assert.equal(monthlyCents({ price: 1200, cycle: WEEKLY }), 5200);
  assert.equal(monthlyCents({ price: 300, cycle: WEEKLY }), 1300);
});

test('[core] weekly plans charge every 7 days from their first charge', () => {
  const sub = { cycle: WEEKLY, since: '2026-10-20' };
  assert.equal(nextCharge(sub, '2026-10-24'), '2026-10-27');
  assert.equal(nextCharge(sub, '2026-10-27'), '2026-10-27');
  assert.equal(nextCharge(sub, '2026-10-28'), '2026-11-03');
  assert.equal(nextCharge(sub, '2026-10-01'), '2026-10-20');
  assert.equal(nextCharge({ cycle: WEEKLY, since: '2026-12-29' }, '2027-01-02'), '2027-01-05');
  assert.equal(nextCharge({ cycle: WEEKLY, since: '2025-01-06' }, '2026-10-24'), '2026-10-26');
});

test('[core] a weekly plan is a valid subscription', () => {
  assert.equal(validate({ name: 'Cleaner', price: 4500, cycle: WEEKLY, since: '2026-10-20' }), null);
});
