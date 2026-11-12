"""Opt-in six one-turn real-model probes using only disposable synthetic crew.

No actual Wreckforge canon, player saves, background scheduling or model loading.
Each turn is independently accepted/rejected; one rejected model action does not
silently abort the evidence for the other five synthetic identities.
"""
from __future__ import annotations

import argparse
import hashlib
from contextlib import closing
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

from qualify_real_crew_model import _rss_kib, _mem_available_kib
from verify_realm_crew_auth import HANDLES, HUMAN, WORLD, _roster


def main(args: argparse.Namespace) -> None:
    if not args.allow_existing_loopback_model:
        raise ValueError("Explicit existing-local-model permission required")
    if _mem_available_kib() is not None and _mem_available_kib() < 2 * 1024 ** 2:
        raise RuntimeError("Insufficient available RAM; no model request issued")
    if not (args.realm_src / "realm" / "principal_roles.py").is_file():
        raise ValueError("Pinned REALM checkout lacks NPC identity reservation")

    sys.path.insert(0, str(args.realm_src.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from driftspace.crew_turns import CrewTurnCoordinator
    from realm.gateway import Gateway
    from realm.npc_local_model import LocalChatConfig, LocalChatProposer
    from realm.principal_roles import reserve_npc
    from realm.worldpack import import_worldpack

    class ObservedProposer(LocalChatProposer):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.requests = 0
            self.last_command = None
            self.latencies_s = []
            self.model_inputs = []

        def propose(self, view):
            observed = json.loads(view)
            local_scene = observed["authorized_room_scene"]
            self.model_inputs.append({
                "public_handle": observed["host_identity"]["public_handle"],
                "scene_actor": local_scene["resident"],
                "distinct_view_sha256": hashlib.sha256(view.encode()).hexdigest(),
                "prior_npc_speech": any(
                    utterance["speaker"] in HANDLES
                    and utterance["speaker"] != HUMAN
                    for utterance in local_scene["recent_speech"]
                ),
            })
            self.requests += 1
            self.last_command = None
            start = time.monotonic()
            try:
                result = super().propose(view)
                self.last_command = result["command"]
                return result
            finally:
                self.latencies_s.append(round(time.monotonic() - start, 3))

    config = LocalChatConfig(
        endpoint=args.endpoint, model=args.model,
        timeout_seconds=args.timeout, max_tokens=args.max_tokens,
    )
    model = ObservedProposer(config)
    actors = [name for name in HANDLES if name != HUMAN]
    tested_actors = actors[:args.max_actors]
    styles = {
        actor: "Synthetic-only integration persona: " + HANDLES[actor]
        + ". You are speaking as this character, not as the captain. One short line only."
        for actor in actors
    }
    report = {
        "realm_source": args.realm_src.name,
        "world": WORLD, "model_requests": 0,
        "tested_actors": len(tested_actors),
        "rss_kib_before": _rss_kib(args.model_pid) if args.model_pid else None,
        "mem_available_kib_before": _mem_available_kib(),
        "results": [],
    }
    with tempfile.TemporaryDirectory(prefix="driftspace-real-six-model-") as td:
        root = Path(td)
        roster = root / "synthetic-crew.json"
        _roster(roster)
        db = root / "world.sqlite3"
        import_worldpack(
            db, Path(__file__).resolve().parents[1]
            / "examples/driftspace-synthetic-demo.worldpack.v1.json",
        )
        host = Gateway(db, world_id=WORLD)
        host.join(HUMAN)
        for actor in actors:
            host.join(actor)
            if not reserve_npc(host.engine, actor):
                raise AssertionError("synthetic resident reservation failed")
        host.engine.act(HUMAN, "say SYNTHETIC_CAPTAIN_AUTHORIZED_SCENE_CONTEXT")
        coordinator = CrewTurnCoordinator(
            host, roster, world_id=WORLD,
            human_actor_id=HUMAN, public_handles=HANDLES,
            styles=styles, proposer=model, synthetic_trial=True,
        )
        rejected_captain = False
        try:
            coordinator.run_speech_turns(((HUMAN, "cannot-automate-captain"),))
        except ValueError:
            rejected_captain = True
        if not rejected_captain or model.requests != 0:
            raise AssertionError("human captain was eligible for model control")
        for index, actor in enumerate(tested_actors):
            event = {"actor": actor, "handle": HANDLES[actor]}
            action = f"real-six-{index:02d}"
            seen_before = model.requests
            start = time.monotonic()
            try:
                (result,) = coordinator.run_speech_turns(((actor, action),))
                with closing(host.engine._connect()) as conn:
                    speech = conn.execute(
                        "SELECT payload_json FROM events "
                        "WHERE actor=? AND kind='say' ORDER BY id",
                        (actor,),
                    ).fetchall()
                    receipts = conn.execute(
                        "SELECT 1 FROM action_receipts "
                        "WHERE actor=? AND action_id=?",
                        ("@resident:" + actor, action),
                    ).fetchall()
                if len(speech) != 1 or len(receipts) != 1 or result.replayed:
                    raise AssertionError("speech or host receipt mismatch")
                prior_requests = model.requests
                (retry,) = coordinator.run_speech_turns(((actor, action),))
                if not retry.replayed or model.requests != prior_requests:
                    raise AssertionError("replay requested inference")
                event["status"] = "ACCEPTED"
                event["speech"] = json.loads(speech[0]["payload_json"])["text"]
                event["replay_without_inference"] = True
            except (ValueError, TimeoutError, RuntimeError, OSError) as exc:
                event["status"] = "REJECTED"
                event["reason"] = str(exc)[:160]
                event["last_untrusted_proposal"] = (model.last_command or "")[:180]
            event["duration_s"] = round(time.monotonic() - start, 3)
            event["model_requests_for_actor"] = model.requests - seen_before
            report["results"].append(event)
        with closing(host.engine._connect()) as conn:
            c = conn.execute(
                "SELECT COUNT(*) FROM events WHERE actor=? AND kind='say'", (HUMAN,),
            ).fetchone()[0]
            if c != 1:
                raise AssertionError("human captain action count mutated")
    report["model_requests"] = model.requests
    report["observed_model_inputs"] = model.model_inputs
    report["model_inputs_bound_to_correct_actor"] = all(
        source["scene_actor"] == actor
        and source["public_handle"] == HANDLES[actor]
        for source, actor in zip(model.model_inputs, tested_actors)
    ) and len(model.model_inputs) == len(tested_actors)
    report["observed_model_latency_s"] = model.latencies_s
    report["model_latency_median_s"] = (round(statistics.median(model.latencies_s), 3)
                                      if model.latencies_s else None)
    report["accepted_count"] = sum(v["status"] == "ACCEPTED" for v in report["results"])
    accepted_text = [v["speech"].strip().casefold() for v in report["results"]
                     if v["status"] == "ACCEPTED"]
    report["distinct_accepted_utterances"] = len(set(accepted_text))
    report["exact_duplicate_utterances"] = len(accepted_text) - len(set(accepted_text))
    report["rss_kib_after"] = _rss_kib(args.model_pid) if args.model_pid else None
    report["mem_available_kib_after"] = _mem_available_kib()
    report["note"] = (
        f"{len(tested_actors)} synthetic single-turn probes, "
        "not a voice or canon validation"
    )
    print(json.dumps(report, sort_keys=True))
    if (report["accepted_count"] != len(tested_actors)
            or report["distinct_accepted_utterances"] != len(tested_actors)
            or not report["model_inputs_bound_to_correct_actor"]):
        raise SystemExit(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-existing-loopback-model", action="store_true")
    ap.add_argument("--realm-src", type=Path, required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--model-pid", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=40)
    ap.add_argument("--max-tokens", type=int, default=96)
    ap.add_argument("--max-actors", type=int, choices=range(1, 7), default=6)
    main(ap.parse_args())
