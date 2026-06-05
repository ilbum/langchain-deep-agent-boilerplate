import os

import pytest


@pytest.fixture(scope="session")
def langsmith_experiment_metadata():
    return {
        "model": os.environ.get("MAIN_MODEL", "unknown"),
        "environment": os.environ.get("ENV", "local"),
    }
