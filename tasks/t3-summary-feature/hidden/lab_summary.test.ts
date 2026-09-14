// Hidden acceptance tests for t3. Copied in at grading time only.
import { describe, expect, it } from 'vitest';
import { renderSummary } from './gate/report.js';
import type { GateResult, Finding } from './gate/schema.js';

const f = (checkId: string, severity: 'block' | 'warn'): Finding => ({ checkId, severity, message: 'm', source: 'validator' });
const result = (verdict: GateResult['verdict'], findings: Finding[]): GateResult => ({ verdict, tier: null, findings, gateSection: '## FRAI Gate' });

describe('lab contract: renderSummary', () => {
  it('passes with all checks answered', () => {
    expect(renderSummary(result('PASS', []))).toBe('PASS 7/7');
  });
  it('warnings do not reduce answered', () => {
    expect(renderSummary(result('WARN', [f('evaluation', 'warn')]))).toBe('WARN 7/7');
  });
  it('lists blocked checks once, in GATE_CHECKS order', () => {
    const r = result('BLOCK', [f('transparency', 'block'), f('evaluation', 'block'), f('evaluation', 'block'), f('bias', 'warn')]);
    expect(renderSummary(r)).toBe('BLOCK 5/7: evaluation, transparency');
  });
  it('handles a missing gate section', () => {
    expect(renderSummary({ verdict: 'BLOCK', tier: null, findings: [f('structure', 'block')], gateSection: null })).toBe('BLOCK 0/7: structure');
  });
});
