// Hidden acceptance tests for h1-draft-check. Copied in at grading time only.
import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateSpec } from './gate/validate.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = (name: string) => fs.readFileSync(path.join(here, 'lab_h1_fixtures', name), 'utf8');
const GATE_IDS = ['risk-tier', 'data-privacy', 'oversight', 'evaluation', 'bias', 'monitoring', 'transparency'];
const blocksFor = (r: ReturnType<typeof validateSpec>) =>
  [...new Set(r.findings.filter((f) => f.severity === 'block').map((f) => f.checkId))].sort();

/** A fully answered gate in the drafter's `**Label:** value` style; override any subsection by key. */
function colonSpec(overrides: Partial<Record<string, string>> = {}): string {
  const s: Record<string, string> = {
    tier: `### Risk tier

- **Tier:** **limited**
- **Justification:** Chatbot answering policy questions; no automated decisions about people.
- **Sign-off:** not required (tier below high)`,
    data: `### Data provenance & privacy

- **Data sources:** internal policy docs; user questions at runtime
- **PII involved?** no
- **Retention:** prompts kept 30 days, then hard-deleted
- **Used for training?** no; provider training disabled`,
    oversight: `### Human oversight

- **Automation level:** assistive
- **Override path:** support team can correct answers via admin panel
- **Kill switch:** feature flag chat_enabled, ops on-call, off within 5 minutes`,
    evaluation: `### Evaluation plan

- **Pre-ship metrics & thresholds:** groundedness >= 0.85; refusal rate <= 2%
- **Eval dataset:** eval/policy-qa.jsonl, 300 questions from real support tickets
- **Who runs it and when:** CI on every prompt change`,
    bias: `### Bias & fairness

- **Groups at risk of disparate impact:** non-native English speakers
- **Mitigations:** multilingual eval slice; simplified-language prompt rule
- **How tested:** disaggregated groundedness by question language`,
    monitoring: `### Monitoring & rollback

- **Production monitoring:** thumbs-down rate, refusal rate, latency
- **Degradation definition:** thumbs-down > 10% over 24h
- **Rollback trigger & procedure:** on-call flips chat_enabled off; users see the legacy FAQ`,
    transparency: `### Transparency & incident response

- **User disclosure:** "AI assistant" label in the chat header
- **Incident owner:** Dana Rivers (support-eng rotation)
- **Incident path:** in-chat report -> triage queue -> fix or disable, response within 24h`
  };
  Object.assign(s, overrides);
  return `# Spec: Policy Chatbot\n\n## 1. Objective\n\nAnswer policy questions.\n\n## Responsible AI Gate\n\n${Object.values(s).join('\n\n')}\n\n## 6. Rollout\n\nLater.\n`;
}

describe('lab h1: the reference draft from frai-gate draft', () => {
  it('blocks the raw draft only because of its open NEEDS HUMAN INPUT items', () => {
    const r = validateSpec(fixture('draft-raw.md'));
    expect(r.verdict).toBe('BLOCK');
    expect(r.tier).toBe('limited');
    expect(r.findings.filter((f) => /unanswered field/i.test(f.message))).toEqual([]);
    expect(r.findings.filter((f) => /must be one of/i.test(f.message))).toEqual([]);
    expect(blocksFor(r)).toEqual([...GATE_IDS].sort());
  });

  it('passes the same draft once a person has resolved every NEEDS HUMAN INPUT item', () => {
    const r = validateSpec(fixture('draft-resolved.md'));
    expect(r.findings).toEqual([]);
    expect(r.verdict).toBe('PASS');
    expect(r.tier).toBe('limited');
  });
});

describe('lab h1: label styles', () => {
  it('passes a complete gate written with **Label:** value', () => {
    const r = validateSpec(colonSpec());
    expect(r.findings).toEqual([]);
    expect(r.verdict).toBe('PASS');
    expect(r.tier).toBe('limited');
  });

  it('still blocks an empty **Label:** field', () => {
    const r = validateSpec(
      colonSpec({
        data: `### Data provenance & privacy

- **Data sources:** internal policy docs
- **PII involved?** no
- **Retention:**
- **Used for training?** no`
      })
    );
    expect(r.verdict).toBe('BLOCK');
    expect(blocksFor(r)).toEqual(['data-privacy']);
    expect(r.findings.some((f) => f.checkId === 'data-privacy' && /unanswered field/i.test(f.message))).toBe(true);
  });

  it('still blocks an empty **Label**: field followed directly by the next field', () => {
    const r = validateSpec(
      colonSpec({
        oversight: `### Human oversight

- **Automation level**: assistive
- **Override path**:
- **Kill switch**: feature flag chat_enabled, off within 5 minutes`
      })
    );
    expect(blocksFor(r)).toEqual(['oversight']);
    expect(r.findings.filter((f) => /unanswered field/i.test(f.message))).toHaveLength(1);
  });

  it('still blocks an empty last field before the next heading, in both styles', () => {
    const r = validateSpec(
      colonSpec({
        transparency: `### Transparency & incident response

- **User disclosure:** "AI assistant" label in the chat header
- **Incident owner**:
- **Incident path:**`
      })
    );
    expect(blocksFor(r)).toEqual(['transparency']);
    expect(r.findings.filter((f) => /unanswered field/i.test(f.message))).toHaveLength(2);
  });
});

