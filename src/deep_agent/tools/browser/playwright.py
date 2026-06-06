import base64
import threading

from playwright.sync_api import TimeoutError as PlaywrightTimeout, sync_playwright

from deep_agent.tools.browser.base import BrowserAdapter


class _PlaywrightBrowser:
    """One Playwright session per thread — safe for parallel sub-agent execution."""

    def __init__(self):
        self._local = threading.local()

    def _ensure_page(self):
        if not getattr(self._local, "pw", None):
            self._local.pw = sync_playwright().start()
            self._local.browser = self._local.pw.chromium.launch(headless=True)
            self._local.page = self._local.browser.new_page()

    def navigate(self, url: str) -> str:
        self._ensure_page()
        try:
            self._local.page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except PlaywrightTimeout:
            pass
        return f"Navigated to {url}. Title: {self._local.page.title()}"

    def screenshot(self) -> str:
        self._ensure_page()
        return base64.b64encode(self._local.page.screenshot()).decode()

    def click(self, x: int, y: int) -> str:
        self._ensure_page()
        self._local.page.mouse.click(x, y)
        try:
            self._local.page.wait_for_load_state("domcontentloaded", timeout=3000)
        except PlaywrightTimeout:
            pass
        return f"Clicked at ({x}, {y}). Current page: {self._local.page.title()} — {self._local.page.url}"

    def js(self, expression: str) -> str:
        self._ensure_page()
        try:
            return str(self._local.page.evaluate(expression))
        except Exception as e:
            return f"JavaScript error: {e}"

    def page_info(self) -> str:
        self._ensure_page()
        title = self._local.page.title()
        url = self._local.page.url
        try:
            text = self._local.page.inner_text("body")[:3000]
        except Exception:
            text = "(could not extract page text)"
        return f"Title: {title}\nURL: {url}\n\n{text}"


_session = _PlaywrightBrowser()

playwright_browser = BrowserAdapter(
    name="playwright_browser",
    navigate_fn=_session.navigate,
    screenshot_fn=_session.screenshot,
    click_fn=_session.click,
    js_fn=_session.js,
    page_info_fn=_session.page_info,
)
