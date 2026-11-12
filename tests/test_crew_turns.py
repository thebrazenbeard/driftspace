"""Pure validation checks; REALM runtime integration is in tools/verify_realm_crew_turns.py."""
import unittest

from driftspace.crew_turns import _unique_object


class CrewTurnValidationTests(unittest.TestCase):
    def test_reject_ambiguous_scene_identity(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            _unique_object([("resident", "SyntheticTessa"), ("resident", "SyntheticCaptain")])

    def test_preserve_unambiguous_scene_values(self):
        self.assertEqual({"resident": "SyntheticTessa", "room": {"name": "lab"}},
                         _unique_object([("resident", "SyntheticTessa"),
                                         ("room", {"name": "lab"})]))


if __name__ == "__main__":
    unittest.main()
