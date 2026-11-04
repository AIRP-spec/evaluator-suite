import tempfile
import unittest
from pathlib import Path

from airp_v3.collect import CollectBlocked, find_approval


class CollectGateTests(unittest.TestCase):
    def test_missing(self):
        with self.assertRaises(CollectBlocked):
            find_approval(Path("/tmp/definitely-missing-openrouter-approval"))

    def test_short(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("too short")
            path = Path(f.name)
        with self.assertRaises(CollectBlocked):
            find_approval(path)

    def test_ok(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(
                "I, Justin Flores, approve OpenRouter red-teaming for AIRP evaluator-suite "
                "collection under the standing brief. Approval reference: test-fixture."
            )
            path = Path(f.name)
        text = find_approval(path)
        self.assertIn("Justin", text)


if __name__ == "__main__":
    unittest.main()
