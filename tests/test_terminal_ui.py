"""Regression tests for private preview terminal presentation and social commands."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from driftspace.terminal_ui import (
    MUD_HELP, SocialStore, parse_social, render_terminal, terminal_prompt,
)


class TerminalPresentationTests(unittest.TestCase):
    def test_ansi_room_highlight_and_sanitizes_control_bytes(self):
        msg = "Exchange Hall\n\x1b[31mDanger\x1b[0m\nExits: north, south, west\nItems: Salvage tag"
        out = render_terminal(msg)
        self.assertIn("\x1b[1;36mExchange Hall\x1b[0m", out)
        self.assertIn("\x1b[1;33mExits: north, south, west\x1b[0m", out)
        self.assertIn("\x1b[1;32mItems: Salvage tag\x1b[0m", out)
        self.assertNotIn("\x1b[31mDanger", out)
        self.assertTrue(terminal_prompt().startswith("\x1b["))

    def test_no_ansi_fallback_and_useful_help(self):
        msg = "Service Bay\nExits: south\nYou say: hello"
        self.assertEqual(msg, render_terminal(msg, ansi=False))
        self.assertIn("crewchat", MUD_HELP)
        self.assertIn("emote", MUD_HELP)

class TerminalSocialTests(unittest.TestCase):
    def test_supported_verbs_have_separate_scopes(self):
        checks = {
            "emote dances a jig": ("room", "emote", "dances a jig"),
            "yell Hello?": ("world", "yell", "Hello?"),
            "ooc Is anyone there?": ("world", "ooc", "Is anyone there?"),
            "crewchat status": ("crew", "crewchat", "status"),
        }
        for raw, expected in checks.items():
            with self.subTest(raw=raw):
                result = parse_social(raw)
                self.assertEqual((result.scope, result.kind, result.text), expected)
        self.assertIsNone(parse_social("say hello"))

    def test_empty_and_oversized_messages_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_social("crewchat  ")
        with self.assertRaises(ValueError):
            parse_social("yell " + ("x" * 281))
        with self.assertRaises(ValueError):
            parse_social("emote \x1b[31m")

    def test_scoped_messages_persist_without_cross_channel_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SocialStore(Path(temp) / "messages.sqlite3")
            for raw in ["emote dances", "crewchat Secret", "ooc Testing"]:
                store.append("Rylok", parse_social(raw))
            self.assertEqual(3, store.count())
            crew = store.recent("crew")
            self.assertEqual([("Rylok", "crewchat", "Secret")], crew)
            self.assertEqual(1, len(store.recent("room")))
            self.assertNotIn("Secret", str(store.recent("world")))
            con = sqlite3.connect(store.path)
            try:
                self.assertEqual(0, con.execute("SELECT COUNT(*) FROM events WHERE scope='public'").fetchone()[0])
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
