"""Tests for WhatsApp Web chat discovery."""

from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from collector.whatsapp import ChatSummary, WhatsAppDiscoveryError, discover_chats


class FakeRow:
    def __init__(
        self,
        text: str,
        attributes: dict[str, str | None] | None = None,
        child_attributes: dict[str, list[dict[str, str | None]]] | None = None,
        fail_read: bool = False,
    ) -> None:
        self.text = text
        self.attributes = attributes or {}
        self.child_attributes = child_attributes or {}
        self.fail_read = fail_read

    def inner_text(self, timeout: int) -> str:
        if self.fail_read:
            raise PlaywrightError("row detached")
        return self.text

    def get_attribute(self, attribute: str) -> str | None:
        return self.attributes.get(attribute)

    def locator(self, selector: str) -> "FakeElements":
        return FakeElements(self.child_attributes.get(selector, []))


class FakeElement:
    def __init__(self, attributes: dict[str, str | None]) -> None:
        self.attributes = attributes

    def get_attribute(self, attribute: str) -> str | None:
        return self.attributes.get(attribute)


class FakeElements:
    def __init__(self, elements: list[dict[str, str | None]]) -> None:
        self.elements = [FakeElement(element) for element in elements]

    def count(self) -> int:
        return len(self.elements)

    def nth(self, index: int) -> FakeElement:
        return self.elements[index]


class FakeRows:
    def __init__(self, rows: list[FakeRow]) -> None:
        self.rows = rows

    def count(self) -> int:
        return len(self.rows)

    def nth(self, index: int) -> FakeRow:
        return self.rows[index]


class FakeChatList:
    def __init__(self, rows_by_selector: dict[str, list[FakeRow]]) -> None:
        self.rows_by_selector = rows_by_selector

    def locator(self, selector: str) -> FakeRows:
        return FakeRows(self.rows_by_selector.get(selector, []))


class FailingChatList:
    def locator(self, selector: str) -> FakeRows:
        raise PlaywrightError(f"{selector} failed")


class FakePage:
    def __init__(
        self,
        visible_selectors: set[str] | None = None,
        chat_list: FakeChatList | FailingChatList | None = None,
    ) -> None:
        self.visible_selectors = visible_selectors or set()
        self.chat_list = chat_list or FakeChatList({})
        self.waited_selectors: list[tuple[str, int]] = []

    def wait_for_selector(self, selector: str, timeout: int) -> None:
        self.waited_selectors.append((selector, timeout))
        if selector not in self.visible_selectors:
            raise PlaywrightTimeoutError(f"{selector} not visible")

    def locator(self, selector: str) -> FakeChatList | FailingChatList:
        return self.chat_list


def test_discovers_visible_chats() -> None:
    page = FakePage(
        visible_selectors={"[aria-label='Chat list']"},
        chat_list=FakeChatList(
            {
                "div[role='listitem']": [
                    FakeRow(
                        "1 unread message\nYesterday\nFamily\nDinner at 8?\nPinned\nMuted",
                        attributes={"data-id": "12345@g.us"},
                        child_attributes={
                            "[title]": [{"title": "Family"}],
                            "[aria-label]": [
                                {"aria-label": "1 unread message"},
                                {"aria-label": "Pinned"},
                                {"aria-label": "Muted"},
                            ],
                        },
                    ),
                    FakeRow(
                        "10:31 AM\nAsha\nOn my way",
                        child_attributes={"[title]": [{"title": "Asha"}]},
                    ),
                ]
            }
        ),
    )

    chats = discover_chats(page, timeout_ms=1_000)

    assert chats == [
        ChatSummary(
            external_id="12345@g.us",
            name="Family",
            unread_count=1,
            last_message_preview="Dinner at 8?",
            last_activity_text="Yesterday",
        ),
        ChatSummary(
            external_id=None,
            name="Asha",
            unread_count=None,
            last_message_preview="On my way",
            last_activity_text="10:31 AM",
        ),
    ]
    assert ("[aria-label='Chat list']", 250) in page.waited_selectors


def test_discovers_chat_when_unread_badge_text_precedes_name() -> None:
    page = FakePage(
        visible_selectors={"[data-testid='chat-list']"},
        chat_list=FakeChatList(
            {
                "div[role='listitem']": [
                    FakeRow(
                        "1 unread message\n2:31 PM\nIRIS Robotic Event 2026",
                        child_attributes={
                            "[title]": [{"title": "IRIS Robotic Event 2026"}],
                            "[aria-label]": [{"aria-label": "1 unread message"}],
                        },
                    )
                ]
            }
        ),
    )

    assert discover_chats(page) == [
        ChatSummary(
            external_id=None,
            name="IRIS Robotic Event 2026",
            unread_count=1,
            last_message_preview=None,
            last_activity_text="2:31 PM",
        )
    ]


def test_ignores_decorative_titles_for_group_chat_name() -> None:
    page = FakePage(
        visible_selectors={"[data-testid='chat-list']"},
        chat_list=FakeChatList(
            {
                "div[role='listitem']": [
                    FakeRow(
                        "Muted\nPinned\nSat\nSchool Parents\nTeacher: See you Monday",
                        child_attributes={
                            "[title]": [
                                {"title": "Muted"},
                                {"title": "Pinned"},
                                {"title": "School Parents"},
                            ],
                        },
                    )
                ]
            }
        ),
    )

    assert discover_chats(page) == [
        ChatSummary(
            external_id=None,
            name="School Parents",
            unread_count=None,
            last_message_preview="Teacher: See you Monday",
            last_activity_text="Sat",
        )
    ]


def test_falls_back_to_grid_rows() -> None:
    page = FakePage(
        visible_selectors={"div[role='grid']"},
        chat_list=FakeChatList({"div[role='row']": [FakeRow("School")]}),
    )

    assert discover_chats(page, timeout_ms=1_000) == [
        ChatSummary(external_id=None, name="School")
    ]


def test_raises_when_chat_list_never_loads() -> None:
    page = FakePage()

    with pytest.raises(WhatsAppDiscoveryError, match="did not finish loading"):
        discover_chats(page, timeout_ms=100)


def test_raises_when_rows_are_missing() -> None:
    page = FakePage(
        visible_selectors={"[data-testid='chat-list']"},
        chat_list=FakeChatList({}),
    )

    with pytest.raises(WhatsAppDiscoveryError, match="No WhatsApp chats"):
        discover_chats(page)


def test_wraps_row_selector_failures() -> None:
    page = FakePage(
        visible_selectors={"[data-testid='chat-list']"},
        chat_list=FailingChatList(),
    )

    with pytest.raises(WhatsAppDiscoveryError, match="row selector failed"):
        discover_chats(page)


def test_wraps_row_read_failures() -> None:
    page = FakePage(
        visible_selectors={"[data-testid='chat-list']"},
        chat_list=FakeChatList(
            {"div[role='listitem']": [FakeRow("", fail_read=True)]}
        ),
    )

    with pytest.raises(WhatsAppDiscoveryError, match="Could not read"):
        discover_chats(page)
