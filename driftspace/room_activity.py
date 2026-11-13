"""Credential-bound REALM room activity projection for a private terminal session.

Only accepts a host-authenticated Gateway feed callback. This is a session-local
read model, never a source of world or chat authority. No pre-entry history.
"""
from __future__ import annotations

from collections import deque
import re
from urllib.error import HTTPError
from typing import Callable


_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MAX_RECORDS = 50
_MAX_RESPONSE_EVENTS = 100
_MAX_TEXT = 500


def parse_activity_command(command: str) -> tuple[str, int] | None:
    """Intercept *all* listen/history verbs to prevent legacy history leakage."""
    parts = command.strip().split(None, 1)
    if not parts:
        return None
    word, raw_count = parts[0], parts[1] if len(parts) == 2 else ""
    verb = word.casefold()
    if verb not in {"listen", "history"}:
        return None
    if verb == "listen":
        if raw_count.strip():
            raise ValueError("Use listen (no arguments); history N is session-only")
        return ("listen", 10)
    count = raw_count.strip()
    if not count:
        return ("history", 10)
    if not count.isdecimal() or len(count) > 2 or not 1 <= int(count) <= 50:
        raise ValueError("Use history or history N (1-50)")
    return ("history", int(count))


def gateway_room_cursor(response: dict) -> int:
    """Select a host entry boundary, falling back only for older Gateways.

    The legacy global cursor can skip simultaneous messages; use the
    authoritative room_entry_cursor whenever the host explicitly supplies it.
    Malformed claims fail closed rather than silently selecting a global tail.
    """
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise ValueError("Authenticated Gateway response is required")
    current = response.get("cursor")
    if not isinstance(current, int) or isinstance(current, bool) or current < 0:
        raise ValueError("Invalid Gateway cursor")
    if "room_entry_cursor" not in response:
        return current  # compatibility with current live REALM main
    entry = response["room_entry_cursor"]
    if (
        not isinstance(entry, int) or isinstance(entry, bool)
        or entry < 0 or entry > current
    ):
        raise ValueError("Invalid or missing room-entry evidence")
    return entry


class RoomActivity:
    def __init__(self, actor: str, cursor: int):
        if not actor or not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            raise ValueError("Authenticated actor and nonnegative Gateway cursor required")
        self.actor = actor
        self.cursor = cursor
        self._recent: deque[str] = deque(maxlen=_MAX_RECORDS)
        # A trusted REALM feed changes this host-issued watermark on every
        # crew membership/role mutation, even when no new messages are visible.
        self._channel_revision: int | None = None

    def invalidate_history(self) -> None:
        """Discard cached text without forgetting the last trusted host epoch."""
        self._recent.clear()
        # The watermark survives failed polls: otherwise a second replay of
        # the same regressed epoch would be incorrectly accepted as "first".

    @staticmethod
    def _safe(text: object) -> str:
        if not isinstance(text, str) or len(text) > _MAX_TEXT:
            raise ValueError("Invalid room activity text")
        return _CONTROL.sub(" ", text).strip()

    def enter_new_room(self, cursor: int) -> None:
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < self.cursor:
            raise ValueError("Invalid room transition cursor")
        self.cursor = cursor
        self._recent.clear()

    def listen(self, authenticated_get: Callable[[str], dict]) -> str:
        """Fetch only events since session join or last room transition.

        The gateway callback must use the already-authenticated player's bearer.
        It must never accept a client-provided player id or cursor.
        """
        try:
            response = authenticated_get(f"/api/v1/feed?after={self.cursor}")
        except (HTTPError, PermissionError) as exc:
            # A failed or conflicting authenticated host response cannot
            # validate previously displayed private channel material.
            if (isinstance(exc, PermissionError) or
                    (isinstance(exc, HTTPError) and exc.code in (401, 403, 409))):
                self.invalidate_history()
            raise
        if not isinstance(response, dict) or response.get("ok") is not True:
            raise ValueError("Authenticated room activity unavailable")
        # Legacy feeds may omit this field; they cannot authorize caching
        # group messages. A modern feed must return an actual monotonic int.
        revision = response.get("channel_revision")
        if "channel_revision" in response and (
                type(revision) is not int or revision < 0):
            self.invalidate_history()
            raise ValueError("Invalid channel-access revision")
        previous_revision = self._channel_revision
        if previous_revision is not None and revision != previous_revision:
            # Permission change is meaningful even with zero returned events.
            self.invalidate_history()
            if revision is not None and revision < previous_revision:
                raise ValueError("Channel-access revision regressed")
        cursor = response.get("cursor")
        events = response.get("events")
        if (
            not isinstance(cursor, int) or isinstance(cursor, bool)
            or cursor < self.cursor or not isinstance(events, list)
            or len(events) > _MAX_RESPONSE_EVENTS
        ):
            raise ValueError("Malformed room activity response")
        fresh: list[str] = []
        retainable: list[str] = []
        previous = self.cursor
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("Malformed room activity event")
            event_id = event.get("id")
            if (
                not isinstance(event_id, int) or isinstance(event_id, bool)
                or not previous < event_id <= cursor
            ):
                raise ValueError("Nonmonotonic or replayed room event")
            previous = event_id
            actor = self._safe(event.get("actor"))
            message = self._safe(event.get("text"))
            if not actor or not message:
                raise ValueError("Malformed room activity event")
            if actor.casefold() == self.actor.casefold():
                continue
            fresh.append(message)
            # A cached offline group message could be reread after the member
            # was revoked but before another authenticated poll. Do not retain
            # any crewchat in local session history, even while authorized.
            if event.get("kind") != "crewchat":
                retainable.append(message)
        # Commit cursor and revision only after every event validates.
        self.cursor = cursor
        self._channel_revision = revision
        self._recent.extend(retainable)
        return "\n".join(fresh) if fresh else "No new room activity."

    def history(self, count: int = 10) -> str:
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= _MAX_RECORDS:
            raise ValueError("History count must be between 1 and 50")
        if not self._recent:
            return "No recent activity in this room."
        return "\n".join(list(self._recent)[-count:])
