"""AMENDMENT / supplement S1: writer selection by self_harm-compose rate (counts only)."""
import json, tempfile
from pathlib import Path
from airp_v3 import supplement_pilot as sp
from airp_v3.compose import COMPOSITION_2A_SHA256, load_composition

COMP = load_composition(None, COMPOSITION_2A_SHA256)
SH = {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}
NONE = {"stance": "describes", "objects": [], "qualifiers": []}


def _write(p, rows):
    Path(p).write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_score_picks_highest_rate_tie_smaller():
    with tempfile.TemporaryDirectory() as d:
        outs = []
        for k, n_ok, n_tot in (("granite-4.2-8b", 2, 4), ("phi-4", 2, 4), ("seed-oss-36b", 1, 4), ("glm-4.5-air", 3, 4)):
            rows = [{"id": f"p{i}::{k}@pilot-s0", "provenance": {"model_key": k}, "content": ""} for i in range(n_tot)]
            outs.append(f"{d}/{k}.jsonl"); _write(outs[-1], rows)
        labs = []
        for k, n_ok, n_tot in (("granite-4.2-8b", 2, 4), ("phi-4", 2, 4), ("seed-oss-36b", 1, 4), ("glm-4.5-air", 3, 4)):
            for i in range(n_tot):
                labs.append({"id": f"p{i}::{k}@pilot-s0", "primitives": SH if i < n_ok else NONE})
        lp = f"{d}/labels.jsonl"; _write(lp, labs)
        r = sp.score_pilot(lp, outs, COMP)
        # glm 0.75, granite/phi 0.5 (granite smaller wins tie), seed 0.25
        assert r["chosen_writers"] == ["glm-4.5-air", "granite-4.2-8b"]
        assert r["by_candidate"]["glm-4.5-air"]["rate"] == 0.75
