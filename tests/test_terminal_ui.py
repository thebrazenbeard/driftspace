"""Regression tests for private preview terminal presentation and social commands."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from driftspace.terminal_ui import (
    MUD_HELP, SocialStore, parse_social, render_terminal, terminal_prompt, terminal_palette,
)


class TerminalPresentationTests(unittest.TestCase):
    def test_ansi_room_highlight_and_sanitizes_control_bytes(self):
        msg = "Exchange Hall\n\x1b[31mDanger\x1b[0m\nExits: north, south, west\nItems: Salvage tag"
        out = render_terminal(msg)
        self.assertIn("\x1b[1;36mExchange Hall\x1b[0m", out)
        self.assertIn("\x1b[37mExits:\x1b[0m \x1b[1;33mnorth, south, west\x1b[0m", out)
        self.assertNotIn("\x1b[1;33mExits: north", out)
        self.assertIn("\x1b[37mItems:\x1b[0m \x1b[1;32mSalvage tag\x1b[0m", out)
        self.assertNotIn("\x1b[1;32mItems: Salvage", out)
        self.assertNotIn("\x1b[31mDanger", out)
        self.assertTrue(terminal_prompt().startswith("\x1b["))

    def test_other_labels_and_values_are_distinct(self):
        response = "You carry: Test Lamp\nYou take Test Badge.\nYou say: Hello?"
        rendered = render_terminal(response)
        self.assertIn("\x1b[37mYou carry:\x1b[0m \x1b[1;32mTest Lamp\x1b[0m", rendered)
        self.assertIn("\x1b[37mYou take\x1b[0m \x1b[1;32mTest Badge.\x1b[0m", rendered)
        self.assertIn("\x1b[37mYou say:\x1b[0m \x1b[1;35mHello?\x1b[0m", rendered)

    def test_color_words_in_room_prose_only(self):
        example = (
            "Arrival Platform\n"
            "Copper coils blink amber. The black monitor reflects silver dust; "
            "a coppery scratch is not a color name.\n"
            "Exits: east\n"
            "You say: amber copper black\n"
        )
        output = render_terminal(example)
        self.assertIn("\x1b[38;2;184;115;51mCopper\x1b[0m", output)
        self.assertIn("\x1b[38;2;255;191;0mamber\x1b[0m", output)
        self.assertIn("\x1b[30;47mblack\x1b[0m", output)
        self.assertIn("\x1b[38;2;192;192;192msilver\x1b[0m", output)
        self.assertIn("coppery", output)
        self.assertIn("You say:\x1b[0m \x1b[1;35mamber copper black\x1b[0m", output)
        self.assertEqual(example, render_terminal(example, ansi=False))

    def test_room_description_colors_do_not_bleed_into_exits(self):
        text = "Exchange Hall\nAmber and black placards.\nExits: north, west\nItems: Copper token"
        out = render_terminal(text)
        self.assertIn("\x1b[37mExits:\x1b[0m \x1b[1;33mnorth, west\x1b[0m", out)
        self.assertIn("\x1b[37mItems:\x1b[0m \x1b[1;32mCopper token\x1b[0m", out)
        self.assertNotIn("\x1b[38;2;184;115;51mCopper token", out)

    def test_extended_palette_and_multiword_grey_names(self):
        scene = (
            "Viewing Gallery\n"
            "A cyan lamp glows over a pink ribbon and a light grey panel. "
            "Dark gray rails frame a bright blue display; black glass reflects teal.\n"
            "Exits: north\nItems: Pink Badge\nYou say: cyan pink"
        )
        rendered = render_terminal(scene)
        for expected in (
            "\x1b[38;2;0;255;255mcyan\x1b[0m",
            "\x1b[38;2;255;105;180mpink\x1b[0m",
            "\x1b[38;2;211;211;211mlight grey\x1b[0m",
            "\x1b[38;2;144;144;144mDark gray\x1b[0m",
            "\x1b[38;2;98;187;255mbright blue\x1b[0m",
            "\x1b[30;47mblack\x1b[0m",
            "\x1b[38;2;0;180;170mteal\x1b[0m",
        ):
            self.assertIn(expected, rendered)
        self.assertIn("\x1b[1;32mPink Badge\x1b[0m", rendered)
        self.assertIn("\x1b[1;35mcyan pink\x1b[0m", rendered)
        self.assertNotIn("\x1b[38;2;255;105;180mPink Badge", rendered)

    def test_american_british_and_hyphenated_aliases(self):
        text = ("Exchange Hall\nA light gray panel and a light-grey pane face "
                "dark grey and dark-gray bulkheads. Cyanide is uncolored.\nExits: west")
        rendered = render_terminal(text)
        self.assertEqual(2, rendered.count("\x1b[38;2;211;211;211m"))
        self.assertEqual(2, rendered.count("\x1b[38;2;144;144;144m"))
        self.assertIn("Cyanide", rendered)
        self.assertNotIn("\x1b[38;2;0;255;255mCyan", rendered)

    def test_color_word_spans_reset_before_normal_room_text(self):
        text = "Service Bay\ncopper amber cyan pink light grey dark grey words.\nExits: south"
        rendered = render_terminal(text)
        self.assertIn("\x1b[38;2;255;105;180mpink\x1b[0m ", rendered)
        self.assertIn("\x1b[37mExits:\x1b[0m \x1b[1;33msouth\x1b[0m", rendered)
        self.assertEqual(text, render_terminal(text, ansi=False))

    def test_palette_preview_shows_color_swatches_and_resets(self):
        preview = terminal_palette()
        self.assertIn("Classic:", preview)
        self.assertIn("Extended:", preview)
        self.assertIn("\x1b[38;2;0;255;255mcyan\x1b[0m", preview)
        self.assertIn("\x1b[38;2;255;105;180mpink\x1b[0m", preview)
        self.assertIn("\x1b[38;2;211;211;211mlight grey\x1b[0m", preview)
        self.assertIn("\x1b[38;2;144;144;144mdark grey\x1b[0m", preview)
        self.assertIn("\x1b[30;47mblack\x1b[0m", preview)
        self.assertIn("room descriptions", preview)
        self.assertIn("palette", MUD_HELP)

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
