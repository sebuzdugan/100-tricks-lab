Docs for the Vercel AI SDK 7 (ai 7.0.128), copied from ai-sdk.dev:

=== https://ai-sdk.dev/docs/ai-sdk-core/generating-text ===

Large language models (LLMs) can generate text in response to a prompt, which can contain instructions and information to process.
For example, you can ask a model to come up with a recipe, draft an email, or summarize a document.

The AI SDK Core provides two functions to generate text and stream it from LLMs:

- [`generateText`](#generatetext): Generates text for a given prompt and model.
- [`streamText`](#streamtext): Streams text from a given prompt and model.

Advanced LLM features such as [tool calling](./tools-and-tool-calling) and [structured data generation](./generating-structured-data) are built on top of text generation.

## `generateText`

You can generate text using the [`generateText`](/docs/reference/ai-sdk-core/generate-text) function. This function is ideal for non-interactive use cases where you need to write text (e.g. drafting email or summarizing web pages) and for agents that use tools.

```tsx
import { generateText } from 'ai';

const { text } = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Write a vegetarian lasagna recipe for 4 people.',
});
```

You can use more [advanced prompts](/docs/foundations/prompts) to generate text with more complex instructions and content:

```tsx
import { generateText } from 'ai';

const { text } = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  instructions:
    'You are a professional writer. ' +
    'You write simple, clear, and concise content.',
  prompt: `Summarize the following article in 3-5 sentences: ${article}`,
});
```

The result object of `generateText` contains the generated output and metadata:

- `result.content`: The content that was generated in all steps.
- `result.text`: The generated text from the final step.
- `result.files`: The files that were generated in all steps.
- `result.sources`: Sources that have been used as references in all steps (only available for some models).
- `result.toolCalls`: The tool calls that were made in all steps.
- `result.toolResults`: The results of the tool calls from all steps.
- `result.finishReason`: The reason the model finished generating text.
- `result.rawFinishReason`: The raw reason why the generation finished (from the provider).
- `result.usage`: The total usage across all steps (for multi-step generations).
- `result.warnings`: Warnings from the model provider in all steps (e.g. unsupported settings).
- `result.steps`: Details for all steps, useful for getting information about intermediate steps, including per-step `performance`.
- `result.finalStep`: Details for the final step, including `performance`.
- `result.output`: The generated structured output using the `output` specification.

Each step includes `performance` with timing and throughput information:

- `effectiveOutputTokensPerSecond`: Effective output tokens per second, calculated as `outputTokens / requestSeconds`.
- `outputTokensPerSecond`: For streaming steps, output tokens per second after the first generated output chunk, calculated as `outputTokens / outputStreamSeconds`. For `generateText`, this is `undefined`.
- `inputTokensPerSecond`: For streaming steps, input tokens per second before the first generated output chunk, calculated as `inputTokens / ttftSeconds`. For `generateText`, this is `undefined`.
- `effectiveTotalTokensPerSecond`: Effective total tokens per second, calculated as `(inputTokens + outputTokens) / requestSeconds`.
- `stepTimeMs`: Total time spent on the step, including language model response time and tool execution time, in milliseconds.
- `responseTimeMs`: Time spent waiting for the language model response in milliseconds.
- `toolExecutionMs`: Time spent executing each client-side tool call in the step in milliseconds, keyed by tool call ID.
- `timeToFirstOutputMs`: For streaming steps, the time until the first generated output chunk was received in milliseconds. For `generateText`, this is `undefined`.
- `timeBetweenOutputChunksMs`: For streaming steps with at least two output chunks, timing statistics for the gaps between generated output chunks in milliseconds.

### Accessing response headers & body

Sometimes you need access to the full response from the model provider,
e.g. to access some provider-specific headers or body content.

You can access the raw response headers and body using the `finalStep.response` property:

```ts
import { generateText } from 'ai';

const result = await generateText({
  // ...
});

console.log(JSON.stringify(result.finalStep.response.headers, null, 2));
console.log(JSON.stringify(result.finalStep.response.body, null, 2));
```

### `onEnd` callback

When using `generateText`, you can provide an `onEnd` callback that is triggered after the last step is finished (
[API Reference](/docs/reference/ai-sdk-core/generate-text#on-end)
).
It contains the text, usage information, finish reason, messages, steps, total usage, and more:

```tsx {7-10}
import { generateText } from 'ai';

const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
  onEnd({ text, finishReason, usage, responseMessages, steps, totalUsage }) {
    // your own logic, e.g. for saving the chat history or recording usage

    const messages = responseMessages; // messages that were generated
  },
});
```

### Lifecycle callbacks (experimental)

Experimental callbacks are subject to breaking changes in incremental package
releases.

`generateText` provides several experimental lifecycle callbacks that let you hook into different phases of the generation process.
These are useful for logging, observability, debugging, and custom telemetry.
Errors thrown inside these callbacks are silently caught and do not break the generation flow.

```tsx
import { generateText } from 'ai';

const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'What is the weather in San Francisco?',
  tools: {
    // ... your tools
  },

  onStart({ modelId }) {
    console.log('Generation started', { modelId });
  },

  onStepStart({ stepNumber, modelId, messages }) {
    console.log(`Step ${stepNumber} starting`, { modelId });
  },

  onLanguageModelCallStart({ modelId, messages }) {
    console.log('Model call starting', {
      modelId,
      messageCount: messages.length,
    });
  },

  onLanguageModelCallEnd({ modelId, finishReason, content }) {
    console.log('Model call finished', {
      modelId,
      finishReason,
      contentParts: content.length,
    });
  },

  onToolExecutionStart({ toolCall }) {
    console.log(`Tool call starting: ${toolCall.toolName}`, {
      toolCallId: toolCall.toolCallId,
    });
  },

  onToolExecutionEnd({ toolCall, toolExecutionMs, toolOutput }) {
    console.log(
      `Tool call finished: ${toolCall.toolName} (${toolExecutionMs}ms)`,
      {
        success: toolOutput.type === 'tool-result',
      },
    );
  },

  onStepEnd({ stepNumber, finishReason, usage, performance }) {
    console.log(`Step ${stepNumber} finished`, {
      finishReason,
      usage,
      performance,
    });
  },
});
```

The available lifecycle callbacks are:

- **`onStart`**: Called once when the `generateText` operation begins, before any LLM calls. Receives model info, messages, settings, and `runtimeContext`.
- **`onStepStart`**: Called before each step (LLM call). Receives the step number, model, messages being sent, tools, and prior steps.
- **`onLanguageModelCallStart`**: Called immediately before the provider model call begins. Useful when you want to observe the model invocation separately from later tool execution.
- **`onLanguageModelCallEnd`**: Called after the model response has been normalized and parsed, but before any client-side tool execution begins. Receives the model-call content parts, usage, finish reason, and provider metadata.
- **`onToolExecutionStart`**: Called right before a tool's `execute` function runs. Receives the tool call object, messages, and `toolContext`.
- **`onToolExecutionEnd`**: Called right after a tool's `execute` function completes or errors. Receives the tool call object, `toolExecutionMs`, and a `toolOutput` discriminated union (`type: 'tool-result'` with `output`, or `type: 'tool-error'` with `error`).
- **`onStepEnd`**: Called after each step finishes. Includes `stepNumber` (zero-based index of the completed step).

## `streamText`

Depending on your model and prompt, it can take a large language model (LLM) up to a minute to finish generating its response. This delay can be unacceptable for interactive use cases such as chatbots or real-time applications, where users expect immediate responses.

AI SDK Core provides the [`streamText`](/docs/reference/ai-sdk-core/stream-text) function which simplifies streaming text from LLMs:

```ts
import { streamText } from 'ai';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
});

// example: use textStream as an async iterable
for await (const textPart of result.textStream) {
  console.log(textPart);
}
```

`result.textStream` is both a `ReadableStream` and an `AsyncIterable`.

`streamText` immediately starts streaming and suppresses errors to prevent
server crashes. Use the `onError` callback to log errors.

You can use `streamText` on its own or in combination with [AI SDK
UI](/examples/next-pages/basics/streaming-text-generation) and [AI SDK
RSC](/examples/next-app/basics/streaming-text-generation).
The `result.stream` can be passed to several standalone helpers to make the integration into [AI SDK UI](/docs/ai-sdk-ui) easier:

- `createUIMessageStreamResponse({ stream: toUIMessageStream({ stream: result.stream }) })`: Creates a UI Message stream HTTP response (with tool calls etc.) that can be used in a Next.js App Router API route.
- `pipeUIMessageStreamToResponse({ stream: toUIMessageStream({ stream: result.stream }), response })`: Writes UI Message stream delta output to a Node.js response-like object.
- `createTextStreamResponse({ stream: toTextStream({ stream: result.stream }) })`: Creates a simple text stream HTTP response.
- `pipeTextStreamToResponse({ stream: toTextStream({ stream: result.stream }), response })`: Writes text delta output to a Node.js response-like object.

`streamText` is using backpressure and only generates tokens as they are
requested. You need to consume the stream in order for it to finish.

It also provides several promises that resolve when the stream is finished:

- `result.content`: The content that was generated in all steps.
- `result.text`: The generated text from the final step.
- `result.finalStep`: Details for the final step, including per-step `performance`.
- `result.files`: Files that have been generated by the model in all steps.
- `result.sources`: Sources that have been used as references in all steps (only available for some models).
- `result.toolCalls`: The tool calls that have been executed in all steps.
- `result.toolResults`: The tool results that have been generated in all steps.
- `result.finishReason`: The reason the model finished generating text.
- `result.rawFinishReason`: The raw reason why the generation finished (from the provider).
- `result.usage`: The total usage across all steps (for multi-step generations).
- `result.totalUsage`: Deprecated. Use `result.usage` instead.
- `result.warnings`: Warnings from the model provider in all steps (e.g. unsupported settings).
- `result.steps`: Details for all steps, useful for getting information about intermediate steps, including per-step `performance`.

For `streamText`, `timeToFirstOutputMs` is set when the first generated output chunk is received for a step. `timeBetweenOutputChunksMs` includes `min`, `p10`, `median`, `avg`, `p90`, and `max` when at least two output chunks are received.

### `onError` callback

`streamText` immediately starts streaming to enable sending data without waiting for the model.
Errors become part of the stream and are not thrown to prevent e.g. servers from crashing.

To log errors, you can provide an `onError` callback that is triggered when an error occurs.

```tsx {7-9}
import { streamText } from 'ai';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
  onError({ error }) {
    console.error(error); // your error logging logic here
  },
});
```

### `onChunk` callback

When using `streamText`, you can provide an `onChunk` callback that is triggered for each chunk of the stream.

It receives all stream part types from `stream`, including:

- `start`
- `start-step`
- `text-start`
- `text-delta`
- `text-end`
- `reasoning-start`
- `reasoning-delta`
- `reasoning-end`
- `custom`
- `source`
- `file`
- `reasoning-file`
- `tool-call`
- `tool-input-start`
- `tool-input-delta`
- `tool-input-end`
- `tool-result`
- `tool-error`
- `tool-output-denied`
- `tool-approval-request`
- `tool-approval-response`
- `finish-step`
- `finish`
- `abort`
- `error`
- `raw`

```tsx {7-12}
import { streamText } from 'ai';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
  onChunk({ chunk }) {
    // implement your own logic here, e.g.:
    if (chunk.type === 'text-delta') {
      console.log(chunk.text);
    }
  },
});
```

### `onEnd` callback

When using `streamText`, you can provide an `onEnd` callback that is triggered when the stream is finished (
[API Reference](/docs/reference/ai-sdk-core/stream-text#on-end)
).
It contains the text, usage information, finish reason, messages, steps, total usage, and more:

```tsx {7-10}
import { streamText } from 'ai';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
  onEnd({ text, finishReason, usage, responseMessages, steps, totalUsage }) {
    // your own logic, e.g. for saving the chat history or recording usage

    const messages = responseMessages; // messages that were generated
  },
});
```

### Lifecycle callbacks (experimental)

Experimental callbacks are subject to breaking changes in incremental package
releases.

`streamText` provides several experimental lifecycle callbacks that let you hook into different phases of the streaming process.
These are useful for logging, observability, debugging, and custom telemetry.
Errors thrown inside these callbacks are silently caught and do not break the streaming flow.

```tsx
import { streamText } from 'ai';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'What is the weather in San Francisco?',
  tools: {
    // ... your tools
  },

  onStart({ modelId, instructions, messages }) {
    console.log('Streaming started', { modelId });
  },

  onStepStart({ stepNumber, modelId, messages }) {
    console.log(`Step ${stepNumber} starting`, { modelId });
  },

  onLanguageModelCallStart({ modelId, messages }) {
    console.log('Model call starting', {
      modelId,
      messageCount: messages.length,
    });
  },

  onLanguageModelCallEnd({ modelId, finishReason, content }) {
    console.log('Model call finished', {
      modelId,
      finishReason,
      contentParts: content.length,
    });
  },

  onToolExecutionStart({ toolCall }) {
    console.log(`Tool call starting: ${toolCall.toolName}`, {
      toolCallId: toolCall.toolCallId,
    });
  },

  onToolExecutionEnd({ toolCall, toolExecutionMs, toolOutput }) {
    console.log(
      `Tool call finished: ${toolCall.toolName} (${toolExecutionMs}ms)`,
      {
        success: toolOutput.type === 'tool-result',
      },
    );
  },

  onStepEnd({ finishReason, usage }) {
    console.log('Step finished', { finishReason, usage });
  },
});
```

The available lifecycle callbacks are:

- **`onStart`**: Called once when the `streamText` operation begins, before any LLM calls. Receives model info, messages, settings, and `runtimeContext`.
- **`onStepStart`**: Called before each step (LLM call). Receives the step number, model, messages being sent, tools, and prior steps.
- **`onLanguageModelCallStart`**: Called immediately before the provider model call begins. Useful when you want to observe the model invocation separately from later tool execution.
- **`onLanguageModelCallEnd`**: Called after the model response has been normalized and parsed, but before any client-side tool execution begins. Receives the model-call content parts, usage, finish reason, and provider metadata.
- **`onToolExecutionStart`**: Called right before a tool's `execute` function runs. Receives the tool call object, messages, and `toolContext`.
- **`onToolExecutionEnd`**: Called right after a tool's `execute` function completes or errors. Receives the tool call object, `toolExecutionMs`, and a `toolOutput` discriminated union (`type: 'tool-result'` with `output`, or `type: 'tool-error'` with `error`).
- **`onStepEnd`**: Called after each step finishes. Receives the finish reason, usage, and other step details.

### `stream` property

You can read a stream with all events using the `stream` property.
This can be useful if you want to implement your own UI or handle the stream in a different way.
Here is an example of how to use the `stream` property:

```tsx
import { streamText } from 'ai';
import { z } from 'zod';

const result = streamText({
  model: "anthropic/claude-sonnet-5.5",
  tools: {
    cityAttractions: {
      inputSchema: z.object({ city: z.string() }),
      execute: async ({ city }) => ({
        attractions: ['attraction1', 'attraction2', 'attraction3'],
      }),
    },
  },
  prompt: 'What are some San Francisco tourist attractions?',
});

for await (const part of result.stream) {
  switch (part.type) {
    case 'start': {
      // handle start of stream
      break;
    }
    case 'start-step': {
      // handle start of step
      break;
    }
    case 'text-start': {
      // handle text start
      break;
    }
    case 'text-delta': {
      // handle text delta here
      break;
    }
    case 'text-end': {
      // handle text end
      break;
    }
    case 'reasoning-start': {
      // handle reasoning start
      break;
    }
    case 'reasoning-delta': {
      // handle reasoning delta here
      break;
    }
    case 'reasoning-end': {
      // handle reasoning end
      break;
    }
    case 'source': {
      // handle source here
      break;
    }
    case 'file': {
      // handle file here
      break;
    }
    case 'tool-call': {
      switch (part.toolName) {
        case 'cityAttractions': {
          // handle tool call here
          break;
        }
      }
      break;
    }
    case 'tool-input-start': {
      // handle tool input start
      break;
    }
    case 'tool-input-delta': {
      // handle tool input delta
      break;
    }
    case 'tool-input-end': {
      // handle tool input end
      break;
    }
    case 'tool-result': {
      switch (part.toolName) {
        case 'cityAttractions': {
          // handle tool result here
          break;
        }
      }
      break;
    }
    case 'tool-error': {
      // handle tool error
      break;
    }
    case 'finish-step': {
      // handle finish step
      break;
    }
    case 'finish': {
      // handle finish here
      break;
    }
    case 'error': {
      // handle error here
      break;
    }
    case 'raw': {
      // handle raw value
      break;
    }
  }
}
```

### Stream transformation

You can use the `experimental_transform` option to transform the stream.
This is useful for e.g. filtering, changing, or smoothing the text stream.

The transformations are applied before the callbacks are invoked and the promises are resolved.
If you e.g. have a transformation that changes all text to uppercase, the `onEnd` callback will receive the transformed text.

#### Smoothing streams

The AI SDK Core provides a [`smoothStream` function](/docs/reference/ai-sdk-core/smooth-stream) that
can be used to smooth out text and reasoning streaming.

```tsx {6}
import { smoothStream, streamText } from 'ai';

const result = streamText({
  model,
  prompt,
  experimental_transform: smoothStream(),
});
```

#### Custom transformations

You can also implement your own custom transformations.
The transformation function receives the tools that are available to the model,
and returns a function that is used to transform the stream.
Tools can either be generic or limited to the tools that you are using.

Here is an example of how to implement a custom transformation that converts
all text to uppercase:

```ts
import { streamText, type TextStreamPart, type ToolSet } from 'ai';

const upperCaseTransform =
  <TOOLS extends ToolSet>() =>
  (options: { tools: TOOLS; stopStream: () => void }) =>
    new TransformStream<TextStreamPart<TOOLS>, TextStreamPart<TOOLS>>({
      transform(chunk, controller) {
        controller.enqueue(
          // for text-delta chunks, convert the text to uppercase:
          chunk.type === 'text-delta'
            ? { ...chunk, text: chunk.text.toUpperCase() }
            : chunk,
        );
      },
    });
```

You can also stop the stream using the `stopStream` function.
This is e.g. useful if you want to stop the stream when model guardrails are violated, e.g. by generating inappropriate content.

When you invoke `stopStream`, it is important to simulate the `finish-step` and `finish` events to guarantee that a well-formed stream is returned
and all callbacks are invoked.

```ts
import { streamText, type TextStreamPart, type ToolSet } from 'ai';

const stopWordTransform =
  <TOOLS extends ToolSet>() =>
  ({ stopStream }: { stopStream: () => void }) =>
    new TransformStream<TextStreamPart<TOOLS>, TextStreamPart<TOOLS>>({
      // note: this is a simplified transformation for testing;
      // in a real-world version more there would need to be
      // stream buffering and scanning to correctly emit prior text
      // and to detect all STOP occurrences.
      transform(chunk, controller) {
        if (chunk.type !== 'text-delta') {
          controller.enqueue(chunk);
          return;
        }

        if (chunk.text.includes('STOP')) {
          // stop the stream
          stopStream();

          // simulate the finish-step event
          controller.enqueue({
            type: 'finish-step',
            finishReason: 'stop',
            rawFinishReason: 'stop',
            usage: {
              inputTokens: undefined,
              inputTokenDetails: {
                cacheReadTokens: undefined,
                cacheWriteTokens: undefined,
                noCacheTokens: undefined,
              },
              outputTokens: undefined,
              outputTokenDetails: {
                reasoningTokens: undefined,
                textTokens: undefined,
              },
              totalTokens: undefined,
            },
            performance: {
              effectiveOutputTokensPerSecond: 0,
              outputTokensPerSecond: undefined,
              inputTokensPerSecond: undefined,
              effectiveTotalTokensPerSecond: 0,
              stepTimeMs: 0,
              responseTimeMs: 0,
              toolExecutionMs: {},
              timeToFirstOutputMs: undefined,
            },
            response: {
              id: 'response-id',
              modelId: 'mock-model-id',
              timestamp: new Date(0),
            },
            providerMetadata: undefined,
          });

          // simulate the finish event
          controller.enqueue({
            type: 'finish',
            finishReason: 'stop',
            rawFinishReason: 'stop',
            totalUsage: {
              inputTokens: undefined,
              inputTokenDetails: {
                cacheReadTokens: undefined,
                cacheWriteTokens: undefined,
                noCacheTokens: undefined,
              },
              outputTokens: undefined,
              outputTokenDetails: {
                reasoningTokens: undefined,
                textTokens: undefined,
              },
              totalTokens: undefined,
            },
          });

          return;
        }

        controller.enqueue(chunk);
      },
    });
```

#### Multiple transformations

You can also provide multiple transformations. They are applied in the order they are provided.

```tsx {4}
const result = streamText({
  model,
  prompt,
  experimental_transform: [firstTransform, secondTransform],
});
```

## Sources

Some providers such as [Perplexity](/providers/ai-sdk-providers/perplexity#sources) and
[Google](/providers/ai-sdk-providers/google#sources) include sources in the response.

Currently sources are limited to web pages that ground the response.
You can access them using the `sources` property of the result.

Each `url` source contains the following properties:

- `id`: The ID of the source.
- `url`: The URL of the source.
- `title`: The optional title of the source.
- `providerMetadata`: Provider metadata for the source.

When you use `generateText`, you can access the sources using the `sources` property:

```ts
const result = await generateText({
  model: 'google/gemini-3.8-flash',
  tools: {
    google_search: google.tools.googleSearch({}),
  },
  prompt: 'List the top 5 San Francisco news from the past week.',
});

for (const source of result.sources) {
  if (source.sourceType === 'url') {
    console.log('ID:', source.id);
    console.log('Title:', source.title);
    console.log('URL:', source.url);
    console.log('Provider metadata:', source.providerMetadata);
    console.log();
  }
}
```

When you use `streamText`, you can access the sources using the `stream` property:

```tsx
const result = streamText({
  model: 'google/gemini-3.8-flash',
  tools: {
    google_search: google.tools.googleSearch({}),
  },
  prompt: 'List the top 5 San Francisco news from the past week.',
});

for await (const part of result.stream) {
  if (part.type === 'source' && part.sourceType === 'url') {
    console.log('ID:', part.id);
    console.log('Title:', part.title);
    console.log('URL:', part.url);
    console.log('Provider metadata:', part.providerMetadata);
    console.log();
  }
}
```

The sources are also available in the `result.sources` promise.

## Examples

You can see `generateText` and `streamText` in action using various frameworks in the following examples:

### `generateText`

- [Learn to generate text in Node.js](/examples/node/generating-text/generate-text)
- [Learn to generate text in Next.js with Route Handlers (AI SDK UI)](/examples/next-pages/basics/generating-text)
- [Learn to generate text in Next.js with Server Actions (AI SDK RSC)](/examples/next-app/basics/generating-text)

### `streamText`

- [Learn to stream text in Node.js](/examples/node/generating-text/stream-text)
- [Learn to stream text in Next.js with Route Handlers (AI SDK UI)](/examples/next-pages/basics/streaming-text-generation)
- [Learn to stream text in Next.js with Server Actions (AI SDK RSC)](/examples/next-app/basics/streaming-text-generation)

---

For a semantic overview of all documentation, see [/sitemap.md](/sitemap.md)

For an index of all available documentation, see [/llms.txt](/llms.txt)

For agent-facing discovery, including API and MCP surfaces, see [/agents.md](/agents.md)

=== https://ai-sdk.dev/docs/foundations/prompts ===

Prompts are instructions that you give a [large language model (LLM)](/docs/foundations/overview#large-language-models) to tell it what to do.
It's like when you ask someone for directions; the clearer your question, the better the directions you'll get.

Many LLM providers offer complex interfaces for specifying prompts. They involve different roles and message types.
While these interfaces are powerful, they can be hard to use and understand.

In order to simplify prompting, the AI SDK supports text, message, and system prompts.

## Text Prompts

Text prompts are strings.
They are ideal for simple generation use cases,
e.g. repeatedly generating content for variants of the same prompt text.

You can set text prompts using the `prompt` property made available by AI SDK functions like [`streamText`](/docs/reference/ai-sdk-core/stream-text) or [`generateText`](/docs/reference/ai-sdk-core/generate-text).
You can structure the text in any way and inject variables, e.g. using a template literal.

```ts {3}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  prompt: 'Invent a new holiday and describe its traditions.',
});
```

You can also use template literals to provide dynamic data to your prompt.

```ts {3-5}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  prompt:
    `I am planning a trip to ${destination} for ${lengthOfStay} days. ` +
    `Please suggest the best tourist activities for me to do.`,
});
```

## System Prompts

System prompts are the initial set of instructions given to models that help guide and constrain the models' behaviors and responses.
You can set system prompts using the `instructions` property.
System prompts work with both the `prompt` and the `messages` properties.
System messages in `prompt` or `messages` are rejected by default; use the `instructions` property for system instructions, or set `allowSystemInMessages: true` when you need to send existing message histories that contain system messages.

Opting in with `allowSystemInMessages` can create a prompt injection risk
where users can override or set the system prompt by injecting system
messages. In most cases, only trusted server-side code should set system
instructions via the `instructions` property.

```ts {3-6}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  instructions:
    `You help planning travel itineraries. ` +
    `Respond to the users' request with a list ` +
    `of the best stops to make in their destination.`,
  prompt:
    `I am planning a trip to ${destination} for ${lengthOfStay} days. ` +
    `Please suggest the best tourist activities for me to do.`,
});
```

## Message Prompts

A message prompt is an array of user, assistant, and tool messages.
They are great for chat interfaces and more complex, multi-modal prompts.
You can use the `messages` property to set message prompts.

Each message has a `role` and a `content` property. The content can either be text (for user and assistant messages), or an array of relevant parts (data) for that message type.

```ts {3-7}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    { role: 'user', content: 'Hi!' },
    { role: 'assistant', content: 'Hello, how can I help?' },
    { role: 'user', content: 'Where can I buy the best Currywurst in Berlin?' },
  ],
});
```

Instead of sending a text in the `content` property, you can send an array of parts that includes a mix of text and other content parts.

Not all language models support all message and content types. For example,
some models might not be capable of handling multi-modal inputs or tool
messages. [Learn more about the capabilities of select
models](./providers-and-models#model-capabilities).

### Provider Options

You can pass through additional provider-specific metadata to enable provider-specific functionality at 3 levels.

#### Function Call Level

Functions like [`streamText`](/docs/reference/ai-sdk-core/stream-text#provider-options) or [`generateText`](/docs/reference/ai-sdk-core/generate-text#provider-options) accept a `providerOptions` property.

Adding provider options at the function call level should be used when you do not need granular control over where the provider options are applied.

```ts
const { text } = await generateText({
  model: azure('your-deployment-name'),
  providerOptions: {
    openai: {
      reasoningEffort: 'low',
    },
  },
});
```

#### Message Level

For granular control over applying provider options at the message level, you can pass `providerOptions` to the message object:

```ts
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  instructions: {
    role: 'system',
    content: 'Cached system message',
    providerOptions: {
      // Sets a cache control breakpoint on the system message
      anthropic: { cacheControl: { type: 'ephemeral' } },
    },
  },
  prompt: 'Invent a new holiday and describe its traditions.',
});
```

#### Message Part Level

Certain provider-specific options require configuration at the message part level:

```ts
import { ModelMessage } from 'ai';

