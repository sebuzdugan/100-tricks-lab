import test from 'node:test';
import assert from 'node:assert/strict';
import { CYCLES, monthlyCents, nextCharge } from '../src/cycles.js';

test('every stored cycle name is known', () => {
  assert.ok(CYCLES.includes('monthly'));
  assert.ok(CYCLES.includes('yearly'));
});

test('a monthly plan costs its price a month', () => {
  assert.equal(monthlyCents({ price: 1299, cycle: 'monthly' }), 1299);
  assert.equal(monthlyCents({ price: 0, cycle: 'monthly' }), 0);
});

test('a yearly plan costs a twelfth of its price a month', () => {
  assert.equal(monthlyCents({ price: 12000, cycle: 'yearly' }), 1000);
  assert.equal(monthlyCents({ price: 2400, cycle: 'yearly' }), 200);
});

test('the next charge of a plan that charges today is today', () => {
  assert.equal(nextCharge({ cycle: 'monthly', since: '2026-08-24' }, '2026-10-24'), '2026-10-24');
  assert.equal(nextCharge({ cycle: 'yearly', since: '2025-10-24' }, '2026-10-24'), '2026-10-24');
});

test('a plan that has not started yet next charges on its first day', () => {
  assert.equal(nextCharge({ cycle: 'monthly', since: '2026-11-05' }, '2026-10-24'), '2026-11-05');
});

test('monthly charges started on the 31st fall on the last day of shorter months', () => {
  assert.equal(nextCharge({ cycle: 'monthly', since: '2026-01-31' }, '2026-02-01'), '2026-02-28');
  assert.equal(nextCharge({ cycle: 'monthly', since: '2026-01-31' }, '2026-03-01'), '2026-03-31');
  assert.equal(nextCharge({ cycle: 'monthly', since: '2026-01-31' }, '2026-04-02'), '2026-04-30');
});

test('a yearly plan charges once a year on the same day', () => {
  assert.equal(nextCharge({ cycle: 'yearly', since: '2023-03-02' }, '2026-10-24'), '2027-03-02');
  assert.equal(nextCharge({ cycle: 'yearly', since: '2024-02-29' }, '2026-10-24'), '2027-02-28');
});
