import unittest

from literature.notebook import ResearchNotebook


class NotebookTests(unittest.TestCase):
    def test_saved_statistics_and_evidence_use_the_same_frame(self):
        notebook = ResearchNotebook([{"chapter": "c1"}, {"chapter": "c2"}])
        rows = [{"chapter": "c1", "character": "alias", "revision": 1, "mentions": 3}]
        note = notebook.describe("draft", rows, {"alias": "hero"}, {"c1"}, "convenience")
        self.assertEqual(note["statistics"]["mentions"], {"hero": 3})
        self.assertEqual(notebook.evidence("draft", "hero"), rows)
        rows[0]["mentions"] = 20
        self.assertEqual(notebook.evidence("draft", "hero")[0]["mentions"], 3)

    def test_partial_selection_is_not_a_census(self):
        notebook = ResearchNotebook([{"chapter": "c1"}, {"chapter": "c2"}])
        with self.assertRaises(ValueError):
            notebook.describe("draft", [], {}, {"c1"}, "census")
