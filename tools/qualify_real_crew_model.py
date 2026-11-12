"""Opt-in ONE real local model turn in synthetic Driftspace: never the played world.

Requires --allow-existing-loopback-model. An already-running host model must
be supplied; this script never launches inference software or downloads weights.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
from time import monotonic

from verify_realm_crew_auth import HANDLES, HUMAN, WORLD, _roster


def _rss_kib(pid: int) -> int | None:
    try:
        text = Path(f"/proc/{pid}/status").read_text()
    except (OSError, ValueError):
        return None
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return None


def _mem_available_kib() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except OSError:
        pass
    return None


def run(args: argparse.Namespace) -> None:
    if args.allow_existing_loopback_model is not True:
        raise ValueError("Explicit --allow-existing-loopback-model is required")
    if not (args.realm_src / "realm" / "principal_roles.py").is_file():
        raise ValueError("REALM source lacks host-reserved NPC principal contract")
    sys.path.insert(0, str(args.realm_src.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from driftspace.crew_turns import CrewTurnCoordinator
    from realm.gateway import Gateway
    from realm.npc_local_model import LocalChatConfig, LocalChatProposer
    from realm.principal_roles import reserve_npc
    from realm.worldpack import import_worldpack

    config = LocalChatConfig(
        endpoint=args.endpoint, model=args.model, timeout_seconds=args.timeout,
        max_tokens=args.max_tokens,
    )
    available = _mem_available_kib()
    if available is not None and available < 2 * 1024**2:
        raise RuntimeError("Host memory below 2 GiB available: no inference requested")
    baseline = _rss_kib(args.model_pid) if args.model_pid else None
    names = [a for a in HANDLES if a != HUMAN]
    styles = {a: "Synthetic integration only; respond as test handle " + HANDLES[a]
              + ". Use one short in-character line without claiming special authority."
              for a in names}
    with tempfile.TemporaryDirectory(prefix="driftspace-real-model-one-turn-") as tmp:
        root = Path(tmp)
        roster = root / "synthetic-roster.json"
        _roster(roster)
        db = root / "synthetic.sqlite3"
        import_worldpack(db, Path(__file__).resolve().parents[1] /
                         "examples/driftspace-synthetic-demo.worldpack.v1.json")
        gateway = Gateway(db, world_id=WORLD)
        gateway.join(HUMAN)
        for name in names:
            gateway.join(name)
            if not reserve_npc(gateway.engine, name):
                raise AssertionError("Fresh synthetic world did not reserve NPC")
        gateway.engine.act(HUMAN, "say SYNTHETIC HUMAN MESSAGE")
        class _ObservedLocalProposer(LocalChatProposer):
            last_proposal: dict[str, str] | None = None
            call_count = 0

            def propose(self, host_view: str) -> dict[str, str]:
                self.call_count += 1
                result = super().propose(host_view)
                self.last_proposal = result
                return result

        observer = _ObservedLocalProposer(config)
        controller = CrewTurnCoordinator(
            gateway, roster, world_id=WORLD, human_actor_id=HUMAN,
            public_handles=HANDLES, styles=styles,
            proposer=observer, synthetic_trial=True,
        )
        before = _mem_available_kib()
        start = monotonic()
        try:
            turns = controller.run_speech_turns(((names[0], "real-neural-probe-001"),))
        except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
            print(json.dumps({
                "result": "REJECTED_OR_UNAVAILABLE", "exception": type(exc).__name__,
                "reason": str(exc)[:500], "elapsed_s": round(monotonic() - start, 3),
                "synthetic_model_proposal": (observer.last_proposal or {}).get("command", "")[:180],
                "model_request_count": observer.call_count,
                "model_rss_kib_before": baseline,
                "model_rss_kib_after": _rss_kib(args.model_pid) if args.model_pid else None,
                "mem_available_kib_before": before,
                "mem_available_kib_after": _mem_available_kib(),
                "claim": "one bounded request; no accepted host action proven",
            }, sort_keys=True))
            raise SystemExit(2)
        first_elapsed = monotonic() - start
        with closing(gateway.engine._connect()) as conn:
            speech = conn.execute(
                "SELECT payload_json FROM events WHERE kind='say' AND actor=?",
                (names[0],),
            ).fetchall()
            receipts = conn.execute(
                "SELECT action_id FROM action_receipts WHERE actor=?",
                ("@resident:" + names[0],),
            ).fetchall()
        if len(turns) != 1 or len(speech) != 1 or len(receipts) != 1:
            raise AssertionError("Real model output lacked a single host-owned game receipt")
        second = controller.run_speech_turns(((names[0], "real-neural-probe-001"),))
        if not second[0].replayed or observer.call_count != 1:
            raise AssertionError("Host receipt replay unexpectedly called the model")
        print(json.dumps({
            "result": "ACCEPTED_HOST_SPEECH",
            "first_inference_and_commit_s": round(first_elapsed, 3),
            "elapsed_s": round(monotonic() - start, 3),
            "model_request_count": observer.call_count,
            "replayed_without_second_inference": bool(second[0].replayed),
            "synthetic_speaker": "SyntheticTessa",
            "committed_speech": json.loads(speech[0]["payload_json"]).get("text"),
            "action_receipt": receipts[0][0],
            "model_rss_kib_before": baseline,
            "model_rss_kib_after": _rss_kib(args.model_pid) if args.model_pid else None,
            "mem_available_kib_before": before,
            "mem_available_kib_after": _mem_available_kib(),
            "claim": "real model proposal via existing local worker accepted in disposable world",
        }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-existing-loopback-model", action="store_true")
    parser.add_argument("--realm-src", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-pid", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=40)
    parser.add_argument("--max-tokens", type=int, default=96)
    run(parser.parse_args())
