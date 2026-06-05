# deep-agent-boilerplate

A production-ready boilerplate for building **Deep Agents** — multi-step AI agents that plan, delegate, research, and write — on top of LangGraph and LangChain.

Deep Agents go beyond simple ReAct loops. They maintain a task list, offload context to a virtual filesystem, and delegate specialized work to isolated sub-agents — keeping each agent's context lean and focused.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                 Deep Agent                  │
│                                             │
│  State                                      │
│  ├── messages   conversation history        │
│  ├── todos      task list + status          │
│  └── files      virtual filesystem          │
│                                             │
│  Tools                                      │
│  ├── write_todos / read_todos               │
│  ├── ls / read_file / write_file            │
│  ├── tavily_search / think_tool             │
│  └── task() ──► Sub-agent (isolated ctx)    │
└─────────────────────────────────────────────┘
```

**Key design patterns:**

- **Context isolation** — sub-agents receive only their task description, not the parent's message history
- **Virtual filesystem** — research results are saved to files, keeping the main context window small
- **Atomic state updates** — tools return LangGraph `Command` objects for safe, conflict-free state mutations
- **`file_reducer`** — merges file state correctly when multiple tools write concurrently
- **Reflection checkpoints** — `think_tool()` creates deliberate pauses to prevent runaway search loops

---

## Project structure

```
src/deep_agent/
├── state.py          # DeepAgentState — todos, files, file_reducer
├── prompts.py        # System prompts and tool descriptions
├── file_tools.py     # ls, read_file, write_file
├── todo_tools.py     # write_todos, read_todos
├── research_tools.py # tavily_search, think_tool, HTML→Markdown processing
└── task_tool.py      # Sub-agent factory with context isolation
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

The boilerplate provides the tools and state — you wire them into a graph. Create `src/deep_agent/agent.py`:

```python
from deepagents import create_deep_agent
from .file_tools import ls, read_file, write_file
from .todo_tools import write_todos, read_todos
from .research_tools import tavily_search, think_tool
from .task_tool import create_task_tool
from .state import DeepAgentState

tools = [write_todos, read_todos, ls, read_file, write_file, tavily_search, think_tool]

graph = create_deep_agent(
    tools=tools,
    state_schema=DeepAgentState,
)
```

Then add a `langgraph.json` at the project root:

```json
{
    "dependencies": ["."],
    "graphs": {
        "agent": "src/deep_agent/agent.py:graph"
    },
    "env": "./.env",
    "python_version": "3.13"
}
```

---

## How an agent run works

1. Agent receives a task and calls `write_todos()` to plan its steps
2. For each todo, it either handles it directly or delegates via `task()`
3. Research tasks use `tavily_search()` to fetch results, `think_tool()` to reflect, and `write_file()` to save findings
4. The parent agent reads results back with `read_file()` and synthesizes a final answer
5. Todo statuses are updated to `completed` as work finishes

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
| `deepagents` | Deep Agents framework |
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

**Add a tool** — define a function with `@tool` and add it to the `tools` list in `agent.py`.

**Add a sub-agent** — pass a `subagents` config list to `create_task_tool()`. Each sub-agent gets its own tool set and model.

**Change the model** — swap the model in `create_deep_agent()`. The boilerplate ships with OpenAI but works with any LangChain-compatible provider.

**Persistent memory** — use `StoreBackend` or `CompositeBackend` from the Deep Agents memory system for cross-thread state.
