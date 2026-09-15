## packages/frai-agent

- TypeScript LangChain agent. Build: `pnpm --filter frai-agent build`. There is no test script.
- Run it from the repo root with `pnpm agent:frai "<instruction>"`; it needs `OPENAI_API_KEY`.
- `src/agent/executor.ts` builds the agent (`createFraIAgentExecutor`); `src/agent/prompt.ts` holds the system prompt.
- `src/tools/` wraps frai-core as LangChain tools: `scan_repository` (Scanners) and `generate_responsible_ai_docs` (Documents).
- `src/cli/run.ts` is the command-line entry: one turn when given an instruction, a REPL without one.
- Nothing else in the repo imports frai-agent.
- Double quotes; Node built-ins use the `node:` prefix (`node:path`, `node:fs`).
