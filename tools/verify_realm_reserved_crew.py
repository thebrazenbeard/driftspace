"""Opt-in six-crew NPC reservation probe on disposable REALM/SQLite and loopback HTTP.

Requires trusted REALM source with host-only principal_roles. No live-world change.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import sys
import tempfile
import threading

from verify_realm_crew_auth import HANDLES, HUMAN, WORLD, _http, _roster


def verify(realm_src: Path, worldpack: Path) -> None:
    if not (realm_src / "realm" / "principal_roles.py").is_file():
        raise ValueError("REALM source lacks host-only NPC reservation")
    if not (realm_src / "realm" / "gateway.py").is_file() or not worldpack.is_file():
        raise ValueError("Trusted REALM source or synthetic worldpack absent")
    sys.path.insert(0, str(realm_src.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from driftspace.host_admission import CrewHostAdmission
    from realm.gateway import Gateway, GatewayServer
    from realm.principal_roles import reserve_npc, is_reserved_npc
    from realm.residents import ResidentController
    from realm.worldpack import import_worldpack

    passed = 0

    def check(ok, name):
        nonlocal passed
        if not ok:
            raise AssertionError(name)
        passed += 1

    def rejected(op, name):
        try:
            op()
        except ValueError:
            check(True, name)
        else:
            raise AssertionError(name)

    with tempfile.TemporaryDirectory(prefix="driftspace-host-reservation-") as temp:
        root = Path(temp)
        roster = root / "roster.json"
        _roster(roster)
        names = [n for n in HANDLES if n != HUMAN]
        db = root / "six.sqlite3"
        import_worldpack(db, worldpack)
        host = Gateway(db, world_id=WORLD)
        host.join(HUMAN)
        for name in names:
            host.join(name)
            check(reserve_npc(host.engine, name), name + ": reserve")
            check(not reserve_npc(host.engine, name), name + ": idempotent")
            with closing(host.engine._connect()) as connection:
                check(is_reserved_npc(connection, name), name + ": persisted")
            rejected(lambda n=name: host.credentials.provision(n), name + ": issuance denied")
            rejected(lambda n=name: host.credentials.rotate(n), name + ": rotation denied")
        with closing(host.engine._connect()) as connection:
            check(not is_reserved_npc(connection, HUMAN), "captain remains human")
        admission = CrewHostAdmission.load(host, roster, world_id=WORLD,
                                           human_actor_id=HUMAN, public_handles=HANDLES)
        token = admission.provision_captain(HUMAN)
        check(admission.authenticate_captain(token) == HUMAN, "captain token")
        projection = admission.public_crew_for_token(token)
        check([r["control_type"] for r in projection["crew"]] == ["human"] + ["ai"] * 6,
              "six AI designations, one human")
        check(projection.get("player_handle") == "Rylok" and "player_id" not in projection,
              "private actor not misrepresented")
        resident = ResidentController(host.engine, names[0])
        resident.commit({"command": "say SYNTHETIC HOST CONTROLLED"}, action_id="synthetic-host-01")
        check("SYNTHETIC HOST CONTROLLED" in host.engine.act(HUMAN, "history"),
              "host-bound NPC action possible")
        server = GatewayServer(host, (), port=0)
        thread = threading.Thread(target=server.serve_forever,
                                  kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        try:
            check(_http(server, "/api/v1/room", token=token)[0] == 200, "human bearer admitted")
            check(_http(server, "/api/v1/join", token=token,
                        payload={"player": names[0]})[0] == 403, "NPC claim denied")
            check(_http(server, "/api/v1/command", token=token,
                        payload={"player": names[0], "command": "say spoof"})[0] == 403,
                  "NPC command spoof denied")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            check(not thread.is_alive(), "test server shut down")
        for scoped in (False, True):
            db2 = root / ("scoped.sqlite3" if scoped else "legacy.sqlite3")
            import_worldpack(db2, worldpack)
            remote = Gateway(db2, world_id=WORLD, scoped_credentials=scoped)
            remote.join(names[1])
            store = remote.scoped_credentials if scoped else remote.credentials
            old_token = store.provision(names[1])
            check(reserve_npc(remote.engine, names[1]), "preissued role reserved")
            if scoped:
                auth = store.authenticate(old_token, required_capability="command:write")
            else:
                auth = store.authenticate(old_token)
            check(auth is None, "preissued bearer disabled")
            rejected(lambda: store.provision(names[1]), "new bearer blocked")
            rejected(lambda: store.rotate(old_token if scoped else names[1]),
                     "bearer rotation blocked")

    print(f"PASS: {passed} disposable Driftspace NPC authority assertions")
    print("HOLD: PR-only qualification; no AI model, live principal, host upgrade or public release")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", required=True, type=Path)
    parser.add_argument("--worldpack", type=Path, default=Path(__file__).resolve().parents[1] /
                        "examples" / "driftspace-synthetic-demo.worldpack.v1.json")
    args = parser.parse_args()
    verify(args.realm_src, args.worldpack)