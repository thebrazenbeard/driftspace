"""Disposable authenticated Gateway+Telnet proof of automatic room events.

Requires an explicit private bridge-source path on an authorized host.
No real access code, player data, station DB, or existing service is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets
import select
import socket
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def verify(realm_src: Path, bridge_source: Path, bind_host: str) -> None:
    if not (realm_src/"realm"/"gateway.py").is_file() or not bridge_source.is_file():
        raise ValueError("Explicit trusted REALM and private bridge source paths required")
    sys.path.insert(0,str(realm_src.resolve()))
    from realm.gateway import Gateway, GatewayServer
    from realm.worldpack import import_worldpack

    spec=importlib.util.spec_from_file_location("driftspace_private_bridge_watch_probe",bridge_source)
    bridge=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(bridge)

    def plain(data: bytes) -> str:
        return re.sub(rb"\x1b\[[0-9;]*m",b"",data).decode("utf-8","replace")

    pending_by_socket: dict[int, bytearray] = {}
    def receive(client: socket.socket, fragment: bytes, seconds: float = 9.0) -> str:
        import time
        deadline=time.monotonic()+seconds
        pending=pending_by_socket.setdefault(client.fileno(),bytearray())
        while time.monotonic()<deadline:
            index=pending.find(fragment)
            if index>=0:
                boundary=index+len(fragment)
                data=bytes(pending[:boundary])
                del pending[:boundary]
                return plain(data)
            ready,_,_=select.select([client],[],[],min(0.5,max(0,deadline-time.monotonic())))
            if not ready:continue
            piece=client.recv(8192)
            if not piece:raise AssertionError("Disconnected before "+str(fragment))
            pending.extend(piece)
        raise AssertionError(("No expected automatic room output",fragment,plain(bytes(pending[-500:]))))

    def send(client: socket.socket,text: str):
        client.sendall(text.encode("utf-8")+b"\r\n")

    with TemporaryDirectory(prefix="driftspace-auto-room-") as folder:
        root=Path(folder)
        private=root/"private"
        private.mkdir(mode=0o700)
        db=root/"world.sqlite3"
        world=Path(__file__).resolve().parents[1]/"examples"/"driftspace-synthetic-demo.worldpack.v1.json"
        import_worldpack(db,world)
        gateway=Gateway(db,world_id="driftspace-synthetic-demo")
        rylok=gateway.credentials.provision("Rylok")
        visitor=gateway.credentials.provision("Visitor")
        gateway.join("Visitor")
        gateway.command("Visitor","say PRIVATE BEFORE RYLOK LOGGED IN",None)

        token=private/"rylok.token"
        token.write_text(rylok)
        token.chmod(0o600)
        code="disposable-auto-watch-passcode"
        salt=secrets.token_bytes(16)
        auth=private/"auth.json"
        auth.write_text(json.dumps({
            "salt":salt.hex(),
            "hash":hashlib.pbkdf2_hmac("sha256",code.encode(),salt,250000).hex()
        }))
        auth.chmod(0o600)
        bridge.ROOT=root
        bridge.AUTH=auth
        bridge.BEARER=token

        http=GatewayServer(gateway,(),0)
        bridge.API=f"http://127.0.0.1:{http.server_port}"
        ht=Thread(target=http.serve_forever,daemon=True)
        ht.start()
        listener=bridge.Bridge(bind_host,0)
        lt=Thread(target=listener.serve_forever,daemon=True)
        lt.start()
        try:
            client=socket.create_connection(listener.server_address,5)
            receive(client,b"Game access code:")
            send(client,code)
            welcome=receive(client,b"Driftspace>")
            assert "Authenticated as Captain Rylok" in welcome
            assert "PRIVATE BEFORE" not in welcome

            gateway.command("Visitor","say AUTOMATIC HELLO CAPTAIN",None)
            unsolicited=receive(client,b"AUTOMATIC HELLO CAPTAIN")
            assert "PRIVATE BEFORE" not in unsolicited
            receive(client,b"Driftspace>")

            send(client,"watch perhaps")
            malformed=receive(client,b"Driftspace>")
            assert "Command rejected: Use watch on" in malformed,malformed

            send(client,"watch off")
            off=receive(client,b"Driftspace>")
            assert "disabled" in off.lower(),off
            gateway.command("Visitor","say QUIET WHILE WATCH OFF",None)
            ready,_,_=select.select([client],[],[],3.0)
            assert not ready,"A disabled room watch emitted unsolicited data"

            send(client,"watch on")
            on=receive(client,b"Driftspace>")
            assert "enabled" in on.lower(),on
            async_quiet=receive(client,b"QUIET WHILE WATCH OFF")
            assert "QUIET WHILE WATCH OFF" in async_quiet
            receive(client,b"Driftspace>")

            gateway.command("Visitor","east",None)
            gateway.command("Visitor","say SECRET BEFORE RYLOK ENTERS",None)
            send(client,"east")
            moved=receive(client,b"Driftspace>")
            assert "Exchange Hall" in moved,moved
            assert "SECRET BEFORE" not in moved,moved
            gateway.command("Visitor","say NEW EXCHANGE WELCOME",None)
            incoming=receive(client,b"NEW EXCHANGE WELCOME")
            assert "SECRET BEFORE" not in incoming,incoming
            receive(client,b"Driftspace>")

            # While a user has begun typing a command but not submitted it,
            # an idle notification must not overwrite their incomplete input.
            client.sendall(b"say ")
            gateway.command("Visitor","say NEW MESSAGE WHILE TYPING",None)
            ready,_,_=select.select([client],[],[],2.5)
            assert not ready,"Automatic update interrupted a partially typed command"
            client.sendall(b"typing done\r\n")
            own_reply=receive(client,b"Driftspace>")
            assert "You say: typing done" in own_reply,own_reply
            typed_event=receive(client,b"NEW MESSAGE WHILE TYPING")
            assert "NEW MESSAGE WHILE TYPING" in typed_event,typed_event
            receive(client,b"Driftspace>")

            send(client,"history")
            history=receive(client,b"Driftspace>")
            assert "NEW EXCHANGE WELCOME" in history
            assert "AUTOMATIC HELLO CAPTAIN" not in history
            assert "SECRET BEFORE" not in history
            send(client,"quit")
            assert "Disconnected" in receive(client,b"Disconnected")
            client.close()
            print("PASS: disposable credentialed REALM Gateway+Telnet push-on-idle, watch off/on, no prelogin/preentry leak, move resets history, quit")
        finally:
            listener.shutdown();listener.server_close();lt.join(4)
            http.shutdown();http.server_close();ht.join(4)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src",required=True,type=Path)
    parser.add_argument("--bridge-source",required=True,type=Path)
    parser.add_argument("--bind-host",required=True)
    args=parser.parse_args()
    verify(args.realm_src,args.bridge_source,args.bind_host)
