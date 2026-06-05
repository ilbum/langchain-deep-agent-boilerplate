# deep-agent-boilerplate

A production-ready boilerplate for building **Deep Agents** — multi-step AI agents that gather information, synthesize it, and take action — on top of LangGraph and LangChain.

Deep Agents go beyond simple ReAct loops. They delegate specialized work to isolated sub-agents, offload context to a virtual filesystem, and coordinate complex multi-step workflows while keeping each agent's context lean and focused.

---

## Design

The orchestrator follows a **gather → synthesize → act** loop:

1. **Gather** — delegate information-gathering or data-fetching tasks to sub-agents in parallel
2. **Synthesize** — combine results, reason about what was found, plan next steps
3. **Act** — delegate action-taking sub-agents (write, send, publish) with the synthesized output

```
User request
     │
     ▼
┌─────────────────────────────────────────────────┐
│                  Orchestrator                   │
│                                                 │
│  think_tool  — reflection + planning            │
│  task() ──► Sub-agent (isolated context)        │
│                                                 │
│  Gather ──► Synthesize ──► Act                  │
└─────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
   research-agent           report-writer
   (web search)             (Google Docs)
```

**Key design principles:**

- **SDK-managed middleware** — todo list, filesystem, and sub-agent delegation are wired automatically by `create_deep_agent()`
- **Context isolation** — sub-agents receive only their task description, not the parent's message history
- **Context offloading** — `tavily_search` saves full page content to the shared filesystem; the orchestrator's context sees only a short summary
- **Declarative HITL** — action-taking sub-agents declare which tools require user approval via `interrupt_on`; the framework handles pause and resume

---

## Project structure

```
src/deep_agent/
├── agent.py                  # Orchestrator — wires model, tools, and subagents
├── subagents.py              # Subagent definitions (extend here to add new agents)
├── tools.py                  # Shared tools (think_tool)
├── research_tools.py         # Research tools (tavily_search)
└── google_workspace_tools.py # Google Docs integration (create_google_doc)
```

---

## Quick start

**1. Clone and install**

```bash
git clone https://github.com/ilbum/deep-agent-boilerplate
cd deep-agent-boilerplate
uv sync
```

**2. Set environment variables**

Copy `.env.example` to `.env` and fill in your keys:

```bash
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Models (optional — these are the defaults)
MAIN_MODEL=openai:gpt-5.5
SUMMARIZATION_MODEL=openai:gpt-5.4-mini

# Orchestrator limits (optional)
MAX_CONCURRENT_AGENTS=3       # max parallel sub-agents per iteration
MAX_AGENT_ITERATIONS=5        # max total task delegations per run
MAX_SEARCH_CALLS=5            # max tavily_search calls per research agent

# Google Workspace — required only for the report-writer subagent
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...

# LangSmith tracing (optional)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=deep-agent-boilerplate
```

**3. Start the local dev server**

```bash
uv run langgraph dev
```

This starts a hot-reloading server at `http://localhost:2024` with the LangGraph Studio UI.

---

## How a run works

1. User sends a request to the orchestrator
2. Orchestrator uses `think_tool` to plan its approach
3. It delegates to one or more sub-agents via `task()` — in parallel when tasks are independent
4. Sub-agents execute in isolated contexts and return their findings or confirmation of action
5. Orchestrator synthesizes results, then delegates to action sub-agents if needed
6. If a sub-agent's tool is marked `interrupt_on`, the framework pauses and surfaces the action to the user for approval before proceeding

---

## Extending

### Adding a sub-agent

All sub-agents live in `subagents.py`. Add a private function and append it to the `subagents` list:

```python
def _my_agent() -> dict:
    return {
        "name": "my-agent",
        "description": "One sentence — the orchestrator uses this to decide when to call this agent",
        "system_prompt": _MY_AGENT_INSTRUCTIONS,
        "tools": [my_tool],
    }

subagents: list[dict] = [
    _research_agent(),
    _report_writer(),
    _my_agent(),   # ← add here
]
```

The orchestrator's prompt is automatically updated — `{subagent_listing}` is generated from the `name` and `description` fields at startup.

**If your sub-agent takes irreversible actions** (sends messages, writes to external systems, deletes data), declare `interrupt_on` for those tools. The framework will pause and ask the user for approval before the tool fires:

```python
def _slack_agent() -> dict:
    return {
        "name": "slack-agent",
        "description": "Posts a message to a Slack channel",
        "system_prompt": _SLACK_INSTRUCTIONS,
        "tools": [send_slack_message],
        "interrupt_on": {"send_slack_message": True},  # pauses for user approval
    }
```

The user can approve, edit the message, or reject — handled natively by the framework with no extra code.

### Adding tools

Each integration gets its own `*_tools.py` file. Define your tool with `@tool` and import it into `subagents.py`:

```python
# src/deep_agent/slack_tools.py
from langchain_core.tools import tool

@tool
def send_slack_message(channel: str, message: str) -> str:
    """Post a message to a Slack channel. Returns confirmation."""
    ...
```

Then import and use in `subagents.py`:

```python
from deep_agent.slack_tools import send_slack_message
```

If a tool is used by both the orchestrator and a sub-agent (like `think_tool`), define it in `tools.py` and import from there.

### Changing the model

Set `MAIN_MODEL` or `SUMMARIZATION_MODEL` in `.env`. Any `provider:model` string supported by `init_chat_model` works:

```bash
MAIN_MODEL=anthropic:claude-opus-4-7
MAIN_MODEL=ollama/llama3.2
```

---

## Deployment

**Docker (local):**

```bash
uv run langgraph build -t deep-agent-boilerplate
uv run langgraph up
```

Runs at `http://localhost:8123` with a Postgres-backed checkpointer.

**LangSmith (cloud):**

```bash
uv run langgraph deploy
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `deepagents` | Deep Agents framework — middleware, backends, `create_deep_agent` |
| `langchain` / `langchain-core` | LangChain 1.0 LTS |
| `langgraph` | Graph orchestration and HITL interrupt support |
| `langsmith` | Tracing and evaluation |
| `langchain-openai` | OpenAI model provider |
| `langchain-ollama` | Local model provider |
| `langchain-tavily` / `tavily-python` | Web search |
| `markdownify` | HTML → Markdown for search results |
| `google-auth-oauthlib` / `google-api-python-client` | Google Workspace integration |
| `langgraph-cli` | Local dev, build, deploy |
