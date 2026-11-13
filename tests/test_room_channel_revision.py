"""Auth-bound channel epoch invalidates cached private pilot room history.

REALM's authenticated feed includes 'channel_revision': a monotonic
host-issued membership marker. These are disposable callback fixtures,
not proof that the private VN2 terminal is already upgraded.
"""
from __future__ import annotations

from urllib.error import HTTPError
import unittest

from driftspace.room_activity import RoomActivity


class ChannelRevisionPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.activity = RoomActivity("Rylok", 3)

    def feed(self, *, cursor, events, revision=10, include_revision=True):
        result = {"ok": True, "cursor": cursor, "events": events}
        if include_revision:
            result["channel_revision"] = revision
        return result

    def seed(self):
        self.activity.listen(lambda _: self.feed(
            cursor=4,
            events=[{"id": 4, "actor": "Visitor", "kind": "say",
                     "text": "Visitor: previously received room words"}],
        ))
        self.assertIn("previously received", self.activity.history(10))

    def test_same_epoch_retains_ordinary_room_history(self):
        self.seed()
        new = self.feed(cursor=5, events=[{
            "id": 5, "actor": "Scout", "kind": "say", "text": "Scout: new room words",
        }])
        self.assertIn("new room words", self.activity.listen(lambda _: new))
        self.assertIn("previously received", self.activity.history(10))
        self.assertIn("new room words", self.activity.history(10))

    def test_changed_epoch_purges_history_even_with_zero_new_events(self):
        self.seed()
        result = self.activity.listen(lambda _: self.feed(
            cursor=4, revision=12, events=[],
        ))
        self.assertEqual("No new room activity.", result)
        self.assertEqual("No recent activity in this room.", self.activity.history())
        self.assertEqual(4, self.activity.cursor)

    def test_private_crewchat_can_display_but_is_never_cached_offline(self):
        delivered = self.activity.listen(lambda _: self.feed(
            cursor=5, events=[
                {"id": 4, "actor": "Crewmate", "kind": "crewchat",
                 "text": "[Private crew] A sensitive briefing"},
                {"id": 5, "actor": "Visitor", "kind": "say",
                 "text": "Visitor: public room comment"},
            ],
        ))
        self.assertIn("A sensitive briefing", delivered)
        self.assertIn("public room comment", delivered)
        self.assertNotIn("sensitive briefing", self.activity.history())
        self.assertIn("public room comment", self.activity.history())

    def test_regressed_epoch_fails_closed_without_advancing_cursor(self):
        self.seed()
        with self.assertRaises(ValueError):
            self.activity.listen(lambda _: self.feed(
                cursor=5, revision=9,
                events=[{"id": 5, "actor": "Visitor", "kind": "say",
                         "text": "should not surface"}],
            ))
        self.assertEqual(4, self.activity.cursor)
        self.assertEqual("No recent activity in this room.", self.activity.history())

    def test_epoch_rollback_remains_denied_on_repeated_poll(self):
        # Rejecting one stale response is insufficient if clearing cached
        # text also forgets the highest host-issued epoch ever observed.
        self.seed()
        stale = self.feed(cursor=4, revision=9, events=[])
        for attempt in range(2):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                self.activity.listen(lambda _: stale)
        self.assertEqual(4, self.activity.cursor)
        self.assertEqual("No recent activity in this room.", self.activity.history())

    def test_missing_or_malformed_epoch_never_preserves_old_cache(self):
        for marker in ("missing", None, True, -1, "12"):
            with self.subTest(marker=marker):
                self.setUp()
                self.seed()
                value = self.feed(
                    cursor=4, revision=marker,
                    include_revision=marker != "missing", events=[],
                )
                if marker == "missing":
                    self.assertEqual("No new room activity.",
                                     self.activity.listen(lambda _: value))
                else:
                    with self.assertRaises(ValueError):
                        self.activity.listen(lambda _: value)
                self.assertEqual(4, self.activity.cursor)
                self.assertEqual("No recent activity in this room.",
                                 self.activity.history())

    def test_auth_denial_or_host_epoch_conflict_invalidates_local_history(self):
        for status in (401, 403, 409):
            with self.subTest(status=status):
                self.setUp()
                self.seed()
                def denied(_):
                    raise HTTPError(
                        "http://127.0.0.1/private", status,
                        "auth or channel revision changed", {}, None,
                    )
                with self.assertRaises(HTTPError):
                    self.activity.listen(denied)
                self.assertEqual(4, self.activity.cursor)
                self.assertEqual("No recent activity in this room.",
                                 self.activity.history())

    def test_legacy_feed_refuses_private_and_unrecognized_event_types(self):
        for kind in ("crewchat", "CrewChat", "future_private_channel"):
            with self.subTest(kind=kind):
                activity = RoomActivity("Rylok", 3)
                response = self.feed(
                    cursor=4, include_revision=False,
                    events=[{"id": 4, "actor": "Crewmate",
                             "kind": kind, "text": "Synthetic private words"}],
                )
                with self.assertRaises(ValueError):
                    activity.listen(lambda _: response)
                self.assertEqual(3, activity.cursor)
                self.assertEqual("No recent activity in this room.",
                                 activity.history())

    def test_future_private_event_and_case_variant_never_enter_offline_cache(self):
        response = self.feed(cursor=6, events=[
            {"id": 4, "actor": "Crewmate", "kind": "CrewChat",
             "text": "Synthetic variant private words"},
            {"id": 5, "actor": "Crewmate", "kind": "future_private_channel",
             "text": "Synthetic future private words"},
            {"id": 6, "actor": "Visitor", "kind": "say",
             "text": "Visitor: ordinary room words"},
        ])
        displayed = self.activity.listen(lambda _: response)
        self.assertIn("Synthetic variant private words", displayed)
        self.assertIn("Synthetic future private words", displayed)
        self.assertIn("ordinary room words", displayed)
        cached = self.activity.history(50)
        self.assertNotIn("Synthetic", cached)
        self.assertIn("ordinary room words", cached)

    def test_missing_event_kind_is_malformed_not_cacheable(self):
        response = self.feed(cursor=4, events=[
            {"id": 4, "actor": "Crewmate", "text": "Undifferentiated private text"},
        ])
        with self.assertRaises(ValueError):
            self.activity.listen(lambda _: response)
        self.assertEqual(3, self.activity.cursor)
        self.assertEqual("No recent activity in this room.",
                         self.activity.history())

    def test_legacy_feed_still_replays_only_plain_room_activity(self):
        old = self.feed(cursor=4, include_revision=False, events=[{
            "id": 4, "actor": "Visitor", "kind": "say",
            "text": "Visitor: ordinary old-host event",
        }])
        self.activity.listen(lambda _: old)
        self.assertIn("old-host event", self.activity.history())


if __name__ == "__main__":
    unittest.main()
