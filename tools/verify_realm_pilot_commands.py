"""Exercise Driftspace MUD aliases through a real authenticated REALM HTTP gateway.

Synthetic-only, disposable SQLite. No VN2 live world state or credentials used.
Requires explicitly supplied trusted REALM source directory.
"""
from __future__ import annotations
import argparse
from http import HTTPStatus
from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def verify(realm_src: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    if not (realm_src / "realm" / "gateway.py").is_file():
        raise ValueError("Trusted REALM source directory is required")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(realm_src.resolve()))
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack
    from driftspace.pilot_actions import interpret_pilot_command

    with TemporaryDirectory(prefix="driftspace-alias-gateway-") as folder:
        db = Path(folder) / "world.sqlite3"
        pack = root / "examples" / "driftspace-synthetic-demo.worldpack.v1.json"
        import_worldpack(db, pack)
        gateway = Gateway(db, world_id="driftspace-synthetic-demo")
        token = gateway.credentials.provision("Rylok")
        server = GatewayServer(gateway, (), 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = "http://127.0.0.1:" + str(server.server_port)

        def call(path: str, body: dict | None = None) -> dict:
            wire = json.dumps(body).encode() if body is not None else None
            req = Request(
                url + path, data=wire, method="POST" if wire is not None else "GET",
                headers={"Authorization": "Bearer " + token, **({"Content-Type": "application/json"} if wire is not None else {})},
            )
            with urlopen(req, timeout=3) as response:
                return json.loads(response.read())

        def action(command: str) -> str:
            routed = interpret_pilot_command(command, db, "Rylok")
            if routed is not None and routed.response is not None:
                return routed.response
            actual = routed.host_command if routed is not None else command
            assert actual is not None
            return call("/api/v1/command", {"player": "Rylok", "command": actual})["text"]

        try:
            assert "Arrival Platform" in call("/api/v1/join", {"player": "Rylok"})["text"]
            assert "blank badge" in action("examine badge")
            assert "take Test Badge" in action("get test")
            assert "Test Badge" in action("inv")
            assert "Exchange Hall" in action("east")
            assert "not visible" in action("inspect lamp")
            assert "Service Bay" in action("north")
            assert "portable light" in action("examine lamp")
            assert "take Test Lamp" in action("pickup test")
            assert "drop Test Lamp" in action("discard lamp")
            assert "You say: hello" in action("say hello")
            assert "not visible" in action("examine Test Badge Copy")
            try:
                call("/api/v1/command", {"player": "Tessa", "command": "north"})
            except HTTPError as exc:
                assert exc.code == 403
            else:
                raise AssertionError("Forged actor was accepted")
            print("PASS: authenticated REALM gateway + synthetic world, inspect, get, inventory, move, distance denial, pickup, discard, say, forged actor denial")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", type=Path, required=True)
    verify(parser.parse_args().realm_src)
