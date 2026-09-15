// Hidden CLI and frai-agent checks for h3-key-store. Usage: node lab_h3_cli.mjs <workdir>. Exit 0 = pass.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const W = path.resolve(process.argv[2]);
const CLI = path.join(W, 'packages/frai-cli/dist/index.js');
const fail = (msg) => { console.log(`FAIL ${msg}`); process.exit(1); };
const ENV_BEFORE = '# app\nDATABASE_URL=postgres://db/app\n\nOPENAI_API_KEY=sk-old\nLOG_LEVEL=debug\n';

function sandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h3-'));
  const home = path.join(root, 'home');
  const cwd = path.join(root, 'project');
  fs.mkdirSync(home);
  fs.mkdirSync(cwd);
  fs.writeFileSync(path.join(cwd, '.env'), ENV_BEFORE);
  return { root, home, cwd };
}
function frai(box, args) {
  const env = { ...process.env, HOME: box.home, USERPROFILE: box.home, CI: 'true' };
  delete env.OPENAI_API_KEY;
  const r = spawnSync(process.execPath, [CLI, ...args], { cwd: box.cwd, env, input: '', encoding: 'utf8', timeout: 20000 });
  return { code: r.status ?? `signal ${r.signal}`, timedOut: r.error?.code === 'ETIMEDOUT', out: `${r.stdout ?? ''}${r.stderr ?? ''}` };
}
const envOf = (box) => fs.readFileSync(path.join(box.cwd, '.env'), 'utf8');
const globalOf = (box) => {
  const p = path.join(box.home, '.config/frai/config');
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : null;
};
const expectLocal = (box, key, label) => {
  const expected = ENV_BEFORE.replace('OPENAI_API_KEY=sk-old', `OPENAI_API_KEY=${key}`);
  if (envOf(box) !== expected) fail(`${label}: .env should only have its key changed, got ${JSON.stringify(envOf(box))}`);
};

for (const [args, where, label] of [
  [['setup', '--key', 'sk-sub-local'], 'local', 'frai setup --key'],
  [['setup', '--key', 'sk-sub-global', '--global'], 'global', 'frai setup --key --global'],
  [['setup', '--global', '--key', 'sk-sub-global2'], 'global', 'frai setup --global --key'],
  [['--setup', '--key', 'sk-root-local'], 'local', 'frai --setup --key'],
  [['--setup', '--key', 'sk-root-global', '--global'], 'global', 'frai --setup --key --global']
]) {
  const box = sandbox();
  const key = args[args.indexOf('--key') + 1];
  const r = frai(box, args);
  if (r.timedOut) fail(`${label} waited for interactive input`);
  if (r.code !== 0) fail(`${label} exits ${r.code}: ${r.out.trim().slice(0, 200)}`);
  if (where === 'local') {
    expectLocal(box, key, label);
    if (globalOf(box)) fail(`${label} also wrote the global config`);
  } else {
    if (globalOf(box)?.OPENAI_API_KEY !== key) fail(`${label} did not store the key globally`);
    if (envOf(box) !== ENV_BEFORE) fail(`${label} changed the local .env`);
  }
  fs.rmSync(box.root, { recursive: true, force: true });
}

// frai config: a .env without a key is not a configured key.
{
  const box = sandbox();
  fs.writeFileSync(path.join(box.cwd, '.env'), 'DATABASE_URL=postgres://db/app\n');
  const status = (out) => {
    const line = out.split('\n').find((l) => l.includes('configuration status'));
    try { return JSON.parse(line.slice(line.indexOf('{'))); } catch { return null; }
  };
  let r = frai(box, ['config']);
  if (r.code !== 0 || status(r.out)?.local?.configured !== false) fail(`frai config with a key-less .env: ${r.out.trim().slice(0, 200)}`);
  fs.writeFileSync(path.join(box.cwd, '.env'), 'export OPENAI_API_KEY="sk-live" # rotated\n');
  r = frai(box, ['config']);
  if (r.code !== 0 || status(r.out)?.local?.configured !== true) fail(`frai config with an exported quoted key: ${r.out.trim().slice(0, 200)}`);
  fs.rmSync(box.root, { recursive: true, force: true });
}

// frai-agent resolves the key through frai-core.
{
  const box = sandbox();
  fs.writeFileSync(path.join(box.cwd, '.env'), 'FOO=1\nexport OPENAI_API_KEY="sk-agent" # rotated\n');
  const env = { ...process.env, HOME: box.home, USERPROFILE: box.home };
  delete env.OPENAI_API_KEY;
  const mod = path.join(W, 'packages/frai-agent/dist/config/env.js');
  const r = spawnSync(process.execPath, ['--input-type=module', '-e', `const m = await import(${JSON.stringify(mod)}); console.log(JSON.stringify(m.resolveOpenAiApiKey()));`], { cwd: box.cwd, env, encoding: 'utf8', timeout: 20000 });
  if ((r.stdout ?? '').trim() !== '"sk-agent"') fail(`frai-agent resolveOpenAiApiKey returned ${(r.stdout || r.stderr || '').trim().slice(0, 200)}`);
  fs.rmSync(box.root, { recursive: true, force: true });
}
console.log('OK');
