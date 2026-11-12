"""Automatic room notifications for the private, Rylok-only terminal pilot."""
import unittest

from driftspace.room_activity import RoomActivity
from driftspace.room_watch import RoomWatch, parse_watch_command


class RoomWatchTests(unittest.TestCase):
    def test_terminal_help_discloses_automatic_updates_and_controls(self):
        from driftspace.terminal_ui import MUD_HELP
        self.assertIn("watch on/off/status", MUD_HELP)
        self.assertIn("automatically", MUD_HELP)

    def test_watch_verbs_are_intercepted_and_unsupported_variants_rejected(self):
        self.assertEqual("status", parse_watch_command("watch"))
        self.assertEqual("status", parse_watch_command("watch status"))
        self.assertEqual("on", parse_watch_command("WATCH ON"))
        self.assertEqual("off", parse_watch_command("watch off"))
        self.assertIsNone(parse_watch_command("say watch on"))
        for command in ("watch maybe", "watch on now", "watch 1", "watch\tfoo"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_watch_command(command)

    def test_automatic_notification_uses_authenticated_feed_and_does_not_repeat(self):
        calls=[]
        def get(path):
            calls.append(path)
            return {"ok":True,"cursor":6,"events":[
                {"id":6,"actor":"Visitor","kind":"say","text":"Visitor: Hello, Captain"},
            ]} if path.endswith("after=5") else {"ok":True,"cursor":6,"events":[]}
        activity=RoomActivity("Rylok",5)
        watcher=RoomWatch(activity,get)
        self.assertEqual("Visitor: Hello, Captain",watcher.poll())
        self.assertIsNone(watcher.poll())
        self.assertEqual(["/api/v1/feed?after=5","/api/v1/feed?after=6"],calls)
        self.assertIn("Hello, Captain",activity.history(10))

    def test_automatic_watching_is_turned_off_and_can_resume(self):
        calls=[]
        def get(path):
            calls.append(path)
            return {"ok":True,"cursor":1,"events":[{"id":1,"actor":"Visitor","text":"Hello","kind":"say"}]}
        watcher=RoomWatch(RoomActivity("Rylok",0),get)
        self.assertIn("disabled",watcher.configure("off"))
        self.assertIsNone(watcher.poll())
        self.assertEqual([],calls)
        self.assertIn("disabled",watcher.configure("status"))
        self.assertIn("enabled",watcher.configure("on"))
        self.assertEqual("Hello",watcher.poll())

    def test_invalid_host_response_does_not_repeat_errors_or_advance_cursor(self):
        activity=RoomActivity("Rylok",8)
        calls=[]
        def broken(path):
            calls.append(path)
            raise RuntimeError("private token should never be shown")
        watcher=RoomWatch(activity,broken)
        self.assertIsNone(watcher.poll())
        self.assertIsNone(watcher.poll())
        last=watcher.poll()
        self.assertIn("paused",last.lower())
        self.assertNotIn("private token",last)
        self.assertFalse(watcher.enabled)
        self.assertIsNone(watcher.poll())
        self.assertEqual(3,len(calls))
        self.assertEqual(8,activity.cursor)

    def test_moving_rooms_clears_session_history_and_filters_own_echo(self):
        activity=RoomActivity("Rylok",4)
        responses=[
            {"ok":True,"cursor":5,"events":[{"id":5,"actor":"Visitor","text":"Secret in old room","kind":"say"}]},
            {"ok":True,"cursor":12,"events":[
                {"id":11,"actor":"Rylok","text":"Rylok arrived","kind":"move"},
                {"id":12,"actor":"Scout","text":"New room greeting","kind":"say"},
            ]},
        ]
        watcher=RoomWatch(activity,lambda path:responses.pop(0))
        self.assertIn("Secret in old room",watcher.poll())
        activity.enter_new_room(10)
        self.assertEqual("New room greeting",watcher.poll())
        self.assertNotIn("Secret in old room",activity.history(10))
        self.assertNotIn("Rylok arrived",activity.history(10))


if __name__=="__main__":
    unittest.main()
