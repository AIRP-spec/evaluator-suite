import json
import tempfile
import unittest
from pathlib import Path

from airp_v3.filter_cse import filter_rows, category_hit, keyword_hit


class FilterTests(unittest.TestCase):
    def test_category_cse(self):
        self.assertEqual(category_hit({"hazard": "cse", "prompt": "x"}), "cse")
        self.assertIsNotNone(category_hit({"violated_categories": ["Sexual (minor)"]}))

    def test_keyword_age(self):
        self.assertIsNotNone(keyword_hit("a 14 year old joins a club"))
        self.assertIsNone(keyword_hit("Explain photosynthesis."))

    def test_counts(self):
        rows = [
            {"id": "a", "prompt": "ok", "hazard": "benign"},
            {"id": "b", "prompt": "x", "hazard": "cse"},
            {"id": "c", "prompt": "help a teenager budget", "category": "benign"},
        ]
        kept, report = filter_rows(rows)
        self.assertEqual(report["n_kept"], 1)
        self.assertEqual(report["n_dropped_category"], 1)
        self.assertEqual(report["n_dropped_keyword"], 1)
        self.assertEqual(kept[0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
