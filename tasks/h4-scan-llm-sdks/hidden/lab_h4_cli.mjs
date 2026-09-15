// Hidden CLI and frai-agent checks for h4-scan-llm-sdks. Usage: node lab_h4_cli.mjs <workdir> <demo-fixture-dir>. Exit 0 = pass.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const W = path.resolve(process.argv[2]);
const CLI = path.join(W, 'packages/frai-cli/dist/index.js');
const fail = (msg) => { console.log(`FAIL ${msg}`); process.exit(1); };
const T = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h4-cli-'));
const demo = path.join(T, 'services', 'triage');
fs.cpSync(path.resolve(process.argv[3]), demo, { recursive: true });
fs.writeFileSync(path.join(T, 'unrelated.js'), "import OpenAI from 'openai';\n");
const env = { ...process.env, HOME: T, CI: 'true' };
const frai = (cwd, args) => {
  const r = spawnSync(process.execPath, [CLI, ...args], { cwd, env, input: '', encoding: 'utf8', timeout: 20000 });
  return { code: r.status, out: `${r.stdout ?? ''}${r.stderr ?? ''}`, stdout: r.stdout ?? '' };
};

let r = frai(demo, ['scan']);
if (r.code !== 0 || !/^\s*- src\/triage\.js\s*$/m.test(r.out) || /No AI indicators/.test(r.out)) fail(`frai scan inside the demo: exit ${r.code}\n${r.out.slice(0, 300)}`);

r = frai(T, ['scan', 'services/triage']);
if (r.code !== 0 || !/^\s*- (services\/triage\/)?src\/triage\.js\s*$/m.test(r.out)) fail(`frai scan services/triage (relative dir) did not list src/triage.js: exit ${r.code}\n${r.out.slice(0, 300)}`);
if (/unrelated\.js/.test(r.out)) fail('frai scan <dir> scanned outside the given directory');

r = frai(os.tmpdir(), ['scan', demo, '--json']);
let json;
try { json = JSON.parse(r.stdout); } catch { fail(`frai scan <dir> --json is not JSON: ${r.out.slice(0, 200)}`); }
if (r.code !== 0 || json.totalFiles !== 2 || JSON.stringify(json.aiLibraryMatches[path.join(demo, 'src', 'triage.js')]) !== '["openai"]') {
  fail(`frai scan <abs dir> --json: exit ${r.code}, ${JSON.stringify(json).slice(0, 300)}`);
}

r = frai(T, ['scan', 'does-not-exist']);
if (r.code === 0) fail('frai scan on a missing directory exits 0');
r = frai(T, ['scan', 'does-not-exist', '--json']);
if (r.code === 0) fail('frai scan --json on a missing directory exits 0');

// frai-agent's scan_repository tool goes through the same scanner.
const tool = path.join(W, 'packages/frai-agent/dist/tools/scan-tool.js');
const a = spawnSync(process.execPath, ['--input-type=module', '-e', `const m = await import(${JSON.stringify(tool)}); console.log('RESULT:' + await m.scanRepositoryTool.func({ root: ${JSON.stringify(demo)} }));`], { cwd: T, env, encoding: 'utf8', timeout: 30000 });
const out = (a.stdout ?? '').split('\n').find((l) => l.startsWith('RESULT:')) ?? '';
if (!out.includes('src/triage.js') || !/openai \(src\/triage\.js\)/.test(out)) fail(`frai-agent scan_repository: ${(out || a.stderr || '').slice(0, 300)}`);

fs.rmSync(T, { recursive: true, force: true });
console.log('OK');
