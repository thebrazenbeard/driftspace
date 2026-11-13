"""Opt-in REALM Engine/SQLite smoke test for the synthetic station fixture.

Requires an explicit, trusted REALM checkout path. Creates only a temporary DB;
never imports into a saved, played, or live world.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile


def verify(realm_src: Path, worldpack: Path) -> None:
    if not realm_src.is_dir() or not (realm_src / "realm" / "engine.py").is_file():
        raise ValueError("An explicit REALM source directory is required")
    if not worldpack.is_file():
        raise ValueError("Worldpack file is required")
    sys.path.insert(0, str(realm_src.resolve()))
    from realm.engine import Engine
    from realm.worldpack import import_worldpack

    with tempfile.TemporaryDirectory(prefix="driftspace-worldpack-smoke-") as tmp:
        db = Path(tmp) / "synthetic.sqlite3"
        import_worldpack(db, worldpack)
        engine = Engine(db)
        principal = "SyntheticGuest"
        engine.join(principal)
        steps = (
            ("look", "Arrival Platform"),
            ("go east", "Exchange Hall"),
            ("go north", "Service Bay"),
            ("take test_lamp", "take"),
            ("inventory", "Test Lamp"),
        )
        for command, expected in steps:
            observed = engine.act(principal, command)
            if expected.casefold() not in observed.casefold():
                raise AssertionError(f"REALM action {command!r} lacked expected {expected!r}: {observed!r}")
        print("REALM importer and five actual Engine actions: PASS (disposable SQLite)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm-src", required=True, type=Path)
    parser.add_argument(
        "--worldpack", type=Path,
        default=Path(__file__).resolve().parents[1] / "examples" / "driftspace-synthetic-demo.worldpack.v1.json",
    )
    args = parser.parse_args()
    verify(args.realm_src, args.worldpack)
