from deep_agent.tools.document.base import DocumentAdapter
from deep_agent.tools.document.google import ADAPTERS as DOCUMENT_ADAPTERS, google_doc
from deep_agent.tools.reflect.base import think_tool
from deep_agent.tools.search.base import SearchAdapter
from deep_agent.tools.search.tavily import ADAPTERS as SEARCH_ADAPTERS, tavily_news, tavily_web


class TestSearchAdapter:
    def test_tool_name_is_consistent(self):
        assert tavily_web.as_tool().name == "search"
        assert tavily_news.as_tool().name == "search"

    def test_tool_description_matches_adapter(self):
        assert tavily_web.as_tool().description == tavily_web.description
        assert tavily_news.as_tool().description == tavily_news.description

    def test_adapters_have_distinct_descriptions(self):
        assert tavily_web.description != tavily_news.description

    def test_registry_contains_all_adapters(self):
        assert "tavily_web" in SEARCH_ADAPTERS
        assert "tavily_news" in SEARCH_ADAPTERS

    def test_adapter_is_correct_type(self):
        assert isinstance(tavily_web, SearchAdapter)
        assert isinstance(tavily_news, SearchAdapter)

    def test_fn_is_callable(self):
        assert callable(tavily_web.fn)
        assert callable(tavily_news.fn)


class TestDocumentAdapter:
    def test_tool_name_is_consistent(self):
        assert google_doc.as_tool().name == "create_document"

    def test_tool_description_matches_adapter(self):
        assert google_doc.as_tool().description == google_doc.description

    def test_registry_contains_adapter(self):
        assert "google_doc" in DOCUMENT_ADAPTERS

    def test_adapter_is_correct_type(self):
        assert isinstance(google_doc, DocumentAdapter)

    def test_fn_is_callable(self):
        assert callable(google_doc.fn)


class TestThinkTool:
    def test_tool_name(self):
        assert think_tool.name == "think_tool"

    def test_records_reflection(self):
        result = think_tool.invoke({"reflection": "test thought"})
        assert "test thought" in result
