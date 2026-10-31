"""Dry-run of the self-hosted collection path (no pod, no GPU).

Uses a tiny CPU model behind tools/tiny_openai_server.py, a dry-run POLICY_VERIFIED
that lists only that model, and benign OASST2 first turns. Proves every gate refuses
(exit 2, nothing written) and that an allowed run writes full provenance and resumes.

  python3 tools/dryrun_selfhost.py --base-url http://127.0.0.1:8765 --test-prompts <prompts-test.jsonl>
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3))
from airp_v3 import collect, filter_cse  # noqa: E402

D = V3 / "dryrun" / "selfhost"
TINY = {"hf_id": "HuggingFaceTB/SmolLM2-135M-Instruct", "revision": "12fd25f77366fa6b3b4b768ec3050bf629380bac"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args: list[str]) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = collect.main(args)
    return rc, err.getvalue().strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--test-prompts", required=True, help="real prompts-test.jsonl; only 8 benign OASST2 rows are used")
    a = ap.parse_args()
    work = D / "work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "policy" / "licenses").mkdir(parents=True)
    # fixture prompts: 8 benign OASST2 first turns, re-filtered so the report carries out_sha256
    rows = [json.loads(l) for l in Path(a.test_prompts).read_text().splitlines() if l.strip()]
    fx = [r for r in rows if r["prompt_set"] == "oasst2-firstturn"][:8]
    for r in fx:
        r["assigned_model"] = "tiny-smollm2"
    src = D / "fixture-in.jsonl"
    src.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fx))
    filter_cse.main(["--in", str(src), "--out", str(D / "fixture-prompts.jsonl"), "--report", str(D / "fixture-filter-report.json")])
    prompts, report = D / "fixture-prompts.jsonl", D / "fixture-filter-report.json"
    # train-side fixture (for the reverse refusal)
    trow = [{"id": "donotanswer:dry", "prompt_set": "donotanswer", "side": "train", "kind": "harmful", "prompt": "placeholder"}]
    tp = work / "train-prompts.jsonl"
    tp.write_text(json.dumps(trow[0]) + "\n")
    tr = work / "train-report.json"
    tr.write_text(json.dumps({"out_sha256": sha(tp)}))
    # dry policy: tiny model CLEAR (test), a DOUBT fixture, plus a hash-mismatch fixture
    lic = work / "policy" / "licenses" / "smollm2.README.md"
    shutil.copy(D / "smollm2.README.md", lic)
    base = {"license_name": "Apache-2.0", "license_url": "https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct",
            "license_doc": "smollm2.README.md", "license_sha256": sha(lic), "retrieval_date": "2026-11-01"}
    pol = {"schema": "airp-v3-policy-verified/1", "license_dir": "licenses", "models": [
        dict(base, key="tiny-smollm2", **TINY, role="test", verdict="CLEAR"),
        dict(base, key="tiny-doubt", hf_id="fixture/doubt-model", revision="r1", role="test", verdict="DOUBT"),
        dict(base, key="tiny-badhash", hf_id="fixture/badhash-model", revision="r1", role="test", verdict="CLEAR",
             license_sha256="0" * 64),
        dict(base, key="tiny-train", hf_id="fixture/train-model", revision="r1", role="train", verdict="CLEAR"),
    ], "excluded": []}
    polp = work / "policy" / "POLICY_VERIFIED.json"
    polp.write_text(json.dumps(pol, indent=2))
    mk = lambda key, hf, rev, role, ctk=None, lsha=None: {
        "key": key, "hf_id": hf, "revision": rev, "role": role, "quantization": "fp32 (CPU dry-run)",
        "chat_template_kwargs": ctk or {}, "terms_ref": "Apache-2.0; dry-run fixture", "license_sha256": lsha or sha(lic)}
    models = {"models": [
        mk("tiny-smollm2", TINY["hf_id"], TINY["revision"], "test", {"enable_thinking": False}),
        mk("tiny-unlisted", "fixture/unlisted-model", "r1", "test"),
        mk("tiny-doubt", "fixture/doubt-model", "r1", "test"),
        mk("tiny-badhash", "fixture/badhash-model", "r1", "test", lsha="0" * 64),
        mk("tiny-train", "fixture/train-model", "r1", "train"),
        mk("tiny-openai", "openai/gpt-oss-20b", "r1", "test"),
    ]}
    mp = work / "models.json"
    mp.write_text(json.dumps(models, indent=2))
    bad_report = work / "bad-report.json"
    bad_report.write_text(json.dumps({"out_sha256": "0" * 64}))
    out = work / "out.jsonl"
    common = ["--backend", "local", "--base-url", a.base_url, "--models", str(mp), "--policy-file", str(polp),
              "--host", "box-cpu/none/tiny-openai-server", "--concurrency", "2", "--max-tokens", "48"]
    cases = [
        ("unlisted model", ["--model-key", "tiny-unlisted", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("DOUBT verdict", ["--model-key", "tiny-doubt", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("license hash mismatch", ["--model-key", "tiny-badhash", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("wrong role", ["--model-key", "tiny-smollm2", "--role", "train", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("test prompt set on training model", ["--model-key", "tiny-train", "--role", "train", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("training prompt set on test model", ["--model-key", "tiny-smollm2", "--role", "test", "--prompts", str(tp), "--filter-report", str(tr)]),
        ("prompts sha != filter report", ["--model-key", "tiny-smollm2", "--role", "test", "--prompts", str(prompts), "--filter-report", str(bad_report)]),
        ("OpenAI model", ["--model-key", "tiny-openai", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report)]),
        ("max tokens over 800", ["--model-key", "tiny-smollm2", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report), "--max-tokens", "900"]),
    ]
    summary = {"refusals": [], "allowed": {}}
    for name, extra in cases:
        rc, err = run(common + extra + ["--out", str(out)])
        summary["refusals"].append({"case": name, "exit_code": rc, "refused": rc == 2 and not out.exists(),
                                    "message": err.replace(str(V3), "v3")[:240]})
    # allowed run: first 4 rows, then resume to all 8
    rc1, _ = run(common + ["--model-key", "tiny-smollm2", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report),
                           "--out", str(out), "--limit", "4", "--summary", str(work / "run1.json")])
    rc2, _ = run(common + ["--model-key", "tiny-smollm2", "--role", "test", "--prompts", str(prompts), "--filter-report", str(report),
                           "--out", str(out), "--assigned-only", "--summary", str(work / "run2.json")])
    outs = [json.loads(l) for l in out.read_text().splitlines()]
    pv = outs[0]["provenance"]
    summary["allowed"] = {
        "exit_codes": [rc1, rc2],
        "run1": json.loads((work / "run1.json").read_text()),
        "run2_resume": json.loads((work / "run2.json").read_text()),
        "n_rows": len(outs), "n_unique_ids": len({o["id"] for o in outs}),
        "provenance_keys": sorted(pv),
        "provenance_example": {k: pv[k] for k in ("model", "revision", "quantization", "role", "host", "backend", "prompt_set",
                                                  "prompt_id", "token_counts", "thinking_forced_off", "provider_terms_ref",
                                                  "license_sha256", "policy_verdict", "prompts_sha256")},
    }
    summary["allowed"]["run1"].pop("out", None)
    summary["allowed"]["run2_resume"].pop("out", None)
    summary["all_refusals_ok"] = all(r["refused"] for r in summary["refusals"])
    summary["fixture_prompts_sha256"] = sha(prompts)
    (D / "DRYRUN-SELFHOST-SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"all_refusals_ok": summary["all_refusals_ok"], "n_rows": len(outs),
                      "resume_skipped": summary["allowed"]["run2_resume"]["n_skipped_resume"],
                      "exit_codes": [rc1, rc2]}))
    shutil.rmtree(work)
    src.unlink()
    return 0 if summary["all_refusals_ok"] and len(outs) == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
