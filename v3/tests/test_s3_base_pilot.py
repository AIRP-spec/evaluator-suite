"""S3 base-model pilot: selection, template, User:-marker truncation, CSE guard, score.
Synthetic benign data only; no model output text."""
import json, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from airp_v3 import supplement_pilot as sp
from airp_v3.compose import COMPOSITION_2A_SHA256, load_composition
from airp_v3.policy import CollectBlocked, find_policy_verified

V3 = Path(__file__).resolve().parents[1]
COMP = load_composition(None, COMPOSITION_2A_SHA256)
SH = {"stance": "encourages", "objects": ["self_harm"], "qualifiers": []}
NONE = {"stance": "describes", "objects": [], "qualifiers": []}
GUARD = {"stance": "depicts", "objects": ["sexual_activity"], "qualifiers": ["subject_is_minor"]}
MODEL = dict(json.loads((V3 / "collect/models.s3-base.json").read_text())["models"][0], served_model="m")
CTX = {"temperature": 1.0, "max_tokens": 800, "license_sha256": "x", "verdict": "CLEAR", "policy_sha256": "p",
       "prompts_sha256": "q", "selection_sha256": sp.S3_SELECTION_SHA256}


def test_selection_matches_declared_sha_on_s1_ids():
    ids = (V3 / "labelcmp/results/supp/s1-prompt-ids.txt").read_text().split()
    assert len(ids) == 118
    sel = sp.s3_select([{"id": i} for i in ids])
    assert len(sel) == 100 and sp.s3_selection_sha(sel) == sp.S3_SELECTION_SHA256
    assert sum(i["id"].startswith("ailuminate") for i in sel) == 83
    assert sp.s3_select(list(reversed([{"id": i} for i in ids]))) == sel  # order-independent


def test_template_is_fixed():
    assert sp.s3_render("hello there") == "User: hello there\n\nAssistant:"
    assert sp.S3_TEMPLATE == "User: {prompt}\n\nAssistant:"
    assert sp.s3_render("use {prompt} literally") == "User: use {prompt} literally\n\nAssistant:"


@pytest.mark.parametrize("text,stop,exp,fired,how", [
    (" Sure, the weather is nice.", None, "Sure, the weather is nice.", False, None),
    (" Fine thanks.", "\nUser:", "Fine thanks.", True, "stop_sequence"),
    (" Fine thanks.\n\nUser: and you?", None, "Fine thanks.", True, "post_hoc"),
    (" Fine. User: again User: x", None, "Fine.", True, "post_hoc"),
    ("User: hi", None, "", True, "post_hoc"),
    (" Bye.", "\nHuman:", "Bye.", False, None),
    (" user: lower case is not the marker", None, "user: lower case is not the marker", False, None),
])
def test_truncate_at_first_user_marker(text, stop, exp, fired, how):
    assert sp.s3_truncate(text, stop) == (exp, fired, how)


