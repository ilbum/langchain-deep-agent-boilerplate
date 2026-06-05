# Production Stateful Deepagents with Cloudflare & LangChain

## Architecture Overview

```
Client / API / Slack / Webhook
        |
        v
Cloudflare Worker
- auth
- rate limiting
- request validation
- streaming response
- routes requests
        |
        v
Durable Object per agent/conversation/user
- stateful agent session
- message ordering
- short-term memory
- locks/idempotency
- WebSocket/SSE coordination
- local SQLite state
        |
        +--> Cloudflare Workflow
        |    - long-running agent tasks
        |    - retries
        |    - sleeps
        |    - human-in-the-loop waits
        |
        +--> Queue
        |    - async tools
        |    - embedding jobs
        |    - summarization
        |    - ingestion
        |
        +--> Vectorize
        |    - semantic memory
        |    - RAG search
        |
        +--> R2
        |    - files
        |    - transcripts
        |    - artifacts
        |    - large tool outputs
        |
        +--> D1 / external Postgres
        |    - users
        |    - runs
        |    - audit records
        |    - billing
        |    - agent configs
        |
        +--> AI Gateway
             - OpenAI/Anthropic/etc.
             - Workers AI
             - logs
             - retries
             - rate limits
             - caching
             - fallback
```

---

## The Core Challenge

Stateful AI agents need four things:
1. **Request edge** — fast auth/routing/streaming
2. **State kernel** — durable per-user/conversation memory
3. **Durable executor** — something surviving long runs, retries, human approval
4. **External stores** — vectors, blobs, metadata, traces

Cloudflare provides most of this natively, but you must map LangChain/LangGraph concepts carefully onto its primitives.

---

## Pattern A: Cloudflare-Native TypeScript Agents

**Use this when:** Your agents are chat/tool-focused and you want edge-native deployment.

**Architecture:**
```
Worker (auth, routing, streaming)
  ↓
Durable Object per conversation (stateful kernel)
  ↓
LangChain.js agent turn
  ↓
AI Gateway → LLM calls
```

**State lives in:**
- Durable Object SQLite: recent messages, summary, active run
- Vectorize: semantic memory
- R2: large artifacts
- D1: metadata

**Why this works:**
- Durable Objects solve the race condition problem (two requests for same conversation arriving simultaneously)
- Single-threaded coordination prevents inconsistent state
- Sub-50ms latency to 95% of users
- Pay-per-inference (Workers AI) not per-idle-GPU

**Critical constraint:** Each Durable Object maxes at **10 GB storage** (Workers Paid). Long-lived agents need summarization/compaction.

**Gotcha:** Not all LangChain.js packages are edge-compatible. Avoid filesystem access, native Node modules, child processes, or heavy browser tooling.

---

## Pattern B: Cloudflare + Regional LangGraph Runtime

**Use this when:** You need Python LangGraph, deepagents, browser automation, code execution, or complex tools.

**Architecture:**
```
Cloudflare Worker (edge gateway, auth, rate limit, streaming proxy)
  ↓
Regional LangGraph/LangSmith Agent Server (Python or Node)
  ↓
Postgres checkpointer (durable state)
```

**Why this approach:**
- Cloudflare at the edge: routing, security, AI Gateway, R2, Vectorize
- Full agent runtime in container: Cloud Run, Fly.io, ECS, LangGraph Platform
- Postgres naturally supports LangGraph's checkpoint/thread/run/memory model
- Better for long-running, complex, Python-heavy agents

**State design:**
- **Checkpoints** → Postgres (LangGraph saves state after nodes)
- **Threads/runs** → Postgres (conversation/workflow identity)
- **Semantic memory** → Vectorize or external vector DB
- **Artifacts** → R2
- **Metadata** → D1 or Postgres

---

## Component Mapping

### Workers = Stateless Edge
- Auth, validation, routing, rate limiting
- **Never** store agent memory in global variables
- Call Durable Objects, Queues, Workflows, R2, D1, Vectorize

### Durable Objects = Stateful Session Kernel
- One object per conversation/agent/user
- SQLite-backed, single-threaded coordination
- **Soft limit:** ~1,000 requests/second per object
- **Storage:** 10 GB max (Workers Paid)
- **Wall time:** Unlimited while caller connected

### Workflows = Durable Long-Running Tasks
- Research agents, multi-step chains, human-in-the-loop waits
- Each step can run unlimited wall time
- Steps must be idempotent
- **Do not** keep HTTP open for these; return job ID immediately

### Queues = Async Buffering
- Embeddings, ingestion, slow tools, fanout
- **Wall-time limit:** 15 minutes per consumer invocation
- Assume at-least-once delivery; design for idempotency
- Every message should include: `jobId`, `tenantId`, `conversationId`, `idempotencyKey`

### R2 = Artifact Storage
- Uploaded files, transcripts, tool outputs, large intermediate results
- **Bad:** Storing 500-page PDFs directly in Durable Object state
- **Good:** Store reference `r2://tenant-123/docs/file-456.txt`

