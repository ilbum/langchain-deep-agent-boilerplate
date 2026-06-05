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
- **Context offloading** — the `search` tool runs a fetch → summarize → save pipeline: full page content goes to `StateBackend`; the agent context sees only a ≤150-word summary
- **Declarative HITL** — action-taking sub-agents declare which tools require user approval via `interrupt_on`; the framework handles pause and resume
- **Swappable tool adapters** — each tool capability (search, document, reflect) has a typed adapter; swap implementations at assembly time without touching agent logic

---

## Project structure

```
src/deep_agent/
├── agent.py                  # Orchestrator — wires model, tools, and subagents
├── agents/
│   ├── __init__.py           # Subagent registry — assembles the active list
│   ├── types.py              # SubagentConfig dataclass
│   ├── researcher.py         # research-agent — web search + synthesis
│   └── report_writer.py      # report-writer — creates documents
└── tools/
    ├── search/
    │   ├── base.py           # SearchAdapter — typed adapter + as_tool()
    │   ├── _pipeline.py      # Shared fetch → summarize → save pipeline
    │   ├── tavily.py         # tavily_web, tavily_news adapters
    │   ├── brave.py          # brave_web adapter (requires BRAVE_API_KEY)
    │   └── __init__.py       # SEARCH_ADAPTERS registry
    ├── document/
    │   ├── base.py           # DocumentAdapter — typed adapter + as_tool()
    │   ├── google.py         # google_doc adapter
    │   └── __init__.py       # DOCUMENT_ADAPTERS registry
    └── reflect/
        └── base.py           # think_tool

tests/
├── unit/                     # Fast tests — no API calls, no LangGraph context
│   ├── test_agents.py        # SubagentConfig, subagent factories, adapter injection
│   └── test_tools.py         # Adapter interfaces and registries
├── integration/              # Real API calls — skipped unless -m integration
│   └── test_search_adapters.py
└── evals/                    # LangSmith evals — skipped unless -m langsmith
    └── test_search_evals.py
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
MAX_SEARCH_CALLS=5            # max search calls per research agent

# Brave Search — required only if using the brave_web adapter
BRAVE_API_KEY=...               # Brave Data for AI subscription

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

## Testing

```bash
# Unit tests (no API keys required)
uv run pytest

# Integration tests — real API calls, requires TAVILY_API_KEY / BRAVE_API_KEY
uv run pytest -m integration

# LangSmith evals — requires LANGSMITH_API_KEY
uv run pytest -m langsmith
```

Integration and eval tests are deselected by default. The integration suite stubs `StateBackend` with an in-memory dict so adapters can run outside a LangGraph execution context.

---

## Extending

### Adding a sub-agent

Each sub-agent is a discrete module in `agents/`. Create a new file that exports a `subagent()` function returning a `SubagentConfig`, then register it in `agents/__init__.py`:

```python
# src/deep_agent/agents/slack.py
from deep_agent.agents.types import SubagentConfig
from deep_agent.tools.messaging.slack import slack_adapter

_INSTRUCTIONS = """You post messages to Slack..."""

def subagent(
    messaging=slack_adapter,
) -> SubagentConfig:
    return SubagentConfig(
        name="slack-agent",
        description="Posts a message to a Slack channel",
        system_prompt=_INSTRUCTIONS,
        tools=[messaging.as_tool()],
        interrupt_on={"send_message": True},  # pauses for user approval
    )
```

```python
# src/deep_agent/agents/__init__.py
from deep_agent.agents import researcher, report_writer, slack

subagents: list[dict] = [
    researcher.subagent().to_dict(),
    report_writer.subagent().to_dict(),
    slack.subagent().to_dict(),           # ← add here
]
```

The orchestrator's prompt is automatically updated — `{subagent_listing}` is generated from the `name` and `description` fields at startup.

**Irreversible actions** (sends messages, writes to external systems, deletes data) should declare `interrupt_on`. The framework pauses and asks the user for approval before the tool fires — the user can approve, edit the input, or reject.

### Adding tool adapters

Tools are organised by capability under `tools/`. Each capability has a typed adapter dataclass (`SearchAdapter`, `DocumentAdapter`) and an `as_tool()` method that produces the LangChain tool the sub-agent receives.

**Adding a new adapter to an existing capability** (e.g. a Brave search adapter):

```python
# src/deep_agent/tools/search/brave.py
from deep_agent.tools.search.base import SearchAdapter

def _brave_search(query: str) -> str:
    ...

brave_web = SearchAdapter(
    name="brave_web",
    description="Search the web using Brave Search.",
    fn=_brave_search,
)

ADAPTERS: dict[str, SearchAdapter] = {brave_web.name: brave_web}
```

If your adapter fetches URLs and you want the same fetch → summarize → save behaviour as Tavily, import the shared pipeline from `tools/search/_pipeline.py` instead of reinventing it.

```python
# src/deep_agent/tools/search/__init__.py
from deep_agent.tools.search.tavily import ADAPTERS as _tavily
from deep_agent.tools.search.brave import ADAPTERS as _brave   # ← add here

SEARCH_ADAPTERS = {**_tavily, **_brave}
```

The sub-agent selects which adapter to use:

```python
# Use Brave instead of Tavily for this researcher
researcher.subagent(search=brave_web).to_dict()
```

**Adding a new capability** (e.g. messaging):

1. Create `tools/messaging/base.py` with a `MessagingAdapter` dataclass and `as_tool()`.
2. Create `tools/messaging/slack.py` with a concrete `slack_adapter` instance.
3. Create `tools/messaging/__init__.py` composing the registry.
4. Import the adapter in your sub-agent file.

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
| `langchain-tavily` / `tavily-python` | Tavily web search adapter |
| `httpx` | HTTP client used by the Brave search adapter |
| `markdownify` | HTML → Markdown conversion in the search pipeline |
| `google-auth-oauthlib` / `google-api-python-client` | Google Workspace integration |
| `playwright` | Optional headless browser for web scraping |
| `langgraph-cli` | Local dev, build, deploy |
| `agentevals` (test) | Agent evaluation utilities for LangSmith evals |

---

## Acknowledgements

This boilerplate builds on two LangChain projects:

- **[deep-agents-from-scratch](https://github.com/langchain-ai/deep-agents-from-scratch)** — the reference implementation this project learned its patterns from: sub-agent isolation, virtual filesystem offloading, and the gather → synthesize → act orchestration loop.
- **[deepagents](https://github.com/langchain-ai/deepagents)** — the SDK used under the hood (`create_deep_agent`, middleware wiring, `StateBackend`). Licensed MIT.
