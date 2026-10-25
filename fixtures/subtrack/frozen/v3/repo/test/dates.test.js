import test from 'node:test';
import assert from 'node:assert/strict';
import { addDays, addMonths, daysBetween, parseDate, shortLabel } from '../src/dates.js';

test('parseDate accepts real dates only', () => {
  assert.equal(parseDate('2026-10-24'), '2026-10-24');
  assert.equal(parseDate('2028-02-29'), '2028-02-29');
  for (const text of ['2026-02-30', '2026-13-01', '24/10/2026', '2026-1-5', '']) assert.equal(parseDate(text), null, text);
});

test('addDays crosses months and years', () => {
  assert.equal(addDays('2026-10-30', 3), '2026-11-02');
  assert.equal(addDays('2026-12-30', 3), '2027-01-02');
  assert.equal(addDays('2026-03-01', -1), '2026-02-28');
});

test('addMonths keeps the day or uses the last day of a shorter month', () => {
  assert.equal(addMonths('2026-01-15', 1), '2026-02-15');
  assert.equal(addMonths('2026-01-31', 1), '2026-02-28');
  assert.equal(addMonths('2026-01-31', 2), '2026-03-31');
  assert.equal(addMonths('2028-02-29', 12), '2029-02-28');
  assert.equal(addMonths('2026-11-30', 3), '2027-02-28');
});

test('daysBetween counts whole days', () => {
  assert.equal(daysBetween('2026-10-24', '2026-10-31'), 7);
  assert.equal(daysBetween('2026-10-24', '2026-10-24'), 0);
  assert.equal(daysBetween('2026-12-31', '2027-01-01'), 1);
  assert.equal(daysBetween('2026-10-24', '2026-10-20'), -4);
});

test('shortLabel is day and month', () => {
  assert.equal(shortLabel('2026-11-02'), '2 Nov');
  assert.equal(shortLabel('2026-12-25'), '25 Dec');
});