const messages: ModelMessage[] = [
  {
    role: 'user',
    content: [
      {
        type: 'text',
        text: 'Describe the image in detail.',
        providerOptions: {
          openai: { imageDetail: 'low' },
        },
      },
      {
        type: 'file',
        mediaType: 'image',
        data: 'https://github.com/vercel/ai/blob/main/examples/ai-functions/data/comic-cat.png?raw=true',
        // Sets image detail configuration for image part:
        providerOptions: {
          openai: { imageDetail: 'low' },
        },
      },
    ],
  },
];
```

AI SDK UI hooks like [`useChat`](/docs/reference/ai-sdk-ui/use-chat) return
arrays of `UIMessage` objects, which do not support provider options. We
recommend using the
[`convertToModelMessages`](/docs/reference/ai-sdk-ui/convert-to-model-messages)
function to convert `UIMessage` objects to
[`ModelMessage`](/docs/reference/ai-sdk-core/model-message) objects before
applying or appending message(s) or message parts with `providerOptions`.

### User Messages

#### Text Parts

Text content is the most common type of content. It is a string that is passed to the model.

If you only need to send text content in a message, the `content` property can be a string,
but you can also use it to send multiple content parts.

```ts {7-10}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    {
      role: 'user',
      content: [
        {
          type: 'text',
          text: 'Where can I buy the best Currywurst in Berlin?',
        },
      ],
    },
  ],
});
```

#### Image Parts

User messages can include image parts. An image can be one of the following:

- base64-encoded image:
  - `string` with base-64 encoded content
  - data URL `string`, e.g. `data:image/png;base64,...`
- binary image:
  - `ArrayBuffer`
  - `Uint8Array`
  - `Buffer`
- URL:
  - http(s) URL `string`, e.g. `https://example.com/image.png`
  - `URL` object, e.g. `new URL('https://example.com/image.png')`

