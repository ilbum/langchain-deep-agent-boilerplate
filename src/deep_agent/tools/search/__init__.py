from deep_agent.tools.search.base import SearchAdapter  # noqa: F401 — re-export
from deep_agent.tools.search.brave import ADAPTERS as _brave
from deep_agent.tools.search.tavily import ADAPTERS as _tavily

SEARCH_ADAPTERS: dict[str, SearchAdapter] = {**_tavily, **_brave}
