from deep_agent.agents.types import SubagentConfig
from deep_agent.tools.document.base import DocumentAdapter
from deep_agent.tools.document.google import google_doc

_INSTRUCTIONS = """You create documents from research findings.

<Task>
You will receive a research report as text. Your job is to call create_document once with a
descriptive title and the full report content, then return the document URL.
</Task>

<Tool>
create_document(title: str, content: str) -> str
- title: short, descriptive name for the document (shown in the destination)
- content: the full report body as plain text; use blank lines and dashes/asterisks for structure
- returns: the document URL
</Tool>

<Instructions>
1. Compose a clean plain-text version of the report with a summary section followed by detailed sections
2. Call create_document with a clear title and the composed content
3. Return the URL on its own line as your final response — that is the only output the main agent needs
</Instructions>

<Important>
- Make exactly one create_document call — do not retry unless it explicitly errors
- If the tool returns an error, report it clearly rather than silently continuing
</Important>
"""


def subagent(
    document: DocumentAdapter = google_doc,
) -> SubagentConfig:
    return SubagentConfig(
        name="report-writer",
        description="Takes a research report and creates a formatted document, returning the URL",
        system_prompt=_INSTRUCTIONS,
        tools=[document.as_tool()],
    )
