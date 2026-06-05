from dataclasses import dataclass
from typing import Callable

from langchain_core.tools import BaseTool, StructuredTool


@dataclass
class SearchAdapter:
    name: str
    description: str
    fn: Callable[[str], str]

    def as_tool(self) -> BaseTool:
        return StructuredTool.from_function(
            func=self.fn,
            name="search",
            description=self.description,
        )
