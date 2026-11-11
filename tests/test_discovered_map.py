"""Private pilot discovered-room map: read-only and actor-scoped."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from driftspace.discovered_map import render_discovered_map


class DiscoveredMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "game.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.executescript("""
            CREATE TABLE players(id TEXT PRIMARY KEY,room_id TEXT);
            CREATE TABLE rooms(id TEXT PRIMARY KEY,name TEXT,description TEXT);
            CREATE TABLE exits(room_id TEXT,direction TEXT,destination TEXT);
            CREATE TABLE events(id INTEGER PRIMARY KEY, actor TEXT,room_id TEXT,kind TEXT);
            CREATE TABLE world_meta(key TEXT PRIMARY KEY,value TEXT);
            INSERT INTO world_meta VALUES('start_room','arrival');
            INSERT INTO players VALUES('Rylok','arrival');
            INSERT INTO players VALUES('Visitor','service');
            INSERT INTO rooms VALUES('arrival','Arrival Platform','');
            INSERT INTO rooms VALUES('exchange','Exchange Hall','');
            INSERT INTO rooms VALUES('service','Service Bay','');
            INSERT INTO rooms VALUES('gallery','Viewing Gallery','');
            INSERT INTO exits VALUES('arrival','east','exchange');
            INSERT INTO exits VALUES('exchange','west','arrival');
            INSERT INTO exits VALUES('exchange','north','service');
            INSERT INTO exits VALUES('service','south','exchange');
            INSERT INTO exits VALUES('exchange','south','gallery');
            INSERT INTO exits VALUES('gallery','north','exchange');
            INSERT INTO events(actor,room_id,kind) VALUES('Rylok','arrival','join');
            INSERT INTO events(actor,room_id,kind) VALUES('Visitor','service','join');
            """)

    def test_starts_with_only_known_room_and_exit_direction(self):
        result=render_discovered_map(self.path,"Rylok")
        self.assertIn("Arrival Platform",result)
        self.assertIn("east: unexplored",result)
        self.assertNotIn("Exchange Hall",result)
        self.assertNotIn("Service Bay",result)
        self.assertNotIn("Viewing Gallery",result)

    def test_movement_reveals_visited_rooms_only(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE players SET room_id='exchange' WHERE id='Rylok'")
            db.execute("INSERT INTO events(actor,room_id,kind) VALUES('Rylok','exchange','move')")
        result=render_discovered_map(self.path,"Rylok")
        self.assertIn("Exchange Hall",result)
        self.assertIn("Arrival Platform",result)
        self.assertIn("north: unexplored",result)
        self.assertIn("south: unexplored",result)
        self.assertNotIn("Service Bay",result)
        self.assertNotIn("Viewing Gallery",result)
        self.assertIn("* [Exchange Hall]",result)

    def test_other_actor_history_does_not_grant_room_knowledge(self):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO events(actor,room_id,kind) VALUES('Visitor','gallery','move')")
        own=render_discovered_map(self.path,"Rylok")
        self.assertNotIn("Viewing Gallery",own)
        other=render_discovered_map(self.path,"Visitor")
        self.assertIn("Viewing Gallery",other)
        self.assertNotIn("Arrival Platform",other)

    def test_read_only_and_missing_world_fail_closed(self):
        before=self.path.read_bytes()
        render_discovered_map(self.path,"Rylok")
        self.assertEqual(before,self.path.read_bytes())
        missing=Path(self.temp.name)/"nope.sqlite3"
        self.assertIn("unavailable",render_discovered_map(missing,"Rylok").lower())
        self.assertFalse(missing.exists())
        self.assertIn("unavailable",render_discovered_map(self.path,"Unjoined").lower())

    def test_map_coordinates_do_not_recenter_when_player_moves(self):
        with sqlite3.connect(self.path) as db:
            for room in ("exchange","service","gallery"):
                db.execute("INSERT INTO events(actor,room_id,kind) VALUES('Rylok',?,'move')",(room,))
            db.execute("UPDATE players SET room_id='service' WHERE id='Rylok'")
        first=render_discovered_map(self.path,"Rylok").replace("* [","  [")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE players SET room_id='gallery' WHERE id='Rylok'")
        second=render_discovered_map(self.path,"Rylok").replace("* [","  [")
        self.assertEqual(first,second,"A player move must not rearrange known map coordinates")

    def test_help_marks_map_as_discovery_scoped(self):
        from driftspace.terminal_ui import MUD_HELP
        self.assertIn("map (discovered rooms only)", MUD_HELP)

    def test_full_station_coordinates_and_current_marker(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE players SET room_id='gallery' WHERE id='Rylok'")
            for room in ("exchange","service","gallery"):
                db.execute("INSERT INTO events(actor,room_id,kind) VALUES('Rylok',?,'move')",(room,))
        result=render_discovered_map(self.path,"Rylok")
        self.assertIn("[Arrival Platform]",result)
        self.assertIn("[Exchange Hall]",result)
        self.assertIn("[Service Bay]",result)
        self.assertIn("* [Viewing Gallery]",result)
        self.assertIn("---",result)
        self.assertIn("|",result)


if __name__=="__main__":
    unittest.main()
