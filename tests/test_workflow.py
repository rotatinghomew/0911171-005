import unittest

from literature.notebook import ResearchNotebook


def make_notebook(chapters=4):
    frame = [{"work": "w", "chapter": f"c{i}", "segments": ["s1", "s2"]} for i in range(1, chapters + 1)]
    notebook = ResearchNotebook(frame)
    notebook.register_aliases({"kid": "youngest", "little": "youngest"})
    notebook.register_kinship_group("sibs", [
        {"character": "eldest", "birth_order": 1},
        {"character": "middle", "birth_order": 2},
        {"character": "youngest", "birth_order": 3},
    ], work="w")
    return notebook


class AdjudicationTests(unittest.TestCase):
    def test_disagreement_excluded_until_adjudicated(self):
        notebook = make_notebook()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "kid", "annotator": "A",
             "revision": 1, "mentions": 3, "narrative_length": 90},
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "B",
             "revision": 1, "mentions": 1, "narrative_length": 10},
        ])
        disagreements = notebook.disagreements()
        self.assertEqual(len(disagreements), 1)
        self.assertEqual(disagreements[0]["character"], "youngest")
        result = notebook.compare(["sibs"], permutations=200)
        self.assertEqual(len(result["unresolved"]), 1)
        self.assertEqual(result["positions"]["3"]["annotated_chapters"], 0)
        notebook.adjudicate("c1", "youngest", {"appears": True, "mentions": 3, "narrative_length": 90},
                            editor="ed", segment="s1")
        self.assertEqual(notebook.disagreements(), [])
        resolved = notebook.compare(["sibs"], permutations=200)
        self.assertEqual(resolved["positions"]["3"]["narrative_length"], 90)
        unit = [u for u in resolved["units"] if u["character"] == "youngest"][0]
        self.assertTrue(unit["adjudicated"])

    def test_adjudication_requires_existing_annotation(self):
        notebook = make_notebook()
        with self.assertRaises(ValueError):
            notebook.adjudicate("c1", "ghost", {"mentions": 1}, editor="ed", segment="s1")

    def test_alias_and_duplicate_rows_do_not_stack(self):
        notebook = make_notebook()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "kid", "annotator": "A",
             "revision": 1, "mentions": 2, "narrative_length": 50},
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "B",
             "revision": 1, "mentions": 2, "narrative_length": 50},
            {"chapter": "c1", "segment": "s1", "character": "little", "annotator": "A",
             "revision": 2, "mentions": 2, "narrative_length": 50},
        ])
        result = notebook.compare(["sibs"], permutations=100)
        self.assertEqual(result["positions"]["3"]["annotated_chapters"], 1)
        self.assertEqual(result["positions"]["3"]["narrative_length"], 50)
        units = [u for u in result["units"] if u["character"] == "youngest"]
        self.assertEqual(len(units), 1)

    def test_withdrawn_revision_removes_the_record(self):
        notebook = make_notebook()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "A",
             "revision": 1, "mentions": 2, "narrative_length": 50},
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "A",
             "revision": 2, "withdrawn": True},
        ])
        result = notebook.compare(["sibs"], permutations=100)
        self.assertEqual(result["positions"]["3"]["annotated_chapters"], 0)


