"""Shared fetch-summarize-save pipeline used by all search adapters."""

import base64
import os
import uuid
from datetime import datetime

import httpx
from deepagents.backends.state import StateBackend
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from markdownify import markdownify
from pydantic import BaseModel, Field

_SUMMARIZE_PROMPT = """You are creating a minimal summary for research steering - your goal is to help an agent know what information it has collected, NOT to preserve all details.

<webpage_content>
{webpage_content}
</webpage_content>

Create a VERY CONCISE summary focusing on:
1. Main topic/subject in 1-2 sentences
2. Key information type (facts, tutorial, news, analysis, etc.)
3. Most significant 1-2 findings or points

Keep the summary under 150 words total. The agent needs to know what's in this file to decide if it should search for more information or use this source.

Generate a descriptive filename that indicates the content type and topic (e.g., "mcp_protocol_overview.md", "ai_safety_research_2024.md").

Output format:
```json
{{
   "filename": "descriptive_filename.md",
   "summary": "Very brief summary under 150 words focusing on main topic and key findings"
}}
```

Today's date: {date}
"""

_summarization_model = init_chat_model(model=os.environ.get("SUMMARIZATION_MODEL", "openai:gpt-5.4-mini"))
_http_client = httpx.Client(timeout=30.0)


class _Summary(BaseModel):
    filename: str = Field(description="Name of the file to store.")
    summary: str = Field(description="Key learnings from the webpage.")


def _get_today_str() -> str:
    return datetime.now().strftime("%a %b %-d, %Y")


def _summarize(webpage_content: str) -> _Summary:
    try:
        structured_model = _summarization_model.with_structured_output(_Summary)
        return structured_model.invoke(
            [HumanMessage(content=_SUMMARIZE_PROMPT.format(
                webpage_content=webpage_content, date=_get_today_str()
            ))]
        )
    except Exception:
        return _Summary(
            filename="search_result.md",
            summary=webpage_content[:1000] + ("..." if len(webpage_content) > 1000 else ""),
        )


def _fetch_and_summarize(url: str, fallback_content: str) -> tuple[str, _Summary]:
    try:
        response = _http_client.get(url)
        if response.status_code == 200:
            raw_content = markdownify(response.text)
            return raw_content, _summarize(raw_content)
        return fallback_content, _Summary(
            filename="URL_error.md",
            summary=fallback_content or "Error reading URL; try another search.",
        )
    except (httpx.TimeoutException, httpx.RequestError):
        return fallback_content, _Summary(
            filename="connection_error.md",
            summary=fallback_content or "Could not fetch URL (timeout/connection error). Try another search.",
        )


def run_pipeline(query: str, items: list[dict]) -> str:
    """Fetch, summarize, and save search results to StateBackend.

    items: list of {"url": str, "title": str, "fallback_content": str}
    """
    backend = StateBackend()
    saved_files = []
    summaries = []
    today = _get_today_str()

    for item in items:
        url = item["url"]
        title = item["title"]
        fallback = item.get("fallback_content", "")

        raw_content, summary_obj = _fetch_and_summarize(url, fallback)

        uid = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("ascii")[:8]
        name, ext = os.path.splitext(summary_obj.filename)
        filename = f"{name}_{uid}{ext}"

        file_content = f"""# Search Result: {title}

**URL:** {url}
**Query:** {query}
**Date:** {today}

## Summary
{summary_obj.summary}

## Raw Content
{raw_content if raw_content else 'No raw content available'}
"""
        backend.write(f"/{filename}", file_content)
        saved_files.append(filename)
        summaries.append(f"- {filename}: {summary_obj.summary}...")

    return f"""🔍 Found {len(items)} result(s) for '{query}':

{chr(10).join(summaries)}

Files: {', '.join(saved_files)}
💡 Use read_file() to access full details when needed."""
