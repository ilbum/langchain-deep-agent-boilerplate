"""Tavily search adapters.

Exports:
  tavily_web   — general web search
  tavily_news  — recent news articles
  ADAPTERS     — registry dict keyed by adapter name
"""

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
from tavily import TavilyClient

from deep_agent.tools.search.base import SearchAdapter

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
_tavily_client = TavilyClient()
_http_client = httpx.Client(timeout=30.0)


class _Summary(BaseModel):
    filename: str = Field(description="Name of the file to store.")
    summary: str = Field(description="Key learnings from the webpage.")


def _get_today_str() -> str:
    return datetime.now().strftime("%a %b %-d, %Y")


def _run_tavily(query: str, topic: str, max_results: int) -> dict:
    return _tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=True,
        topic=topic,
    )


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


def _process_results(results: dict) -> list[dict]:
    processed = []
    for result in results.get("results", []):
        url = result["url"]
        try:
            response = _http_client.get(url)
            if response.status_code == 200:
                raw_content = markdownify(response.text)
                summary_obj = _summarize(raw_content)
            else:
                raw_content = result.get("raw_content", "")
                summary_obj = _Summary(
                    filename="URL_error.md",
                    summary=result.get("content", "Error reading URL; try another search."),
                )
        except (httpx.TimeoutException, httpx.RequestError):
            raw_content = result.get("raw_content", "")
            summary_obj = _Summary(
                filename="connection_error.md",
                summary=result.get("content", "Could not fetch URL (timeout/connection error). Try another search."),
            )

        uid = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("ascii")[:8]
        name, ext = os.path.splitext(summary_obj.filename)
        summary_obj.filename = f"{name}_{uid}{ext}"

        processed.append({
            "url": url,
            "title": result["title"],
            "summary": summary_obj.summary,
            "filename": summary_obj.filename,
            "raw_content": raw_content,
        })
    return processed


def _search(query: str, topic: str, max_results: int = 1) -> str:
    backend = StateBackend()
    raw = _run_tavily(query, topic=topic, max_results=max_results)
    results = _process_results(raw)

    saved_files = []
    summaries = []
    for result in results:
        filename = result["filename"]
        file_content = f"""# Search Result: {result['title']}

**URL:** {result['url']}
**Query:** {query}
**Date:** {_get_today_str()}

## Summary
{result['summary']}

## Raw Content
{result['raw_content'] if result['raw_content'] else 'No raw content available'}
"""
        backend.write(f"/{filename}", file_content)
        saved_files.append(filename)
        summaries.append(f"- {filename}: {result['summary']}...")

    return f"""🔍 Found {len(results)} result(s) for '{query}':

{chr(10).join(summaries)}

Files: {', '.join(saved_files)}
💡 Use read_file() to access full details when needed."""


def _web_search(query: str) -> str:
    return _search(query, topic="general")


def _news_search(query: str) -> str:
    return _search(query, topic="news")


tavily_web = SearchAdapter(
    name="tavily_web",
    description="Search the general web for factual information, research, and background context.",
    fn=_web_search,
)

tavily_news = SearchAdapter(
    name="tavily_news",
    description="Search for recent news articles and current events.",
    fn=_news_search,
)

ADAPTERS: dict[str, SearchAdapter] = {a.name: a for a in [tavily_web, tavily_news]}
