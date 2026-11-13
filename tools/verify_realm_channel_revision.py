"""Physical source integration: REALM host group epochs -> Driftspace history.

Only creates disposable SQLite worlds and OS-selected localhost HTTP servers.
Requires a separately checked out, explicitly pinned REALM source tree.
No real player data, private lore, credentials or model server is accessed.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from driftspace.room_activity import RoomActivity, gateway_room_cursor
from driftspace.room_watch import RoomWatch


def verify(realm_src: Path) -> int:
    if not (realm_src / "realm" / "channel_roster.py").is_file():
        raise ValueError("A trusted REALM group-authority source checkout is required")
    sys.path.insert(0, str(realm_src.resolve()))
    from realm.channel_roster import ChannelRoster
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack

    checks: list[str] = []

    def expect(label: str, actual: bool) -> None:
        if not actual:
            raise AssertionError("REALM channel epoch integration: " + label)
        checks.append(label)

    world_id = "driftspace-synthetic-demo"
    with TemporaryDirectory(prefix="driftspace-epoch-http-") as folder:
        db = Path(folder) / "world.sqlite3"
        import_worldpack(db, ROOT / "examples" /
                         "driftspace-synthetic-demo.worldpack.v1.json")
        gateway = Gateway(db, world_id=world_id)
        captain_token = gateway.credentials.provision("Rylok")
        scout_token = gateway.credentials.provision("Visitor")
        roster = ChannelRoster(db, world_id=world_id)
        roster.install()
        roster.create_group("pilotcrew", "Synthetic Crew")

        server = GatewayServer(gateway, (), port=0)
        expect("server is bound only to localhost",
               server.server_address[0] == "127.0.0.1")
        thread = Thread(target=server.serve_forever,
                        kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)

        def call(token: str, path: str, body: dict | None = None) -> dict:
            wire = json.dumps(body).encode() if body is not None else None
            req = Request(
                base + path, data=wire,
                method="POST" if wire is not None else "GET",
                headers={"Authorization": "Bearer " + token,
                         **({"Content-Type": "application/json"} if wire is not None else {})},
            )
            with urlopen(req, timeout=5) as response:
                return json.loads(response.read(32768))

        def captain_get(path: str) -> dict:
            return call(captain_token, path)

        try:
            joined = call(captain_token, "/api/v1/join",
                          {"player": "Rylok"})
            call(scout_token, "/api/v1/join", {"player": "Visitor"})
            roster.grant("Rylok", "pilotcrew", role="Captain")
            roster.grant("Visitor", "pilotcrew", role="Scout")
            activity = RoomActivity("Rylok", gateway_room_cursor(joined))

            call(scout_token, "/api/v1/command",
                 {"player": "Visitor", "command": "crewchat Synthetic code alpha"})
            first = activity.listen(captain_get)
            expect("host delivered authorized crew chat", "Synthetic code alpha" in first)
            expect("crew chat cannot be replayed by offline history",
                   "Synthetic code alpha" not in activity.history(50))

            call(scout_token, "/api/v1/command",
                 {"player": "Visitor", "command": "say Synthetic public ping"})
            plain = activity.listen(captain_get)
            expect("host delivered ordinary room speech",
                   "Synthetic public ping" in plain)
            expect("ordinary room speech cached while access unchanged",
                   "Synthetic public ping" in activity.history(50))

            roster.revoke("Rylok")
            after = activity.listen(captain_get)
            expect("revocation clears cached history even if feed is empty",
                   activity.history(50) == "No recent activity in this room.")
            expect("no new group data after silent host revocation",
                   "Synthetic code" not in after)

            call(scout_token, "/api/v1/command",
                 {"player": "Visitor", "command": "crewchat Synthetic forbidden after revoke"})
            revoked = activity.listen(captain_get)
            expect("revoked member cannot read future crew channel",
                   "Synthetic forbidden after revoke" not in revoked)

            roster.grant("Rylok", "pilotcrew", role="Engineer")
            call(scout_token, "/api/v1/command",
                 {"player": "Visitor", "command": "crewchat Synthetic regranted signal"})
            regranted = activity.listen(captain_get)
            expect("newly authorized membership sees fresh group message",
                   "Synthetic regranted signal" in regranted)
            expect("fresh private group text still excluded from offline history",
                   "Synthetic regranted signal" not in activity.history(50))

            call(scout_token, "/api/v1/command",
                 {"player": "Visitor", "command": "say Synthetic visible after regrant"})
            activity.listen(captain_get)
            expect("room cache seeded before host epoch conflict",
                   "Synthetic visible after regrant" in activity.history(50))

            # Deterministic race: real authenticated HTTP handler snapshots
            # host channel epoch, then Gateway.feed is delayed until an
            # actual trusted-host role revoke commits. It should answer 409,
            # and the client must discard prior cached history.
            original_feed = gateway.feed
            def changing_feed(player: str, after_cursor: int) -> dict:
                result = original_feed(player, after_cursor)
                if player.casefold() == "rylok":
                    roster.revoke("Rylok")
                return result

            gateway.feed = changing_feed
            previous_cursor = activity.cursor
            watcher = RoomWatch(activity, captain_get)
            try:
                try:
                    watcher.poll()
                except HTTPError as exc:
                    with closing(exc):
                        expect("HTTP host epoch conflict reaches room watcher",
                               exc.code == 409)
                else:
                    raise AssertionError("Room watch suppressed host channel conflict")
            finally:
                gateway.feed = original_feed
            expect("HTTP 409 does not consume transient outage budget",
                   watcher.enabled and watcher._consecutive_errors == 0)
            expect("HTTP 409 does not advance session feed cursor",
                   activity.cursor == previous_cursor)
            expect("HTTP 409 clears old session display cache",
                   activity.history(50) == "No recent activity in this room.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            expect("localhost HTTP server stopped", not thread.is_alive())

    print(json.dumps({
        "result": "PASS", "checks": len(checks),
        "scope": "disposable authenticated REALM Gateway with host group roster",
        "live_world_touched": False,
    }, sort_keys=True))
    return len(checks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", type=Path, required=True)
    verify(parser.parse_args().realm_src)