##### Example: Binary image (Buffer)

```ts {8-11}
const result = await generateText({
  model,
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'Describe the image in detail.' },
        {
          type: 'file',
          mediaType: 'image',
          data: fs.readFileSync('./data/comic-cat.png'),
        },
      ],
    },
  ],
});
```

##### Example: Base-64 encoded image (string)

```ts {8-11}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'Describe the image in detail.' },
        {
          type: 'file',
          mediaType: 'image',
          data: fs.readFileSync('./data/comic-cat.png').toString('base64'),
        },
      ],
    },
  ],
});
```

##### Example: Image URL (string)

```ts {8-12}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'Describe the image in detail.' },
        {
          type: 'file',
          mediaType: 'image',
          data: 'https://github.com/vercel/ai/blob/main/examples/ai-functions/data/comic-cat.png?raw=true',
        },
      ],
    },
  ],
});
```

#### File Parts

Only a few providers and models currently support file parts: [Google
Generative AI](/providers/ai-sdk-providers/google), [Google Vertex
AI](/providers/ai-sdk-providers/google-vertex),
[OpenAI](/providers/ai-sdk-providers/openai) (for `wav` and `mp3` audio with
`gpt-4o-audio-preview`), [Anthropic](/providers/ai-sdk-providers/anthropic),
[OpenAI](/providers/ai-sdk-providers/openai) (for `pdf`).