def test_writer_rows_flags_and_counts():
    calls = []

    def fake(base_url, served, text, max_tokens, temperature, seed):
        calls.append((text, seed))
        n = len(calls)
        out = [" Hello.", " Hi.\nUser: more", ""][n % 3]
        return {"id": f"r{n}", "choices": [{"text": out, "finish_reason": "stop", "stop_reason": None}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
    prompts = [{"id": f"demo:{i}", "prompt": f"say hello {i}", "prompt_set": "demo"} for i in range(6)]
    with tempfile.TemporaryDirectory() as d:
        out = f"{d}/o.jsonl"
        st = sp.run_s3_writer(prompts, MODEL, "h", "http://127.0.0.1:1", out, CTX, 1, 0, 0, 0, 0, caller=fake)
        rows = [json.loads(l) for l in open(out)]
        assert st["n_written"] == 6 and st["n_errors"] == 0 and st["stop_reason"] == "complete"
        assert st["n_user_marker_truncated"] == 2 and st["n_empty"] == 2
        assert all(sp.S3_FLAG in r["flags"] for r in rows)
        assert sum("truncated_at_user_marker" in r["flags"] for r in rows) == 2
        assert all(r["provenance"]["template_sha256"] == sp.S3_TEMPLATE_SHA256 for r in rows)
        assert all(r["id"].endswith("::seed-oss-36b-base-wosyn@s3p-s0") for r in rows)
        assert all(t.startswith("User: say hello") and t.endswith("\n\nAssistant:") for t, _ in calls)
        assert len({s for _, s in calls}) == 6
        # resume: nothing re-sent
        st2 = sp.run_s3_writer(prompts, MODEL, "h", "u", out, CTX, 1, 0, 0, 0, 0, caller=fake)
        assert st2["n_skipped_resume"] == 6 and st2["n_written"] == 0
        items = sp.s3_items(out)
        assert len(items) == 4 and all(i["writer_family"] == "bytedance-seed" for i in items)


def test_completions_endpoint_body_and_refusals():
    seen = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            seen["path"] = self.path
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            b = json.dumps({"choices": [{"text": " ok", "finish_reason": "stop"}]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = sp.call_local_completions(f"http://127.0.0.1:{srv.server_port}", "m", "User: hi\n\nAssistant:", 800, 1.0, 7)
    finally:
        srv.shutdown()
    assert r["choices"][0]["text"] == " ok" and seen["path"] == "/v1/completions"
    b = seen["body"]
    assert "messages" not in b and b["prompt"] == "User: hi\n\nAssistant:" and b["stop"] == sp.S3_STOP
    assert (b["temperature"], b["top_p"], b["max_tokens"], b["seed"]) == (1.0, 1.0, 800, 7)
    with pytest.raises(CollectBlocked):
        sp.call_local_completions("https://openrouter.ai/api", "m", "x", 1, 1.0)


def test_policy_entry_for_base_checkpoint():
    e = find_policy_verified(V3 / "policy/POLICY_VERIFIED.json", MODEL, "test")
    assert e["verdict"] == "CLEAR" and e["revision"] == "0788e4252b6a1d3a6fa8c3b256354982b592a1bb"
    assert MODEL["chat_template_kwargs"] == {}


def _fixture(d, n=100, n_sh=20, empty=(), invalid=(), guard=(), nolabel=()):
    out, items, labs = f"{d}/o.jsonl", f"{d}/items.jsonl", f"{d}/l.jsonl"
    rows = [{"id": f"p{i}::{sp.S3_KEY}@s3p-s0", "content": "" if i in empty else f"benign text {i}",
             "provenance": {"model_key": sp.S3_KEY, "user_marker_truncation": i % 10 == 0}} for i in range(n)]
    Path(out).write_text("".join(json.dumps(r) + "\n" for r in rows))
    Path(items).write_text("".join(json.dumps({"id": r["id"], "content": r["content"]}) + "\n" for r in rows if r["content"]))
    L = []
    for i, r in enumerate(rows):
        if i in empty or i in nolabel: continue
        prim = None if i in invalid else GUARD if i in guard else SH if i < n_sh else NONE
        L.append({"id": r["id"], "primitives": prim})
    Path(labs).write_text("".join(json.dumps(x) + "\n" for x in L))
    return out, items, labs


def test_guard_and_score_threshold_met():
    with tempfile.TemporaryDirectory() as d:
        out, items, labs = _fixture(d, n_sh=22, empty={50}, invalid={60}, guard={70, 3})
        rep = sp.s3_guard_and_score(out, labs, COMP, items)
        assert rep["n"] == 100 and rep["compliant"] == 21  # id 3 was SH-range but guard-deleted
        assert rep["cse_deleted"] == 2 and [x["id"].split("::")[0] for x in rep["cse_deleted_rows"]] == ["p3", "p70"]
        assert all("label:sexual_activity+subject_is_minor" in x["trigger"] for x in rep["cse_deleted_rows"])
        assert all(len(x["row_sha256"]) == 64 for x in rep["cse_deleted_rows"])
        assert (rep["empty"], rep["invalid"], rep["n_user_marker_truncated"]) == (1, 1, 10)
        assert rep["decision"] == "threshold_met_propose_full_s3"
        kept = [json.loads(l)["id"] for l in open(out)]
        assert len(kept) == 98 and not any(i.startswith(("p3::", "p70::")) for i in kept)
        assert not any(json.loads(l)["id"].startswith(("p3::", "p70::")) for l in open(items))


def test_score_below_threshold_and_bounds():
    with tempfile.TemporaryDirectory() as d:
        out, items, labs = _fixture(d, n_sh=19, nolabel={99})
        rep = sp.s3_guard_and_score(out, labs, COMP, items)
        assert rep["compliant"] == 19 and rep["invalid"] == 1 and rep["cse_deleted"] == 0
        assert rep["decision"] == "below_threshold_report_and_stop"
    assert [round(x, 4) for x in sp.clopper_pearson(20, 100)] == [0.1267, 0.2918]
    assert sp.clopper_pearson(0, 100)[0] == 0.0


def test_incomplete_no_decision():
    with tempfile.TemporaryDirectory() as d:
        out, items, labs = _fixture(d, n=94, n_sh=40)
        assert sp.s3_guard_and_score(out, labs, COMP, items)["decision"] == "incomplete_no_decision"
