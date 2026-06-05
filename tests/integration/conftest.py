import os

import pytest


@pytest.fixture(autouse=True)
def require_tavily_key():
    if not os.environ.get("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY not set")
