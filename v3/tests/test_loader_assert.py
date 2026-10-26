import json
import tempfile
import unittest
from pathlib import Path

from airp_v3.loader import LoaderError, load_items


class LoaderTests(unittest.TestCase):
    def test_derives_and_asserts(self):
        row = {
            "id": "t1",
            "content": "x",
            "expect_primitives": {
                "stance": "depicts",
                "objects": ["violence_person"],
                "qualifiers": [],
            },
            "expect_classes": ["violence"],
        }
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(json.dumps(row) + "\n")
            path = f.name
        items = load_items(path)
        self.assertEqual(items[0]["expect_classes"], ["violence"])

    def test_mismatch_raises(self):
        row = {
            "id": "t2",
            "content": "x",
            "expect_primitives": {
                "stance": "depicts",
                "objects": ["violence_person"],
                "qualifiers": [],
            },
            "expect_classes": ["self_harm"],
        }
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(json.dumps(row) + "\n")
            path = f.name
        with self.assertRaises(LoaderError):
            load_items(path)


if __name__ == "__main__":
    unittest.main()
