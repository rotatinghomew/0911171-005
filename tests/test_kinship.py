import unittest

from literature.kinship import KinshipRegistry


class KinshipTests(unittest.TestCase):
    def test_positions_must_be_contiguous_from_one(self):
        registry = KinshipRegistry()
        with self.assertRaises(ValueError):
            registry.register("g", [
                {"character": "a", "birth_order": 1},
                {"character": "b", "birth_order": 3},
            ])

    def test_duplicate_group_and_character_rejected(self):
        registry = KinshipRegistry()
        registry.register("g", [{"character": "a", "birth_order": 1}], work="w")
        with self.assertRaises(ValueError):
            registry.register("g", [{"character": "b", "birth_order": 1}])
        with self.assertRaises(ValueError):
            registry.register("h", [
                {"character": "a", "birth_order": 1},
                {"character": "a", "birth_order": 2},
            ])

    def test_lookup(self):
        registry = KinshipRegistry()
        registry.register("g", [
            {"character": "a", "birth_order": 1},
            {"character": "b", "birth_order": 2},
        ], work="w")
        self.assertEqual(registry.get("g")["work"], "w")
        self.assertEqual(registry.position_of("g", "b"), 2)
        with self.assertRaises(ValueError):
            registry.get("missing")
        with self.assertRaises(ValueError):
            registry.position_of("g", "outsider")


if __name__ == "__main__":
    unittest.main()
