// Hidden acceptance tests for h4-scan-llm-sdks (frai-core scanner API). Copied in at grading time only.
import fs from 'fs';
import os from 'os';
import path from 'path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { Scanners } from '../index.js';
import { createLibraryDetector } from './detectors.js';

const FILES = {
  'anthropic.mts': "import Anthropic from '@anthropic-ai/sdk';\n\nexport const client = new Anthropic();\n",
  'types.ts': "import type { MessageParam } from '@anthropic-ai/sdk/resources/messages';\n\nexport type Msg = MessageParam;\n",
  'chain.ts': "import {\n  ChatOpenAI,\n  OpenAIEmbeddings,\n} from '@langchain/openai';\nimport { ChatAnthropic } from \"@langchain/anthropic\";\n\nexport const models = [ChatOpenAI, OpenAIEmbeddings, ChatAnthropic];\n",
  'multiline-default.js': "import OpenAI, {\n  toFile,\n} from 'openai';\n\nexport { OpenAI, toFile };\n",
  'shims.mjs': "import 'openai/shims/node';\n\nexport const ready = true;\n",
  'reexport.cts': "export { OpenAI as default } from 'openai';\nexport * from 'langchain/chains';\n",
  'legacy.cjs': 'const OpenAI = require("openai");\n\nmodule.exports = { OpenAI };\n',
  'lazy.js': "export async function load() {\n  const { default: Anthropic } = await import('@anthropic-ai/sdk');\n  return Anthropic;\n}\n",
  'py_multi.py': 'import numpy as np, openai\nimport torch.nn as nn\n\nclient = openai.OpenAI()\n',
  'py_from.py': 'from anthropic import Anthropic\nfrom langchain.chains import LLMChain\n\nclient = Anthropic()\n',
  'py_plain.py': 'import anthropic\n\nclient = anthropic.Anthropic()\n',
  'mock.js': "import OpenAI from 'openai-mock';\nconst caretaker = require('caretaker');\n\nexport { OpenAI, caretaker };\n",
  'relative.ts': "import { client } from './openai';\nimport chains from '../langchain/index.js';\n\nexport { client, chains };\n",
  'commented.js': "// import OpenAI from 'openai';\n// const Anthropic = require('@anthropic-ai/sdk');\nexport const x = 1;\n",
  'py_negative.py': 'import caretaker\nfrom openai_helpers import thing\nfrom .openai import client\nfrom . import anthropic\n# import torch\n# from openai import OpenAI\n\nvalue = thing\n'
};
const EXPECTED = {
  'anthropic.mts': ['@anthropic-ai/sdk'],
  'types.ts': ['@anthropic-ai/sdk'],
  'chain.ts': ['@langchain'],
  'multiline-default.js': ['openai'],
  'shims.mjs': ['openai'],
  'reexport.cts': ['langchain', 'openai'],
  'legacy.cjs': ['openai'],
  'lazy.js': ['@anthropic-ai/sdk'],
  'py_multi.py': ['openai', 'torch'],
  'py_from.py': ['anthropic', 'langchain'],
  'py_plain.py': ['anthropic'],
  'mock.js': [],
  'relative.ts': [],
  'commented.js': [],
  'py_negative.py': []
};

let dir;
let result;
const libsFor = (name) => [...(result.aiLibraryMatches[path.join(dir, name)] ?? [])].sort();

beforeAll(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h4-'));
  for (const [name, content] of Object.entries(FILES)) fs.writeFileSync(path.join(dir, name), content);
  result = Scanners.scanCodebase({ root: dir });
});
afterAll(() => fs.rmSync(dir, { recursive: true, force: true }));

describe('lab h4: LLM SDK detection', () => {
  it('keeps the result shape', () => {
    expect(Object.keys(result).sort()).toEqual(['aiFiles', 'aiFunctionMatches', 'aiLibraryMatches', 'totalFiles']);
    expect(result.totalFiles).toBe(Object.keys(FILES).length);
  });

  it.each(Object.entries(EXPECTED))('%s', (name, libs) => {
    expect(libsFor(name)).toEqual(libs);
    if (libs.length) expect(result.aiFiles).toContain(path.join(dir, name));
  });

  it('records each library once per file', () => {
    for (const libs of Object.values(result.aiLibraryMatches)) {
      expect(new Set(libs).size).toBe(libs.length);
    }
  });
});

describe('lab h4: other entry points into the scanner', () => {
  it('detects the support-triage demo', () => {
    const demo = path.join(path.dirname(new URL(import.meta.url).pathname), 'lab_h4_demo');
    const scan = Scanners.scanCodebase({ root: demo });
    expect(scan.aiFiles).toEqual([path.join(demo, 'src', 'triage.js')]);
    expect(scan.aiLibraryMatches[path.join(demo, 'src', 'triage.js')]).toEqual(['openai']);
  });

  it('keeps custom library lists working with the same matching rules', () => {
    const custom = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h4-custom-'));
    try {
      fs.writeFileSync(path.join(custom, 'a.ts'), "import fancy from 'fancy-ml/sub';\nexport default fancy;\n");
      fs.writeFileSync(path.join(custom, 'b.ts'), "import other from 'fancy-ml-extra';\nimport ai from 'openai';\nexport default [other, ai];\n");
      const scan = Scanners.createScanner({ detectors: [createLibraryDetector(['fancy-ml'])] })({ root: custom });
      expect(scan.aiLibraryMatches).toEqual({ [path.join(custom, 'a.ts')]: ['fancy-ml'] });
      expect(scan.aiFiles).toEqual([path.join(custom, 'a.ts')]);
    } finally {
      fs.rmSync(custom, { recursive: true, force: true });
    }
  });
});
