"""Synthetic contract tests; no private Wreckforge roster is imported."""

import json
import tempfile
import unittest
from pathlib import Path

from driftspace.crew_projection import CrewProjection


WORLD = "synthetic-review-world"
HUMAN = "synthetic_captain"
HANDLES = {
    HUMAN: "Rylok",
    "actor_t": "Tessa",
    "actor_c": "Calamar",
    "actor_g": "Ghost",
    "actor_k": "Kira",
    "actor_b": "Bulwark",
    "actor_m": "Milo",
}


def proposal():
    actors = []
    for actor_id in HANDLES:
        human = actor_id == HUMAN
        actors.append({
            "actor_id": actor_id,
            "control": "human_pc" if human else "ai_npc",
            "ai_control_allowed": not human,
            "model_binding": None,
            "runtime_state": "not_activated",
            "action_authority": None if human else "host_validated_proposal_only",
            "private_role": "never expose this field",
        })
    return {
        "schema": "realm.private_crew_proposal.v1",
        "world_id": WORLD,
        "classification": "private_proposed",
        "activated": False,
        "actors": actors,
        "private_source": "never expose this field",
    }


class CrewProjectionContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="driftspace-synthetic-")
        self.path = Path(self.tmp.name) / "private.json"
        self.write(proposal())

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, payload):
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self, **kwargs):
        return CrewProjection.load(
            self.path, world_id=kwargs.get("world_id", WORLD),
            human_actor_id=kwargs.get("human_actor_id", HUMAN),
            public_handles=kwargs.get("public_handles", HANDLES),
        )

    def test_six_npcs_and_human_rylok_only_public_handles(self):
        actual = self.load().present("authenticated-player")
        self.assertEqual(actual["world_id"], WORLD)
        self.assertEqual(actual["status"], "proposed_not_activated")
        self.assertEqual([x["handle"] for x in actual["crew"]], list(HANDLES.values()))
        self.assertEqual([x["control_type"] for x in actual["crew"]], ["human"] + ["ai"] * 6)
        self.assertNotIn("synthetic_captain", json.dumps(actual))
        self.assertNotIn("never expose", json.dumps(actual))
        self.assertNotIn("private_", json.dumps(actual))

    def test_payload_is_not_shared_between_requests(self):
        view = self.load()
        first = view.present("one")
        first["crew"][0]["handle"] = "tampered"
        self.assertEqual(view.present("two")["crew"][0]["handle"], "Rylok")

    def test_world_mismatch_fails(self):
        with self.assertRaises(ValueError):
            self.load(world_id="other-world")

    def test_activation_claim_fails(self):
        payload = proposal()
        payload["activated"] = True
        self.write(payload)
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_json_field_fails(self):
        original = self.path.read_text(encoding="utf-8")
        self.path.write_text(original.replace('"activated": false', '"activated": true, "activated": false', 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_actor_identity_fails(self):
        payload = proposal()
        payload["actors"][1]["actor_id"] = HUMAN.upper()
        self.write(payload)
        with self.assertRaises(ValueError):
            self.load()

    def test_ai_cannot_take_human_control(self):
        payload = proposal()
        payload["actors"][0]["ai_control_allowed"] = True
        self.write(payload)
        with self.assertRaises(ValueError):
            self.load()

    def test_model_binding_and_runtime_activation_fail(self):
        payload = proposal()
        payload["actors"][2]["model_binding"] = "unverified.gguf"
        self.write(payload)
        with self.assertRaises(ValueError):
            self.load()
        payload["actors"][2]["model_binding"] = None
        payload["actors"][2]["runtime_state"] = "active"
        self.write(payload)
        with self.assertRaises(ValueError):
            self.load()

    def test_public_handles_cannot_be_missing_or_doubled(self):
        with self.assertRaises(ValueError):
            self.load(public_handles={HUMAN: "Rylok"})
        alias_collision = dict(HANDLES)
        alias_collision["actor_t"] = "rylok"
        with self.assertRaises(ValueError):
            self.load(public_handles=alias_collision)


if __name__ == "__main__":
    unittest.main()
