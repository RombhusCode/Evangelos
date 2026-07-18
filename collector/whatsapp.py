"""WhatsApp Web collection interfaces.

This module owns collection only. It intentionally does not contain database,
AI, or presentation logic.

Selector assumptions:
- WhatsApp Web exposes the chat sidebar as a chat list, chats landmark, or grid.
- Individual chat rows are represented by ``div[role='listitem']`` or
  ``div[role='row']`` inside that sidebar.
- Chat names are commonly exposed on descendants with a ``title`` attribute.
- Unread badges are commonly exposed through ``aria-label`` text such as
  ``1 unread message``. WhatsApp does not provide a stable public DOM contract,
  so selectors and defensive fallbacks are intentionally centralized here.
- Real WhatsApp chat ids may appear in row attributes, descendant attributes,
  hrefs, or serialized dataset values. Generated ids such as ``list-item-0``
  are treated only as last-resort fallbacks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import sleep
from typing import Any

from playwright.sync_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


class WhatsAppDiscoveryError(RuntimeError):
    """Raised when WhatsApp Web chat discovery cannot be completed."""


@dataclass(frozen=True)
class ChatSummary:
    """Lightweight metadata for a discovered WhatsApp chat."""

    external_id: str | None
    name: str
    unread_count: int | None = None
    last_message_preview: str | None = None
    last_activity_text: str | None = None


class WhatsAppChatCollector:
    """Discover lightweight chat metadata from an authenticated WhatsApp page."""

    _chat_list_selectors = (
        "[data-testid='chat-list']",
        "[aria-label='Chat list']",
        "[aria-label='Chats']",
        "div[role='grid']",
    )
    _chat_row_selectors = (
        "div[role='listitem']",
        "div[role='row']",
    )
    _external_id_attributes = ("data-id", "data-testid", "id")
    _stable_id_attribute_selector = "[data-id], [data-testid], [id], [href]"
    _title_selector = "[title]"
    _aria_label_selector = "[aria-label]"
    _decorative_text = {
        "archived",
        "muted",
        "online",
        "pinned",
        "typing...",
    }
    _placeholder_text = {
        "loading...",
        "loading…",
    }
    _generated_row_id_pattern = re.compile(r"^list-item-\d+$", re.IGNORECASE)
    _chat_id_pattern = re.compile(
        r"(?:\d{5,}|[a-z0-9._%+-]{3,})@(?:c|g)\.us",
        re.IGNORECASE,
    )
    _time_pattern = re.compile(
        r"^(?:"
        r"(?:[01]?\d|2[0-3]):[0-5]\d(?:\s?[AP]M)?"
        r"|(?:yesterday|today)"
        r"|(?:mon|tue|wed|thu|fri|sat|sun)"
        r"|(?:\d{1,2}/\d{1,2}/\d{2,4})"
        r")$",
        re.IGNORECASE,
    )
    _unread_pattern = re.compile(r"(\d[\d,]*)\s+unread messages?", re.IGNORECASE)

    def __init__(self, page: Page, timeout_ms: int = 30_000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    def discover_chats(self) -> list[ChatSummary]:
        """Return currently visible WhatsApp chats with lightweight metadata only."""
        chat_list_selector = self._wait_for_chat_list()
        rows = self._find_chat_rows(chat_list_selector)

        summaries: list[ChatSummary] = []
        for index in range(rows.count()):
            summary = self._summarize_row(rows.nth(index))
            if summary is not None:
                summaries.append(summary)

        return summaries

    def _wait_for_chat_list(self) -> str:
        last_error: PlaywrightTimeoutError | None = None
        per_selector_timeout = max(
            1,
            self.timeout_ms // len(self._chat_list_selectors),
        )

        for selector in self._chat_list_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=per_selector_timeout)
                return selector
            except PlaywrightTimeoutError as exc:
                last_error = exc
            except PlaywrightError as exc:
                raise WhatsAppDiscoveryError(
                    f"WhatsApp chat list selector failed: {selector}"
                ) from exc

        raise WhatsAppDiscoveryError(
            "WhatsApp chat list did not finish loading."
        ) from last_error

    def _find_chat_rows(self, chat_list_selector: str) -> Any:
        chat_list = self.page.locator(chat_list_selector)

        for row_selector in self._chat_row_selectors:
            try:
                rows = chat_list.locator(row_selector)
                if rows.count() > 0:
                    return rows
            except PlaywrightError as exc:
                raise WhatsAppDiscoveryError(
                    f"WhatsApp chat row selector failed: {row_selector}"
                ) from exc

        raise WhatsAppDiscoveryError("No WhatsApp chats were found in the chat list.")

    def _summarize_row(self, row: Any) -> ChatSummary | None:
        row_text = self._stable_row_text(row)

        text_parts = [part.strip() for part in row_text.splitlines() if part.strip()]
        title_parts = self._attribute_values(row, self._title_selector, "title")
        aria_labels = self._attribute_values(
            row,
            self._aria_label_selector,
            "aria-label",
        )
        candidates = self._unique_text(title_parts + text_parts + aria_labels)
        if not candidates:
            return None

        unread_count = self._extract_unread_count(candidates)
        name = self._extract_chat_name(title_parts, candidates)
        if name is None:
            return None

        last_activity_text = self._extract_last_activity_text(candidates)
        last_message_preview = self._extract_last_message_preview(
            text_parts,
            name,
            last_activity_text,
        )

        return ChatSummary(
            external_id=self._extract_external_id(row),
            name=name,
            unread_count=unread_count,
            last_message_preview=last_message_preview,
            last_activity_text=last_activity_text,
        )

    def _stable_row_text(self, row: Any) -> str:
        try:
            row_text = row.inner_text(timeout=1_000)
        except PlaywrightError as exc:
            raise WhatsAppDiscoveryError("Could not read a WhatsApp chat row.") from exc

        if not self._contains_placeholder_text(row_text):
            return row_text

        sleep(0.2)
        try:
            return row.inner_text(timeout=1_000)
        except PlaywrightError as exc:
            raise WhatsAppDiscoveryError("Could not refresh a WhatsApp chat row.") from exc

    def _contains_placeholder_text(self, text: str | None) -> bool:
        if not text:
            return False

        lowered = text.lower()

        return any(
            placeholder in lowered
            for placeholder in self._placeholder_text
        )
        
    def _attribute_values(
        self,
        row: Any,
        selector: str,
        attribute: str,
    ) -> list[str]:
        try:
            elements = row.locator(selector)
            count = elements.count()
        except (AttributeError, PlaywrightError):
            return []

        values: list[str] = []
        for index in range(count):
            try:
                value = elements.nth(index).get_attribute(attribute)
            except PlaywrightError:
                continue
            if value:
                values.append(value.strip())
        return values

    def _extract_external_id(self, row: Any) -> str | None:
        for attribute in self._external_id_attributes:
            try:
                value = row.get_attribute(attribute)
            except PlaywrightError:
                continue
            if value:
                return value
        return None

    def _extract_unread_count(self, candidates: list[str]) -> int | None:
        for candidate in candidates:
            match = self._unread_pattern.search(candidate)
            if match:
                return int(match.group(1).replace(",", ""))

        for candidate in candidates:
            unread_text = candidate.replace(",", "")
            if unread_text.isdigit():
                return int(unread_text)

        return None

    def _extract_chat_name(
        self,
        title_parts: list[str],
        candidates: list[str],
    ) -> str | None:
        for title in title_parts:
            if self._is_chat_name_candidate(title):
                return title

        for candidate in candidates:
            if self._is_chat_name_candidate(candidate):
                return candidate

        return None

    def _extract_last_activity_text(self, candidates: list[str]) -> str | None:
        for candidate in candidates:
            if self._is_activity_text(candidate):
                return candidate
        return None

    def _extract_last_message_preview(
        self,
        text_parts: list[str],
        name: str,
        last_activity_text: str | None,
    ) -> str | None:
        for part in text_parts:
            if part == name or part == last_activity_text:
                continue
            if self._is_unread_text(part) or self._is_decorative_text(part):
                continue
            if self._is_activity_text(part):
                continue
            return part
        return None

    def _is_chat_name_candidate(self, value: str) -> bool:
        return not (
            self._is_unread_text(value)
            or self._is_activity_text(value)
            or self._is_decorative_text(value)
        )

    def _is_activity_text(self, value: str) -> bool:
        return bool(self._time_pattern.match(value.strip()))

    def _is_unread_text(self, value: str) -> bool:
        value = value.strip()
        return (
            bool(self._unread_pattern.search(value))
            or value.replace(",", "").isdigit()
        )

    def _is_decorative_text(self, value: str) -> bool:
        return value.strip().lower() in self._decorative_text

    def _unique_text(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique_values: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_values.append(normalized)
        return unique_values


def discover_chats(page: Page, timeout_ms: int = 30_000) -> list[ChatSummary]:
    """Discover currently visible WhatsApp chats from an authenticated page."""
    return WhatsAppChatCollector(page=page, timeout_ms=timeout_ms).discover_chats()


def fetch_messages() -> list[dict[str, str]]:
    """Return newly collected messages from WhatsApp Web.

    The Playwright implementation will be added in the collector milestone.
    """
    return []


def sync() -> int:
    """Synchronize messages from WhatsApp Web and return the number collected."""
    return len(fetch_messages())
