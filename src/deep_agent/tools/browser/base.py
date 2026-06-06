from dataclasses import dataclass
from typing import Callable

from langchain_core.tools import BaseTool, StructuredTool


@dataclass
class BrowserAdapter:
    name: str
    navigate_fn: Callable[[str], str]
    screenshot_fn: Callable[[], str]
    click_fn: Callable[[int, int], str]
    js_fn: Callable[[str], str]
    page_info_fn: Callable[[], str]

    def as_tools(self) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                func=self.navigate_fn,
                name="navigate",
                description="Navigate to a URL. Returns the page title on success.",
            ),
            StructuredTool.from_function(
                func=self.screenshot_fn,
                name="screenshot",
                description="Capture the current viewport as a base64 PNG. Save large results with write_file().",
            ),
            StructuredTool.from_function(
                func=self.click_fn,
                name="click",
                description="Click at viewport coordinates (x, y). Use js() to find element positions first.",
            ),
            StructuredTool.from_function(
                func=self.js_fn,
                name="js",
                description="Evaluate a JavaScript expression on the current page and return the result.",
            ),
            StructuredTool.from_function(
                func=self.page_info_fn,
                name="page_info",
                description="Return the current page title, URL, and a plain-text excerpt of visible content.",
            ),
        ]
