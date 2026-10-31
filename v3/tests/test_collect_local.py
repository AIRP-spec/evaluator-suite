"""Refusal and provenance tests for the self-hosted (--backend local) collector."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from airp_v3 import collect
from airp_v3.policy import CollectBlocked, check_prompts, find_policy_verified, sha256_path

V3 = Path(__file__).resolve().parents[1]
POLICY = V3 / "policy" / "POLICY_VERIFIED.json"
MODELS = V3 / "collect" / "models.selfhost.json"


def models():
    return {m["key"]: m for m in json.loads(MODELS.read_text())["models"]}


class TmpPolicy:
    """Copy of the real policy dir that a test can mutate."""

    def __enter__(self):
        self.dir = Path(tempfile.mkdtemp())
        shutil.copytree(V3 / "policy", self.dir / "policy")
        self.path = self.dir / "policy" / "POLICY_VERIFIED.json"
        self.doc = json.loads(self.path.read_text())
        return self

    def save(self):
        self.path.write_text(json.dumps(self.doc))

    def __exit__(self, *a):
        shutil.rmtree(self.dir)


def write_prompts(d: Path, rows, report_sha=None):
    p = d / "prompts.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    rep = d / "report.json"
    rep.write_text(json.dumps({"out_sha256": report_sha or sha256_path(p)}))
    return p, rep


class PolicyGateTests(unittest.TestCase):
    def test_real_policy_accepts_every_planned_model_in_its_role(self):
        for k, m in models().items():
            e = find_policy_verified(POLICY, m, m["role"])
            self.assertIn(e["verdict"], ("CLEAR", "CLEAR-WITH-CONDITIONS"), k)

    def test_no_family_on_both_sides(self):
        fam = lambda h: h.split("/")[0].lower()
        sides = {}
        for m in models().values():
            sides.setdefault(fam(m["hf_id"]), set()).add(m["role"])
        self.assertTrue(all(len(s) == 1 for s in sides.values()), sides)

    def test_refuses_unlisted_model(self):
        m = dict(models()["phi-4"], hf_id="someone/unlisted-model")
        with self.assertRaisesRegex(CollectBlocked, "not listed"):
            find_policy_verified(POLICY, m, "test")

    def test_refuses_excluded_doubt_model(self):
        m = {"hf_id": "meta-llama/Llama-3.3-70B-Instruct", "revision": "x", "role": "test"}
        with self.assertRaisesRegex(CollectBlocked, "DOUBT"):
            find_policy_verified(POLICY, m, "test")

    def test_refuses_doubt_verdict_in_models_list(self):
        with TmpPolicy() as t:
            for e in t.doc["models"]:
                if e["key"] == "phi-4":
                    e["verdict"] = "DOUBT"
            t.save()
            with self.assertRaisesRegex(CollectBlocked, "DOUBT"):
                find_policy_verified(t.path, models()["phi-4"], "test")

    def test_refuses_wrong_role(self):
        with self.assertRaisesRegex(CollectBlocked, "role"):
            find_policy_verified(POLICY, models()["phi-4"], "train")
        with self.assertRaisesRegex(CollectBlocked, "role"):
            find_policy_verified(POLICY, models()["gemma-4-31b"], "test")

    def test_refuses_wrong_revision(self):
        m = dict(models()["phi-4"], revision="0" * 40)
        with self.assertRaisesRegex(CollectBlocked, "revision"):
            find_policy_verified(POLICY, m, "test")

    def test_refuses_license_hash_mismatch_on_disk(self):
        with TmpPolicy() as t:
            lic = t.path.parent / "licenses" / "phi-4.LICENSE"
            lic.write_text(lic.read_text() + "\nchanged\n")
            with self.assertRaisesRegex(CollectBlocked, "sha256 mismatch"):
                find_policy_verified(t.path, models()["phi-4"], "test")

    def test_refuses_model_entry_hash_mismatch(self):
        m = dict(models()["phi-4"], license_sha256="f" * 64)
        with self.assertRaisesRegex(CollectBlocked, "differs"):
            find_policy_verified(POLICY, m, "test")

    def test_refuses_missing_policy(self):
        with self.assertRaisesRegex(CollectBlocked, "not found"):
            find_policy_verified(Path("/nonexistent/POLICY_VERIFIED.json"), models()["phi-4"], "test")


class PromptGateTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_accepts_matching_side(self):
        p, r = write_prompts(self.d, [{"id": "xstest:1", "prompt_set": "xstest", "side": "test", "prompt": "hi"}])
        self.assertEqual(len(check_prompts(p, r, "test")), 1)

    def test_unicode_line_separators_inside_prompts(self):
        # JSONL rows may carry U+2028 / U+0085 inside strings; str.splitlines() would split them
        p = self.d / "prompts.jsonl"
        p.write_text(json.dumps({"id": "aegis2-train:1", "prompt_set": "aegis2-train", "side": "train",
                                 "prompt": "a\u2028b\x85c\x1cd"}, ensure_ascii=False) + "\n", encoding="utf-8")
        self.assertIn("\u2028", p.read_text(encoding="utf-8"))
        r = self.d / "report.json"
        r.write_text(json.dumps({"out_sha256": sha256_path(p)}))
        rows = check_prompts(p, r, "train")
        self.assertEqual(rows[0]["prompt"], "a\u2028b\x85c\x1cd")

    def test_refuses_test_set_on_training_model(self):
        p, r = write_prompts(self.d, [{"id": "xstest:1", "prompt_set": "xstest", "prompt": "hi"}])
        with self.assertRaisesRegex(CollectBlocked, "test side"):
            check_prompts(p, r, "train")

    def test_refuses_training_set_on_test_model(self):
        p, r = write_prompts(self.d, [{"id": "donotanswer:1", "prompt_set": "donotanswer", "prompt": "hi"}])
        with self.assertRaisesRegex(CollectBlocked, "train side"):
            check_prompts(p, r, "test")

    def test_refuses_unknown_set(self):
        p, r = write_prompts(self.d, [{"id": "dolly:1", "prompt_set": "dolly", "prompt": "hi"}])
        with self.assertRaisesRegex(CollectBlocked, "unknown prompt set"):
            check_prompts(p, r, "train")

    def test_refuses_sha_mismatch(self):
        p, r = write_prompts(self.d, [{"id": "xstest:1", "prompt_set": "xstest", "prompt": "hi"}], report_sha="0" * 64)
        with self.assertRaisesRegex(CollectBlocked, "does not match"):
            check_prompts(p, r, "test")

    def test_refuses_missing_report(self):
        p, _ = write_prompts(self.d, [{"id": "xstest:1", "prompt_set": "xstest", "prompt": "hi"}])
        with self.assertRaisesRegex(CollectBlocked, "report"):
            check_prompts(p, self.d / "missing.json", "test")


def fake_server(reasoning=None):
    calls = []

    def caller(base_url, served, prompt, max_tokens, temperature, ctk):
        calls.append({"prompt": prompt, "ctk": ctk, "max_tokens": max_tokens})
        msg = {"content": "response to " + prompt}
        if reasoning:
            msg["reasoning_content"] = reasoning
        return {"id": "r1", "choices": [{"message": msg, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12,
                          "completion_tokens_details": {"reasoning_tokens": 3 if reasoning else 0}}}
    return caller, calls


class RunLocalTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.model = dict(models()["granite-4.2-8b"], served_model="m")
        self.ctx = {"chat_template_kwargs": self.model["chat_template_kwargs"], "temperature": 0.7,
                    "max_tokens": 800, "license_sha256": "L", "verdict": "CLEAR", "policy_sha256": "P",
                    "prompts_sha256": "S"}
        self.rows = [{"id": f"xstest:{i}", "prompt_set": "xstest", "kind": "benign", "prompt": f"p{i}"} for i in range(10)]

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_(self, rows, **kw):
        caller = kw.pop("caller", None) or fake_server()[0]
        args = dict(concurrency=4, max_wall_seconds=0, max_dollars=0, dollars_per_hour=0, billing_start=0)
        args.update(kw)
        return collect.run_local(rows, self.model, "runpod:x/A6000/vllm-0", "http://127.0.0.1:1",
                                 self.d / "out.jsonl", self.ctx, caller=caller, **args)

    def test_provenance_and_thinking_off(self):
        caller, calls = fake_server()
        st = self.run_(self.rows, caller=caller)
        self.assertEqual(st["n_written"], 10)
        self.assertTrue(all(c["ctk"] == {"enable_thinking": False} for c in calls))
        row = json.loads((self.d / "out.jsonl").read_text().splitlines()[0])
        pv = row["provenance"]
        for k in ("model", "revision", "quantization", "host", "role", "prompt_set", "prompt_id", "timestamp",
                  "token_counts", "provider_terms_ref", "license_sha256", "policy_verified_sha256", "prompts_sha256"):
            self.assertIn(k, pv)
        self.assertEqual(pv["token_counts"]["reasoning"], 0)
        self.assertEqual(pv["thinking_forced_off"], {"enable_thinking": False})

    def test_reasoning_tokens_recorded(self):
        caller, _ = fake_server(reasoning="thought")
        self.run_(self.rows[:1], caller=caller)
        row = json.loads((self.d / "out.jsonl").read_text().splitlines()[0])
        self.assertEqual(row["provenance"]["token_counts"]["reasoning"], 3)
        self.assertEqual(row["reasoning_content"], "thought")

    def test_resume_skips_done_ids(self):
        self.run_(self.rows[:4])
        st = self.run_(self.rows)
        self.assertEqual(st["n_skipped_resume"], 4)
        self.assertEqual(st["n_written"], 6)
        ids = [json.loads(l)["id"] for l in (self.d / "out.jsonl").read_text().splitlines()]
        self.assertEqual(len(ids), len(set(ids)), "no duplicate ids after resume")

    def test_dollar_limit_stops(self):
        t = [1000.0]
        st = self.run_(self.rows, max_dollars=1.0, dollars_per_hour=1.0, billing_start=0.0, clock=lambda: t[0] + 3600)
        self.assertEqual(st["stop_reason"], "dollar_limit")
        self.assertEqual(st["n_written"], 0)

    def test_wall_clock_limit_stops(self):
        seq = iter([0.0] + [100.0] * 100)
        st = self.run_(self.rows, max_wall_seconds=50, clock=lambda: next(seq))
        self.assertEqual(st["stop_reason"], "wall_clock_limit")

    def test_errors_recorded_not_silent(self):
        def bad(*a):
            raise OSError("down")
        import airp_v3.collect as c
        orig = c.time.sleep
        c.time.sleep = lambda s: None
        try:
            st = self.run_(self.rows[:2], caller=bad)
        finally:
            c.time.sleep = orig
        self.assertEqual(st["n_errors"], 2)
        self.assertTrue((self.d / "out.errors.jsonl").is_file())

    def test_local_refuses_openrouter_url(self):
        with self.assertRaises(CollectBlocked):
            collect.call_local("https://openrouter.ai/api", "m", "p", 10, 0.7, {})


class MainLocalTests(unittest.TestCase):
    def test_local_backend_does_not_need_openrouter_approval_but_needs_policy(self):
        d = Path(tempfile.mkdtemp())
        try:
            p, r = write_prompts(d, [{"id": "xstest:1", "prompt_set": "xstest", "prompt": "hi"}])
            rc = collect.main(["--backend", "local", "--base-url", "http://127.0.0.1:1", "--models", str(MODELS),
                               "--model-key", "phi-4", "--role", "test", "--policy-file", str(d / "nope.json"),
                               "--prompts", str(p), "--filter-report", str(r), "--host", "h", "--out", str(d / "o.jsonl")])
            self.assertEqual(rc, 2)
            rc = collect.main(["--backend", "local", "--base-url", "http://127.0.0.1:1", "--models", str(MODELS),
                               "--model-key", "phi-4", "--role", "train", "--policy-file", str(POLICY),
                               "--prompts", str(p), "--filter-report", str(r), "--host", "h", "--out", str(d / "o.jsonl")])
            self.assertEqual(rc, 2)
            self.assertFalse((d / "o.jsonl").exists())
        finally:
            shutil.rmtree(d)

    def test_openrouter_backend_still_needs_approval(self):
        rc = collect.main(["--backend", "openrouter", "--prompts", "x", "--models", "y", "--prompt-set", "z",
                           "--out", "/tmp/never.jsonl", "--approval-file", "/nonexistent/OPENROUTER_APPROVAL"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
