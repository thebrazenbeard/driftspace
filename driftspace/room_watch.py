"""Single-threaded, opt-out automatic room notices for the private MUD pilot.

No player identity is accepted from the client. RoomActivity's current actor,
host-authenticated feed callback and entry cursor enforce this pilot's scope.
"""
from __future__ import annotations

from typing import Callable
from urllib.error import HTTPError
from .room_activity import RoomActivity


def parse_watch_command(command: str) -> str | None:
    """Intercept all watch verbs, including invalid ones, before REALM fallback."""
    parts = command.strip().split(None, 1)
    if not parts or parts[0].casefold() != "watch":
        return None
    mode = parts[1].strip().casefold() if len(parts) > 1 else "status"
    if mode not in {"on", "off", "status"}:
        raise ValueError("Use watch on, watch off, or watch status")
    return mode


class RoomWatch:
    """Pull bounded new events on a socket idle tick; no background threads."""

    def __init__(self, activity: RoomActivity, authenticated_get: Callable[[str], dict]):
        self.activity = activity
        self.authenticated_get = authenticated_get
        self.enabled = True
        self._consecutive_errors = 0

    def configure(self, mode: str) -> str:
        if mode == "on":
            self.enabled = True
            self._consecutive_errors = 0
        elif mode == "off":
            self.enabled = False
        elif mode != "status":
            raise ValueError("Invalid automatic watch mode")
        state = "enabled" if self.enabled else "disabled"
        return f"Automatic room notices {state}. Type watch off/on to change."

    def poll(self) -> str | None:
        if not self.enabled:
            return None
        try:
            result = self.activity.listen(self.authenticated_get)
        except (RuntimeError, ValueError, OSError) as error:
            # Authorization denial is not a transient gateway hiccup. The
            # authenticated terminal owner must handle it, not keep polling.
            if (isinstance(error, PermissionError) or
                    (isinstance(error, HTTPError) and error.code in (401, 403))):
                raise
            self._consecutive_errors += 1
            if self._consecutive_errors >= 3:
                self.enabled = False
                return "Automatic room notices paused: game gateway unavailable. Type watch on to retry."
            return None
        self._consecutive_errors = 0
        return result if result != "No new room activity." else None
