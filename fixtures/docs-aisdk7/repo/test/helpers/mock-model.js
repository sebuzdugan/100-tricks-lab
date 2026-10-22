// Scripted mock language model for tests (AI SDK 7, LanguageModelV4 spec). No network, no API key.
//
//   const model = scriptedModel([
//     { toolCalls: [{ name: 'someTool', input: { id: 'X1' } }], usage: [100, 7] }, // step 1: the model calls a tool
//     { text: 'All done.', usage: [200, 9] },                                     // step 2: the model answers
//   ]);
//
// Each entry is one model response, used in order (the last one repeats if the model is called again).
// `usage` is [inputTokens, outputTokens] (default [10, 5]). For streaming, `chunks` splits the text into deltas.
// `model.calls` records the options of every model call (prompt, tools, responseFormat, ...).
//
// The usage and finish-reason objects below are the provider-level (LanguageModelV4) shapes a real provider returns.
// The SDK converts them: the results of generateText/streamText report finishReason as a string and token
// counts as numbers, as they do with a real model.
import { MockLanguageModelV4, convertArrayToReadableStream } from 'ai/test';

const usageOf = ([input, output] = [10, 5]) => ({
  inputTokens: { total: input, noCache: input, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: output, text: output, reasoning: 0 },
});
const finish = (reason) => ({ unified: reason, raw: reason });

export function scriptedModel(steps) {
  let i = 0;
  const calls = [];
  const next = () => steps[Math.min(i++, steps.length - 1)];
  const model = new MockLanguageModelV4({
    doGenerate: async (options) => {
      calls.push(options);
      const step = next();
      if (step.toolCalls) {
        return {
          content: step.toolCalls.map((c, k) => ({ type: 'tool-call', toolCallId: `call-${i}-${k}`, toolName: c.name, input: JSON.stringify(c.input) })),
          finishReason: finish('tool-calls'), usage: usageOf(step.usage), warnings: [],
        };
      }
      return { content: [{ type: 'text', text: step.text }], finishReason: finish('stop'), usage: usageOf(step.usage), warnings: [] };
    },
    doStream: async (options) => {
      calls.push(options);
      const step = next();
      const parts = [{ type: 'stream-start', warnings: [] }];
      if (step.toolCalls) {
        step.toolCalls.forEach((c, k) => parts.push({ type: 'tool-call', toolCallId: `call-${i}-${k}`, toolName: c.name, input: JSON.stringify(c.input) }));
      } else {
        parts.push({ type: 'text-start', id: 't' });
        for (const delta of step.chunks ?? [step.text]) parts.push({ type: 'text-delta', id: 't', delta });
        parts.push({ type: 'text-end', id: 't' });
      }
      parts.push({ type: 'finish', finishReason: finish(step.toolCalls ? 'tool-calls' : 'stop'), usage: usageOf(step.usage) });
      return { stream: convertArrayToReadableStream(parts) };
    },
  });
  model.calls = calls;
  return model;
}