### D1 = Relational Metadata
- **Limit:** 10 GB per database
- Users, orgs, conversation index, run records, audit logs
- For serious LangGraph, use Postgres instead (D1 is better for edge-native app config)

### KV = Stale-Tolerant Config Only
- **Never** use for agent memory, locks, counters, or read-after-write correctness
- KV is eventually consistent (updates can take seconds to propagate)
- Use for prompt templates, feature flags, static config

### Vectorize = Semantic Memory/RAG
- **Max vector dimensions:** 1536 (float32)
- **Max vectors:** 10,000,000 per index
- **Max returned:** 50 with metadata, 100 without
- **Max metadata:** 10 KiB per vector
- Store source documents in R2, chunk metadata in D1

### AI Gateway = Model Control Plane
- Observability, caching, retries, rate limiting, fallback, provider abstraction
- **Warning:** Logs may contain sensitive prompts, PII, secrets. Set redaction policies.

---

## Minimal Stateful Agent Sketch

```typescript
// Worker routes to Durable Object per conversation_id
export default {
  async fetch(request, env) {
    const conversationId = new URL(request.url).pathname.split("/").pop();
    const id = env.CONVERSATIONS.idFromName(conversationId);
    return env.CONVERSATIONS.get(id).fetch(request);
  }
};

// Durable Object owns conversation state
export class ConversationObject {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    const { message } = await request.json();

    // Load persisted state
    let agentState = await this.state.storage.get("agentState") || {
      messages: [],
      summary: "",
      toolLedger: []
    };

    // Retrieve semantic memory from Vectorize
    const memory = await retrieveMemory(message);

    // Call LLM through AI Gateway
    const response = await callModel({
      messages: agentState.messages,
      summary: agentState.summary,
      memory: memory
    });

    // Update state
    agentState.messages.push({ role: "user", content: message });
    agentState.messages.push({ role: "assistant", content: response.text });
    await this.state.storage.put("agentState", agentState);

    return Response.json({ response: response.text });
  }
}
```

---

## Production Gotchas & Mitigations

| Problem | Cause | Fix |
|---------|-------|-----|
| Race conditions | Two requests for same conversation | Use Durable Object (single-threaded) |
| Hot object bottleneck | One Durable Object overloaded | Shard by conversation/user/task |
| Memory growth | 10 GB limit exceeded | Summarize, compact, archive to R2 |
| Incorrect state | KV eventually consistent | Use Durable Objects or D1 for correctness |
| Infinite loops | Agent never stops | Max iterations, token budget, time limit |
| Duplicate actions | Queue/Workflow retries | Idempotency keys + side-effect ledger |
| Model variance | AI Gateway fallback changes behavior | Pin models, validate schema, test fallback |
| Missing traces | Multi-service logs scattered | Propagate `requestId`, `threadId`, `runId` everywhere |
| Prompt injection | RAG content overrides system rules | Treat retrieved text as untrusted data |

---

## Human-in-the-Loop Pattern

For risky tools (send email, make purchase, delete data):

1. Agent decides action, stores proposal
2. Mark run as `waiting_for_approval`
3. Notify user with approval UI
4. User approves/rejects
5. Agent resumes from checkpoint

**Critical:** Store real approval records, not just text like "User approved this."

---

## Memory Architecture

**Short-term:** Recent conversation turns → Durable Object or LangGraph checkpoint

**Summary:** Condensed history → Durable Object or D1

**Semantic:** Embeddings of facts, docs → Vectorize

**Artifacts:** Large files, reports → R2

---

## Idempotency (Non-Negotiable)

Every side-effecting action needs an idempotency key:

```json
{
  "tool": "send_email",
  "idempotencyKey": "run_123:send_email:attempt_1",
  "inputHash": "abc123"
}
```

Before executing, check: *Have we already done this?* If yes, return stored result. If no, execute and record.

---

## Recommendation

**For most teams building stateful deepagents in production:**

Use **Pattern B** (Cloudflare edge + regional LangGraph runtime). Reasons:

1. Cloudflare excels at global ingress, security, rate limiting
2. LangGraph/deepagents thrive in containers with Postgres
3. Cleaner separation of concerns
4. Less dependency compatibility pain
5. Easier local development

**Exception:** If your agents are simple chat or lightweight tools in TypeScript, Pattern A (Cloudflare-native) is faster to ship and costs less.

---

## Quick Build Sequence

1. **Phase 1:** Worker → Durable Object → LLM (streaming chat)
2. **Phase 2:** Add R2 artifacts, Vectorize memory, D1 metadata
3. **Phase 3:** Add tool execution with idempotency ledger
4. **Phase 4:** Add Workflows/Queues for long-running tasks
5. **Phase 5:** Add LangSmith tracing, cost limits, evals, audit logs

---

**Bottom line:** Cloudflare is excellent infrastructure for stateful agents if you embrace its primitives (Workers for ingress, Durable Objects for state, Workflows for durability) rather than forcing a monolithic server pattern onto the edge.
