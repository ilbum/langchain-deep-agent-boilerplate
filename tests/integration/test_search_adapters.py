import pytest

from deep_agent.tools.search.tavily import tavily_news, tavily_web


@pytest.mark.integration
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
