"""Test credential-bound, session-limited room activity without prior-room history."""
import unittest
from driftspace.room_activity import RoomActivity, parse_activity_command, gateway_room_cursor


class RoomActivityTests(unittest.TestCase):
    def test_entry_cursor_prefers_authoritative_room_boundary(self):
        joined={"ok":True,"cursor":15,"room_entry_cursor":12}
        self.assertEqual(12,gateway_room_cursor(joined))
        self.assertEqual(12,RoomActivity("Rylok",gateway_room_cursor(joined)).cursor)

    def test_older_gateway_uses_global_cursor_without_guessing(self):
        self.assertEqual(15,gateway_room_cursor({"ok":True,"cursor":15}))

    def test_invalid_or_missing_room_entry_cursor_rejected(self):
        for message in (
            {"ok": True, "cursor":9, "room_entry_cursor":None},
            {"ok": True, "cursor":9, "room_entry_cursor":10},
            {"ok": True, "cursor":9, "room_entry_cursor":True},
            {"ok": True, "cursor":9, "room_entry_cursor":-1},
            {"ok": True, "cursor":9, "room_entry_cursor":"3"},
            {"ok": True, "cursor":-1},
            {"ok":False, "cursor":9},
        ):
            with self.subTest(message=message),self.assertRaises(ValueError):
                gateway_room_cursor(message)

    def test_new_session_does_not_replay_events_prior_to_login(self):
        f=RoomActivity("Rylok", cursor=18)
        args=[]
        def get(path):
            args.append(path)
            return {"ok":True,"cursor":19,"events":[
                {"id":19,"kind":"say","actor":"Visitor","text":"Visitor: Fresh greeting","room":"arrival"}
            ]}
        response=f.listen(get)
        self.assertEqual(["/api/v1/feed?after=18"],args)
        self.assertIn("Fresh greeting",response)
        self.assertNotIn("old gossip",response)
        self.assertIn("Fresh greeting",f.history(10))

    def test_filters_own_echo_but_advances_cursor(self):
        f=RoomActivity("Rylok",cursor=5)
        def get(path):
            return {"ok":True,"cursor":7,"events":[
                {"id":6,"actor":"Rylok","kind":"say","text":"Rylok: hello"},
                {"id":7,"actor":"Visitor","kind":"move","text":"Visitor arrived."},
            ]}
        self.assertIn("Visitor arrived.", f.listen(get))
        self.assertNotIn("Rylok: hello", f.history(10))
        self.assertEqual(7,f.cursor)

    def test_failed_server_response_does_not_advance_cursor(self):
        f=RoomActivity("Rylok",cursor=11)
        with self.assertRaises(ValueError):
            f.listen(lambda _:{"ok":True,"cursor":999,"events":[{"id":10,"actor":"Visitor","kind":"say","text":"old"}]})
        self.assertEqual(11,f.cursor)

    def test_room_transition_discards_previous_room_activity(self):
        f=RoomActivity("Rylok",cursor=2)
        f.listen(lambda _:{"ok":True,"cursor":3,"events":[
            {"id":3,"kind":"say","actor":"Visitor","text":"Visitor: From prior room"}]})
        f.enter_new_room(10)
        self.assertEqual("No recent activity in this room.",f.history(10))
        args=[]
        def get(path):
            args.append(path)
            return {"ok":True,"cursor":11,"events":[
                {"id":11,"kind":"say","actor":"Scout","text":"Scout: New location"}
            ]}
        self.assertIn("New location",f.listen(get))
        self.assertEqual(["/api/v1/feed?after=10"],args)

    def test_history_is_bounded_and_never_falls_back_to_engine_history(self):
        f=RoomActivity("Rylok",cursor=0)
        f.listen(lambda _:{"ok":True,"cursor":3,"events":[
            {"id":1,"actor":"A","kind":"say","text":"A: one"},
            {"id":2,"actor":"B","kind":"say","text":"B: two"},
            {"id":3,"actor":"C","kind":"say","text":"C: three"}]})
        self.assertNotIn("one",f.history(2))
        self.assertIn("two",f.history(2))
        with self.assertRaises(ValueError):
            f.history(51)
        with self.assertRaises(ValueError):
            f.history(0)

    def test_terminal_control_bytes_are_removed_from_host_feed(self):
        f=RoomActivity("Rylok",cursor=2)
        out=f.listen(lambda _:{"ok":True,"cursor":3,"events":[
            {"id":3,"actor":"Visit\x1b[31mor","kind":"say","text":"hi\x1b[0m\rfake prompt\n"}]})
        self.assertNotIn("\x1b",out)
        self.assertNotIn("\n",out)
        self.assertNotIn("\r",out)

    def test_listen_history_verbs_never_fall_back_to_engine_history(self):
        self.assertEqual(("listen", 10), parse_activity_command("listen"))
        self.assertEqual(("history", 10), parse_activity_command("history"))
        self.assertEqual(("history", 3), parse_activity_command("history 3"))
        self.assertIsNone(parse_activity_command("say hello"))
        for raw in ("listen 5", "listen please", "history 0", "history 51", "history abc"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_activity_command(raw)

    def test_whitespace_separated_history_stays_in_the_private_interceptor(self):
        # A future REALM verb parser may accept whitespace that was formerly
        # rejected. No history/listen variant may bypass this session reader.
        for raw, expected in (
            ("history\\t2", ("history", 2)),
            (" HISTORY\\n3 ", ("history", 3)),
            ("history\\u00a04", ("history", 4)),
            (" \\tlisten\\t", ("listen", 10)),
        ):
            with self.subTest(raw=repr(raw)):
                self.assertEqual(expected, parse_activity_command(raw))
        for raw in ("listen\\t5", "LISTEN\\nany", "history\\t0",
                    "history\\n51", "history\\tword"):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValueError):
                parse_activity_command(raw)
        self.assertIsNone(parse_activity_command("historybook"))

    def test_help_does_not_promise_pre_entry_history(self):
        from driftspace.terminal_ui import MUD_HELP
        self.assertIn("listen (new room activity)", MUD_HELP)
        self.assertIn("history [1-50] (this session only)", MUD_HELP)

    def test_untrusted_oversized_events_fail_closed(self):
        f=RoomActivity("Rylok",cursor=4)
        with self.assertRaises(ValueError):
            f.listen(lambda _:{"ok":True,"cursor":5,"events":[
                {"id":5,"actor":"Visitor","kind":"say","text":"a"*3000}]})
        self.assertEqual(4,f.cursor)


if __name__=="__main__":
    unittest.main()
