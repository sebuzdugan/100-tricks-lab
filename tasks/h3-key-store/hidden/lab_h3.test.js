// Hidden acceptance tests for h3-key-store (frai-core Config API). Copied in at grading time only.
import fs from 'fs';
import os from 'os';
import path from 'path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Config } from '../index.js';

let cwd;
let home;
const envPath = () => path.join(cwd, '.env');
const writeEnv = (content) => fs.writeFileSync(envPath(), content, 'utf8');
const readEnv = () => fs.readFileSync(envPath(), 'utf8');
const configPath = () => path.join(home, '.config', 'frai', 'config');
const mode = (p) => fs.statSync(p).mode & 0o777;

beforeEach(() => {
  cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h3-cwd-'));
  home = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h3-home-'));
});
afterEach(() => {
  fs.rmSync(cwd, { recursive: true, force: true });
  fs.rmSync(home, { recursive: true, force: true });
});

describe('lab h3: saving a local key', () => {
  it('creates a new .env readable only by the owner and returns its path', () => {
    expect(Config.setLocalApiKey('sk-new', cwd)).toBe(envPath());
    expect(readEnv()).toContain('OPENAI_API_KEY=sk-new');
    expect(mode(envPath())).toBe(0o600);
    expect(Config.getLocalApiKey(cwd)).toBe('sk-new');
  });

  it('updates an existing key in place and leaves every other line untouched', () => {
    const before = ['# app settings', 'DATABASE_URL=postgres://db:5432/app', '', 'OPENAI_API_KEY=sk-old', '  # keep me', 'LOG_LEVEL=debug', ''];
    writeEnv(before.join('\n'));
    fs.chmodSync(envPath(), 0o640);
    expect(Config.setLocalApiKey('sk-rotated', cwd)).toBe(envPath());
    const after = readEnv().split('\n');
    expect(after).toHaveLength(before.length);
    after.forEach((line, i) => {
      if (i === 3) expect(line).toMatch(/^OPENAI_API_KEY=(["']?)sk-rotated\1$/);
      else expect(line).toBe(before[i]);
    });
    expect(mode(envPath()) & ~0o640).toBe(0); // never loosened
    expect(Config.getLocalApiKey(cwd)).toBe('sk-rotated');
  });

  it('keeps the export prefix of the definition it updates', () => {
    writeEnv('FOO=1\nexport OPENAI_API_KEY="sk-old" # rotated monthly\nBAR=2\n');
    Config.setLocalApiKey('sk-rotated', cwd);
    const lines = readEnv().split('\n');
    expect(lines[0]).toBe('FOO=1');
    expect(lines[1]).toMatch(/^export OPENAI_API_KEY=/);
    expect(lines[2]).toBe('BAR=2');
    expect(lines).toHaveLength(4);
    expect(Config.getLocalApiKey(cwd)).toBe('sk-rotated');
  });

  it('appends the key when .env has none, even without a trailing newline', () => {
    writeEnv('DATABASE_URL=postgres://db/app\n# OPENAI_API_KEY=sk-commented');
    Config.setLocalApiKey('sk-added', cwd);
    const lines = readEnv().split('\n');
    expect(lines.slice(0, 2)).toEqual(['DATABASE_URL=postgres://db/app', '# OPENAI_API_KEY=sk-commented']);
    expect(lines.slice(2).filter((l) => /OPENAI_API_KEY/.test(l))).toHaveLength(1);
    expect(lines.slice(2).some((l) => /^(export\s+)?OPENAI_API_KEY=(["']?)sk-added\2$/.test(l))).toBe(true);
    expect(lines.slice(2).every((l) => l.trim() === '' || l.trim().startsWith('#') || /OPENAI_API_KEY/.test(l))).toBe(true);
    expect(Config.getLocalApiKey(cwd)).toBe('sk-added');
  });

  it('updates the last definition when the key is defined twice', () => {
    writeEnv('OPENAI_API_KEY=sk-first\nFOO=1\nOPENAI_API_KEY=sk-second\n');
    Config.setLocalApiKey('sk-third', cwd);
    const lines = readEnv().split('\n');
    expect(lines[0]).toBe('OPENAI_API_KEY=sk-first');
    expect(lines[1]).toBe('FOO=1');
    expect(lines[2]).toMatch(/^OPENAI_API_KEY=(["']?)sk-third\1$/);
    expect(Config.getLocalApiKey(cwd)).toBe('sk-third');
  });
});

describe('lab h3: reading a local key', () => {
  const cases = [
    ['plain', 'OPENAI_API_KEY=sk-plain\n', 'sk-plain'],
    ['export prefix', 'export OPENAI_API_KEY=sk-exported\n', 'sk-exported'],
    ['double quotes and a comment', 'export OPENAI_API_KEY="sk-quoted" # rotated\n', 'sk-quoted'],
    ['single quotes keep a hash inside', "OPENAI_API_KEY='sk-has#hash' # note\n", 'sk-has#hash'],
    ['comment after an unquoted value', 'OPENAI_API_KEY=sk-unquoted # from vault\n', 'sk-unquoted'],
    ['commented-out definitions are ignored', '# OPENAI_API_KEY=sk-disabled\nOPENAI_API_KEY=sk-live\n#OPENAI_API_KEY=sk-other\n', 'sk-live'],
    ['the last definition wins', 'OPENAI_API_KEY=sk-first\nOPENAI_API_KEY=sk-second\n', 'sk-second'],
    ['only commented out', '# OPENAI_API_KEY=sk-disabled\nFOO=1\n', null],
    ['empty value', 'FOO=1\nOPENAI_API_KEY=\n', null],
    ['empty quotes', 'OPENAI_API_KEY=""\n', null]
  ];
  it.each(cases)('%s', (_name, content, expected) => {
    writeEnv(content);
    expect(Config.getLocalApiKey(cwd)).toBe(expected);
    expect(Config.hasLocalApiKey(cwd)).toBe(expected !== null);
  });

  it('does not count a .env without the key as configured', () => {
    writeEnv('DATABASE_URL=postgres://db/app\n');
    expect(Config.hasLocalApiKey(cwd)).toBe(false);
    expect(Config.getLocalApiKey(cwd)).toBeNull();
  });
});

describe('lab h3: global config', () => {
  it('keeps other settings when saving the key and returns the config path', () => {
    fs.mkdirSync(path.dirname(configPath()), { recursive: true });
    fs.writeFileSync(configPath(), JSON.stringify({ telemetry: false, OPENAI_API_KEY: 'sk-old', model: 'gpt-4.1' }));
    expect(Config.setGlobalApiKey('sk-global', home)).toBe(configPath());
    expect(JSON.parse(fs.readFileSync(configPath(), 'utf8'))).toEqual({ telemetry: false, OPENAI_API_KEY: 'sk-global', model: 'gpt-4.1' });
    expect(Config.getGlobalApiKey(home)).toBe('sk-global');
  });

  it('creates the config with owner-only permissions', () => {
    Config.setGlobalApiKey('sk-global', home);
    expect(mode(configPath())).toBe(0o600);
    expect(mode(path.dirname(configPath()))).toBe(0o700);
    expect(Config.hasGlobalApiKey(home)).toBe(true);
  });

  it('refuses to overwrite a config that is not valid JSON', () => {
    fs.mkdirSync(path.dirname(configPath()), { recursive: true });
    const broken = '{ "telemetry": false, oops';
    fs.writeFileSync(configPath(), broken);
    expect(() => Config.setGlobalApiKey('sk-global', home)).toThrow();
    expect(fs.readFileSync(configPath(), 'utf8')).toBe(broken);
    expect(Config.getGlobalApiKey(home)).toBeNull();
    expect(Config.hasGlobalApiKey(home)).toBe(false);
  });

  it('does not count a config without a non-empty key as configured', () => {
    fs.mkdirSync(path.dirname(configPath()), { recursive: true });
    fs.writeFileSync(configPath(), JSON.stringify({ telemetry: false }));
    expect(Config.hasGlobalApiKey(home)).toBe(false);
    fs.writeFileSync(configPath(), JSON.stringify({ OPENAI_API_KEY: '' }));
    expect(Config.hasGlobalApiKey(home)).toBe(false);
    expect(Config.getGlobalApiKey(home)).toBeNull();
  });
});
