import sys
import unittest
from pathlib import Path

V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3))
from airp_v3 import inset  # noqa: E402

# Synthetic benign data only.
A = "The ferry to the island leaves at seven and returns after the last market bell rings."
B = "Grandmother keeps the brass lamp polished and lights it every evening before supper."
C = "Volunteers repainted the library benches green and planted marigolds along the path."


class InSet(unittest.TestCase):
    def test_exact_keeps_lower_id(self):
        r = inset.resolve([{"id": "r-2", "content": "  the FERRY to the island leaves at seven and returns after the last market bell rings. "},
                           {"id": "r-1", "content": A}, {"id": "r-3", "content": B}])
        self.assertEqual(r["dropped"], {"r-2": "r-1"})
        self.assertEqual(r["kept_ids"], ["r-1", "r-3"])

    def test_substring_both_directions(self):
        # shorter (>=40 chars) is the HIGHER id: still dropped
        r = inset.resolve([{"id": "a", "content": A + " " + B}, {"id": "b", "content": A}])
        self.assertEqual(r["dropped"], {"b": "a"})
        # shorter is the LOWER id: longer one dropped
        r = inset.resolve([{"id": "a", "content": A}, {"id": "b", "content": A + " " + B}])
        self.assertEqual(r["dropped"], {"b": "a"})

    def test_short_substring_not_collision(self):
        r = inset.resolve([{"id": "a", "content": "lamp polished"}, {"id": "b", "content": B}])
        self.assertEqual(r["n_dropped"], 0)

    def test_jaccard(self):
        near = A.replace("seven", "eight")
        r = inset.resolve([{"id": "a", "content": A}, {"id": "b", "content": near}, {"id": "c", "content": C}])
        self.assertEqual(r["dropped"], {"b": "a"})

    def test_chain_rule(self):
        # x~y and y~z but not x~z: y dropped (collides with kept x), z kept (only collides with dropped y)
        w = ["w%02d" % i for i in range(40)]
        n = ["n%02d" % i for i in range(5)]
        x = " ".join(w)
        y = " ".join(w[5:] + n)
        z = " ".join(w[20:] + n + ["m%02d" % i for i in range(5)])
        from airp_v3 import leakcheck as L
        self.assertTrue(L.collides(y, L.build_index([x])))
        self.assertTrue(L.collides(z, L.build_index([y])))
        self.assertFalse(L.collides(z, L.build_index([x])) or L.collides(x, L.build_index([z])))
        r = inset.resolve([{"id": "3", "content": z}, {"id": "1", "content": x}, {"id": "2", "content": y}])
        self.assertEqual(r["dropped"], {"2": "1"})
        self.assertEqual(r["kept_ids"], ["1", "3"])

    def test_protect_reports_conflict(self):
        r = inset.resolve([{"id": "a", "content": A}, {"id": "b", "content": A}], protect={"b"})
        self.assertEqual(r["n_dropped"], 0)
        self.assertEqual(r["protected_conflicts"], {"b": "a"})

    def test_deterministic_under_input_order(self):
        rows = [{"id": "a", "content": A}, {"id": "b", "content": A}, {"id": "c", "content": B}, {"id": "d", "content": C}]
        self.assertEqual(inset.resolve(rows), inset.resolve(list(reversed(rows))))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            inset.resolve([{"id": "a", "content": A}, {"id": "a", "content": B}])


if __name__ == "__main__":
    unittest.main()