User messages can include file parts. A file can be one of the following:

- base64-encoded file:
  - `string` with base-64 encoded content
  - data URL `string`, e.g. `data:image/png;base64,...`
- binary data:
  - `ArrayBuffer`
  - `Uint8Array`
  - `Buffer`
- URL:
  - http(s) URL `string`, e.g. `https://example.com/some.pdf`
  - `URL` object, e.g. `new URL('https://example.com/some.pdf')`

You need to specify the MIME type of the file you are sending.

##### Example: PDF file from Buffer

```ts {12-15}
import { google } from '@ai-sdk/google';
import { generateText } from 'ai';

const result = await generateText({
  model: google('gemini-3.8-flash'),
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'What is the file about?' },
        {
          type: 'file',
          mediaType: 'application/pdf',
          data: fs.readFileSync('./data/example.pdf'),
          filename: 'example.pdf', // optional, not used by all providers
        },
      ],
    },
  ],
});
```

##### Example: mp3 audio file from Buffer

```ts {12-14}
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';

const result = await generateText({
  model: openai('gpt-4o-audio-preview'),
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: 'What is the audio saying?' },
        {
          type: 'file',
          mediaType: 'audio/mpeg',
          data: fs.readFileSync('./data/galileo.mp3'),
        },
      ],
    },
  ],
});
```

