import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BIN = fileURLToPath(new URL('../bin/subtrack.js', import.meta.url));

function cli(file, ...args) {
  const r = spawnSync(process.execPath, [BIN, ...args, '--file', file], { encoding: 'utf8' });
  return { code: r.status, out: r.stdout, err: r.stderr };
}

function withFile(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'subtrack-cli-'));
  try {
    fn(join(dir, 'subs.json'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('add, list and total', () => withFile((file) => {
  assert.equal(cli(file, 'add', 'Netflix', '12.99', '--since', '2026-09-14').code, 0);
  assert.equal(cli(file, 'add', 'Domain name', '24', '--every', 'year', '--since', '2026-03-02').code, 0);
  const list = cli(file, 'list');
  assert.equal(list.code, 0);
  assert.match(list.out, /Netflix\s+€12\.99 monthly\s+€12\.99 a month/);
  assert.match(list.out, /Domain name\s+€24\.00 yearly\s+€2\.00 a month/);
  assert.equal(cli(file, 'total').out, 'Monthly total: €14.99 (2 plans)\n');
}));

test('renewals shows what charges next', () => withFile((file) => {
  cli(file, 'add', 'Netflix', '12.99', '--since', '2026-09-27');
  const r = cli(file, 'renewals', '--within', '7', '--today', '2026-10-24');
  assert.equal(r.code, 0);
  assert.equal(r.out, '27 Oct  Netflix  €12.99\n');
  assert.equal(cli(file, 'renewals', '--within', '2', '--today', '2026-10-24').out, 'Nothing renews in the next 2 days.\n');
}));

test('export writes CSV', () => withFile((file) => {
  cli(file, 'add', 'Netflix', '12.99', '--since', '2026-09-27');
  assert.equal(cli(file, 'export', '--today', '2026-10-24').out,
    'name,price,cycle,monthly_cost,next_charge\nNetflix,12.99,monthly,12.99,2026-10-27\n');
}));

test('bad input exits 2 with a message', () => withFile((file) => {
  for (const args of [['add', 'X', 'abc'], ['add', 'X'], ['frobnicate'], ['renewals', '--within', 'soon'], ['add', 'X', '5', '--every', 'fortnight']]) {
    const r = cli(file, ...args);
    assert.equal(r.code, 2, args.join(' '));
    assert.match(r.err, /^subtrack: /, args.join(' '));
  }
}));

test('adding the same name twice fails', () => withFile((file) => {
  cli(file, 'add', 'Netflix', '12.99');
  const r = cli(file, 'add', 'netflix', '9.99');
  assert.equal(r.code, 1);
  assert.match(r.err, /already on the list/);
}));
