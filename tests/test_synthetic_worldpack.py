"""Source-only topology and non-canon checks for the sample worldpack."""

from collections import deque
import json
from pathlib import Path
import unittest


PACK = Path(__file__).resolve().parents[1] / "examples" / "driftspace-synthetic-demo.worldpack.v1.json"


class SyntheticWorldpackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_complete_declarative_worldpack_shape(self):
        self.assertEqual(set(self.pack), {"schema", "world_id", "name", "start_room", "rooms", "items"})
        self.assertEqual(self.pack["schema"], "realm.worldpack.v1")
        self.assertEqual(self.pack["world_id"], "driftspace-synthetic-demo")
        self.assertIn("Not Canon", self.pack["name"])
        self.assertEqual(len(self.pack["rooms"]), 4)
        self.assertEqual(len(self.pack["items"]), 2)

    def test_all_rooms_reachable_and_exits_reciprocal(self):
        graph = {r["id"]: r["exits"] for r in self.pack["rooms"]}
        self.assertIn(self.pack["start_room"], graph)
        visited = {self.pack["start_room"]}
        pending = deque(visited)
        while pending:
            here = pending.popleft()
            for there in graph[here].values():
                self.assertIn(there, graph)
                self.assertIn(here, graph[there].values())
                if there not in visited:
                    visited.add(there)
                    pending.append(there)
        self.assertEqual(visited, set(graph))

    def test_items_start_in_valid_rooms(self):
        rooms = {r["id"] for r in self.pack["rooms"]}
        ids = [i["id"] for i in self.pack["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i["room"] in rooms for i in self.pack["items"]))

    def test_no_scripts_model_bindings_or_private_character_records(self):
        text = PACK.read_text(encoding="utf-8").lower()
        for forbidden in ("model_binding", "wreckforge", "zyrik", "tessari", "crew_prompt", "https://", "sqlite", "private_source"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
