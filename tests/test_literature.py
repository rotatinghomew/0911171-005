import unittest

from literature.analysis import prominence


class LiteratureTests(unittest.TestCase):
    def test_latest_revision_replaces_old_annotation(self):
        rows = [
            {"chapter": "c1", "character": "Alias", "revision": 1, "mentions": 4},
            {"chapter": "c1", "character": "Name", "revision": 2, "mentions": 2},
        ]
        self.assertEqual(prominence(rows, {"Alias": "Name"}, {"c1"})["mentions"], {"Name": 2})

    def test_scope_is_reported_even_when_empty(self):
        result = prominence([], {}, {"c1", "c2"})
        self.assertEqual(result["chapter_count"], 2)


if __name__ == "__main__":
    unittest.main()