class ComparisonTests(unittest.TestCase):
    def fill(self, notebook, lengths):
        rows = []
        for chapter, values in lengths.items():
            for character, length in values.items():
                rows.append({"chapter": chapter, "segment": "s1", "character": character,
                             "annotator": "A", "revision": 1,
                             "mentions": 1 if length else 0, "narrative_length": length})
        notebook.register_annotations(rows)

    def test_zero_appearance_is_not_unannotated(self):
        notebook = make_notebook()
        self.fill(notebook, {"c1": {"youngest": 0}})
        result = notebook.compare(["sibs"], permutations=100)
        member = next(m for m in result["members"] if m["character"] == "youngest")
        self.assertEqual(member["annotated_chapters"], 1)
        self.assertEqual(member["zero_appearances"], 1)
        self.assertEqual(member["unannotated_chapters"], ["c2", "c3", "c4"])
        position = result["positions"]["3"]
        self.assertEqual(position["appearances"], 0)
        self.assertEqual(position["appearance_rate"], 0.0)

    def test_convenience_scope_is_descriptive_only(self):
        notebook = make_notebook()
        self.fill(notebook, {"c1": {"eldest": 10, "middle": 20, "youngest": 30}})
        result = notebook.compare(["sibs"], chapters={"c1"}, permutations=100)
        self.assertEqual(result["inference"]["method"], "convenience")
        self.assertIn("仅所选章节", result["inference"]["generalizable_to"])
        self.assertTrue(any("便利选章" in c for c in result["inference"]["caveats"]))

    def test_probability_plan_weights_and_caveats(self):
        notebook = make_notebook(chapters=6)
        lengths = {f"c{i}": {"eldest": 10, "middle": 20, "youngest": 40} for i in range(1, 7)}
        self.fill(notebook, lengths)
        plan = notebook.plan_sample("p1", "bernoulli", works=["w"], strata={"w": 0.5},
                                    groups=["sibs"], seed=3)
        result = notebook.compare(plan_id="p1", permutations=500, seed=5)
        self.assertEqual(result["scope"]["chapters"], plan["sampled_chapters"])
        self.assertEqual(result["inference"]["method"], "bernoulli")
        position = result["positions"]["3"]
        self.assertAlmostEqual(position["weighted_narrative_length"], 2 * position["narrative_length"])
        self.assertTrue(any("入样概率" in c for c in result["inference"]["caveats"]))
        self.assertEqual(result["inference"]["frame_size"], 6)

    def test_permutation_test_is_reproducible(self):
        notebook = make_notebook()
        self.fill(notebook, {f"c{i}": {"eldest": 10, "middle": 20, "youngest": 40} for i in range(1, 5)})
        first = notebook.compare(["sibs"], permutations=500, seed=9)
        second = notebook.compare(["sibs"], permutations=500, seed=9)
        self.assertEqual(first["tests"]["narrative_length"], second["tests"]["narrative_length"])
        self.assertTrue(first["conclusion"]["youngest_leads"])

    def test_drill_down_units_reference_chapters_and_annotations(self):
        notebook = make_notebook()
        self.fill(notebook, {"c1": {"eldest": 10, "middle": 20, "youngest": 30}})
        notebook.compare(["sibs"], note_id="n1", permutations=100)
        note = notebook.get_note("n1")
        unit = next(u for u in note["statistics"]["units"] if u["character"] == "youngest")
        self.assertEqual(unit["chapter"], "c1")
        self.assertTrue(unit["annotation_ids"])
        original = notebook.evidence("n1", "youngest")
        self.assertEqual(len(original), 1)
        self.assertEqual(original[0]["narrative_length"], 30)

    def test_scope_change_can_flip_conclusion(self):
        notebook = make_notebook()
        self.fill(notebook, {
            "c1": {"eldest": 10, "middle": 20, "youngest": 100},
            "c2": {"eldest": 10, "middle": 20, "youngest": 100},
            "c3": {"eldest": 120, "middle": 20, "youngest": 5},
            "c4": {"eldest": 120, "middle": 20, "youngest": 5},
        })
        report = notebook.compare_scopes(["sibs"], {
            "前半": {"c1", "c2"},
            "全部": {"c1", "c2", "c3", "c4"},
        }, permutations=200, seed=4)
        self.assertTrue(report["前半"]["conclusion"]["youngest_leads"])
        self.assertFalse(report["全部"]["conclusion"]["youngest_leads"])

    def test_note_id_cannot_be_reused_for_a_different_analysis(self):
        notebook = make_notebook()
        self.fill(notebook, {"c1": {"eldest": 10, "middle": 20, "youngest": 30}})
        notebook.compare(["sibs"], chapters={"c1"}, note_id="n1", permutations=100)
        with self.assertRaises(ValueError):
            notebook.compare(["sibs"], chapters={"c1", "c2"}, note_id="n1", permutations=100)


class ExcerptStalenessTests(unittest.TestCase):
    def make_note_with_excerpt(self):
        notebook = make_notebook()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "kid", "annotator": "A",
             "revision": 1, "mentions": 3, "narrative_length": 90},
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "B",
             "revision": 1, "mentions": 1, "narrative_length": 10},
        ])
        notebook.adjudicate("c1", "youngest", {"appears": True, "mentions": 3, "narrative_length": 90},
                            editor="ed", segment="s1")
        notebook.compare(["sibs"], note_id="n1", permutations=100)
        excerpt = notebook.add_excerpt("n1", {
            "character": "youngest", "chapter": "c1", "segment": "s1",
            "claim": {"mentions": 3, "narrative_length": 90},
        })
        return notebook, excerpt

    def test_excerpt_must_match_current_annotation(self):
        notebook = make_notebook()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "A",
             "revision": 1, "mentions": 3, "narrative_length": 90},
        ])
        notebook.compare(["sibs"], note_id="n1", permutations=100)
        with self.assertRaises(ValueError):
            notebook.add_excerpt("n1", {"character": "youngest", "chapter": "c1", "segment": "s1",
                                        "claim": {"narrative_length": 999}})
        with self.assertRaises(ValueError):
            notebook.add_excerpt("n1", {"character": "ghost", "chapter": "c9", "claim": {}})

    def test_readjudication_marks_excerpt_stale_and_updates_current_statistics(self):
        notebook, excerpt = self.make_note_with_excerpt()
        self.assertEqual(notebook.stale_excerpts("n1"), [])
        notebook.adjudicate("c1", "youngest", {"appears": True, "mentions": 1, "narrative_length": 10},
                            editor="ed2", segment="s1", comment="二次复核改采乙")
        stale = notebook.stale_excerpts("n1")
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["excerpt_id"], excerpt["excerpt_id"])
        self.assertEqual(stale[0]["differences"]["narrative_length"], {"摘录": 90, "当前": 10})
        refreshed = notebook.refresh("n1")
        self.assertEqual(refreshed["published_statistics"]["positions"]["3"]["narrative_length"], 90)
        self.assertEqual(refreshed["current_statistics"]["positions"]["3"]["narrative_length"], 10)
        self.assertEqual(len(refreshed["stale_excerpts"]), 1)
        original = notebook.evidence("n1", "youngest")
        self.assertEqual(sorted(row["narrative_length"] for row in original), [10, 90])

    def test_withdrawal_invalidates_excerpt(self):
        notebook, excerpt = self.make_note_with_excerpt()
        notebook.register_annotations([
            {"chapter": "c1", "segment": "s1", "character": "kid", "annotator": "A",
             "revision": 2, "withdrawn": True},
            {"chapter": "c1", "segment": "s1", "character": "youngest", "annotator": "B",
             "revision": 2, "withdrawn": True},
        ])
        stale = notebook.stale_excerpts("n1")
        self.assertEqual(len(stale), 1)
        self.assertIn("撤回", stale[0]["reason"])


if __name__ == "__main__":
    unittest.main()
