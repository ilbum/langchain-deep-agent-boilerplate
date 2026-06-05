import os

import pytest


@pytest.fixture
def require_tavily_key():
    if not os.environ.get("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY not set")


@pytest.fixture
def require_brave_key():
    if not os.environ.get("BRAVE_API_KEY"):
        pytest.skip("BRAVE_API_KEY not set")
