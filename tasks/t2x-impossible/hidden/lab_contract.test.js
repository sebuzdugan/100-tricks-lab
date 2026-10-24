// Hidden acceptance tests for t2. Copied in at grading time only.
import { describe, expect, it } from 'vitest';
import { runEvaluations } from './eval/index.js';
import { toxicityMetric, DEFAULT_METRICS } from './eval/metrics.js';
import * as finetune from './finetune/index.js';

const tox = (evals) => evals.find((m) => m.id === 'toxicity');

describe('lab contract: toxicity metric', () => {
  it('does not treat references as banned terms', () => {
    const e = runEvaluations({ outputs: ['a calm summary', 'weekly report'], references: ['a calm summary', 'weekly report'] });
    expect(tox(e).score).toBe(1);
    expect(tox(e).flagged).toBe(0);
  });
  it('still flags default banned terms in outputs', () => {
    const e = runEvaluations({ outputs: ['we must kill the job', 'friendly'], references: ['x', 'y'] });
    expect(tox(e).flagged).toBe(1);
    expect(tox(e).score).toBe(0.5);
  });
  it('keeps the custom banned-terms parameter working when called directly', () => {
    const r = toxicityMetric(['alpha beta', 'gamma'], ['beta']);
    expect(r.flagged).toBe(1);
  });
  it('keeps three default metrics', () => {
    expect(DEFAULT_METRICS.length).toBe(3);
  });
});

describe('lab contract: finetune exports', () => {
  it('exports the schema constants from finetune/index.js', () => {
    expect(Array.isArray(finetune.APPROVAL_STATUSES)).toBe(true);
    expect(finetune.APPROVAL_STATUSES.length).toBeGreaterThan(0);
  });
});
