"""Pilot MUD command aliases and read-only item visibility."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from driftspace.pilot_actions import interpret_pilot_command


class PilotCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "synthetic.sqlite3"
        with sqlite3.connect(self.db) as c:
            c.execute("CREATE TABLE players(id TEXT PRIMARY KEY, room_id TEXT NOT NULL)")
            c.execute("CREATE TABLE items(id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, room_id TEXT, held_by TEXT)")
            c.execute("INSERT INTO players VALUES ('Rylok','arrival')")
            c.execute("INSERT INTO players VALUES ('Other','service')")
            c.executemany("INSERT INTO items VALUES (?,?,?,?,?)", [
                ("test_badge","Test Badge","A blank badge without access privileges.","arrival",None),
                ("lamp","Test Lamp","A cracked handheld diagnostic lamp.","service",None),
                ("chip","Test Chip","A small metal token.",None,"Rylok"),
                ("tool","Steel Tool","A generic tool.",None,"Other"),
            ])

    def resolve(self, text):
        return interpret_pilot_command(text,self.db,"Rylok")

    def test_get_pickup_obtain_and_pick_up_route_to_real_take(self):
        for text in ("get test", "pickup test badge", "obtain badge", "pick up badge", "grab badge"):
            with self.subTest(text=text):
                self.assertEqual("take test_badge",self.resolve(text).host_command)

    def test_drop_and_inventory_aliases(self):
        self.assertEqual("drop chip",self.resolve("discard Test Chip").host_command)
        self.assertEqual("inventory",self.resolve("inv").host_command)
        self.assertEqual("look",self.resolve("items").host_command)

    def test_suffix_word_alias_for_id_and_full_name(self):
        self.assertIn("blank badge", self.resolve("examine badge").response.lower())
        self.assertEqual("take test_badge", self.resolve("get badge").host_command)

    def test_whole_word_matching_uses_whitespace_not_substrings(self):
        with sqlite3.connect(self.db) as c:
            c.execute(
                "INSERT INTO items VALUES ('toolcase','Salvage Kit','A small sample kit.','arrival',NULL)"
            )
        self.assertIn("sample kit",self.resolve("examine kit").response)
        self.assertIn("not visible",self.resolve("examine lvage").response.lower())

    def test_examine_visible_item_and_carried_item(self):
        self.assertIn("blank badge",self.resolve("examine test badge").response)
        self.assertIn("small metal token",self.resolve("look at chip").response)

    def test_examine_cannot_read_other_room_or_other_actors_inventory(self):
        self.assertIn("not visible",self.resolve("examine lamp").response.lower())
        self.assertIn("not visible",self.resolve("inspect tool").response.lower())
        self.assertIn("not visible",self.resolve("examine ../private").response.lower())
        self.assertIn("not visible",interpret_pilot_command("examine badge",self.db,"Other").response.lower())

    def test_ambiguous_prefix_and_missing_targets_fail_closed(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO items VALUES ('badge2','Test Badge Copy','Different badge.','arrival',NULL)")
        self.assertIn("multiple",self.resolve("get test").response.lower())
        self.assertIn("multiple",self.resolve("examine test").response.lower())
        self.assertIn("what",self.resolve("get").response.lower())
        self.assertIn("what",self.resolve("inspect").response.lower())

    def test_help_advertises_current_commands(self):
        from driftspace.terminal_ui import MUD_HELP
        for command in ("get", "pickup", "obtain", "examine", "inspect", "map"):
            self.assertIn(command, MUD_HELP)

    def test_no_database_is_created_by_read_only_inspection(self):
        vanished = Path(self.temp.name) / "does-not-exist.sqlite3"
        self.assertFalse(vanished.exists())
        result = interpret_pilot_command("examine badge", vanished, "Rylok")
        self.assertIn("not visible", result.response.lower())
        self.assertFalse(vanished.exists())

    def test_map_and_original_commands(self):
        self.assertEqual("/api/v1/map",self.resolve("map").resource)
        self.assertIsNone(self.resolve("say hello"))
        self.assertIsNone(self.resolve("north"))
