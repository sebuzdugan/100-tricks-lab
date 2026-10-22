// Support assistant helpers. Written for AI SDK 6 (ai@6.0.x); not yet migrated to AI SDK 7.
import { generateText, Output, stepCountIs, tool } from 'ai';
import { z } from 'zod';
import { findOrder } from '../data/orders.js';

const SUMMARY_RULES = 'You summarise support threads for the next agent on shift. Two sentences, no greetings.';
const ORDER_RULES = "You are Acme's order assistant. Only discuss the current customer's orders. Be brief.";

/** Looks up one of the current customer's orders. The customer id comes from the call's context. */
const orderLookup = tool({
  description: "Look up one of the current customer's orders by id.",
  inputSchema: z.object({ orderId: z.string() }),
  execute: async ({ orderId }, { experimental_context }) => {
    const { customerId } = experimental_context;
    const order = findOrder(orderId);
    if (!order || order.customerId !== customerId) return { orderId, error: 'not found' };
    return { orderId, status: order.status, eta: order.eta };
  },
});

/**
 * Summarises a support thread for the next agent on shift.
 * @param {import('ai').LanguageModel} model
 * @param {{ from: 'customer' | 'agent', text: string }[]} thread oldest first
 * @returns {Promise<{ summary: string, inputTokens: number, cachedInputTokens: number }>}
 *   the summary, the input tokens the call used, and how many of those were read from the provider's prompt cache
 */
export async function summarizeThread(model, thread) {
  const result = await generateText({
    model,
    messages: [
      { role: 'system', content: SUMMARY_RULES },
      ...thread.map((m) => ({ role: m.from === 'customer' ? 'user' : 'assistant', content: m.text })),
      { role: 'user', content: 'Summarise this thread.' },
    ],
  });
  return {
    summary: result.text,
    inputTokens: result.usage.inputTokens,
    cachedInputTokens: result.usage.cachedInputTokens ?? 0,
  };
}

/**
 * Answers a customer's question about their orders. The model may look up orders (at most 4 model calls);
 * it can only see orders that belong to `customerId`.
 * @param {import('ai').LanguageModel} model
 * @param {string} question
 * @param {{ customerId: string }} customer
 * @returns {Promise<{ text: string, toolsUsed: string[] }>} the answer and the names of the tools called, in order
 */
export async function answerAboutOrders(model, question, { customerId }) {
  const result = await generateText({
    model,
    system: ORDER_RULES,
    tools: { orderLookup },
    experimental_context: { customerId },
    stopWhen: stepCountIs(4),
    prompt: question,
  });
  return { text: result.text, toolsUsed: result.steps.flatMap((s) => s.toolCalls.map((c) => c.toolName)) };
}

const ticketSchema = z.object({
  category: z.enum(['billing', 'shipping', 'bug', 'other']),
  urgent: z.boolean(),
});

/**
 * Classifies a support ticket.
 * @param {import('ai').LanguageModel} model
 * @param {string} text the ticket text
 * @returns {Promise<{ category: 'billing' | 'shipping' | 'bug' | 'other', urgent: boolean }>} validated against the schema
 */
export async function classifyTicket(model, text) {
  const { experimental_output } = await generateText({
    model,
    experimental_output: Output.object({ schema: ticketSchema }),
    prompt: `Classify this support ticket:\n\n${text}`,
  });
  return experimental_output;
}

/**
 * Continues an order-support chat by one user turn.
 * @param {import('ai').LanguageModel} model
 * @param {import('ai').ModelMessage[]} history earlier user, assistant and tool messages (no system messages)
 * @param {string} userText the customer's new message
 * @param {{ customerId: string }} customer
 * @returns {Promise<import('ai').ModelMessage[]>} the full updated history: `history`, the new user message, then every
 *   message the model produced this turn (assistant tool calls, tool results and the final answer), so the next turn
 *   sees what was looked up
 */
export async function continueChat(model, history, userText, { customerId }) {
  const messages = [...history, { role: 'user', content: userText }];
  const result = await generateText({
    model,
    system: ORDER_RULES,
    tools: { orderLookup },
    experimental_context: { customerId },
    stopWhen: stepCountIs(4),
    messages,
  });
  return [...messages, ...result.response.messages];
}
