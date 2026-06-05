import pytest

from deep_agent.agents import report_writer, researcher
from deep_agent.agents.types import SubagentConfig
from deep_agent.tools.document.google import google_doc
from deep_agent.tools.search.tavily import tavily_news, tavily_web


class TestSubagentConfig:
    def test_requires_name(self):
        with pytest.raises(ValueError, match="name"):
            SubagentConfig(name="", description="x", system_prompt="x", tools=["x"])

    def test_requires_tools(self):
        with pytest.raises(ValueError, match="tools"):
            SubagentConfig(name="x", description="x", system_prompt="x", tools=[])

    def test_interrupt_on_defaults_empty(self):
        config = SubagentConfig(name="x", description="x", system_prompt="x", tools=["x"])
        assert config.interrupt_on == {}

    def test_to_dict_omits_empty_interrupt_on(self):
        config = SubagentConfig(name="x", description="x", system_prompt="x", tools=["x"])
        assert "interrupt_on" not in config.to_dict()

    def test_to_dict_includes_interrupt_on_when_set(self):
        config = SubagentConfig(
            name="x", description="x", system_prompt="x",
            tools=["x"], interrupt_on={"my_tool": True},
        )
        assert config.to_dict()["interrupt_on"] == {"my_tool": True}

    def test_to_dict_has_required_keys(self):
        d = SubagentConfig(name="x", description="x", system_prompt="x", tools=["x"]).to_dict()
        assert all(k in d for k in ["name", "description", "system_prompt", "tools"])


class TestResearcherSubagent:
    def test_returns_subagent_config(self):
        assert isinstance(researcher.subagent(), SubagentConfig)

    def test_default_search_tool_name(self):
        config = researcher.subagent()
        assert any(t.name == "search" for t in config.tools)

    def test_default_adapter_is_tavily_web(self):
        config = researcher.subagent()
        search_tool = next(t for t in config.tools if t.name == "search")
        assert search_tool.description == tavily_web.description

    def test_accepts_custom_search_adapter(self):
        config = researcher.subagent(search=tavily_news)
        search_tool = next(t for t in config.tools if t.name == "search")
        assert search_tool.description == tavily_news.description

    def test_max_search_calls_reflected_in_prompt(self):
        config = researcher.subagent(max_search_calls=2)
        assert "2" in config.system_prompt

    def test_think_tool_included(self):
        config = researcher.subagent()
        assert any(t.name == "think_tool" for t in config.tools)


class TestReportWriterSubagent:
    def test_returns_subagent_config(self):
        assert isinstance(report_writer.subagent(), SubagentConfig)

    def test_default_document_tool_name(self):
        config = report_writer.subagent()
        assert any(t.name == "create_document" for t in config.tools)

    def test_accepts_custom_document_adapter(self):
        config = report_writer.subagent(document=google_doc)
        assert any(t.name == "create_document" for t in config.tools)
