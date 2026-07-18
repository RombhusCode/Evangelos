"""Tests for WhatsApp Web authentication session management."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from collector.auth import (
    WHATSAPP_WEB_URL,
    WhatsAppAuthenticationError,
    WhatsAppAuthenticator,
    WhatsAppAuthConfig,
)


class FakePage:
    def __init__(self, visible_selectors: set[str] | None = None) -> None:
        self.visible_selectors = visible_selectors or set()
        self.selector_failures: dict[str, int] = {}
        self.goto_calls: list[tuple[str, str | None]] = []
        self.waited_selectors: list[str] = []
        self.closed = False

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.goto_calls.append((url, wait_until))

    def wait_for_selector(self, selector: str, timeout: int) -> None:
        self.waited_selectors.append(selector)
        failures_left = self.selector_failures.get(selector, 0)
        if failures_left > 0:
            self.selector_failures[selector] = failures_left - 1
            raise PlaywrightTimeoutError(f"{selector} not visible yet")
        if selector not in self.visible_selectors:
            raise PlaywrightTimeoutError(f"{selector} not visible")

    def is_closed(self) -> bool:
        return self.closed


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.default_timeout: int | None = None
        self.default_navigation_timeout: int | None = None
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def set_default_timeout(self, timeout: int) -> None:
        self.default_timeout = timeout

    def set_default_navigation_timeout(self, timeout: int) -> None:
        self.default_navigation_timeout = timeout

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, context: FakeContext) -> None:
        self.context = context
        self.launch_kwargs: dict[str, object] | None = None

    def launch_persistent_context(self, **kwargs: object) -> FakeContext:
        self.launch_kwargs = kwargs
        return self.context


class FakePlaywright:
    def __init__(self, context: FakeContext) -> None:
        self.chromium = FakeChromium(context)
        self.stopped = False

    def start(self) -> "FakePlaywright":
        return self

    def stop(self) -> None:
        self.stopped = True


def make_auth(
    tmp_path: Path,
    page: FakePage,
    timeout_ms: int = 90_000,
) -> tuple[WhatsAppAuthenticator, FakePlaywright, FakeContext]:
    context = FakeContext(page)
    playwright = FakePlaywright(context)
    config = WhatsAppAuthConfig(
        profile_dir=tmp_path / "whatsapp-profile",
        timeout_ms=timeout_ms,
        navigation_timeout_ms=30_000,
    )
    auth = WhatsAppAuthenticator(config=config, playwright_factory=lambda: playwright)
    return auth, playwright, context


def test_reuses_valid_persistent_session(tmp_path: Path) -> None:
    page = FakePage(visible_selectors={"[aria-label='Chat list']"})
    auth, playwright, context = make_auth(tmp_path, page)

    authenticated_page = auth.get_authenticated_page()

    assert authenticated_page is page
    assert page.goto_calls == [(WHATSAPP_WEB_URL, "domcontentloaded")]
    assert playwright.chromium.launch_kwargs == {
        "user_data_dir": str(tmp_path / "whatsapp-profile"),
        "headless": False,
        "slow_mo": 0,
    }
    assert context.default_timeout == 90_000
    assert context.default_navigation_timeout == 30_000
    assert (tmp_path / "whatsapp-profile").is_dir()


def test_waits_for_login_when_session_is_logged_out(tmp_path: Path) -> None:
    page = FakePage(visible_selectors={"canvas", "[data-testid='chat-list']"})
    page.selector_failures["[data-testid='chat-list']"] = 1
    auth, _, _ = make_auth(tmp_path, page)

    assert auth.get_authenticated_page() is page
    assert "canvas" in page.waited_selectors
    assert "[data-testid='chat-list']" in page.waited_selectors


def test_raises_when_login_does_not_complete(tmp_path: Path) -> None:
    page = FakePage(visible_selectors={"canvas"})
    auth, _, _ = make_auth(tmp_path, page, timeout_ms=100)

    with pytest.raises(WhatsAppAuthenticationError):
        auth.get_authenticated_page()


def test_close_releases_browser_resources(tmp_path: Path) -> None:
    page = FakePage(visible_selectors={"[aria-label='Chat list']"})
    auth, playwright, context = make_auth(tmp_path, page)

    auth.get_authenticated_page()
    auth.close()

    assert context.closed is True
    assert playwright.stopped is True
