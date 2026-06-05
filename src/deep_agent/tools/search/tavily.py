"""Tavily search adapters.

Exports:
  tavily_web   — general web search
  tavily_news  — recent news articles
  ADAPTERS     — registry dict keyed by adapter name
"""

from tavily import TavilyClient

from deep_agent.tools.search._pipeline import run_pipeline
from deep_agent.tools.search.base import SearchAdapter

_tavily_client = TavilyClient()


def _run_tavily(query: str, topic: str, max_results: int = 1) -> str:
    raw = _tavily_client.search(query, max_results=max_results, include_raw_content=True, topic=topic)
    items = [
        {"url": r["url"], "title": r["title"], "fallback_content": r.get("raw_content", r.get("content", ""))}
        for r in raw.get("results", [])
    ]
    return run_pipeline(query, items)


def _web_search(query: str) -> str:
    return _run_tavily(query, topic="general")


def _news_search(query: str) -> str:
    return _run_tavily(query, topic="news")


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