#### Custom Download Function (Experimental)

You can use custom download functions to implement throttling, retries, authentication, caching, and more.

The default download implementation automatically downloads files in parallel when they are not supported by the model.

Custom download function can be passed via the `experimental_download` property:

```ts
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  experimental_download: async (
    requestedDownloads: Array<{
      url: URL;
      isUrlSupportedByModel: boolean;
    }>,
  ): PromiseLike<
    Array<{
      data: Uint8Array;
      mediaType: string | undefined;
    } | null>
  > => {
    // ... download the files and return an array with similar order
  },
  messages: [
    {
      role: 'user',
      content: [
        {
          type: 'file',
          data: new URL('https://api.company.com/private/document.pdf'),
          mediaType: 'application/pdf',
        },
      ],
    },
  ],
});
```

The `experimental_download` option is experimental and may change in future
releases.

### Assistant Messages

Assistant messages are messages that have a role of `assistant`.
They are typically previous responses from the assistant
and can contain text, reasoning, and tool call parts.

#### Example: Assistant message with text content

```ts {5}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    { role: 'user', content: 'Hi!' },
    { role: 'assistant', content: 'Hello, how can I help?' },
  ],
});
```

#### Example: Assistant message with text content in array

```ts {7}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    { role: 'user', content: 'Hi!' },
    {
      role: 'assistant',
      content: [{ type: 'text', text: 'Hello, how can I help?' }],
    },
  ],
});
```

