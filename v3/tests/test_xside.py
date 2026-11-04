import json
from airp_v3.compose import COMPOSITION_2A_SHA256, load_composition
from airp_v3 import xside

C = load_composition(None, COMPOSITION_2A_SHA256)
NONE = {"stance": "describes", "objects": [], "qualifiers": []}
PROF = {"stance": "describes", "objects": ["profanity"], "qualifiers": []}
SH = {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}


def test_majority_no_adjudication():
    d = xside.decide_test([PROF, PROF, NONE], C)
    assert d["adjudicate"] == [] and d["majority_classes"] == ["profanity"]
    f = xside.finalize_test(d, None, C)
    assert f["status"] == "majority" and f["final_classes"] == ["profanity"] and f["primitives_consistent"]


def test_single_safety_fire_goes_to_adjudication_and_adjudicator_decides():
    d = xside.decide_test([NONE, NONE, SH], C)
    assert d["adjudicate"] == ["any_fire:self_harm"]
    assert xside.finalize_test(d, NONE, C)["final_classes"] == []
    assert xside.finalize_test(d, SH, C)["final_classes"] == ["self_harm"]
    assert xside.finalize_test(d, None, C)["status"] == "adjudication_missing_or_invalid"


def test_invalid_abstains_and_tie_goes_to_adjudication():
    d = xside.decide_test([PROF, NONE, None], C)
    assert "tie:profanity" in d["adjudicate"]
    f = xside.finalize_test(d, PROF, C)
    assert f["final_classes"] == ["profanity"]


def test_fewer_than_two_valid():
    d = xside.decide_test([PROF, None, None], C)
    assert "fewer_than_2_valid" in d["adjudicate"]


def test_train_queue(tmp_path):
    items = tmp_path / "items.jsonl"
    items.write_text("".join(json.dumps({"id": i, "content": "x", "writer_family": "qwen"}) + "\n" for i in "abcd"))
    ld = tmp_path / "l"; ld.mkdir()
    P = {"a": NONE, "b": PROF, "c": SH, "d": None}
    S = {"a": NONE, "b": NONE, "c": SH, "d": NONE}
    for k, m in (("nemotron-3-super", P), ("seed-oss-36b", S)):
        (ld / f"labels-{k}.jsonl").write_text("".join(json.dumps({"id": i, "primitives": p}) + "\n" for i, p in m.items()))
    r = xside.combine_train(items, ld, tmp_path / "f.jsonl", tmp_path / "q.jsonl", tmp_path / "r.json")
    assert r["agreed_rows"] == 1 and r["queued_rows"] == 3
    q = {json.loads(l)["id"]: json.loads(l)["reasons"] for l in (tmp_path / "q.jsonl").read_text().splitlines()}
    assert q == {"b": ["class_disagreement"], "c": ["fire:self_harm"], "d": ["primary_invalid"]}


def test_adj_messages_has_no_extra_text():
    m = xside.adj_messages("G", "CONTENT", [NONE, None, PROF])
    assert "Labeler B: (invalid output)" in m[1]["content"] and m[1]["content"].count("CONTENT") == 1


CSE_P = {"stance": "describes", "objects": ["sexual_activity"], "qualifiers": ["subject_is_minor"]}


def test_a3_hp_fire_stands_over_adjudication():
    d = xside.decide_test_a3([NONE, SH, NONE], NONE, C)  # gemma (HP on self_harm) fires; qwen3 adjudication said no
    assert d["status"] == "hp_fire_stands" and "self_harm" in d["final_classes"] and d["disputed_classes"] == []


def test_a3_recorded_mention_reason_overturns():
    d = xside.decide_test_a3([NONE, SH, NONE], NONE, C, {"self_harm": "mention"})
    assert d["status"] == "adjudicated" and d["disputed_classes"] == ["self_harm"]


def test_a3_low_precision_fire_goes_to_adjudication():
    d = xside.decide_test_a3([NONE, NONE, SH], None, C)  # qwen3 self_harm precision < 0.95
    assert d["status"] == "needs_adjudication"
    d = xside.decide_test_a3([NONE, NONE, SH], NONE, C)
    assert d["status"] == "adjudicated" and d["disputed_classes"] == ["self_harm"]


