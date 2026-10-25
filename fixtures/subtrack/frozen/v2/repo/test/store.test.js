import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { load, save, storePath, validate } from '../src/store.js';

test('storePath prefers --file, then $SUBTRACK_FILE', () => {
  assert.equal(storePath('a.json', { SUBTRACK_FILE: 'b.json' }), 'a.json');
  assert.equal(storePath(undefined, { SUBTRACK_FILE: 'b.json' }), 'b.json');
  assert.equal(storePath(undefined, {}), 'subscriptions.json');
});

test('validate accepts a good subscription', () => {
  assert.equal(validate({ name: 'Netflix', price: 1299, cycle: 'monthly', since: '2026-01-31' }), null);
  assert.equal(validate({ name: 'Domain', price: 1400, cycle: 'yearly', since: '2026-01-31' }), null);
});

test('validate explains what is wrong', () => {
  assert.match(validate({ name: '', price: 1, cycle: 'monthly', since: '2026-01-01' }), /name/);
  assert.match(validate({ name: 'A', price: 12.5, cycle: 'monthly', since: '2026-01-01' }), /whole cents/);
  assert.match(validate({ name: 'A', price: -1, cycle: 'monthly', since: '2026-01-01' }), /whole cents/);
  assert.match(validate({ name: 'A', price: 1, cycle: 'daily', since: '2026-01-01' }), /unknown billing cycle "daily"/);
  assert.match(validate({ name: 'A', price: 1, cycle: 'monthly', since: '2026-02-30' }), /date/);
});

test('save and load round-trip, and a missing file is an empty list', () => {
  const dir = mkdtempSync(join(tmpdir(), 'subtrack-'));
  try {
    const path = join(dir, 'subs.json');
    assert.deepEqual(load(path), []);
    const subs = [{ name: 'Netflix', price: 1299, cycle: 'monthly', since: '2026-01-31' }];
    save(path, subs);
    assert.deepEqual(load(path), subs);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('load reads files written by subtrack 0.1 ("month" and "year")', () => {
  const dir = mkdtempSync(join(tmpdir(), 'subtrack-'));
  try {
    const path = join(dir, 'old.json');
    writeFileSync(path, JSON.stringify({ subscriptions: [
      { name: 'Netflix', price: 1299, cycle: 'month', since: '2025-11-14' },
      { name: 'Domain', price: 1400, cycle: 'year', since: '2023-03-02' },
    ] }));
    assert.deepEqual(load(path).map((s) => s.cycle), ['monthly', 'yearly']);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
