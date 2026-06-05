# deep-agent-boilerplate

A production-ready boilerplate for building **Deep Agents** — multi-step AI agents that plan, delegate, research, and write — on top of LangGraph and LangChain.

Deep Agents go beyond simple ReAct loops. They maintain a task list, offload context to a virtual filesystem, and delegate specialized work to isolated sub-agents — keeping each agent's context lean and focused.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     Main Agent                       │
│                                                      │
│  SDK-managed (automatic)                             │
│  ├── write_todos              [TodoListMiddleware]   │
│  ├── ls / read_file /         [FilesystemMiddleware] │
│  │   write_file / edit_file                         │
│  └── task() ──► Sub-agent    [SubAgentMiddleware]    │
│                  (isolated context)                  │
│                                                      │
│  Custom tools                                        │
│  ├── tavily_search  — search + summarize + save      │
│  └── think_tool     — reflection checkpoint          │
└──────────────────────────────────────────────────────┘
```

**Key design patterns:**

- **SDK-managed middleware** — todo list, filesystem, and sub-agent delegation are provided automatically by `create_deep_agent()`; no boilerplate wiring needed
- **Context isolation** — sub-agents receive only their task description, not the parent's message history
- **Context offloading** — `tavily_search` saves full page content to the shared filesystem via `StateBackend`; the main agent's context sees only a short summary
- **Reflection checkpoints** — `think_tool()` creates deliberate pauses to prevent runaway search loops

---

## Project structure

```
src/deep_agent/
├── agent.py          # Entry point — wires model, tools, and subagents
├── prompts.py        # System prompts for main agent and research subagent
└── research_tools.py # tavily_search, think_tool, HTML→Markdown processing
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
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Models (optional — these are the defaults)
MAIN_MODEL=openai:gpt-5.5
SUMMARIZATION_MODEL=openai:gpt-5.4-mini

# Optional — enables LangSmith tracing
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

## Building your agent

`agent.py` is the only file you need to edit to configure the graph:

```python
import os
from datetime import datetime
from deepagents import create_deep_agent
from deep_agent.prompts import RESEARCHER_INSTRUCTIONS, SUBAGENT_USAGE_INSTRUCTIONS
from deep_agent.research_tools import tavily_search, think_tool

graph = create_deep_agent(
    model=os.environ.get("MAIN_MODEL", "openai:gpt-5.5"),
    tools=[tavily_search, think_tool],
    subagents=[
        {
            "name": "research-agent",
            "description": "Conducts web research on a specific topic and saves findings to files",
            "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=datetime.now().strftime("%Y-%m-%d")),
        }
    ],
    system_prompt=SUBAGENT_USAGE_INSTRUCTIONS.format(
        max_concurrent_research_units=3,
        max_researcher_iterations=5,
    ),
)
```

`create_deep_agent()` automatically includes:
- `TodoListMiddleware` — `write_todos` tool + `todos` state
- `FilesystemMiddleware` — `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` + `files` state
- `SubAgentMiddleware` — `task` tool that dispatches to declared subagents
- `SummarizationMiddleware`, `PatchToolCallsMiddleware`

---

## How an agent run works

1. Agent receives a task and calls `write_todos()` to plan its steps
2. For research tasks, it delegates via `task(agent="research-agent", description="…")`
3. The research subagent calls `tavily_search()` — which fetches pages, summarizes them, and saves full content to `StateBackend`
4. The research subagent uses `think_tool()` to reflect before deciding whether to search further
5. The parent agent reads findings with `read_file()` and synthesizes a final answer
6. Todo statuses are updated to `completed` as work finishes

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
| `deepagents` | Deep Agents framework (middleware, backends, `create_deep_agent`) |
| `langchain` / `langchain-core` | LangChain 1.0 LTS |
| `langgraph` | Graph orchestration |
| `langsmith` | Tracing and evaluation |
| `langchain-openai` | OpenAI model provider |
| `langchain-ollama` | Local model provider |
| `langchain-tavily` / `tavily-python` | Web search |
| `markdownify` | HTML → Markdown for search results |
| `playwright` | Browser automation |
| `langgraph-cli` | Local dev, build, deploy |

---

## Extending

**Add a tool** — define a function with `@tool` in `research_tools.py` (or a new file) and add it to the `tools` list in `agent.py`.

**Add a sub-agent** — add an entry to the `subagents` list in `agent.py`. Each sub-agent inherits the main agent's tools unless it declares its own `tools` key.

**Change the model** — set `MAIN_MODEL` or `SUMMARIZATION_MODEL` in `.env`. Any `provider:model` string supported by `init_chat_model` works (e.g. `anthropic:claude-opus-4-7`).

**Persistent memory** — use `StoreBackend` or `CompositeBackend` from the Deep Agents memory system for cross-thread state.
