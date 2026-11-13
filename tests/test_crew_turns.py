"""Pure validation checks; REALM runtime integration is in tools/verify_realm_crew_turns.py."""
import unittest

from driftspace.crew_turns import CrewTurnCoordinator, _unique_object, _synthetic_voice_template_key


class CrewTurnValidationTests(unittest.TestCase):
    def test_reject_ambiguous_scene_identity(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            _unique_object([("resident", "SyntheticTessa"), ("resident", "SyntheticCaptain")])

    def test_name_substitution_does_not_count_as_a_new_voice(self):
        tessa = "Welcome aboard, SyntheticTessa. Your cargo is cleared for docking."
        calamar = "Welcome aboard, SyntheticCalamar. Your cargo is cleared for docking."
        self.assertEqual(_synthetic_voice_template_key(tessa),
                         _synthetic_voice_template_key(calamar))
        self.assertNotEqual(_synthetic_voice_template_key("say inspect the vial"),
                            _synthetic_voice_template_key("say inspect the map"))

    def test_synthetic_template_key_does_not_replace_partial_words(self):
        self.assertNotEqual(
            _synthetic_voice_template_key("A ghostly vessel drifted."),
            _synthetic_voice_template_key("A vessel drifted."),
        )

    def test_quality_retry_budget_never_accepts_bools_or_more_than_one(self):
        for invalid in (True, -1, 2, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CrewTurnCoordinator(
                    None, None, world_id="driftspace-synthetic-demo",
                    human_actor_id="SyntheticCaptain", public_handles={},
                    styles={}, synthetic_trial=True, max_quality_retries=invalid,
                )

    def test_preserve_unambiguous_scene_values(self):
        self.assertEqual({"resident": "SyntheticTessa", "room": {"name": "lab"}},
                         _unique_object([("resident", "SyntheticTessa"),
                                         ("room", {"name": "lab"})]))


if __name__ == "__main__":
    unittest.main()
