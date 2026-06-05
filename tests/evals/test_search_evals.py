import pytest
from langsmith import testing as t

from deep_agent.tools.search.tavily import tavily_news, tavily_web

_QUERIES = [
    "latest developments in AI safety research",
    "LangGraph agent architecture patterns",
    "Python async best practices 2025",
]

# When brave_web is added to tools/search/brave.py, append it here —
# no other change needed.
_ADAPTERS = [tavily_web, tavily_news]


@pytest.mark.langsmith
@pytest.mark.parametrize("adapter", _ADAPTERS, ids=lambda a: a.name)
@pytest.mark.parametrize("query", _QUERIES)
def test_search_adapter_returns_results(adapter, query):
    t.log_inputs({"adapter": adapter.name, "query": query})

    result = adapter.fn(query)

    t.log_outputs({"result": result})
    assert len(result) > 100
