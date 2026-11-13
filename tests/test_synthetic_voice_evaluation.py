"""Synthetic style criteria are not approved Wreckforge characterization."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from qualify_isolated_voice import score_synthetic_style


class SyntheticVoiceEvaluationTests(unittest.TestCase):
    def test_observed_synthetic_tessa_reply_does_not_pass_first_person(self):
        result = score_synthetic_style(
            "SyntheticTessa", "Gyroscope alignment stabilized, resuming normal operations."
        )
        self.assertTrue(result["required_topic"])
        self.assertFalse(result["first_person"])

    def test_observed_synthetic_calamar_reply_does_not_pass_question_form(self):
        result = score_synthetic_style(
            "SyntheticCalamar", "'Test Badge activated. Sterile flask at your disposal.'"
        )
        self.assertTrue(result["required_topic"])
        self.assertFalse(result["requested_question_form"])
        self.assertFalse(result["first_person"])

    def test_first_person_topic_and_form_can_pass_typed_synthetic_rubric(self):
        tessa = score_synthetic_style(
            "SyntheticTessa", "I have recalibrated my gyroscope."
        )
        calamar = score_synthetic_style(
            "SyntheticCalamar", "May I test my sterile flask?"
        )
        self.assertTrue(all(tessa.values()), tessa)
        self.assertTrue(all(calamar.values()), calamar)

    def test_automatic_name_replacement_is_not_acceptable_style(self):
        item = score_synthetic_style(
            "SyntheticTessa", "Welcome aboard, SyntheticTessa. Your cargo is ready."
        )
        self.assertFalse(item["no_generic_greeting"])
        self.assertFalse(item["no_self_address"])


if __name__ == "__main__":
    unittest.main()
