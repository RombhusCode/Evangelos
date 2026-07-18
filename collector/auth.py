"""WhatsApp Web authentication and browser session management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from utils.config import whatsapp_profile_dir


WHATSAPP_WEB_URL = "https://web.whatsapp.com/"


class WhatsAppAuthenticationError(RuntimeError):
    """Raised when WhatsApp Web authentication cannot be completed."""


class PlaywrightStarter(Protocol):
    """Object that can start Playwright."""

    def start(self) -> Playwright:
        """Start and return a Playwright instance."""


class PlaywrightFactory(Protocol):
    """Callable that returns a Playwright starter for dependency injection in tests."""

    def __call__(self) -> PlaywrightStarter:
        """Return a Playwright starter."""


@dataclass(frozen=True)
class WhatsAppAuthConfig:
    """Configuration for WhatsApp Web authentication."""

    profile_dir: Path
    headless: bool = False
    timeout_ms: int = 120_000
    navigation_timeout_ms: int = 60_000
    slow_mo_ms: int = 0

    @classmethod
    def from_settings(cls) -> Self:
        """Build configuration from the application's configuration system."""
        return cls(profile_dir=whatsapp_profile_dir())


class WhatsAppAuthenticator:
    """Provide authenticated WhatsApp Web pages using a persistent browser profile."""

    _authenticated_selectors = (
        "[data-testid='chat-list']",
        "[aria-label='Chat list']",
        "[aria-label='Chats']",
        "div[role='grid']",
    )
    _logged_out_selectors = (
        "canvas[aria-label*='Scan']",
        "canvas",
        "text=Use WhatsApp on your computer",
        "text=Log in to WhatsApp Web",
    )

    def __init__(
        self,
        config: WhatsAppAuthConfig | None = None,
        playwright_factory: PlaywrightFactory = sync_playwright,
    ) -> None:
        self.config = config or WhatsAppAuthConfig.from_settings()
        self._playwright_factory = playwright_factory
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def get_authenticated_page(self) -> Page:
        """Return a WhatsApp Web page, prompting for login only when needed."""
        page = self._get_page()
        self._open_whatsapp(page)

        if self.is_session_valid(page):
            return page

        self._wait_for_login(page)
        return page

    def is_session_valid(self, page: Page | None = None) -> bool:
        """Return whether WhatsApp Web currently appears authenticated."""
        page = page or self._page
        if page is None:
            return False

        try:
            self._wait_for_any_selector(page, self._authenticated_selectors, timeout_ms=5_000)
            return True
        except PlaywrightTimeoutError:
            return False

    def close(self) -> None:
        """Close the browser context and stop Playwright."""
        if self._context is not None:
            self._context.close()
            self._context = None
            self._page = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _get_page(self) -> Page:
        context = self._get_context()
        if self._page is None or self._page.is_closed():
            self._page = context.new_page()
        return self._page

    def _get_context(self) -> BrowserContext:
        if self._context is not None:
            return self._context

        self.config.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = self._playwright_factory().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.config.profile_dir),
            headless=self.config.headless,
            slow_mo=self.config.slow_mo_ms,
        )
        self._context.set_default_timeout(self.config.timeout_ms)
        self._context.set_default_navigation_timeout(self.config.navigation_timeout_ms)
        return self._context

    def _open_whatsapp(self, page: Page) -> None:
        try:
            page.goto(WHATSAPP_WEB_URL, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            raise WhatsAppAuthenticationError("Could not open WhatsApp Web.") from exc

    def _wait_for_login(self, page: Page) -> None:
        try:
            self._wait_for_any_selector(page, self._logged_out_selectors, timeout_ms=15_000)
        except PlaywrightTimeoutError:
            pass

        try:
            self._wait_for_any_selector(
                page,
                self._authenticated_selectors,
                timeout_ms=self.config.timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise WhatsAppAuthenticationError(
                "WhatsApp Web is not authenticated. Scan the QR code, then try again."
            ) from exc

    def _wait_for_any_selector(
        self,
        page: Page,
        selectors: tuple[str, ...],
        timeout_ms: int,
    ) -> str:
        last_error: PlaywrightTimeoutError | None = None
        per_selector_timeout = max(1, timeout_ms // len(selectors))

        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=per_selector_timeout)
                return selector
            except PlaywrightTimeoutError as exc:
                last_error = exc

        raise last_error or PlaywrightTimeoutError("No matching selector found.")
