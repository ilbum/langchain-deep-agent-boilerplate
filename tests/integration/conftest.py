import os

import pytest


class _DictBackend:
    def __init__(self):
        self.files = {}

    def write(self, path: str, content: str) -> None:
        self.files[path] = content


@pytest.fixture(autouse=True)
def patch_state_backend(monkeypatch):
    """Replace StateBackend with an in-memory stub so adapters can run outside a LangGraph context."""
    backend = _DictBackend()
    monkeypatch.setattr("deep_agent.tools.search._pipeline.StateBackend", lambda: backend)
    return backend


@pytest.fixture
def require_tavily_key():
    if not os.environ.get("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY not set")


@pytest.fixture
def require_brave_key():
    if not os.environ.get("BRAVE_API_KEY"):
        pytest.skip("BRAVE_API_KEY not set")
