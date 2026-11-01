"""v3-safety generator tests. Synthetic benign text only; labels are primitive dicts."""
import json
import re
from pathlib import Path

import pytest

from airp_v3 import v3_safety as vs
from airp_v3.policy import CollectBlocked

NONE = {"stance": "describes", "objects": [], "qualifiers": []}
SH = {"stance": "encourages", "objects": ["self_harm"], "qualifiers": ["directed_at_user"]}
SH_Q = {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}
CSE = {"stance": "describes", "objects": ["sexual_activity"], "qualifiers": ["subject_is_minor"]}


def test_pins_match_files():
    spec, sysp = vs.load_pinned()
    assert spec["system_prompt_sha256"] == vs.SYSTEM_PROMPT_SHA256
    assert "under 18" in sysp and "sexual content" in sysp


def test_unpinned_spec_refused(tmp_path):
    p = tmp_path / "spec.json"; p.write_text(vs.SLOT_SPEC.read_text() + " ")
    with pytest.raises(CollectBlocked):
        vs.load_pinned(spec_path=p)


def test_jobs_shape_and_seed_rule():
    spec, _ = vs.load_pinned()
    jobs = vs.build_jobs(spec)
    assert len(jobs) == 270 and len({j["cell"] for j in jobs}) == 45 and len({j["id"] for j in jobs}) == 270
    import hashlib
    j = jobs[7]
    assert j["seed"] == int(hashlib.sha256(f"v3s|{j['cell']}|{j['sample']}".encode()).hexdigest()[:8], 16)
    assert {j["family"] for j in jobs} == {"v3s-sh01", "v3s-sh02-offer", "v3s-sh03", "v3s-sh04", "v3s-offer-shape"}


def test_request_is_one_system_and_one_user_turn():
    spec, sysp = vs.load_pinned()
    b = vs.request_body(spec, sysp, vs.build_jobs(spec)[0], "m")
    assert [m["role"] for m in b["messages"]] == ["system", "user"]
    assert b["temperature"] == 0.9 and b["max_tokens"] == 400 and b["chat_template_kwargs"] == {"thinking_budget": 0}
    assert "{" not in b["messages"][1]["content"]


def test_no_training_recipe_import():
    import ast
    tree = ast.parse(Path(vs.__file__).read_text())
    body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) else tree.body  # drop module docstring
    src = "\n".join(ast.unparse(n) for n in body)
    for bad in ("recipe.json", "contrast", "kind-label", "kind_label", "train_recipe", "templates"):
        assert bad not in src
    spec = vs.SLOT_SPEC.read_text()
    assert "recipe.json is read" not in spec


def test_slot_spec_has_no_minor_or_sexual_request():
    spec, _ = vs.load_pinned()
    for f in spec["families"]:
        s = f["shape"].lower()
        assert not re.search(r"\b(child|minor|teen|kid|sexual)\b", s)


def test_openai_and_openrouter_refused():
    with pytest.raises(CollectBlocked):
        vs._post("https://api.openai.com", {})


def _fake_post(base_url, body):
    n = 30 if "at most 40" in body["messages"][1]["content"] else 80
    return {"choices": [{"message": {"content": " ".join(["word"] * n)}, "finish_reason": "stop"}]}


def test_generate_resumes_and_records_provenance(tmp_path):
    out = tmp_path / "gen.jsonl"
    st = vs.generate("http://127.0.0.1:1", "m", str(out), "test", concurrency=4, post=_fake_post)
    assert st["n_written"] == 270 and st["n_errors"] == 0
    st2 = vs.generate("http://127.0.0.1:1", "m", str(out), "test", concurrency=4, post=_fake_post)
    assert st2["n_resumed"] == 270 and st2["n_written"] == 0
    r = json.loads(out.read_text().splitlines()[0])
    assert r["provenance"]["slot_spec_sha256"] == vs.SLOT_SPEC_SHA256 and r["provenance"]["synthetic"] is True


def _write(p, rows):
    Path(p).write_text("".join(json.dumps(r) + "\n" for r in rows))


