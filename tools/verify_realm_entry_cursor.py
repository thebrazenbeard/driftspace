"""Verify lossless room-entry cursors against a disposable authenticated REALM Gateway.

No live players, station databases, credentials, or external services used.
Requires a REALM source revision with the proposed 'room_entry_cursor' field.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
from urllib.request import Request, urlopen

# Direct invocation from the tools/ directory must also work on Windows.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from driftspace.room_activity import RoomActivity, gateway_room_cursor


def verify(realm_src: Path) -> None:
    if not (realm_src / "realm" / "gateway.py").is_file():
        raise ValueError("Trusted REALM source directory required")
    sys.path.insert(0, str(realm_src.resolve()))
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack

    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="driftspace-entry-cursor-") as folder:
        db = Path(folder) / "synthetic.sqlite3"
        import_worldpack(db, root / "examples" / "driftspace-synthetic-demo.worldpack.v1.json")
        gateway = Gateway(db, world_id="driftspace-synthetic-demo")
        rylok_token = gateway.credentials.provision("Rylok")
        gateway.credentials.provision("Visitor")
        gateway.join("Visitor")
        origin_cursor = gateway.cursor
        server = GatewayServer(gateway, (), 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def post(command: str, body: dict) -> dict:
            request = Request(
                base + command, data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + rylok_token,
                         "Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=4) as response:
                return json.loads(response.read())

        def read(path: str) -> dict:
            request = Request(base + path, headers={"Authorization": "Bearer " + rylok_token})
            with urlopen(request, timeout=4) as response:
                return json.loads(response.read())

        try:
            def during_join():
                gateway.engine.act("Visitor", "say Greetings after join, before cursor")
                return origin_cursor()

            with patch.object(gateway, "cursor", side_effect=during_join):
                joined = post("/api/v1/join", {"player": "Rylok"})
            cursor = gateway_room_cursor(joined)
            assert cursor < joined["cursor"], joined
            activity = RoomActivity("Rylok", cursor)
            joined_speech = activity.listen(read)
            assert "Greetings after join, before cursor" in joined_speech, joined_speech

            gateway.engine.act("Visitor", "east")
            def during_move():
                gateway.engine.act("Visitor", "say Greetings after move, before cursor")
                return origin_cursor()

            with patch.object(gateway, "cursor", side_effect=during_move):
                moved = post("/api/v1/command", {"player": "Rylok", "command": "east"})
            assert "Exchange Hall" in moved["text"]
            move_cursor = gateway_room_cursor(moved)
            assert move_cursor < moved["cursor"], moved
            activity.enter_new_room(move_cursor)
            moved_speech = activity.listen(read)
            assert "Greetings after move, before cursor" in moved_speech, moved_speech
            assert "Greetings after join" not in activity.history(50)

            # An unqualified legacy response retains its old behavior rather
            # than claiming this new lossless guarantee.
            assert gateway_room_cursor({"ok": True, "cursor": 99}) == 99
            print("PASS: authenticated REALM HTTP join and move, injected interleaved speech both delivered, actor-scoped room resets, legacy fallback")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", type=Path, required=True)
    verify(parser.parse_args().realm_src)
