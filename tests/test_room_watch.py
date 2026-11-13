"""Automatic room notifications for the private, Rylok-only terminal pilot."""
import unittest
from urllib.error import HTTPError, URLError

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

    def test_transient_gateway_network_errors_count_toward_bounded_pause(self):
        for kind in ("socket", "url", "http503"):
            with self.subTest(kind=kind):
                calls = []
                def get(path):
                    calls.append(path)
                    if kind == "socket":
                        raise OSError("secret socket diagnostic")
                    if kind == "url":
                        raise URLError("secret connection detail")
                    raise HTTPError("http://localhost/private", 503,
                                    "secret internal response", {}, None)
                state = RoomActivity("Rylok", 8)
                watcher = RoomWatch(state, get)
                self.assertIsNone(watcher.poll())
                self.assertIsNone(watcher.poll())
                notice = watcher.poll()
                self.assertIn("paused", notice)
                self.assertNotIn("secret", notice)
                self.assertFalse(watcher.enabled)
                self.assertEqual(3, len(calls))
                self.assertEqual(8, state.cursor)

    def test_local_permission_failure_is_not_treated_as_gateway_outage(self):
        activity = RoomActivity("Rylok", 8)
        def denied(path):
            raise PermissionError("host file or credential access denied")
        watcher = RoomWatch(activity, denied)
        with self.assertRaises(PermissionError):
            watcher.poll()
        self.assertEqual(0, watcher._consecutive_errors)
        self.assertEqual(8, activity.cursor)

    def test_authentication_denial_is_propagated_not_silently_retried(self):
        # A revoked bearer must not be treated as ordinary transient trouble.
        for status in (401, 403):
            with self.subTest(status=status):
                def denied(path):
                    raise HTTPError("http://localhost/private", status,
                                    "authentication failed", {}, None)
                watcher = RoomWatch(RoomActivity("Rylok", 10), denied)
                with self.assertRaises(HTTPError):
                    watcher.poll()
                self.assertEqual(0, watcher._consecutive_errors)
                self.assertEqual(10, watcher.activity.cursor)

    def test_channel_epoch_conflict_409_reaches_authenticated_terminal_owner(self):
        # REALM can detect group membership changing after feed read and
        # before HTTP bytes are sent. This is an authorization conflict, not
        # an ordinary outage to retry silently three times.
        activity = RoomActivity("Rylok", 2)
        activity.listen(lambda _: {
            "ok": True, "cursor": 3, "channel_revision": 4,
            "events": [{"id": 3, "actor": "Visitor", "kind": "say",
                        "text": "Visitor: previously received room words"}],
        })
        self.assertIn("previously received", activity.history(10))
        calls = []
        def changed(path):
            calls.append(path)
            raise HTTPError("http://127.0.0.1/private", 409,
                            "host membership changed", {}, None)
        watcher = RoomWatch(activity, changed)
        with self.assertRaises(HTTPError) as denied:
            watcher.poll()
        self.assertEqual(409, denied.exception.code)
        self.assertEqual(1, len(calls))
        self.assertEqual(0, watcher._consecutive_errors)
        self.assertTrue(watcher.enabled)
        self.assertEqual(3, activity.cursor)
        self.assertEqual("No recent activity in this room.", activity.history(10))

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