describe('lab h1: answers on the lines below a field', () => {
  it('accepts nested bullets and an indented table, with blank lines in between', () => {
    const r = validateSpec(
      colonSpec({
        evaluation: `### Evaluation plan

- **Pre-ship metrics & thresholds** (all suggested):

  | Metric | Threshold |
  |---|---|
  | groundedness | >= 0.85 |

- **Eval dataset:**
  - eval/policy-qa.jsonl
  - 300 questions from real support tickets
- **Who runs it and when**:

    CI on every prompt change, plus a monthly re-run.`
      })
    );
    expect(r.findings).toEqual([]);
    expect(r.verdict).toBe('PASS');
  });

  it('reads a Tier value from the line below the field', () => {
    const r = validateSpec(
      colonSpec({
        tier: `### Risk tier

- **Tier:**
  - limited
- **Justification:** re-run at high if tickets can carry medical content; minimal is too low.
- **Sign-off:** not required (tier below high)`
      })
    );
    expect(r.tier).toBe('limited');
    expect(r.findings).toEqual([]);
  });

  it('reads a bold high Tier despite other tier words, and a sign-off given on the line below', () => {
    const r = validateSpec(
      colonSpec({
        tier: `### Risk tier

- **Tier:** **high**
- **Justification:** screens job applicants; not limited or minimal because it affects livelihoods.
- **Sign-off:**
  - Ana Pop (Head of Compliance), 2026-08-01`
      })
    );
    expect(r.tier).toBe('high');
    expect(r.findings.filter((f) => f.checkId === 'risk-tier')).toEqual([]);
  });

  it('still blocks high risk whose sign-off says not required, in the new style', () => {
    const r = validateSpec(
      colonSpec({
        tier: `### Risk tier

- **Tier:** **high**
- **Justification:** screens job applicants automatically.
- **Sign-off:** not required (tier below high)`
      })
    );
    expect(r.tier).toBe('high');
    expect(r.verdict).toBe('BLOCK');
    expect(blocksFor(r)).toEqual(['risk-tier']);
  });

  it('still blocks high risk with an empty sign-off', () => {
    const r = validateSpec(
      colonSpec({
        tier: `### Risk tier

- **Tier:** high
- **Justification:** screens job applicants automatically.
- **Sign-off:**`
      })
    );
    expect(r.verdict).toBe('BLOCK');
    expect(blocksFor(r)).toEqual(['risk-tier']);
  });
});

describe('lab h1: NEEDS HUMAN INPUT', () => {
  it('blocks only the check that still has an open item, even inside a nested bullet', () => {
    const r = validateSpec(
      colonSpec({
        bias: `### Bias & fairness

- **Groups at risk of disparate impact:** non-native English speakers
  - **NEEDS HUMAN INPUT:** which slices may lawfully be built?
- **Mitigations:** multilingual eval slice
- **How tested:** disaggregated groundedness by question language`
      })
    );
    expect(r.verdict).toBe('BLOCK');
    expect(blocksFor(r)).toEqual(['bias']);
  });
});

describe('lab h1: no regressions', () => {
  it('reports exactly the same findings on the untouched spec template', () => {
    const expected = JSON.parse(fixture('template-findings.json'));
    const r = validateSpec(fixture('template.md'));
    expect(r.verdict).toBe(expected.verdict);
    expect(r.tier).toBe(expected.tier);
    expect(r.findings).toEqual(expected.findings);
  });

  it('keeps the example specs passing', () => {
    for (const name of ['example-policy-chatbot.md', 'example-support-triage.md']) {
      const r = validateSpec(fixture(name));
      expect(r.findings).toEqual([]);
      expect(r.verdict).toBe('PASS');
      expect(r.tier).toBe('limited');
    }
  });
});
