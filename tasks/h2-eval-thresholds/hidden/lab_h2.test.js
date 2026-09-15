// Hidden acceptance tests for h2-eval-thresholds (frai-core API). Copied in at grading time only.
import fs from 'fs';
import os from 'os';
import path from 'path';
import { describe, expect, it } from 'vitest';

import { Eval } from './index.js';

const byMetric = (report, id) => (report.thresholds ?? []).find((t) => t.metric === id);
/** Text of the Markdown "Thresholds" section, split per metric: { metricId: text up to the next metric }. */
const thresholdSection = (md, ids) => {
  const lines = md.split('\n');
  const start = lines.findIndex((l) => /^(#+\s|\*\*).*threshold/i.test(l));
  if (start === -1) return null;
  const rest = lines.slice(start + 1);
  const end = rest.findIndex((l) => /^#{1,2}\s|^---\s*$/.test(l));
  const text = (end === -1 ? rest : rest.slice(0, end)).join('\n');
  const at = ids.map((id) => [id, text.indexOf(id)]).filter(([, i]) => i >= 0).sort((a, b) => a[1] - b[1]);
  return Object.fromEntries(at.map(([id, i], k) => [id, text.slice(i, k + 1 < at.length ? at[k + 1][1] : text.length)]));
};
const report = (evaluations, thresholds) =>
  Eval.generateReport({
    evaluations,
    outputsPath: '/tmp/outputs.json',
    referencesPath: '/tmp/references.json',
    generatedAt: '2026-01-01T00:00:00.000Z',
    ...(thresholds === undefined ? {} : { thresholds })
  });
// exact_match 0.5 (one of two matches), length_variance 1 (same lengths)
const scored = () => Eval.runEvaluations({ outputs: ['Hello', 'World'], references: ['hello', 'there'] });

describe('lab h2: generateReport thresholds', () => {
  it('leaves reports without thresholds exactly as before', () => {
    const r = report(scored());
    expect(Object.keys(r).sort()).toEqual(['metadata', 'metrics']);
    expect(r.metadata).toEqual({
      generatedAt: '2026-01-01T00:00:00.000Z',
      outputsPath: '/tmp/outputs.json',
      referencesPath: '/tmp/references.json',
      totalSamples: 2
    });
  });

  it('records one entry per threshold and passes when every score reaches its minimum', () => {
    const r = report(scored(), { exact_match: 0.5, length_variance: 0.9 });
    expect(r.passed).toBe(true);
    expect(r.thresholds).toHaveLength(2);
    expect(byMetric(r, 'exact_match')).toMatchObject({ metric: 'exact_match', min: 0.5, score: 0.5, passed: true });
    expect(byMetric(r, 'length_variance')).toMatchObject({ metric: 'length_variance', min: 0.9, score: 1, passed: true });
    expect(r.metrics).toEqual(scored());
  });

  it('fails when any score is below its minimum', () => {
    const r = report(scored(), { length_variance: 0.9, exact_match: 0.75 });
    expect(r.passed).toBe(false);
    expect(byMetric(r, 'exact_match')).toMatchObject({ metric: 'exact_match', min: 0.75, score: 0.5, passed: false });
    expect(byMetric(r, 'length_variance').passed).toBe(true);
  });

  it('fails a threshold whose metric has no score, even with a minimum of 0', () => {
    const evaluations = Eval.runEvaluations({ outputs: ['a', 'b'] });
    const r = report(evaluations, { exact_match: 0 });
    expect(r.passed).toBe(false);
    expect(byMetric(r, 'exact_match')).toMatchObject({ metric: 'exact_match', min: 0, score: null, passed: false });
  });

  it('works for custom metrics passed to runEvaluations', () => {
    const custom = () => ({ id: 'citation_rate', label: 'Citation rate', score: 0.7, total: 2 });
    const evaluations = Eval.runEvaluations({ outputs: ['a', 'b'], references: ['a', 'b'], metrics: [custom] });
    expect(report(evaluations, { citation_rate: 0.6 }).passed).toBe(true);
    const failing = report(evaluations, { citation_rate: 0.8 });
    expect(failing.passed).toBe(false);
    expect(byMetric(failing, 'citation_rate')).toMatchObject({ metric: 'citation_rate', min: 0.8, score: 0.7, passed: false });
  });

  it('writes threshold outcomes to JSON and Markdown reports', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lab-h2-'));
    try {
      const r = report(scored(), { exact_match: 0.75, length_variance: 0.9 });
      const jsonPath = Eval.writeReport({ report: r, format: 'json', reportPath: path.join(dir, 'r.json') });
      const saved = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
      expect(saved.passed).toBe(false);
      expect(saved.thresholds).toHaveLength(2);

      const mdPath = Eval.writeReport({ report: r, format: 'markdown', reportPath: path.join(dir, 'r.md') });
      const md = fs.readFileSync(mdPath, 'utf8');
      const section = thresholdSection(md, ['exact_match', 'length_variance']);
      expect(section).not.toBeNull();
      expect(section.exact_match).toMatch(/FAIL/);
      expect(section.exact_match).not.toMatch(/PASS/);
      expect(section.length_variance).toMatch(/PASS/);

      const plain = Eval.writeReport({ report: report(scored()), format: 'markdown', reportPath: path.join(dir, 'p.md') });
      expect(fs.readFileSync(plain, 'utf8')).not.toMatch(/threshold/i);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
