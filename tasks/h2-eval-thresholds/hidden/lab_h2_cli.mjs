// Hidden CLI acceptance checks for h2-eval-thresholds. Usage: node lab_h2_cli.mjs <workdir>. Exit 0 = pass.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const W = path.resolve(process.argv[2]);
const CLI = path.join(W, 'packages/frai-cli/dist/index.js');
const T = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h2-cli-'));
fs.writeFileSync(path.join(T, 'outputs.json'), JSON.stringify(['Hello', 'World']));
fs.writeFileSync(path.join(T, 'references.json'), JSON.stringify(['hello', 'there']));
// With these files: exact_match = 0.5, length_variance = 1.

const fail = (msg) => { console.log(`FAIL ${msg}`); process.exit(1); };
const run = (args) => {
  const r = spawnSync(process.execPath, [CLI, 'eval', ...args], {
    cwd: T, encoding: 'utf8', timeout: 30000, env: { ...process.env, HOME: T, CI: 'true' }
  });
  return { code: r.status, out: `${r.stdout ?? ''}${r.stderr ?? ''}` };
};
const withRefs = (report, ...rest) => ['--outputs', 'outputs.json', '--references', 'references.json', '--report', report, ...rest];
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(T, name), 'utf8'));
const exists = (name) => fs.existsSync(path.join(T, name));

let r = run(withRefs('plain.json'));
if (r.code !== 0) fail(`frai eval without --threshold exits ${r.code}`);
if (Object.keys(readJson('plain.json')).sort().join() !== 'metadata,metrics') fail('report without --threshold changed shape');
r = run(withRefs('plain.md', '--format', 'markdown'));
if (r.code !== 0 || /threshold/i.test(fs.readFileSync(path.join(T, 'plain.md'), 'utf8'))) fail('markdown report without --threshold changed');

r = run(withRefs('pass.json', '--threshold', 'exact_match=0.5', '--threshold', 'length_variance=1'));
if (r.code !== 0) fail(`two passing thresholds (one exactly at its minimum) exit ${r.code}\n${r.out}`);
let rep = readJson('pass.json');
if (rep.passed !== true || !Array.isArray(rep.thresholds) || rep.thresholds.length !== 2) fail(`passing run report: passed=${rep.passed}, thresholds=${JSON.stringify(rep.thresholds)}`);

for (const [name, order] of [['fail1.json', ['exact_match=0.75', 'length_variance=0.9']], ['fail2.json', ['length_variance=0.9', 'exact_match=0.75']]]) {
  r = run(withRefs(name, '--threshold', order[0], '--threshold', order[1]));
  if (r.code !== 1) fail(`thresholds ${order.join(' + ')} (exact_match fails) exit ${r.code}, expected 1`);
  if (!exists(name)) fail('report not written when a threshold fails');
  rep = readJson(name);
  const em = (rep.thresholds ?? []).find((t) => t.metric === 'exact_match');
  const lv = (rep.thresholds ?? []).find((t) => t.metric === 'length_variance');
  if (rep.passed !== false || rep.thresholds?.length !== 2 || !em || !lv) fail(`repeated --threshold not all recorded: ${JSON.stringify(rep.thresholds)}`);
  if (em.passed !== false || em.score !== 0.5 || em.min !== 0.75 || lv.passed !== true) fail(`wrong threshold entries: ${JSON.stringify(rep.thresholds)}`);
}

r = run(['--outputs', 'outputs.json', '--report', 'noscore.json', '--threshold', 'exact_match=0']);
if (r.code !== 1) fail(`threshold on a metric with no score exits ${r.code}, expected 1`);
rep = readJson('noscore.json');
if (rep.passed !== false || rep.thresholds?.[0]?.score !== null || rep.thresholds?.[0]?.passed !== false) fail(`no-score threshold entry wrong: ${JSON.stringify(rep.thresholds)}`);

r = run(withRefs('fail.md', '--format', 'markdown', '--threshold', 'exact_match=0.75', '--threshold', 'length_variance=0.9'));
if (r.code !== 1) fail(`markdown run with a failing threshold exits ${r.code}`);
const mdLines = fs.readFileSync(path.join(T, 'fail.md'), 'utf8').split('\n');
const start = mdLines.findIndex((l) => /^(#+\s|\*\*).*threshold/i.test(l));
if (start < 0) fail('markdown report has no Thresholds section');
const rest = mdLines.slice(start + 1);
const end = rest.findIndex((l) => /^#{1,2}\s|^---\s*$/.test(l));
const text = (end === -1 ? rest : rest.slice(0, end)).join('\n');
const iEm = text.indexOf('exact_match');
const iLv = text.indexOf('length_variance');
if (iEm < 0 || iLv < 0) fail('markdown Thresholds section does not list both metrics');
const seg = (i, j) => text.slice(i, j > i ? j : text.length);
const emText = seg(iEm, iLv);
const lvText = seg(iLv, iEm);
if (!/FAIL/.test(emText) || /PASS/.test(emText) || !/PASS/.test(lvText)) fail('markdown Thresholds section does not show PASS/FAIL per metric');

const usage = ['exact_match', 'exact_match=', 'exact_match=abc', '=0.5', 'exact_match=1.5', 'exact_match=-0.1', 'bogus=0.5'];
for (const [i, spec] of usage.entries()) {
  const name = `usage${i}.json`;
  r = run(withRefs(name, '--threshold', 'length_variance=0.5', '--threshold', spec));
  if (r.code !== 2) fail(`--threshold "${spec}" exits ${r.code}, expected 2`);
  if (exists(name)) fail(`--threshold "${spec}" still wrote a report`);
  if (!r.out.trim()) fail(`--threshold "${spec}" exits 2 without a message`);
}
r = run(withRefs('unknown.json', '--threshold', 'bogus=0.5'));
for (const id of ['exact_match', 'toxicity', 'length_variance']) {
  if (!r.out.includes(id)) fail(`unknown metric message does not list valid id ${id}: ${r.out.trim()}`);
}

// "Document the option with the other frai eval options": the other eval options are listed in `frai eval --help`
// (the READMEs only name the command), so the help text or either README counts.
const docs = ['README.md', 'packages/frai-cli/README.md'].map((f) => fs.readFileSync(path.join(W, f), 'utf8'));
const help = spawnSync(process.execPath, [CLI, 'eval', '--help'], { cwd: T, encoding: 'utf8', timeout: 30000, env: { ...process.env, HOME: T, CI: 'true' } });
docs.push(`${help.stdout ?? ''}${help.stderr ?? ''}`);
if (!docs.some((d) => d.includes('--threshold'))) fail('--threshold is not documented');

fs.rmSync(T, { recursive: true, force: true });
console.log('OK');