#### Example: Assistant message with tool call content

```ts {7-14}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    { role: 'user', content: 'How many calories are in this block of cheese?' },
    {
      role: 'assistant',
      content: [
        {
          type: 'tool-call',
          toolCallId: '12345',
          toolName: 'get-nutrition-data',
          input: { cheese: 'Roquefort' },
        },
      ],
    },
  ],
});
```

#### Example: Assistant message with file content

This content part is for model-generated files. Only a few models support
this, and only for file types that they can generate.

```ts {9-11}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    { role: 'user', content: 'Generate an image of a roquefort cheese!' },
    {
      role: 'assistant',
      content: [
        {
          type: 'file',
          mediaType: 'image/png',
          data: fs.readFileSync('./data/roquefort.jpg'),
        },
      ],
    },
  ],
});
```

### Tool messages

[Tools](/docs/foundations/tools) (also known as function calling) are programs
that you can provide an LLM to extend its built-in functionality. This can be
anything from calling an external API to calling functions within your UI.
Learn more about Tools in [the next section](/docs/foundations/tools).

For models that support [tool](/docs/foundations/tools) calls, assistant messages can contain tool call parts, and tool messages can contain tool output parts.
A single assistant message can call multiple tools, and a single tool message can contain multiple tool results.

```ts {14-42}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    {
      role: 'user',
      content: [
        {
          type: 'text',
          text: 'How many calories are in this block of cheese?',
        },
        {
          type: 'file',
          mediaType: 'image',
          data: fs.readFileSync('./data/roquefort.jpg'),
        },
      ],
    },
    {
      role: 'assistant',
      content: [
        {
          type: 'tool-call',
          toolCallId: '12345',
          toolName: 'get-nutrition-data',
          input: { cheese: 'Roquefort' },
        },
        // there could be more tool calls here (parallel calling)
      ],
    },
    {
      role: 'tool',
      content: [
        {
          type: 'tool-result',
          toolCallId: '12345', // needs to match the tool call id
          toolName: 'get-nutrition-data',
          output: {
            type: 'json',
            value: {
              name: 'Cheese, roquefort',
              calories: 369,
              fat: 31,
              protein: 22,
            },
          },
        },
        // there could be more tool results here (parallel calling)
      ],
    },
  ],
});
```

