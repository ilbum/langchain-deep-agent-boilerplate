import os

from deepagents import create_deep_agent

from deep_agent.prompts import SUBAGENT_USAGE_INSTRUCTIONS
from deep_agent.research_tools import tavily_search, think_tool
from deep_agent.subagents import subagents

graph = create_deep_agent(
    model=os.environ.get("MAIN_MODEL", "openai:gpt-5.5"),
    tools=[tavily_search, think_tool],
    subagents=subagents,
    system_prompt=SUBAGENT_USAGE_INSTRUCTIONS.format(
        max_concurrent_research_units=3,
        max_researcher_iterations=5,
    ),
)
