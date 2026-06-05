# Future Improvements

## Runtime subagent selection

The `agents/` directory is a catalog of all available subagents. Today, all agents are activated at startup. The next step is to let a runtime config determine which subset is active for a given deployment or request.

**Open questions before implementing:**

1. **Per-deployment or per-request?**
   - Per-deployment: config is read at startup (e.g. env var `ENABLED_AGENTS=researcher,report_writer`). The graph is compiled once. Simpler, fits the LangGraph server model.
   - Per-request: caller passes which agents to use in each request payload. More dynamic, but requires rebuilding the agent list per run and a different graph structure.

2. **Flat list or structured config?**
   - Flat list: `ENABLED_AGENTS=researcher,report_writer` — simple, per-agent tuning still handled by existing env vars.
   - Structured: `{ "researcher": { "max_search_calls": 3 }, "report_writer": {} }` — full control per deployment, no env var per agent needed.
