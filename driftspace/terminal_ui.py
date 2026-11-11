"""Public-safe color, help and scoped social receipts for Driftspace's terminal pilot.

Social receipts are pilot-local; they do NOT imply multiplayer delivery or AI crew.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import sqlite3

ROOMS = frozenset({"Arrival Platform", "Exchange Hall", "Service Bay", "Viewing Gallery"})
_SGR = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SOCIAL = {
    "emote": "room",
    "yell": "world",
    "ooc": "world",
    "crewchat": "crew",
}
MUD_HELP = (
    "Movement: north/south/east/west (n/s/e/w), look, where\n"
    "Items: take <item>, drop <item>, inventory\n"
    "Comms: say <text>, emote <action>, yell <text>, ooc <text>, crewchat <text>\n"
    "Information: who, listen, history [1-50], socials, help, quit\n"
    "This is a synthetic private pilot. Socials are saved locally; AI crew"
    " and live multiplayer channel delivery are NOT online."
)

@dataclass(frozen=True)
class Social:
    scope: str
    kind: str
    text: str


def _clean(text: str) -> str:
    return _CTRL.sub("", _SGR.sub("", text)).strip()


def parse_social(raw: str) -> Social | None:
    verb, _, text = raw.strip().partition(" ")
    kind = verb.casefold()
    if kind not in _SOCIAL:
        return None
    clean = _clean(text)
    if not clean:
        raise ValueError(f"{kind}: message required")
    if len(clean) > 280:
        raise ValueError("Social messages must be 280 characters or fewer")
    return Social(_SOCIAL[kind], kind, clean)


def render_terminal(text: str, *, ansi: bool = True) -> str:
    if not ansi:
        return text
    def color(line: str) -> str:
        clean = _SGR.sub("", line)
        if clean in ROOMS:
            return "\x1b[1;36m" + clean + "\x1b[0m"
        if clean.startswith("Exits:"):
            return "\x1b[1;33m" + clean + "\x1b[0m"
        if clean.startswith(("Items:", "You carry:", "You take", "You drop")):
            return "\x1b[1;32m" + clean + "\x1b[0m"
        if clean.startswith(("Unknown command", "Access denied", "Command rejected")):
            return "\x1b[1;31m" + clean + "\x1b[0m"
        if clean.startswith(("You say:", "[OOC]", "[Wreckforge]", "You yell:")):
            return "\x1b[1;35m" + clean + "\x1b[0m"
        return clean
    return "\n".join(color(line) for line in text.split("\n"))


def terminal_prompt() -> str:
    return "\x1b[1;36mDriftspace>\x1b[0m "

class SocialStore:
    """Scoped single-player pilot receipts, kept OUT of host/public feed."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        os.chmod(self.path, 0o600)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                kind TEXT NOT NULL,
                scope TEXT NOT NULL,
                message TEXT NOT NULL
            )""")

    def _db(self):
        return sqlite3.connect(self.path, timeout=5)

    def append(self, actor: str, social: Social) -> None:
        if actor != "Rylok" or social.scope not in {"room", "world", "crew"}:
            raise ValueError("This pilot only supports Captain Rylok")
        with self._db() as db:
            db.execute(
                "INSERT INTO events (actor,kind,scope,message) VALUES (?,?,?,?)",
                (actor, social.kind, social.scope, social.text)
            )

    def count(self) -> int:
        with self._db() as db:
            return int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def recent(self, scope: str) -> list[tuple[str, str, str]]:
        if scope not in {"room", "world", "crew"}:
            raise ValueError("Invalid pilot social scope")
        with self._db() as db:
            return list(db.execute(
                "SELECT actor,kind,message FROM events WHERE scope=? ORDER BY id DESC LIMIT 12",
                (scope,)
            ))
