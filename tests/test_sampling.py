import unittest

from literature.sampling import build_plan

FRAME = {f"c{i}": {"work": "w1" if i <= 4 else "w2"} for i in range(1, 9)}


class SamplingTests(unittest.TestCase):
    def test_census_includes_everything_with_probability_one(self):
        plan = build_plan(FRAME, "p", "census")
        self.assertTrue(plan["probability_based"])
        self.assertEqual(plan["frame_size"], 8)
        self.assertEqual(len(plan["sampled_chapters"]), 8)
        self.assertTrue(all(s["probability"] == 1.0 for s in plan["selection"].values()))

    def test_bernoulli_is_seeded_and_records_probabilities(self):
        first = build_plan(FRAME, "p", "bernoulli", strata={"w1": 0.5, "w2": 0.5}, seed=7)
        second = build_plan(FRAME, "p", "bernoulli", strata={"w1": 0.5, "w2": 0.5}, seed=7)
        self.assertEqual(first["sampled_chapters"], second["sampled_chapters"])
        self.assertTrue(all(s["probability"] == 0.5 for s in first["selection"].values()))
        self.assertTrue(first["probability_based"])

    def test_convenience_has_no_probabilities(self):
        plan = build_plan(FRAME, "p", "convenience", chapters=["c1", "c5"])
        self.assertFalse(plan["probability_based"])
        self.assertEqual(plan["sampled_chapters"], ["c1", "c5"])
        self.assertIsNone(plan["selection"]["c1"]["probability"])
        self.assertFalse(plan["selection"]["c2"]["included"])

    def test_invalid_probability_and_strata_rejected(self):
        with self.assertRaises(ValueError):
            build_plan(FRAME, "p", "bernoulli", strata={"w1": 0, "w2": 0.5})
        with self.assertRaises(ValueError):
            build_plan(FRAME, "p", "bernoulli", strata={"w1": 0.5})

    def test_unknown_work_and_chapter_rejected(self):
        with self.assertRaises(ValueError):
            build_plan(FRAME, "p", "census", works=["nowhere"])
        with self.assertRaises(ValueError):
            build_plan(FRAME, "p", "convenience", chapters=["c9"])

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            build_plan(FRAME, "p", "lucky-draw")


if __name__ == "__main__":
    unittest.main()
