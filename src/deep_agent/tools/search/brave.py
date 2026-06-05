"""Brave search adapter.

Exports:
  brave_web  — web search via Brave Search API
  ADAPTERS   — registry dict keyed by adapter name

Requires BRAVE_API_KEY environment variable (Brave Data for AI subscription).
"""

import os

import httpx

from deep_agent.tools.search._pipeline import run_pipeline
from deep_agent.tools.search.base import SearchAdapter

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_brave_client = httpx.Client(timeout=30.0)


def _brave_web_search(query: str, count: int = 5) -> str:
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return "BRAVE_API_KEY not configured — set this environment variable to use Brave Search."

    response = _brave_client.get(
        _BRAVE_SEARCH_URL,
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        params={"q": query, "count": count},
    )
    response.raise_for_status()
    data = response.json()

    items = [
        {"url": r["url"], "title": r["title"], "fallback_content": r.get("description", "")}
        for r in data.get("web", {}).get("results", [])
    ]
    return run_pipeline(query, items)


brave_web = SearchAdapter(
    name="brave_web",
    description="Search the web using Brave Search, a privacy-focused independent search index.",
    fn=_brave_web_search,
)

ADAPTERS: dict[str, SearchAdapter] = {brave_web.name: brave_web}
