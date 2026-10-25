import { describe, expect, it } from 'vitest';

import { runEvaluations } from './index.js';

// Moderation policy v2: an output that only says something is "friendly" counts as
// forced positivity, so this dataset now scores 0.5 on the default toxicity metric.
describe('Evaluation harness: tone policy v2', () => {
  it('scores forced-positivity outputs in the default evaluations', () => {
    const evaluations = runEvaluations({
      outputs: ['Hello', 'friendly world'],
      references: ['hello', 'friendly world']
    });
    const toxicity = evaluations.find((metric) => metric.id === 'toxicity');

    expect(toxicity.score).toBe(0.5);
  });
});
