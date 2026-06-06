import os
import re

from deep_agent.agents.types import SubagentConfig
from deep_agent.tools.browser.base import BrowserAdapter
from deep_agent.tools.reflect.base import think_tool


def _browser_from_env() -> BrowserAdapter | None:
    name = os.environ.get("BROWSER_ADAPTER")
    if not name:
        return None
    from deep_agent.tools.browser import BROWSER_ADAPTERS
    adapter = BROWSER_ADAPTERS.get(name)
    if adapter is None:
        raise ValueError(f"Unknown BROWSER_ADAPTER '{name}'. Available: {list(BROWSER_ADAPTERS)}")
    return adapter


def _describe_execute(tool_call, state, runtime) -> str:
    command = tool_call["args"].get("command", "")

    # Extract heredoc body
    match = re.search(r"<<['\"]?PY['\"]?\n(.*?)\nPY\s*$", command, re.DOTALL)
    body = match.group(1) if match else command

    parts = []

    urls = re.findall(r"(?:new_tab|goto_url)\(['\"]([^'\"]+)['\"]", body)
    if urls:
        parts.append(f"navigate to {urls[0]}")

    if "capture_screenshot" in body:
        parts.append("take screenshot")
    if re.search(r"\bjs\(", body):
        parts.append("run JavaScript")
    if "click_at_xy" in body:
        parts.append("click element")
    if "page_info" in body:
        parts.append("get page info")
    if "write_file" in body:
        parts.append("save to file")

    if parts:
        return f"Browser agent wants to: {', '.join(parts)}"

    # Fallback: first non-comment non-blank line
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return f"Browser execute: {line[:200]}"

    return "Browser execute command"


def _describe_navigate(tool_call, state, runtime) -> str:
    url = tool_call["args"].get("url", "")
    return f"Browser agent wants to navigate to: {url}"


def _describe_click(tool_call, state, runtime) -> str:
    x = tool_call["args"].get("x", 0)
    y = tool_call["args"].get("y", 0)
    return f"Browser agent wants to click at coordinates ({x}, {y})"


_BROWSER_HARNESS_INSTRUCTIONS = """You are a browser automation agent. You control a web browser to complete tasks by calling the `execute` tool with browser-harness commands.

<Invocation>
Always call browser-harness using a heredoc to avoid shell quoting issues:

execute(command=\"\"\"browser-harness <<'PY'
# your Python here — helpers are pre-imported
PY\"\"\")

First navigation in a session must use new_tab(url), not goto_url(url). After that, goto_url(url) navigates the current tab.
</Invocation>

<Available Helpers>
Navigation:
  new_tab(url)              — open a new tab and navigate to url
  goto_url(url)             — navigate current tab to url
  wait_for_load()           — wait for page load to settle
  ensure_real_tab()         — recover from stale or internal tab

Inspection:
  page_info()               — returns title, url, and visible text summary
  capture_screenshot()      — returns base64 PNG of the current viewport
  js(expression)            — evaluate JavaScript and return result

Interaction:
  click_at_xy(x, y)         — click at viewport coordinates (use after screenshot)
  cdp(method, **params)     — raw Chrome DevTools Protocol call

Cloud browser (headless/parallel):
  start_remote_daemon(name)                          — start a Browser Use cloud browser
  start_remote_daemon(name, profileName="my-work")  — reuse a saved cloud profile
</Available Helpers>

<Workflow>
1. Use think_tool to plan your approach before acting
2. Open the page with new_tab(url), then wait_for_load()
3. Call capture_screenshot() to see the current state — always use screenshots to find click targets
4. Click with click_at_xy(x, y) using coordinates read from the screenshot
5. After every meaningful action, capture_screenshot() to verify the result
6. Use page_info() for a quick text summary; use js() to extract specific DOM values
7. Save large page content or screenshots with write_file() to avoid filling your context
</Workflow>

<Context Offloading>
Screenshots (base64) and full page text can be large. When you capture content you want to reference later:
- Save it: write_file("/browser/screenshot_01.txt", base64_content)
- Return only a short description in your final message

Your final message is the ONLY output the main agent receives. Summarise what you did and what you found — do not reference files you wrote.
</Context Offloading>

<Hard Rules>
- Auth walls: if redirected to a login page, STOP and ask the user for credentials. Never type passwords visible in screenshots.
- Stop after completing the assigned task — don't explore further.
- If browser-harness is not installed or Chrome is not reachable, report the error clearly rather than retrying blindly.
</Hard Rules>
"""

_PLAYWRIGHT_INSTRUCTIONS = """You are a browser automation agent. You control a web browser to complete tasks.

<Workflow>
1. Use think_tool to plan your approach before acting
2. Navigate to the target page with navigate(url)
3. Use page_info() for a text summary of what's on the page
4. Use js() to find element positions: document.querySelector('button').getBoundingClientRect()
5. Click with click(x, y) using the center coordinates from js()
6. After every meaningful action, call page_info() or screenshot() to verify the result
7. Save large content or screenshots with write_file() to avoid filling context
</Workflow>

<Available Tools>
Navigation:
  navigate(url)      — go to a URL; returns page title on success

Inspection:
  page_info()        — get current page title, URL, and visible text (truncated to 3000 chars)
  screenshot()       — capture the current viewport as base64 PNG; save large results with write_file()
  js(expression)     — evaluate JavaScript and return the result

Interaction:
  click(x, y)        — click at viewport coordinates; use js() to get element bounds first
</Workflow>

<Finding Click Targets>
Use js() to get element center coordinates before clicking:
  js("const r = document.querySelector('button[type=submit]').getBoundingClientRect(); `${r.left + r.width/2},${r.top + r.height/2}`")
Then click(x, y) with those values.
</Finding Click Targets>

<Context Offloading>
Screenshots (base64) and full page text can be large. Save content you'll need later:
  write_file("/browser/screenshot_01.txt", base64_content)
Return only a short description in your final message — do not paste raw screenshots or full page dumps.

Your final message is the ONLY output the main agent receives. Summarise what you did and what you found.
</Context Offloading>

<Hard Rules>
- Auth walls: if redirected to a login page, STOP and report. Never handle credentials.
- Stop after completing the assigned task — don't explore further.
- If Playwright is not installed, report the error clearly rather than retrying blindly.
</Hard Rules>
"""


def subagent(browser: BrowserAdapter | None = _browser_from_env()) -> SubagentConfig:
    if browser is not None:
        return SubagentConfig(
            name="browser-agent",
            description="Navigates websites, fills forms, and extracts information from web pages via browser automation",
            system_prompt=_PLAYWRIGHT_INSTRUCTIONS,
            tools=[*browser.as_tools(), think_tool],
            interrupt_on={
                "navigate": {
                    "allowed_decisions": ["approve", "edit", "reject", "respond"],
                    "description": _describe_navigate,
                },
                "click": {
                    "allowed_decisions": ["approve", "edit", "reject", "respond"],
                    "description": _describe_click,
                },
            },
        )

    return SubagentConfig(
        name="browser-agent",
        description="Navigates websites, fills forms, and extracts information from web pages via browser automation",
        system_prompt=_BROWSER_HARNESS_INSTRUCTIONS,
        tools=[think_tool],
        interrupt_on={
            "execute": {
                "allowed_decisions": ["approve", "edit", "reject", "respond"],
                "description": _describe_execute,
            }
        },
    )
