"""Source-only Driftspace MUD aliases and local-only read-only item inspection.

Command mutability is host-authoritative: only the authenticated REALM gateway
executes take/drop; direct SQLite inspection never changes the database.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import re


@dataclass(frozen=True)
class PilotAction:
    host_command: str | None = None
    response: str | None = None
    resource: str | None = None


def _items(db_path: Path, actor: str, *, location: str) -> list[sqlite3.Row]:
    # Opening in URI read-only mode forbids accidental DB creation or mutation.
    target = Path(db_path)
    if not target.is_file():
        return []
    with sqlite3.connect(target.resolve().as_uri() + "?mode=ro", uri=True, timeout=5) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        player = db.execute("SELECT room_id FROM players WHERE id=?", (actor,)).fetchone()
        if player is None:
            return []
        if location == "room":
            cursor = db.execute(
                "SELECT id,name,description FROM items WHERE room_id=? AND held_by IS NULL",
                (player["room_id"],),
            )
        elif location == "held":
            cursor = db.execute(
                "SELECT id,name,description FROM items WHERE held_by=?", (actor,)
            )
        else:
            cursor = db.execute(
                "SELECT id,name,description FROM items "
                "WHERE (room_id=? AND held_by IS NULL) OR held_by=?",
                (player["room_id"], actor),
            )
        return cursor.fetchall()


def _resolve(items: list[sqlite3.Row], query: str) -> PilotAction | sqlite3.Row:
    query = query.casefold().strip()
    if not query or len(query) > 128 or any(not c.isprintable() for c in query):
        return PilotAction(response="Which item? Provide a visible item name.")
    exact = [item for item in items if query in (item["id"].casefold(), item["name"].casefold())]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return PilotAction(response="Multiple items share that name; be more specific.")
    # A common MUD shorthand is the final item word: 'badge' selects Test Badge.
    # Match entire words, not arbitrary substrings ('badge' must not match 'badger').
    words = [
        item for item in items
        if query in re.split(r"[\s_-]+", item["id"].casefold())
        or query in re.split(r"[\s_-]+", item["name"].casefold())
    ]
    if len(words) == 1:
        return words[0]
    if len(words) > 1:
        return PilotAction(response="Multiple items match. Use a longer name.")
    starts = [item for item in items if item["id"].casefold().startswith(query) or item["name"].casefold().startswith(query)]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1:
        return PilotAction(response="Multiple items match. Use a longer name.")
    return PilotAction(response="That item is not visible or carried here.")


def interpret_pilot_command(raw: str, db_path: Path, actor: str) -> PilotAction | None:
    """Interpret only selected MUD conveniences in an authenticated pilot session.

    Unknown commands pass through to REALM unchanged. A local lookup is only a
    *hint*; the REALM host rechecks ownership and location transactionally.
    """
    original = raw.strip()
    lower = original.casefold()
    if lower in {"inv", "gear", "equipment", "eq"}:
        return PilotAction(host_command="inventory")
    if lower in {"items", "item"}:
        return PilotAction(host_command="look")
    if lower in {"map", "automap"}:
        return PilotAction(resource="/api/v1/map")
    if lower.startswith("pick up "):
        verb, arg = "take", original[8:].strip()
    elif lower.startswith("look at "):
        verb, arg = "examine", original[8:].strip()
    else:
        action, sep, arg = original.partition(" ")
        word = action.casefold()
        verb = (
            "take" if word in {"get", "grab", "pickup", "obtain", "collect"}
            else "drop" if word in {"discard"}
            else "examine" if word in {"examine", "inspect", "x"}
            else None
        )
        if verb is None:
            return None
        arg = arg.strip()
    if not arg:
        return PilotAction(response="Take what?" if verb == "take" else "Drop what?" if verb == "drop" else "Examine what?")
    visible = _items(db_path, actor, location="room" if verb == "take" else "held" if verb == "drop" else "either")
    result = _resolve(visible, arg)
    if isinstance(result, PilotAction):
        return result
    if verb == "examine":
        return PilotAction(response=result["name"] + "\n" + result["description"])
    return PilotAction(host_command=verb + " " + result["id"])
