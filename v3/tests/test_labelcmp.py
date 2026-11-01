"""Labeler comparison: gate, same-family skip, scoring sanity, side-respecting selection."""
import json, subprocess, sys
from pathlib import Path
import pytest
V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3)); sys.path.insert(0, str(V3 / "tools"))
from airp_v3 import label_local  # noqa: E402
from airp_v3.policy import CollectBlocked  # noqa: E402
import labelcmp_score as S  # noqa: E402

LAB = json.loads((V3 / "labelcmp/labelers.labelcmp.json").read_text())["labelers"]
MODELS = {m["key"]: m for m in json.loads((V3 / "collect/models.selfhost.json").read_text())["models"]}
POL = V3 / "policy/POLICY_VERIFIED.json"


def test_every_candidate_passes_policy_gate():
    for L in LAB:
        assert label_local.gate(L, MODELS[L["key"]], POL, "http://127.0.0.1:18001")["verdict"] in ("CLEAR", "CLEAR-WITH-CONDITIONS")


def test_hosted_url_and_openai_refused():
    L = LAB[0]
    with pytest.raises(CollectBlocked):
        label_local.gate(L, MODELS[L["key"]], POL, "https://openrouter.ai/api")
    with pytest.raises(CollectBlocked):
        label_local.gate(dict(L, key="openai/gpt-oss-120b"), MODELS[L["key"]], POL, "http://127.0.0.1:1")


def test_families_distinct_and_roles_match_policy():
    assert len({L["family"] for L in LAB}) == len(LAB)
    for L in LAB:
        assert MODELS[L["key"]]["role"] == L["role"]


def test_scoring_gold_is_perfect_and_empty_misses_all_safety():
    comp = S.load_composition(None, S.COMPOSITION_2A_SHA256)
    gold = [{"id": "a", "gold": {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}, "classes": ["self_harm"]},
            {"id": "b", "gold": {"stance": "describes", "objects": [], "qualifiers": ["is_mention_not_use"]}, "classes": []}]
    s = S.score(gold, {g["id"]: g["gold"] for g in gold}, comp)
    assert s["class_set_exact"] == 1.0 and s["primitives_exact"] == 1.0
    e = S.score(gold, {}, comp)
    assert e["classes"]["self_harm"]["fn"] == 1 and e["valid"] == 0


def test_selection_respects_sides():
    mk = lambda cse: {"P": {"valid_rate": 1.0, "class_set_exact": cse, "min_safety_recall": 1.0, "primitives_exact": cse}}
    scores = {L["key"]: mk(0.5 + i / 100) for i, L in enumerate(LAB)}
    sel = S.select(scores, LAB)
    roles = {L["key"]: L["role"] for L in LAB}
    assert all(roles[k] == "train" for k in sel["label_test_rows"]["pair"])
    assert all(roles[k] == "test" for k in sel["label_train_rows"]["pair"])
