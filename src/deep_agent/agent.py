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