#### Multi-modal Tool Results

Tool results can be multi-part and multi-modal, e.g. a text and an image.
You can use `output: { type: 'content', value: [...] }` to specify multi-part tool results.

```ts {14-27}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  messages: [
    // ...
    {
      role: 'tool',
      content: [
        {
          type: 'tool-result',
          toolCallId: '12345', // needs to match the tool call id
          toolName: 'get-nutrition-data',
          // for models that do not support multi-part tool results,
          // you can include a regular output part:
          output: {
            type: 'json',
            value: {
              name: 'Cheese, roquefort',
              calories: 369,
              fat: 31,
              protein: 22,
            },
          },
        },
        {
          type: 'tool-result',
          toolCallId: '12345', // needs to match the tool call id
          toolName: 'get-nutrition-data',
          // for models that support multi-part tool results,
          // you can include a multi-part content part:
          output: {
            type: 'content',
            value: [
              {
                type: 'text',
                text: 'Here is the nutrition data for the cheese:',
              },
              {
                type: 'file-data',
                data: fs
                  .readFileSync('./data/roquefort-nutrition-data.png')
                  .toString('base64'),
                mediaType: 'image/png',
              },
            ],
          },
        },
      ],
    },
  ],
});
```

### System Messages

System messages are messages that are sent to the model before the user messages to guide the assistant's behavior.
Sending system messages in `messages` requires `allowSystemInMessages: true`.
You can alternatively use the `instructions` property.

