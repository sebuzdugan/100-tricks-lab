// Day 55 overlay ("only the failing test"): the user's report turned into one failing test, the way a maintainer
// would write it. Not part of base/subtrack-m6; a trick folds it into the baseline with its overlay.
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BIN = fileURLToPath(new URL('../bin/subtrack.js', import.meta.url));

test('issue #41: a gym membership at 39.95 can be added', () => {
  const dir = mkdtempSync(join(tmpdir(), 'subtrack-41-'));
  try {
    const file = join(dir, 'subs.json');
    const add = spawnSync(process.execPath, [BIN, 'add', 'Gym', '39.95', '--since', '2026-10-03', '--file', file], { encoding: 'utf8' });
    assert.equal(add.status, 0, add.stderr);
    const list = spawnSync(process.execPath, [BIN, 'list', '--file', file], { encoding: 'utf8' });
    assert.match(list.stdout, /Gym\s+€39\.95 monthly\s+€39\.95 a month/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