def test_a3_qwen3_cse_fire_is_high_precision():
    d = xside.decide_test_a3([NONE, NONE, CSE_P], NONE, C)
    assert d["status"] == "hp_fire_stands" and d["final_classes"] == ["child_sexual_exploitation"]


def test_a3_classes_always_composed_from_primitives():
    d = xside.decide_test_a3([PROF, PROF, NONE], None, C)
    assert d["status"] == "primitive_majority" and d["final_classes"] == ["profanity"]
    d = xside.decide_test_a3([PROF, NONE, None], None, C)
    assert "tie:profanity" in d["trace"] and d["status"] == "needs_adjudication"


def test_a3_train_triggers():
    w, _, _ = xside.train_queue_a3(CSE_P, NONE, C)
    assert "hp_fire_stands_unless_mention_or_refusal:child_sexual_exploitation" in w
    w, _, _ = xside.train_queue_a3(SH, SH, C)
    assert w == ["lp_fire:self_harm"]


# AMENDMENT-4: majority primitives + only the HP labeler's safety primitives
VP = {"stance": "conveys_method", "objects": ["violence_person"], "qualifiers": ["exceeds_common_knowledge"]}
SH_RICH = {"stance": "encourages", "objects": ["self_harm", "violence_person", "profanity"], "qualifiers": []}


def test_a4_majority_plus_safety_only():
    # gemma (HP self_harm) fires with extra non-safety primitives; majority is describes/none
    d = xside.decide_test_a4([NONE, SH_RICH, NONE], NONE, C)
    assert d["status"] == "hp_fire_stands_a4"
    assert d["final_primitives"] == {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}
    assert d["final_classes"] == ["self_harm"] and d["disputed_classes"] == [] and d["standing_not_composed"] == []


def test_a4_cse_overlay_keeps_majority_non_safety():
    d = xside.decide_test_a4([VP, VP, CSE_P], None, C)  # qwen3 HP on CSE
    fp = d["final_primitives"]
    assert fp["stance"] == "conveys_method" and fp["objects"] == ["sexual_activity", "violence_person"]
    assert fp["qualifiers"] == ["exceeds_common_knowledge", "subject_is_minor"]
    assert "child_sexual_exploitation" in d["final_classes"] and "criminal_assistance" in d["final_classes"]


def test_a4_mention_gate_dropped_only_when_source_lacks_it():
    M = {"stance": "describes", "objects": [], "qualifiers": ["is_mention_not_use"]}
    d = xside.decide_test_a4([M, M, CSE_P], None, C)
    assert d["final_classes"] == ["child_sexual_exploitation"] and "is_mention_not_use" not in d["final_primitives"]["qualifiers"]


def test_a4_non_hp_rows_identical_to_a3():
    for L in ([PROF, PROF, NONE], [PROF, NONE, None], [NONE, NONE, SH]):
        a3 = xside.decide_test_a3(L, NONE, C); a4 = xside.decide_test_a4(L, NONE, C)
        assert {k: a4[k] for k in a3} == a3 and a4["a4_changes"] == []


# AMENDMENT-5: train-queue majority with guide-reader
VIO = {"stance": "depicts", "objects": ["violence_person"], "qualifiers": []}


def test_a5_pick_reader():
    g = {"nemotron-3-super": {"valid_frac": 1.0, "exact": 0.8159}, "qwen3-30b-a3b-2507": {"valid_frac": 1.0, "exact": 0.7186}}
    assert xside.pick_guide_reader(g) == "nemotron-3-super"  # qwen is a train-side writer family -> ineligible


def test_a5_majority_and_tiebreak():
    d = xside.decide_train_a5(PROF, NONE, PROF, C)
    assert d["status"] == "decided" and d["final_classes"] == ["profanity"]
    d = xside.decide_train_a5(PROF, None, NONE, C)  # seed invalid: reader breaks the tie
    assert d["final_classes"] == []


def test_a5_three_way_drops():
    d = xside.decide_train_a5(PROF, NONE, VIO, C)
    assert d["status"] == "dropped" and d["drop_reason"].startswith("three_way")


def test_a5_cse_and_reader_invalid_drop():
    assert xside.decide_train_a5(NONE, NONE, CSE_P, C)["drop_reason"] == "cse_flag_any_labeler_unread"
    assert xside.decide_train_a5(PROF, NONE, None, C)["drop_reason"] == "reader_invalid"
