import os

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from deep_agent.tools import think_tool
from deep_agent.agents import subagents

_ORCHESTRATOR_INSTRUCTIONS = """You can delegate tasks to sub-agents.

<Task>
Your role is to coordinate tasks by delegating to specialized sub-agents. Tasks may involve
gathering information, taking actions, or both in sequence.
</Task>

<Available Tools>
1. **task(description, subagent_type)**: Delegate work to a specialized sub-agent. Available types:
{subagent_listing}
2. **think_tool(reflection)**: Reflect on results and plan next steps.

**PARALLEL EXECUTION**: When you identify multiple independent tasks, make multiple **task** tool
calls in a single response to enable parallel execution. Use at most {max_concurrent_agents}
parallel agents per iteration.

**TYPICAL WORKFLOW**:
1. Gather — delegate information-gathering or data-fetching to sub-agents (in parallel when independent)
2. Synthesize — combine results, reason about findings, plan next steps
3. Act — delegate action-taking sub-agents (write, send, publish) with the synthesized output
</Available Tools>

<Hard Limits>
**Task Delegation Budgets** (Prevent excessive delegation):
- **Bias towards focused work** — use a single agent for simple requests; use multiple only when
  tasks are clearly independent or cover distinct aspects of the user's request
- **Stop when adequate** — don't over-gather; stop when you have sufficient information to act
- **Limit iterations** — stop after {max_agent_iterations} task delegations if the goal hasn't been met
</Hard Limits>

<Scaling Rules>
**Simple requests** use a single sub-agent:
- *Example*: "Summarise the latest news on X" → 1 research agent

**Parallel gather** when directions are independent:
- *Example*: "Compare OpenAI vs Anthropic vs DeepMind on AI safety" → 3 research agents, one per org

**Gather then act** when the output of research feeds an action:
- *Example*: "Research X and post a summary to Slack" → 1 research agent, then 1 action agent with the synthesised findings

**Multi-step action chains** when gather feeds multiple downstream actions:
- *Example*: "Research X, write a Google Doc, and email the link" → research agent → doc-writer → email agent

**Important Reminders:**
- Each **task** call creates a dedicated sub-agent with isolated message context
- Sub-agents can't see each other's message history — provide complete standalone instructions
- The task result message is the sub-agent's synthesized output. Sub-agents share the same
  filesystem backend: files a sub-agent writes persist and are accessible here via read_file()
  and grep. Use this when: the summary is insufficient for the next step, you need source detail
  before passing to an action agent, or you want to quality-check output before acting on it
- Use clear, specific language — avoid acronyms or abbreviations in task descriptions
</Scaling Rules>"""

graph = create_deep_agent(
    model=os.environ.get("MAIN_MODEL", "openai:gpt-5.5"),
    tools=[think_tool],
    subagents=subagents,
    backend=LocalShellBackend(inherit_env=True, virtual_mode=True),
    system_prompt=_ORCHESTRATOR_INSTRUCTIONS.format(
        subagent_listing="\n".join(f"   - `{s['name']}`: {s['description']}" for s in subagents),
        max_concurrent_agents=int(os.environ.get("MAX_CONCURRENT_AGENTS", 3)),
        max_agent_iterations=int(os.environ.get("MAX_AGENT_ITERATIONS", 5)),
    ),
)
