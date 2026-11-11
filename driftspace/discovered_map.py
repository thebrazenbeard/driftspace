"""Private Rylok-pilot discovered-room map.

Read-only graph derived from this actor's own join/move ledger and exits.
Not a host-authoritative fog-of-war API; never publish unknown room names.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
import re
import sqlite3

_MAX_ROOMS = 48
_DELTAS = {"north": (0,-1), "south":(0,1), "east":(1,0), "west":(-1,0)}
_CLEAN = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def render_discovered_map(db_path: Path, actor: str) -> str:
    path=Path(db_path)
    if not path.is_file():
        return "Discovered map unavailable for this pilot."
    try:
        with sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, timeout=5) as db:
            db.row_factory=sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            player=db.execute("SELECT room_id FROM players WHERE id=?", (actor,)).fetchone()
            if player is None:
                return "Discovered map unavailable: character not joined."
            current=player["room_id"]
            actor_rooms={r["room_id"] for r in db.execute(
                "SELECT DISTINCT room_id FROM events WHERE actor=? AND kind IN ('join','move')",(actor,)
            )}
            actor_rooms.add(current)
            if len(actor_rooms)>_MAX_ROOMS:
                return "Discovered map unavailable: pilot view limit reached."
            names={r["id"]:_CLEAN.sub("",r["name"])[:60] for r in db.execute(
                "SELECT id,name FROM rooms"
            ) if r["id"] in actor_rooms}
            if current not in names:
                return "Discovered map unavailable: unknown current room."
            start_row=db.execute(
                "SELECT value FROM world_meta WHERE key='start_room'"
            ).fetchone()
            first=db.execute(
                "SELECT room_id FROM events WHERE actor=? AND kind IN ('join','move') "
                "ORDER BY id LIMIT 1", (actor,)
            ).fetchone()
            # The first authored start room is stable while known; otherwise
            # anchor at this actor's earliest known history, never at the
            # moving current-room marker.
            authored_start=start_row["value"] if start_row else None
            anchor=(authored_start if authored_start in names
                    else first["room_id"] if first and first["room_id"] in names
                    else current)
            passages={}
            for r in db.execute("SELECT room_id,direction,destination FROM exits"):
                if r["room_id"] in names:
                    passages[(r["room_id"],r["direction"])]=r["destination"]
    except (sqlite3.Error,OSError,ValueError):
        return "Discovered map unavailable for this pilot."

    # Place visited cardinal passages only. Unknown rooms have no coordinates
    # or names in the output, even when a destination ID exists in the database.
    positions={}
    occupied=set()
    for start in ([anchor]+sorted(names)):
        if start in positions:continue
        base=(0,0) if not occupied else (max(x for x,y in occupied)+2,0)
        positions[start]=base
        occupied.add(base)
        queue=deque([start])
        while queue:
            src=queue.popleft()
            x,y=positions[src]
            for direction in ("north","east","south","west"):
                target=passages.get((src,direction))
                if target not in names or target in positions:
                    continue
                dx,dy=_DELTAS[direction]
                dest=(x+dx,y+dy)
                if dest in occupied:
                    continue
                positions[target]=dest
                occupied.add(dest)
                queue.append(target)

    # A fixed-width marker field keeps labels stationary across movement.
    label=lambda rid: ("*" if rid==current else " ")+" ["+names[rid]+"]"
    # Reserve marker space for every room, not only for the current room:
    # otherwise moving the * changes cell width and shifts the entire map.
    width=max(20,min(68,max(len(names[room])+6 for room in positions)))
    x_values=range(min(x for x,y in occupied),max(x for x,y in occupied)+1)
    y_values=range(min(y for x,y in occupied),max(y for x,y in occupied)+1)
    at={position:room for room,position in positions.items()}
    lines=[f"Discovered station map ({len(names)} visited rooms)  * = here"]
    for row_index,y in enumerate(y_values):
        cells=[]
        for x in x_values:
            room=at.get((x,y))
            cells.append((label(room) if room else "").center(width))
            if x!=x_values.stop-1:
                dest=at.get((x+1,y))
                linked=(room is not None and dest is not None and
                    (passages.get((room,"east"))==dest or passages.get((dest,"west"))==room))
                cells.append("---" if linked else "   ")
        lines.append("".join(cells).rstrip())
        if y!=y_values.stop-1:
            connectors=[]
            for x in x_values:
                room=at.get((x,y))
                below=at.get((x,y+1))
                linked=(room is not None and below is not None and
                    (passages.get((room,"south"))==below or passages.get((below,"north"))==room))
                connectors.append(("|" if linked else "").center(width))
                if x!=x_values.stop-1: connectors.append("   ")
            lines.append("".join(connectors).rstrip())
    unknown=[
        f"{names[room]}: {direction}: unexplored"
        for (room,direction),target in sorted(passages.items())
        if target not in names
    ]
    if unknown:
        lines.append("Unexplored passages:")
        lines.extend(unknown)
    lines.append("Private synthetic pilot; discovery is from this character's own movement history.")
    return "\n".join(lines)
