"""Opt-in synthetic REALM/Driftspace credential contract probe.

Requires trusted REALM source. Uses disposable SQLite and temporary loopback
listeners on OS-selected ports; never contacts or changes a running world.
Demonstrates the remaining bypass in unmodified generic REALM explicitly.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from http.server import HTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib import error, request


WORLD = "driftspace-synthetic-demo"
HUMAN = "SyntheticCaptain"
HANDLES = {
    HUMAN: "Rylok", "SyntheticTessa": "Tessa", "SyntheticCalamar": "Calamar",
    "SyntheticGhost": "Ghost", "SyntheticKira": "Kira",
    "SyntheticBulwark": "Bulwark", "SyntheticMilo": "Milo",
}


def _roster(path: Path) -> None:
    actors = []
    for actor_id in HANDLES:
        human = actor_id == HUMAN
        actors.append({
            "actor_id": actor_id, "control": "human_pc" if human else "ai_npc",
            "ai_control_allowed": not human, "model_binding": None,
            "runtime_state": "not_activated",
            "action_authority": None if human else "host_validated_proposal_only",
        })
    path.write_text(json.dumps({
        "schema": "realm.private_crew_proposal.v1", "world_id": WORLD,
        "classification": "private_proposed", "activated": False,
        "actors": actors,
    }), encoding="utf-8")


def _http(server: HTTPServer, path: str, *, token: str | None = None,
          payload: dict | None = None) -> tuple[int, dict]:
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        data=body, headers=headers,
    )
    try:
        with request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except error.HTTPError as response:
        with closing(response):
            return response.code, json.loads(response.read())


def verify(realm_src: Path, worldpack: Path) -> None:
    if not (realm_src / "realm" / "gateway.py").is_file():
        raise ValueError("An explicit trusted REALM src directory is required")
    if not worldpack.is_file():
        raise ValueError("Synthetic worldpack file is required")
    sys.path.insert(0, str(realm_src.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack
    from driftspace.host_admission import CrewHostAdmission

    checked: list[str] = []

    def expect(name: str, ok: bool) -> None:
        if not ok:
            raise AssertionError(f"Credential contract failed: {name}")
        checked.append(name)

    def refused(name: str, action) -> None:
        try:
            action()
        except ValueError:
            checked.append(name)
        else:
            raise AssertionError(f"Credential contract accepted: {name}")

    with tempfile.TemporaryDirectory(prefix="driftspace-auth-qual-") as temp:
        root = Path(temp)
        roster_path = root / "synthetic-roster.json"
        _roster(roster_path)
        db_a, db_b = root / "a.sqlite3", root / "b.sqlite3"
        import_worldpack(db_a, worldpack)
        gateway_a = Gateway(db_a, world_id=WORLD)
        gateway_b = Gateway(db_b, world_id="other-synthetic-world")
        admission = CrewHostAdmission.load(
            gateway_a, roster_path, world_id=WORLD,
            human_actor_id=HUMAN, public_handles=HANDLES,
        )

        # Compatibility guard: current REALM main has legacy credentials, but
        # draft scoped mode is a different security contract. This synthetic
        # marker tests fail-closed behavior, NOT actual PR #180 qualification.
        gateway_a.scoped_credentials = object()
        try:
            refused("unqualified scoped credential mode rejected", lambda: CrewHostAdmission.load(
                gateway_a, roster_path, world_id=WORLD,
                human_actor_id=HUMAN, public_handles=HANDLES,
            ))
        finally:
            del gateway_a.scoped_credentials

        refused("cross-world admission binding", lambda: CrewHostAdmission.load(
            gateway_b, roster_path, world_id=WORLD,
            human_actor_id=HUMAN, public_handles=HANDLES,
        ))
        for actor in ("SyntheticTessa", "synthetictessa", "Tessa", "Rylok", "OtherPlayer"):
            refused("no human credential for " + actor, lambda actor=actor: admission.provision_captain(actor))
        token_a = admission.provision_captain(HUMAN)
        token_b = gateway_b.credentials.provision(HUMAN)
        expect("captain token accepted only by bound admission", admission.authenticate_captain(token_a) == HUMAN)
        expect("other-world bearer rejected", admission.authenticate_captain(token_b) is None)
        projection = admission.public_crew_for_token(token_a)
        expect("public handle is not misrepresented as an Engine player ID",
               projection.get("player_handle") == "Rylok" and "player_id" not in projection)
        expect("private actor identities absent from projection",
               all(actor not in json.dumps(projection) for actor in HANDLES))
        expect("six AI, one human", [x["control_type"] for x in projection["crew"]] == ["human"] + ["ai"] * 6)

        servers = [GatewayServer(gateway_a, (), port=0), GatewayServer(gateway_b, (), port=0)]
        threads = [threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
                   for s in servers]
        try:
            for thread in threads:
                thread.start()
            a, b = servers
            expect("missing bearer 401", _http(a, "/api/v1/room")[0] == 401)
            expect("invalid bearer 401", _http(a, "/api/v1/room", token="invalid-token")[0] == 401)
            expect("valid captain join 200", _http(a, "/api/v1/join", token=token_a,
                   payload={"player": HUMAN})[0] == 200)
            status, room = _http(a, "/api/v1/room", token=token_a)
            expect("actual imported station visible to captain",
                   status == 200 and "Arrival Platform" in room.get("text", ""))
            expect("claimed NPC join denied 403", _http(a, "/api/v1/join", token=token_a,
                   payload={"player": "SyntheticTessa"})[0] == 403)
            expect("claimed NPC action denied 403", _http(a, "/api/v1/command", token=token_a,
                   payload={"player": "SyntheticGhost", "command": "say impersonation"})[0] == 403)
            expect("world B bearer fails in A 401", _http(a, "/api/v1/room", token=token_b)[0] == 401)
            expect("world A bearer fails in B 401", _http(b, "/api/v1/room", token=token_a)[0] == 401)
            rotated = admission.rotate_captain(HUMAN)
            expect("rotated old bearer fails 401", _http(a, "/api/v1/room", token=token_a)[0] == 401)
            expect("rotated new bearer succeeds 200", _http(a, "/api/v1/room", token=rotated)[0] == 200)
            expect("revoke removed credential", gateway_a.credentials.revoke(HUMAN))
            expect("revoked bearer fails 401", _http(a, "/api/v1/room", token=rotated)[0] == 401)

            # Deliberately characterize generic REALM's remaining bypass:
            # a privileged caller can still issue an NPC token outside this
            # adapter, then the unmodified HTTP gateway will accept it.
            npc_token = gateway_a.credentials.provision("synthetictessa")
            expect("generic host bypass demonstrably exists",
                   _http(a, "/api/v1/join", token=npc_token,
                         payload={"player": "synthetictessa"})[0] == 200)
            refused("admission refuses existing NPC credential",
                    lambda: admission.authenticate_captain(npc_token))
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=2)

    print(f"PASS: {len(checked)} isolated real-Gateway contract assertions (temporary DB and loopback ports)")
    print("RELEASE HOLD: generic REALM still accepts privileged out-of-band NPC credential issuance")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", type=Path, required=True)
    parser.add_argument("--worldpack", type=Path, default=Path(__file__).resolve().parents[1]
                        / "examples" / "driftspace-synthetic-demo.worldpack.v1.json")
    args = parser.parse_args()
    verify(args.realm_src, args.worldpack)
