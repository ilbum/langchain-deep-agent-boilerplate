from deep_agent.tools.document.base import DocumentAdapter  # noqa: F401 — re-export
from deep_agent.tools.document.google import ADAPTERS as _google

DOCUMENT_ADAPTERS: dict[str, DocumentAdapter] = {**_google}
