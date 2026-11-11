"""Verify pilot map against a disposable imported REALM world and host moves."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from driftspace.discovered_map import render_discovered_map


def verify(realm_src: Path) -> None:
    if not (realm_src/"realm"/"engine.py").is_file():
        raise ValueError("Trusted REALM source checkout required")
    sys.path.insert(0,str(realm_src))
    from realm.engine import Engine
    from realm.worldpack import import_worldpack

    with TemporaryDirectory(prefix="driftspace-discovery-") as folder:
        db=Path(folder)/"world.sqlite3"
        world=Path(__file__).resolve().parents[1]/"examples"/"driftspace-synthetic-demo.worldpack.v1.json"
        import_worldpack(db,world)
        engine=Engine(db)
        engine.join("Rylok")
        before=db.read_bytes()
        initial=render_discovered_map(db,"Rylok")
        assert "Arrival Platform" in initial
        assert "Exchange Hall" not in initial
        assert "east: unexplored" in initial
        assert before==db.read_bytes(),"A read-only map changed SQLite"
        engine.join("Visitor")
        engine.act("Visitor","east")
        still_initial=render_discovered_map(db,"Rylok")
        assert "Exchange Hall" not in still_initial,"Other actor's travel leaked"
        engine.act("Rylok","east")
        middle=render_discovered_map(db,"Rylok")
        assert "Exchange Hall" in middle
        assert "Service Bay" not in middle
        assert "Viewing Gallery" not in middle
        assert "north: unexplored" in middle
        engine.act("Rylok","north")
        final=render_discovered_map(db,"Rylok")
        assert "Service Bay" in final
        assert "* [Service Bay]" in final
        assert "Viewing Gallery" not in final
        print("PASS: real Engine+imported world, actor-scoped discovery, other-player isolation, movement refresh, unknown names hidden, map read-only")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src",required=True,type=Path)
    verify(parser.parse_args().realm_src)
