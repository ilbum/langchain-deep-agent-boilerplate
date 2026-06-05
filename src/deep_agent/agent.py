import os
from datetime import datetime

from deepagents import create_deep_agent

from deep_agent.google_workspace_tools import create_google_doc
from deep_agent.prompts import (
    REPORT_WRITER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    SUBAGENT_USAGE_INSTRUCTIONS,
)
from deep_agent.research_tools import tavily_search, think_tool

graph = create_deep_agent(
    model=os.environ.get("MAIN_MODEL", "openai:gpt-5.5"),
    tools=[tavily_search, think_tool],
    subagents=[
        {
            "name": "research-agent",
            "description": "Conducts web research on a specific topic and returns a full findings report",
            "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=datetime.now().strftime("%Y-%m-%d")),
        },
        {
            "name": "report-writer",
            "description": "Takes a research report and creates a formatted Google Doc in Drive, returning the document URL",
            "system_prompt": REPORT_WRITER_INSTRUCTIONS,
            "tools": [create_google_doc],
        },
    ],
    system_prompt=SUBAGENT_USAGE_INSTRUCTIONS.format(
        max_concurrent_research_units=3,
        max_researcher_iterations=5,
    ),
)
