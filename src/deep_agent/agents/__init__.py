"""Subagent registry.

To add a new subagent:
  1. Create agents/<name>.py with a subagent() -> SubagentConfig function.
  2. Import and call it here.

Tool modules follow the convention: one *_tools.py file per integration
(e.g. slack_tools.py, email_tools.py). Tools shared across agents live in tools.py.
"""

from deep_agent.agents import report_writer, researcher
from deep_agent.agents.types import SubagentConfig  # noqa: F401 — re-export

subagents: list[dict] = [
    researcher.subagent().to_dict(),
    report_writer.subagent().to_dict(),
]