def _fixture(tmp_path):
    gen = tmp_path / "gen.jsonl"
    _write(gen, [{"id": f"g{i}", "content": f"benign sample {i}", "provenance": {"cell": f"v3s-sh01|terse|short", "length_in_band": True}}
                 for i in range(5)])
    real = [{"id": i, "content": "benign real", "provenance": {"real_elicited": True, "model_key": "phi-4"}} for i in ("r1",)]
    it = tmp_path / "items.jsonl"
    _write(it, [{"id": f"g{i}", "content": f"benign sample {i}", "writer_family": "bytedance-seed"} for i in range(5)]
           + [{"id": "r1", "content": "benign real", "writer_family": "microsoft-phi"}])
    ld = tmp_path / "labels"; ld.mkdir()
    lab = {  # mistral, gemma, qwen3
        "g0": (SH, SH, SH),        # positive
        "g1": (NONE, NONE, NONE),  # negative
        "g2": (SH, None, None),    # fewer than 2 valid
        "g3": (CSE, NONE, NONE),   # CSE guard
        "g4": (NONE, NONE, SH_Q),  # qwen3 low-precision fire -> adjudication
        "r1": (SH, SH, NONE),
    }
    for j, k in enumerate(vs.TRIO):
        _write(ld / f"labels-{k}.jsonl", [{"id": i, "primitives": v[j]} for i, v in lab.items()])
    return gen, it, ld, real


def test_todo_and_finalize(tmp_path):
    from airp_v3 import xside
    gen, it, ld, real = _fixture(tmp_path)
    st = vs.todo_adjudication(str(it), str(ld), str(tmp_path / "todo.jsonl"))
    todo = [json.loads(l)["id"] for l in (tmp_path / "todo.jsonl").read_text().splitlines()]
    assert "g4" in todo and "g0" not in todo and st["n_todo"] == len(todo)
    adj = tmp_path / "adj.jsonl"; _write(adj, [{"id": "g4", "primitives": NONE}])
    comb = tmp_path / "combined.jsonl"
    xside.combine_test_a4(str(it), str(ld), str(adj), str(comb), str(tmp_path / "rep.json"))
    rep = vs.finalize(str(gen), str(it), str(ld), str(adj), str(comb), real, tmp_path / "out")
    assert [d["id"] for d in rep["cse_deleted"]] == ["g3"]
    assert "g3" not in gen.read_text() and "g3" not in it.read_text()
    assert rep["generated_positive"] == 1 and rep["real_positive_ids"] == []  # r1 is not a declared real id
    assert rep["ids"]["fewer_than_2_valid"] == ["g2"]
    assert any("validity_bar" in s for s in rep["stop"])  # 1/6 invalid for gemma and qwen3 is below 0.95


def test_seal_input_rows_load(tmp_path):
    from airp_v3.loader import load_items
    gen, it, ld, real = _fixture(tmp_path)
    comb = tmp_path / "combined.jsonl"
    from airp_v3 import xside
    adj = tmp_path / "adj.jsonl"; _write(adj, [{"id": "g4", "primitives": NONE}])
    xside.combine_test_a4(str(it), str(ld), str(adj), str(comb), str(tmp_path / "rep.json"))
    sel = vs.select(str(comb))
    st = vs.seal_input(sel, str(gen), real, str(tmp_path / "seal-in.jsonl"))
    assert st["n"] == 2 and st["n_real"] == 1
    r = json.loads((tmp_path / "seal-in.jsonl").read_text().splitlines()[0])
    assert r["id"] == "g0" and r["expect_primitives"] == SH
    assert len(load_items(tmp_path / "seal-in.jsonl")) == 2


def test_cse_class_name_matches_composition():
    from airp_v3.compose import COMPOSITION_2A_SHA256, load_composition, compose
    comp = load_composition(None, COMPOSITION_2A_SHA256)
    assert vs.CSE_CLASS in compose(CSE, comp)
    assert "compose:" + vs.CSE_CLASS in vs.cse_trigger(CSE, comp)
