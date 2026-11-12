"""Verify session-limited room events against real authenticated REALM Gateway.

Runs only in disposable synthetic worlds, with temporary per-player credentials.
No running VN2 pilot or user-owned game database is accessed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from driftspace.room_activity import RoomActivity


def verify(realm_src: Path) -> None:
    if not (realm_src/"realm"/"gateway.py").is_file():
        raise ValueError("Trusted REALM checkout required")
    sys.path.insert(0,str(realm_src.resolve()))
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack

    worldpack=Path(__file__).resolve().parents[1]/"examples"/"driftspace-synthetic-demo.worldpack.v1.json"
    with TemporaryDirectory(prefix="driftspace-real-feed-") as folder:
        root=Path(folder)
        db=root/"world-a.sqlite3"
        import_worldpack(db,worldpack)
        gateway=Gateway(db,world_id="driftspace-synthetic-demo")
        captain_token=gateway.credentials.provision("Rylok")
        visitor_token=gateway.credentials.provision("Visitor")
        server=GatewayServer(gateway,(),0)
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url="http://127.0.0.1:"+str(server.server_port)

        def call(token: str, path: str, body: dict | None = None) -> dict:
            wire=json.dumps(body).encode("utf-8") if body is not None else None
            req=Request(
                url+path,data=wire,method="POST" if wire is not None else "GET",
                headers={"Authorization":"Bearer "+token,
                         **({"Content-Type":"application/json"} if wire is not None else {})}
            )
            with urlopen(req,timeout=4) as resp:
                return json.loads(resp.read(32768))

        try:
            call(visitor_token,"/api/v1/join",{"player":"Visitor"})
            call(visitor_token,"/api/v1/command",{"player":"Visitor","command":"say Before Rylok joined"})
            joined=call(captain_token,"/api/v1/join",{"player":"Rylok"})
            feed=RoomActivity("Rylok",joined["cursor"])
            assert "Before Rylok joined" not in feed.listen(
                lambda path:call(captain_token,path)), "Prejoin speech leaked"

            call(visitor_token,"/api/v1/command",{"player":"Visitor","command":"say After you arrived"})
            observed=feed.listen(lambda path:call(captain_token,path))
            assert "After you arrived" in observed,observed
            assert "Before Rylok joined" not in feed.history(50)

            call(visitor_token,"/api/v1/command",{"player":"Visitor","command":"east"})
            call(visitor_token,"/api/v1/command",{"player":"Visitor","command":"say This was before room entry"})
            moved=call(captain_token,"/api/v1/command",{"player":"Rylok","command":"east"})
            assert "Exchange Hall" in moved["text"]
            feed.enter_new_room(moved["cursor"])
            assert "After you arrived" not in feed.history(50), "Previous-room history retained"
            no_old=feed.listen(lambda path:call(captain_token,path))
            assert "before room entry" not in no_old.lower(),no_old

            call(visitor_token,"/api/v1/command",{"player":"Visitor","command":"say Welcome to the exchange"})
            fresh=feed.listen(lambda path:call(captain_token,path))
            assert "Welcome to the exchange" in fresh,fresh
            assert "before room entry" not in feed.history(50)

            call(captain_token,"/api/v1/command",{"player":"Rylok","command":"say My own greeting"})
            self_echo=feed.listen(lambda path:call(captain_token,path))
            assert "My own greeting" not in self_echo
            assert "My own greeting" not in feed.history(50)

            try:
                call(visitor_token,"/api/v1/feed?after=0&player=Rylok")
            except HTTPError as exc:
                assert exc.code==403,exc.code
            else:
                raise AssertionError("Visitor forged Rylok feed access")

            db2=root/"world-b.sqlite3"
            second_pack=root/"second-world.worldpack.v1.json"
            other_world=json.loads(worldpack.read_text(encoding="utf-8"))
            other_world["world_id"]="driftspace-independent-test"
            second_pack.write_text(json.dumps(other_world),encoding="utf-8")
            import_worldpack(db2,second_pack)
            another=Gateway(db2,world_id="driftspace-independent-test")
            other_server=GatewayServer(another,(),0)
            other_thread=Thread(target=other_server.serve_forever,daemon=True)
            other_thread.start()
            try:
                req=Request("http://127.0.0.1:"+str(other_server.server_port)+"/api/v1/feed?after=0",
                            headers={"Authorization":"Bearer "+captain_token})
                try:
                    urlopen(req,timeout=4)
                except HTTPError as exc:
                    assert exc.code==401,exc.code
                else:
                    raise AssertionError("Cross-world bearer was accepted")
            finally:
                other_server.shutdown();other_server.server_close();other_thread.join(3)
            print("PASS: two authenticated actors, no prejoin/preentry speech leak, same-room delivery, room-transition cursor, no self echo, forged-actor and cross-world token denial")
        finally:
            server.shutdown();server.server_close();thread.join(3)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src",required=True,type=Path)
    verify(parser.parse_args().realm_src)
