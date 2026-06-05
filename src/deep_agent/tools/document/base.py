from dataclasses import dataclass
from typing import Callable

from langchain_core.tools import BaseTool, StructuredTool


@dataclass
class DocumentAdapter:
    name: str
    description: str
    fn: Callable[[str, str], str]  # title, content -> url

    def as_tool(self) -> BaseTool:
        return StructuredTool.from_function(
            func=self.fn,
            name="create_document",
            description=self.description,
        )
