# Stateful Deepagents on Cloudflare: Production Architecture

## The Core Pattern

You need four layers:

1. **Edge ingress** (Workers) — auth, rate-limit, routing
2. **State kernel** (Durable Objects) — per-conversation memory, coordination
3. **Durable execution** (Workflows/external LangGraph) — long tasks, retries, checkpoints
4. **External stores** — R2 (files), D1/Postgres (metadata), Vectorize (semantic memory)

## Two Viable Paths

### Path A: Cloudflare-Native TypeScript
Use Workers + Durable Objects + LangChain.js for bounded chat agents. Good for support bots and lightweight tool use. Risk: "Not all LangChain packages are edge-compatible" and Workers impose CPU/time limits unsuitable for complex deepagents.

### Path B: Cloudflare Edge + Regional LangGraph Server
Cloudflare handles global routing/security/caching. A container (Cloud Run, Fly, ECS) runs the actual LangGraph/deepagents runtime with Postgres checkpointing. This is safer for Python, complex tools, and long-running research agents.

## Key Cloudflare Primitives Mapped

| Primitive | Agent Concept | Limit |
|-----------|---------------|-------|
| **Durable Objects** | Per-conversation state, message ordering, WebSocket coordination | 10 GB storage per object (Paid plan) |
| **Workflows** | Durable multi-step execution, tool chains, human-in-the-loop waits | Unlimited wall time per step, subject to CPU limits |
| **Queues** | Async tool calls, embeddings, backpressure | 15-minute wall time per consumer |
| **Vectorize** | Semantic memory, RAG retrieval | 1536-dim max, 50M vectors per index, topK≤50 |
| **R2** | Files, transcripts, artifacts, large outputs | No limit (S3-compatible) |
| **D1** | Relational metadata, users, runs, configs | 10 GB per database |
| **AI Gateway** | Model observability, caching, rate limits, fallback | All providers, plus Workers AI |

## Three Critical Gotchas

1. **State consistency**: KV is eventually consistent—never use for agent memory. Use Durable Objects or external Postgres instead.

2. **Hot object bottleneck**: A single Durable Object has a soft limit of ~1,000 requests/second. Shard by conversation ID, not tenant ID.

3. **Long-running deepagents**: Do not hold HTTP connections open for 10+ minute research tasks. Return a `run_id` immediately and use Workflows or a regional container.

## Minimal Sketch: Chat Agent

Worker routes to Durable Object per `conversationId`. Object maintains message history, calls model through AI Gateway, stores state to SQLite. Artifacts go to R2. Semantic search hits Vectorize. Done.

## LangGraph/Deepagents Recommendation

If using Python LangGraph or deepagents:
- Keep Cloudflare at the edge for auth, routing, R2, Vectorize, AI Gateway
- Run the full agent runtime in a durable regional container with Postgres checkpointing
- Use `thread_id` for conversation identity, `run_id` for execution attempts
- Store checkpoints in Postgres (not Workers)
- Stream events back via Worker proxy

## Production Checklist

- [ ] Idempotency keys on every tool call
- [ ] Budget limits (max iterations, tokens, runtime)
- [ ] Human approval before irreversible actions
- [ ] Side-effect ledger to prevent duplicate work
- [ ] Correlation IDs across all services
- [ ] Structured event stream for reconnectable clients
- [ ] Large artifacts in R2, metadata in D1/Postgres
- [ ] All LLM calls through AI Gateway
- [ ] LangSmith tracing from day one

The architecture works because Durable Objects solve the hardest problem: keeping one conversation's state single-threaded and coherent under concurrent requests.
