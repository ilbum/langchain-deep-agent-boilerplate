import pytest

from deep_agent.tools.search.brave import brave_web
from deep_agent.tools.search.tavily import tavily_news, tavily_web


@pytest.mark.integration
@pytest.mark.usefixtures("require_tavily_key")
class TestTavilyAdapters:
    def test_tavily_web_returns_results(self):
        result = tavily_web.fn("LangChain deep agents framework")
        assert "Found" in result
        assert len(result) > 0

    def test_tavily_news_returns_results(self):
        result = tavily_news.fn("AI news today")
        assert "Found" in result

    def test_tavily_web_saves_files(self):
        result = tavily_web.fn("Python async programming")
        assert "Files:" in result

    def test_tavily_web_and_news_return_different_results(self):
        query = "OpenAI"
        web_result = tavily_web.fn(query)
        news_result = tavily_news.fn(query)
        assert web_result != news_result


@pytest.mark.integration
@pytest.mark.usefixtures("require_brave_key")
class TestBraveAdapters:
    def test_brave_web_returns_results(self):
        result = brave_web.fn("LangChain deep agents framework")
        assert "Found" in result
        assert len(result) > 0

    def test_brave_web_saves_files(self):
        result = brave_web.fn("Python async programming")
        assert "Files:" in result

    def test_brave_web_missing_key_returns_message(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        result = brave_web.fn("anything")
        assert "BRAVE_API_KEY" in result