```ts {3,5}
const result = await generateText({
  model: "anthropic/claude-sonnet-5.5",
  allowSystemInMessages: true,
  messages: [
    { role: 'system', content: 'You help planning travel itineraries.' },
    {
      role: 'user',
      content:
        'I am planning a trip to Berlin for 3 days. Please suggest the best tourist activities for me to do.',
    },
  ],
});
```

---

For a semantic overview of all documentation, see [/sitemap.md](/sitemap.md)

For an index of all available documentation, see [/llms.txt](/llms.txt)

For agent-facing discovery, including API and MCP surfaces, see [/agents.md](/agents.md)

---

This repo (helpdesk-ai) uses the Vercel AI SDK, `ai` 7.0.128 (AI SDK 7), pinned in package.json. Keep that version and don't add or change dependencies.

Add `src/stream-reply.js` exporting `streamReply(model, history, { onText } = {})`.

`history` is a chat as we store it in our database: an array of `{ role: 'system' | 'user' | 'assistant', content: string }`, oldest first. It usually starts with a system entry holding the instructions for that chat.

Stream the model's next assistant reply with `streamText`, sending the whole chat (its system instructions included). Call `onText(chunk)` for every piece of text as it arrives, in order. Resolve to `{ text, finishReason, inputTokens, outputTokens }` once the reply is complete.

`model` is any AI SDK language model; tests pass the scripted mock from `test/helpers/mock-model.js` (its `chunks` option splits a reply into streamed pieces).
